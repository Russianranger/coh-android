#!/usr/bin/env python3
"""Host admission/lifecycle contract tests; no server-interoperability claim."""
import contextlib
import hashlib
import importlib.util
import io
import inspect
import json
import math
import os
import socket
import selectors
import stat
import subprocess
import sys
import time
import threading
from pathlib import Path
import tempfile
import textwrap
import zipfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('combined_runtime', HERE / 'server_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class PostgresMemoryTests(unittest.TestCase):
    def test_owned_start_reduces_memory_without_changing_durability_or_datadir(self):
        original=['postgres','-D',Path('/private/profile/pgdata'),'-c','max_connections=80',
                  '-c','shared_buffers=32MB','-c','listen_addresses=127.0.0.1',
                  '-c','fsync=on','-c','synchronous_commit=on','-c','full_page_writes=on']
        before=original.copy();actual=runtime.postgres_memory_argv('postgres_native_combined',original)
        self.assertEqual(original,before)
        self.assertEqual(actual[:3],original[:3])
        settings=dict(actual[i+1].split('=',1) for i,arg in enumerate(actual[:-1]) if arg=='-c')
        for name,value in runtime.POSTGRES_MEMORY_SETTINGS.items():self.assertEqual(settings[name],value)
        for name in ('fsync','synchronous_commit','full_page_writes'):self.assertEqual(settings[name],'on')
        self.assertEqual(settings['listen_addresses'],'127.0.0.1')
        self.assertGreaterEqual(int(settings['max_connections'])-int(settings['superuser_reserved_connections']),65+1)
        self.assertEqual(runtime.postgres_memory_argv('postgres_native_combined',actual),actual)
        self.assertIs(runtime.postgres_memory_argv('other_child',original),original)

    def test_readback_is_actual_SHOW_and_unavailable_never_fails_startup(self):
        sql=mock.Mock(return_value='72\n3\n16MB\n1MB\n16MB')
        observed=runtime.postgres_memory_observation(sql)
        self.assertEqual(observed['observation_status'],'observed')
        self.assertEqual(observed['observed'],runtime.POSTGRES_MEMORY_SETTINGS)
        self.assertEqual(observed['source'],'owned_postgresql_SHOW')
        self.assertFalse(observed['rss_pss_change_measured'])
        sql.assert_called_once_with('SHOW max_connections;\nSHOW superuser_reserved_connections;\nSHOW shared_buffers;\nSHOW work_mem;\nSHOW maintenance_work_mem;')
        # A different SHOW value is observed as received, never replaced by argv.
        actual=runtime.postgres_memory_observation(lambda query:'71\n3\n32MB\n2MB\n8MB')
        self.assertEqual(actual['observed']['max_connections'],'71')
        self.assertEqual(actual['requested']['max_connections'],'72')
        for value in (None,42,'','private account text','1\n'*1000,'72|3|16MB|1MB|16MB',
                      '72\n3\n16MB\n1MB','72MB\n3\n16MB\n1MB\n16MB',
                      '72\n3\n16MB\n1MB\n16MB\nprivate','9'*11+'\n3\n16MB\n1MB\n16MB'):
            with self.subTest(value=str(value)[:40]):
                self.assertEqual(runtime.postgres_memory_observation(lambda query:value)['reason'],'POSTGRES_SHOW_RESULT_INVALID')
        def failed(query):raise RuntimeError('password=never-retain-this')
        failure=runtime.postgres_memory_observation(failed)
        self.assertEqual(failure['observation_status'],'unavailable')
        self.assertEqual(failure['reason'],'POSTGRES_SHOW_FAILED')
        self.assertNotIn('never-retain-this',json.dumps(failure))

    def test_actual_main_retains_current_owned_SHOW_event_and_final_report(self):
        class Stopped(Exception):pass
        class Context:
            def __init__(self,args):
                self.session_id=args.session_id;self.stage_name='owned_profile'
                self.report={'processes':[],'stages':[]};self.stage_started_monotonic=None
                self.children=[];self.owned_start_attempts=0
        class Owner:
            def __init__(self,args,context):
                self.context=context;self.ready_path=args.state/'server-ready.json'
                self.cleanup_status={'owned_processes_reaped':True}
                self.server=SimpleNamespace(creation_report={});self.ready_receipt=None
            def execute(self):
                runtime.retain_postgres_memory_observation(self.context,lambda query:'71\n3\n32MB\n2MB\n8MB')
                raise Stopped()
            def cleanup(self):return []
        with tempfile.TemporaryDirectory() as tmp:
            output=io.StringIO();state=Path(tmp)/'state'
            with mock.patch.object(runtime,'validate_arguments'),mock.patch.object(runtime,'load_guest_modules'), \
                    mock.patch.object(runtime,'runtime_classes',return_value=(Context,Owner)), \
                    mock.patch.object(runtime,'base',SimpleNamespace(Cancelled=Stopped)), \
                    mock.patch.object(runtime.signal,'signal'),contextlib.redirect_stdout(output):
                code=runtime.main(['--state',str(state),'--session-id','a'*32,
                                   '--import-generation','generation-'+'b'*32])
            self.assertEqual(code,0)
            report=json.loads((state/'latest-report.json').read_text())
            observation=report['postgresql_memory_settings']
            self.assertEqual(observation['observed']['max_connections'],'71')
            self.assertEqual(observation['requested']['max_connections'],'72')
            self.assertTrue(report['cleanup_complete'])
            self.assertTrue(report['profile_preserved'])
            events=[json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(events[0]['type'],'postgresql_memory_settings')
            self.assertEqual(events[0]['session_id'],'a'*32)
            self.assertEqual({k:v for k,v in events[0].items() if k not in ('type','session_id')},observation)
            self.assertTrue(events[-1]['report_written'])
            self.assertLess(len(json.dumps(events[0])),1024)

    def test_owned_profile_invokes_the_readback_after_actual_start(self):
        source=inspect.getsource(runtime.runtime_classes)
        start=source.index("d.start_postgres('postgres_native_combined')")
        readback=source.index('retain_postgres_memory_observation(self.ctx, d.sql)')
        self.assertLess(start,readback)


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

    def test_session_display_endpoints_preserve_interrupted_legacy_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'runtime').mkdir(mode=0o700)
            legacy = root / 'runtime/vnc.sock'
            legacy.write_text('unrelated or interrupted endpoint; preserve')
            previous = legacy.stat()
            first = runtime.presentation_endpoint(root, 'a' * 32)
            second = runtime.presentation_endpoint(root, 'b' * 32)
            self.assertNotEqual(first, second)
            self.assertEqual(first.name, 'v' + hashlib.sha256(('a' * 32).encode()).hexdigest()[:24])
            self.assertEqual(len(first.name), 25)
            for prefix in ('/data/user/0', '/data/data', '/data/user/10', '/data/user/12345'):
                backing = Path(prefix) / 'org.coh.nativecombined/files/combined-server/diagnostic/runtime' / first.name
                self.assertLessEqual(len(os.fsencode(backing)), 107)
            self.assertLessEqual(len(os.fsencode(first)), 107)
            self.assertEqual(legacy.read_text(), 'unrelated or interrupted endpoint; preserve')
            self.assertEqual(legacy.stat(), previous)
            first.write_text('preserve a conflicting current-session endpoint')
            with self.assertRaisesRegex(runtime.AdmissionError, 'OWNED_DISPLAY_SOCKET_ALREADY_EXISTS'):
                runtime.presentation_endpoint(root, 'a' * 32)
            self.assertEqual(first.read_text(), 'preserve a conflicting current-session endpoint')
            self.assertEqual(runtime.presentation_endpoint(root, 'b' * 32), second)

    def test_session_display_refuses_linked_malformed_and_unowned_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'runtime'
            directory.mkdir(mode=0o700)
            target = root / 'target'
            target.write_text('preserved')
            endpoint = runtime.presentation_endpoint(root, 'a' * 32)
            endpoint.symlink_to(target)
            with self.assertRaisesRegex(runtime.AdmissionError, 'OWNED_DISPLAY_SOCKET_ALREADY_EXISTS'):
                runtime.presentation_endpoint(root, 'a' * 32)
            self.assertTrue(endpoint.is_symlink())
            self.assertEqual(target.read_text(), 'preserved')
            endpoint.unlink()
            directory.chmod(0o755)
            with self.assertRaisesRegex(runtime.AdmissionError, 'INVALID_PRIVATE_DISPLAY_DIRECTORY'):
                runtime.presentation_endpoint(root, 'a' * 32)
            directory.chmod(0o700)
            with mock.patch.object(runtime.os, 'geteuid', return_value=directory.stat().st_uid + 1):
                with self.assertRaisesRegex(runtime.AdmissionError, 'INVALID_PRIVATE_DISPLAY_DIRECTORY'):
                    runtime.presentation_endpoint(root, 'a' * 32)
            for session in ('', 'a' * 31, 'A' * 32, '../' + 'a' * 32, None, True):
                with self.subTest(session=session), self.assertRaises(runtime.AdmissionError):
                    runtime.presentation_endpoint(root, session)
            directory.rmdir()
            real = root / 'real'
            real.mkdir(mode=0o700)
            directory.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(runtime.AdmissionError, 'LINKED_PRIVATE_PATH'):
                runtime.presentation_endpoint(root, 'a' * 32)
            self.assertTrue(directory.is_symlink())

    def test_session_display_path_length_is_checked_before_spawn(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ('d' * 70)
            (root / 'runtime').mkdir(mode=0o700, parents=True)
            with self.assertRaisesRegex(runtime.AdmissionError, 'OWNED_DISPLAY_SOCKET_PATH_TOO_LONG'):
                runtime.presentation_endpoint(root, 'a' * 32)

    def test_real_unix_socket_interruption_then_new_session_restart(self):
        try:
            probe = socket.socket(socket.AF_UNIX)
        except PermissionError:
            self.skipTest('Host sandbox does not permit AF_UNIX socket creation')
        probe.close()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'runtime').mkdir(mode=0o700)
            first = runtime.presentation_endpoint(root, 'a' * 32)
            worker = subprocess.Popen([sys.executable, '-c',
                "import socket,sys,signal; s=socket.socket(socket.AF_UNIX); "
                "s.bind(sys.argv[1]); s.listen(1); print('ready',flush=True); signal.pause()", str(first)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(worker.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=5))
                    self.assertEqual(worker.stdout.readline().strip(), 'ready')
                before = first.lstat()
                # Simulate abrupt Android process death: no guest cleanup runs.
                worker.kill()
                worker.communicate(timeout=5)
                self.assertTrue(stat.S_ISSOCK(first.lstat().st_mode))
                with self.assertRaisesRegex(runtime.AdmissionError, 'OWNED_DISPLAY_SOCKET_ALREADY_EXISTS'):
                    runtime.presentation_endpoint(root, 'a' * 32)
                second = runtime.presentation_endpoint(root, 'b' * 32)
                with socket.socket(socket.AF_UNIX) as restarted:
                    restarted.bind(str(second))
                    restarted.listen(1)
                    self.assertTrue(stat.S_ISSOCK(second.lstat().st_mode))
                    self.assertEqual(first.lstat(), before)
                    # A live endpoint with this session name is also refused;
                    # no connect probe or unlink touches an unknown listener.
                    with self.assertRaisesRegex(runtime.AdmissionError, 'OWNED_DISPLAY_SOCKET_ALREADY_EXISTS'):
                        runtime.presentation_endpoint(root, 'b' * 32)
                    restarted.setblocking(False)
                    with self.assertRaises(BlockingIOError):
                        restarted.accept()
                self.assertTrue(second.exists())
                self.assertEqual(first.lstat(), before)
            finally:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate(timeout=5)

    def test_guest_resource_reads_are_bounded_and_numeric_only(self):
        opened = mock.mock_open(read_data='Name: private\nVmRSS: 12345 kB\n')
        with mock.patch('io.open', opened), \
             mock.patch.object(runtime.resource, 'getrusage', side_effect=[
                 SimpleNamespace(ru_maxrss=23456), SimpleNamespace(ru_maxrss=34567)]):
            sample = runtime.guest_resource_sample()
        opened.assert_called_once()
        self.assertEqual(opened.call_args.args[0], Path('/proc/self/status'))
        opened().read.assert_called_once_with(16384)
        self.assertEqual(sample, {'rss_kib': 12345, 'peak_rss_kib': 23456,
            'children_peak_rss_kib': 34567, 'cgroup_current_bytes': None,
            'cgroup_max_bytes': None, 'cgroup_oom_kill_count': None})
        self.assertNotIn('private', json.dumps(sample))

    def test_guest_resource_unknown_wrong_types_and_bounds_do_not_fail(self):
        for value in (-1, True, 12.5, '123', 8 * 1024 * 1024 + 1, None):
            with self.subTest(value=value), \
                 mock.patch('io.open', side_effect=PermissionError('private details')), \
                 mock.patch.object(runtime.resource, 'getrusage', return_value=SimpleNamespace(ru_maxrss=value)):
                self.assertTrue(all(v is None for v in runtime.guest_resource_sample().values()))
        for text in ('VmRSS: ' + '9' * 5000 + ' kB\n', 'VmRSS: -1 kB\n', 'VmRSS: 0.5 kB\n', 'missing'):
            with mock.patch('io.open', mock.mock_open(read_data=text)), \
                 mock.patch.object(runtime.resource, 'getrusage', side_effect=OSError('private details')):
                sample = runtime.guest_resource_sample()
            self.assertTrue(all(v is None for v in sample.values()))

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

    def test_actual_context_applies_postgresql_arguments_before_owned_start(self):
        ctx=self.Context(SimpleNamespace(state=Path('/unused'),timeout_seconds=600,session_id='a'*32))
        original=['/opt/coh/pgsql/bin/postgres','-D','/private/profile/pgdata','-c','max_connections=80','-c','shared_buffers=32MB','-c','fsync=on']
        with mock.patch.object(runtime.base,'OwnedProcess') as constructor:
            child=ctx.start('postgres_native_combined',original)
            self.assertIs(child,constructor.return_value)
            label,argv,_,_=constructor.call_args.args
            self.assertEqual(label,'postgres_native_combined')
            self.assertIn('max_connections=72',argv);self.assertIn('shared_buffers=16MB',argv)
            self.assertIn('work_mem=1MB',argv);self.assertIn('maintenance_work_mem=16MB',argv)
            self.assertIn('fsync=on',argv);self.assertEqual(original[4],'max_connections=80')
            self.assertEqual(ctx.children,[child])

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

    def test_guest_resource_stage_events_are_session_bound_and_retained_bounded(self):
        args = SimpleNamespace(state=Path('/unused'), timeout_seconds=600, session_id='a' * 32)
        ctx = self.Context(args)
        sample = {'rss_kib': 100, 'peak_rss_kib': 200, 'children_peak_rss_kib': 300,
            'cgroup_current_bytes': None, 'cgroup_max_bytes': None, 'cgroup_oom_kill_count': None}
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.object(runtime, 'guest_resource_sample', return_value=sample):
            for i in range(20):
                ctx.stage('phase_' + str(i))
        resources = [json.loads(line) for line in output.getvalue().splitlines()
                     if json.loads(line).get('type') == 'guest_resources']
        self.assertEqual(len(resources), 40)
        self.assertEqual(len(ctx.guest_resource_samples), 32)
        self.assertEqual(resources[0]['boundary'], 'leaving')
        self.assertEqual(resources[0]['stage'], 'preflight')
        self.assertEqual(resources[1]['boundary'], 'entered')
        self.assertEqual(resources[1]['stage'], 'phase_0')
        self.assertTrue(all(row['session_id'] == 'a' * 32 for row in resources))
        self.assertTrue(all(set(row) == set(sample) | {'type', 'stage', 'boundary', 'session_id', 'time_utc'} for row in resources))
        self.assertNotIn('/unused', output.getvalue())

    def test_guest_resource_event_is_flushed_before_abrupt_guest_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = textwrap.dedent("""\
                import importlib.util,os,signal,sys
                from pathlib import Path
                from types import SimpleNamespace
                spec=importlib.util.spec_from_file_location('runtime_abrupt_exit',sys.argv[1])
                runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
                runtime.load_guest_modules(Path(sys.argv[2]))
                Context,_=runtime.runtime_classes()
                ctx=Context(SimpleNamespace(state=Path(sys.argv[3]),timeout_seconds=30,session_id='a'*32))
                ctx.stage('server_only_input_admission')
                os.kill(os.getpid(),signal.SIGKILL)
                """)
            child = subprocess.run([sys.executable, '-c', script, str(HERE / 'server_runtime.py'),
                str(Path(runtime.startup.__file__).parent), temporary],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, -9)
            values = [json.loads(line) for line in child.stdout.splitlines()]
            self.assertEqual(values[-1]['type'], 'guest_resources')
            self.assertEqual(values[-1]['stage'], 'server_only_input_admission')
            self.assertEqual(values[-1]['boundary'], 'entered')
            self.assertEqual(values[-1]['session_id'], 'a' * 32)
            self.assertTrue(type(values[-1]['rss_kib']) is int and values[-1]['rss_kib'] > 0)
            self.assertIsNone(values[-1]['cgroup_oom_kill_count'])
            self.assertNotIn(temporary, child.stdout)

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
            owner.root = Path(temporary)
            (owner.root / 'runtime').mkdir(mode=0o700)
            owner.args = SimpleNamespace(session_id='a' * 32)
            owner.ctx = SimpleNamespace(stage=lambda name: None, report={})
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

    def test_geometry_preparation_refuses_resident_server_processes(self):
        for pg, display, wine in ((object(), None, False), (None, object(), False), (None, None, True)):
            owner = SimpleNamespace(pg=pg, xserver=display, wine_started=wine)
            with self.assertRaisesRegex(runtime.AdmissionError, 'GEOMETRY_PREPARATION_REQUIRES_STOPPED_SERVERS'):
                runtime.prepare_geometry_before_servers(owner)

    def test_initialize_prepares_geometry_before_postgresql(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(assets=root, wine=root/'wine', wineserver=root/'wineserver',
                game_data=root/'data', import_generation='generation-'+'b'*32)
            ctx = self.Context(SimpleNamespace(state=root, timeout_seconds=600, session_id='a'*32))
            owner = self.Owner.__new__(self.Owner)
            owner.args=args; owner.ctx=ctx; owner.root=root
            owner.pg=None; owner.xserver=None; owner.wine_started=False
            order=[]
            def geometry(actual):
                self.assertIs(actual, owner)
                self.assertIsNone(owner.pg)
                self.assertFalse(owner.wine_started)
                order.append('geometry')
            def postgres():
                order.append('postgres')
                owner.pg=object()
            owner.server=SimpleNamespace(initialize=postgres, destination={'map_port':7001})
            with mock.patch.object(runtime, 'admit_local_port'), \
                 mock.patch.object(runtime.platform, 'machine', return_value='aarch64'), \
                 mock.patch.object(runtime.os, 'geteuid', return_value=1000), \
                 mock.patch.object(runtime.startup, 'verify_assets', return_value={}), \
                 mock.patch.object(runtime.base, 'arm64_elf'), \
                 mock.patch.object(runtime.startup, 'import_identity', return_value={'generation':args.import_generation}), \
                 mock.patch.object(runtime.startup, 'prepare_worktree', return_value=(root,{})), \
                 mock.patch.object(runtime.character.avatar, 'install'), \
                 mock.patch.object(runtime.character.world, 'install'), \
                 mock.patch.object(runtime, 'prepare_geometry_before_servers', side_effect=geometry), \
                 contextlib.redirect_stdout(io.StringIO()):
                owner.initialize()
            self.assertEqual(order, ['geometry','postgres'])

    def test_owned_geometry_child_original_cold_warm_and_tamper_oracle(self):
        # Synthetic selected GEO bytes exercise the unchanged original install,
        # ZIP, digest, immutable-output and cache-receipt functions. Only fixture
        # metadata pins differ; this does not qualify original native geometry.
        import atlas_beacon_package as beacons
        import client_visual_assets as visual
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); assets=root/'assets';assets.mkdir()
            work=root/'work';work.mkdir();(work/'data').mkdir()
            (work/'data/object_library/fixture').mkdir(parents=True)
            (work/'client-work.json').write_text('{"fixture":"protected-worktree"}')
            state=root/'state';state.mkdir()
            (assets/'atlas-beacons.zip').write_bytes(b'fixture presence marker')
            payloads={'data/object_library/fixture/g%d.geo'%i:('fixture geometry %d'%i).encode()
                      for i in range(beacons.REQUIRED_GEOS)}
            files={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                   for name,raw in payloads.items()}
            document={'files':files}
            (assets/visual.MANIFEST).write_text(json.dumps(document,sort_keys=True,separators=(',',':')))
            with zipfile.ZipFile(assets/visual.ARCHIVE,'w',zipfile.ZIP_DEFLATED) as archive:
                for name,raw in payloads.items():
                    entry=zipfile.ZipInfo(name);entry.compress_type=zipfile.ZIP_DEFLATED
                    entry.external_attr=(0o100444)<<16
                    archive.writestr(entry,raw)
            geometry_sha=hashlib.sha256(beacons.canonical(files)).hexdigest()
            harness=root/'worker_oracle.py'
            harness.write_text(textwrap.dedent("""
                import importlib.util,sys,json,hashlib
                from pathlib import Path
                spec=importlib.util.spec_from_file_location('runtime_oracle',sys.argv[1])
                runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
                runtime.load_guest_modules(Path(sys.argv[2]))
                import atlas_beacon_package as beacons, client_visual_assets as visual
                assets=Path(sys.argv[3]);document=json.loads((assets/visual.MANIFEST).read_text())
                beacons.REQUIRED_GEOMETRY_SHA256=hashlib.sha256(beacons.canonical(document['files'])).hexdigest()
                visual.ARCHIVE_BYTES=(assets/visual.ARCHIVE).stat().st_size
                visual.FILE_COUNT=len(document['files'])
                visual.package=lambda path:document
                runtime.load_guest_modules=lambda path:None
                sys.exit(runtime.geometry_worker_main(sys.argv[4:]))
            """))
            args=SimpleNamespace(assets=assets,state=state,session_id='a'*32,
                                 import_generation='generation-'+'b'*32)
            ctx=self.Context(SimpleNamespace(state=state,timeout_seconds=600,session_id=args.session_id))
            owner=SimpleNamespace(pg=None,xserver=None,wine_started=False,args=args,
                                  work=work,ctx=ctx,base_env=os.environ.copy())
            run_original=ctx.run
            def run(label,argv,**kwargs):
                self.assertEqual(label,'isolated-required-geometry')
                self.assertIn('--geometry-worker',argv)
                self.assertIsNone(owner.pg);self.assertFalse(owner.wine_started)
                command=[sys.executable,str(harness),str(HERE/'server_runtime.py'),
                         str(Path(runtime.startup.__file__).parent),str(assets),*argv[2:]]
                return run_original(label,command,**kwargs)
            ctx.run=run
            with mock.patch.object(beacons,'REQUIRED_GEOMETRY_SHA256',geometry_sha), \
                 mock.patch.object(visual,'ARCHIVE_BYTES',(assets/visual.ARCHIVE).stat().st_size), \
                 mock.patch.object(visual,'FILE_COUNT',len(files)), \
                 mock.patch.object(visual,'package',side_effect=AssertionError('Parent must not load full metadata')), \
                 contextlib.redirect_stdout(io.StringIO()):
                runtime.prepare_geometry_before_servers(owner)
                first=ctx.report['geometry_preparation'].copy()
                self.assertTrue(first['worker_used']);self.assertTrue(first['worker_reaped'])
                self.assertEqual(first['input_files_checked'],beacons.REQUIRED_GEOS)
                self.assertEqual(len(ctx.children),1)
                self.assertEqual(beacons.validate_required_geometry(work,ctx)['required_geometry_sha256'],geometry_sha)
                for child in ctx.children:
                    self.assertIsNotNone(child.process.poll())
                    self.assertFalse(child.reader.is_alive());self.assertFalse(child.writer.is_alive())
                runtime.prepare_geometry_before_servers(owner)
                self.assertFalse(ctx.report['geometry_preparation']['worker_used'])
                self.assertEqual(len(ctx.children),1)
                target=work/next(iter(files));target.chmod(0o600);target.write_bytes(b'tampered')
                with self.assertRaises((runtime.AdmissionError,runtime.base.DiagnosticError)):
                    runtime.prepare_geometry_before_servers(owner)
                self.assertEqual(target.read_bytes(),b'tampered')
                self.assertTrue(all(child.process.poll() is not None for child in ctx.children))

    def test_stop_during_owned_geometry_worker_reaps_real_child(self):
        import atlas_beacon_package as beacons
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'atlas-beacons.zip').write_bytes(b'presence')
            args=SimpleNamespace(assets=root,state=root,session_id='a'*32,
                                 import_generation='generation-'+'b'*32)
            ctx=self.Context(SimpleNamespace(state=root,timeout_seconds=600,session_id=args.session_id))
            owner=SimpleNamespace(pg=None,xserver=None,wine_started=False,args=args,
                                  work=root,ctx=ctx,base_env=os.environ.copy())
            original=ctx.run
            def run(label,argv,**kwargs):
                return original(label,[sys.executable,'-c','import time; time.sleep(30)'],**kwargs)
            ctx.run=run
            timer=threading.Timer(.15,lambda:setattr(ctx,'cancel_requested',True))
            with mock.patch.object(beacons,'validate_required_geometry',side_effect=ValueError('cold fixture')), \
                 contextlib.redirect_stdout(io.StringIO()):
                timer.start()
                try:
                    with self.assertRaises(runtime.base.Cancelled):
                        runtime.prepare_geometry_before_servers(owner)
                finally:
                    timer.cancel();timer.join()
            self.assertEqual(len(ctx.children),1)
            child=ctx.children[0]
            self.assertIsNotNone(child.process.poll())
            self.assertFalse(child.reader.is_alive());self.assertFalse(child.writer.is_alive())
            self.assertNotIn('geometry_preparation',ctx.report)
            self.assertIsNone(owner.pg);self.assertFalse(owner.wine_started)

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
