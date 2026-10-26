"""The first-login helper prompt is answered only with its original None button."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import login_ui

PROMPT = [('Welcome!', 400, 300), ('This', 420, 300), ('character', 460, 300), ('is', 500, 300),
          ('new', 520, 300), ('Help', 380, 400), ('Me!', 400, 400), ('None', 500, 400),
          ('Helper', 600, 400)]
TARGET = ('101', (100, 100, 1024, 768))


class HelperStatus(unittest.TestCase):
    def run_once(self, words=PROMPT, targets=None, dialogs=None, focus=0, status=None):
        screen = Mock()
        screen.words.return_value = words
        screen.shot.return_value = Path('after.png')
        status = {} if status is None else status
        with patch.object(login_ui, 'owned_client_target', side_effect=targets or [TARGET, TARGET]), \
             patch.object(login_ui, 'dialogs_clear', side_effect=dialogs or [True, True]), \
             patch.object(login_ui, 'sh', return_value=SimpleNamespace(returncode=focus)), \
             patch.object(login_ui.time, 'sleep'):
            sent = login_ui.dismiss_helper_status(screen, Path('before.png'), [8082], Path('trace'), status)
        return screen, sent, status

    def test_clicks_unique_none(self):
        screen, sent, status = self.run_once()
        self.assertTrue(sent)
        screen.click.assert_called_once_with(500, 400)
        screen.key.assert_not_called()
        self.assertEqual(status['helper_status_actions'][0]['after'], 'after.png')

    def test_requires_prompt_text_and_unique_button_inside_client(self):
        for words in ([w for w in PROMPT if w[0] != 'new'], [w for w in PROMPT if w[0] != 'None'],
                      PROMPT + [('None', 700, 400)], [w if w[0] != 'None' else ('None', 50, 400) for w in PROMPT],
                      [w if w[0] != 'None' else ('Nonce', 500, 400) for w in PROMPT]):
            screen, sent, _ = self.run_once(words=words)
            self.assertFalse(sent)
            screen.click.assert_not_called()

    def test_owner_dialog_and_focus_gates(self):
        for kwargs in (dict(targets=[None]), dict(targets=[TARGET, ('102', TARGET[1])]),
                       dict(dialogs=[False]), dict(dialogs=[True, False]), dict(focus=1)):
            screen, sent, _ = self.run_once(**kwargs)
            self.assertFalse(sent)
            screen.click.assert_not_called()

    def test_attempts_are_bounded(self):
        status = {'helper_status_actions': [{}, {}]}
        screen, sent, _ = self.run_once(status=status)
        self.assertFalse(sent)
        screen.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
