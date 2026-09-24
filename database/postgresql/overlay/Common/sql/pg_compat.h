/* PostgreSQL dialect shared by DbServer and the ODBC integration probe.
 * Inputs are trusted, source-generated schema identifiers, never player text.
 * SQL format strings below are used directly in the patched DbServer.
 */
#ifndef COH_PG_COMPAT_H
#define COH_PG_COMPAT_H
#include <stdio.h>
#include <string.h>

/* Explicit unsigned conversion: psqlODBC 18 rejects 255 as signed tinyint. */
#define COH_PG_BYTE_CTYPE SQL_C_UTINYINT

/* PostgreSQL index names are schema-wide. CoH reuses e.g. Name_ind on many
 * tables. Hash the complete lower-case table/index pair to avoid truncation.
 * Remove pre-patch indexes only when they actually belong to this table. */
#define COH_PG_ADD_INDEX \
    "DO $$DECLARE n text := 'coh_' || md5(lower('%s:%s')); BEGIN " \
    "EXECUTE format('CREATE INDEX IF NOT EXISTS %%I ON dbo.%%I (%%s)', n, lower('%s'), '%s'); END$$;"
#define COH_PG_DROP_INDEX \
    "DO $$DECLARE t regclass := 'dbo.%s'::regclass; r record; BEGIN " \
    "FOR r IN SELECT c.relname FROM pg_catalog.pg_index i " \
    "JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid " \
    "WHERE i.indrelid=t AND c.relname IN ('coh_' || md5(lower('%s:%s')), lower('%s')) " \
    "LOOP EXECUTE format('DROP INDEX dbo.%%I', r.relname); END LOOP; END$$;"
#define COH_PG_ADD_FK \
    "DO $$BEGIN IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint " \
    "WHERE conrelid='dbo.%s'::regclass AND conname=lower('fk_%s_%s_%s')::name) THEN " \
    "ALTER TABLE dbo.%s ADD CONSTRAINT FK_%s_%s_%s FOREIGN KEY (%s) " \
    "REFERENCES dbo.%s; END IF; END$$;"
#define COH_PG_DROP_FK \
    "ALTER TABLE dbo.%s DROP CONSTRAINT IF EXISTS FK_%s_%s_%s;"
#define COH_PG_INSERT_CONTAINER \
    "SELECT dbo.coh_reserve_id('dbo.%s'::regclass, ?); " \
    "INSERT INTO dbo.%s (ContainerId) VALUES (?);"
#define COH_PG_HIGH_WATER "SELECT dbo.coh_container_high_water('dbo.%s'::regclass);"

/* SQLColumns type names, unlike its display lengths/SQL type codes, identify
 * the actual PG storage type. text/bytea have driver-dependent maximum lengths.
 * varchar serves both ANSI and Unicode fields. Use Unicode for schema reads. */
typedef enum CohPgKind {
    COH_PG_UNKNOWN, COH_PG_SHORT, COH_PG_INT, COH_PG_FLOAT,
    COH_PG_STRING, COH_PG_TIMESTAMP, COH_PG_TEXT, COH_PG_BINARY
} CohPgKind;

static CohPgKind cohPgColumnType(const char *name, int length,
                                char *canonical, size_t capacity)
{
    CohPgKind kind = COH_PG_UNKNOWN;
    const char *type = NULL;
    if (!strcmp(name, "int2") || !strcmp(name, "smallint")) {
        kind = COH_PG_SHORT; type = "int2";
    } else if (!strcmp(name, "int4") || !strcmp(name, "integer")) {
        kind = COH_PG_INT; type = "int4";
    } else if (!strcmp(name, "float4") || !strcmp(name, "real")) {
        kind = COH_PG_FLOAT; type = "float4";
    } else if (!strcmp(name, "varchar") || !strcmp(name, "character varying")) {
        if (length <= 0) return COH_PG_UNKNOWN;
        kind = COH_PG_STRING;
        if (snprintf(canonical, capacity, "varchar(%d)", length) >= (int)capacity)
            return COH_PG_UNKNOWN;
        return kind;
    } else if (!strcmp(name, "timestamp") || !strcmp(name, "timestamp without time zone")) {
        kind = COH_PG_TIMESTAMP; type = "timestamp";
    } else if (!strcmp(name, "text")) {
        kind = COH_PG_TEXT; type = "text";
    } else if (!strcmp(name, "bytea")) {
        kind = COH_PG_BINARY; type = "bytea";
    }
    if (type && snprintf(canonical, capacity, "%s", type) >= (int)capacity)
        return COH_PG_UNKNOWN;
    return kind;
}
#endif
