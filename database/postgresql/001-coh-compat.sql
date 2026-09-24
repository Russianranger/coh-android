-- Run as the owner of the game database (coh_game), never a superuser service.
-- Re-runnable migration; contains no game data and never drops tables.
BEGIN;
CREATE SCHEMA IF NOT EXISTS dbo AUTHORIZATION CURRENT_USER;
-- DbServer prunes unreferenced tables in dbo; keep migration metadata separate.
CREATE SCHEMA IF NOT EXISTS coh_meta AUTHORIZATION CURRENT_USER;
CREATE TABLE IF NOT EXISTS coh_meta.schema_version (
    version integer PRIMARY KEY, installed_at timestamptz NOT NULL DEFAULT now()
);

-- DbServer allocates IDs in memory, then persists on asynchronous connections.
-- A low ID can reach SQL after a high one. Serialize sequence reservations and
-- never decrease the high-water mark. setval is deliberately NOT transactional:
-- failed/rolled-back inserts consume IDs, which prevents reuse after restart.
-- This retains CoH's ONE DbServer writer per shard contract; it does not make
-- two independent in-memory allocators safe to run against the same database.
CREATE OR REPLACE FUNCTION dbo.coh_reserve_id(target regclass, requested integer)
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog AS $$
DECLARE
    seq regclass;
    last_id bigint;
    called boolean;
BEGIN
    IF requested IS NULL OR requested < 1 THEN
        RAISE EXCEPTION 'Container ID must be positive' USING ERRCODE = '22003';
    END IF;
    seq := pg_get_serial_sequence(target::text, 'containerid')::regclass;
    IF seq IS NULL THEN
        RAISE EXCEPTION 'Container table % has no owned sequence', target;
    END IF;
    PERFORM pg_advisory_xact_lock(seq::oid::bigint);
    EXECUTE format('SELECT last_value, is_called FROM %s', seq) INTO last_id, called;
    IF requested > last_id OR NOT called THEN
        PERFORM setval(seq, greatest(last_id, requested), true);
    END IF;
    RETURN requested;
END $$;

-- Reading startup state must not consume or rewind a sequence. MAX also covers
-- rows copied by schema rebuilds or an offline import without reservation calls.
CREATE OR REPLACE FUNCTION dbo.coh_container_high_water(target regclass)
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog AS $$
DECLARE
    seq regclass;
    last_id bigint;
    row_id bigint;
BEGIN
    seq := pg_get_serial_sequence(target::text, 'containerid')::regclass;
    IF seq IS NULL THEN
        RAISE EXCEPTION 'Container table % has no owned sequence', target;
    END IF;
    PERFORM pg_advisory_xact_lock(seq::oid::bigint);
    EXECUTE format('SELECT CASE WHEN is_called THEN last_value ELSE 0 END FROM %s', seq) INTO last_id;
    EXECUTE format('SELECT coalesce(max(containerid), 0) FROM %s', target) INTO row_id;
    RETURN greatest(last_id, row_id)::integer;
END $$;
REVOKE ALL ON FUNCTION dbo.coh_reserve_id(regclass, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION dbo.coh_container_high_water(regclass) FROM PUBLIC;
INSERT INTO coh_meta.schema_version(version) VALUES (1) ON CONFLICT DO NOTHING;

-- Match the game's case-insensitive byte-string cache without conflating
-- accented names, Unicode normalization forms, or trailing spaces.
CREATE OR REPLACE FUNCTION dbo.coh_name_key(value text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
SET search_path = pg_catalog AS $$
    SELECT translate(value COLLATE "C", 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
$$;
REVOKE ALL ON FUNCTION dbo.coh_name_key(text) FROM PUBLIC;

-- Called only during DbServer schema initialization, with source-generated
-- identifiers/types. One statement performs the complete replacement: an error
-- restores the original table, rows, sequence, indexes and foreign keys.
-- This intentionally refuses customized objects it cannot faithfully preserve.
CREATE OR REPLACE FUNCTION dbo.coh_rebuild_table(target regclass, definition text,
                                               copy_columns text, container boolean)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog AS $$
DECLARE
    original_name text;
    replacement text;
    high_water integer;
    inbound jsonb;
    constraints jsonb;
    indexes text[];
    item jsonb;
    command text;
BEGIN
    SELECT relname INTO original_name FROM pg_class
    WHERE oid=target AND relnamespace='dbo'::regnamespace AND relkind='r'
      AND relpersistence='p' AND NOT relrowsecurity AND NOT relforcerowsecurity
      AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
      AND relacl IS NULL;
    IF original_name IS NULL THEN
        RAISE EXCEPTION 'Rebuild requires an ordinary, privately owned dbo table';
    END IF;
    EXECUTE format('LOCK TABLE %s IN ACCESS EXCLUSIVE MODE', target);
    IF EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid=target OR inhparent=target)
       OR EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=target AND NOT tgisinternal)
       OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=target AND attnum>0 AND NOT attisdropped
                  AND (attidentity<>'' OR attgenerated<>'' OR
                       (attnotnull AND attname NOT IN ('containerid','subid'))))
       OR EXISTS (SELECT 1 FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum
                  WHERE d.adrelid=target AND NOT (container AND a.attname='containerid')) THEN
        RAISE EXCEPTION 'Custom table features require a reviewed migration for %', target;
    END IF;
    IF container THEN high_water := dbo.coh_container_high_water(target); END IF;
    replacement := 'coh_rebuild_' || md5(target::oid::text);
    SELECT coalesce(jsonb_agg(jsonb_build_object('schema',n.nspname,'table',t.relname,
                        'name',c.conname,'definition',pg_get_constraintdef(c.oid,true))), '[]'::jsonb)
      INTO inbound FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
      JOIN pg_namespace n ON n.oid=t.relnamespace
      WHERE c.contype='f' AND c.confrelid=target AND c.conrelid<>target;
    SELECT coalesce(jsonb_agg(jsonb_build_object('name',conname,'definition',pg_get_constraintdef(oid,true))
                            ORDER BY (contype='f')), '[]'::jsonb)
      INTO constraints FROM pg_constraint WHERE conrelid=target AND contype<>'p';
    SELECT array_agg(pg_get_indexdef(i.indexrelid)) INTO indexes FROM pg_index i
      WHERE i.indrelid=target AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid=i.indexrelid);
    EXECUTE format('CREATE TABLE dbo.%I (%s)', replacement, definition);
    EXECUTE format('INSERT INTO dbo.%I (%s) SELECT %s FROM %s', replacement, copy_columns, copy_columns, target);
    FOR item IN SELECT * FROM jsonb_array_elements(inbound) LOOP
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I', item->>'schema',item->>'table',item->>'name');
    END LOOP;
    -- No CASCADE: an unhandled dependency must abort, never disappear silently.
    EXECUTE format('DROP TABLE %s', target);
    EXECUTE format('ALTER TABLE dbo.%I RENAME TO %I', replacement, original_name);
    FOR item IN SELECT * FROM jsonb_array_elements(constraints) LOOP
        EXECUTE format('ALTER TABLE dbo.%I ADD CONSTRAINT %I %s', original_name,item->>'name',item->>'definition');
    END LOOP;
    FOR item IN SELECT * FROM jsonb_array_elements(inbound) LOOP
        EXECUTE format('ALTER TABLE %I.%I ADD CONSTRAINT %I %s', item->>'schema',item->>'table',item->>'name',item->>'definition');
    END LOOP;
    IF indexes IS NOT NULL THEN
        FOREACH command IN ARRAY indexes LOOP EXECUTE command; END LOOP;
    END IF;
    IF container AND high_water>0 THEN
        PERFORM dbo.coh_reserve_id(format('dbo.%I',original_name)::regclass,high_water);
    END IF;
END $$;
REVOKE ALL ON FUNCTION dbo.coh_rebuild_table(regclass,text,text,boolean) FROM PUBLIC;
INSERT INTO coh_meta.schema_version(version) VALUES (2) ON CONFLICT DO NOTHING;
COMMIT;
