import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import process_observation


class ProcessObservation(unittest.TestCase):
    def test_exit_witness_requires_a_complete_exact_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / 'zone.jsonl'
            self.assertFalse(process_observation.exit_marker_seen(trace))
            for text in ('{"stage":"replay.exit.begin"}',
                         '{"stage":"replay.cleanup.begin"}\n',
                         '["replay.exit.begin"]\n', 'broken\n'):
                trace.write_text(text)
                self.assertFalse(process_observation.exit_marker_seen(trace))
            trace.write_text('x' * 9000 + '\n{"stage":"replay.exit.begin"}\n')
            self.assertTrue(process_observation.exit_marker_seen(trace))

    def test_passive_exit_observation_does_not_rescue_a_killed_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'process.json'
            trace = Path(tmp) / 'zone.jsonl'
            for ending, expected in (('raise SystemExit(2)', 2),
                    ('os.kill(os.getpid(),signal.SIGKILL)', -9)):
                trace.unlink(missing_ok=True)
                program = ('import os,signal,time;from pathlib import Path;'
                    f'Path({str(trace)!r}).write_text(\'{{"stage":"replay.exit.begin"}}\\n\');'
                    'time.sleep(0.25);' + ending)
                result = process_observation.run([sys.executable, '-c', program],
                    evidence=evidence, timeout=5, exit_trace=trace)
                self.assertEqual(result.returncode, expected)
                report = json.loads(evidence.read_text())
                self.assertEqual(report['returncode'], expected)
                self.assertNotIn('host_timeout_kill', report)
                observation = report['exit_observation']
                self.assertTrue(observation['marker_seen'])
                self.assertTrue(observation['samples'])
                self.assertLessEqual(len(observation['samples']), 40)
                # Some local /proc providers hide task directories. Missing
                # evidence must be explicit, not interpreted as no threads.
                self.assertTrue(all(s['tasks'] or 'unavailable' in s
                                    or s.get('task_count') == 0
                                    for s in observation['samples']))
                self.assertEqual(observation['scope'], 'passive_linux_tasks_not_signal_sender')

    def test_task_evidence_is_bounded_and_reports_unavailable_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for tid in range(1, 67):
                task = root / '123/task' / str(tid)
                task.mkdir(parents=True)
                (task / 'stat').write_text('S' * 5000)
                if tid != 1:
                    (task / 'wchan').write_text('futex_wait_queue')
            result = process_observation.task_sample(123, time.monotonic(), root)
            self.assertEqual(result['task_count'], 66)
            self.assertTrue(result['truncated'])
            self.assertEqual(len(result['tasks']), 64)
            self.assertEqual(len(result['tasks'][0]['stat']), 4096)
            self.assertIn('wchan_unavailable', result['tasks'][0])
            self.assertEqual(result['tasks'][1]['wchan'], 'futex_wait_queue')

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
