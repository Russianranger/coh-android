/* Test double declarations only: the production build uses Windows SDK ODBC.
 * This permits native execution of the actual adapter without a DB driver. */
#ifndef COH_TEST_SQL_H
#define COH_TEST_SQL_H
#include <stdint.h>
typedef int16_t SQLRETURN;
typedef int16_t SQLSMALLINT;
typedef uint16_t SQLUSMALLINT;
typedef uint16_t SQLWCHAR;
typedef unsigned char SQLCHAR;
typedef uint32_t SQLUINTEGER;
typedef void *SQLPOINTER;
typedef void *SQLHDBC;
typedef void *SQLHSTMT;
#define SQL_SUCCESS 0
#define SQL_SUCCESS_WITH_INFO 1
#define SQL_ERROR (-1)
#define SQL_NTS (-3)
#define SQL_SUCCEEDED(value) ((value) == SQL_SUCCESS || (value) == SQL_SUCCESS_WITH_INFO)
#define SQL_DRIVER_NAME 6
#define SQL_DRIVER_VER 7
#define SQL_DRIVER_ODBC_VER 77
#define SQL_TXN_CAPABLE 46
SQLRETURN SQLGetInfoW(SQLHDBC, SQLUSMALLINT, SQLPOINTER, SQLSMALLINT, SQLSMALLINT *);
SQLRETURN SQLColumnsW(SQLHSTMT, SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT,
                     SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT);
SQLRETURN SQLTablesW(SQLHSTMT, SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT,
                    SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT);
SQLRETURN SQLForeignKeysW(SQLHSTMT, SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT,
                         SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT,
                         SQLWCHAR *, SQLSMALLINT, SQLWCHAR *, SQLSMALLINT);
#endif
