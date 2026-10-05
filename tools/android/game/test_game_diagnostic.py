"""Focused lifecycle boundaries for the hosted game orchestration."""
import errno
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest
import game_map_progress as progress


class FixedInputTests(unittest.TestCase):
    def diagnostic(self, root):
        payloads = {'data/server/db/servers.cfg': 'private configuration',
                    'data/server/db/nested/loadBalance.cfg': 'load balance',
                    'data/defs/entities.def': 'schema', 'data/attributes/names.def': 'attributes'}
        for name, payload in payloads.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload)
        value = object.__new__(guest.GameDiagnostic)
        value.runtime = root
        value.fixed_schema_paths = {'data/defs/entities.def', 'data/attributes/names.def'}
        value.ctx = SimpleNamespace(check=Mock())
        value.game = {'fixed_inputs': {'checks': []}}
        value.bind_fixed_inputs()
        return value

    def test_baseline_tracks_schema_and_complete_db_tree_but_allows_generated_bins(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.diagnostic(root)
            baseline = diagnostic.game['fixed_inputs']['baseline']
            self.assertEqual(baseline['file_count'], 4)
            self.assertEqual(baseline['directories'], ['data/server/db', 'data/server/db/nested'])
            self.assertEqual(baseline['inventory_sha256'], hashlib.sha256(json.dumps(
                {key: baseline[key] for key in ('files', 'directories')},
                sort_keys=True, separators=(',', ':')).encode()).hexdigest())
            (root / 'data/bin').mkdir()
            (root / 'data/bin/generated.bin').write_text('legitimate MapServer cache')
            for phase in ('before-first', 'after-first-save', 'before-restart', 'after-second-save'):
                diagnostic.check_fixed_inputs(phase)
            self.assertEqual([item['phase'] for item in diagnostic.game['fixed_inputs']['checks']],
                             ['before-first', 'after-first-save', 'before-restart', 'after-second-save'])

    def test_mutation_replacement_links_and_restored_bytes_are_rejected(self):
        def rewrite_restore(path):
            before, original = path.stat(), path.read_bytes()
            time.sleep(.002)
            path.write_bytes(b'changed')
            path.write_bytes(original)
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))

        def replace(path):
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.replace(replacement, path)

        mutations = {
            'contents': lambda root: (root / 'data/defs/entities.def').write_text('changed'),
            'add': lambda root: (root / 'data/server/db/WeeklyTF.cfg').write_text('new'),
            'delete': lambda root: (root / 'data/server/db/nested/loadBalance.cfg').unlink(),
            'replace': lambda root: replace(root / 'data/defs/entities.def'),
            'rewrite-restored': lambda root: rewrite_restore(root / 'data/defs/entities.def'),
            'directory-add': lambda root: (root / 'data/server/db/extra').mkdir(),
            'symlink': lambda root: (root / 'data/server/db/linked').symlink_to(root / 'data/defs/entities.def'),
            'hardlink': lambda root: os.link(root / 'data/defs/entities.def', root / 'second-link'),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                diagnostic = self.diagnostic(root)
                diagnostic.check_fixed_inputs('before-first')
                mutate(root)
                with self.assertRaises((guest.base.DiagnosticError, FileNotFoundError)):
                    diagnostic.check_fixed_inputs('after-first-save')
                self.assertEqual(len(diagnostic.game['fixed_inputs']['checks']), 1)

    def test_baseline_cannot_be_rebound_and_checks_have_one_fixed_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = self.diagnostic(Path(temporary))
            with patch.object(guest, 'fixed_input_snapshot', side_effect=AssertionError('must fail before hashing')):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'already bound'):
                    diagnostic.bind_fixed_inputs()
                for phase in ('after-first-save', 'before-restart', 'after-second-save', 'unknown'):
                    with self.subTest(phase=phase), self.assertRaisesRegex(guest.base.DiagnosticError, 'out of order'):
                        diagnostic.check_fixed_inputs(phase)
            for phase in ('before-first', 'after-first-save', 'before-restart', 'after-second-save'):
                diagnostic.check_fixed_inputs(phase)
                with patch.object(guest, 'fixed_input_snapshot', side_effect=AssertionError('must fail before hashing')):
                    with self.assertRaisesRegex(guest.base.DiagnosticError, 'out of order'):
                        diagnostic.check_fixed_inputs(phase)

    def test_casefold_collisions_in_schema_configuration_union_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.diagnostic(root)
            path = root / 'data/server/db/Servers.cfg'
            path.write_text('colliding schema input')
            diagnostic.fixed_schema_paths.add(path.relative_to(root).as_posix())
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Case-conflicting'):
                diagnostic.check_fixed_inputs('before-first')

    def test_no_follow_parents_and_resource_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.diagnostic(root)
            for constant, limit in (('FIXED_INPUT_FILE_LIMIT', 3), ('FIXED_INPUT_BYTE_LIMIT', 1),
                                    ('FIXED_INPUT_DIRECTORY_LIMIT', 1)):
                with self.subTest(constant=constant), patch.object(guest, constant, limit):
                    with self.assertRaisesRegex(guest.base.DiagnosticError, 'exceeded bound'):
                        diagnostic.check_fixed_inputs('before-first')
            (root / 'data/defs').rename(root / 'moved')
            (root / 'data/defs').symlink_to(root / 'moved', target_is_directory=True)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Linked'):
                diagnostic.check_fixed_inputs('before-first')

    def test_acknowledgement_requires_one_complete_exact_line_in_owned_output(self):
        child = SimpleNamespace(overflow=False, text=Mock())
        ack = guest.dbserver.FIXED_INPUTS_ACK
        for output in ('unrelated\n', ack, ack + '\r'):
            child.text.return_value = output
            self.assertFalse(guest.fixed_inputs_acknowledgement(child))
        child.text.return_value = 'prior diagnostics\n' + ack + '\r\npartial next line'
        self.assertEqual(guest.fixed_inputs_acknowledgement(child),
                         {'requested': True, 'startup_acknowledgement': ack})
        for output in (ack + '\n' + ack + '\n', 'prefix ' + ack + '\n', ack + '.\n'):
            child.text.return_value = output
            with self.assertRaises(guest.base.DiagnosticError):
                guest.fixed_inputs_acknowledgement(child)
        child.overflow = True
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'overflowed'):
            guest.fixed_inputs_acknowledgement(child)

    def test_service_launch_scopes_mode_to_db_and_requires_ack_before_atlas(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = object.__new__(guest.GameDiagnostic)
            diagnostic.runtime = Path(temporary)
            diagnostic.ctx = SimpleNamespace(stage=Mock(), passed=Mock())
            diagnostic.wine_env = {'WINEPREFIX': '/private/wine'}
            diagnostic.loopback_enabled = False
            diagnostic.check_fixed_inputs = Mock()
            diagnostic.dispatch_paths, diagnostic.dispatch_stages = {}, {}
            diagnostic.schema = {'expected_tables': {}}
            diagnostic.schema_snapshot = Mock(return_value={'table_count': 99})
            diagnostic.game = {'dispatch_progress': {'phases': {}}, 'phases': []}
            child = SimpleNamespace(overflow=False, text=lambda: guest.dbserver.FIXED_INPUTS_ACK + '\n')
            diagnostic.start_game = Mock(return_value=child)
            diagnostic.map_status = Mock(side_effect=[{'ready': False, 'not_started': True}, {'ready': True}])
            def wait(predicate, seconds, label):
                if label == 'DbServer schema and local listener':
                    return True
                if label == 'DbServer fixed-input activation acknowledgement':
                    self.assertEqual(diagnostic.start_game.call_count, 1)
                return predicate()
            diagnostic.wait = wait
            with patch.object(guest, 'check_game_port'), \
                    patch.object(guest.hang_evidence, 'read_dispatch_record', return_value={'loop_count': 1}), \
                    patch.object(guest.evidence, 'map_ready_current', return_value=True):
                diagnostic.start_services('first')
            diagnostic.check_fixed_inputs.assert_called_once_with('before-first')
            calls = diagnostic.start_game.call_args_list
            self.assertEqual(calls[0].kwargs['env'][guest.dbserver.FIXED_INPUTS_ENV], '1')
            self.assertEqual(calls[1].kwargs, {})
            self.assertNotIn(guest.dbserver.FIXED_INPUTS_ENV, diagnostic.wine_env)
            self.assertEqual(diagnostic.game['phases'][0]['fixed_inputs']['startup_acknowledgement'],
                             guest.dbserver.FIXED_INPUTS_ACK)


class LoopbackProfileTests(unittest.TestCase):
    def package(self):
        manifest = json.loads((ROOT / 'docs/android-evidence/dbserver-package-36460867428.json').read_text())
        return {'dbserver_profile': 'loopback', 'files': copy.deepcopy(manifest['variants']['normal']['files']),
                'inputs': {'dbserver': {'run_id': 36460867428,
                    'repository_commit': manifest['repository_commit'],
                    'manifest_sha256': guest.dbserver.DEVICE_PACKAGE_MANIFEST, 'manifest': manifest}}}

    def endpoints(self):
        return guest.game_loopback_contract(self.package())['endpoints']

    def output(self, *, optional=False):
        endpoints = self.endpoints()
        return guest.dbserver.LOOPBACK_ACK + '\n' + ''.join(
            guest.dbserver.LOOPBACK_ENV + ' bind verified: protocol={protocol} address={address} port={port}\n'.format(**item)
            for item in reversed(endpoints['required'] + (endpoints['optional'] if optional else [])))

    def test_only_explicit_loopback_profile_accepts_exact_qualified_normal_donor(self):
        self.assertIsNone(guest.game_loopback_contract({}))
        self.assertIsNone(guest.game_loopback_contract({'dbserver_profile': 'accepted'}))
        contract = guest.game_loopback_contract(self.package())
        self.assertEqual(contract['metadata'], guest.dbserver.LOOPBACK_METADATA)
        self.assertEqual(len(contract['endpoints']['required']), 13)
        self.assertEqual(contract['endpoints']['optional'], [{'protocol': 'tcp', 'address': '127.0.0.1', 'port': 6992}])
        mutations = [lambda p: p.update(dbserver_profile='unknown'),
                     lambda p: p['inputs']['dbserver'].update(run_id=36451873322),
                     lambda p: p['inputs']['dbserver'].update(manifest_sha256='f' * 64),
                     lambda p: p['inputs']['dbserver'].update(repository_commit='f' * 40),
                     lambda p: p['inputs']['dbserver']['manifest']['variants']['normal'].update(postgresql_persistence_fixture=True),
                     lambda p: p['files']['DbServer.exe'].update(sha256='f' * 64),
                     lambda p: p['files']['CrashRpt.dll'].update(sha256='f' * 64),
                     lambda p: p['inputs']['dbserver']['manifest']['wine_build_input']['loopback_only'].update(android_execution_validated=True)]
        for mutate in mutations:
            package = self.package()
            mutate(package)
            with self.assertRaises(guest.base.DiagnosticError):
                guest.game_loopback_contract(package)

    def test_ack_waits_for_complete_mandatory_records_and_allows_only_known_optional(self):
        child = SimpleNamespace(overflow=False, text=Mock())
        output = self.output()
        lines = output.splitlines(keepends=True)
        for pending in ('', guest.dbserver.LOOPBACK_ACK, ''.join(lines[:-1]), output[:-1]):
            child.text.return_value = pending
            self.assertFalse(guest.loopback_acknowledgement(child, self.endpoints()))
        for optional in (False, True):
            child.text.return_value = self.output(optional=optional) + 'partial next diagnostic'
            receipt = guest.loopback_acknowledgement(child, self.endpoints())
            self.assertEqual(len(receipt['endpoints']), 13 + optional)
            self.assertEqual(receipt['startup_acknowledgement'], guest.dbserver.LOOPBACK_ACK)

    def test_ack_refuses_duplicates_unknown_wildcard_and_malformed_records_without_waiting(self):
        output = self.output()
        invalid = (output + output.splitlines()[1] + '\n', output + guest.dbserver.LOOPBACK_ACK + '\n',
                   output.replace('address=127.0.0.1', 'address=0.0.0.0', 1),
                   output.replace('port=7000', 'port=65535'), output.replace('port=7000', 'port=70000'),
                   output.replace('protocol=udp', 'protocol=tcp'), 'prefix ' + output,
                   output.replace('bind verified:', 'bind failed:', 1))
        child = SimpleNamespace(overflow=False, text=Mock())
        for value in invalid:
            child.text.return_value = value
            with self.subTest(output=value), self.assertRaises(guest.base.DiagnosticError):
                guest.loopback_acknowledgement(child, self.endpoints())
        child.overflow = True
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'overflowed'):
            guest.loopback_acknowledgement(child, self.endpoints())

    def test_partial_db_startup_refuses_assertion_listener_before_required_binds_complete(self):
        # Replay the 0.13.12 THORHERO reopen order from the physical report:
        # SQL connected, then native SuperAssert's listener bound TCP52015.
        # This is a secondary crash signal, never additional readiness evidence.
        prefix = guest.dbserver.LOOPBACK_ACK + '\r\n' + ''.join(
            guest.dbserver.LOOPBACK_ENV +
            ' bind verified: protocol=tcp address=127.0.0.1 port={}\r\n'.format(port)
            for port in (6989, 6997, 6971, 6996, 6992))
        child = SimpleNamespace(overflow=False, text=Mock(return_value=prefix))
        self.assertFalse(guest.loopback_acknowledgement(child, self.endpoints()))
        assertion = (guest.dbserver.LOOPBACK_ENV +
                     ' bind verified: protocol=tcp address=127.0.0.1 port=52015')
        # An incomplete read remains pending until the actual record completes.
        child.text.return_value = prefix + assertion
        self.assertFalse(guest.loopback_acknowledgement(child, self.endpoints()))
        child.text.return_value += '\r\n'
        with self.assertRaisesRegex(guest.base.DiagnosticError,
                                    'Unexpected or duplicate game listener evidence'):
            guest.loopback_acknowledgement(child, self.endpoints())

    def test_launch_environment_cannot_enable_mapserver_or_legacy_dbserver(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.wine_env = {'WINEPREFIX': '/private/wine', guest.dbserver.LOOPBACK_ENV: 'inherited'}
        diagnostic.runtime = Path('/private/game')
        diagnostic.args = SimpleNamespace(wine=Path('/wine'))
        diagnostic.ctx = SimpleNamespace(start=Mock())
        diagnostic.services = []
        for enabled, executable in ((False, 'DbServer.exe'), (True, 'DbServer.exe'),
                                    (True, 'MapServer.exe'), (True, 'TestClientCreate.exe')):
            diagnostic.loopback_enabled = enabled
            for supplied in (None, {**diagnostic.wine_env, guest.dbserver.LOOPBACK_ENV: '1'}):
                with self.subTest(enabled=enabled, executable=executable, supplied=supplied):
                    diagnostic.start_game('owned', executable, [], env=supplied)
                    environment = diagnostic.ctx.start.call_args.kwargs['env']
                    self.assertEqual(environment.get(guest.dbserver.LOOPBACK_ENV),
                                     '1' if enabled and executable == 'DbServer.exe' else None)
                    self.assertEqual(environment['WINEPREFIX'], '/private/wine')
        self.assertEqual(diagnostic.wine_env[guest.dbserver.LOOPBACK_ENV], 'inherited')

    def test_both_service_starts_wait_after_dispatch_and_before_atlas_then_record_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            diagnostic = object.__new__(guest.GameDiagnostic)
            diagnostic.runtime = Path(temporary)
            diagnostic.ctx = SimpleNamespace(stage=Mock(), passed=Mock())
            diagnostic.wine_env = {'WINEPREFIX': '/private/wine'}
            diagnostic.loopback_enabled = True
            diagnostic.loopback_contract = guest.game_loopback_contract(self.package())
            diagnostic.check_fixed_inputs = Mock()
            diagnostic.dispatch_paths, diagnostic.dispatch_stages = {}, {}
            diagnostic.schema = {'expected_tables': {}}
            diagnostic.schema_snapshot = Mock(return_value={'table_count': 99})
            diagnostic.game = {'dispatch_progress': {'phases': {}}, 'phases': []}
            child = SimpleNamespace(overflow=False, text=lambda: guest.dbserver.FIXED_INPUTS_ACK + '\n' + self.output())
            diagnostic.start_game = Mock(return_value=child)
            diagnostic.map_status = Mock(side_effect=[{'ready': False, 'not_started': True}, {'ready': True}] * 2)
            waits = []
            def wait(predicate, seconds, label):
                waits.append(label)
                if label == 'DbServer schema and local listener':
                    return True
                if label == 'DbServer loopback listener acknowledgements':
                    self.assertIn('DbServer main-thread dispatch publication', waits)
                    self.assertEqual(diagnostic.start_game.call_count % 2, 1, 'Atlas must not start before verified binds')
                result = predicate()
                self.assertTrue(result)
                return result
            diagnostic.wait = wait
            with patch.object(guest, 'check_game_port'), \
                    patch.object(guest.hang_evidence, 'read_dispatch_record', return_value={'loop_count': 1}), \
                    patch.object(guest.evidence, 'map_ready_current', return_value=True):
                diagnostic.start_services('first')
                diagnostic.start_services('restart')
            self.assertEqual(waits.count('DbServer loopback listener acknowledgements'), 2)
            for number, call in enumerate(diagnostic.start_game.call_args_list):
                if number % 2 == 0:
                    self.assertEqual(call.kwargs['env'][guest.dbserver.LOOPBACK_ENV], '1')
                    self.assertEqual(call.kwargs['env'][guest.dbserver.FIXED_INPUTS_ENV], '1')
                else:
                    self.assertEqual(call.args[1], 'MapServer.exe')
                    self.assertEqual(call.kwargs, {})
            self.assertNotIn(guest.dbserver.LOOPBACK_ENV, diagnostic.wine_env)
            self.assertEqual([phase['phase'] for phase in diagnostic.game['phases']],
                             ['first_services_ready', 'restart_services_ready'])
            for phase in diagnostic.game['phases']:
                self.assertEqual(phase['loopback_only']['endpoints'], self.endpoints()['required'])

    def test_clean_logs_rechecks_late_duplicates_and_does_not_claim_mapserver_policy(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.loopback_enabled = True
        diagnostic.loopback_contract = guest.game_loopback_contract(self.package())
        database = SimpleNamespace(label='first-dbserver', text=Mock(return_value=self.output()))
        atlas = SimpleNamespace(label='first-atlas', text=lambda: 'normal MapServer diagnostics\n')
        diagnostic.services = [database, atlas]
        diagnostic.ctx = SimpleNamespace(log_paths=lambda: [], secrets=[])
        diagnostic.completed_logout = False
        diagnostic.clean_logs()
        database.text.return_value = self.output(optional=True)
        diagnostic.clean_logs()
        database.text.return_value += guest.dbserver.LOOPBACK_ACK + '\n'
        with self.assertRaises(guest.base.DiagnosticError):
            diagnostic.clean_logs()


class GameListenerProfileTests(unittest.TestCase):
    def test_only_selected_atlas_and_clients_inherit_game_policy(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.wine_env = {'WINEPREFIX': '/private/wine', guest.dbserver.LOOPBACK_ENV: 'inherited',
                               guest.evidence.GAME_LOOPBACK_ENV: 'inherited'}
        diagnostic.loopback_enabled = True
        for enabled in (False, True):
            diagnostic.game_listener_enabled = enabled
            for executable in guest.EXES:
                with self.subTest(enabled=enabled, executable=executable):
                    environment = diagnostic.game_environment(executable)
                    self.assertEqual(environment.get(guest.dbserver.LOOPBACK_ENV),
                                     '1' if executable == 'DbServer.exe' else None)
                    self.assertEqual(environment.get(guest.evidence.GAME_LOOPBACK_ENV),
                        '1' if enabled and executable in ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe') else None)
                    self.assertEqual(environment['WINEPREFIX'], '/private/wine')
        self.assertEqual(diagnostic.wine_env[guest.evidence.GAME_LOOPBACK_ENV], 'inherited')

    def test_game_source_metadata_is_disabled_by_default_and_keeps_namespace_required(self):
        self.assertIsNone(guest.game_listener_contract({}))
        for package in ({'game_listener_profile': 'unknown'},
                        {'game_listener_profile': 'loopback'},
                        {'inputs': {'loopback_game': {}}}):
            with self.subTest(package=package), self.assertRaises(guest.base.DiagnosticError):
                guest.game_listener_contract(package)

    def test_live_observation_checks_actual_client_console_before_recording(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.game_listener_enabled = True
        diagnostic.game = {'client_listener_observations': {}}
        diagnostic.wait = lambda predicate, *args, **kwargs: predicate()
        text = guest.evidence.GAME_LOOPBACK_ACK + '\n' + ''.join(
            f'{guest.evidence.GAME_LOOPBACK_ENV} bind verified: protocol=udp address=127.0.0.1 port={port}\n'
            for port in (41001, 41002))
        session = SimpleNamespace(console=lambda: text)
        diagnostic.observe_client_listeners(session, 'first')
        self.assertEqual(len(diagnostic.game['client_listener_observations']['first']['endpoints']), 2)
        session.console = lambda: text.replace('127.0.0.1', '0.0.0.0')
        with self.assertRaises(guest.base.DiagnosticError):
            diagnostic.observe_client_listeners(session, 'second')
        self.assertNotIn('second', diagnostic.game['client_listener_observations'])


@unittest.skipUnless(sys.platform.startswith('linux'), 'Wine guest uses native Linux socket semantics')
class GamePortTests(unittest.TestCase):
    def test_tcp_preflight_accepts_closed_wine_style_connection_in_time_wait(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('0.0.0.0', 0))
            port = listener.getsockname()[1]
            listener.listen(1)
            listener.settimeout(2)
            with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    # The server closes first, leaving its local port in
                    # TIME_WAIT after both endpoints finish their FIN exchange.
                    connection.shutdown(socket.SHUT_WR)
                    self.assertEqual(client.recv(1), b'')
                    client.shutdown(socket.SHUT_WR)
                    self.assertEqual(connection.recv(1), b'')
        with socket.socket() as previous_preflight:
            with self.assertRaises(OSError) as busy:
                previous_preflight.bind(('0.0.0.0', port))
            self.assertEqual(busy.exception.errno, errno.EADDRINUSE)
        guest.check_game_port(port, socket.SOCK_STREAM)

    def test_tcp_preflight_rejects_live_listeners_with_port_context(self):
        for address in ('0.0.0.0', '127.0.0.1'):
            for reuse in (False, True):
                with self.subTest(address=address, reuse=reuse), socket.socket() as listener:
                    if reuse:
                        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind((address, 0))
                    port = listener.getsockname()[1]
                    listener.listen(1)
                    with self.assertRaisesRegex(guest.base.DiagnosticError, f'TCP port {port} unavailable'):
                        guest.check_game_port(port, socket.SOCK_STREAM)

    def test_udp_preflight_rejects_live_bound_sockets_with_port_context(self):
        for address in ('0.0.0.0', '127.0.0.1'):
            for reuse in (False, True):
                with self.subTest(address=address, reuse=reuse), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as owner:
                    if reuse:
                        owner.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    owner.bind((address, 0))
                    port = owner.getsockname()[1]
                    with self.assertRaisesRegex(guest.base.DiagnosticError, f'UDP port {port} unavailable'):
                        guest.check_game_port(port, socket.SOCK_DGRAM)


class GameOrchestrationTests(unittest.TestCase):
    def session(self, root):
        value = object.__new__(guest.BridgeSession)
        value.root = root
        value.commands = value.acknowledged_commands = value.last_event_count = 0
        value.stopped = value.proof_complete = False
        value.ctx = SimpleNamespace(check=Mock(), record=Mock())
        value.child = SimpleNamespace(process=Mock(returncode=0), reader=Mock(), writer=Mock())
        value.child.process.poll.return_value = 0
        value.child.reader.is_alive.return_value = False
        value.child.writer.is_alive.return_value = False
        return value

    def ready(self):
        return {'format': 1, 'child_pid': 42, 'transport_pid': 42, 'console_attached': True,
                'pipe_pid_verified': True, 'protocol_pid_verified': True, 'initial_snapshot': True,
                'version_requests': 1, 'buffer_rows_limit': 16384,
                'capture_byte_limit': guest.CONSOLE_LIMIT, 'event_byte_limit': guest.EVENT_LIMIT}

    def test_final_capture_requires_child_exit_pipe_disconnect_and_completed_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'ready.json').write_text(json.dumps(self.ready()))
            (root / 'events.jsonl').write_text('\n'.join([]) + '\n')
            event = {'sequence': 1, 'kind': 'PID', 'value': '42', 'raw': 'PID: 42', 'elapsed_ms': 0}
            (root / 'events.jsonl').write_text(json.dumps(event) + '\n')
            (root / 'console.txt').write_text('bounded final console')
            result = {'child_pid': 42, 'child_exit_code': 0, 'error': None, 'final_snapshot': True,
                      'pipe_framing_complete': True, 'pipe_disconnected': True, 'version_requests': 1,
                      'command_count': 0, 'event_count': 1, 'capture_byte_limit': guest.CONSOLE_LIMIT,
                      'event_byte_limit': guest.EVENT_LIMIT}
            for key, wrong in (('pipe_disconnected', False), ('child_exit_code', None),
                               ('final_snapshot', False), ('event_count', 2)):
                with self.subTest(key=key):
                    session = self.session(root)
                    session.proof_complete = True
                    (root / 'result.json').write_text(json.dumps({**result, key: wrong}))
                    with self.assertRaises(guest.base.DiagnosticError):
                        session.stop()
            session = self.session(root)
            (root / 'result.json').write_text(json.dumps(result))
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'completed save proof'):
                session.stop()
            session.proof_complete = True
            self.assertTrue(session.stop()['proof_completed_before_stop'])

    def test_atomic_command_requires_matching_acknowledgement_before_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for response in ('CMD influence 12345', 'CMD other'):
                session = self.session(root)
                session.check = Mock()
                session.ready = Mock(return_value=self.ready())
                record = {'kind': 'Command', 'command_sequence': 1, 'value': response}
                session.events = Mock(return_value=[record])
                session.diagnostic = SimpleNamespace(wait=lambda predicate, *_a, **_k: predicate())
                if response.endswith('other'):
                    with self.assertRaisesRegex(guest.base.DiagnosticError, 'different command'):
                        session.send('CMD influence 12345')
                    self.assertEqual(session.acknowledged_commands, 0)
                else:
                    self.assertEqual(session.send(response), 1)
                    self.assertEqual((root / 'command-000001.txt').read_bytes(), response.encode())
                    self.assertEqual(session.acknowledged_commands, 1)
                (root / 'command-000001.txt').unlink()

    def test_events_ignore_current_partial_record_but_reject_reordered_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session = self.session(root)
            event = {'sequence': 1, 'kind': 'PID', 'value': '42', 'raw': 'PID: 42', 'elapsed_ms': 0}
            path = root / 'events.jsonl'
            path.write_text(json.dumps(event) + '\n{"sequence":')
            self.assertEqual(session.events(), [event])
            path.write_text('')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'truncated'):
                session.events()
            path.write_text(json.dumps({**event, 'sequence': 2}) + '\n')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'reordered'):
                session.events()

    def test_prior_expected_logout_does_not_hide_failure_in_new_active_client(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.completed_logout = True
        diagnostic.services = [SimpleNamespace(text=lambda: 'Fatal Error: Booted back to login screen\n')]
        diagnostic.ctx = SimpleNamespace(log_paths=lambda: [], secrets=[])
        diagnostic.clean_logs()
        session = SimpleNamespace(console=lambda: 'Fatal Error: Booted back to login screen\n')
        with self.assertRaises(guest.base.DiagnosticError):
            diagnostic.clean_logs(session=session)
        diagnostic.clean_logs(session=session, allow_logout=True)
        session.console = lambda: 'Fatal Error: unexpected database failure\n'
        with self.assertRaises(guest.base.DiagnosticError):
            diagnostic.clean_logs(session=session, allow_logout=True)

    def test_legacy_resume_argument_refuses_whitespace_and_quote_changes(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        for name in ('TEST with space', 'TEST"quote', 'TEST\nnewline'):
            diagnostic.game = {'account': 'CohAccount', 'character': {'name': name}}
            with self.subTest(name=name), patch.object(guest, 'BridgeSession') as launch:
                with self.assertRaises(guest.base.DiagnosticError):
                    diagnostic.new_client('resume', resume=True)
                launch.assert_not_called()

    def test_capture_export_redacts_structured_values_and_partial_failure_without_private_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge = root / 'private-bridge'
            bridge.mkdir()
            (bridge / 'ready.json').write_text(json.dumps({'value': 'password=private-secret'}))
            (bridge / 'events.jsonl').write_text(json.dumps({'raw': 'Password=private-secret'}) + '\n{"partial":')
            (bridge / 'console.txt').write_text('driver Password=private-secret; diagnostic\n')
            (bridge / 'private-config.cfg').write_text('secret config')
            diagnostic = object.__new__(guest.GameDiagnostic)
            diagnostic.args = SimpleNamespace(state=root)
            diagnostic.ctx = SimpleNamespace(secrets=['private-secret'])
            diagnostic.sessions = [SimpleNamespace(label='create', root=bridge)]
            diagnostic.snapshots = {'first': {'identity': {'name': 'TEST1'}, 'login_count': 1, 'rows': {}}}
            diagnostic.game = {'sessions': {'first': {}}}
            diagnostic.export_captures()
            output = root / 'game-captures'
            self.assertEqual(set(p.name for p in output.iterdir()),
                             {'first-ready.json', 'first-events.jsonl', 'first-console.txt', 'first-snapshot.json'})
            for name, record in diagnostic.game['capture_files'].items():
                payload = (output / name).read_bytes()
                self.assertNotIn(b'private-secret', payload)
                self.assertEqual(record, {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
            self.assertEqual(json.loads((output / 'first-ready.json').read_text())['value'], 'password=[redacted]')
            self.assertEqual(len((output / 'first-events.jsonl').read_text().splitlines()), 1)
            self.assertEqual(diagnostic.game['sessions']['first']['events_sha256'],
                             diagnostic.game['capture_files']['first-events.jsonl']['sha256'])
            self.assertEqual(diagnostic.game['sessions']['first']['console_sha256'],
                             diagnostic.game['capture_files']['first-console.txt']['sha256'])
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'stale'):
                diagnostic.export_captures()

    def test_config_pins_loopback_fakeauth_and_disables_automatic_launchers(self):
        actual = guest.game_config('UseFakeAuth 0\nUseQueueServer 1\nSqlAllowDDL 1\nAdvertisedIp 8.8.8.8\n',
            'coh_test_123', 'Driver={PostgreSQL Unicode};Password=private-secret;')
        for line in ('UseFakeAuth 1', 'UseQueueServer 0', 'AdvertisedIp 127.0.0.1',
                     'DoNotLaunchBeaconMasterServer 1', 'DoNotLaunchMapServerTSR 1', 'AssertMode Exit'):
            self.assertIn(line + '\n', actual)
        self.assertNotIn('8.8.8.8', actual)

    def test_process_budget_is_bounded_without_dropping_prior_children(self):
        context = object.__new__(guest.GameContext)
        context.check = Mock()
        context.children = [object()] * guest.PROCESS_LIMIT
        with patch.object(guest.base, 'OwnedProcess') as spawn:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'count exceeded'):
                context.start('excess', ['true'], cleanup=True)
            spawn.assert_not_called()
        self.assertEqual(len(context.children), guest.PROCESS_LIMIT)

    def test_private_parent_cache_creates_each_directory_once_and_rejects_existing_intruder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            created = {root}
            parent = root / 'data' / 'defs'
            guest.create_private_parents(parent, root, created)
            with patch.object(Path, 'mkdir', side_effect=AssertionError('repeat mkdir')):
                guest.create_private_parents(parent, root, created)
            (root / 'unowned').mkdir()
            with self.assertRaises(FileExistsError):
                guest.create_private_parents(root / 'unowned', root, created)
            with self.assertRaises(guest.base.DiagnosticError):
                guest.create_private_parents(root.parent, root, created)

    def test_scandir_inventory_matches_exact_files_and_rejects_links_and_special_nodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'data').mkdir()
            (root / 'data' / 'one').write_text('one')
            (root / 'manifest.json').write_text('{}')
            check = Mock()
            self.assertEqual(guest.inventory_files(root, check), {'data/one', 'manifest.json'})
            self.assertTrue(check.called)
            (root / 'linked').symlink_to(root / 'data', target_is_directory=True)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Linked'):
                guest.inventory_files(root)
            (root / 'linked').unlink()
            os.mkfifo(root / 'pipe')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Nonregular'):
                guest.inventory_files(root)

    def service_diagnostic(self, root, *, output=b'Atlas startup\n'):
        diagnostic = object.__new__(guest.GameDiagnostic)
        runtime = root / 'runtime'
        runtime.mkdir()
        child = SimpleNamespace(label='first-atlas', output=output, overflow=False,
            text=lambda: output.decode('utf-8', errors='replace'), reader=Mock())
        child.reader.is_alive.return_value = False
        diagnostic.ctx = SimpleNamespace(children=[child], log_root=runtime, secrets=['private-secret'])
        diagnostic.args = SimpleNamespace(state=root)
        diagnostic.game = {}
        return diagnostic

    def test_service_export_keeps_full_owned_output_and_explicit_bounded_log_head_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.service_diagnostic(root, output=b'begin private-secret\n' + b'x' * 20000 + b'\nend\n')
            logs = diagnostic.ctx.log_root / 'logs'
            logs.mkdir()
            payload = b'START Password=private-secret;\n' + b'x' * (3 * guest.SERVICE_LOG_SEGMENT) + b'\nFINAL\n'
            (logs / 'atlas.log').write_bytes(payload)
            (diagnostic.ctx.log_root / 'servers.cfg').write_text('private-secret must not be exported')
            diagnostic.export_service_captures()
            exported = root / 'game-service-captures'
            manifest = json.loads((exported / 'manifest.json').read_text())
            self.assertEqual(manifest['format'], 1)
            self.assertEqual(set(manifest['files']), {'first-atlas-stdout.txt', 'log-001.txt'})
            stdout = (exported / 'first-atlas-stdout.txt').read_text()
            self.assertTrue(stdout.startswith('begin [redacted]'))
            self.assertTrue(stdout.endswith('end\n'))
            self.assertGreater(len(stdout), 16384, 'Export must retain more than report tail')
            log = (exported / 'log-001.txt').read_text()
            self.assertTrue(log.startswith('START Password=[redacted];'))
            self.assertTrue(log.endswith('FINAL\n'))
            self.assertIn('[diagnostic capture: middle omitted]', log)
            record = manifest['files']['log-001.txt']
            self.assertEqual(record['original_bytes'], len(payload))
            self.assertEqual(record['source_relative_path'], 'logs/atlas.log')
            self.assertTrue(record['truncated'])
            for name, digest in diagnostic.game['service_capture_files'].items():
                raw = (exported / name).read_bytes()
                self.assertNotIn(b'private-secret', raw)
                self.assertEqual(digest, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_service_export_refuses_linked_log_but_preserves_already_captured_owned_stdout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = self.service_diagnostic(root)
            (diagnostic.ctx.log_root / 'outside.log').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Linked service log'):
                diagnostic.export_service_captures()
            exported = root / 'game-service-captures'
            manifest = json.loads((exported / 'manifest.json').read_text())
            self.assertEqual(set(manifest['files']), {'first-atlas-stdout.txt'})
            self.assertIn('inspection_failure', manifest)
            self.assertEqual(set(diagnostic.game['service_capture_files']), {'first-atlas-stdout.txt', 'manifest.json'})

    def test_live_queries_keep_25_second_budget_and_startup_can_explicitly_use_90(self):
        diagnostic = object.__new__(guest.GameDiagnostic)
        diagnostic.health = Mock()
        diagnostic.query_count = 0
        diagnostic.runtime = Path('/private/runtime')
        diagnostic.run_windows = Mock(return_value=({'exit_code': 0}, 'status'))
        diagnostic.query(['-getstatus', '3', '42'], 'live')
        self.assertEqual(diagnostic.run_windows.call_args.kwargs['timeout'], 25)
        diagnostic.query(['-getstatus', '1', '1'], 'startup', timeout=90)
        self.assertEqual(diagnostic.run_windows.call_args.kwargs['timeout'], 90)


class MapProgressProfileTests(unittest.TestCase):
    def test_ordinary_guest_imports_and_runs_default_paths_without_progress_helper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in (ROOT / 'android/guest').glob('*.py'):
                if source.name != 'game_map_progress.py':
                    shutil.copyfile(source, root / source.name)
            shutil.copyfile(ROOT / 'docs/android-evidence/game-listeners-package-36510836956.json', root / 'package.json')
            code = '''
import json, sys, time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path.cwd()))
import game_device_diagnostic
import game_diagnostic as game
package = json.loads(Path('package.json').read_text())
assert game.mapserver_progress_contract(package) is None
assert game.game_listener_contract(package) == game.evidence.GAME_LOOPBACK_METADATA
diagnostic = object.__new__(game.GameDiagnostic)
diagnostic.wine_env = {game.MAP_PROGRESS_ENVIRONMENT: 'inherited'}
diagnostic.health = lambda: None
diagnostic.ctx = SimpleNamespace(deadline=time.monotonic() + 1)
diagnostic.begin_map_progress('first')
assert diagnostic.sample_map_progress('default', force=True) is None
assert diagnostic.wait(lambda: True, 1, 'normal readiness') is True
assert game.MAP_PROGRESS_ENVIRONMENT not in diagnostic.game_environment('MapServer.exe')
assert 'game_map_progress' not in sys.modules
'''
            result = subprocess.run([sys.executable, '-I', '-c', code], cwd=root,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

    def seal(self, package):
        donor = package['inputs']['mapserver_progress']
        manifest = donor['manifest']
        source = (json.dumps(manifest['build_input'], indent=2) + '\n').encode()
        manifest['files']['mapserver-progress-build-input.json'] = {
            'size': len(source), 'sha256': hashlib.sha256(source).hexdigest()}
        donor['manifest_sha256'] = hashlib.sha256((json.dumps(manifest, indent=2) + '\n').encode()).hexdigest()
        return package

    def package(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from prepare_mapserver_progress_source import expected_progress_receipt
        package = json.loads((ROOT / 'docs/android-evidence/game-listeners-package-36510836956.json').read_text())
        package['repository_commit'] = 'f' * 40
        package['mapserver_progress_profile'] = progress.PROFILE
        package['files']['MapServer.exe']['sha256'] = 'c' * 64
        record = {key: value for key, value in package['files']['MapServer.exe'].items() if key != 'bytes'}
        record['size'] = package['files']['MapServer.exe']['bytes']
        build = expected_progress_receipt(ROOT)
        manifest = {'repository_commit': package['repository_commit'], 'schema_version': 1,
            'build_role': 'mapserver_progress', 'status': 'diagnostic_build_packaged_runtime_unverified',
            'configuration': 'OptDebug', 'architecture': 'Win32', 'postgresql_persistence_fixture': False,
            'runtime_execution_validated': False, 'build_targets': ['MapServer'],
            'source_commit': package['source_commit'], 'data_commit': package['data_commit'],
            'build_input': build, 'progress_contract': copy.deepcopy(build['progress_contract']),
            'files': {'MapServer.exe': record}}
        package['inputs']['mapserver_progress'] = {'repository_commit': package['repository_commit'], 'manifest': manifest}
        return self.seal(package)

    def test_explicit_profile_binds_fresh_binary_and_source_receipt_to_accepted_supporting_donors(self):
        package = self.package()
        contract = guest.mapserver_progress_contract(package)
        self.assertEqual(contract['producer']['mapserver_sha256'], 'c' * 64)
        self.assertEqual(contract['contract']['stages'], progress.STAGES)
        self.assertEqual(guest.game_listener_contract(package), guest.evidence.GAME_LOOPBACK_METADATA)
        self.assertIsNone(guest.mapserver_progress_contract({}))
        self.assertIsNone(guest.mapserver_progress_contract({'inputs': {}}))
        for malformed in ({'mapserver_progress_profile': 'unknown'},
                          {'inputs': {'mapserver_progress': {}}},
                          {'mapserver_progress_profile': progress.PROFILE}):
            with self.assertRaises(guest.base.DiagnosticError):
                guest.mapserver_progress_contract(malformed)

    def test_internal_contract_and_binary_mismatch_are_rejected_even_if_envelope_is_rehashed(self):
        original = self.package()
        changes = {
            'revision': lambda p: p['inputs']['mapserver_progress']['manifest'].update(repository_commit='d' * 40),
            'source': lambda p: p['inputs']['mapserver_progress']['manifest']['build_input'].update(source_commit='d' * 40),
            'stage': lambda p: p['inputs']['mapserver_progress']['manifest']['progress_contract']['stages'].update({'26': 'OTHER'}),
            'semantics': lambda p: p['inputs']['mapserver_progress']['manifest']['progress_contract'].update(tick_started_stage=25),
            'base-receipt': lambda p: p['inputs']['mapserver_progress']['manifest']['build_input'].update(game_build_input={}),
            'target': lambda p: p['inputs']['mapserver_progress']['manifest'].update(build_targets=['TestClient']),
            'fixture': lambda p: p['inputs']['mapserver_progress']['manifest'].update(postgresql_persistence_fixture=True),
            'binary': lambda p: p['files']['MapServer.exe'].update(sha256='d' * 64),
            'listener-profile': lambda p: p.update(game_listener_profile='accepted'),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                package = copy.deepcopy(original)
                change(package)
                self.seal(package)
                with self.assertRaises(guest.base.DiagnosticError):
                    guest.mapserver_progress_contract(package)
        package = copy.deepcopy(original)
        package['inputs']['mapserver_progress']['manifest']['files']['mapserver-progress-build-input.json']['sha256'] = 'f' * 64
        donor = package['inputs']['mapserver_progress']
        donor['manifest_sha256'] = hashlib.sha256((json.dumps(donor['manifest'], indent=2) + '\n').encode()).hexdigest()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'source receipt bytes'):
            guest.mapserver_progress_contract(package)

    def test_progress_environment_only_reaches_owned_atlas_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = object.__new__(guest.GameDiagnostic)
            diagnostic.runtime = root
            diagnostic.wine_env = {progress.ENVIRONMENT: 'inherited', 'WINEPREFIX': '/private/wine'}
            diagnostic.services = []
            diagnostic.args = SimpleNamespace(wine=Path('/private/wine/bin/wine'))
            diagnostic.ctx = SimpleNamespace(start=Mock(return_value=SimpleNamespace(process=SimpleNamespace(pid=123))))
            for executable in guest.EXES:
                diagnostic.start_game('unselected', executable, [])
                self.assertNotIn(progress.ENVIRONMENT, diagnostic.ctx.start.call_args.kwargs['env'])
            diagnostic.map_progress_contract = guest.mapserver_progress_contract(self.package())
            diagnostic.map_progress_paths, diagnostic.map_progress_previous = {}, {}
            diagnostic.map_progress_phase, diagnostic.map_progress_next_sample = None, 0
            diagnostic.game = {'mapserver_progress': progress.evidence(diagnostic.map_progress_contract['producer'])}
            diagnostic.begin_map_progress('first')
            for label, executable in (('first-atlas', 'MapServer.exe'), ('query', 'MapServer.exe'),
                                      ('first-dbserver', 'DbServer.exe'), ('client', 'TestClientCreate.exe')):
                diagnostic.start_game(label, executable, [])
                environment = diagnostic.ctx.start.call_args.kwargs['env']
                if label == 'first-atlas':
                    self.assertEqual(environment[progress.ENVIRONMENT],
                                     guest.base.windows_path(diagnostic.map_progress_paths['first']))
                else:
                    self.assertNotIn(progress.ENVIRONMENT, environment)
            self.assertEqual(diagnostic.wine_env[progress.ENVIRONMENT], 'inherited')


if __name__ == '__main__':
    unittest.main()
