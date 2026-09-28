"""Focused lifecycle boundaries for the hosted game orchestration."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest


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


if __name__ == '__main__':
    unittest.main()
