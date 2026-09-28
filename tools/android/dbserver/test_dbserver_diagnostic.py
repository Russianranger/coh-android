"""Bounded real-DbServer acceptance gates; hosted tests execute the PE32 server."""
import copy
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('coh_dbserver_diagnostic', ROOT / 'android/guest/dbserver_diagnostic.py')
guest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guest)


class DbServerAcceptanceTests(unittest.TestCase):
    def test_current_source_receipt_matches_guest_and_host_fixed_input_contract(self):
        with patch.object(sys, 'path', [str(ROOT / 'tools'), str(ROOT / 'tools/android/dbserver'), *sys.path]):
            from prepare_wine_dbserver_source import expected_wine_receipt
            from host_dbserver_smoke import validate_fixed_inputs_metadata as validate_host_metadata
        metadata = expected_wine_receipt(ROOT)['fixed_inputs']
        guest.validate_fixed_inputs_metadata(metadata)
        validate_host_metadata(metadata)

    def test_fixed_input_startup_requires_exact_single_ack_only_when_requested(self):
        self.assertEqual(guest.validate_fixed_inputs('normal startup\n', False),
                         {'requested': False, 'startup_acknowledgement': None})
        self.assertEqual(guest.validate_fixed_inputs(guest.FIXED_INPUTS_ACK + '\r\n', True),
                         {'requested': True, 'startup_acknowledgement': guest.FIXED_INPUTS_ACK})
        cases = ((True, ''), (False, guest.FIXED_INPUTS_ACK),
                 (True, guest.FIXED_INPUTS_ACK + '.'),
                 (True, guest.FIXED_INPUTS_ACK + '\n' + guest.FIXED_INPUTS_ACK),
                 (True, 'prefix ' + guest.FIXED_INPUTS_ACK),
                 (True, guest.FIXED_INPUTS_ACK.replace('lookup mode preserved', 'lookup mode changed')))
        for enabled, output in cases:
            with self.subTest(enabled=enabled, output=output), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_fixed_inputs(output, enabled)

    def test_fixed_input_receipt_cannot_change_mode_semantics(self):
        guest.validate_fixed_inputs_metadata(copy.deepcopy(guest.FIXED_INPUTS_METADATA))
        for field in guest.FIXED_INPUTS_METADATA:
            changed = copy.deepcopy(guest.FIXED_INPUTS_METADATA)
            changed.pop(field)
            with self.subTest(missing=field), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_fixed_inputs_metadata(changed)
        for field, value in (('lookup_mode', 'changed'), ('disabled_by_default', 1),
                             ('proves_generic_notification_fix', 0)):
            with self.subTest(field=field), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_fixed_inputs_metadata({**guest.FIXED_INPUTS_METADATA, field: value})

    def test_fixed_input_environment_is_explicit_per_launch_and_cannot_leak_to_default(self):
        diagnostic = object.__new__(guest.DbServerDiagnostic)
        diagnostic.wine_env = {'WINEPREFIX': '/private/wine', guest.FIXED_INPUTS_ENV: 'inherited'}
        diagnostic.args = SimpleNamespace(wine=Path('/wine'))
        diagnostic.observe_odbc_failure = Mock()
        diagnostic.ctx = SimpleNamespace(run=Mock(return_value={'exit_code': 0}),
                                         children=[SimpleNamespace(text=lambda: 'output')])
        for enabled in (False, True, False):
            diagnostic.run_windows('schema', Path('/DbServer.exe'), [], Path('/private'),
                                   timeout=10, fixed_inputs=enabled)
            environment = diagnostic.ctx.run.call_args.kwargs['env']
            self.assertEqual(environment.get(guest.FIXED_INPUTS_ENV), '1' if enabled else None)
            self.assertEqual(environment['WINEPREFIX'], '/private/wine')
            self.assertEqual(diagnostic.wine_env[guest.FIXED_INPUTS_ENV], 'inherited')

    def test_two_normal_launches_cover_default_creation_and_fixed_input_reload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'schema/data/server/db/servers.cfg'
            source.parent.mkdir(parents=True)
            source.write_text('UseFakeAuth 1\nUseQueueServer 0\nSqlAllowDDL 1\n')
            runtime = root / 'runtime'
            runtime.mkdir()
            diagnostic = object.__new__(guest.DbServerDiagnostic)
            diagnostic.root = root
            diagnostic.args = SimpleNamespace(schema=root / 'schema')
            diagnostic.schema = {'files': ['data/server/db/servers.cfg']}
            diagnostic.prepare_database = Mock()
            diagnostic.stage_variant = Mock(return_value=runtime)
            diagnostic.connection_for = Mock(return_value='Driver={PostgreSQL Unicode};')
            diagnostic.private_connections = []
            diagnostic.expect_sql = Mock()
            diagnostic.sql = Mock(return_value='[{"version":2}]')
            diagnostic.schema_report = {'phases': []}
            diagnostic.schema_snapshot = Mock(return_value={'table_count': 99, 'attribute_counts': {'attributes': 58272}})
            diagnostic.ctx = SimpleNamespace(log_paths=lambda: [], secrets=[], stage=Mock(), passed=Mock(),
                report={'inputs': {'schema_manifest_sha256': 'a' * 64}})
            requested = []
            def run_windows(label, executable, arguments, cwd, *, timeout, fixed_inputs):
                requested.append((label, fixed_inputs))
                Path(arguments[1]).write_bytes(b'')
                return {'exit_code': 0}, guest.FIXED_INPUTS_ACK + '\n' if fixed_inputs else 'Default startup\n'
            diagnostic.run_windows = run_windows
            with patch.object(guest.base, 'windows_path', side_effect=str):
                diagnostic.normal_schema()
            self.assertEqual(requested, [('normal-schema-1', False), ('normal-schema-2', True)])
            self.assertTrue(diagnostic.schema_report['reload_stable'])
            self.assertEqual([phase['fixed_inputs']['requested'] for phase in diagnostic.schema_report['phases']],
                             [False, True])
            self.assertEqual(diagnostic.schema_snapshot.call_count, 2)

    def test_both_variants_stage_private_legacy_data_root_markers_without_game_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = object.__new__(guest.DbServerDiagnostic)
            diagnostic.root = root / 'state'
            diagnostic.root.mkdir()
            diagnostic.args = SimpleNamespace(package=root / 'package')
            diagnostic.package = {'variants': {}}
            for variant in ('fixture', 'normal'):
                source = diagnostic.args.package / variant
                source.mkdir(parents=True)
                (source / 'DbServer.exe').write_bytes(b'verified-executable')
                diagnostic.package['variants'][variant] = {'files': {'DbServer.exe': {}}}
                runtime = diagnostic.stage_variant(variant)
                self.assertTrue((runtime / 'data').is_dir())
                self.assertTrue((runtime / 'tools').is_dir())
                self.assertEqual(list((runtime / 'data').iterdir()), [])
                self.assertEqual(list((runtime / 'tools').iterdir()), [])
                self.assertFalse((runtime / 'gamedatadir.txt').exists())
                self.assertFalse((runtime / 'piggs').exists())
                self.assertEqual((runtime / 'DbServer.exe').read_bytes(), b'verified-executable')
                self.assertEqual(runtime.parent, diagnostic.root)
                self.assertFalse((source / 'data').exists(), 'Accepted package must remain unchanged')

    def test_fixture_requires_exact_completion_and_expected_failure_semantics(self):
        guest.validate_fixture_phase('initial', 0, 0, 'PG_TEST_COMPLETE initial\r\n')
        guest.validate_fixture_phase('fail', 3, 3, 'PG_FIFO_FAILED command=1 SQLSTATE=23514\n')
        guest.validate_fixture_phase('rebuild-fail', 2, 2, 'PG_TEST_FATAL: refused conversion\n')
        cases = [(0, 0, ''), (0, 0, 'PG_TEST_COMPLETE initial trailing'),
                 (0, 0, 'PG_TEST_COMPLETE verify'), (0, 1, 'PG_TEST_COMPLETE initial'),
                 (0, 0, 'PG_TEST_COMPLETE initial\nPG_FIFO_FAILED command=1'),
                 (0, 0, 'PG_TEST_COMPLETE initial\nPG_TEST_COMPLETE initial'),
                 (3, 3, 'PG_TEST_FAILED line=42'), (3, 3, 'PG_TEST_FATAL unknown mode'),
                 (3, 3, 'PG_FIFO_FAILED command=1\nPG_TEST_COMPLETE initial'),
                 (2, 2, 'PG_TEST_FATAL refused\nPG_TEST_FAILED line=42')]
        for expected, code, output in cases:
            with self.subTest(expected=expected, code=code, output=output), self.assertRaises(guest.base.DiagnosticError):
                guest.validate_fixture_phase('initial', expected, code, output)

    def test_private_config_removes_all_old_sql_settings_and_rejects_external_services(self):
        original = ('UseFakeAuth 1\nUseQueueServer 0\nSqlAllowDDL 1\n'
                    'SqlLogin "old"\nSqlDbName old\nSqlDbProvider sqlserver\nSqlInit old.sql\n')
        actual = guest.private_config(original, 'coh_test_123',
                                      'Driver={PostgreSQL Unicode};Database=coh_test_123;Password=secret;')
        self.assertNotIn('old', actual)
        self.assertNotIn('Database=', actual)
        self.assertIn('SqlDbName coh_test_123\n', actual)
        self.assertEqual(actual.count('SqlLogin '), 1)
        for changed in (original.replace('UseFakeAuth 1', 'UseFakeAuth 0'),
                        original.replace('UseQueueServer 0', 'UseQueueServer 1'),
                        original.replace('SqlAllowDDL 1', 'SqlAllowDDL 0'), original + 'AuthServer elsewhere\n'):
            with self.subTest(config=changed), self.assertRaises(guest.base.DiagnosticError):
                guest.private_config(changed, 'coh_test_123', 'Driver={PostgreSQL Unicode};')

    def test_digest_encodes_unicode_identity_boundaries_and_column_order(self):
        rows = [{'id': 1, 'name': 'caf\u00e9\U0001f600'}, {'id': 2, 'name': 'x\n3:y'}]
        encoded = '1:636166c3a9f09f9880\n2:780a333a79\n'.encode()
        self.assertEqual(guest.attribute_digest(rows), hashlib.sha256(encoded).hexdigest())
        self.assertNotEqual(guest.attribute_digest(rows), guest.attribute_digest(list(reversed(rows))))
        tables = {'b': ['id', 'name'], 'a': ['x', 'y']}
        self.assertEqual(guest.column_digest(tables), guest.column_digest({'a': ['x', 'y'], 'b': ['id', 'name']}))
        self.assertNotEqual(guest.column_digest(tables), guest.column_digest({'a': ['y', 'x'], 'b': ['id', 'name']}))

    def test_only_exact_accepted_catalog_notices_are_exempted(self):
        known = 'SQLERROR: -1 00000 NOTICE: relation "ents" does not exist, skipping'
        self.assertIsNotNone(guest.BENIGN_CATALOG_NOTICE.fullmatch(known))
        for line in (known + '; ERROR: denied', known.replace('ents', 'unknown'),
                     'SQLERROR: -1 00000 NOTICE: unexpectedly lost data', 'PG_FIFO_FAILED ' + known):
            self.assertIsNotNone(guest.FAILURE.search(line))
            self.assertIsNone(guest.BENIGN_CATALOG_NOTICE.fullmatch(line))

    def test_inventory_rejects_unrecorded_mutated_linked_and_parent_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'data' / 'one.template'
            target.parent.mkdir()
            target.write_bytes(b'ContainerId int4\n')
            files = {'data/one.template': {'bytes': target.stat().st_size, 'sha256': guest.base.file_hash(target)}}
            guest.verify_inventory(root, files)
            extra = root / 'extra'
            extra.write_text('unexpected')
            with self.assertRaises(guest.base.DiagnosticError):
                guest.verify_inventory(root, files)
            extra.unlink()
            target.write_bytes(b'ContainerId int8\n')
            with self.assertRaises(guest.base.DiagnosticError):
                guest.verify_inventory(root, files)
            target.unlink()
            target.symlink_to('/dev/null')
            with self.assertRaises(guest.base.DiagnosticError):
                guest.verify_inventory(root, files)
            for name in ('../data/one.template', '/data/one.template', 'data/../one.template', 'data//one.template'):
                with self.subTest(path=name), self.assertRaises(guest.base.DiagnosticError):
                    guest.verify_inventory(root, {name: files['data/one.template']})

    def test_duplicate_manifest_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / 'manifest.json'
            manifest.write_text('{"format":1,"format":1}')
            with self.assertRaises(guest.base.DiagnosticError):
                guest.load_json(manifest)

    def test_internal_logs_remain_bounded_and_symlink_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = guest.DbServerContext(root, 1800)
            context.log_root = root
            log = root / 'server.log'
            with log.open('wb') as output:
                output.truncate(guest.LOG_LIMIT + 1)
            with self.assertRaises(guest.base.DiagnosticError):
                context.check()
            log.unlink()
            log.symlink_to('/dev/null')
            with self.assertRaises(guest.base.DiagnosticError):
                context.log_paths()

    def test_incomplete_cleanup_cannot_publish_a_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake = SimpleNamespace(execute=lambda: None, cleanup=lambda: [], cleanup_status={
                'postgres_graceful': True, 'wine_prefix_stopped': True, 'owned_processes_reaped': False})
            with patch.object(guest, 'DbServerDiagnostic', return_value=fake), \
                 patch.object(guest.signal, 'signal'), redirect_stdout(io.StringIO()):
                code = guest.main(['--state', temporary, '--timeout-seconds', '1800', '--execution-platform', 'host'])
            report = json.loads((Path(temporary) / 'latest-report.json').read_text())
            self.assertEqual(code, 1)
            self.assertFalse(report['passed'])
            self.assertEqual(report['status'], 'failed')
            self.assertIn('Required owned cleanup was not proved', report['failures'])

    def test_cleanup_tracks_created_database_even_if_later_setup_fails(self):
        diagnostic = object.__new__(guest.DbServerDiagnostic)
        diagnostic.created_databases = []
        diagnostic.ctx = SimpleNamespace(children=[SimpleNamespace(text=lambda: 'CREATE DATABASE\n')])
        name = 'coh_test_' + 'a' * 16
        with patch.object(guest.base.Diagnostic, 'sql', return_value='CREATE DATABASE') as sql:
            diagnostic.sql('CREATE DATABASE "' + name + '" OWNER cohtest;')
            self.assertEqual(diagnostic.created_databases, [name])
            diagnostic.sql('DROP DATABASE "' + name + '";', cleanup=True)
            self.assertEqual(sql.call_args.args[0], 'DROP DATABASE "' + name + '";')


if __name__ == '__main__':
    unittest.main()
