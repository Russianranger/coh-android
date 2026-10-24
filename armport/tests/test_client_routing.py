"""Exercise real creation/reopen inheritance without starting any runtime."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import armport_interactive as armport
from character_creation_diagnostic import CharacterCreationDiagnostic
from character_reopen_diagnostic import CharacterReopenDiagnostic


class ClientRoutingTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
