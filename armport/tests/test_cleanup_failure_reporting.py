"""Keep original owned-cleanup failures when the actual cache refuses return."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_login_diagnostic as login
import character_server_data_cache as cache


class CleanupFailureReportingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='armport-cleanup-report-')
        self.addCleanup(self.tmp.cleanup)
        profile = Path(self.tmp.name)
        (profile / 'pgdata').mkdir()
        (profile / 'pgdata/PG_VERSION').write_text('15')
        (profile / 'profile.json').write_text('{}')
        self.owner = login.ClientLoginDiagnostic.__new__(login.ClientLoginDiagnostic)
        self.owner.ctx = SimpleNamespace(server_health=object(), report={'postgres_started': True})
        self.owner.cleanup_status = dict(postgres_graceful=True, wine_prefix_stopped=False,
                                         owned_processes_reaped=True)
        self.owner.database_created = False
        self.cache = cache.ServerDataCache.__new__(cache.ServerDataCache)
        self.cache.record = {'fixture': True}
        # release checks the real shutdown prerequisites before inspecting paths.
        self.owner.local_server = SimpleNamespace(profile=profile, report={},
            cleanup_config=lambda: self.cache.release(profile / 'unused', self.owner.cleanup_status))

    def test_original_failure_and_actual_cache_refusal_both_survive(self):
        with patch.object(login.interactive.ClientInteractiveDiagnostic, 'cleanup',
                          return_value=['Wine cleanup: fixture -w timeout']):
            failures = self.owner.cleanup()
        self.assertEqual(failures, ['Wine cleanup: fixture -w timeout',
            'Server configuration/cache cleanup: Atlas data cache return lacks proved owned Wine cleanup'])
        self.assertIsNone(self.owner.ctx.server_health)
        self.assertIs(self.owner.cleanup_status['wine_prefix_stopped'], False)
        self.assertIs(self.owner.local_server.report['database_preserved'], True)

    def test_raised_cleanup_error_is_preserved_with_cache_refusal(self):
        with patch.object(login.interactive.ClientInteractiveDiagnostic, 'cleanup',
                          side_effect=RuntimeError('fixture descendant inspection failed')):
            failures = self.owner.cleanup()
        self.assertEqual(failures, ['Owned cleanup failed: fixture descendant inspection failed',
            'Server configuration/cache cleanup: Atlas data cache return lacks proved owned Wine cleanup'])

    def test_incomplete_descendant_proof_still_refuses_cache_return(self):
        self.owner.cleanup_status.update(wine_prefix_stopped=True, owned_processes_reaped=False)
        with patch.object(login.interactive.ClientInteractiveDiagnostic, 'cleanup', return_value=[]):
            failures = self.owner.cleanup()
        self.assertEqual(failures, [
            'Server configuration/cache cleanup: Atlas data cache return lacks proved owned Wine cleanup'])
        self.assertIs(self.owner.cleanup_status['owned_processes_reaped'], False)

    def test_success_keeps_cleanup_and_profile_result(self):
        self.owner.cleanup_status.update(wine_prefix_stopped=True, owned_processes_reaped=True)
        self.owner.local_server.cleanup_config = lambda: None
        with patch.object(login.interactive.ClientInteractiveDiagnostic, 'cleanup', return_value=[]):
            self.assertEqual(self.owner.cleanup(), [])
        self.assertIs(self.owner.local_server.report['database_preserved'], True)

    def test_profile_failure_is_not_hidden_by_cache_failure(self):
        self.owner.cleanup_status['postgres_graceful'] = False
        with patch.object(login.interactive.ClientInteractiveDiagnostic, 'cleanup',
                          return_value=['PostgreSQL cleanup: fixture failure']):
            failures = self.owner.cleanup()
        self.assertEqual(len(failures), 3)
        self.assertEqual(failures[0], 'PostgreSQL cleanup: fixture failure')
        self.assertIn('cache cleanup', failures[1])
        self.assertEqual(failures[2], 'Persistent profile preservation or PostgreSQL shutdown was not proved')
        self.assertIs(self.owner.local_server.report['database_preserved'], False)


if __name__ == '__main__':
    unittest.main()
