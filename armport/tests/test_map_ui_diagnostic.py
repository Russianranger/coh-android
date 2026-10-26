from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import login_ui

class MapDiagnostic(unittest.TestCase):
    def run_probe(self, words=None, targets=None, dialogs=None, focus=0):
        screen = Mock()
        screen.shot.side_effect = [Path('before.png'), Path('after.png')]
        screen.words.return_value = words if words is not None else [('Map', 200, 150)]
        target = ('101', (100, 100, 1024, 768))
        with patch.object(login_ui, 'owned_client_target', side_effect=targets or [target, target]), \
             patch.object(login_ui, 'dialogs_clear', side_effect=dialogs or [True, True, True]), \
             patch.object(login_ui, 'sh', return_value=SimpleNamespace(returncode=focus)), \
             patch.object(login_ui.time, 'sleep'):
            report = login_ui.map_ui_diagnostic(screen, [8082], Path('trace'))
        self.assertFalse(report['rendering_acceptance_changed'])
        return screen, report

    def test_one_click_separate_frames_no_acceptance(self):
        screen, r = self.run_probe()
        screen.click.assert_called_once_with(200, 150)
        self.assertTrue(r['click_sent'])
        self.assertEqual(r['after'], 'after.png')
        screen.key.assert_not_called()
        self.assertNotIn('world_rendered', r)

    def test_missing_ambiguous_outside_navigation(self):
        for words in ([], [('Map', 200, 150)] * 2, [('Map', 200, 500)],
                      [('Map', 99, 150)], [('Map', 1124, 150)], [('Maps', 200, 150)]):
            screen, r = self.run_probe(words=words)
            screen.click.assert_not_called()
            self.assertFalse(r['click_sent'])

    def test_missing_or_changed_owner(self):
        for targets in ([None], [('101', (100,100,1024,768)), ('102', (100,100,1024,768))]):
            screen, _ = self.run_probe(targets=targets)
            screen.click.assert_not_called()

    def test_dialog_at_each_boundary(self):
        for dialogs in ([False], [True,False], [True,True,False]):
            screen, _ = self.run_probe(dialogs=dialogs)
            screen.click.assert_not_called()

    def test_focus_failure(self):
        screen, _ = self.run_probe(focus=1)
        screen.click.assert_not_called()

    def test_after_original_verdict_and_frames(self):
        s = (Path(__file__).resolve().parents[1] / 'server/armport_game_host.py').read_text()
        body = s[s.index("        status['world_rendered'] = rendered >= 2"):s.index('\n\ndef main():')]
        self.assertLess(body.index("status['atlas_shot_later']"), body.index("status['map_ui_diagnostic']"))
        self.assertLess(body.index('except Exception as exc:'), body.index("state / 'armport-host-done.json'"))
        self.assertEqual(body.count("status['world_rendered']"), 1)

if __name__ == '__main__': unittest.main()
