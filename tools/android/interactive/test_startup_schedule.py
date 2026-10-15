"""Client-only preparation follows Atlas proof and never outlives owned cleanup."""
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_creation_diagnostic as guest
import texture_header_index


class BeforeClientLaunch(Exception):
    pass


class StartupScheduleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.trace = []
        self.context = guest.CharacterContext(self.root, 30)
        self.context.report.update(import_identity={'format': 1, 'pinned': True},
            asset_sha256=dict.fromkeys(guest.REQUIRED, 'pinned'), native_responsiveness_candidate={
                'repository_commit': 'synthetic-wrapper-test'})
        self.context.event = Mock(side_effect=lambda kind, **fields: self.trace.append(
            ('event', kind, fields, threading.get_ident())))
        self.context.server_health = Mock()
        diagnostic = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
        diagnostic.ctx = self.context
        diagnostic.args = SimpleNamespace(state=self.root, assets=self.root / 'assets',
            session_id='1' * 32, wine=Path('/synthetic-wine'), startup_timeout_seconds=60)
        diagnostic.work = self.root / 'client-work'
        diagnostic.finish_path = self.root / 'interaction-finish.json'
        diagnostic.client_executable_sha256 = '2' * 64
        diagnostic.local_server = SimpleNamespace(report={}, creation_report={})
        diagnostic.wine_env = {'DISPLAY': ':100'}
        diagnostic.presentation_socket = self.root / 'view.sock'
        diagnostic.texture_header_preparation = None
        self.diagnostic = diagnostic
        self.addCleanup(self.join_worker)

    def join_worker(self):
        preparation = self.diagnostic.texture_header_preparation
        if preparation is not None:
            preparation.cancel_and_join()

    def server_ready(self, diagnostic):
        self.trace.append(('server-ready',))
        diagnostic.local_server.report['server_ready'] = True
        diagnostic.local_server.creation_report['map_ready'] = True

    def prepare_result(self, context):
        return {'records': 7, 'native_fallback_available': True}, {'COH_TEXTURE_HEADER_ID': 'verified'}

    def start(self, prepare):
        entered = threading.Event()
        def run(context):
            entered.set()
            return prepare(context)
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', lambda diagnostic: self.server_ready(diagnostic)), \
                patch.object(self.diagnostic, 'prepare_texture_header_index', side_effect=run):
            self.diagnostic.start_wine()
            self.assertTrue(entered.wait(1))
        return self.diagnostic.texture_header_preparation

    def reset(self):
        with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'reset_client_startup_inputs') as reset:
            self.diagnostic.reset_client_startup_inputs()
        return reset

    def test_initialize_never_indexes_textures_before_server_readiness(self):
        with patch.object(guest.login.ClientLoginDiagnostic, 'initialize'), \
                patch.object(guest.avatar, 'install', return_value={}) as avatar, \
                patch.dict(sys.modules, atlas_world_assets=SimpleNamespace(install=Mock(return_value={}))), \
                patch.object(texture_header_index, 'prepare') as prepare:
            self.diagnostic.initialize()
        avatar.assert_called_once()
        prepare.assert_not_called()
        self.assertIsNone(self.diagnostic.texture_header_preparation)

    def test_inherited_execute_overlaps_owned_probe_and_joins_before_client(self):
        indexed = threading.Event()
        probe_started = threading.Event()
        prepare_threads = []
        def prepare(context):
            prepare_threads.append(threading.get_ident())
            self.trace.append(('index-start',))
            context.event('log', label='index-worker', message='buffered until joined')
            indexed.set()
            while not probe_started.wait(.005):
                context.check()
            # The owned probe is alive while this independent file operation
            # completes. No Wine process/prefix or server-cache work is started.
            time.sleep(.03)
            context.check()
            return self.prepare_result(context)
        original_run = self.context.run
        def run(label, argv, **kwargs):
            self.assertEqual(label, 'runtime-probe')
            self.assertTrue(indexed.wait(1))
            self.assertNotIn('COH_TEXTURE_HEADER_ID', self.diagnostic.wine_env)
            self.assertFalse(any(entry[:2] == ('event', 'log') for entry in self.trace))
            self.trace.append(('probe-start',))
            child = self.context.start(label, [sys.executable, '-c', 'import time; time.sleep(.1)'])
            # Preserve Context.run's real owned-process exit/output proof while
            # giving the worker the actual process start time for the overlap.
            probe_started.set()
            with patch.object(self.context, 'start', return_value=child):
                return original_run(label, argv, **kwargs)
        def launch():
            self.trace.append(('client-launch',))
            self.assertEqual(self.diagnostic.wine_env['COH_TEXTURE_HEADER_ID'], 'verified')
            self.assertIsNone(self.diagnostic.texture_header_preparation)
            raise BeforeClientLaunch()
        self.diagnostic.initialize = Mock()
        self.diagnostic.mark_wine_ready = Mock(side_effect=lambda: self.trace.append(('wine-ready',)))
        self.diagnostic.capture = Mock()
        self.diagnostic.launch_client_attempt = launch
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', lambda diagnostic: self.server_ready(diagnostic)), \
                patch.object(self.diagnostic, 'prepare_texture_header_index', side_effect=prepare), \
                patch.object(self.context, 'run', side_effect=run), \
                patch.object(guest.base, 'validate_runtime_probe', return_value={}), \
                patch.object(guest.interactive.ClientInteractiveDiagnostic, 'reset_client_startup_inputs') as reset, \
                patch.object(guest.interactive, 'XObserver'):
            with self.assertRaises(BeforeClientLaunch):
                self.diagnostic.execute()
        order = [entry[0] for entry in self.trace]
        self.assertLess(order.index('server-ready'), order.index('index-start'))
        self.assertLess(order.index('index-start'), order.index('probe-start'))
        self.assertLess(order.index('probe-start'), order.index('wine-ready'))
        self.assertLess(order.index('wine-ready'), order.index('client-launch'))
        reset.assert_called_once()
        schedule = self.context.report['client_texture_startup_schedule']
        self.assertGreater(schedule['actual_overlap_seconds'], 0)
        self.assertTrue(schedule['runtime_probe_completion_observed'])
        self.assertFalse(schedule['physical_startup_savings_validated'])
        self.assertEqual(schedule['preparation_phase'], 'after_current_owned_atlas_readiness')
        self.assertTrue(schedule['worker_joined'])
        self.assertNotEqual(prepare_threads, [threading.get_ident()])
        self.assertTrue(all(entry[3] == threading.get_ident() for entry in self.trace if entry[0] == 'event'))
        self.assertTrue(all(child.process.poll() == 0 and not child.reader.is_alive()
                            and not child.writer.is_alive() for child in self.context.children))
        with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'reset_client_startup_inputs') as retry:
            self.diagnostic.reset_client_startup_inputs()
        retry.assert_called_once()
        self.assertEqual(len(prepare_threads), 1)

    def test_server_failure_and_missing_readiness_never_start_index(self):
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', side_effect=RuntimeError('server failed')), \
                patch.object(self.diagnostic, 'prepare_texture_header_index') as prepare:
            with self.assertRaisesRegex(RuntimeError, 'server failed'):
                self.diagnostic.start_wine()
            prepare.assert_not_called()
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine'), \
                patch.object(self.diagnostic, 'prepare_texture_header_index') as prepare:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'owned server readiness'):
                self.diagnostic.start_wine()
            prepare.assert_not_called()

    def test_optional_index_failure_keeps_native_fallback_and_clears_environment(self):
        self.diagnostic.wine_env.update(COH_TEXTURE_HEADER_PACK='stale', COH_TEXTURE_HEADER_ID='stale',
                                        COH_TEXTURE_DIAGNOSTIC_DEDUP='1')
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', lambda diagnostic: self.server_ready(diagnostic)), \
                patch.object(texture_header_index, 'prepare', side_effect=OSError('index unavailable')):
            self.diagnostic.start_wine()
            preparation = self.diagnostic.texture_header_preparation
            self.reset()
        self.assertFalse(preparation.thread.is_alive())
        self.assertFalse(self.context.report['texture_header_index']['enabled'])
        self.assertTrue(self.context.report['texture_header_index']['native_fallback_available'])
        self.assertTrue(all(not key.startswith('COH_TEXTURE') for key in self.diagnostic.wine_env))
        self.assertEqual(self.context.report['client_texture_startup_schedule']['actual_overlap_seconds'], 0)

    def test_unexpected_index_failure_is_propagated_before_reset_or_client(self):
        def fail(context):
            raise guest.base.DiagnosticError('texture identity changed')
        preparation = self.start(fail)
        with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'reset_client_startup_inputs') as reset:
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'texture identity changed'):
                self.diagnostic.reset_client_startup_inputs()
        self.assertFalse(preparation.thread.is_alive())
        self.assertIsNone(self.diagnostic.texture_header_preparation)
        reset.assert_not_called()
        self.assertEqual(self.context.report['client_texture_startup_schedule']['status'], 'failed_before_client')

    def cancellable_prepare(self, context):
        while True:
            context.check()
            time.sleep(.001)

    def test_cancellation_and_deadline_join_worker_before_return(self):
        for kind in ('cancel', 'deadline'):
            with self.subTest(kind=kind):
                self.context.cancel_requested = False
                self.context.deadline = time.monotonic() + 30
                preparation = self.start(self.cancellable_prepare)
                if kind == 'cancel':
                    self.context.cancel_requested = True
                    exception, message = guest.base.Cancelled, 'Cancellation requested'
                else:
                    self.context.deadline = time.monotonic() - 1
                    exception, message = guest.base.DiagnosticError, 'deadline exceeded'
                with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'reset_client_startup_inputs') as reset:
                    with self.assertRaisesRegex(exception, message):
                        self.diagnostic.reset_client_startup_inputs()
                self.assertFalse(preparation.thread.is_alive())
                self.assertIsNone(self.diagnostic.texture_header_preparation)
                self.assertEqual(self.context.children, [])
                reset.assert_not_called()

    def test_failed_owned_probe_cleanup_joins_worker_before_shared_cleanup(self):
        preparation = self.start(self.cancellable_prepare)
        with self.assertRaises(guest.base.DiagnosticError):
            self.context.run('runtime-probe', [sys.executable, '-c', 'raise SystemExit(3)'])
        def cleanup(diagnostic):
            self.assertFalse(preparation.thread.is_alive())
            self.assertIsNone(diagnostic.texture_header_preparation)
            self.assertTrue(all(child.process.poll() is not None and not child.reader.is_alive()
                                and not child.writer.is_alive() for child in self.context.children))
            return []
        with patch.object(guest.login.ClientLoginDiagnostic, 'cleanup', cleanup):
            self.assertEqual(self.diagnostic.cleanup(), [])
        self.assertEqual(self.context.report['client_texture_startup_schedule']['status'], 'aborted_before_client')
        self.assertNotIn('COH_TEXTURE_HEADER_ID', self.diagnostic.wine_env)

    def test_unsupported_worker_falls_back_after_readiness_with_zero_overlap(self):
        with patch.object(threading.Thread, 'start', side_effect=RuntimeError('unsupported')):
            preparation = self.start(self.prepare_result)
        self.assertFalse(preparation.thread_started)
        self.reset()
        self.assertEqual(self.context.report['client_texture_startup_schedule']['actual_overlap_seconds'], 0)
        self.assertFalse(self.context.report['client_texture_startup_schedule']['worker_started'])
        self.assertEqual(self.diagnostic.wine_env['COH_TEXTURE_HEADER_ID'], 'verified')


if __name__ == '__main__':
    unittest.main()
