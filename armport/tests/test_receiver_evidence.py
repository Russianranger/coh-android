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
        self.wine = self.path / 'wine-output.txt'
        self.wine.write_text('')
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
        self.rows.append(dict(type='receive_boundary', index=0, stage='entity_tail', cursor=300328, error_flags=0))
        for number in range(11):
            for boundary in ('begin', 'end'):
                self.rows.append(dict(type='game_command_' + boundary, index=0,
                                      command=number+1, cursor=300360+number*32, error_flags=0))
        self.rows.append(dict(type='game_command_end', index=0, command=0, cursor=303248, error_flags=0))
        self.rows.append(dict(type='receive_boundary', index=0, stage='command_tail_end', cursor=303248, error_flags=0))
        self.rows.append(dict(type='result', dispatches=117, exact_cursors=True,
                              state_comparison_complete=False, m3_replay_complete=False))

    def check(self):
        output = self.path / 'receiver.jsonl'
        output.write_text('\n'.join(json.dumps(row) for row in self.rows))
        return replay.check_output(output, self.expected, 1, self.wine)

    def test_complete_cursor_stage_still_not_milestone_pass(self):
        self.assertFalse(self.check()['m3_replay_complete'])

    def test_partial_dispatch_rejected(self):
        self.rows.pop(1)
        with self.assertRaisesRegex(ValueError, '117'):
            self.check()

    def test_complete_transcript_does_not_hide_wine_fatal(self):
        for message in ('wine: Unhandled page fault on read access',
                        'wine: fatal error: failed to initialize',
                        'wine client error:0: write: Bad file descriptor',
                        '0024:err:module:import_dll Library missing.dll not found'):
            with self.subTest(message=message):
                self.wine.write_text(message + '\n')
                with self.assertRaisesRegex(ValueError, 'Wine exception/fatal'):
                    self.check()

    def test_handled_seh_also_rejected(self):
        self.wine.write_text('0024:trace:seh:dispatch_exception code=c0000005 flags=0\n'
                             '0024:trace:seh:call_handlers handler returned 0\n')
        with self.assertRaisesRegex(ValueError, 'Wine exception/fatal'):
            self.check()

    def test_missing_wine_evidence_rejected(self):
        self.wine.unlink()
        with self.assertRaises(FileNotFoundError):
            self.check()

    def test_bootstrap_exceptions_are_separate_from_game_evidence(self):
        (self.path / 'bootstrap-output.txt').write_text(
            '0024:trace:seh:dispatch_exception code=6ba RPC_S_SERVER_UNAVAILABLE\n')
        self.assertFalse(self.check()['m3_replay_complete'])

    def test_native_initial_tail_boundary_mismatch_rejected(self):
        next(row for row in self.rows if row.get('stage') == 'entity_tail')['cursor'] -= 8
        with self.assertRaisesRegex(ValueError, 'native INITIAL boundary'):
            self.check()

    def test_native_initial_missing_tail_command_rejected(self):
        self.rows.remove(next(row for row in self.rows if row['type'] == 'game_command_begin'))
        with self.assertRaisesRegex(ValueError, 'command count'):
            self.check()

    def test_native_initial_missing_zero_terminator_rejected(self):
        self.rows.remove(next(row for row in self.rows if row.get('command') == 0))
        with self.assertRaisesRegex(ValueError, 'zero terminator'):
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
