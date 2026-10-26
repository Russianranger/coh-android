"""Diagnostic snapshot equality cannot qualify a failed execution."""
import hashlib
import json
import unittest

import test_receiver_state_comparison as fixtures
from diagnose_state import diagnose


class RejectedState(unittest.TestCase):
    def fixture(self):
        case = fixtures.StateComparison()
        self.addCleanup(case.doCleanups)
        root = case.fixture()
        for target in ('arm64', 'i686'):
            report = root / target / 'report.json'
            document = json.loads(report.read_text())
            document.pop('cursor_stage_passed')
            report.write_text(json.dumps(document))
            for label in ('id1-a', 'id1-b', 'id31'):
                folder = root / target / label
                (folder / 'process-observation.json').write_text(json.dumps(dict(
                    returncode=-9 if (target, label) == ('i686', 'id31') else 2)))
        return root

    def test_equal_snapshots_retain_failed_execution_and_incomplete_flags(self):
        result = diagnose(self.fixture(), 'a' * 40)
        self.assertTrue(result['diagnostic_snapshots_equal'])
        self.assertEqual(len(result['comparisons']), 7)
        self.assertEqual(result['executions'][-1]['returncode'], -9)
        self.assertFalse(result['executions'][-1]['source_cursor_stage_passed'])
        for key in ('execution_qualified', 'state_schema_complete',
                    'state_comparison_complete', 'm3_replay_complete'):
            self.assertIs(result[key], False)

    def test_hash_tampering_and_wrong_commit_abort_diagnostic(self):
        root = self.fixture()
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            diagnose(root, 'b' * 40)
        path = root / 'i686/id31/state-116.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'snapshot digest'):
            diagnose(root, 'a' * 40)

    def test_authenticated_difference_is_reported(self):
        root = self.fixture()
        folder = root / 'i686/id31'
        path = folder / 'state-116.json'
        document = json.loads(path.read_text())
        document['entities'][0]['costume']['bodytype'] = 99
        raw = json.dumps(document).encode()
        path.write_bytes(raw)
        rows = [json.loads(line) for line in (folder / 'receiver.jsonl').read_text().splitlines()]
        for row in rows:
            if row['type'] == 'state' and row['index'] == 116:
                row['sha256'] = hashlib.sha256(raw).hexdigest()
        (folder / 'receiver.jsonl').write_text('\n'.join(map(json.dumps, rows)))
        result = diagnose(root, 'a' * 40)
        self.assertFalse(result['diagnostic_snapshots_equal'])
        self.assertEqual(result['comparisons'][2]['mismatches'], [dict(index=116,
            fields=['$.entities[0].costume.bodytype'])])

    def test_only_dispatch_data_errors_can_be_inspected(self):
        root = self.fixture()
        folder = root / 'arm64/id1-a'
        trace = folder / 'zone-trace.jsonl'
        rows = trace.read_text().splitlines(True)
        rows.insert(5, json.dumps(dict(stage='client.error', text='missing texture', tid=1)) + '\n')
        trace.write_text(''.join(rows))
        (folder / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error missing texture tid=1\n')
        result = diagnose(root, 'a' * 40)
        self.assertEqual(result['executions'][0]['dispatch_errors'], 1)
        self.assertFalse(result['execution_qualified'])
        (folder / 'wine-output.txt').write_text('trace:seh:dispatch_exception code=c0000005\n')
        with self.assertRaisesRegex(ValueError, 'Wine exception'):
            diagnose(root, 'a' * 40)
