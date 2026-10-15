#!/usr/bin/env python3
"""Host admission/lifecycle contract tests; no server-interoperability claim."""
import contextlib
import importlib.util
import io
import inspect
import json
import math
import os
import socket
import time
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('combined_runtime', HERE / 'server_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class AdmissionTests(unittest.TestCase):
    def row(self):
        return {'containerid': 1, 'authname': 'COHLOCAL', 'name': 'THORHERO', 'authid': 100,
                'mapid': 5, 'staticmapid': 5, 'posx': 1.25, 'posy': -768, 'posz': 200}

    def test_saved_map_uses_static_destination(self):
        result = runtime.select_destination([self.row()])
        self.assertEqual((result['map_id'], result['map_port']), (5, 7003))
        self.assertTrue(result['saved_character_available'])
        for target, port in ((1, 7001), (5, 7003)):
            row = dict(self.row(), mapid=None, staticmapid=target)
            self.assertEqual(runtime.select_destination([row])['map_port'], port)

    def test_source_helper_generated_name_is_preserved(self):
        row = dict(self.row(), name='Real Generated Hero')
        before = row.copy()
        runtime.select_destination([row])
        self.assertEqual(row, before)

    def test_empty_profile_is_explicit(self):
        result = runtime.select_destination([])
        self.assertFalse(result['saved_character_available'])
        self.assertEqual(result['character_count'], 0)
        self.assertEqual(result['selection_authority'], 'explicit_empty_profile_atlas')
        with self.assertRaises(runtime.AdmissionError):
            runtime.select_destination([], empty_map=5)

    def test_malformed_saved_destinations_refused(self):
        changes = [{'staticmapid': 101}, {'staticmapid': True}, {'staticmapid': 999},
                   {'mapid': 1}, {'mapid': True}, {'posx': math.nan}, {'posy': math.inf},
                   {'posz': 1e9}, {'posz': True}, {'containerid': 2}, {'containerid': True},
                   {'authid': 0}, {'authid': 0x100000000}, {'authid': True},
                   {'authname': 'OTHER'}, {'name': 'bad\nname'}, {'name': 'x' * 64},
                   {'name': ''}, {'name': None}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(runtime.AdmissionError):
                runtime.select_destination([dict(self.row(), **change)])
        for rows in (None, {}, [self.row()] * 2, [self.row()] * 65, [{}],
                     [dict(self.row(), unexpected=1)]):
            with self.subTest(rows=str(rows)[:60]), self.assertRaises(runtime.AdmissionError):
                runtime.select_destination(rows)

    def test_backup_format_size_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            backup = directory / 'profile.backup'
            backup.write_bytes(b'PGDMP' + bytes(100))
            value = runtime.backup_identity(backup)
            self.assertEqual(value['bytes'], 105)
            self.assertEqual(len(value['sha256']), 64)
            for contents in (b'', b'PGDMP', b'CREATE DATABASE unsafe;', b'xxxxx' + bytes(100)):
                backup.write_bytes(contents)
                with self.assertRaises(runtime.AdmissionError):
                    runtime.backup_identity(backup)
            backup.write_bytes(b'PGDMP' + bytes(100))
            linked = directory / 'linked'
            linked.symlink_to(backup)
            with self.assertRaises(runtime.AdmissionError):
                runtime.backup_identity(linked)
            linked.unlink()
            os.link(backup, linked)
            with self.assertRaises(runtime.AdmissionError):
                runtime.backup_identity(backup)

    def test_all_ancestor_symlinks_and_traversal_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            actual = directory / 'actual'
            actual.mkdir()
            (actual / 'file').write_bytes(b'data')
            (directory / 'link').symlink_to(actual, target_is_directory=True)
            for path in (directory / 'link' / 'file', directory / 'actual' / '..' / 'actual' / 'file',
                         Path('/'), Path('relative')):
                with self.subTest(path=path), self.assertRaises(runtime.AdmissionError):
                    runtime.real_private_path(path)

    def test_ready_contract_has_no_authentication_secrets(self):
        args = SimpleNamespace(session_id='a' * 32, import_generation='generation-' + 'b' * 32)
        ready = runtime.ready_document(args, runtime.select_destination([self.row()]),
                                       assets_sha256='c' * 64, import_receipt_sha256='d' * 64)
        self.assertEqual(ready['db_port'], 7000)
        self.assertEqual(ready['map_port'], 7003)
        self.assertTrue(ready['local_fake_auth'])
        self.assertFalse(ready['native_world_entry_verified'])
        self.assertFalse(ready['encrypted_authentication_verified'])
        self.assertFalse(ready['conventional_client_started'])
        self.assertNotIn('authid', ready)
        for field in ('password', 'cookie', 'credentials', 'session_key', 'character_position'):
            self.assertNotIn(field, ready)
        self.assertLess(len(json.dumps(ready)), 2048)

    def test_invalid_ready_identity(self):
        for session, generation in (('short', 'generation-' + 'b' * 32),
                                    ('a' * 32, 'unscoped'), ('A' * 32, 'generation-' + 'b' * 32)):
            args = SimpleNamespace(session_id=session, import_generation=generation)
            with self.assertRaises(runtime.AdmissionError):
                runtime.ready_document(args, runtime.select_destination([]),
                                       assets_sha256='c' * 64, import_receipt_sha256='d' * 64)

    def test_failure_output_never_includes_exception_details(self):
        # A missing input produces only a constant admission code. A driver
        # must not accidentally expose SQL text or raw process output on error.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = runtime.main(['--state', str(directory / 'state'),
                    '--guest-modules', str(directory / 'missing'),
                    '--assets', str(directory / 'missing'),
                    '--session-id', 'a' * 32, '--import-generation', 'generation-' + 'b' * 32])
            lines = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(status, 1)
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]['failure_code'], 'MISSING_PRIVATE_INPUT')
            self.assertNotIn(str(directory), output.getvalue())
            receipt = json.loads((directory / 'state/latest-report.json').read_text())
            self.assertEqual(receipt['session_id'], 'a' * 32)
            self.assertEqual(receipt['primary_failure_code'], 'MISSING_PRIVATE_INPUT')
            self.assertTrue(receipt['cleanup_complete'])
            self.assertTrue(receipt['cleanup']['no_owned_children_started'])
            self.assertTrue(lines[0]['report_written'])
            metadata = runtime.failure_metadata(OSError(28, 'password=never-export', '/secret/path'))
            self.assertEqual(metadata['failure_errno'], 28)
            self.assertNotIn('never-export', json.dumps(metadata))
            self.assertNotIn('/secret/path', json.dumps(metadata))


class RetainedSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guest = HERE.parents[2] / 'android' / 'guest'
        # Support a repo root explicitly supplied by the CI test driver.
        guest = Path(os.environ.get('COH_COMBINED_GUEST', guest))
        if not guest.is_dir():
            raise unittest.SkipTest('Guest sources require COH_COMBINED_GUEST')
        runtime.load_guest_modules(guest)
        cls.Context, cls.Owner = runtime.runtime_classes()

    def test_api_closure_is_available(self):
        for name in ('initialize', 'execute', 'cleanup', 'sql', 'publish_ready'):
            self.assertTrue(callable(getattr(self.Owner, name)))
        for cls, methods in ((runtime.login.LocalLoginServer, ('start', 'health', 'payloads')),
                             (runtime.character.LocalCharacterServer, ('prepare_runtime', 'sql_rows')),
                             (runtime.zoning.LocalCharacterZoningServer,
                              ('start_map', 'qualify_monorail_preparation', '_spawn_map'))):
            for name in methods:
                self.assertTrue(callable(getattr(cls, name)))

    def test_existing_profile_cannot_be_provisioned_implicitly(self):
        server_class = inspect.getclosurevars(self.Owner.__init__).nonlocals['Server']
        with tempfile.TemporaryDirectory() as temporary:
            server = server_class.__new__(server_class)
            server.profile = Path(temporary)
            server.owner = SimpleNamespace(args=SimpleNamespace(provision_test_character=True,
                                                               logical_backup=None))
            server.destination = runtime.select_destination([])
            with self.assertRaisesRegex(runtime.AdmissionError, 'EXISTING_PROFILE_PROVISIONING_FORBIDDEN'):
                server.provision_if_requested()
            self.assertEqual(list(server.profile.iterdir()), [])

    def test_imported_profile_provision_is_forbidden(self):
        server_class = inspect.getclosurevars(self.Owner.__init__).nonlocals['Server']
        server = server_class.__new__(server_class)
        server.owner = SimpleNamespace(args=SimpleNamespace(provision_test_character=True,
                                                           logical_backup=Path('/unused/backup')))
        with self.assertRaisesRegex(runtime.AdmissionError, 'IMPORTED_PROFILE_PROVISIONING_FORBIDDEN'):
            server.provision_if_requested()

    def test_completed_provision_skips_source_helper(self):
        server_class = inspect.getclosurevars(self.Owner.__init__).nonlocals['Server']
        with tempfile.TemporaryDirectory() as temporary:
            server = server_class.__new__(server_class)
            server.profile = Path(temporary)
            receipt = {'format': 1, 'app_id': runtime.APP_ID, 'committed_sql_verified': True,
                       'helper_reaped': True, 'source_helper_used': True,
                       'native_character_creation_verified': False,
                       'implementation': 'unchanged_source_TestClientCreate_bridge',
                       'snapshot_sha256': 'd' * 64}
            (server.profile / 'provision-complete.json').write_text(json.dumps(receipt))
            server.owner = SimpleNamespace(args=SimpleNamespace(provision_test_character=True,
                                                               logical_backup=None))
            server.destination = runtime.select_destination([AdmissionTests().row()])
            server.provision_if_requested()
            self.assertEqual(server.provision, receipt)

    def test_actual_bound_ports_fail_then_release(self):
        for transport in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            with self.subTest(transport=transport):
                with socket.socket(socket.AF_INET, transport) as listener:
                    listener.bind(('127.0.0.1', 0))
                    if transport == socket.SOCK_STREAM:
                        listener.listen(1)
                    port = listener.getsockname()[1]
                    with self.assertRaisesRegex(runtime.AdmissionError, 'LOCAL_SERVER_PORT_IN_USE'):
                        runtime.admit_local_port(port, transport)
                runtime.admit_local_port(port, transport)

    def test_retained_headless_start_has_single_odbc_owner(self):
        display = inspect.getsource(runtime.startup.presentation.PresentationDiagnostic.start_wine)
        owner = self.Owner.__new__(self.Owner)
        with tempfile.TemporaryDirectory() as temporary:
            owner.presentation_socket = Path(temporary) / 'rfb.sock'
            with mock.patch.object(runtime.startup.presentation.PresentationDiagnostic, 'start_wine') as retained:
                owner.start_wine()
                retained.assert_called_once_with(owner)
        local_login = inspect.getsource(runtime.login.LocalLoginServer.start)
        self.assertNotIn('psqlodbc_x86.msi', display)
        self.assertNotIn('--odbc-driver', display)
        self.assertEqual(local_login.count("'local-install-x86-psqlodbc'"), 1)
        self.assertEqual(local_login.count("'local-odbc-driver'"), 1)

    def test_owned_display_socket_cleanup_allows_repeat_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner = self.Owner.__new__(self.Owner)
            owner.ready_path = root / 'server-ready.json'
            owner.presentation_socket = root / 'rfb.sock'
            owner.xserver = SimpleNamespace(process=SimpleNamespace(poll=lambda: 0),
                                            reader=SimpleNamespace(is_alive=lambda: False))
            owner.cleanup_status = {'owned_processes_reaped': True}
            owner.provisioner = None
            owner.server = SimpleNamespace(cleanup_config=lambda: None)
            try:
                available = socket.socket(socket.AF_UNIX)
            except PermissionError:
                self.skipTest('Host sandbox does not permit AF_UNIX socket creation')
            available.close()
            for _ in range(2):
                with socket.socket(socket.AF_UNIX) as endpoint:
                    endpoint.bind(str(owner.presentation_socket))
                    info = owner.presentation_socket.lstat()
                    owner.presentation_socket_identity = (info.st_dev, info.st_ino)
                with mock.patch.object(runtime.base.Diagnostic, 'cleanup', return_value=[]):
                    self.assertEqual(owner.cleanup(), [])
                self.assertFalse(owner.presentation_socket.exists())
                self.assertTrue(owner.cleanup_status['presentation_socket_removed'])

    def test_changed_display_endpoint_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner = self.Owner.__new__(self.Owner)
            owner.ready_path = root / 'server-ready.json'
            owner.presentation_socket = root / 'rfb.sock'
            owner.presentation_socket.write_text('preserved replacement')
            owner.presentation_socket_identity = (-1, -1)
            owner.xserver = SimpleNamespace(process=SimpleNamespace(poll=lambda: 0),
                                            reader=SimpleNamespace(is_alive=lambda: False))
            owner.cleanup_status = {'owned_processes_reaped': True}
            owner.provisioner = None
            owner.server = SimpleNamespace(cleanup_config=lambda: None)
            with mock.patch.object(runtime.base.Diagnostic, 'cleanup', return_value=[]):
                self.assertTrue(owner.cleanup())
            self.assertEqual(owner.presentation_socket.read_text(), 'preserved replacement')
            self.assertFalse(owner.cleanup_status['presentation_socket_removed'])

    def test_wine_marker_survives_later_prepare_failure_only_after_valid_odbc(self):
        server_class = inspect.getclosurevars(self.Owner.__init__).nonlocals['Server']
        valid_probe = ("COH_ODBC_DRIVER_V1 NAME PostgreSQL Unicode(x86)\n"
                       "COH_ODBC_DRIVER_V1 DLL C:\\windows\\syswow64\\psqlodbc35w.dll\n"
                       "COH_ODBC_DRIVER_V1 PASS bits=32\n")
        for probe_ok in (True, False):
            with self.subTest(valid_probe=probe_ok), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                owner = self.Owner.__new__(self.Owner)
                owner.wineprefix = root / 'prefix'; owner.wineprefix.mkdir()
                owner.wine_ready_marker = owner.wineprefix / '.coh-wine-ready.json'
                owner.wine_ready_identity = {'format': 1, 'purpose': 'coh-wine-initialization',
                                             'runtime_lock_sha256': 'd' * 64}
                owner.wine_initialization = {'state': 'initialized'}
                (owner.wineprefix / '.update-timestamp').write_text('1700000000\n')
                owner.args = SimpleNamespace(wine=root / 'wine', assets=root / 'assets')
                owner.wine_env = {}; owner.port = 5432
                owner.credentials = {'cohtest': 'private-test-fixture'}
                calls = []
                def run(label, argv, **kwargs):
                    calls.append(label)
                    return {'exit_code': 0, 'output': valid_probe if probe_ok else 'FAIL invalid driver'}
                ctx = SimpleNamespace(stage=lambda name: None, passed=lambda **fields: None,
                                      run=run, report={})
                server = server_class.__new__(server_class)
                server.owner = owner; server.ctx = ctx
                with mock.patch.object(runtime.base, 'verify_pe32'), \
                     mock.patch.object(runtime.character.LocalCharacterServer, 'prepare_runtime',
                                       side_effect=RuntimeError('expected later preparation failure')) as preparation:
                    if probe_ok:
                        with self.assertRaisesRegex(RuntimeError, 'expected later preparation failure'):
                            runtime.login.LocalLoginServer.start(server)
                        preparation.assert_called_once_with(server)
                    else:
                        with self.assertRaises(runtime.base.DiagnosticError):
                            runtime.login.LocalLoginServer.start(server)
                        preparation.assert_not_called()
                self.assertEqual(calls, ['local-install-x86-psqlodbc', 'local-odbc-driver'])
                self.assertEqual(owner.wine_ready_marker.exists(), probe_ok)
                self.assertEqual(owner.wine_initialization['state'], 'ready' if probe_ok else 'initialized')
                if probe_ok:
                    self.assertEqual(json.loads(owner.wine_ready_marker.read_text()), owner.wine_ready_identity)

    def test_wine_timestamp_reuse_matches_retained_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / 'assets'; assets.mkdir()
            (assets / 'runtime-lock.json').write_text('{}')
            wine = root / 'wine/bin/wine'; wine.parent.mkdir(parents=True)
            wine.write_bytes(b'not executed')
            inf = root / 'wine/share/wine/wine.inf'; inf.parent.mkdir(parents=True)
            inf.write_bytes(b'pinned INF fixture')
            os.utime(inf, (1700000000, 1700000000))
            prefix = root / 'prefix'; prefix.mkdir()
            owner = self.Owner.__new__(self.Owner)
            owner.args = SimpleNamespace(assets=assets, wine=wine)
            owner.wineprefix = prefix
            owner.ctx = self.Context(SimpleNamespace(state=root, timeout_seconds=600, session_id='a' * 32))
            marker = {'format': 1, 'purpose': 'coh-wine-initialization',
                      'runtime_lock_sha256': runtime.digest(assets / 'runtime-lock.json')}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                for _ in range(2):
                    (prefix / '.coh-wine-ready.json').write_text(json.dumps(marker))
                    (prefix / '.update-timestamp').write_text('1700000000\n')
                    owner.prepare_wine_initialization()
                    self.assertTrue(owner.wine_initialization['ready_prefix_reused'])
                    self.assertEqual(owner.wine_initialization['refresh_reason'], 'none')
                (prefix / '.coh-wine-ready.json').write_text(json.dumps(marker))
                os.utime(inf, (1700000001, 1700000001))
                owner.prepare_wine_initialization()
            self.assertFalse(owner.wine_initialization['ready_prefix_reused'])
            self.assertEqual(owner.wine_initialization['refresh_reason'], 'wine_inf_timestamp_changed')
            self.assertFalse((prefix / '.update-timestamp').exists())

    def constructor_case(self, *, attempt=False, context_failure=False):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            actual_context = self.Context
            class FailingOwner:
                def __init__(self, args, context):
                    if attempt:
                        context.owned_start_attempts = 1
                    raise RuntimeError('password=never-log-this')
            class FailingContext:
                def __init__(self, args):
                    raise RuntimeError('unknown constructor ownership')
            output = io.StringIO()
            with mock.patch.object(runtime, 'validate_arguments'), \
                 mock.patch.object(runtime, 'load_guest_modules'), \
                 mock.patch.object(runtime, 'runtime_classes', return_value=(
                     FailingContext if context_failure else actual_context, FailingOwner)), \
                 contextlib.redirect_stdout(output):
                result = runtime.main(['--state', str(state), '--session-id', 'a' * 32,
                    '--import-generation', 'generation-' + 'b' * 32])
            self.assertEqual(result, 1)
            self.assertNotIn('never-log-this', output.getvalue())
            receipt = json.loads((state / 'latest-report.json').read_text())
            self.assertEqual(receipt['primary_failure_code'], 'RETAINED_GUEST_DEPENDENCY_FAILED')
            return receipt

    def test_owner_constructor_without_start_is_clean(self):
        receipt = self.constructor_case()
        self.assertTrue(receipt['cleanup_complete'])
        self.assertEqual(receipt['exception_type'], 'RuntimeError')

    def test_owner_constructor_after_start_attempt_is_ambiguous(self):
        receipt = self.constructor_case(attempt=True)
        self.assertFalse(receipt['cleanup_complete'])
        self.assertEqual(receipt['cleanup_failure_code'], 'OWNED_CLEANUP_INCOMPLETE')
        self.assertEqual(receipt['failure_code'], 'RETAINED_GUEST_DEPENDENCY_FAILED')

    def test_context_constructor_failure_is_ambiguous(self):
        self.assertFalse(self.constructor_case(context_failure=True)['cleanup_complete'])

    def test_refresh_preserves_completed_child_duration(self):
        ctx = self.Context(SimpleNamespace(state=Path('/unused'), timeout_seconds=600, session_id='a' * 32))
        child = SimpleNamespace(label='completed-fixture', started=time.monotonic() - 500,
            completion={'elapsed_seconds': 1.25}, forced_stop=False, recorded=None,
            process=SimpleNamespace(poll=lambda: 0), output=b'test', overflow=False,
            reader=SimpleNamespace(is_alive=lambda: False), writer=SimpleNamespace(is_alive=lambda: False),
            text=lambda: 'not exported')
        first = ctx.record(child)
        child.started -= 100
        second = ctx.record(child, refresh=True)
        self.assertEqual(first['elapsed_seconds'], 1.25)
        self.assertEqual(second['elapsed_seconds'], 1.25)
        self.assertGreater(second['observed_lifetime_seconds'], first['observed_lifetime_seconds'])
        self.assertEqual(second['elapsed_scope'], 'completed_execution')
        self.assertEqual(second['output_bytes'], 4)

    def test_report_output_symlink_does_not_overwrite_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            target = state / 'preserve'; target.write_text('original')
            (state / 'latest-report.json').symlink_to(target)
            args = SimpleNamespace(state=state, session_id='a' * 32,
                                   import_generation='generation-' + 'b' * 32)
            with self.assertRaisesRegex(runtime.AdmissionError, 'INVALID_REPORT_OUTPUT'):
                runtime.write_report(args, {'format': 1})
            self.assertEqual(target.read_text(), 'original')

    def test_private_sql_record_not_exported_or_logged(self):
        args = SimpleNamespace(state=Path('/unused'), timeout_seconds=600, session_id='a' * 32)
        ctx = self.Context(args)
        child = SimpleNamespace(label='sql-test', started=0, forced_stop=False,
            recorded=None, process=SimpleNamespace(poll=lambda: 0),
            reader=SimpleNamespace(is_alive=lambda: False), writer=SimpleNamespace(is_alive=lambda: False),
            text=lambda: 'secret-cookie-and-password-user-data')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            receipt = ctx.record(child)
        self.assertIn('secret-cookie', receipt['output'])  # Available only to accepted internal parser.
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn('secret-cookie', json.dumps(ctx.report))
        self.assertNotIn('output', child.recorded)

    def test_event_projection_drops_raw_packet_cookie_sql(self):
        args = SimpleNamespace(state=Path('/unused'), timeout_seconds=600, session_id='a' * 32)
        ctx = self.Context(args)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ctx.event('log', message='password=raw cookie=raw SQL row')
            ctx.event('local_server_ready', cookie='raw', auth_id=99, password='raw')
        raw = output.getvalue()
        self.assertNotIn('raw', raw)
        self.assertNotIn('password', raw)
        self.assertNotIn('cookie', raw)
        self.assertEqual(len(raw.splitlines()), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
