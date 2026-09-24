/* Opt-in diagnostic entry inside the actual DbServer executable. No mocks of
 * sql_fifo, sqltask, container_merge, container_sql, or container_tplt are used.
 * Only controlled templates/records replace asset-generated game templates. */
#include <utilitieslib/stdtypes.h>
#include <utilitieslib/utils/utils.h>
#include <utilitieslib/utils/error.h>
#include <utilitieslib/utils/SuperAssert.h>
#include <utilitieslib/components/EString.h>
#include "sql/sqlinclude.h"
#include "container.h"
#include "container_tplt.h"
#include "container_merge.h"
#include "sql_fifo.h"
#include "dbserver/servercfg.h"
#include "comm_backend.h"
#include "namecache.h"
#include <process.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"PG_TEST_FAILED line=%d: %s\n",__LINE__,#x); fflush(stderr); _exit(2); } } while (0)
static void failNow(char *message) { fprintf(stderr,"PG_TEST_FATAL: %s\n",message); fflush(stderr); _exit(2); }
static void errorNow(char *message) { fprintf(stderr,"PG_TEST_DIAGNOSTIC: %s\n",message); }
static int scalar(char *sql) { return sqlGetSingleValue(sql, SQL_NTS, NULL, SQLCONN_FOREGROUND); }
static void execute(char *sql) { CHECK(SQL_SUCCEEDED(sqlConnExecDirectMany(sql,SQL_NTS,SQLCONN_FOREGROUND,true))); }
static void drain(void) { sqlFifoBarrier(); sqlFifoFinish(); }

static void field(ColumnInfo *f, const char *name, const char *type, bool reserved)
{
    char mutable_type[80];
    char *native;
    strcpy(f->name,name);
    strcpy(mutable_type,type);
    f->data_type=dataType(mutable_type,&f->column_size,&f->num_bytes,&native);
    strcpy(f->data_type_name,native);
    f->reserved_word=reserved;
}
static ContainerTemplate *fixture(bool rebuilt)
{
    ContainerTemplate *t=calloc(1,sizeof(*t));
    TableInfo *a,*b;
    t->dblist_id=CONTAINER_TESTDATABASETYPES;
    t->table_count=2;
    t->tables=calloc(2,sizeof(*t->tables));
    a=&t->tables[0]; b=&t->tables[1];
    strcpy(a->name,"PgFifo"); a->table_type=TT_CONTAINER;
    a->num_columns=rebuilt?7:6; a->columns=calloc(a->num_columns,sizeof(ColumnInfo));
    field(&a->columns[0],"ContainerId","int4",true);
    field(&a->columns[1],"Active","int4",true);
    field(&a->columns[rebuilt?3:2],"Name","unicodestring[64]",false);
    a->columns[rebuilt?3:2].indexed=1;
    field(&a->columns[rebuilt?2:3],"Score","int4",false);
    field(&a->columns[4],"Flag","int1",false);
    if(rebuilt) field(&a->columns[5],"Rating","int4",false);
    field(&a->columns[rebuilt?6:5],"Notes","unicodestring(max)",false);
    strcpy(b->name,"PgFifoItems"); b->table_type=TT_SUBCONTAINER; b->array_count=512;
    b->num_columns=4; b->columns=calloc(4,sizeof(ColumnInfo));
    field(&b->columns[0],"ContainerId","int4",true);
    field(&b->columns[1],"SubId","int4",true); b->columns[1].is_sub_id_field=1;
    field(&b->columns[2],"ItemValue","int4",false);
    field(&b->columns[3],"Label","unicodestring[32]",false);
    hashAllNames(t,"PostgreSQL controlled fixture");
    return t;
}
static void writeRecord(ContainerTemplate *t,int id,int score,int last,bool create,int rows)
{
    char *text=NULL;
    LineList lines={0};
    int i;
    estrPrintf(&text,"Name \"AlphaHero\"\nScore %d\nFlag 255\nNotes \"caf\xc3\xa9 \xf0\x9f\x98\x80",score);
    for(i=0;i<8192;++i) estrConcatCharString(&text,"X");
    estrConcatCharString(&text,"\"\n");
    for(i=0;i<rows;++i)
        estrConcatf(&text,"PgFifoItems[%d].ItemValue %d\nPgFifoItems[%d].Label \"slot%d\"\n",i,i==511?last:i+1,i,i);
    CHECK(textToLineList(t,text,&lines,NULL));
    if(create) sqlContainerUpdateFromScratchAsync(t,id,&lines,false);
    else sqlContainerUpdateAsync(t,id,&lines);
    CHECK(sqlIsAsyncWritePending(t->dblist_id,id));
    freeLineList(&lines); estrDestroy(&text);
}
static void verifyRecord(ContainerTemplate *t)
{
    char *mem,*text;
    char notes[9000],expected[9000];
    LineList lines={0};
    CHECK(scalar("SELECT Score FROM dbo.PgFifo WHERE ContainerId=101;")==555);
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=101;")==512);
    CHECK(scalar("SELECT ItemValue FROM dbo.PgFifoItems WHERE ContainerId=101 AND SubId=511;")==8888);
    CHECK(scalar("SELECT Flag FROM dbo.PgFifo WHERE ContainerId=101;")==255);
    mem=sqlContainerRead(t,101,SQLCONN_FOREGROUND); CHECK(mem);
    memToLineList(mem,&lines); text=lineListToText(t,&lines,0);
    CHECK(strstr(text,"AlphaHero")); CHECK(strstr(text,"caf\xc3\xa9"));
    CHECK(strstr(text,"\xf0\x9f\x98\x80")); CHECK(strstr(text,"PgFifoItems[511]"));
    CHECK(scalar("SELECT octet_length(Notes) FROM dbo.PgFifo WHERE ContainerId=101;")==8202);
    strcpy(expected,"caf\xc3\xa9 \xf0\x9f\x98\x80");
    memset(expected+10,'X',8192); expected[8202]=0;
    CHECK(findFieldText(text,"Notes",notes)); CHECK(!strcmp(notes,expected));
    free(mem); freeLineList(&lines);
}
static int callback_count;
static void readCallback(Packet *p,U8 *data,int count,ColumnInfo **fields,void *user)
{
    CHECK(!p && count==1 && data && fields[0]);
    CHECK(*(int*)data==*(int*)user); ++callback_count;
}
static void tests(ContainerTemplate *t)
{
    int i,expected=20;
    DbList list={0}; list.tplt=t;
    tpltUpdateSqlcolumns(t); drain();
    sqlAddForeignKeyConstraintAsync("PgFifoItems","ContainerId","PgFifo"); drain();
    writeRecord(t,101,10,512,true,512);
    sqlFifoTickWhileWritePending(t->dblist_id,101);
    CHECK(!sqlIsAsyncWritePending(t->dblist_id,101));
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=101;")==512);
    writeRecord(t,101,20,512,false,0);
    sqlReadColumnsAsync(&t->tables[0],NULL,"Score","WHERE ContainerId=101",readCallback,&expected,NULL,101);
    drain(); CHECK(callback_count==1);
    // Exercise independent worker queues and repeated saves in one queue.
    for(i=200;i<216;++i) writeRecord(t,i,i,1,true,1);
    for(i=21;i<=30;++i) writeRecord(t,101,i,512,false,0);
    drain();
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifo WHERE ContainerId BETWEEN 200 AND 215;")==16);
    CHECK(scalar("SELECT Score FROM dbo.PgFifo WHERE ContainerId=101;")==30);
    CHECK(containerIdFindByElement(&list,"Name","aLpHaHeRo")>0);
    pnameInit(); pnameAdd("AlphaHero",101); CHECK(pnameFindByName("aLpHaHeRo")==101);
    CHECK(scalar("SELECT CASE WHEN dbo.coh_name_key('AlphaHero')=dbo.coh_name_key('aLpHaHeRo') AND dbo.coh_name_key('AlphaHero ')<>dbo.coh_name_key('AlphaHero') AND dbo.coh_name_key('cafe')<>dbo.coh_name_key('caf\xc3\xa9') THEN 1 ELSE 0 END;")==1);
    CHECK(scalar("SELECT CASE WHEN LOCALTIMESTAMP - INTERVAL '2 days' > LOCALTIMESTAMP - (7 * INTERVAL '1 day') THEN 1 ELSE 0 END;")==1);
    // A late child-row update runs after at least one FLUSH_BINDS boundary.
    // Sequence increments survive rollback and prove the injected failure ran.
    execute("CREATE SEQUENCE coh_meta.fifo_serial_fail; CREATE SEQUENCE coh_meta.fifo_deadlock_fail; CREATE SEQUENCE coh_meta.fifo_commit_fail;"
        "CREATE FUNCTION coh_meta.fifo_fault() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN "
        "IF NEW.SubId=511 AND NEW.ItemValue=7777 AND nextval('coh_meta.fifo_serial_fail')=1 THEN RAISE EXCEPTION 'injected serialization' USING ERRCODE='40001'; END IF;"
        "IF NEW.SubId=511 AND NEW.ItemValue=8888 AND nextval('coh_meta.fifo_deadlock_fail')=1 THEN RAISE EXCEPTION 'injected deadlock' USING ERRCODE='40P01'; END IF; RETURN NEW; END$$;"
        "CREATE TRIGGER fifo_fault BEFORE UPDATE ON dbo.PgFifoItems FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_fault();"
        "CREATE FUNCTION coh_meta.fifo_commit_fault() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN "
        "IF NEW.Score=555 AND nextval('coh_meta.fifo_commit_fail')=1 THEN RAISE EXCEPTION 'injected commit failure' USING ERRCODE='40001'; END IF; RETURN NEW; END$$;"
        "CREATE CONSTRAINT TRIGGER fifo_commit_fault AFTER UPDATE ON dbo.PgFifo DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION coh_meta.fifo_commit_fault();");
    writeRecord(t,102,42,7777,true,512); drain();
    CHECK(sqlFifoRetryCount()==1);
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=102;")==512);
    CHECK(scalar("SELECT last_value::integer FROM coh_meta.fifo_serial_fail;")==2);
    writeRecord(t,101,44,8888,false,512); drain(); CHECK(sqlFifoRetryCount()==2);
    writeRecord(t,101,555,8888,false,0); drain(); CHECK(sqlFifoRetryCount()==3);
    CHECK(scalar("SELECT last_value::integer FROM coh_meta.fifo_commit_fail;")==2);
    verifyRecord(t);
    execute("DROP TRIGGER fifo_fault ON dbo.PgFifoItems; DROP TRIGGER fifo_commit_fault ON dbo.PgFifo;");
    sqlDeleteContainer(t,102); drain();
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifo WHERE ContainerId=102;")==0);
    CHECK(scalar("SELECT count(*) FROM dbo.PgFifoItems WHERE ContainerId=102;")==0);
    CHECK(scalar("SELECT dbo.coh_reserve_id('dbo.PgFifo',9000);")==9000);
    printf("PG_TEST_PASS real queue: multi-batch create/update/read/delete, ordering, 16 writers, SQLSTATE 40001/40P01 and commit retry, UTF-8, case lookup\n");
}
int pgPersistenceTestMain(int argc,char **argv)
{
    char login[SHORT_SQL_STRING];
    FILE *f;
    ContainerTemplate *t;
    bool rebuilt;
    const char *mode;
    int i;
    CHECK(argc==5);
    setAssertMode(ASSERTMODE_STDERR|ASSERTMODE_EXIT);
    FatalErrorfSetCallback(failNow); ErrorfSetCallback(errorNow);
    CHECK(!strncmp(argv[3],"coh_test_",9));
    for(i=0;argv[3][i];++i) CHECK((argv[3][i]>='a'&&argv[3][i]<='z') || (argv[3][i]>='0'&&argv[3][i]<='9') || argv[3][i]=='_');
    CHECK(!fopen_s(&f,argv[2],"rb")); CHECK(f); CHECK(fgets(login,sizeof(login),f)); fclose(f);
    login[strcspn(login,"\r\n")]=0;
    gDatabaseProvider=DBPROV_POSTGRESQL;
    CHECK(sqlConnInit(SQLCONN_MAX)); sqlConnSetLogin(login);
    CHECK(sqlConnDatabaseConnect(argv[3],"COH_PG_PERSISTENCE_TEST"));
    CHECK(scalar("SELECT CASE WHEN current_database() LIKE 'coh_test\\_%' ESCAPE '\\' AND NOT (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) AND EXISTS (SELECT 1 FROM coh_meta.persistence_test_guard) THEN 1 ELSE 0 END;")==1);
    odbcInitialSetup(); queryDatabaseVersion(); server_cfg.sql_allow_all_ddl=1;
    mode=argv[4]; rebuilt=!strcmp(mode,"verify-rebuilt"); t=fixture(rebuilt);
    sqlFifoInit();
    if(!strcmp(mode,"initial")) tests(t);
    else if(!strcmp(mode,"verify") || rebuilt) {
        verifyRecord(t); CHECK(scalar("SELECT dbo.coh_container_high_water('dbo.PgFifo');")==9000);
        printf("PG_TEST_PASS reload through real container reader\n");
    } else if(!strcmp(mode,"fail") || !strcmp(mode,"exhaust")) {
        writeRecord(t,103,90,9999,true,512); drain();
        CHECK(!"Failed save must terminate without completion");
    } else if(!strcmp(mode,"disconnect")) {
        sqlExecAsyncEx("UPDATE dbo.PgFifo SET Score=666 WHERE ContainerId=101; SELECT pg_terminate_backend(pg_backend_pid());",SQL_NTS,101,false);
        drain(); CHECK(!"Lost connection must not acknowledge the write");
    } else if(!strcmp(mode,"delete-fail")) {
        sqlDeleteContainer(t,101); drain(); CHECK(!"Failed delete must terminate");
    } else if(!strcmp(mode,"rebuild-fail") || !strcmp(mode,"rebuild-fail-view")) {
        t=fixture(strcmp(mode,"rebuild-fail-view")!=0);
        if(!strcmp(mode,"rebuild-fail")) field(&t->tables[0].columns[3],"Name","unicodestring[1]",false);
        tpltUpdateSqlcolumns(t); drain(); CHECK(!"Invalid rebuild must fail");
    } else if(!strcmp(mode,"rebuild")) {
        t=fixture(true); tpltUpdateSqlcolumns(t); drain(); verifyRecord(t);
        CHECK(scalar("SELECT dbo.coh_container_high_water('dbo.PgFifo');")==9000);
        CHECK(scalar("SELECT count(*) FROM pg_constraint WHERE conrelid='dbo.PgFifoItems'::regclass AND contype='f';")==1);
        printf("PG_TEST_PASS real schema rebuild preserves rows, high-water and foreign key\n");
    } else CHECK(!"Unknown mode");
    sqlFifoShutdown(); sqlConnShutdown();
    printf("PG_TEST_COMPLETE %s\n",mode); fflush(stdout); return 0;
}
