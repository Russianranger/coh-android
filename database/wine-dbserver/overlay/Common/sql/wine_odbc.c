/* Wine b073859675060c9211fcbccfd90e4e87520dc2c2 ODBC compatibility.
 * Keep the public manager handle when calling W entry points. ANSI metadata
 * forwarding in this Wine version mishandles that handle or optional NULLs.
 * This adapter is linked only into the separately identified Wine DbServer. */
#include "wine_odbc.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#ifndef COH_WINE_ODBC
#error Wine ODBC adapter requires the isolated Wine DbServer build definition
#endif
typedef char coh_sqlwchar_must_be_utf16[(sizeof(SQLWCHAR) == 2) ? 1 : -1];

typedef struct CohWineFilter {
    SQLWCHAR *text;
    SQLSMALLINT length;
} CohWineFilter;

/* SQL metadata lengths are signed 16-bit; SQL_NTS scans are bounded too.
 * Reject malformed UTF-8 rather than silently changing an identifier. */
static int cohWineFilter(SQLCHAR *source, SQLSMALLINT length, CohWineFilter *out)
{
    size_t bytes = 0, position = 0, count = 0;
    out->text = NULL;
    out->length = length;
    if (!source)
        return 1; /* A NULL filter is not an empty string; retain its length. */
    if (length == SQL_NTS) {
        while (bytes <= SHRT_MAX && source[bytes])
            ++bytes;
        if (bytes > SHRT_MAX)
            return 0;
    } else if (length < 0) {
        return 0;
    } else {
        bytes = (size_t)length;
    }
    out->text = (SQLWCHAR *)malloc((bytes + 1) * sizeof(SQLWCHAR));
    if (!out->text)
        return 0;
    while (position < bytes) {
        unsigned long point = source[position++];
        unsigned long minimum = 0;
        unsigned extra = 0, i;
        if (point >= 0xc2 && point <= 0xdf) {
            point &= 0x1f; extra = 1; minimum = 0x80;
        } else if (point >= 0xe0 && point <= 0xef) {
            point &= 0x0f; extra = 2; minimum = 0x800;
        } else if (point >= 0xf0 && point <= 0xf4) {
            point &= 0x07; extra = 3; minimum = 0x10000;
        } else if (point >= 0x80) {
            goto invalid;
        }
        if (position + extra > bytes)
            goto invalid;
        for (i = 0; i < extra; ++i) {
            unsigned next = source[position++];
            if ((next & 0xc0) != 0x80)
                goto invalid;
            point = (point << 6) | (next & 0x3f);
        }
        if (point < minimum || point > 0x10ffff || (point >= 0xd800 && point <= 0xdfff))
            goto invalid;
        if (point >= 0x10000) {
            point -= 0x10000;
            out->text[count++] = (SQLWCHAR)(0xd800 + (point >> 10));
            out->text[count++] = (SQLWCHAR)(0xdc00 + (point & 0x3ff));
        } else {
            out->text[count++] = (SQLWCHAR)point;
        }
    }
    out->text[count] = 0;
    out->length = length == SQL_NTS ? SQL_NTS : (SQLSMALLINT)count;
    return 1;
invalid:
    free(out->text);
    out->text = NULL;
    return 0;
}

static void cohWineFreeFilters(CohWineFilter *filters, unsigned count)
{
    unsigned i;
    for (i = 0; i < count; ++i)
        free(filters[i].text);
}

static int cohWineMakeFilters(SQLCHAR **sources, SQLSMALLINT *lengths,
                              CohWineFilter *filters, unsigned count)
{
    unsigned i;
    memset(filters, 0, sizeof(*filters) * count);
    for (i = 0; i < count; ++i) {
        if (!cohWineFilter(sources[i], lengths[i], &filters[i])) {
            cohWineFreeFilters(filters, count);
            return 0;
        }
    }
    return 1;
}

SQLRETURN cohWineColumns(SQLHSTMT statement,
    SQLCHAR *catalog, SQLSMALLINT catalog_length, SQLCHAR *schema, SQLSMALLINT schema_length,
    SQLCHAR *table, SQLSMALLINT table_length, SQLCHAR *column, SQLSMALLINT column_length)
{
    SQLCHAR *sources[] = {catalog, schema, table, column};
    SQLSMALLINT lengths[] = {catalog_length, schema_length, table_length, column_length};
    CohWineFilter filters[4];
    SQLRETURN result;
    if (!cohWineMakeFilters(sources, lengths, filters, 4)) return SQL_ERROR;
    result = SQLColumnsW(statement, filters[0].text, filters[0].length,
        filters[1].text, filters[1].length, filters[2].text, filters[2].length,
        filters[3].text, filters[3].length);
    cohWineFreeFilters(filters, 4);
    return result;
}

SQLRETURN cohWineTables(SQLHSTMT statement,
    SQLCHAR *catalog, SQLSMALLINT catalog_length, SQLCHAR *schema, SQLSMALLINT schema_length,
    SQLCHAR *table, SQLSMALLINT table_length, SQLCHAR *type, SQLSMALLINT type_length)
{
    SQLCHAR *sources[] = {catalog, schema, table, type};
    SQLSMALLINT lengths[] = {catalog_length, schema_length, table_length, type_length};
    CohWineFilter filters[4];
    SQLRETURN result;
    if (!cohWineMakeFilters(sources, lengths, filters, 4)) return SQL_ERROR;
    result = SQLTablesW(statement, filters[0].text, filters[0].length,
        filters[1].text, filters[1].length, filters[2].text, filters[2].length,
        filters[3].text, filters[3].length);
    cohWineFreeFilters(filters, 4);
    return result;
}

SQLRETURN cohWineForeignKeys(SQLHSTMT statement,
    SQLCHAR *primary_catalog, SQLSMALLINT primary_catalog_length,
    SQLCHAR *primary_schema, SQLSMALLINT primary_schema_length,
    SQLCHAR *primary_table, SQLSMALLINT primary_table_length,
    SQLCHAR *foreign_catalog, SQLSMALLINT foreign_catalog_length,
    SQLCHAR *foreign_schema, SQLSMALLINT foreign_schema_length,
    SQLCHAR *foreign_table, SQLSMALLINT foreign_table_length)
{
    SQLCHAR *sources[] = {primary_catalog, primary_schema, primary_table,
                         foreign_catalog, foreign_schema, foreign_table};
    SQLSMALLINT lengths[] = {primary_catalog_length, primary_schema_length, primary_table_length,
                            foreign_catalog_length, foreign_schema_length, foreign_table_length};
    CohWineFilter filters[6];
    SQLRETURN result;
    if (!cohWineMakeFilters(sources, lengths, filters, 6)) return SQL_ERROR;
    result = SQLForeignKeysW(statement, filters[0].text, filters[0].length,
        filters[1].text, filters[1].length, filters[2].text, filters[2].length,
        filters[3].text, filters[3].length, filters[4].text, filters[4].length,
        filters[5].text, filters[5].length);
    cohWineFreeFilters(filters, 6);
    return result;
}

SQLRETURN cohWineGetInfo(SQLHDBC connection, SQLUSMALLINT type, SQLPOINTER value,
                         SQLSMALLINT capacity, SQLSMALLINT *length)
{
    /* Only these three string metadata queries exist in sqlconn.c. Numeric
     * queries retain the caller's original storage, length and manager handle. */
    SQLWCHAR wide[1024];
    char utf8[4096];
    SQLSMALLINT wide_bytes = 0;
    SQLRETURN result;
    size_t units, index, count = 0, copied;
    if (type != SQL_DRIVER_NAME && type != SQL_DRIVER_VER && type != SQL_DRIVER_ODBC_VER)
        return SQLGetInfoW(connection, type, value, capacity, length);
    if (value && capacity < 0) return SQL_ERROR;
    if (value && capacity) ((char *)value)[0] = 0;
    if (length) *length = 0;
    memset(wide, 0, sizeof(wide));
    result = SQLGetInfoW(connection, type, wide, (SQLSMALLINT)sizeof(wide), &wide_bytes);
    if (!SQL_SUCCEEDED(result)) return result;
    if (wide_bytes < 0 || (size_t)wide_bytes >= sizeof(wide)
            || wide_bytes % sizeof(SQLWCHAR)) return SQL_ERROR;
    units = (size_t)wide_bytes / sizeof(SQLWCHAR);
    if (wide[units] != 0) return SQL_ERROR;
    for (index = 0; index < units; ++index) {
        unsigned long point = wide[index];
        if (point >= 0xd800 && point <= 0xdbff) {
            unsigned long low;
            if (++index >= units) return SQL_ERROR;
            low = wide[index];
            if (low < 0xdc00 || low > 0xdfff) return SQL_ERROR;
            point = 0x10000 + ((point - 0xd800) << 10) + low - 0xdc00;
        } else if (point >= 0xdc00 && point <= 0xdfff) {
            return SQL_ERROR;
        }
        if (point < 0x80) utf8[count++] = (char)point;
        else if (point < 0x800) {
            utf8[count++] = (char)(0xc0 | (point >> 6));
            utf8[count++] = (char)(0x80 | (point & 0x3f));
        } else if (point < 0x10000) {
            utf8[count++] = (char)(0xe0 | (point >> 12));
            utf8[count++] = (char)(0x80 | ((point >> 6) & 0x3f));
            utf8[count++] = (char)(0x80 | (point & 0x3f));
        } else {
            utf8[count++] = (char)(0xf0 | (point >> 18));
            utf8[count++] = (char)(0x80 | ((point >> 12) & 0x3f));
            utf8[count++] = (char)(0x80 | ((point >> 6) & 0x3f));
            utf8[count++] = (char)(0x80 | (point & 0x3f));
        }
    }
    utf8[count] = 0;
    if (length) *length = (SQLSMALLINT)count;
    if (!value) return result;
    if (!capacity) return SQL_SUCCESS_WITH_INFO;
    copied = count < (size_t)capacity ? count : (size_t)capacity - 1;
    /* Do not leave a partial UTF-8 sequence in a truncated metadata string. */
    while (copied && ((unsigned char)utf8[copied] & 0xc0) == 0x80) --copied;
    memcpy(value, utf8, copied);
    ((char *)value)[copied] = 0;
    return count >= (size_t)capacity ? SQL_SUCCESS_WITH_INFO : result;
}
