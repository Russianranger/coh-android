#!/usr/bin/env python3
"""Host admission/lifecycle contract tests; no server-interoperability claim."""
import contextlib
import importlib.util
import io
import inspect
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

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
                status = runtime.main(['--guest-modules', str(directory / 'missing'),
                    '--assets', str(directory / 'missing'),
                    '--session-id', 'a' * 32, '--import-generation', 'generation-' + 'b' * 32])
            lines = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(status, 1)
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]['failure_code'], 'MISSING_PRIVATE_INPUT')
            self.assertNotIn(str(directory), output.getvalue())


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
