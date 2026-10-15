"""Compile the production row merger/emitter for the observed zeroed-window save."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REQUIRE_POSTGRESQL = os.environ.get('COH_REQUIRE_STARTUP_BUNDLE_PG') == '1'
POSTGRES_FIXTURES_RUN = set()
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(Path(__file__).parent)]
import package_startup_dbserver as retained

PATCH = 'patches/startup-bundle/0001-pg-cancelled-child-insert.patch'


def function(text, signature):
    """Keep the complete authored function; no translated implementation."""
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    offset = opening + 1
    # These selected functions have no brace-containing string literals.
    while depth:
        depth += (text[offset] == '{') - (text[offset] == '}')
        offset += 1
    return text[start:offset] + '\n'


def source(directory, patched=True):
    names = {'DBServer/src/container_sql.c', 'DBServer/src/container_merge.c',
             'DBServer/src/container.h'}
    pg = retained.wine.expected_wine_receipt()['postgresql_build_input']
    names.update(pg['patched_sha256'])
    for name in names:
        target = directory/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/'upstream/ouroboros'/name, target)
    retained.wine.apply_patch(directory, (ROOT/'patches/postgresql/0001-dbserver-postgresql.patch')
                              .read_bytes().replace(b'\r\n', b'\n'))
    if patched:
        retained.wine.apply_patch(directory, (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n'))
    return directory/'DBServer/src/container_sql.c'


HEADER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
typedef unsigned U32;
typedef float F32;
#ifndef _MSC_VER
#define __FUNCTION__ "production-emitter"
#endif
#define FAKE_STR_IDX -1
#define TT_CONTAINER 1
#define TT_SUBCONTAINER 2
#define DBPROV_MSSQL 1
#define DBPROV_POSTGRESQL 2
#define CFTYPE_INT 1
#define LONG_SQL_STRING 1000000
#ifndef FLUSH_BINDS
#define FLUSH_BINDS 1000
#endif
#define xcase break; case
#define xdefault break; default
#define DBPROV_XDEFAULT() xdefault: abort()
typedef int HSTMT;
typedef int SqlConn;
static int gDatabaseProvider;
typedef struct AttributeList { void *hash_table; } AttributeList;
typedef struct ColumnInfo { AttributeList *attr; } ColumnInfo;
typedef struct TableInfo { char *name; int table_type; ColumnInfo *columns; } TableInfo;
typedef struct SlotInfo { TableInfo *table; int sub_id,idx; } SlotInfo;
typedef struct ContainerTemplate { SlotInfo *slots; } ContainerTemplate;
static void *dynArrayAdd(void *address, int bytes, int *count, int *capacity, int amount) {
    void **array = (void **)address; void *result;
    if (*count + amount > *capacity) {
        *capacity = (*count + amount) * 2;
        *array = realloc(*array, (size_t)*capacity * (size_t)bytes);
        if (!*array) abort();
    }
    result = (char*)*array + (size_t)*count * (size_t)bytes; *count += amount; return result;
}
static int stashFindInt(void *table, const char *name, int *out) { (void)table; (void)name; *out=0; return 0; }
static int valueNotNull(char *text) { return text && *text; }
static int bound[2000]; static unsigned bound_count;
static void bindInputParameter(HSTMT stmt, unsigned index, int type, int *value, void *length) {
    (void)stmt; (void)type; (void)length; if (!value || index>=2000) abort(); bound[index]=*value; bound_count=index+1;
}
static void FatalErrorf(const char *format, ...) { (void)format; abort(); }
static void estrConcatf(char **target, const char *format, ...) {
    char output[4096]; size_t old=*target?strlen(*target):0; int length; va_list args;
    va_start(args,format); length=vsnprintf(output,sizeof(output),format,args); va_end(args);
    if(length<0 || length>=(int)sizeof(output)) abort();
    *target=realloc(*target,old+(size_t)length+1); if(!*target)abort(); memcpy(*target+old,output,(size_t)length+1);
}
static unsigned estrLength(char **target) { return *target ? (unsigned)strlen(*target) : 0; }
static void estrClear(char **target) { if(*target)**target=0; }
static void sqlConnStmtExecDirectMany(HSTMT stmt,char *sql,unsigned length,SqlConn conn,bool flag) {
    unsigned i; (void)stmt; (void)length; (void)conn; (void)flag;
    printf("%s\t",sql);
    for(i=0;i<bound_count;++i)printf("%s%d",i?",":"",bound[i]);
    puts("");
}
static void sqlConnStmtUnbindCols(HSTMT stmt) { (void)stmt; }
static void sqlConnStmtUnbindParams(HSTMT stmt) { (void)stmt; bound_count=0; }
static void sqlConnStmtCloseCursor(HSTMT stmt) { (void)stmt; }
'''
MAIN = r'''
int main(int argc,char **argv) {
    ColumnInfo cols[2]={{0},{0}};
    TableInfo windows={"Windows",TT_SUBCONTAINER,cols}, other={"OtherWindows",TT_SUBCONTAINER,cols}, ents={"Ents",TT_CONTAINER,cols};
    SlotInfo slots[]={{&windows,17,0},{&windows,17,1},{&windows,18,0},{&other,17,0},{&ents,0,0}};
    ContainerTemplate t={slots}; LineList diff={0},orig={0},curr={0};
    RowAddDel commands[8]; LineTracker line; char *sql=NULL; unsigned bind=0;
    if(argc!=3)return 2;
    gDatabaseProvider=atoi(argv[2]);
    memset(commands,0,sizeof(commands)); memset(&line,0,sizeof(line));
    diff.row_cmds=commands; diff.cmd_max=8;
    if(!strcmp(argv[1],"generated-null")) {
        diff.row_cmds=NULL;diff.cmd_max=0;line.idx=0;diff.lines=&line;diff.count=1;
        mergeLineLists(&t,&orig,&diff,&curr);
        if(diff.cmd_count!=2 || !diff.row_cmds[0].add || diff.row_cmds[1].add || curr.count) return 3;
    } else if(!strcmp(argv[1],"cancelled")) {
        commands[0].idx=0;commands[0].add=1;commands[1].idx=1;diff.cmd_count=2;
    } else if(!strcmp(argv[1],"replacement")) {
        commands[0].idx=0;commands[1].idx=1;commands[1].add=1;diff.cmd_count=2;
    } else if(!strcmp(argv[1],"unrelated-row")) {
        commands[0].idx=0;commands[0].add=1;commands[1].idx=2;diff.cmd_count=2;
    } else if(!strcmp(argv[1],"unrelated-table")) {
        commands[0].idx=0;commands[0].add=1;commands[1].idx=3;diff.cmd_count=2;
    } else if(!strcmp(argv[1],"interleaved")) {
        commands[0].idx=0;commands[0].add=1;commands[1].idx=2;commands[1].add=1;commands[2].idx=1;diff.cmd_count=3;
    } else if(!strcmp(argv[1],"cancelled-replacement")) {
        commands[0].idx=0;commands[0].add=1;commands[1].idx=1;commands[2].idx=0;commands[2].add=1;diff.cmd_count=3;
    } else if(!strcmp(argv[1],"container")) {
        commands[0].idx=4;commands[0].add=1;commands[1].idx=4;diff.cmd_count=2;
    } else if(!strcmp(argv[1],"add-only")) {
        commands[0].idx=0;commands[0].add=1;diff.cmd_count=1;
    } else return 4;
    { int container=1; sqlContainerAddOrDelRows(&t,&container,&diff,&sql,&bind,0,0); }
    if(estrLength(&sql))sqlFlushStatement(0,&sql,&bind,0);
    free(sql); if(diff.row_cmds!=commands)free(diff.row_cmds); free(curr.lines);free(curr.text);free(curr.row_cmds);return 0;
}
'''


class CancelledChildSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if not compiler: raise RuntimeError('Production row-command regression requires a C compiler')
        cls.temporary=tempfile.TemporaryDirectory(prefix='coh-window-save-')
        cls.directory=Path(cls.temporary.name); cls.executables={}
        if REQUIRE_POSTGRESQL:
            if os.environ.get('PGHOST') not in ('127.0.0.1','localhost'):
                raise RuntimeError('PostgreSQL regression requires an explicit localhost fixture')
            if os.environ.get('PGDATABASE') != 'coh_test_startup_bundle':
                raise RuntimeError('PostgreSQL regression requires coh_test_startup_bundle')
            cls.psql=shutil.which('psql')
            if not cls.psql:raise RuntimeError('Required real PostgreSQL regression needs psql')
            guard=subprocess.run([cls.psql,'-X','-qAt','-c','SELECT current_database();'],capture_output=True,text=True,timeout=20)
            if guard.returncode or guard.stdout.strip()!='coh_test_startup_bundle':
                raise RuntimeError('Cannot validate the owned PostgreSQL regression database')
        for patched, flush in ((False,1000),(True,1000),(True,2)):
            folder=cls.directory/('%s-%s'%(patched,flush));folder.mkdir()
            path=source(folder,patched)
            emitter=path.read_text()
            merger=(folder/'DBServer/src/container_merge.c').read_text()
            structs=(folder/'DBServer/src/container.h').read_text().split('typedef struct LineTracker',1)[1].split('#define DBCONTAINER_MEMBERS',1)[0]
            pieces=[HEADER, '#include "pg_compat.h"\n', 'typedef struct LineTracker'+structs,
                function(merger,'static int lineNotNull('),function(merger,'void reinitLineList('),
                function(merger,'void mergeLineLists('),function(emitter,'static void sqlFlushStatement(')]
            if patched:pieces.append(function(emitter,'static bool postgresChildInsertCancelled('))
            pieces.extend((function(emitter,'static void sqlContainerAddOrDelRows('),MAIN))
            harness=folder/'save.c';harness.write_text('\n'.join(pieces))
            binary=folder/('save.exe' if os.name=='nt' else 'save')
            includes=ROOT/'database/postgresql/overlay/Common/sql'
            if os.name=='nt':
                command=[compiler,'/nologo','/W3','/O2','/MT',f'/DFLUSH_BINDS={flush}',f'/I{includes}',str(harness),f'/Fe:{binary}']
            else:
                command=[compiler,'-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-sign-compare',f'-DFLUSH_BINDS={flush}','-I'+str(includes),str(harness),'-o',str(binary)]
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=30)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            cls.executables[patched,flush]=binary

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def commands(self, mode, provider=2, patched=True, flush=1000):
        result=subprocess.run([str(self.executables[patched,flush]),mode,str(provider)],capture_output=True,text=True,timeout=10,check=True)
        self.assertEqual(result.stderr,'')
        rows=[]
        for line in result.stdout.splitlines():
            text,args=line.split('\t'); rows.append((text,[int(value) for value in args.split(',') if value]))
        return rows

    def database(self, existing=True):
        db=sqlite3.connect(':memory:')
        db.execute("ATTACH DATABASE ':memory:' AS dbo")
        db.execute('CREATE TABLE dbo.Windows(ContainerId int,SubId int,xp int,Scale real,PRIMARY KEY(ContainerId,SubId))')
        db.execute('CREATE TABLE dbo.OtherWindows(ContainerId int,SubId int,PRIMARY KEY(ContainerId,SubId))')
        db.execute('CREATE TABLE dbo.Ents(ContainerId int PRIMARY KEY,Score int)')
        db.execute('INSERT INTO dbo.Ents VALUES(1,40)')
        if existing:db.execute('INSERT INTO dbo.Windows VALUES(1,17,500,1)')
        db.commit();self.addCleanup(db.close);return db

    def execute(self, db, batches):
        for statements,args in batches:
            for statement in filter(None,statements.split(';')):
                count=statement.count('?');db.execute(statement,args[:count]);args=args[count:]
            self.assertEqual(args,[])

    def postgres_fixture(self, mode, *, patched=True, replacement=False):
        """Execute the exact emitted statement order with bound integer values.

        Only fixture substitution changes ODBC ? markers to their captured values;
        production SQL and its INSERT/DELETE ordering remain byte-for-byte.
        """
        commands=[]
        for statements,args in self.commands(mode,patched=patched):
            text=statements
            for value in args:text=text.replace('?',str(value),1)
            self.assertNotIn('?',text);commands.append(text)
        ddl="""BEGIN;
CREATE SCHEMA IF NOT EXISTS dbo;
DROP TABLE IF EXISTS dbo.Windows; DROP TABLE IF EXISTS dbo.Ents;
CREATE TABLE dbo.Windows(ContainerId integer,SubId integer,xp integer,Scale real,PRIMARY KEY(ContainerId,SubId));
CREATE TABLE dbo.Ents(ContainerId integer PRIMARY KEY,Score integer);
INSERT INTO dbo.Windows VALUES(1,17,500,1); INSERT INTO dbo.Ents VALUES(1,40);
COMMIT; BEGIN;
"""
        updates=('UPDATE dbo.Windows SET xp=88 WHERE ContainerId=1 AND SubId=17;' if replacement else
                 'UPDATE dbo.Windows SET xp=NULL,Scale=0 WHERE ContainerId=1 AND SubId=17;')
        query=("SELECT COALESCE((SELECT xp::text FROM dbo.Windows WHERE ContainerId=1 AND SubId=17),'missing') || ':' || Score::text FROM dbo.Ents WHERE ContainerId=1;" if replacement else
               "SELECT (SELECT count(*)::text FROM dbo.Windows) || ':' || Score::text FROM dbo.Ents WHERE ContainerId=1;")
        script='\\set VERBOSITY verbose\n'+ddl+''.join(commands)+updates+'UPDATE dbo.Ents SET Score=99 WHERE ContainerId=1;COMMIT;'+query+'DROP TABLE dbo.Windows;DROP TABLE dbo.Ents;'
        result=subprocess.run([self.psql,'-X','-qAt','-v','ON_ERROR_STOP=0'],input=script,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0)
        expected='88:99' if replacement else ('0:99' if patched else '1:40')
        self.assertEqual(result.stdout.strip(),expected)
        if patched:self.assertNotIn('ERROR:',result.stderr)
        else:
            self.assertIn('23505',result.stderr)
            self.assertIn('25P02',result.stderr)
        POSTGRES_FIXTURES_RUN.add('delete_insert_replacement_commits' if replacement else
            ('cancelled_child_deletion_commits' if patched else 'duplicate_insert_23505_rollback'))

    def test_real_merger_reproduces_observed_duplicate_and_whole_save_rollback(self):
        db=self.database()
        with self.assertRaises(sqlite3.IntegrityError):
            with db:self.execute(db,self.commands('generated-null',patched=False));db.execute('UPDATE dbo.Ents SET Score=99 WHERE ContainerId=1')
        self.assertEqual(db.execute('SELECT Score FROM dbo.Ents').fetchone(),(40,))
        self.assertEqual(db.execute('SELECT xp FROM dbo.Windows').fetchone(),(500,))
        if REQUIRE_POSTGRESQL:self.postgres_fixture('generated-null',patched=False)

    def test_real_zeroed_row_merger_deletes_existing_row_and_commits_other_changes(self):
        db=self.database()
        with db:
            self.execute(db,self.commands('generated-null'))
            db.execute('UPDATE dbo.Windows SET xp=NULL,Scale=0 WHERE ContainerId=1 AND SubId=17')
            db.execute('UPDATE dbo.Ents SET Score=99 WHERE ContainerId=1')
        self.assertEqual(db.execute('SELECT count(*) FROM dbo.Windows').fetchone(),(0,))
        self.assertEqual(db.execute('SELECT Score FROM dbo.Ents').fetchone(),(99,))
        if REQUIRE_POSTGRESQL:self.postgres_fixture('generated-null')

    def test_same_row_different_column_slots_match_and_missing_row_stays_missing(self):
        for present in (True,False):
            with self.subTest(present=present):
                db=self.database(present)
                self.execute(db,self.commands('cancelled'))
                self.assertEqual(db.execute('SELECT count(*) FROM dbo.Windows').fetchone(),(0,))

    def test_real_delete_then_insert_replaces_existing_row_and_keeps_order(self):
        db=self.database();batches=self.commands('replacement')
        self.assertTrue(batches[0][0].startswith('DELETE'))
        with db:self.execute(db,batches);db.execute('UPDATE dbo.Windows SET xp=88 WHERE ContainerId=1 AND SubId=17')
        self.assertEqual(db.execute('SELECT xp FROM dbo.Windows').fetchone(),(88,))
        if REQUIRE_POSTGRESQL:self.postgres_fixture('replacement',replacement=True)

    def test_other_rows_and_tables_do_not_cancel_an_insert(self):
        for mode in ('unrelated-row','unrelated-table'):
            with self.subTest(mode=mode):
                batches=self.commands(mode);self.assertTrue(batches[0][0].startswith('INSERT'))
                db=self.database(False);self.execute(db,batches)
                self.assertEqual(db.execute('SELECT count(*) FROM dbo.Windows').fetchone(),(1,))

    def test_interleaved_commands_and_binding_flushes_remain_valid(self):
        for flush in (1000,2):
            with self.subTest(flush=flush):
                db=self.database();self.execute(db,self.commands('interleaved',flush=flush))
                self.assertEqual(db.execute('SELECT SubId FROM dbo.Windows').fetchall(),[(18,)])

    def test_cancelled_pair_followed_by_real_replacement_still_inserts(self):
        db=self.database();self.execute(db,self.commands('cancelled-replacement'))
        self.assertEqual(db.execute('SELECT SubId,xp FROM dbo.Windows').fetchall(),[(17,None)])

    def test_uncancelled_duplicate_still_fails_instead_of_ignoring_conflicts(self):
        db=self.database()
        with self.assertRaises(sqlite3.IntegrityError):self.execute(db,self.commands('add-only'))

    def test_sql_server_provider_and_parent_commands_are_byte_identical(self):
        for mode,provider in (('cancelled',1),('replacement',1),('container',2)):
            with self.subTest(mode=mode,provider=provider):
                self.assertEqual(self.commands(mode,provider),self.commands(mode,provider,False))

    def test_crlf_patch_checkout_produces_the_same_staged_native_source(self):
        raw_reader=Path.read_bytes
        normalized=raw_reader(ROOT/PATCH).replace(b'\r\n',b'\n')
        def checkout_bytes(path):
            return normalized.replace(b'\n',b'\r\n') if path == ROOT/PATCH else raw_reader(path)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);ordinary=root/'ordinary';ordinary.mkdir();crlf=root/'crlf';crlf.mkdir()
            expected=source(ordinary).read_bytes()
            with mock.patch.object(Path,'read_bytes',checkout_bytes):
                actual=source(crlf).read_bytes()
            self.assertEqual(actual,expected)

    def test_only_row_emitter_changes_and_fifo_ack_commit_logic_is_retained(self):
        patch=(ROOT/PATCH).read_text()
        self.assertEqual([line[6:] for line in patch.splitlines() if line.startswith('+++ b/')],['DBServer/src/container_sql.c'])
        self.assertNotIn('ON CONFLICT',patch)
        self.assertNotIn('sqlFifo',patch)
        self.assertNotIn('sendContainerAcks',patch)


if __name__=='__main__':
    for option in ('--require-postgresql','--require-postgres'):
        if option in sys.argv:
            REQUIRE_POSTGRESQL=True;sys.argv.remove(option)
    unittest.main(verbosity=2)
