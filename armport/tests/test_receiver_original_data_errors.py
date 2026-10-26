"""The user-approved original-data exception is literal, opt-in and bounded."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import test_receiver_evidence as evidence
import test_receiver_state_comparison as comparison
import original_data_errors as exception


TEXT = 'CUSTOM TEXTURE ERROR: FEM wants nonexistent texture HIPS_miniskirt_1 as texture 2 on bone HIPS.'


def add_errors(folder, texts=(TEXT,), index=1, after=False):
    path = folder / 'zone-trace.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    edge = 'end' if after else 'begin'
    at = next(i for i, r in enumerate(rows)
              if r['stage'] == 'replay.dispatch.' + edge and r['text'] == str(index)) + 1
    rows[at:at] = [dict(stage='client.error', text=text, tid=1) for text in texts]
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (folder / 'client-stdio.txt').write_text(''.join(
        'ArmPort zone: 1 client.error ' + text + ' tid=1\n' for text in texts))


class OriginalDataErrorTests(unittest.TestCase):
    def fixture(self, texts=(TEXT,), index=1, after=False):
        case = evidence.ReceiverEvidenceTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        add_errors(case.path, texts, index, after)
        return case

    def test_committed_exact_occurrence_only_with_opt_in(self):
        case = self.fixture()
        with self.assertRaises(evidence.replay.DispatchGameErrors):
            case.check()
        result = case.check(original_texture_exception=True)
        self.assertEqual(result['dispatch_game_errors'], 1)
        self.assertEqual(result['accepted_original_data_errors'], [dict(
            text=TEXT, count=1, dispatch_index=1, after_dispatch_index=None)])
        for field in ('m3_replay_complete', 'state_comparison_complete', 'state_schema_complete'):
            self.assertFalse(result[field])

    def test_missing_added_changed_and_moved_occurrences_fail(self):
        for texts, index, after in (((), 1, False), ((TEXT, TEXT), 1, False),
                ((TEXT.lower(),), 1, False), ((TEXT.replace('FEM', 'MALE'),), 1, False),
                ((TEXT.replace('HIPS_miniskirt_1', 'face_skin_head_09'),), 1, False),
                ((TEXT, 'mission.c: Room 2 has no tray'), 1, False),
                ((TEXT, 'unrelated error'), 1, False), ((TEXT,), 0, False),
                ((TEXT,), 1, True)):
            with self.subTest(texts=texts, index=index, after=after):
                with self.assertRaisesRegex(ValueError, 'literal texts/counts/indices'):
                    self.fixture(texts, index, after).check(original_texture_exception=True)

    def test_opt_in_cannot_bypass_wine_cursor_ack_hash_or_trace_integrity(self):
        for change in ('wine', 'cursor', 'ack', 'hash', 'trace'):
            with self.subTest(change=change):
                case = self.fixture()
                if change == 'wine':
                    case.wine.write_text('0024:trace:seh:dispatch_exception code=c0000005 flags=0\n')
                elif change == 'cursor':
                    next(r for r in case.rows if r['type'] == 'cursor')['actual'] -= 1
                elif change == 'ack':
                    next(r for r in case.rows if r['type'] == 'ack')['packet_id'] = 99
                elif change == 'hash':
                    (case.path / 'state-116.json').write_text('{}')
                else:
                    p = case.path / 'zone-trace.jsonl'
                    p.write_text(p.read_text().replace('replay.drain.end', 'missing.drain'))
                with self.assertRaises(ValueError):
                    case.check(original_texture_exception=True)

    def test_changed_proof_or_out_of_scope_policy_rejected(self):
        original = json.loads(exception.POLICY.read_text())
        variants = []
        changed = copy.deepcopy(original)
        changed['proof_sha256']['assets/catalog.json'] = '0' * 64
        variants.append(changed)
        for update in ({'text': 'mission.c: Room 2 has no tray'},
                       {'text': TEXT.replace('HIPS_miniskirt_1', 'new_texture')},
                       {'text': None}, {'count': True}, {'count': 0},
                       {'dispatch_index': 117}, {'after_dispatch_index': 1}):
            changed = copy.deepcopy(original)
            changed['occurrences'][0].update(update)
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed['occurrences'] *= 2
        variants.append(changed)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'policy.json'
            for policy in variants:
                path.write_text(json.dumps(policy))
                with self.subTest(policy=policy['occurrences']):
                    with self.assertRaises(ValueError):
                        exception.load_policy(path)

    def comparison_fixture(self):
        case = comparison.StateComparison()
        self.addCleanup(case.doCleanups)
        root = case.fixture()
        for target in ('arm64', 'i686'):
            path = root / target / 'report.json'
            report = json.loads(path.read_text())
            report['original_texture_exception'] = True
            path.write_text(json.dumps(report))
            for label in ('id1-a', 'id1-b', 'id31'):
                add_errors(root / target / label)
        return root

    def test_six_run_comparison_retains_exception_and_partial_scope(self):
        root = self.comparison_fixture()
        result = comparison.compare(root, 'a' * 40, original_texture_exception=True)
        self.assertTrue(result['partial_state_equal'])
        self.assertEqual(result['accepted_original_data_errors'][0]['text'], TEXT)
        self.assertFalse(result['m3_replay_complete'])
        with self.assertRaisesRegex(ValueError, 'identity or execution'):
            comparison.compare(root, 'a' * 40)
        path = root / 'i686/id31/zone-trace.jsonl'
        path.write_text(path.read_text().replace(TEXT, TEXT.lower()))
        with self.assertRaises(ValueError):
            comparison.compare(root, 'a' * 40, original_texture_exception=True)

    def test_success_report_cannot_rescue_signal_or_host_timeout(self):
        root = self.comparison_fixture()
        path = root / 'arm64/id1-a/process-observation.json'
        for process in ({'returncode': -9}, {'returncode': 2, 'host_timeout_kill': True}, {}):
            path.write_text(json.dumps(process))
            with self.subTest(process=process):
                with self.assertRaisesRegex(ValueError, 'process exit or timeout'):
                    comparison.compare(root, 'a' * 40, original_texture_exception=True)


if __name__ == '__main__':
    unittest.main()
