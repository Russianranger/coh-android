"""Guarded same-operation service reuse without reviving expired deadlines."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_attempt_retry as retry
import client_interactive_diagnostic as interactive

SESSION = '0123456789abcdef0123456789abcdef'


def transcript(pid=44, code=0, session=SESSION):
    return (retry.startup.LAUNCH_MARKER + json.dumps({'session_id': session, 'pid': pid}) + '\n'
            + retry.EXIT_MARKER + json.dumps({'session_id': session, 'exit_code': code}) + '\n')


def live(pid):
    return SimpleNamespace(process=SimpleNamespace(pid=pid, poll=lambda: None), started=10.)


class RetryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ('runtime/data', 'work', 'wine', 'profile', 'captures'):
            (root / name).mkdir(parents=True)
        self.rows = {'ents': [{'containerid': 1, 'logincount': 5}], 'costumes': [{'part': 'original'}]}
        self.baseline = [{'containerid': 1, 'name': 'THORHERO', 'authname': 'COHLOCAL', 'authid': 1}]
        self.server = SimpleNamespace(process=live(2), map_process=live(3), runtime=root / 'runtime',
            profile=root / 'profile', CHARACTER_ID=1, health=Mock(), baseline=self.baseline,
            inventory=Mock(return_value=self.baseline), character_rows=Mock(return_value=self.rows),
            sample_progress=Mock(return_value={'available': True, 'tick_completed': 77, 'unchanged_seconds': 0.}),
            live_progress=lambda value: value.get('available') and value.get('tick_completed') > 0,
            report={'character_list_sent': False},
            creation_report={'connected_on_atlas': False, 'native_client_ready_observed': False,
                'baseline': {'table_sha256': {name: retry.digest(rows) for name, rows in self.rows.items()}}})
        script = 'import sys; sys.stdout.write(' + repr(transcript()) + '); sys.stdout.flush()'
        self.child = retry.base.OwnedProcess('failed-client', [sys.executable, '-c', script], os.environ.copy())
        self.child.process.wait(timeout=5); self.child.reader.join(timeout=2); self.child.writer.join(timeout=2)
        self.addCleanup(lambda: self.child.stop() if self.child.process.poll() is None else None)
        self.owner = SimpleNamespace(args=SimpleNamespace(session_id=SESSION, wine=root / 'wine-bin', assets=root),
            pg=live(1), xserver=live(4), local_server=self.server, work=root / 'work', wineprefix=root / 'wine',
            capture_dir=root / 'captures', client=self.child, observer=Mock(), login_announced=False,
            connected_announced=False, saved_announced=False,
            wine_env={retry.base.WineProcessOwner.ENV_KEY: 'current-owned-token', 'COH_TEXTURE_HEADER_ID': 'same-index',
                      'DISPLAY': ':100'},
            ctx=Mock(report={'diagnostic_mode': 'actual_character_reopen'}, deadline=5400.))
        self.owner.observer.windows.return_value = []
        self.owner.ctx.run.return_value = {'output': ''}
        self.owner.reset_client_startup_inputs = lambda: interactive.ClientInteractiveDiagnostic.reset_client_startup_inputs(self.owner)
        replacement = SimpleNamespace(process=SimpleNamespace(pid=1234, poll=lambda: None))
        def launch(**_kwargs):
            self.owner.client = replacement
        self.owner.launch_client_attempt = Mock(side_effect=launch)
        self.clock = 100.
        clock = patch.object(retry.time, 'monotonic', lambda: self.clock); clock.start(); self.addCleanup(clock.stop)
        self.guard = retry.ClientAttemptRetry(self.owner, 99., 900.)

    def test_real_closed_launcher_retries_once_and_keeps_services_and_original_deadlines(self):
        logs = self.owner.work / 'logs'; logs.mkdir(); (logs / 'failed.log').write_text('original failure\n')
        identity = retry.service_identity(self.owner)
        self.assertTrue(self.guard.prepare(None))
        self.assertEqual(retry.service_identity(self.owner), identity)
        self.assertEqual(self.guard.deadline, 900.)
        self.assertEqual(self.owner.ctx.deadline, 5400.)
        self.assertEqual(self.guard.record['reuse_count'], 1)
        self.assertFalse(self.guard.record['deadlines_extended'])
        self.assertFalse(self.guard.record['retained_after_operation'])
        self.assertEqual(len(self.guard.attempts), 2)
        self.assertNotEqual(self.guard.attempts[0]['attempt_id'], self.guard.attempts[1]['attempt_id'])
        self.assertTrue(self.guard.attempts[0]['native_client_terminated'])
        self.assertTrue(self.guard.attempts[0]['selected_sql_rows_unchanged'])
        self.assertEqual((self.owner.capture_dir / 'client-attempt-1-console.log').read_text(), transcript())
        self.assertEqual((self.owner.capture_dir / 'client-attempt-1-logs/failed.log').read_text(), 'original failure\n')
        self.assertFalse(logs.exists())
        self.assertEqual(self.owner.wine_env['COH_TEXTURE_HEADER_ID'], 'same-index')
        self.assertEqual([call.args[0] for call in self.owner.ctx.run.call_args_list],
                         ['client-progress-reset', 'client-progress-empty'])
        self.assertFalse(self.guard.prepare(None))
        self.owner.launch_client_attempt.assert_called_once_with(label='actual-coh-client-retry')

    def test_original_deadline_readiness_or_disabled_mode_prevents_retry(self):
        self.clock = 900.
        self.assertFalse(self.guard.prepare(None))
        self.clock = 100.
        self.assertFalse(self.guard.prepare(99.))
        self.guard.enabled = False
        self.assertFalse(self.guard.prepare(None))
        self.owner.launch_client_attempt.assert_not_called()

    def test_login_connection_or_save_evidence_forbids_retry(self):
        for field in ('login_announced', 'connected_announced', 'saved_announced'):
            with self.subTest(field=field):
                setattr(self.owner, field, True)
                with self.assertRaisesRegex(retry.base.DiagnosticError, 'readiness/login/save'):
                    self.guard.prepare(None)
                setattr(self.owner, field, False)
        for field in ('connected_on_atlas', 'native_client_ready_observed'):
            with self.subTest(field=field):
                self.server.creation_report[field] = True
                with self.assertRaisesRegex(retry.base.DiagnosticError, 'readiness/login/save'):
                    self.guard.prepare(None)
                self.server.creation_report[field] = False
        self.owner.launch_client_attempt.assert_not_called()

    def test_prior_window_or_unclosed_pipes_or_forced_exit_cannot_retry(self):
        self.owner.observer.windows.return_value = [{'title': 'City of Heroes : PID: 44', 'mapped': False}]
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'window remains'):
            self.guard.prepare(None)
        self.owner.observer.windows.return_value = []
        self.child.forced_stop = True
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'naturally closed'):
            self.guard.prepare(None)
        self.child.forced_stop = False
        with patch.object(self.child.reader, 'is_alive', return_value=True):
            with self.assertRaisesRegex(retry.base.DiagnosticError, 'remain open'):
                self.guard.prepare(None)
        self.owner.launch_client_attempt.assert_not_called()

    def test_native_service_identity_sql_rows_and_tick_progress_must_remain_current(self):
        self.server.map_process.process.pid = 99
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'services changed'):
            self.guard.prepare(None)
        self.server.map_process.process.pid = 3
        self.server.sample_progress.return_value = {'available': False}
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'progress is stale'):
            self.guard.prepare(None)
        self.server.sample_progress.return_value = {'available': True, 'tick_completed': 78}
        self.server.character_rows.return_value = {'ents': [{'containerid': 1, 'logincount': 6}]}
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'rows changed'):
            self.guard.prepare(None)
        self.owner.launch_client_attempt.assert_not_called()

    def test_new_attempt_rejects_previous_or_changing_native_pid(self):
        self.assertTrue(self.guard.prepare(None))
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'previous native client PID'):
            self.guard.observe_launch({'pid': 44})
        self.guard.observe_launch({'pid': 45})
        self.assertEqual(self.guard.attempts[-1]['native_client_pid'], 45)
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'identity changed'):
            self.guard.observe_launch({'pid': 46})

    def test_registry_reset_failure_cannot_relaunch(self):
        self.owner.ctx.run.return_value = {'output': 'GameProgress REG_SZ game_mainLoop\n'}
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'could not be cleared'):
            self.guard.prepare(None)
        self.owner.launch_client_attempt.assert_not_called()

    def test_preparation_consuming_original_deadline_cannot_relaunch(self):
        reset = self.owner.reset_client_startup_inputs
        def expired_reset():
            reset(); self.clock = 900.
        self.owner.reset_client_startup_inputs = expired_reset
        with self.assertRaisesRegex(retry.base.DiagnosticError, 'deadline expired'):
            self.guard.prepare(None)
        self.owner.launch_client_attempt.assert_not_called()

    def test_stop_request_prevents_any_retry_preparation_or_relaunch(self):
        self.owner.ctx.check.side_effect = retry.base.Cancelled('Cancellation requested')
        with self.assertRaises(retry.base.Cancelled):
            self.guard.prepare(None)
        self.owner.launch_client_attempt.assert_not_called()
        self.assertFalse((self.owner.capture_dir / 'client-attempt-1-console.log').exists())

    def test_execute_reuses_services_once_and_accepts_only_fresh_attempt_menu(self):
        d = interactive.ClientInteractiveDiagnostic.__new__(interactive.ClientInteractiveDiagnostic)
        d.__dict__.update(self.owner.__dict__)
        d.args.startup_timeout_seconds = 900
        d.args.observation_seconds = 30
        d.args.interaction_seconds = 1200
        d.finish_path = d.work / 'interaction-finish.json'
        d.presentation_socket = d.work / 'view.sock'
        d.captures = []; d.startup_complete = False
        d.initialize = Mock(); d.start_wine = Mock(); d.mark_wine_ready = Mock(); d.save_evidence = Mock()
        d.finish_observation = Mock(return_value={})
        fresh_output = (retry.startup.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': 45}) + '\n'
            + retry.startup.CONSOLE_MARKER + json.dumps({'session_id': SESSION, 'pid': 45, 'attached': True})
            + '\nRenderer initialization complete\nLoaded all data!\n')
        fresh = SimpleNamespace(process=SimpleNamespace(pid=1234, poll=lambda: None),
                                text=lambda: fresh_output, overflow=False)
        clients = iter((self.child, fresh))
        d.launch_client_attempt = Mock(side_effect=lambda **_kwargs: setattr(d, 'client', next(clients)))
        d.reset_client_startup_inputs = lambda: interactive.ClientInteractiveDiagnostic.reset_client_startup_inputs(d)
        observer = Mock()
        observer.windows.side_effect = lambda: [] if d.client is self.child else [
            {'title': 'City of Heroes : PID: 45', 'mapped': True, 'width': 800, 'height': 600}]
        observer.capture.return_value = {'distinct_colors_capped': 16, 'path': 'capture.ppm'}
        d.ctx.run.side_effect = lambda label, *_a, **_kw: {
            'output': 'GameProgress REG_SZ game_mainLoop\n' if label == 'client-progress-registry' else ''}
        def event(kind, **_fields):
            if kind == 'client_interaction_ready':
                d.finish_path.write_text(json.dumps({'format': 1, 'session_id': SESSION,
                    'client_pid': 45, 'action': 'finish_interaction'}))
        d.ctx.event.side_effect = event
        def sleep(seconds):
            self.clock = round(self.clock + seconds, 6)
        with patch.object(interactive, 'XObserver', return_value=observer), \
             patch.object(interactive.base, 'validate_runtime_probe', return_value={}), \
             patch.object(interactive.time, 'sleep', sleep):
            d.execute()
        self.assertTrue(d.startup_complete)
        self.assertEqual(d.ctx.report['client_launch']['pid'], 45)
        self.assertEqual(d.ctx.report['warm_client_retry']['reuse_count'], 1)
        self.assertEqual(d.ctx.report['warm_client_retry']['original_startup_deadline_monotonic'], 1000.)
        self.assertEqual(d.ctx.report['warm_client_retry']['original_overall_deadline_monotonic'], 5400.)
        self.assertEqual(d.ctx.report['interaction_finish_request']['client_pid'], 45)
        d.initialize.assert_called_once(); d.start_wine.assert_called_once()
        self.assertEqual(d.launch_client_attempt.call_count, 2)
        self.assertEqual(self.server.map_process.process.pid, 3)


class NativeExitAndLogTests(unittest.TestCase):
    def test_native_exit_rejects_missing_duplicate_wrong_session_timeout_or_active_code(self):
        self.assertEqual(retry.native_exit(transcript(), SESSION)['pid'], 44)
        malformed = [transcript(session='f' * 32), transcript(code=259), transcript() + transcript(),
                     transcript() + 'COH_CLIENT_LAUNCHER_TIMEOUT_V1 {}\n',
                     retry.startup.LAUNCH_MARKER + json.dumps({'session_id': SESSION, 'pid': 44}) + '\n']
        for output in malformed:
            with self.subTest(output=output):
                with self.assertRaises(retry.base.DiagnosticError):
                    retry.native_exit(output, SESSION)

    def test_log_archive_is_bounded_and_rejects_linked_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'logs'; source.mkdir()
            (source / 'large.log').write_bytes(b'x' * (300 * 1024))
            result = retry.archive_logs(source, root / 'archive')
            self.assertEqual(result, {'files': 1, 'bytes': 256 * 1024})
            (source / 'escape').symlink_to(root / 'archive', target_is_directory=True)
            with self.assertRaisesRegex(retry.base.DiagnosticError, 'Linked'):
                retry.archive_logs(source, root / 'refused')


if __name__ == '__main__':
    unittest.main()
