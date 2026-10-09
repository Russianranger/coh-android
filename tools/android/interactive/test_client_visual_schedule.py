"""Client supplements require owned Atlas readiness and precede texture indexing."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_creation_diagnostic as guest


class ClientVisualScheduleTests(unittest.TestCase):
    INPUTS = {'client_visual_assets.py', 'client_animation_package.py',
              'client-visual-assets.zip', 'client-visual-manifest.json'}
    PINS = INPUTS | {'server-animations.pigg', 'server-animation-manifest.json'}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.assets = root / 'assets'
        self.assets.mkdir()
        self.trace = []
        self.ctx = SimpleNamespace(report={'native_responsiveness_candidate': {'verified': True},
            'asset_sha256': dict.fromkeys(self.PINS, 'verified')}, check=Mock(),
            stage=Mock(side_effect=lambda name: self.trace.append(name)), passed=Mock())
        self.value = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
        self.value.ctx = self.ctx
        self.value.args = SimpleNamespace(assets=self.assets)
        self.value.work = root / 'client-work'
        self.value.local_server = SimpleNamespace(report={'server_ready': True},
            creation_report={'map_ready': True})
        self.value.texture_header_preparation = None
        self.visual = Mock(side_effect=lambda *args, **kwargs: {'selected_files': 2})
        self.animation = Mock(side_effect=lambda *args, **kwargs: {'tracks': 3})
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, client_visual_assets=SimpleNamespace(install=self.visual),
            client_animation_package=SimpleNamespace(install=self.animation)).start()

    def complete_inputs(self):
        for name in self.INPUTS:
            (self.assets / name).write_bytes(b'pinned fixture')

    def assert_not_installed(self):
        self.visual.assert_not_called()
        self.animation.assert_not_called()
        self.assertIsNone(self.value.texture_header_preparation)

    def test_historical_absent_bundle_preserves_original_path(self):
        self.value.prepare_client_visual_inputs()
        self.assert_not_installed()
        self.ctx.stage.assert_not_called()

    def test_every_partial_bundle_is_rejected(self):
        self.complete_inputs()
        for missing in sorted(self.INPUTS):
            with self.subTest(missing=missing):
                path = self.assets / missing
                path.unlink()
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'Incomplete client'):
                    self.value.prepare_client_visual_inputs()
                self.assert_not_installed()
                path.write_bytes(b'pinned fixture')

    def test_dangling_payload_link_cannot_masquerade_as_absent_bundle(self):
        (self.assets / 'client-visual-assets.zip').symlink_to(self.assets / 'missing')
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Incomplete client'):
            self.value.prepare_client_visual_inputs()
        self.assert_not_installed()

    def test_each_unpinned_input_fails_before_preparation(self):
        self.complete_inputs()
        for name in sorted(self.PINS):
            with self.subTest(name=name):
                self.ctx.report['asset_sha256'] = dict.fromkeys(self.PINS - {name}, 'verified')
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'verified asset pins'):
                    self.value.prepare_client_visual_inputs()
                self.assert_not_installed()

    def test_each_missing_readiness_proof_fails_before_install(self):
        self.complete_inputs()
        for report, key in ((self.value.local_server.report, 'server_ready'),
                            (self.value.local_server.creation_report, 'map_ready')):
            with self.subTest(key=key):
                report[key] = False
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'owned Atlas readiness'):
                    self.value.prepare_client_visual_inputs()
                self.assert_not_installed()
                report[key] = True

    def test_owned_readiness_then_visual_animation_then_index_worker(self):
        self.complete_inputs()
        worker = Mock()
        worker.start.side_effect = lambda: self.trace.append('texture-index-start')
        def ready(value):
            self.trace.append('owned-atlas-ready')
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', ready), \
                patch.object(guest, 'TextureHeaderPreparation', return_value=worker):
            self.value.start_wine()
        self.assertEqual(self.trace, ['owned-atlas-ready', 'client_visual_assets',
            'client_animation_pack', 'texture-index-start'])
        self.visual.assert_called_once_with(self.value.work, self.assets, self.ctx)
        self.animation.assert_called_once_with(self.assets / 'server-animations.pigg',
            self.assets / 'server-animation-manifest.json', self.value.work,
            assets=self.assets, context=self.ctx)
        self.assertEqual(self.ctx.report['client_visual_supplement'], {'selected_files': 2})
        self.assertEqual(self.ctx.report['client_animation_pack'], {'tracks': 3})
        self.assertEqual(self.ctx.passed.call_count, 2)
        self.assertIs(self.value.texture_header_preparation, worker)

    def test_server_failure_prevents_both_supplements_and_index(self):
        self.complete_inputs()
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine', side_effect=RuntimeError('owned failure')), \
                patch.object(guest, 'TextureHeaderPreparation') as worker:
            with self.assertRaisesRegex(RuntimeError, 'owned failure'):
                self.value.start_wine()
            worker.assert_not_called()
        self.assert_not_installed()

    def test_installer_failures_prevent_following_preparation_or_launch(self):
        self.complete_inputs()
        for failed in ('visual', 'animation'):
            with self.subTest(failed=failed):
                self.visual.reset_mock()
                self.animation.reset_mock()
                self.visual.side_effect = RuntimeError('visual refused') if failed == 'visual' else None
                self.visual.return_value = {'selected_files': 2}
                self.animation.side_effect = RuntimeError('animation refused')
                with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine'), \
                        patch.object(guest, 'TextureHeaderPreparation') as worker:
                    with self.assertRaisesRegex(RuntimeError, failed + ' refused'):
                        self.value.start_wine()
                    worker.assert_not_called()
                if failed == 'visual':
                    self.animation.assert_not_called()
                self.assertIsNone(self.value.texture_header_preparation)

    def test_cancelled_session_never_installs_supplements(self):
        self.complete_inputs()
        self.ctx.check.side_effect = guest.base.Cancelled('Cancellation requested')
        with patch.object(guest.login.ClientLoginDiagnostic, 'start_wine'), \
                patch.object(guest, 'TextureHeaderPreparation') as worker:
            with self.assertRaises(guest.base.Cancelled):
                self.value.start_wine()
            worker.assert_not_called()
        self.assert_not_installed()


if __name__ == '__main__':
    unittest.main()
