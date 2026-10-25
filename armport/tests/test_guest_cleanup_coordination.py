"""Exercise the real M3 guest cleanup methods with a simulated host clock."""
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CleanupCoordination(unittest.TestCase):
    def exercise(self, *, ready=True, stopped=False, acknowledge=True, receipt=None):
        events = []
        clock = [0]
        class Original:
            def cleanup(self):
                events.append('original-audit')
                return ['original-failure']
            def health(self):
                raise AssertionError('Failed health must not gate host teardown')
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            if ready: (state/'armport-ready.json').touch()
            data = json.dumps({'stopped': True, 'errors': []} if receipt is None else receipt)
            if stopped: (state/'armport-client-stopped.json').write_text(data)
            def marker(name, value):
                events.append(name)
                (state/name).write_text('finished')
            def sleep(seconds):
                clock[0] += seconds
                if acknowledge: (state/'armport-client-stopped.json').write_text(data)
            def require(ok, message):
                if not ok: raise RuntimeError(message)
            path = ROOT/'armport/server/armport_game_guest.py'
            node = next(n for n in ast.parse(path.read_text()).body
                        if isinstance(n, ast.ClassDef) and n.name == 'ArmPortGame')
            ns = dict(json=json, gd=SimpleNamespace(GameDiagnostic=Original), STATE=state,
                      write_marker=marker, require=require,
                      time=SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
            result = ns['ArmPortGame']().cleanup()
            return result, events, clock[0]

    def test_failure_path_stops_host_before_original_audit(self):
        result, events, _ = self.exercise()
        self.assertEqual(events, ['armport-guest-finished.json','original-audit'])
        self.assertEqual(result, ['original-failure'])

    def test_host_timeout_fails_and_still_runs_original_audit(self):
        result, events, elapsed = self.exercise(acknowledge=False)
        self.assertEqual(elapsed, 180)
        self.assertIn('Host client cleanup coordination:', result[0])
        self.assertEqual(result[-1], 'original-failure')
        self.assertEqual(events[-1], 'original-audit')

    def test_no_host_launch_requires_no_handshake(self):
        result, events, elapsed = self.exercise(ready=False)
        self.assertEqual(events, ['original-audit'])
        self.assertEqual(elapsed, 0)
        self.assertEqual(result, ['original-failure'])

    def test_completed_normal_handshake_is_validated_without_wait(self):
        result, events, elapsed = self.exercise(stopped=True)
        self.assertEqual(events, ['armport-guest-finished.json', 'original-audit'])
        self.assertEqual(elapsed, 0)
        self.assertEqual(result, ['original-failure'])

    def test_failed_or_incomplete_host_receipt_cannot_bypass_original_audit(self):
        for receipt in ({'stopped': False, 'errors': ['timeout']},
                        {'stopped': True, 'errors': ['timeout']},
                        {'stopped': True}, {'stopped': 1, 'errors': []}, []):
            result, events, elapsed = self.exercise(stopped=True, receipt=receipt)
            self.assertIn('Host client cleanup coordination:', result[0])
            self.assertEqual(events[-1], 'original-audit')
            self.assertEqual(result[-1], 'original-failure')
