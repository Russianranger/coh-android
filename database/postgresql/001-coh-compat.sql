-- Run as the owner of the game database (coh_game), never a superuser service.
-- Re-runnable migration; contains no game data and never drops tables.
BEGIN;
CREATE SCHEMA IF NOT EXISTS dbo AUTHORIZATION CURRENT_USER;
CREATE TABLE IF NOT EXISTS dbo.coh_schema_version (
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
INSERT INTO dbo.coh_schema_version(version) VALUES (1) ON CONFLICT DO NOTHING;
COMMIT;
