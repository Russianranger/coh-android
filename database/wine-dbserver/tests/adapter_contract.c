#include "wine_odbc.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static SQLHDBC manager = (SQLHDBC)(uintptr_t)0x1234;
static unsigned backend_calls, metadata_mode;
static SQLWCHAR filters[6][64];
static SQLSMALLINT lengths[6];
static int nulls[6];
static SQLPOINTER numeric_pointer;
static SQLSMALLINT *numeric_length;

static SQLRETURN capture(SQLHSTMT statement, SQLWCHAR **values, SQLSMALLINT *sizes, unsigned count)
{
    unsigned i, j;
    assert(statement == manager);
    ++backend_calls;
    memset(filters, 0, sizeof(filters));
    for (i = 0; i < count; ++i) {
        nulls[i] = values[i] == NULL;
        lengths[i] = sizes[i];
        if (!values[i]) continue;
        if (sizes[i] == SQL_NTS) {
            for (j = 0; j < 63 && values[i][j]; ++j) filters[i][j] = values[i][j];
        } else {
            assert(sizes[i] >= 0 && sizes[i] < 64);
            memcpy(filters[i], values[i], (size_t)sizes[i] * sizeof(SQLWCHAR));
        }
    }
    return SQL_SUCCESS_WITH_INFO;
}
SQLRETURN SQLColumnsW(SQLHSTMT h, SQLWCHAR *a, SQLSMALLINT al, SQLWCHAR *b, SQLSMALLINT bl,
    SQLWCHAR *c, SQLSMALLINT cl, SQLWCHAR *d, SQLSMALLINT dl)
{
    SQLWCHAR *v[] = {a,b,c,d}; SQLSMALLINT n[] = {al,bl,cl,dl}; return capture(h,v,n,4);
}
SQLRETURN SQLTablesW(SQLHSTMT h, SQLWCHAR *a, SQLSMALLINT al, SQLWCHAR *b, SQLSMALLINT bl,
    SQLWCHAR *c, SQLSMALLINT cl, SQLWCHAR *d, SQLSMALLINT dl)
{
    SQLWCHAR *v[] = {a,b,c,d}; SQLSMALLINT n[] = {al,bl,cl,dl}; return capture(h,v,n,4);
}
SQLRETURN SQLForeignKeysW(SQLHSTMT h, SQLWCHAR *a, SQLSMALLINT al, SQLWCHAR *b, SQLSMALLINT bl,
    SQLWCHAR *c, SQLSMALLINT cl, SQLWCHAR *d, SQLSMALLINT dl, SQLWCHAR *e, SQLSMALLINT el,
    SQLWCHAR *f, SQLSMALLINT fl)
{
    SQLWCHAR *v[] = {a,b,c,d,e,f}; SQLSMALLINT n[] = {al,bl,cl,dl,el,fl}; return capture(h,v,n,6);
}
SQLRETURN SQLGetInfoW(SQLHDBC h, SQLUSMALLINT type, SQLPOINTER value,
                     SQLSMALLINT capacity, SQLSMALLINT *length)
{
    static const SQLWCHAR text[] = {'P','G',0xd83d,0xde80,0x00f8,0};
    SQLWCHAR *wide = (SQLWCHAR *)value;
    assert(h == manager);
    ++backend_calls;
    if (type == SQL_TXN_CAPABLE) {
        assert(value == numeric_pointer && length == numeric_length && capacity == 4);
        *(SQLUINTEGER *)value = 42;
        *length = 2;
        return SQL_SUCCESS_WITH_INFO;
    }
    assert(type == SQL_DRIVER_NAME || type == SQL_DRIVER_VER || type == SQL_DRIVER_ODBC_VER);
    assert(capacity >= (SQLSMALLINT)sizeof(text) && capacity % 2 == 0);
    memcpy(value, text, sizeof(text));
    *length = 10;
    if (metadata_mode == 1) *length = 3;
    if (metadata_mode == 2) *length = capacity;
    if (metadata_mode == 3) wide[5] = 'x';
    if (metadata_mode == 4) { wide[0] = 0xd800; wide[1] = 0; *length = 2; }
    if (metadata_mode == 5) { wide[0] = 0xdc00; wide[1] = 0; *length = 2; }
    if (metadata_mode == 6) return SQL_ERROR;
    return SQL_SUCCESS;
}

int main(void)
{
    SQLCHAR schema[] = {'d',0xc3,0xb8};
    SQLCHAR rocket[] = {0xf0,0x9f,0x9a,0x80,0};
    SQLCHAR embedded[] = {'a',0,'b'};
    const char *bad[] = {"\xc0\x80", "\xed\xa0\x80", "\xf4\x90\x80\x80", "\x80", "\xe2\x82"};
    char output[16], expected[] = "PG\xf0\x9f\x9a\x80\xc3\xb8";
    char *oversized;
    SQLSMALLINT length;
    SQLUINTEGER number = 0;
    unsigned i, before;
    assert(cohWineColumns(manager,NULL,0,schema,3,rocket,4,NULL,SQL_NTS) == SQL_SUCCESS_WITH_INFO);
    assert(nulls[0] && lengths[0] == 0 && nulls[3] && lengths[3] == SQL_NTS);
    assert(lengths[1] == 2 && filters[1][0] == 'd' && filters[1][1] == 0xf8);
    assert(lengths[2] == 2 && filters[2][0] == 0xd83d && filters[2][1] == 0xde80);
    assert(cohWineColumns(manager,(SQLCHAR *)"",0,embedded,3,rocket,SQL_NTS,NULL,0) == SQL_SUCCESS_WITH_INFO);
    assert(!nulls[0] && lengths[0] == 0 && filters[0][0] == 0);
    assert(lengths[1] == 3 && filters[1][0] == 'a' && filters[1][1] == 0 && filters[1][2] == 'b');
    assert(lengths[2] == SQL_NTS && filters[2][1] == 0xde80);
    before = backend_calls;
    for (i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i)
        assert(cohWineColumns(manager,NULL,0,(SQLCHAR *)bad[i],SQL_NTS,NULL,0,NULL,0) == SQL_ERROR);
    assert(cohWineColumns(manager,NULL,0,schema,-2,NULL,0,NULL,0) == SQL_ERROR);
    oversized = (char *)malloc(32769); assert(oversized); memset(oversized,'a',32768); oversized[32768] = 0;
    assert(cohWineColumns(manager,NULL,0,(SQLCHAR *)oversized,SQL_NTS,NULL,0,NULL,0) == SQL_ERROR);
    free(oversized);
    assert(backend_calls == before);
    assert(cohWineTables(manager,NULL,0,schema,3,NULL,0,(SQLCHAR *)"TABLE",SQL_NTS) == SQL_SUCCESS_WITH_INFO);
    assert(nulls[0] && nulls[2] && lengths[1] == 2 && filters[3][0] == 'T');
    assert(cohWineForeignKeys(manager,NULL,0,schema,3,rocket,4,NULL,0,NULL,0,NULL,0) == SQL_SUCCESS_WITH_INFO);
    assert(nulls[0] && nulls[3] && nulls[4] && nulls[5] && lengths[2] == 2);
    assert(cohWineGetInfo(manager,SQL_DRIVER_NAME,output,sizeof(output),&length) == SQL_SUCCESS);
    assert(length == 8 && !strcmp(output,expected));
    assert(cohWineGetInfo(manager,SQL_DRIVER_VER,output,5,&length) == SQL_SUCCESS_WITH_INFO);
    assert(length == 8 && !strcmp(output,"PG"));
    assert(cohWineGetInfo(manager,SQL_DRIVER_ODBC_VER,output,7,&length) == SQL_SUCCESS_WITH_INFO);
    assert(length == 8 && strlen(output) == 6 && !memcmp(output,expected,6));
    assert(cohWineGetInfo(manager,SQL_DRIVER_NAME,NULL,99,&length) == SQL_SUCCESS && length == 8);
    output[0] = 'x';
    assert(cohWineGetInfo(manager,SQL_DRIVER_NAME,output,0,&length) == SQL_SUCCESS_WITH_INFO);
    assert(output[0] == 'x' && length == 8);
    numeric_pointer = &number; numeric_length = &length;
    assert(cohWineGetInfo(manager,SQL_TXN_CAPABLE,&number,4,&length) == SQL_SUCCESS_WITH_INFO);
    assert(number == 42 && length == 2);
    for (metadata_mode = 1; metadata_mode <= 6; ++metadata_mode) {
        memset(output,'x',sizeof(output));
        assert(cohWineGetInfo(manager,SQL_DRIVER_NAME,output,sizeof(output),&length) == SQL_ERROR);
        assert(output[0] == 0 && output[1] == 'x');
    }
    puts("PASS Wine DbServer adapter: handles, NULLs, UTF-8/UTF-16 bounds, metadata and numeric lengths");
    return 0;
}
