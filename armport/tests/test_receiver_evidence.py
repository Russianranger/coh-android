"""Reject partial/failing receiver output even when a terminal row looks good."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('receiver_ci', Path(__file__).resolve().parents[1] / 'replay/run_ci.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class ReceiverEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.expected = replay.fixtures(self.path)
        self.rows = [dict(type='configuration', initial_id=1)]
        for i, want in enumerate(self.expected):
            packet_id = 1 if i == 0 else want['packet_id']
            self.rows.append(dict(type='dispatch_begin', index=i, id=packet_id, command=want['command'],
                                  logical_bits=want['logical_bits'], cursor=want['post_command_cursor']))
            self.rows.append(dict(type='cursor', index=i, id=packet_id, expected=want['logical_bits'],
                                  actual=want['logical_bits'], error_flags=0))
            if want['command'] == 3:
                self.rows.append(dict(type='ack', packet_id=packet_id, ack_id=123))
            self.rows.append(dict(type='dispatch_end', count=i+1, id=packet_id,
                                  cursor=want['logical_bits'], error_flags=0))
        self.rows.append(dict(type='result', dispatches=117, exact_cursors=True,
                              state_comparison_complete=False, m3_replay_complete=False))

    def check(self):
        output = self.path / 'receiver.jsonl'
        output.write_text('\n'.join(json.dumps(row) for row in self.rows))
        return replay.check_output(output, self.expected, 1)

    def test_complete_cursor_stage_still_not_milestone_pass(self):
        self.assertFalse(self.check()['m3_replay_complete'])

    def test_partial_dispatch_rejected(self):
        self.rows.pop(1)
        with self.assertRaisesRegex(ValueError, '117'):
            self.check()

    def test_cursor_overrun_rejected(self):
        self.rows[2]['actual'] += 1
        with self.assertRaisesRegex(ValueError, 'cursor'):
            self.check()

    def test_missing_ack_rejected(self):
        self.rows = [r for r in self.rows if r['type'] != 'ack']
        with self.assertRaisesRegex(ValueError, 'ACK'):
            self.check()

    def test_reported_failure_and_false_completion_rejected(self):
        self.rows.insert(-1, dict(type='failure', reason='assertion'))
        with self.assertRaisesRegex(ValueError, 'failure'):
            self.check()
        self.rows.pop(-2)
        self.rows[-1]['m3_replay_complete'] = True
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.check()


if __name__ == '__main__':
    unittest.main()
