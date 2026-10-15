"""Complete current-console identity checks without splitting native log lines."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_startup_diagnostic as guest

SESSION = '0123456789abcdef0123456789abcdef'


def line(marker, **fields):
    return marker + json.dumps(fields)


def stock_values(output, marker):
    return [json.loads(value[len(marker):]) for value in output.splitlines()
            if value.startswith(marker)]


class ConsoleMarkerTests(unittest.TestCase):
    def setUp(self):
        self.launch = {'session_id': SESSION, 'pid': 44}
        self.console = dict(self.launch, attached=True)
        self.output = (line(guest.LAUNCH_MARKER, **self.launch) + '\r\n'
                       + line(guest.CONSOLE_MARKER, **self.console) + '\n')

    def test_complete_current_launch_and_console_match_stock(self):
        for marker in (guest.LAUNCH_MARKER, guest.CONSOLE_MARKER):
            self.assertEqual(stock_values(self.output, marker),
                             guest.console_marker_values(self.output, marker))
        self.assertEqual(self.launch, guest.parse_launch(self.output, SESSION))
        self.assertEqual(self.console, guest.console_identity(self.output, self.launch))

    def test_every_splitlines_boundary_and_final_unterminated_line(self):
        for boundary in guest._CONSOLE_LINE_BOUNDARIES + '\r\n':
            for prefix in ('', 'ordinary diagnostic' + boundary):
                with self.subTest(boundary=repr(boundary), prefix=bool(prefix)):
                    output = prefix + line(guest.LAUNCH_MARKER, **self.launch)
                    for suffix in ('', boundary, boundary + 'next log line'):
                        text = output + suffix
                        self.assertEqual(stock_values(text, guest.LAUNCH_MARKER),
                                         guest.console_marker_values(text, guest.LAUNCH_MARKER))

    def test_embedded_markers_never_establish_an_owned_identity(self):
        output = 'log mentions ' + self.output.replace('\r\n', '\r\nlog mentions ')
        self.assertIsNone(guest.parse_launch(output, SESSION))
        self.assertIsNone(guest.console_identity(output, self.launch))

    def test_late_duplicate_launch_still_rejects(self):
        self.assertEqual(self.launch, guest.parse_launch(self.output, SESSION))
        output = self.output + 'ordinary diagnostics\n' + line(guest.LAUNCH_MARKER, **self.launch)
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate client launch'):
            guest.parse_launch(output, SESSION)

    def test_late_duplicate_console_still_rejects(self):
        self.assertEqual(self.console, guest.console_identity(self.output, self.launch))
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate client console'):
            guest.console_identity(self.output + line(guest.CONSOLE_MARKER, **self.console), self.launch)

    def test_new_attempt_never_reuses_previous_pid_or_session(self):
        self.assertEqual(self.launch, guest.parse_launch(self.output, SESSION))
        current = dict(self.launch, pid=45)
        output = line(guest.LAUNCH_MARKER, **current) + '\n'
        self.assertEqual(current, guest.parse_launch(output, SESSION))
        self.assertIsNone(guest.console_identity(output, current))
        for fields in (dict(current, session_id='f' * 32), dict(current, pid=True),
                       dict(current, extra=1)):
            with self.subTest(fields=fields), self.assertRaises(guest.base.DiagnosticError):
                guest.parse_launch(line(guest.LAUNCH_MARKER, **fields), SESSION)

    def test_mismatched_console_and_malformed_json_are_rejected(self):
        for fields in (dict(self.console, pid=45), dict(self.console, attached=False),
                       dict(self.console, session_id='f' * 32), dict(self.console, extra=1)):
            with self.subTest(fields=fields), self.assertRaises(guest.base.DiagnosticError):
                guest.console_identity(line(guest.CONSOLE_MARKER, **fields), self.launch)
        for marker in (guest.LAUNCH_MARKER, guest.CONSOLE_MARKER):
            with self.assertRaises(json.JSONDecodeError):
                guest.console_marker_values(marker + '{unfinished', marker)

    def test_large_log_uses_no_per_diagnostic_line_split_and_finds_tail_duplicate(self):
        class UnsplitConsole(str):
            def splitlines(self, *args, **kwargs):
                raise AssertionError('Full native log split is forbidden')
        output = UnsplitConsole(self.output + ('ordinary native diagnostic text\r\n' * 50000))
        self.assertEqual(self.launch, guest.parse_launch(output, SESSION))
        self.assertEqual(self.console, guest.console_identity(output, self.launch))
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate client launch'):
            guest.parse_launch(UnsplitConsole(output + line(guest.LAUNCH_MARKER, **self.launch)), SESSION)

    def test_observer_reports_identity_work_separately_without_skipping_current_checks(self):
        diagnostic = guest.ClientStartupDiagnostic.__new__(guest.ClientStartupDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION)
        diagnostic.ctx = SimpleNamespace(report={})
        diagnostic.client = SimpleNamespace(text=lambda: self.output)
        self.assertEqual((self.output, self.launch, self.console), diagnostic.observe_console())
        self.assertEqual((self.output, self.launch, self.console), diagnostic.observe_console())
        metrics = diagnostic.ctx.report['client_console_identity_metrics']
        self.assertEqual(2, metrics['calls'])
        self.assertEqual(len(self.output), metrics['last_console_characters'])
        self.assertTrue(metrics['whole_console_rescanned'])
        self.assertFalse(metrics['identity_cache_added'])
        self.output += line(guest.LAUNCH_MARKER, **self.launch)
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Duplicate client launch'):
            diagnostic.observe_console()


if __name__ == '__main__':
    unittest.main()
