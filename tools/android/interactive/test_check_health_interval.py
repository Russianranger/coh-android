"""0.13.73: check() runs the server health chain at most every 0.05 s.

Thor 0.13.72 (20261117): the supervisor made 418-581 wait4 stops a second through whole
launches. Every loop iteration's check() ran the whole health chain, which polls PostgreSQL
and the DbServer. CI run 44103181482 counted 527,457 polls in a 1,220 s creation session.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_login_diagnostic as guest


class CheckHealthInterval(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.context = guest.LoginContext(Path(temporary.name), 30)
        self.calls = []
        self.context.server_health = lambda: self.calls.append(self.now)
        self.now = 1000.0
        clock = patch.object(guest.time, 'monotonic', side_effect=lambda: self.now)
        clock.start(); self.addCleanup(clock.stop)
        self.context.deadline = self.now + 3600

    def test_the_first_check_runs_health_and_a_burst_runs_it_once(self):
        for _ in range(500):
            self.context.check()
            self.now += 0.0001                      # 500 checks in 0.05 s
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0], 1000.0)

    def test_health_runs_again_after_the_interval(self):
        self.context.check()
        self.now += guest.LoginContext.HEALTH_SECONDS - 0.001
        self.context.check()
        self.assertEqual(len(self.calls), 1)
        self.now += 0.002
        self.context.check()
        self.assertEqual(len(self.calls), 2)
        self.assertLessEqual(guest.LoginContext.HEALTH_SECONDS, 0.1)

    def test_a_dead_server_is_still_reported(self):
        self.context.check()

        def dead():
            raise guest.base.DiagnosticError('Local DbServer exited during login')
        self.context.server_health = dead
        self.now += 0.01
        self.context.check()                        # inside the interval: not looked at yet
        self.now += guest.LoginContext.HEALTH_SECONDS
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'DbServer exited'):
            self.context.check()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'DbServer exited'):
            self.now += guest.LoginContext.HEALTH_SECONDS
            self.context.check()

    def test_cancellation_and_the_deadline_are_checked_every_time(self):
        self.context.check()
        self.context.cancel_requested = True
        with self.assertRaises(guest.base.Cancelled):
            self.context.check()                    # the same instant, inside the interval
        self.context.cancel_requested = False
        self.context.deadline = self.now - 1
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'deadline'):
            self.context.check()

    def test_without_a_server_nothing_is_called(self):
        self.context.server_health = None
        self.context.check()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
