"""Reproduce default AttribMods reads, native training statements, and atomic saves."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

import package_levelup_ui_repair_dbserver as layer
import test_startup_bundle_save as accepted
from test_startup_bundle_dbserver import staged_bundle, executable

REQUIRE_POSTGRESQL = os.environ.get('COH_REQUIRE_LEVELUP_UI_REPAIR_PG') == '1'
POSTGRES_FIXTURES_RUN = set()
REQUIRED_POSTGRES_FIXTURES = {'empty_child_duplicate_23505_rollback', 'empty_child_training_commit',
    'missing_child_insert_commit', 'shuffled_child_read_training_commit'}
ROOT = layer.ROOT


def source(directory, patched=True):
    path = accepted.source(directory)
    if patched:
        layer.retained.retained.wine.apply_patch(directory, layer.patch_bytes())
    return path


HEADER = accepted.HEADER.replace(
    'typedef struct ColumnInfo { AttributeList *attr; } ColumnInfo;',
    'typedef struct ColumnInfo { AttributeList *attr; int data_type,reserved_word,is_sub_id_field; char *name; } ColumnInfo;').replace(
    'typedef struct TableInfo { char *name; int table_type; ColumnInfo *columns; } TableInfo;',
    'typedef struct TableInfo { char *name; int table_type; ColumnInfo *columns; int array_count,num_columns,all_hash_first_idx; HSTMT sql_select_link[1]; char *sql_select_query[1]; } TableInfo;').replace(
    'typedef struct ContainerTemplate { SlotInfo *slots; } ContainerTemplate;',
    'typedef struct ContainerTemplate { SlotInfo *slots; void *all_hashes; } ContainerTemplate;').replace(
    'int type, int *value, void *length)', 'int type, void *value, void *length)').replace(
    'if (!value || index>=2000) abort(); bound[index]=*value;',
    'if (index>=2000) abort(); bound[index]=value?*(int*)value:0;')

STUBS = r'''
#include <wchar.h>
#include <assert.h>
typedef long SQLLEN;
typedef unsigned char U8;
typedef struct SQL_TIMESTAMP_STRUCT { int year,month,day,hour,minute,second; } SQL_TIMESTAMP_STRUCT;
typedef struct sqlBindTemp { int bytes; wchar_t wdata[1]; } sqlBindTemp;
#define SQL_NULL_DATA -1
#define CFTYPE_SHORT 2
#define CFTYPE_BYTE 3
#define CFTYPE_FLOAT 4
#define CFTYPE_BINARY_MAX 5
#define CFTYPE_UNICODESTRING 6
#define CFTYPE_UNICODESTRING_MAX 7
#define CFTYPE_ANSISTRING 8
#define CFTYPE_ANSISTRING_MAX 9
#define CFTYPE_TEXTBLOB 10
#define CFTYPE_BLOB 11
#define CFTYPE_DATETIME 12
#define MAX_QUERY_RESULTS 100
#define MAX_QUERY_SIZE 100
#define ACTUALLY_STORE_BINARY_AS_BINARY 0
#define assertmsgf(c,fmt,typ) assert(c)
#define eaSize(a) 0
#define eaPush(a,b) ((void)(a),(void)(b))
#define TODO() ((void)0)
#define CP_UTF8 65001
#ifndef _MSC_VER
#define _alloca malloc
#endif
#define estrConcatStaticCharArray(a,b) estrConcatf(a,"%s",b)
static void estrSetLength(char **value,unsigned length) { (*value)[length]=0; }
static int MultiByteToWideChar(int cp,int flags,char *s,int len,wchar_t *w,int cap) { (void)cp;(void)flags;(void)s;(void)len;(void)w;(void)cap;return 0; }
static void binStrToHexStr2(char *s,char *h) { (void)s;(void)h; }
static SQLLEN row_results[1][100];
static char row_data[1][100];
static int field_values[100];
typedef int SQLRETURN;
#define estrPrintf(a,...) (estrClear(a),estrConcatf(a,__VA_ARGS__))
static HSTMT sqlConnStmtAlloc(SqlConn conn) { (void)conn;return 1; }
static SQLRETURN sqlConnStmtPrepare(HSTMT stmt,char *query,unsigned length,SqlConn conn) { (void)stmt;(void)query;(void)length;(void)conn;return 0; }
static void s_bindField(HSTMT stmt,ColumnInfo *field,int col,int *idx,SqlConn conn) { (void)stmt;(void)field;(void)col;(void)idx;(void)conn; }
static void *s_getField(HSTMT stmt,ColumnInfo *field,int col,int *idx,SqlConn conn,char *command) {
 (void)stmt;(void)field;(void)idx;(void)conn;(void)command;return &field_values[col];
}
static int addStrToLine(LineList *list,LineTracker *line,char *s,int len) { (void)list;(void)line;(void)s;(void)len;return 0; }
static int addWStrToLine(LineList *list,LineTracker *line,wchar_t *s,int len) { (void)list;(void)line;(void)s;(void)len;return 0; }
'''

MAIN = r'''
int main(int argc,char **argv) {
 ColumnInfo parentcols[3]={{NULL,CFTYPE_INT,1,0,"ContainerId"},{NULL,CFTYPE_INT,0,0,"XP"},
                         {NULL,CFTYPE_INT,0,0,"Level"}};
 ColumnInfo powercols[3]={{NULL,CFTYPE_INT,1,0,"ContainerId"},{NULL,CFTYPE_INT,0,1,"SubId"},
                        {NULL,CFTYPE_INT,0,0,"PowerID"}};
 ColumnInfo cols[4]={{NULL,CFTYPE_INT,1,0,"ContainerId"},{NULL,CFTYPE_INT,0,1,"SubId"},
                    {NULL,CFTYPE_INT,0,0,"Duration"},{NULL,CFTYPE_INT,0,0,"UiD"}};
 TableInfo tables[3]={{"Ents",TT_CONTAINER,parentcols,0,3,0,{0},{NULL}},{"Powers",TT_SUBCONTAINER,powercols,2,3,3,{0},{NULL}},
                     {"AttribMods",TT_SUBCONTAINER,cols,4,4,9,{0},{NULL}}};
 SlotInfo slots[25]; ContainerTemplate t={slots,NULL};LineList orig={0},diff={0},curr={0};
 LineTracker originals[3],updates[7];int row,col,position;char *query=NULL;unsigned bind=0;int container=1;
 sqlBindTemp **temps=NULL; int first_count;
 if(argc!=3)return 2;gDatabaseProvider=atoi(argv[2]);
 memset(originals,0,sizeof(originals));memset(updates,0,sizeof(updates));
 for(col=0;col<3;col++){
   slots[col].table=&tables[0];slots[col].sub_id=0;slots[col].idx=col;
 }
 for(row=0;row<2;row++)for(col=0;col<3;col++){
   slots[3+row*3+col].table=&tables[1];slots[3+row*3+col].sub_id=row;slots[3+row*3+col].idx=col;
 }
 for(row=0;row<4;row++)for(col=0;col<4;col++){
   slots[9+row*4+col].table=&tables[2];slots[9+row*4+col].sub_id=row;slots[9+row*4+col].idx=col;
 }
 originals[0].idx=1;originals[0].ival=115;originals[1].idx=2;originals[1].ival=1;
 originals[2].idx=5;originals[2].ival=7;
 orig.lines=malloc(sizeof(originals));memcpy(orig.lines,originals,sizeof(originals));orig.count=3;orig.max_lines=3;
 for(col=0;col<4;col++)row_results[0][col]=(col<2)?sizeof(int):SQL_NULL_DATA;
 field_values[0]=1;
 if(!strcmp(argv[1],"parent"))tables[2].table_type=TT_CONTAINER;
 sqlTableSelect(&tables[2],&container,0);
 printf("QUERY\t%s\n",tables[2].sql_select_query[0]);bound_count=0;
 if(!strcmp(argv[1],"initial")){orig.count=0;}
 first_count=orig.count;
 for(position=0;position<2;position++){
  row=(!strcmp(argv[1],"unordered") && !strstr(tables[2].sql_select_query[0],"ORDER BY SubId"))?1-position:position;
  *(int*)&row_data[0][4]=row;field_values[1]=row;
  if(!strcmp(argv[1],"zero")){row_results[0][2]=sizeof(int);field_values[2]=0;}
  if(!strcmp(argv[1],"nonzero") || !strcmp(argv[1],"unordered")){row_results[0][2]=sizeof(int);field_values[2]=23+row;}
  if(!strcmp(argv[1],"absent"))continue;
  readRow(0,&t,&tables[2],&orig,0,0,"SELECT * FROM dbo.AttribMods");
 }
 printf("READ\t%d,%d\n",first_count,orig.count);
 if(!strcmp(argv[1],"initial") || !strcmp(argv[1],"parent"))return 0;
 updates[0].idx=1;updates[0].ival=116;
 updates[1].idx=2;updates[1].ival=2;
 /* Training purchases a previously absent power alongside existing child updates. */
 updates[2].idx=8;updates[2].ival=8;
 updates[3].idx=11;updates[3].ival=12;
 updates[4].idx=12;updates[4].ival=42;
 updates[5].idx=15;updates[5].ival=9;
 updates[6].idx=16;updates[6].ival=43;
 diff.lines=updates;diff.count=7;
 mergeLineLists(&t,&orig,&diff,&curr);
 sqlContainerAddOrDelRows(&t,&container,&diff,&query,&bind,0,0);
 sqlContainerUpdateRows(&t,&container,&diff,&query,&bind,0,0,&temps);
 if(estrLength(&query))sqlFlushStatement(0,&query,&bind,0);
 free(query);free(orig.lines);free(diff.row_cmds);free(curr.lines);free(curr.text);free(curr.row_cmds);return 0;
}
'''


class EmptyChildSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if not compiler: raise RuntimeError('Level-up production regression requires a C compiler')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-levelup-save-')
        cls.directory = Path(cls.temporary.name); cls.executables = {}
        if REQUIRE_POSTGRESQL:
            if os.environ.get('PGHOST') not in ('127.0.0.1', 'localhost') or os.environ.get('PGDATABASE') != 'coh_test_startup_bundle':
                raise RuntimeError('Level-up regression requires explicit localhost/coh_test_startup_bundle fixture')
            cls.psql = shutil.which('psql')
            if not cls.psql: raise RuntimeError('Required level-up PostgreSQL regression needs psql')
            guard = subprocess.run([cls.psql, '-X', '-qAt', '-c', 'SELECT current_database();'],
                capture_output=True, text=True, timeout=20)
            if guard.returncode or guard.stdout.strip() != 'coh_test_startup_bundle':
                raise RuntimeError('Cannot validate owned level-up PostgreSQL regression database')
        for patched, flush in ((False, 1000), (True, 1000), (True, 2)):
            folder = cls.directory/('%s-%s' % (patched, flush)); folder.mkdir()
            path = source(folder, patched); emitter = path.read_text()
            merger = (folder/'DBServer/src/container_merge.c').read_text()
            structs = (folder/'DBServer/src/container.h').read_text().split('typedef struct LineTracker', 1)[1].split('#define DBCONTAINER_MEMBERS', 1)[0]
            pieces = [HEADER, '#include "pg_compat.h"', 'typedef struct LineTracker'+structs, STUBS,
                accepted.function(merger, 'static int lineNotNull('),
                accepted.function(merger, 'void reinitLineList('),
                accepted.function(merger, 'void mergeLineLists('),
                accepted.function(emitter, 'static void sqlFlushStatement('),
                accepted.function(emitter, 'static bool postgresChildInsertCancelled('),
                accepted.function(emitter, 'static void sqlContainerAddOrDelRows('),
                accepted.function(emitter, 'static void sqlContainerUpdateRows('),
                accepted.function(emitter, 'static HSTMT sqlTableSelect('),
                accepted.function(emitter, 'static int readRow('), MAIN]
            harness = folder/'save.c'; harness.write_text('\n'.join(pieces))
            binary = folder/('save.exe' if os.name == 'nt' else 'save')
            if os.name == 'nt':
                command = [compiler, '/nologo', '/W3', '/O2', '/MT', f'/DFLUSH_BINDS={flush}',
                    '/I'+str(ROOT/'database/postgresql/overlay/Common/sql'), str(harness), f'/Fe:{binary}']
            else:
                command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-Wno-sign-compare', '-Wno-missing-braces', '-Wno-missing-field-initializers',
                    '-Wno-misleading-indentation', '-Wno-unused-but-set-variable',
                    f'-DFLUSH_BINDS={flush}', '-I'+str(ROOT/'database/postgresql/overlay/Common/sql'), str(harness), '-o', str(binary)]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=30)
            if result.returncode: raise RuntimeError(result.stdout+result.stderr)
            cls.executables[patched, flush] = binary

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def commands(self, mode='train', *, patched=True, provider=2, flush=1000):
        result = subprocess.run([str(self.executables[patched, flush]), mode, str(provider)],
            capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stderr, '')
        records = result.stdout.splitlines(); tag, self.last_query = records.pop(0).split('\t')
        self.assertEqual(tag, 'QUERY'); tag, counts = records.pop(0).split('\t')
        self.assertEqual(tag, 'READ'); rows = []
        for record in records:
            statements, args = record.split('\t')
            rows.append((statements, [int(value) for value in args.split(',') if value]))
        return tuple(int(value) for value in counts.split(',')), rows

    def database(self, existing=True, filename=':memory:'):
        db = sqlite3.connect(':memory:'); db.execute('ATTACH DATABASE ? AS dbo', (str(filename),))
        db.executescript('CREATE TABLE dbo.Ents(ContainerId int PRIMARY KEY,XP int,Level int);'
            'CREATE TABLE dbo.Powers(ContainerId int,SubId int,PowerID int,PRIMARY KEY(ContainerId,SubId));'
            'CREATE TABLE dbo.AttribMods(ContainerId int,SubId int,Duration int,UiD int,PRIMARY KEY(ContainerId,SubId));'
            'INSERT INTO dbo.Ents VALUES(1,115,1);INSERT INTO dbo.Powers VALUES(1,0,7);')
        if existing:
            db.executemany('INSERT INTO dbo.AttribMods VALUES(?,?,?,?)', [(1, 0, None, None), (1, 1, 0, None)])
        db.commit(); return db

    def execute(self, db, batches):
        for statements, args in batches:
            for statement in filter(None, statements.split(';')):
                count = statement.count('?'); db.execute(statement, args[:count]); args = args[count:]
            self.assertEqual(args, [])

    def postgres_fixture(self, *, patched=True, existing=True):
        mode = 'train' if existing else 'absent'; _, batches = self.commands(mode, patched=patched)
        commands = []
        for statements, args in batches:
            text = statements
            for value in args: text = text.replace('?', str(value), 1)
            self.assertNotIn('?', text); commands.append(text)
        ddl = ('BEGIN;CREATE SCHEMA IF NOT EXISTS dbo;DROP TABLE IF EXISTS dbo.AttribMods;'
            'DROP TABLE IF EXISTS dbo.Powers;DROP TABLE IF EXISTS dbo.Ents;'
            'CREATE TABLE dbo.Ents(ContainerId integer PRIMARY KEY,XP integer,Level integer);'
            'CREATE TABLE dbo.Powers(ContainerId integer,SubId integer,PowerID integer,PRIMARY KEY(ContainerId,SubId));'
            'CREATE TABLE dbo.AttribMods(ContainerId integer,SubId integer,Duration integer,UiD integer,PRIMARY KEY(ContainerId,SubId));'
            'INSERT INTO dbo.Ents VALUES(1,115,1);INSERT INTO dbo.Powers VALUES(1,0,7);')
        if existing: ddl += 'INSERT INTO dbo.AttribMods VALUES(1,0,NULL,NULL),(1,1,0,NULL);'
        script = ('\\set VERBOSITY verbose\n'+ddl+'COMMIT;BEGIN;'+''.join(commands)+'COMMIT;'
            "SELECT XP::text || ':' || Level::text || ':' || (SELECT count(*)::text FROM dbo.AttribMods) || ':' || "
            "COALESCE((SELECT Duration::text FROM dbo.AttribMods WHERE SubId=0),'null') || ':' || "
            "(SELECT PowerID::text FROM dbo.Powers WHERE SubId=0) || ':' || "
            "COALESCE((SELECT PowerID::text FROM dbo.Powers WHERE SubId=1),'none') FROM dbo.Ents;"
            'DROP TABLE dbo.AttribMods;DROP TABLE dbo.Powers;DROP TABLE dbo.Ents;')
        result = subprocess.run([self.psql, '-X', '-qAt', '-v', 'ON_ERROR_STOP=0'], input=script,
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        if patched:
            self.assertNotIn('ERROR:', result.stderr); self.assertEqual(result.stdout.strip(), '116:2:2:12:7:8')
        else:
            self.assertIn('23505', result.stderr); self.assertIn('25P02', result.stderr)
            self.assertEqual(result.stdout.strip(), '115:1:2:null:7:none')
        POSTGRES_FIXTURES_RUN.add('empty_child_training_commit' if patched and existing else
            ('missing_child_insert_commit' if patched else 'empty_child_duplicate_23505_rollback'))

    def postgres_order_fixture(self):
        _, batches = self.commands('unordered'); read_query = self.last_query.replace('?', '1')
        commands = []
        for statements, args in batches:
            text = statements
            for value in args: text = text.replace('?', str(value), 1)
            self.assertNotIn('?', text); commands.append(text)
        ddl = ('BEGIN;CREATE SCHEMA IF NOT EXISTS dbo;DROP TABLE IF EXISTS dbo.AttribMods;'
            'DROP TABLE IF EXISTS dbo.Powers;DROP TABLE IF EXISTS dbo.Ents;'
            'CREATE TABLE dbo.Ents(ContainerId integer PRIMARY KEY,XP integer,Level integer);'
            'CREATE TABLE dbo.Powers(ContainerId integer,SubId integer,PowerID integer,PRIMARY KEY(ContainerId,SubId));'
            'CREATE TABLE dbo.AttribMods(ContainerId integer,SubId integer,Duration integer,UiD integer,PRIMARY KEY(ContainerId,SubId));'
            'INSERT INTO dbo.Ents VALUES(1,115,1);INSERT INTO dbo.Powers VALUES(1,0,7);'
            'INSERT INTO dbo.AttribMods VALUES(1,1,24,0),(1,0,23,0);'
            'UPDATE dbo.AttribMods SET Duration=25 WHERE ContainerId=1 AND SubId=0;'
            'UPDATE dbo.AttribMods SET Duration=26 WHERE ContainerId=1 AND SubId=1;COMMIT;')
        script = (ddl+read_query+'BEGIN;'+''.join(commands)+'COMMIT;'
            "SELECT XP::text || ':' || Level::text || ':' || (SELECT count(*)::text FROM dbo.AttribMods) || ':' || "
            "(SELECT Duration::text FROM dbo.AttribMods WHERE SubId=0) || ':' || "
            "(SELECT PowerID::text FROM dbo.Powers WHERE SubId=0) || ':' || "
            "(SELECT PowerID::text FROM dbo.Powers WHERE SubId=1) FROM dbo.Ents;"
            'DROP TABLE dbo.AttribMods;DROP TABLE dbo.Powers;DROP TABLE dbo.Ents;')
        result = subprocess.run([self.psql, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'], input=script,
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertNotIn('ERROR:', result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ['1|0|25|0', '1|1|26|0', '116:2:2:12:7:8'])
        POSTGRES_FIXTURES_RUN.add('shuffled_child_read_training_commit')

    def test_observed_duplicate_rolls_back_whole_training_save(self):
        counts, commands = self.commands(patched=False)
        self.assertEqual(counts, (3, 3)); self.assertEqual(commands[0][0].count('INSERT INTO dbo.AttribMods'), 2)
        db = self.database()
        with self.assertRaises(sqlite3.IntegrityError):
            with db: self.execute(db, commands)
        self.assertEqual(db.execute('SELECT XP,Level FROM dbo.Ents').fetchone(), (115, 1))
        self.assertEqual(db.execute('SELECT SubId,PowerID FROM dbo.Powers ORDER BY SubId').fetchall(), [(0, 7)])
        self.assertEqual(db.execute('SELECT Duration FROM dbo.AttribMods WHERE SubId=0').fetchone(), (None,))
        if REQUIRE_POSTGRESQL: self.postgres_fixture(patched=False)

    def test_default_existing_rows_update_and_commit_without_duplicate_inserts(self):
        for mode, flush in (('train', 1000), ('zero', 1000), ('train', 2)):
            with self.subTest(mode=mode, flush=flush):
                counts, commands = self.commands(mode, flush=flush)
                self.assertEqual(counts, (3, 5)); self.assertNotIn('INSERT INTO dbo.AttribMods', ''.join(x[0] for x in commands))
                db = self.database()
                with db: self.execute(db, commands)
                self.assertEqual(db.execute('SELECT SubId,Duration,UiD FROM dbo.AttribMods ORDER BY SubId').fetchall(), [(0, 12, 42), (1, 9, 43)])
                self.assertEqual(db.execute('SELECT XP,Level FROM dbo.Ents').fetchone(), (116, 2))
                self.assertEqual(db.execute('SELECT SubId,PowerID FROM dbo.Powers ORDER BY SubId').fetchall(), [(0, 7), (1, 8)])
        if REQUIRE_POSTGRESQL: self.postgres_fixture()

    def test_missing_rows_still_insert_and_commit(self):
        counts, commands = self.commands('absent'); self.assertEqual(counts, (3, 3))
        self.assertEqual(commands[0][0].count('INSERT INTO dbo.AttribMods'), 2)
        db = self.database(False)
        with db: self.execute(db, commands)
        self.assertEqual(db.execute('SELECT count(*) FROM dbo.AttribMods').fetchone(), (2,))
        if REQUIRE_POSTGRESQL: self.postgres_fixture(existing=False)

    def test_purchased_power_level_and_xp_survive_database_reopen(self):
        with tempfile.TemporaryDirectory(prefix='coh-training-reopen-') as temporary:
            filename = Path(temporary)/'character.sqlite'
            db = self.database(filename=filename)
            _, batches = self.commands()
            with db: self.execute(db, batches)
            db.close()
            with closing(sqlite3.connect(filename)) as reopened:
                self.assertEqual(reopened.execute('SELECT XP,Level FROM Ents WHERE ContainerId=1').fetchone(), (116, 2))
                self.assertEqual(reopened.execute('SELECT SubId,PowerID FROM Powers ORDER BY SubId').fetchall(), [(0, 7), (1, 8)])
                self.assertEqual(reopened.execute('SELECT SubId,Duration,UiD FROM AttribMods ORDER BY SubId').fetchall(), [(0, 12, 42), (1, 9, 43)])

    def test_non_default_rows_sqlserver_and_parent_reads_retain_prior_policy(self):
        for mode, provider in (('nonzero', 2), ('train', 1), ('zero', 1), ('parent', 2)):
            with self.subTest(mode=mode, provider=provider):
                self.assertEqual(self.commands(mode, provider=provider), self.commands(mode, provider=provider, patched=False))

    def test_initial_empty_row_policy_retains_the_original_first_witness(self):
        old, _ = self.commands('initial', patched=False); changed, _ = self.commands('initial')
        self.assertEqual(old, (0, 1)); self.assertEqual(changed, (0, 2))

    def test_shuffled_nonempty_children_read_in_slot_order_before_training_merge(self):
        counts, old = self.commands('unordered', patched=False)
        self.assertEqual(counts, (3, 5)); self.assertNotIn('ORDER BY', self.last_query)
        self.assertIn('INSERT INTO dbo.AttribMods', ''.join(x[0] for x in old))
        counts, commands = self.commands('unordered')
        self.assertEqual(counts, (3, 5)); self.assertIn('ORDER BY SubId', self.last_query)
        self.assertNotIn('INSERT INTO dbo.AttribMods', ''.join(x[0] for x in commands))
        db = self.database()
        with db: self.execute(db, commands)
        self.assertEqual(db.execute('SELECT SubId,Duration,UiD FROM dbo.AttribMods ORDER BY SubId').fetchall(), [(0, 12, 42), (1, 9, 43)])
        if REQUIRE_POSTGRESQL: self.postgres_order_fixture()

    def test_only_postgresql_child_query_adds_explicit_order(self):
        self.commands('train'); self.assertEqual(self.last_query, 'SELECT * FROM dbo.AttribMods WHERE ContainerId = ? ORDER BY SubId;')
        for mode, provider in (('parent', 2), ('train', 1)):
            self.commands(mode, provider=provider)
            self.assertEqual(self.last_query, 'SELECT * FROM dbo.AttribMods WHERE ContainerId = ?;')


class LevelupNativePackageTests(unittest.TestCase):
    def staged(self, source):
        staged_bundle(source)
        return layer.apply_overlay(source)

    def test_narrow_source_patch_and_frozen_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary); staged_bundle(source)
            receipts = {name: (source/name).read_bytes() for name in ('postgresql-build-input.json',
                layer.retained.retained.wine.RECEIPT, layer.retained.retained.RECEIPT, layer.retained.RECEIPT)}
            base = json.loads((source/layer.retained.retained.RECEIPT).read_text())
            bundle = json.loads((source/layer.retained.RECEIPT).read_text())
            before = {name: layer.retained.retained.wine.sha256(source/name) for name in layer.source_closure(base, bundle)}
            value = layer.apply_overlay(source)
            self.assertEqual(value, layer.expected_receipt(base_startup_build_input=base, base_startup_bundle_build_input=bundle))
            self.assertEqual(value['source_sha256'], {name: before[name] for name in layer.PATCHED_FILES})
            for name, raw in receipts.items(): self.assertEqual((source/name).read_bytes(), raw)
            for name, digest in before.items():
                if name not in layer.PATCHED_FILES: self.assertEqual(layer.retained.retained.wine.sha256(source/name), digest)
            text = layer.patch_bytes().decode()
            self.assertEqual([line[6:] for line in text.splitlines() if line.startswith('+++ b/')], list(layer.PATCHED_FILES))
            for forbidden in ('ON CONFLICT', 'sqlFifo', 'sendContainerAcks', 'DELETE FROM'):
                self.assertNotIn(forbidden, text)

    def test_changed_source_ancestry_or_repeated_layer_is_refused(self):
        for target in ('DBServer/src/container_sql.c', 'DBServer/src/container_merge.c', 'DBServer/src/sql_fifo.c'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary); staged_bundle(source); (source/target).write_text('changed')
                with self.assertRaises(ValueError): layer.apply_overlay(source)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary); self.staged(source)
            with self.assertRaisesRegex(ValueError, 'already exists'): layer.apply_overlay(source)

    def test_package_only_new_dbserver_with_exact_ancestry_and_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root/'source'; source.mkdir(); self.staged(source)
            binary = root/'DbServer.exe'; executable(binary)
            cache = root/'CMakeCache.txt'; cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n')
            args = SimpleNamespace(source=source, binary=binary, cache=cache,
                base_manifest=layer.ROOT/layer.retained.retained.ACCEPTED_BASE_MANIFEST,
                repository_commit='a'*40, output=root/'package')
            manifest = layer.package(args)
            self.assertEqual(layer.validate_package(args.output, args.repository_commit), manifest)
            self.assertEqual(manifest['startup_bundle_build_input'], json.loads((source/layer.retained.RECEIPT).read_text()))
            self.assertEqual(manifest['base_startup_bundle_executable'], layer.BASE_STARTUP_BUNDLE_EXECUTABLE)
            self.assertEqual(set(manifest['files']), {'DbServer.exe'})
            path = args.output/layer.MANIFEST
            for key, replacement in (('levelup_ui_repair_build_input', {}), ('startup_bundle_build_input', {}),
                    ('base_startup_bundle_executable', {}), ('postgresql_persistence_fixture', True), ('retained_normal_files', {})):
                changed = copy.deepcopy(manifest); changed[key] = replacement; path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError): layer.validate_package(args.output, args.repository_commit)
            path.write_text(json.dumps(manifest)); binary = args.output/'DbServer.exe'; binary.write_bytes(b'changed')
            with self.assertRaises(ValueError): layer.validate_package(args.output, args.repository_commit)


if __name__ == '__main__':
    if '--require-postgresql' in sys.argv:
        REQUIRE_POSTGRESQL = True; sys.argv.remove('--require-postgresql')
    unittest.main(verbosity=2)
