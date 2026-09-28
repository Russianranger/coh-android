"""Focused lifecycle boundaries for the hosted game orchestration."""
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest


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


if __name__ == '__main__':
    unittest.main()
