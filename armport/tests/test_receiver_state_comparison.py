"""Only three agreed lifecycle-ID fields may change in ID-sensitivity checks."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'replay'))
from compare_state import canonical_initial_ids, differences, compare
import test_receiver_evidence as evidence


class StateComparison(unittest.TestCase):
    def fixture(self):
        case = evidence.ReceiverEvidenceTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.check()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for target in ('arm64', 'i686'):
            folder = root / target
            folder.mkdir()
            (folder / 'report.json').write_text(json.dumps(dict(target=target,
                source_commit='a' * 40, cursor_stage_passed=True)))
            for label in ('id1-a', 'id1-b', 'id31'):
                run = folder / label
                shutil.copytree(case.path, run)
                if label != 'id31':
                    continue
                rows = json.loads('[' + ','.join((run / 'receiver.jsonl').read_text().splitlines()) + ']')
                rows[0]['initial_id'] = 31
                for row in rows:
                    if row.get('index') == 0 and 'id' in row or row.get('count') == 1:
                        row['id'] = 31
                    if row['type'] == 'ack' and row['packet_id'] == 1:
                        row['packet_id'] = 31
                    if row['type'] == 'state':
                        path = run / row['file']
                        value = json.loads(path.read_text())
                        value['entities'][0]['pkt_id_create'] = 31
                        value['entities'][0]['player']['lastClientStatePktId'] = 31
                        raw = json.dumps(value).encode()
                        path.write_bytes(raw)
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                (run / 'receiver.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
        return root

    def test_complete_partial_comparison_does_not_claim_milestone(self):
        result = compare(self.fixture(), 'a' * 40)
        self.assertTrue(result['partial_state_equal'])
        self.assertEqual(len(result['comparisons']), 7)
        for key in ('state_schema_complete', 'state_comparison_complete', 'm3_replay_complete'):
            self.assertFalse(result[key])

    def test_wrong_reference_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity or execution'):
            compare(self.fixture(), 'b' * 40)

    def test_authenticated_later_state_difference_fails_comparison(self):
        root = self.fixture()
        run = root / 'i686/id1-a'
        path = run / 'state-116.json'
        state = json.loads(path.read_text())
        state['entities'][0]['costume']['bodytype'] = 99
        raw = json.dumps(state).encode()
        path.write_bytes(raw)
        rows = [json.loads(line) for line in (run / 'receiver.jsonl').read_text().splitlines()]
        for row in rows:
            if row['type'] == 'state' and row['index'] == 116:
                row['sha256'] = hashlib.sha256(raw).hexdigest()
        (run / 'receiver.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
        result = compare(root, 'a' * 40)
        self.assertFalse(result['partial_state_equal'])
        self.assertEqual(result['comparisons'][0]['mismatches'], [
            {'index': 116, 'fields': ['$.entities[0].costume.bodytype']}])
        self.assertEqual(result['comparisons'][0]['canonicalized_fields'], [])
        self.assertEqual(len(result['comparisons'][-1]['canonicalized_fields']), 3)

    def test_only_agreed_initial_id_fields_are_canonicalized(self):
        source = {'entities': [{'pkt_id_create': 1, 'id': 1, 'net_ipos': [1, 31, 1],
                  'pkt_id_qrot': [1, 1, 1], 'player': {'lastClientStatePktId': 1}},
                  {'pkt_id_create': 32, 'player': {'lastClientStatePktId': 155}}],
                  'delete_history': [{'pkt_id': 1, 'id': 1}, {'pkt_id': 32, 'id': 31}]}
        result = canonical_initial_ids(source, 1)
        self.assertEqual(set(differences(source, result)), {
            '$.entities[0].pkt_id_create', '$.entities[0].player.lastClientStatePktId',
            '$.delete_history[0].pkt_id'})
        self.assertEqual(source['entities'][0]['pkt_id_create'], 1)
        self.assertEqual(result['entities'][1], source['entities'][1])

    def test_literal_comparison_detects_schema_length_and_float_bit_differences(self):
        a = {'values': [0, 2147483648], 'extra': 1}
        b = {'values': [0, 0, 1]}
        self.assertEqual(list(differences(a, b)), ['$.keys', '$.values.length', '$.values[1]'])


if __name__ == '__main__':
    unittest.main()
