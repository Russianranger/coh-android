import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import process_observation


class ProcessObservation(unittest.TestCase):
    def test_normal_and_signaled_exits_remain_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'process.json'
            for program, expected in (('raise SystemExit(2)', 2),
                                      ('import os,signal;os.kill(os.getpid(),signal.SIGKILL)', -9)):
                result = process_observation.run([sys.executable, '-c', program], evidence=evidence, timeout=5)
                self.assertEqual(result.returncode, expected)
                report = json.loads(evidence.read_text())
                self.assertEqual(report['returncode'], expected)
                self.assertNotIn('host_timeout_kill', report)
                self.assertTrue(report['samples'])
                if expected < 0: self.assertEqual(report['signal'], 'SIGKILL')

    def test_host_timeout_is_recorded_separately_and_still_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'process.json'
            with self.assertRaises(subprocess.TimeoutExpired):
                process_observation.run([sys.executable, '-c', 'import time;time.sleep(30)'],
                                        evidence=evidence, timeout=0.1)
            self.assertTrue(json.loads(evidence.read_text())['host_timeout_kill'])
