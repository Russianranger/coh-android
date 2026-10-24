"""Reject partial/failing receiver output even when a terminal row looks good."""
import importlib.util
import hashlib
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
        (self.path / 'client-stdio.txt').write_text('')
        (self.path / 'zone-trace.jsonl').write_text(''.join(
            json.dumps(dict(stage='replay.dispatch.' + edge, text=str(i), tid=1)) + '\n'
            for i in range(117) for edge in ('begin', 'end')) + ''.join(
            json.dumps(dict(stage='replay.drain.' + edge, text='117', tid=1)) + '\n'
            for edge in ('begin', 'end')))
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
            raw = json.dumps(dict(schema='armport-receiver-state-v1-partial',
                                  state_schema_complete=False, delete_history=[],
                                  entities=[dict(svr_idx=125, type=2, pkt_id_create=1,
                                  player=dict(lastClientStatePktId=1),
                                  pkt_id_pos=[1, 32], pkt_id_qrot=[1, 155, 0],
                                  costume=dict(bodytype=4, num_parts=28, parts=[None] * 60))])).encode()
            name = f'state-{i:03d}.json'
            (self.path / name).write_bytes(raw)
            self.rows.append(dict(type='state', index=i, id=packet_id, file=name,
                                  sha256=hashlib.sha256(raw).hexdigest(), entities=1,
                                  state_schema_complete=False))
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
        self.assertFalse(self.check()['state_schema_complete'])

    def test_game_error_and_assert_rejected(self):
        for text in ('ArmPort zone: 1 client.error missing texture tid=2', 'Assertion failed'):
            (self.path / 'client-stdio.txt').write_text(text)
            with self.assertRaisesRegex(ValueError, 'Game error/assert'):
                self.check()

    def test_dispatch_boundaries_cannot_be_missing_nested_or_misindexed(self):
        trace = self.path / 'zone-trace.jsonl'
        good = trace.read_text().splitlines(True)
        variants = [good[:-1], good[2:], [good[0]] + good,
                    [good[0], good[1].replace('"0"', '"1"')] + good[2:]]
        for rows in variants:
            with self.subTest(rows=len(rows)):
                trace.write_text(''.join(rows))
                with self.assertRaisesRegex(ValueError, 'Game error/assert'):
                    self.check()

    def test_only_errors_outside_dispatch_are_eligible_for_comparison(self):
        trace = self.path / 'zone-trace.jsonl'
        good = trace.read_text()
        error = json.dumps(dict(stage='client.error', text='missing texture', tid=2)) + '\n'
        (self.path / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error missing texture tid=2\n')
        trace.write_text(error + good)
        result = self.check()
        self.assertEqual(result['outside_game_errors'], 1)
        self.assertTrue(result['outside_error_comparison_required'])
        first, rest = good.split('\n', 1)
        trace.write_text(first + '\n' + error + rest)
        with self.assertRaisesRegex(ValueError, '1 dispatch errors'):
            self.check()

    def test_loader_drain_and_inter_dispatch_errors_cannot_escape(self):
        trace = self.path / 'zone-trace.jsonl'
        good = trace.read_text()
        error = json.dumps(dict(stage='client.error', text='late APC failure', tid=99)) + '\n'
        (self.path / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error late APC failure tid=99\n')
        rows = good.splitlines(True)
        for offset in (2, len(rows) - 1):
            trace.write_text(''.join(rows[:offset]) + error + ''.join(rows[offset:]))
            with self.assertRaisesRegex(ValueError, '1 dispatch errors'):
                self.check()
        (self.path / 'client-stdio.txt').write_text('')
        for bad in (''.join(rows[:-2]), ''.join(rows[:-1]), ''.join(rows + rows[-2:]),
                    good.replace(', "tid": 1', ''), good.replace('"tid": 1', '"tid": 0')):
            trace.write_text(bad)
            with self.assertRaises(ValueError):
                self.check()

    def test_missing_game_stdio_rejected(self):
        (self.path / 'client-stdio.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'game stdio'):
            self.check()

    def test_missing_or_partial_isolated_trace_rejected(self):
        trace = self.path / 'zone-trace.jsonl'
        for data in ('', '{"stage":"init","text":""}'):
            trace.write_text(data)
            with self.assertRaises(ValueError):
                self.check()
        trace.unlink()
        with self.assertRaisesRegex(ValueError, 'isolated zone trace'):
            self.check()

    def test_native_logical_count_not_storage_length(self):
        self.assertTrue(self.check()['native_initial_entity_subset_match'])
        path = self.path / 'state-000.json'
        doc = json.loads(path.read_text())
        doc['entities'][0]['costume']['num_parts'] = 29
        raw = json.dumps(doc).encode()
        path.write_bytes(raw)
        next(r for r in self.rows if r['type'] == 'state')['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'native INITIAL entity subset'):
            self.check()

    def test_missing_state_snapshot_rejected(self):
        self.rows = [r for r in self.rows if r['type'] != 'state' or r['index'] != 116]
        with self.assertRaisesRegex(ValueError, '117 partial state'):
            self.check()

    def test_snapshot_tampering_rejected(self):
        (self.path / 'state-116.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.check()

    def test_self_consistent_snapshot_disagrees_with_native_baseline(self):
        path = self.path / 'state-000.json'
        document = json.loads(path.read_text())
        document['entities'][0]['costume']['bodytype'] = 0
        raw = json.dumps(document).encode()
        path.write_bytes(raw)
        next(r for r in self.rows if r['type'] == 'state')['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'native INITIAL entity subset'):
            self.check()

    def test_snapshot_path_substitution_rejected(self):
        next(r for r in self.rows if r['type'] == 'state')['file'] = '../outside.json'
        with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
            self.check()

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
