#ifndef COH_WINE_ODBC_H
#define COH_WINE_ODBC_H

#ifdef _WIN32
#include <windows.h>
#endif
#include <sql.h>
#include <sqlext.h>

#ifdef COH_WINE_ODBC
#ifdef __cplusplus
extern "C" {
#endif
SQLRETURN cohWineGetInfo(SQLHDBC connection, SQLUSMALLINT type, SQLPOINTER value,
                         SQLSMALLINT capacity, SQLSMALLINT *length);
SQLRETURN cohWineColumns(SQLHSTMT statement,
    SQLCHAR *catalog, SQLSMALLINT catalog_length, SQLCHAR *schema, SQLSMALLINT schema_length,
    SQLCHAR *table, SQLSMALLINT table_length, SQLCHAR *column, SQLSMALLINT column_length);
SQLRETURN cohWineTables(SQLHSTMT statement,
    SQLCHAR *catalog, SQLSMALLINT catalog_length, SQLCHAR *schema, SQLSMALLINT schema_length,
    SQLCHAR *table, SQLSMALLINT table_length, SQLCHAR *type, SQLSMALLINT type_length);
SQLRETURN cohWineForeignKeys(SQLHSTMT statement,
    SQLCHAR *primary_catalog, SQLSMALLINT primary_catalog_length,
    SQLCHAR *primary_schema, SQLSMALLINT primary_schema_length,
    SQLCHAR *primary_table, SQLSMALLINT primary_table_length,
    SQLCHAR *foreign_catalog, SQLSMALLINT foreign_catalog_length,
    SQLCHAR *foreign_schema, SQLSMALLINT foreign_schema_length,
    SQLCHAR *foreign_table, SQLSMALLINT foreign_table_length);
#ifdef __cplusplus
}
#endif

/* Pinned Wine implements these original ANSI names; the A aliases are stubs.
 * Existing statement preparation is generated ASCII SQL with bound values. */
#define SQLDriverConnectA SQLDriverConnect
#define SQLExecDirectA SQLExecDirect
#define SQLPrepareA SQLPrepare
#undef SQLGetInfo
#define SQLGetInfo cohWineGetInfo
#define SQLColumnsA cohWineColumns
#define SQLTablesA cohWineTables
#define SQLForeignKeysA cohWineForeignKeys
#endif
#endif
