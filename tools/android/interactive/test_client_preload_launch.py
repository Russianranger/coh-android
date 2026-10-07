"""Exercise the saved-character launch route that bypassed the Game opt-in."""
import copy
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_reopen_diagnostic as reopen

GAME_SHA = 'a' * 64
MANIFEST_SHA = 'b' * 64
SESSION = '0123456789abcdef0123456789abcdef'


class ClientPreloadLaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.diagnostic = reopen.StartupOnlyCharacterReopenDiagnostic.__new__(
            reopen.StartupOnlyCharacterReopenDiagnostic)
        d = self.diagnostic
        d.args = SimpleNamespace(wine=self.root / 'wine', assets=self.root / 'assets',
                                session_id=SESSION)
        d.work = self.root / 'work'
        d.work.mkdir()
        d.wine_env = {'DISPLAY': ':100', 'WINEPREFIX': str(self.root / 'prefix'),
                      'COH_TEXTURE_HEADER_ID': 'verified-index',
                      'COH_CLIENT_KNOWN_STRING_COPY': '1', 'COH_CLIENT_BIN_PROFILE': '1',
                      'COH_CLIENT_DEPENDENCY_PRELOAD': 'inherited-untrusted-value'}
        d.client_startup_followup = True
        d.client_executable_sha256 = GAME_SHA
        self.producer = {
            'repository_commit': 'c' * 40, 'manifest_sha256': MANIFEST_SHA,
            'base_client_executable_sha256': 'd' * 64,
            'client_executable_sha256': GAME_SHA,
            'replacement_scope': 'CityOfHeroes.exe_only', 'metadata_preload_only': True,
            'source_freshness_preserved': True, 'prepared_cache_schema_changed': False,
            'physical_startup_savings_validated': False}
        d.ctx = Mock(report={'client_startup_followup': copy.deepcopy(self.producer)})
        self.original_env = dict(d.wine_env)
        self.original_report = copy.deepcopy(d.ctx.report['client_startup_followup'])
        self.original_cwd = Path.cwd()

    def test_saved_character_initial_and_owned_retry_receive_opt_in_and_keep_inputs(self):
        d = self.diagnostic
        command = d.launcher_command()
        self.assertEqual(command[-1], '--character-creation')
        observed = []
        def start(label, argv, *, env):
            observed.append((label, argv, dict(env), Path.cwd()))
            return SimpleNamespace(process=SimpleNamespace(pid=123, poll=lambda: None))
        d.ctx.start.side_effect = start
        for label in ('actual-coh-client', 'actual-coh-client-retry'):
            d.launch_client_attempt(label=label)
            self.assertEqual(d.ctx.report['client_dependency_preload_environment']['launch_label'], label)
            self.assertFalse(d.ctx.report['client_dependency_preload_environment']['native_execution_validated'])
        expected = dict(self.original_env, COH_CLIENT_DEPENDENCY_PRELOAD='1')
        self.assertEqual(observed, [(label, command, expected, d.work)
                                   for label in ('actual-coh-client', 'actual-coh-client-retry')])
        self.assertEqual(d.wine_env, self.original_env)
        self.assertEqual(d.ctx.report['client_startup_followup'], self.original_report)
        self.assertEqual(Path.cwd(), self.original_cwd)
        self.assertEqual(d.ctx.report['client_dependency_preload_environment']['producer_manifest_sha256'], MANIFEST_SHA)

    def test_unqualified_or_truthy_flag_never_inherits_an_opt_in(self):
        d = self.diagnostic
        for value in (False, None, 1, '1', {}, {'verified': True}):
            with self.subTest(value=value):
                d.client_startup_followup = value
                d.launch_client_attempt()
                environment = d.ctx.start.call_args.kwargs['env']
                self.assertNotIn('COH_CLIENT_DEPENDENCY_PRELOAD', environment)
                self.assertEqual(environment, {k: v for k, v in self.original_env.items()
                                              if k != 'COH_CLIENT_DEPENDENCY_PRELOAD'})
                self.assertFalse(d.ctx.report['client_dependency_preload_environment']['enabled'])
                self.assertEqual(d.wine_env, self.original_env)
        del d.client_startup_followup
        d.launch_client_attempt()
        self.assertNotIn('COH_CLIENT_DEPENDENCY_PRELOAD', d.ctx.start.call_args.kwargs['env'])

    def test_enabled_flag_without_matching_current_typed_producer_fails_before_launch(self):
        d = self.diagnostic
        mutations = [('client_executable_sha256', 'e' * 64), ('manifest_sha256', ''),
                     ('repository_commit', 'foreign'), ('replacement_scope', 'Game_and_MapServer'),
                     ('metadata_preload_only', 1), ('source_freshness_preserved', False),
                     ('prepared_cache_schema_changed', True)]
        for field, value in mutations:
            with self.subTest(field=field):
                producer = copy.deepcopy(self.producer)
                producer[field] = value
                d.ctx.report['client_startup_followup'] = producer
                with self.assertRaisesRegex(reopen.base.DiagnosticError, 'current verified Game producer'):
                    d.launch_client_attempt()
                d.ctx.start.assert_not_called()
                self.assertEqual(Path.cwd(), self.original_cwd)
                self.assertEqual(d.wine_env, self.original_env)
        for value in (None, {}, 'untyped'):
            d.ctx.report['client_startup_followup'] = value
            with self.assertRaisesRegex(reopen.base.DiagnosticError, 'current verified Game producer'):
                d.launch_client_attempt()
        d.ctx.start.assert_not_called()

    def test_current_game_identity_is_required_even_when_report_claims_a_producer(self):
        d = self.diagnostic
        for value in ('', 'a' * 63, None):
            d.client_executable_sha256 = value
            with self.assertRaisesRegex(reopen.base.DiagnosticError, 'current verified Game producer'):
                d.launch_client_attempt()
        del d.client_executable_sha256
        with self.assertRaisesRegex(reopen.base.DiagnosticError, 'current verified Game producer'):
            d.launch_client_attempt()
        d.ctx.start.assert_not_called()

    def test_failed_owned_launch_restores_cwd_and_never_mutates_server_environment(self):
        d = self.diagnostic
        d.ctx.start.side_effect = RuntimeError('owned launch failed')
        with self.assertRaisesRegex(RuntimeError, 'owned launch failed'):
            d.launch_client_attempt()
        self.assertEqual(Path.cwd(), self.original_cwd)
        self.assertEqual(d.wine_env, self.original_env)
        self.assertEqual(d.ctx.report['client_startup_followup'], self.original_report)


class ClientSceneLaunchTests(unittest.TestCase):
    def setUp(self):
        ClientPreloadLaunchTests.setUp(self)
        d = self.diagnostic
        d.client_scene_performance = True
        self.scene = {
            'repository_commit': 'e' * 40, 'manifest_sha256': 'f' * 64,
            'client_executable_sha256': GAME_SHA, 'replacement_scope': 'CityOfHeroes.exe_only',
            'source_freshness_preserved': True, 'prepared_cache_schema_changed': False,
            'renderer_changed': False, 'bounded_diagnostics': True,
            'surviving_fx_preload_preserved': True}
        d.ctx.report['client_scene_performance'] = copy.deepcopy(self.scene)
        for name in ('COH_CLIENT_SCENE_PROFILE', 'COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD',
                     'COH_CLIENT_FRAME_TIMING'):
            d.wine_env[name] = 'inherited-untrusted-value'
        self.original_env = dict(d.wine_env)

    def test_verified_initial_and_retry_have_bounded_profiles_and_disable_legacy_resource_logging(self):
        d = self.diagnostic
        for label in ('actual-coh-client', 'actual-coh-client-retry'):
            d.launch_client_attempt(label=label)
            environment = d.ctx.start.call_args.kwargs['env']
            for name in ('COH_CLIENT_SCENE_PROFILE', 'COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD',
                         'COH_CLIENT_FRAME_TIMING', 'COH_CLIENT_DEPENDENCY_PRELOAD',
                         'COH_CLIENT_KNOWN_STRING_COPY'):
                self.assertEqual(environment[name], '1')
            self.assertEqual(environment['COH_CLIENT_BIN_PROFILE'], '0')
            self.assertEqual(d.ctx.report['client_scene_performance_environment']['launch_label'], label)
            self.assertTrue(d.ctx.report['client_scene_performance_environment']['enabled'])
            self.assertEqual(d.wine_env, self.original_env)
            self.assertEqual(d.ctx.report['client_scene_performance'], self.scene)
            self.assertEqual(Path.cwd(), self.original_cwd)

    def test_old_or_truthy_scene_producer_retains_old_bin_policy_and_strips_scene_controls(self):
        d = self.diagnostic
        for flag in (False, None, 1, '1', {'verified': True}):
            with self.subTest(flag=flag):
                d.client_scene_performance = flag
                d.launch_client_attempt()
                environment = d.ctx.start.call_args.kwargs['env']
                for name in ('COH_CLIENT_SCENE_PROFILE', 'COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD',
                             'COH_CLIENT_FRAME_TIMING'):
                    self.assertNotIn(name, environment)
                self.assertEqual(environment['COH_CLIENT_BIN_PROFILE'], '1')
                self.assertEqual(environment['COH_CLIENT_DEPENDENCY_PRELOAD'], '1')
                self.assertFalse(d.ctx.report['client_scene_performance_environment']['enabled'])
                self.assertEqual(d.wine_env, self.original_env)

    def test_foreign_game_or_unverified_scene_semantics_fail_before_client_or_retry_launch(self):
        d = self.diagnostic
        mutations = [('client_executable_sha256', 'e' * 64), ('manifest_sha256', ''),
                     ('repository_commit', 'foreign'), ('replacement_scope', 'all_native'),
                     ('source_freshness_preserved', False), ('prepared_cache_schema_changed', True),
                     ('renderer_changed', True), ('bounded_diagnostics', 1),
                     ('surviving_fx_preload_preserved', False)]
        for field, value in mutations:
            scene = copy.deepcopy(self.scene); scene[field] = value
            d.ctx.report['client_scene_performance'] = scene
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(field=field, label=label), self.assertRaisesRegex(
                        reopen.base.DiagnosticError, 'current verified Game producer'):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called()
                self.assertEqual(d.wine_env, self.original_env)
        d.ctx.report['client_scene_performance'] = self.scene
        d.client_startup_followup = False
        with self.assertRaisesRegex(reopen.base.DiagnosticError, 'current verified Game producer'):
            d.launch_client_attempt()
        d.ctx.start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
