"""Exercise real creation/reopen inheritance without starting any runtime."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import armport_interactive as armport
from character_creation_diagnostic import CharacterCreationDiagnostic
from character_reopen_diagnostic import CharacterReopenDiagnostic
from test_client_package import pe


class ClientRoutingTests(unittest.TestCase):
    def test_server_helper_only_does_not_activate_optional_visuals(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, value = self.instance(CharacterCreationDiagnostic, 'arm64')
            value.args.assets = Path(temporary)
            (value.args.assets / 'client_visual_assets.py').write_text('server dependency')
            value.prepare_client_visual_inputs()
            (value.args.assets / 'client-visual-assets.zip').write_bytes(b'incomplete')
            with self.assertRaisesRegex(armport.base.DiagnosticError, 'Incomplete client visual'):
                value.prepare_client_visual_inputs()

    def instance(self, base, architecture):
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': architecture}):
            selected = armport.select(base)
        value = selected.__new__(selected)
        value.args = SimpleNamespace(wine=Path('/opt/wine/bin/wine'), assets=Path('/assets'),
                                     session_id='a' * 32)
        value.work = Path('/state/x86-data')
        value.armport_work = Path('/state/arm64-client')
        return selected, value

    def test_default_keeps_existing_classes(self):
        with patch.dict(os.environ, {}, clear=True):
            for base in (CharacterCreationDiagnostic, CharacterReopenDiagnostic):
                self.assertIs(armport.select(base), base)

    def test_actual_create_and_reopen_commands_select_separate_arm64_tree(self):
        for base, mode in ((CharacterCreationDiagnostic, '--character-creation'),
                           (CharacterReopenDiagnostic, '--character-manual')):
            _, value = self.instance(base, 'arm64')
            command = value.launcher_command()
            self.assertEqual(command, [value.args.wine,
                armport.base.windows_path(value.armport_work / 'armport-launcher.exe'), 'a' * 32,
                armport.base.windows_path(value.armport_work / 'CityOfHeroes.exe'),
                armport.base.windows_path(value.armport_work), mode])
            self.assertNotIn('x86-data', ' '.join(map(str, command)))

    def test_x86_commands_remain_original(self):
        for base, mode in ((CharacterCreationDiagnostic, '--character-creation'),
                           (CharacterReopenDiagnostic, '--character-manual')):
            selected, value = self.instance(base, 'x86')
            self.assertIs(selected, base)
            command = value.launcher_command()
            self.assertEqual(command[1], armport.base.windows_path(value.args.assets / 'client-launcher.exe'))
            self.assertEqual(command[3], armport.base.windows_path(value.work / 'CityOfHeroes.exe'))
            self.assertEqual(command[-1], mode)

    def test_unknown_architecture_and_unqualified_zoning_rejected(self):
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'guess'}):
            with self.assertRaisesRegex(armport.base.DiagnosticError, 'Unknown graphical client architecture'):
                armport.select(CharacterCreationDiagnostic)
        class Zoning(CharacterReopenDiagnostic):
            ZONING = True
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'arm64'}):
            with self.assertRaisesRegex(armport.base.DiagnosticError, 'zone travel is not yet qualified'):
                armport.select(Zoning)

    def test_arm64_copy_includes_visuals_installed_after_server_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, binary, bins, shaders = (root / name for name in ('assets', 'binary', 'bins', 'shaders'))
            for path in (assets, binary, bins, shaders): path.mkdir()
            for name in armport.package.BINARIES - {'armport-launcher.exe'}:
                (binary / name).write_bytes(pe())
            launcher = root / 'launcher.exe'
            launcher.write_bytes(pe())
            (bins / 'BodyParts.bin').write_bytes(b'arm64')
            (shaders / 'test.arb').write_bytes(b'ARB')
            armport.package.package(binary, bins, shaders, launcher,
                                    assets / armport.package.ARCHIVE, 123, 122)
            class ExistingGuest:
                def initialize(self): pass
                def start_wine(self): self.server_prepared = True
                def prepare_client_visual_inputs(self):
                    if not self.server_prepared: raise AssertionError('server not prepared')
                    (self.work / 'data/visual.texture').write_bytes(b'late visual input')
            class Selected(armport.ArmPortClient, ExistingGuest): pass
            value = Selected()
            value.root, value.work = root, root / 'x86'
            (value.work / 'data').mkdir(parents=True)
            value.args = SimpleNamespace(assets=assets, session_id='a' * 32)
            value.ctx = SimpleNamespace(report={'asset_sha256': dict.fromkeys(
                ('armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py')),
                'client_worktree': {}, 'native_responsiveness_candidate': {'x86': True}},
                stage=lambda name: None, passed=lambda **kwargs: None)
            value.initialize()
            self.assertFalse(value.armport_work.exists())
            self.assertNotIn('native_responsiveness_candidate', value.ctx.report)
            value.start_wine()
            self.assertEqual((value.armport_work / 'data/visual.texture').read_bytes(), b'late visual input')
            self.assertEqual((value.armport_work / 'data/bin/BodyParts.bin').read_bytes(), b'arm64')
            self.assertFalse(value.ctx.report['armport_client']['x86_bins_reused'])


if __name__ == '__main__':
    unittest.main()
