"""Verify real Wine-over-PG patch provenance and execute the actual C adapter."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import prepare_wine_dbserver_source as wine


class WineDbServerSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'source'
        self.source.mkdir()
        self.expected = wine.expected_wine_receipt()
        self.pg = self.expected['postgresql_build_input']
        self.original = wine.ROOT / 'upstream/ouroboros'
        for name in set(wine.WINE_FILES).union(self.pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.original / name, target)
        wine.apply_patch(self.source, (wine.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                         .read_bytes().replace(b'\r\n', b'\n'))
        for name in self.pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(wine.ROOT / 'database/postgresql/overlay' / name, target)
        self.pg_path = self.source / 'postgresql-build-input.json'
        self.pg_path.write_text(json.dumps(self.pg))

    def test_real_overlay_binds_pg_and_wine_inputs_without_changing_upstream(self):
        before = {name: wine.sha256(self.original / name) for name in wine.WINE_FILES}
        receipt = wine.apply_wine_overlay(self.source)
        self.assertEqual(receipt, self.expected)
        self.assertEqual(json.loads((self.source / wine.RECEIPT).read_text()), receipt)
        self.assertEqual(json.loads(self.pg_path.read_text()), self.pg)
        for name, digest in receipt['patched_sha256'].items():
            self.assertEqual(wine.sha256(self.source / name), digest)
        for name, digest in receipt['wine_overlay_sha256'].items():
            self.assertEqual(wine.sha256(self.source / name), digest)
        self.assertEqual(before, {name: wine.sha256(self.original / name) for name in wine.WINE_FILES})
        cmake = (self.source / 'DBServer/CMakeLists.txt').read_text()
        self.assertIn('target_compile_definitions(DbServer PRIVATE COH_WINE_ODBC=1)', cmake)
        self.assertIn('src/wine_dispatch_progress.c', cmake)
        self.assertIn('option(COH_PG_PERSISTENCE_TESTS', cmake)
        self.assertEqual(receipt['runtime_validation'], 'unverified')

    def test_dispatch_receipt_labels_every_instrumented_stage_and_binds_sources(self):
        receipt = wine.apply_wine_overlay(self.source)
        metadata = receipt['dispatch_progress']
        source = (self.source / 'DBServer/src/dbinit.c').read_text()
        observer = (self.source / 'DBServer/src/wine_dispatch_progress.c').read_text()
        markers = set(re.findall(r'cohDbProgressMark\(COH_DB_STAGE_(\w+)\)', source + observer))
        self.assertEqual(markers, set(metadata['stages'].values()))
        self.assertFalse(metadata['proves_sql_or_game_success'])
        self.assertTrue(metadata['disabled_by_default'])
        self.assertEqual(metadata['environment_variable'], 'COH_WINE_DB_PROGRESS')
        self.assertEqual(metadata['record_bytes'], 128)
        self.assertEqual(metadata['mapping_bytes'], 4096)
        self.assertEqual(metadata['offsets']['sequence'], 24)
        for name in ('DBServer/src/wine_dispatch_progress.c', 'DBServer/src/wine_dispatch_progress.h'):
            self.assertEqual(wine.sha256(self.source / name), receipt['wine_overlay_sha256'][name])
        main = source.split('int main(int argc,char **argv)', 1)[1]
        self.assertLess(main.index('return pgPersistenceTestMain'), main.index('cohDbProgressInit()'))
        self.assertLess(main.index('cohDbProgressInit()'), main.index('setWindowIconColoredLetter'))
        self.assertIn('return 2;', main.split('cohDbProgressInit() < 0)', 1)[1].split('}', 1)[0])

    def test_dispatch_metadata_rejects_duplicate_or_noncontiguous_stage_ids(self):
        original = wine.overlay_bytes(wine.ROOT)
        name = 'DBServer/src/wine_dispatch_progress.h'
        for before, after in ((b'COH_DB_STAGE_STARTUP = 2', b'COH_DB_STAGE_STARTUP = 1'),
                              (b'COH_DB_STAGE_STARTUP = 2', b'COH_DB_STAGE_STARTUP = 99'),
                              (b'COH_DB_STAGE_STARTUP = 2', b'COH_DB_STAGE_INITIALIZED = 2')):
            contents = dict(original)
            contents[name] = contents[name].replace(before, after)
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, 'unique contiguous'):
                wine.dispatch_progress_metadata(contents)

    @unittest.skipUnless(shutil.which('cc'), 'Dispatch boundary contract requires a C compiler')
    def test_actual_msgscan_marks_calls_without_changing_conditional_work(self):
        wine.apply_wine_overlay(self.source)
        source = (self.source / 'DBServer/src/dbinit.c').read_text()
        header = (self.source / 'DBServer/src/wine_dispatch_progress.h').read_text()
        enum = header[header.index('typedef enum CohDbProgressStage'):header.index('} CohDbProgressStage;') + len('} CohDbProgressStage;')]
        functions = source[source.index('static void sendSqlKeepAlive(void)'):source.index('\nchar *getMapName')]
        probe = self.source / 'dispatch-boundaries.c'
        probe.write_text('''#include <assert.h>
#include <string.h>
typedef unsigned U32;
#define false 0
#define SQLCONN_FOREGROUND 0
#define SQLCONN_MAX 3
''' + enum + '''
static CohDbProgressStage stage;
static unsigned now = 120, foreground_calls, queued_calls, auth_calls, client_calls, chat_calls;
static int disconnected;
static struct { int queue_server, use_logserver, name_lock_timeout; } server_cfg;
void cohDbProgressMark(CohDbProgressStage next) { stage = next; }
U32 timerSecondsSince2000(void) {
    assert(stage == COH_DB_STAGE_SQL_KEEPALIVE_CHECK || stage == COH_DB_STAGE_TEMP_LOCKS);
    return now;
}
void sqlConnExecDirect(char *sql, unsigned length, int connection, int flag) {
    assert(stage == COH_DB_STAGE_SQL_KEEPALIVE_FOREGROUND);
    assert(!strcmp(sql, ";") && length == 1 && connection == 0 && flag == 0);
    foreground_calls++;
}
void sqlExecAsyncEx(char *sql, unsigned length, unsigned connection, int flag) {
    assert(stage == COH_DB_STAGE_SQL_KEEPALIVE_QUEUE);
    assert(!strcmp(sql, ";") && length == 1 && connection < 2 && flag == 0);
    queued_calls++;
}
#define OP(name, marker) void name(void) { assert(stage == COH_DB_STAGE_ ## marker); }
OP(sqlFifoTick, SQL_FIFO_TICK)
OP(delinkCrashedMaps, DELINK_MAPS)
OP(delinkDeadLaunchers, DELINK_LAUNCHERS)
OP(sqlFifoDisableNMMonitorIfMemoryLow, SQL_MEMORY_PRESSURE)
void NMMonitor(int timeout) { assert(stage == COH_DB_STAGE_NM_MONITOR && timeout == 1); }
OP(svrMonSendUpdates, SVRMON_UPDATES)
OP(checkServerAutoStart, AUTO_START)
int authDisconnected(void) { assert(stage == COH_DB_STAGE_AUTH_STATUS); return disconnected; }
void reconnectToAuth(void) { assert(stage == COH_DB_STAGE_AUTH_RECONNECT); auth_calls++; }
OP(waitingEntitiesCheck, WAITING_ENTITIES)
OP(dbRelayQueueCheck, DB_RELAY)
void clientClearDeadLinks(void) { assert(stage == COH_DB_STAGE_CLIENT_LINKS); client_calls++; }
OP(queueservercomm_updateCount, CLIENT_LINKS)
OP(launcherLaunchBeaconizers, BEACON_LAUNCHERS)
OP(stat_Update, STATS)
void shardChatMonitor(void) { assert(stage == COH_DB_STAGE_SHARD_CHAT); chat_calls++; }
OP(updateLogStats, LOG_STATS)
OP(auctionMonitorTick, AUCTION)
OP(launcherOverloadProtectionTick, OVERLOAD)
void tempLockTick(int timeout, U32 time) {
    assert(stage == COH_DB_STAGE_TEMP_LOCKS && timeout == 27 && time == now);
}
OP(updateDbServerTitle, CONSOLE_TITLE)
OP(checkExitRequest, EXIT_REQUEST)
OP(FolderCacheDoCallbacks, FOLDER_CALLBACKS)
OP(mpCompactPools, POOL_COMPACT)
''' + functions + '''
int main(void) {
    server_cfg.name_lock_timeout = 27;
    msgScan();
    assert(foreground_calls == 1 && queued_calls == 2);
    assert(auth_calls == 0 && client_calls == 1 && chat_calls == 1);
    assert(stage == COH_DB_STAGE_POOL_COMPACT);
    now = 121; disconnected = 1; server_cfg.queue_server = 1; server_cfg.use_logserver = 1;
    msgScan();
    assert(foreground_calls == 1 && queued_calls == 2);
    assert(auth_calls == 1 && client_calls == 1 && chat_calls == 1);
    now = 180; disconnected = 0;
    msgScan();
    assert(foreground_calls == 2 && queued_calls == 4);
    assert(auth_calls == 1 && client_calls == 1 && chat_calls == 1);
    return 0;
}
''')
        for flags in ([], ['-DQUEUESERVER_VERIFICATION=1']):
            executable = self.source / ('dispatch-boundaries-' + str(len(flags)))
            subprocess.run([shutil.which('cc'), '-std=c99', '-Wall', '-Wextra', '-Werror',
                            *flags, str(probe), '-o', str(executable)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(executable)], check=True, capture_output=True, timeout=10)

    def test_changed_touched_source_or_pg_overlay_is_rejected_before_any_patch(self):
        for name in (*wine.WINE_FILES, next(iter(self.pg['overlay_sha256']))):
            target = self.source / name
            original = target.read_bytes()
            target.write_bytes(original + b'\n// unexpected edit\n')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                wine.apply_wine_overlay(self.source)
            target.write_bytes(original)
        for name, digest in self.expected['source_sha256'].items():
            self.assertEqual(wine.sha256(self.source / name), digest)
        self.assertFalse((self.source / wine.RECEIPT).exists())

    def test_stale_pg_receipt_and_unknown_overlay_profile_are_rejected(self):
        changed = dict(self.pg, source_commit='f' * 40)
        self.pg_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            wine.apply_wine_overlay(self.source)
        changed = json.loads(json.dumps(self.pg))
        name = next(iter(changed['overlay_sha256']))
        target = self.source / name
        target.write_bytes(target.read_bytes() + b'\n// unrecorded code\n')
        changed['overlay_sha256'][name] = wine.sha256(target)
        self.pg_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            wine.apply_wine_overlay(self.source)

    def test_known_pg_crlf_overlay_keeps_its_actual_receipt(self):
        pg = json.loads(json.dumps(self.pg))
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            pg['overlay_sha256'][name] = wine.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        result = wine.apply_wine_overlay(self.source)
        self.assertEqual(result, wine.expected_wine_receipt(postgresql_build_input=pg))
        self.assertEqual(result['postgresql_build_input'], pg)

    def test_existing_adapter_file_is_rejected_before_source_changes(self):
        target = self.source / wine.OVERLAY_FILES[0]
        target.write_text('unrelated preexisting file')
        with self.assertRaisesRegex(ValueError, 'overwrite source'):
            wine.apply_wine_overlay(self.source)
        self.assertEqual(target.read_text(), 'unrelated preexisting file')
        for name, digest in self.expected['source_sha256'].items():
            self.assertEqual(wine.sha256(self.source / name), digest)

    def test_second_application_upstream_and_existing_output_are_rejected(self):
        wine.apply_wine_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            wine.apply_wine_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            wine.apply_wine_overlay(self.original)
        with self.assertRaisesRegex(ValueError, 'new directory'):
            wine.prepare(self.source)

    def test_pinned_sqlgetinfo_source_contract_has_only_three_string_types(self):
        sqlconn = (self.original / 'Common/sql/sqlconn.c').read_text()
        calls = re.findall(r'(?m)^\s*(?:ret = )?SQLGetInfo\([^,]+,\s*([^,]+),', sqlconn)
        self.assertCountEqual(calls, ['info_type', 'SQL_DRIVER_NAME', 'SQL_DRIVER_VER', 'SQL_DRIVER_ODBC_VER'])
        numeric = set()
        for directory in ('Common/sql', 'DBServer/src'):
            for path in (self.original / directory).glob('*.c'):
                numeric.update(re.findall(r'sqlConnGetInfo\((SQL_\w+),', path.read_text(errors='strict')))
        self.assertEqual(numeric, {'SQL_GETDATA_EXTENSIONS', 'SQL_ATTR_QUERY_TIMEOUT',
                                   'SQL_ASYNC_DBC_FUNCTIONS', 'SQL_TXN_CAPABLE'})

    @unittest.skipUnless(shutil.which('cc'), 'Native startup ordering contract requires a C compiler')
    def test_actual_dispatch_warms_cache_before_fixture_only_for_wine_fixture_build(self):
        wine.apply_wine_overlay(self.source)
        source = (self.source / 'DBServer/src/dbinit.c').read_text()
        main = source.split('int main(int argc,char **argv)', 1)[1]
        dispatch = main.split('memCheckInit();', 1)[1].split('EXCEPTION_HANDLER_BEGIN', 1)[0]
        self.assertIn('#include <utilitieslib/utils/log.h>', source)
        self.assertIn('#include <utilitieslib/assert/assert.h>', source)
        self.assertIn('SuperAssert.h', (self.original /
                      'libs/UtilitiesLib/include/utilitieslib/assert/assert.h').read_text())
        probe = self.source / 'startup-order.c'
        probe.write_text('''#include <assert.h>
#include <string.h>
#define ASSERTMODE_STDERR 1
#define ASSERTMODE_EXIT 2
static int startup_step;
void setAssertMode(int mode) {
    assert(mode == (ASSERTMODE_STDERR | ASSERTMODE_EXIT));
    assert(startup_step == 0); startup_step = 1;
}
void logSetDir(const char *directory) {
    assert(startup_step == 1 && !strcmp(directory, "pg-persistence-test"));
    startup_step = 2;
}
int pgPersistenceTestMain(int argc, char **argv) {
    assert(argc == 2 && !strcmp(argv[1], "-pgpersistencetest"));
#ifdef COH_WINE_ODBC
    assert(startup_step == 2);
#else
    assert(startup_step == 0);
#endif
    return 37;
}
int entry(int argc, char **argv) {
    (void)argc; (void)argv;
''' + dispatch + '''
    return -1;
}
int main(void) {
    char *fixture[] = {"DbServer.exe", "-pgpersistencetest"};
    char *normal[] = {"DbServer.exe", "-exportdump"};
#ifdef COH_PG_PERSISTENCE_TESTS
    assert(entry(2,fixture) == 37);
#else
    assert(entry(2,fixture) == -1);
#endif
    startup_step = 0;
    assert(entry(2,normal) == -1 && startup_step == 0);
    return 0;
}
''')
        for flags in ([], ['COH_WINE_ODBC'], ['COH_PG_PERSISTENCE_TESTS'],
                      ['COH_WINE_ODBC', 'COH_PG_PERSISTENCE_TESTS']):
            with self.subTest(flags=flags):
                executable = self.source / ('startup-order-' + str(len(flags)) + ('-wine' if 'COH_WINE_ODBC' in flags else ''))
                subprocess.run([shutil.which('cc'), '-std=c99', '-Wall', '-Wextra', '-Werror',
                                *['-D' + name + '=1' for name in flags], str(probe), '-o', str(executable)],
                               check=True, capture_output=True, timeout=30)
                subprocess.run([str(executable)], check=True, capture_output=True, timeout=10)


class WineOdbcAdapterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'Native adapter contract requires a C compiler')
    def test_actual_adapter_conversion_and_call_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / 'adapter-contract'
            adapter = wine.ROOT / wine.OVERLAY / 'Common/sql'
            tests = wine.ROOT / 'database/wine-dbserver/tests'
            subprocess.run([shutil.which('cc'), '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-DCOH_WINE_ODBC=1', '-I' + str(tests), '-I' + str(adapter),
                            str(adapter / 'wine_odbc.c'), str(tests / 'adapter_contract.c'),
                            '-o', str(executable)], check=True, capture_output=True, timeout=30)
            result = subprocess.run([str(executable)], check=True, capture_output=True, text=True, timeout=10)
            self.assertIn('PASS Wine DbServer adapter:', result.stdout)


if __name__ == '__main__':
    unittest.main()
