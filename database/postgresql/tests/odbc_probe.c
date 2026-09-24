/* Actual ODBC calls and the same SQL dialect header used by patched DbServer.
 * Destructive fixture setup is allowed ONLY in a database named coh_test_*.
 * No game assets, Wine, or DbServer binary are needed for this layer's tests.
 */
#ifdef _WIN32
#include <windows.h>
#endif
#include <sql.h>
#include <sqlext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include "pg_compat.h"

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); exit(1); } } while (0)
static SQLHENV env;
static SQLHDBC dbc;
static char login[2048];

static void check(SQLRETURN rc, SQLSMALLINT type, SQLHANDLE handle, int line)
{
    if (!SQL_SUCCEEDED(rc)) {
        SQLCHAR state[6], message[512]; SQLINTEGER native; SQLSMALLINT len, i;
        fprintf(stderr,"ODBC failure line %d, rc %d\n",line,rc);
        for(i=1; SQLGetDiagRec(type,handle,i,state,&native,message,sizeof(message),&len)==SQL_SUCCESS; i++)
            fprintf(stderr,"%s: %s\n",state,message);
        exit(1);
    }
}
#define CHECK(rc,t,h) check(rc,t,h,__LINE__)
static SQLHSTMT statement(void) {
    SQLHSTMT s; CHECK(SQLAllocHandle(SQL_HANDLE_STMT,dbc,&s),SQL_HANDLE_DBC,dbc); return s;
}
static void release(SQLHSTMT s) { CHECK(SQLFreeHandle(SQL_HANDLE_STMT,s),SQL_HANDLE_STMT,s); }
static void drain(SQLHSTMT s) {
    SQLRETURN rc;
    while ((rc=SQLMoreResults(s))!=SQL_NO_DATA) CHECK(rc,SQL_HANDLE_STMT,s);
}
static void exec(const char *sql) {
    SQLHSTMT s=statement(); CHECK(SQLExecDirectA(s,(SQLCHAR *)sql,SQL_NTS),SQL_HANDLE_STMT,s);
    drain(s); release(s);
}
static int scalar(const char *sql) {
    SQLINTEGER result=0; SQLLEN len; SQLHSTMT s=statement();
    CHECK(SQLExecDirectA(s,(SQLCHAR *)sql,SQL_NTS),SQL_HANDLE_STMT,s);
    CHECK(SQLFetch(s),SQL_HANDLE_STMT,s);
    CHECK(SQLGetData(s,1,SQL_C_SLONG,&result,sizeof(result),&len),SQL_HANDLE_STMT,s);
    REQUIRE(len!=SQL_NULL_DATA); drain(s); release(s); return result;
}
static void connect_db(void) {
    CHECK(SQLAllocHandle(SQL_HANDLE_DBC,env,&dbc),SQL_HANDLE_ENV,env);
    CHECK(SQLDriverConnectA(dbc,NULL,(SQLCHAR *)login,SQL_NTS,NULL,0,NULL,SQL_DRIVER_NOPROMPT),SQL_HANDLE_DBC,dbc);
    REQUIRE(scalar("SELECT (current_database() LIKE 'coh\\_test\\_%' ESCAPE '\\')::int;")==1);
    REQUIRE(scalar("SELECT (NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) ::int FROM pg_roles WHERE rolname=current_user;")==1);
}
static void disconnect_db(void) {
    CHECK(SQLDisconnect(dbc),SQL_HANDLE_DBC,dbc);
    CHECK(SQLFreeHandle(SQL_HANDLE_DBC,dbc),SQL_HANDLE_DBC,dbc);
}
static void reserve_insert(int id) {
    char query[1024]; SQLINTEGER value=id; SQLHSTMT s=statement();
    snprintf(query,sizeof(query),COH_PG_INSERT_CONTAINER,"PgProbe","PgProbe");
    CHECK(SQLBindParameter(s,1,SQL_PARAM_INPUT,SQL_C_LONG,SQL_INTEGER,0,0,&value,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,2,SQL_PARAM_INPUT,SQL_C_LONG,SQL_INTEGER,0,0,&value,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLExecDirectA(s,(SQLCHAR *)query,SQL_NTS),SQL_HANDLE_STMT,s);
    drain(s); release(s);
}
static int high_water(void) {
    char query[1024]; snprintf(query,sizeof(query),COH_PG_HIGH_WATER,"PgProbe"); return scalar(query);
}
static void indexes(void) {
    char query[1024];
    exec("CREATE TABLE dbo.PgOther (ContainerId SERIAL PRIMARY KEY, Name varchar(64));");
    /* A decoy schema must neither suppress creation nor be changed by removal. */
    exec("CREATE SCHEMA decoy; CREATE TABLE decoy.PgProbe (Name varchar(64)); CREATE INDEX Name_ind ON decoy.PgProbe(Name);");
    exec("SET search_path = pg_catalog;");
    snprintf(query,sizeof(query),COH_PG_ADD_INDEX,"PgProbe","Name_ind","PgProbe","Name"); exec(query); exec(query);
    snprintf(query,sizeof(query),COH_PG_ADD_INDEX,"PgOther","Name_ind","PgOther","Name"); exec(query);
    REQUIRE(scalar("SELECT count(*) FROM pg_indexes WHERE schemaname='dbo' AND indexname ~ '^coh_[0-9a-f]{32}$';")==2);
    snprintf(query,sizeof(query),COH_PG_DROP_INDEX,"PgProbe","PgProbe","Name_ind","Name_ind"); exec(query); exec(query);
    REQUIRE(scalar("SELECT count(*) FROM pg_indexes WHERE schemaname='dbo' AND indexname ~ '^coh_[0-9a-f]{32}$';")==1);
    REQUIRE(scalar("SELECT count(*) FROM pg_indexes WHERE schemaname='decoy';")==1);
    /* Old unqualified indexes are removed only on the intended table. */
    exec("CREATE INDEX Name_ind ON dbo.PgOther(Name);"); exec(query);
    REQUIRE(scalar("SELECT count(*) FROM pg_indexes WHERE schemaname='dbo' AND indexname='name_ind';")==1);
    snprintf(query,sizeof(query),COH_PG_DROP_INDEX,"PgOther","PgOther","Name_ind","Name_ind"); exec(query);
    REQUIRE(scalar("SELECT count(*) FROM pg_indexes WHERE schemaname='dbo' AND indexname='name_ind';")==0);
    puts("PASS indexes: duplicate field names, idempotence, schema isolation, legacy cleanup");
}
static void foreign_keys(void) {
    char query[1024]; SQLHSTMT s; SQLRETURN rc; SQLCHAR state[6]; SQLINTEGER native; SQLSMALLINT length;
    exec("CREATE TABLE dbo.PgChild(ContainerId integer, SubId integer, PRIMARY KEY(ContainerId, SubId));");
    snprintf(query,sizeof(query),COH_PG_ADD_FK,"PgChild","PgChild","ContainerId","PgProbe","PgChild","PgChild","ContainerId","PgProbe","ContainerId","PgProbe");
    exec(query); exec(query);
    exec("INSERT INTO dbo.PgChild VALUES(1,0),(1,1);");
    s=statement(); rc=SQLExecDirectA(s,(SQLCHAR *)"INSERT INTO dbo.PgChild VALUES(999,0);",SQL_NTS);
    REQUIRE(rc==SQL_ERROR);
    CHECK(SQLGetDiagRec(SQL_HANDLE_STMT,s,1,state,&native,NULL,0,&length),SQL_HANDLE_STMT,s);
    REQUIRE(!strcmp((char *)state,"23503")); release(s);
    snprintf(query,sizeof(query),COH_PG_DROP_FK,"PgChild","PgChild","ContainerId","PgProbe"); exec(query); exec(query);
    puts("PASS foreign keys: add/remove, child rows, orphan rejection");
}
static void metadata(void) {
    SQLHSTMT s=statement(); SQLRETURN rc; SQLLEN len;
    char name[80],type[80],canonical[80]; SQLINTEGER size; int count=0; CohPgKind kind;
    CHECK(SQLColumnsA(s,NULL,0,(SQLCHAR *)"dbo",SQL_NTS,(SQLCHAR *)"pgprobe",SQL_NTS,NULL,0),SQL_HANDLE_STMT,s);
    while ((rc=SQLFetch(s))!=SQL_NO_DATA) {
        CHECK(rc,SQL_HANDLE_STMT,s);
        CHECK(SQLGetData(s,4,SQL_C_CHAR,name,sizeof(name),&len),SQL_HANDLE_STMT,s);
        CHECK(SQLGetData(s,6,SQL_C_CHAR,type,sizeof(type),&len),SQL_HANDLE_STMT,s);
        CHECK(SQLGetData(s,7,SQL_C_LONG,&size,sizeof(size),&len),SQL_HANDLE_STMT,s);
        kind=cohPgColumnType(type,size,canonical,sizeof(canonical)); REQUIRE(kind!=COH_PG_UNKNOWN);
        if (!strcmp(name,"name")) REQUIRE(kind==COH_PG_STRING && !strcmp(canonical,"varchar(64)"));
        if (!strcmp(name,"bio")) REQUIRE(kind==COH_PG_TEXT && !strcmp(canonical,"text"));
        if (!strcmp(name,"payload")) REQUIRE(kind==COH_PG_BINARY && !strcmp(canonical,"bytea"));
        count++;
    }
    REQUIRE(count==10); release(s);
    puts("PASS SQLColumns: canonical PostgreSQL types, Unicode varchar, text and bytea");
}
static void values(void) {
    SQLHSTMT s; SQLLEN n,wide_bytes,blob_bytes=32768; int i,offset;
    SQLINTEGER value=INT_MAX, out_value, tiny_input=255; SQLSMALLINT small=-32768,out_small;
    SQLCHAR tiny=255,out_tiny; float number=1.25f,out_number;
    SQLWCHAR wide[]={0x41,0xe9,0x65e5,0xd83d,0xde80,0}; SQLWCHAR out_wide[32];
    SQL_TIMESTAMP_STRUCT stamp={2026,9,24,1,2,3,0},out_stamp;
    unsigned char blob[32768],chunk[1024];
    for(i=0;i<(int)sizeof(blob);i++) blob[i]=(unsigned char)i;
    wide_bytes=sizeof(wide)-sizeof(SQLWCHAR);
    s=statement();
    CHECK(SQLBindParameter(s,1,SQL_PARAM_INPUT,SQL_C_LONG,SQL_INTEGER,0,0,&value,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,2,SQL_PARAM_INPUT,SQL_C_SHORT,SQL_SMALLINT,0,0,&small,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,3,SQL_PARAM_INPUT,SQL_C_LONG,SQL_INTEGER,0,0,&tiny_input,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,4,SQL_PARAM_INPUT,SQL_C_FLOAT,SQL_REAL,0,0,&number,0,NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,5,SQL_PARAM_INPUT,SQL_C_WCHAR,SQL_WVARCHAR,0,0,wide,wide_bytes,&wide_bytes),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,6,SQL_PARAM_INPUT,SQL_C_BINARY,SQL_VARBINARY,0,0,blob,blob_bytes,&blob_bytes),SQL_HANDLE_STMT,s);
    CHECK(SQLBindParameter(s,7,SQL_PARAM_INPUT,SQL_C_TYPE_TIMESTAMP,SQL_TYPE_TIMESTAMP,19,0,&stamp,sizeof(stamp),NULL),SQL_HANDLE_STMT,s);
    CHECK(SQLExecDirectA(s,(SQLCHAR *)"UPDATE dbo.PgProbe SET Num=?, Small=?, Tiny=?, Amount=?, Name=?, Payload=?, Stamp=? WHERE ContainerId=1;",SQL_NTS),SQL_HANDLE_STMT,s);
    drain(s); release(s);
    s=statement();
    CHECK(SQLExecDirectA(s,(SQLCHAR *)"SELECT Num,Small,Tiny,Amount,Name,Stamp,Payload FROM dbo.PgProbe WHERE ContainerId=1;",SQL_NTS),SQL_HANDLE_STMT,s);
    CHECK(SQLFetch(s),SQL_HANDLE_STMT,s);
#define GET(col,ctype,pointer,bytes) CHECK(SQLGetData(s,col,ctype,pointer,bytes,&n),SQL_HANDLE_STMT,s)
    GET(1,SQL_C_LONG,&out_value,sizeof(out_value)); REQUIRE(out_value==value);
    GET(2,SQL_C_SHORT,&out_small,sizeof(out_small)); REQUIRE(out_small==small);
    GET(3,SQL_C_TINYINT,&out_tiny,sizeof(out_tiny)); REQUIRE(out_tiny==tiny);
    GET(4,SQL_C_FLOAT,&out_number,sizeof(out_number)); REQUIRE(out_number==number);
    GET(5,SQL_C_WCHAR,out_wide,sizeof(out_wide)); REQUIRE(n==wide_bytes && !memcmp(out_wide,wide,sizeof(wide)));
    GET(6,SQL_C_TYPE_TIMESTAMP,&out_stamp,sizeof(out_stamp)); REQUIRE(!memcmp(&out_stamp,&stamp,sizeof(stamp)));
    for(offset=0;offset<(int)sizeof(blob);offset+=(int)sizeof(chunk)) {
        GET(7,SQL_C_BINARY,chunk,sizeof(chunk)); REQUIRE(!memcmp(chunk,blob+offset,sizeof(chunk)));
    }
    drain(s); release(s);
    exec("UPDATE dbo.PgProbe SET Bio=repeat('Hero ',4000) WHERE ContainerId=1;");
    REQUIRE(scalar("SELECT length(Bio) FROM dbo.PgProbe WHERE ContainerId=1;")==20000);
    exec("UPDATE dbo.PgProbe SET Bio=NULL WHERE ContainerId=1;");
    REQUIRE(scalar("SELECT (Bio IS NULL)::int FROM dbo.PgProbe WHERE ContainerId=1;")==1);
    puts("PASS bound values: integer limits, byte 255, float, UTF-16, timestamp, 32 KiB bytea chunks, long text and NULL");
}
int main(int argc,char **argv) {
    FILE *file; char version[100]; int id;
    REQUIRE(argc>=2); file=fopen(argv[1],"rb"); REQUIRE(file);
    REQUIRE(fgets(login,sizeof(login),file)); REQUIRE(feof(file) || fgetc(file)==EOF); fclose(file);
    login[strcspn(login,"\r\n")]=0;
    CHECK(SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env),SQL_HANDLE_ENV,SQL_NULL_HANDLE);
    CHECK(SQLSetEnvAttr(env,SQL_ATTR_ODBC_VERSION,(SQLPOINTER)SQL_OV_ODBC3,0),SQL_HANDLE_ENV,env);
    connect_db();
    CHECK(SQLGetInfoA(dbc,SQL_DRIVER_VER,version,sizeof(version),NULL),SQL_HANDLE_DBC,dbc);
    printf("psqlODBC %s; pointer bits %d; SQLWCHAR bytes %d\n",version,(int)(sizeof(void*)*8),(int)sizeof(SQLWCHAR));
    if(argc==4 && !strcmp(argv[2],"reserve")) {
        id=atoi(argv[3]); REQUIRE(id>0); reserve_insert(id);
    } else if(argc==3 && !strcmp(argv[2],"verify")) {
        REQUIRE(scalar("SELECT count(*) FROM dbo.PgProbe WHERE ContainerId=1 AND Num=2147483647 AND octet_length(Payload)=32768;")==1);
        REQUIRE(high_water()>=1000); puts("PASS persisted fixture after reconnect/restart/restore");
    } else {
        REQUIRE(argc==2);
        exec("DROP SCHEMA IF EXISTS decoy CASCADE; DROP TABLE IF EXISTS dbo.PgChild; DROP TABLE IF EXISTS dbo.PgOther; DROP TABLE IF EXISTS dbo.PgProbe;");
        exec("CREATE TABLE dbo.PgProbe(ContainerId SERIAL PRIMARY KEY, Active integer, Name varchar(64), Num integer, Small smallint, Tiny smallint, Amount real, Stamp timestamp, Bio text, Payload bytea);");
        REQUIRE(high_water()==0); reserve_insert(1); reserve_insert(100); reserve_insert(2);
        REQUIRE(high_water()==100);
        exec("DELETE FROM dbo.PgProbe WHERE ContainerId=100;"); REQUIRE(high_water()==100);
        CHECK(SQLSetConnectAttr(dbc,SQL_ATTR_AUTOCOMMIT,(SQLPOINTER)SQL_AUTOCOMMIT_OFF,0),SQL_HANDLE_DBC,dbc);
        reserve_insert(1000);
        CHECK(SQLEndTran(SQL_HANDLE_DBC,dbc,SQL_ROLLBACK),SQL_HANDLE_DBC,dbc);
        CHECK(SQLSetConnectAttr(dbc,SQL_ATTR_AUTOCOMMIT,(SQLPOINTER)SQL_AUTOCOMMIT_ON,0),SQL_HANDLE_DBC,dbc);
        REQUIRE(scalar("SELECT count(*) FROM dbo.PgProbe WHERE ContainerId=1000;")==0); REQUIRE(high_water()==1000);
        /* Offline bulk-copy path: startup must also see IDs beyond the sequence. */
        exec("INSERT INTO dbo.PgProbe(ContainerId) VALUES(2000);"); REQUIRE(high_water()==2000);
        exec("DELETE FROM dbo.PgProbe WHERE ContainerId=2000;"); REQUIRE(high_water()==1000);
        puts("PASS ID ordering, deleted highest ID, rollback and bulk-import startup state");
        indexes(); foreign_keys(); values(); metadata();
        exec("ALTER TABLE dbo.PgProbe ALTER COLUMN Name TYPE varchar(96);");
        REQUIRE(scalar("SELECT character_maximum_length FROM information_schema.columns WHERE table_schema='dbo' AND table_name='pgprobe' AND column_name='name';")==96);
        disconnect_db(); connect_db(); REQUIRE(high_water()==1000);
        puts("PASS column migration and connection reopen");
    }
    disconnect_db(); SQLFreeHandle(SQL_HANDLE_ENV,env); return 0;
}
