"""Never acknowledge unknown errors while driving the known QA notice."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import login_ui

NOTICE = 'ArmPort zone: 1 dialog.alert.begin ' + login_ui.QA_NOTICE + ' tid=36\n'


class QANotice(unittest.TestCase):
    def test_only_known_pending_notice(self):
        self.assertTrue(login_ui.pending_qa_notice(NOTICE))
        for text in ('', NOTICE.replace('(9)', '(0)'), NOTICE.replace('alert', 'error'),
                     NOTICE + 'ArmPort zone: 2 dialog.alert.done tid=36\n',
                     NOTICE + 'ArmPort zone: 2 dialog.error.begin Fatal Error tid=36\n',
                     'ArmPort zone: 0 client.fatal bad\n' + NOTICE):
            self.assertFalse(login_ui.pending_qa_notice(text))

    @patch.object(login_ui, 'sh')
    def test_exact_owned_window_and_bounded_input(self, sh):
        sh.return_value = SimpleNamespace(returncode=0, stdout='12345\n')
        screen, status = Mock(), {}
        for _ in range(3):
            self.assertTrue(login_ui.acknowledge_qa_notice(screen, NOTICE, [42], status))
        self.assertFalse(login_ui.acknowledge_qa_notice(screen, NOTICE, [42], status))
        self.assertEqual(screen.key.call_count, 3)
        sh.assert_any_call('xdotool', 'search', '--all', '--onlyvisible', '--pid', '42', '--name', '^Program Error$')
        sh.assert_any_call('xdotool', 'windowfocus', '--sync', '12345')
        screen.key.assert_called_with('Return')

    @patch.object(login_ui, 'sh')
    def test_no_input_on_ambiguous_or_unfocused_window(self, sh):
        screen = Mock()
        for pids, output in (([], '1\n'), ([1, 2], '1\n'), ([1], ''), ([1], '1\n2\n')):
            sh.return_value = SimpleNamespace(returncode=0, stdout=output)
            self.assertFalse(login_ui.acknowledge_qa_notice(screen, NOTICE, pids, {}))
        sh.side_effect = [SimpleNamespace(returncode=0, stdout='1\n'),
                          SimpleNamespace(returncode=1, stdout='')]
        self.assertFalse(login_ui.acknowledge_qa_notice(screen, NOTICE, [1], {}))
        screen.key.assert_not_called()

    @patch.object(login_ui, 'sh')
    def test_unknown_or_finished_notice_never_searches_or_sends_input(self, sh):
        screen = Mock()
        for text in (NOTICE.replace('(9)', '(0)'), NOTICE.replace('alert', 'error'),
                     NOTICE + 'ArmPort zone: 2 dialog.alert.done tid=36\n',
                     NOTICE + 'ArmPort zone: 2 client.fatal bad tid=36\n'):
            self.assertFalse(login_ui.acknowledge_qa_notice(screen, text, [42], {}))
        sh.assert_not_called()
        screen.key.assert_not_called()

    @patch.object(login_ui, 'sh')
    def test_search_failure_or_invalid_window_never_sends_input(self, sh):
        screen = Mock()
        for code, output in ((1, '12345\n'), (0, 'not-a-window\n')):
            sh.return_value = SimpleNamespace(returncode=code, stdout=output)
            self.assertFalse(login_ui.acknowledge_qa_notice(screen, NOTICE, [42], {}))
        screen.key.assert_not_called()


if __name__ == '__main__':
    unittest.main()
