"""Only the agreed lifecycle-ID fields may change in ID-sensitivity checks."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'replay'))
from compare_state import canonical_initial_ids, differences, compare, INITIAL_CHANNEL_IDS, ATTRIBUTE_ID_SCHEMAS
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
                (run / 'process-observation.json').write_text(json.dumps(dict(returncode=2)))
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
                        value['entities'][0]['pkt_id_pos'] = [31, 32]
                        value['entities'][0]['pkt_id_qrot'] = [31, 155, 0]
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

    def test_startup_errors_require_literal_matching_counts_in_all_six_runs(self):
        root = self.fixture()
        for target in ('arm64', 'i686'):
            for label in ('id1-a', 'id1-b', 'id31'):
                run = root / target / label
                trace = run / 'zone-trace.jsonl'
                trace.write_text(json.dumps(dict(stage='client.error', text='literal DATA gap', tid=1)) + '\n' + trace.read_text())
                (run / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error literal DATA gap tid=1\n')
        self.assertTrue(compare(root, 'a' * 40)['outside_error_inventories_equal'])
        run = root / 'i686/id31'
        trace = run / 'zone-trace.jsonl'
        good = trace.read_text()
        trace.write_text(good.replace('literal DATA gap', 'literal data gap'))
        with self.assertRaisesRegex(ValueError, 'inventories or counts differ'):
            compare(root, 'a' * 40)
        trace.write_text(json.dumps(dict(stage='client.error', text='literal DATA gap', tid=1)) + '\n' + good)
        (run / 'client-stdio.txt').write_text('ArmPort zone: 1 client.error literal DATA gap tid=1\n' * 2)
        with self.assertRaisesRegex(ValueError, 'inventories or counts differ'):
            compare(root, 'a' * 40)

    def test_unreviewed_receive_channel_ids_remain_literal_in_sensitivity_comparison(self):
        root = self.fixture()
        for target in ('arm64', 'i686'):
            for label in ('id1-a', 'id1-b', 'id31'):
                run = root / target / label
                path = run / 'state-000.json'
                value = json.loads(path.read_text())
                initial_id = 31 if label == 'id31' else 1
                value['entities'][0]['packet_order'] = dict(pkt_id_unreviewed=initial_id, pkt_id_costume=32)
                self.assertEqual(canonical_initial_ids(value, initial_id)['entities'][0]['packet_order'],
                                 value['entities'][0]['packet_order'])
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                rows = [json.loads(line) for line in (run / 'receiver.jsonl').read_text().splitlines()]
                for row in rows:
                    if row['type'] == 'state' and row['index'] == 0:
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                (run / 'receiver.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
        result = compare(root, 'a' * 40)
        self.assertFalse(result['partial_state_equal'])
        for comparison in result['comparisons']:
            self.assertEqual(comparison['equal'], not comparison['id_sensitivity'])
            if comparison['id_sensitivity']:
                self.assertEqual(comparison['mismatches'], [dict(index=0, fields=['$.entities[0].packet_order.pkt_id_unreviewed'])])

    def test_nested_attribute_ids_remain_literal_in_sensitivity_comparison(self):
        root = self.fixture()
        for target in ('arm64', 'i686'):
            for label in ('id1-a', 'id1-b', 'id31'):
                run = root / target / label
                path = run / 'state-000.json'
                value = json.loads(path.read_text())
                initial_id = 31 if label == 'id31' else 1
                value['entities'][0]['attribute_packet_order'] = dict(self=[dict(field='CurrentAttribs', ids=[dict(field='HitPoints', ids=initial_id)])], basic=None)
                self.assertEqual(canonical_initial_ids(value, initial_id)['entities'][0]['attribute_packet_order'],
                                 value['entities'][0]['attribute_packet_order'])
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                rows = [json.loads(line) for line in (run / 'receiver.jsonl').read_text().splitlines()]
                for row in rows:
                    if row['type'] == 'state' and row['index'] == 0:
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                (run / 'receiver.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
        result = compare(root, 'a' * 40)
        self.assertFalse(result['partial_state_equal'])
        for comparison in result['comparisons']:
            self.assertEqual(comparison['equal'], not comparison['id_sensitivity'])
            if comparison['id_sensitivity']:
                self.assertEqual(comparison['mismatches'], [dict(index=0, fields=['$.entities[0].attribute_packet_order.self[0].ids[0].ids'])])

    def initial_observations(self, packet_id):
        # Independent schema fixture, copied from the original attrib_net tables.
        def rows(names):
            return [dict(field=name, ids=packet_id) for name in names.split()]
        low = 'HitPoints Absorb Endurance Meter StealthRadiusPlayer'
        high = 'HitPoints Absorb Endurance Meter PerceptionRadius StealthRadiusPlayer Confused'
        levels = 'Level CombatLevel'
        return dict(entities=[dict(pkt_id_create=0, pkt_id_pos=[], pkt_id_qrot=[], player=None,
            packet_order={name: packet_id for name in INITIAL_CHANNEL_IDS},
            attribute_packet_order=dict(
                basic=[dict(field='CurrentAttribs', ids=rows(low)), dict(field='MaxAttribs', ids=rows(low)), dict(field='SendLevels', ids=rows(levels))],
                self=[dict(field='CurrentAttribs', ids=rows(high + ' ToHit')), dict(field='MaxAttribs', ids=rows(high)), dict(field='SendLevels', ids=rows(levels))] + rows('ExperiencePoints ExperienceDebt ExperienceRest InfluencePoints')))],
            delete_history=[], friend_receive_id=packet_id)

    def test_approved_snapshot_zero_paths_and_input_immutability(self):
        a, b = self.initial_observations(1), self.initial_observations(31)
        original = copy.deepcopy(a)
        self.assertEqual(canonical_initial_ids(a, 1, 0), canonical_initial_ids(b, 31, 0))
        self.assertEqual(a, original)
        changed = list(differences(a, canonical_initial_ids(a, 1, 0)))
        self.assertEqual(len(changed), 50)  # 16 channels + 12 basic + 21 self + friend
        for index in (None, 1, 116, False, 0.0):
            self.assertEqual(canonical_initial_ids(a, 1, index), a)

    def test_wrong_values_and_adjacent_fields_stay_literal(self):
        for packet_id in (0, 2, 32, 155, True, 1.0, '1', None):
            value = self.initial_observations(packet_id)
            self.assertEqual(canonical_initial_ids(value, 1, 0), value)
        value = self.initial_observations(1)
        entity = value['entities'][0]
        entity['packet_order']['unknown_id'] = 1
        entity['attribute_packet_order']['unknown'] = [dict(field='HitPoints', ids=1)]
        entity['adjacent'] = dict(EntityRef=1, actor=1, taskforce_id=1, token_id=1,
            payload=1, sequence=1, NetFx=1, clock=1)
        result = canonical_initial_ids(value, 1, 0)
        self.assertEqual(result['entities'][0]['adjacent'], entity['adjacent'])
        self.assertEqual(result['entities'][0]['packet_order']['unknown_id'], 1)
        self.assertEqual(result['entities'][0]['attribute_packet_order']['unknown'], entity['attribute_packet_order']['unknown'])

    def test_schema_names_order_extra_fields_and_nulls_are_not_generalized(self):
        for mutate in (
                lambda rows: rows.reverse(),
                lambda rows: rows[0].update(field='Actor'),
                lambda rows: rows[0].update(extra=1),
                lambda rows: rows.append(dict(field='HitPoints', ids=1))):
            value = self.initial_observations(1)
            rows = value['entities'][0]['attribute_packet_order']['self'][0]['ids']
            mutate(rows)
            result = canonical_initial_ids(value, 1, 0)
            self.assertEqual(result['entities'][0]['attribute_packet_order']['self'][0]['ids'], rows)
        value = self.initial_observations(1)
        value['entities'][0]['attribute_packet_order']['basic'] = None
        result = canonical_initial_ids(value, 1, 0)
        self.assertIsNone(result['entities'][0]['attribute_packet_order']['basic'])

    def write_observations(self, root, index, labels=None, wrong_value=None):
        for target in ('arm64', 'i686'):
            for label in ('id1-a', 'id1-b', 'id31'):
                if labels is not None and (target, label) not in labels:
                    continue
                run = root / target / label
                path = run / f'state-{index:03d}.json'
                value = json.loads(path.read_text())
                packet_id = 31 if label == 'id31' else 1
                extra = self.initial_observations(packet_id)
                for key in ('packet_order', 'attribute_packet_order'):
                    value['entities'][0][key] = extra['entities'][0][key]
                value['friend_receive_id'] = packet_id if wrong_value is None else wrong_value
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                rows = [json.loads(line) for line in (run / 'receiver.jsonl').read_text().splitlines()]
                for row in rows:
                    if row['type'] == 'state' and row['index'] == index:
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                (run / 'receiver.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))

    def test_comparison_applies_new_rules_only_to_initial_sensitivity_pairs(self):
        root = self.fixture()
        self.write_observations(root, 0)
        result = compare(root, 'a' * 40)
        self.assertTrue(result['partial_state_equal'])
        self.assertFalse(result['m3_replay_complete'])
        for pair in result['comparisons']:
            self.assertEqual(pair['snapshot0_additional_canonicalization'] is not None, pair['id_sensitivity'])
        self.write_observations(root, 116)
        result = compare(root, 'a' * 40)
        self.assertFalse(result['partial_state_equal'])
        for pair in result['comparisons']:
            self.assertEqual(pair['equal'], not pair['id_sensitivity'])
            if pair['id_sensitivity']:
                self.assertEqual(pair['mismatches'][0]['index'], 116)

    def test_wrong_initial_value_and_same_id_target_difference_fail(self):
        root = self.fixture()
        self.write_observations(root, 0)
        self.write_observations(root, 0, {('i686', 'id1-a')}, wrong_value=31)
        result = compare(root, 'a' * 40)
        self.assertFalse(result['partial_state_equal'])
        failed_literal = [pair for pair in result['comparisons'] if not pair['id_sensitivity'] and not pair['equal']]
        self.assertGreaterEqual(len(failed_literal), 2)
        self.assertTrue(any('$.friend_receive_id' in mismatch['fields'] for pair in failed_literal for mismatch in pair['mismatches']))

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
        self.assertEqual(len(result['comparisons'][-1]['canonicalized_fields']), 5)

    def test_only_agreed_initial_id_fields_are_canonicalized(self):
        source = {'entities': [{'pkt_id_create': 1, 'id': 1, 'net_ipos': [1, 31, 1],
                  'pkt_id_pos': [1, 32], 'pkt_id_qrot': [1, 155, 0], 'player': {'lastClientStatePktId': 1}},
                  {'pkt_id_create': 32, 'pkt_id_pos': [32], 'pkt_id_qrot': [155], 'player': {'lastClientStatePktId': 155}}],
                  'delete_history': [{'pkt_id': 1, 'id': 1}, {'pkt_id': 32, 'id': 31}]}
        source['entities'][0]['character'] = {'power_inventory': {'unique_id': 1, 'build_levels': [1, 31]},
                                               'generic_inventories': {'id': 1, 'amount': 31}}
        source['entities'][0]['player']['badges'] = {'states': [1, 31], 'time_awarded': 1}
        source['badge_client'] = {'debug_display_mode': 1}
        source['entities'][0]['player']['costumes'] = {'current': 1, 'pending_number': 31, 'colors': [[1, 31]]}
        source['entities'][0]['groups'] = {'team_id': 1, 'league_id': 31, 'leader_db_id': 1}
        source['contacts'] = {'alignment_delay_seconds': [1, 31], 'known': [{'handle': 1}]}
        source['task_sets'] = [{'dbid': 1, 'tasks': [{'context': 31, 'timezero': 1}]}]
        source['group_map_names'] = {'team': ['1', '31']}
        result = canonical_initial_ids(source, 1)
        self.assertEqual(set(differences(source, result)), {
            '$.entities[0].pkt_id_create', '$.entities[0].player.lastClientStatePktId',
            '$.delete_history[0].pkt_id', '$.entities[0].pkt_id_pos[0]',
            '$.entities[0].pkt_id_qrot[0]'})
        self.assertEqual(source['entities'][0]['pkt_id_create'], 1)
        self.assertEqual(result['entities'][1], source['entities'][1])

    def test_literal_comparison_detects_schema_length_and_float_bit_differences(self):
        a = {'values': [0, 2147483648], 'extra': 1}
        b = {'values': [0, 0, 1]}
        self.assertEqual(list(differences(a, b)), ['$.keys', '$.values.length', '$.values[1]'])


if __name__ == '__main__':
    unittest.main()
