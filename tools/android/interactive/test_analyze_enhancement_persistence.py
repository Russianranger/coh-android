"""Offline persistence observations retain relation, bounds and proof limits."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import analyze_enhancement_persistence as analyzer


def observation(*, login_count=1):
    power = dict(containerid=1, subid=0, powerid=1, uniqueid=7, buildnum=None,
                 categoryname=1, powersetname=2, powername=3)
    boost = {field: None for field in analyzer.BOOST_FIELDS}
    boost.update(containerid=1, subid=0, powerid=1, idx=None,
                 categoryname=4, powersetname=5, boostname=6, level=None)
    return {'format': 1, 'identity': dict(containerid=1, authid=123,
        authname='COHLOCAL', name='THORHERO'), 'login_count': login_count,
        'rows': {'powers': [power], 'boosts': [boost]},
        'attribute_rows': [{'id': number, 'name': name} for number, name in enumerate(
            ('Inherent', 'InherentSet', 'Sprint', 'Boosts', 'Generic_Endurance_Discount', 'EnduranceDiscount'), 1)]}


class EnhancementObservationTests(unittest.TestCase):
    def pair(self):
        return observation(), observation(login_count=2)

    def test_contract_reads_pinned_actual_generated_schema_and_native_boost_fields(self):
        contract = analyzer.generated_contract()
        self.assertEqual(contract['generated_template_sha256'], analyzer.TEMPLATE_SHA256)
        self.assertEqual(contract['boost_fields'], list(analyzer.BOOST_FIELDS))
        self.assertEqual(len(contract['boost_fields']), 34)
        self.assertEqual(contract['max_boost_rows'], 6010)
        self.assertFalse(contract['query_executed'])
        self.assertFalse(contract['device_validation'])

    def test_query_has_one_readonly_consistent_observation_and_complete_relations(self):
        sql = analyzer.query()
        self.assertTrue(sql.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;'))
        self.assertTrue(sql.endswith('COMMIT;\n'))
        self.assertIn('FROM dbo.boosts WHERE containerid=1', sql)
        self.assertIn('FROM dbo.attributes WHERE id IN (', sql)
        self.assertIn('slottedpowerupsmask', sql)
        self.assertIn('powerupslotid9', sql)
        self.assertNotRegex(sql, r'\b(?:INSERT|UPDATE|DELETE|ALTER|DROP|CREATE)\b')

    def test_query_refuses_untrusted_noninteger_or_negative_character_id(self):
        for value in (True, 0, -1, 2**31, '1; DELETE FROM dbo.boosts'):
            with self.subTest(value=value), self.assertRaises(analyzer.EvidenceError):
                analyzer.query(value)

    def test_slotted_equal_observation_never_becomes_authenticated_sql_or_device_proof(self):
        before, after = self.pair()
        after['session_id'] = 'a' * 32  # A self-declaration has no authority.
        result = analyzer.compare(before, after)
        self.assertEqual(result['status'], 'observed_equal')
        self.assertTrue(result['semantic_rows_equal'])
        self.assertTrue(result['nonempty_enhancements_observed'])
        for field in ('session_attribution_verified', 'committed_sql_verified',
                      'enhancement_persistence_verified', 'physical_device_verified',
                      'observed_snapshot_schema_verified', 'query_executed', 'ordinary_save_gates_changed'):
            self.assertFalse(result[field])

    def test_existing_032_snapshot_without_boosts_is_missing_evidence(self):
        before, after = self.pair()
        for value in (before, after):
            value['rows'].pop('boosts')
            value.pop('attribute_rows')
        result = analyzer.compare(before, after)
        self.assertEqual(result['status'], 'missing_evidence')
        self.assertIsNone(result['semantic_rows_equal'])
        self.assertEqual(result['missing_snapshot_sides'], ['before', 'after'])
        self.assertFalse(result['enhancement_persistence_verified'])

    def test_partial_boost_payload_is_refused_rather_than_compared_as_complete(self):
        before, after = self.pair()
        after['rows']['boosts'][0].pop('powerupslotid9')
        with self.assertRaisesRegex(analyzer.EvidenceError, 'Incomplete'):
            analyzer.compare(before, after)

    def test_unknown_missing_and_boolean_format_is_refused(self):
        for version in (None, True, 2, '1'):
            before, after = self.pair()
            after['format'] = version
            with self.subTest(version=version), self.assertRaisesRegex(analyzer.EvidenceError, 'format'):
                analyzer.compare(before, after)

    def test_missing_attribute_mapping_is_not_an_enhancement_equality_result(self):
        before, after = self.pair()
        after['attribute_rows'] = after['attribute_rows'][:-1]
        with self.assertRaisesRegex(analyzer.EvidenceError, 'name mapping'):
            analyzer.compare(before, after)

    def test_inventory_uses_powerid_minus_one_and_positive_slot_not_stale_comment(self):
        before, after = self.pair()
        for value in (before, after):
            value['rows']['boosts'][0].update(powerid=-1, idx=8)
        self.assertEqual(analyzer.compare(before, after)['status'], 'observed_equal')
        after['rows']['boosts'][0]['idx'] = -1
        with self.assertRaisesRegex(analyzer.EvidenceError, 'slot index'):
            analyzer.compare(before, after)

    def test_row_and_serialized_power_id_reordering_preserves_same_stable_slotted_power(self):
        before, after = self.pair()
        after['rows']['powers'][0].update(subid=9, powerid=12)
        after['rows']['boosts'][0].update(subid=5, powerid=12)
        self.assertEqual(analyzer.compare(before, after)['status'], 'observed_equal')
        after['rows']['powers'][0]['uniqueid'] = 8
        self.assertEqual(analyzer.compare(before, after)['status'], 'observed_changed')

    def test_dangling_or_ambiguous_power_relation_is_refused(self):
        for mutant in ('missing', 'duplicate'):
            before, after = self.pair()
            if mutant == 'missing':
                after['rows']['powers'][0]['powerid'] = 2
            else:
                after['rows']['powers'].append(copy.deepcopy(after['rows']['powers'][0]))
            with self.subTest(mutant=mutant), self.assertRaises(analyzer.EvidenceError):
                analyzer.compare(before, after)

    def test_lost_boost_moved_slot_and_changed_level_or_name_are_observed_changes(self):
        for mutation in ('lost', 'slot', 'level', 'name', 'powerup', 'float_type'):
            before, after = self.pair()
            if mutation == 'lost':
                after['rows']['boosts'] = []
            else:
                boost = after['rows']['boosts'][0]
                if mutation == 'slot': boost['idx'] = 1
                if mutation == 'level': boost['level'] = 2
                if mutation == 'name': after['attribute_rows'][-1]['name'] = 'DifferentEnhancement'
                if mutation == 'powerup': boost['powerupslotid9'] = 99
                if mutation == 'float_type': boost['var0'] = 0.0
            with self.subTest(mutation=mutation):
                self.assertEqual(analyzer.compare(before, after)['status'], 'observed_changed')

    def test_empty_boost_arrays_do_not_establish_nonempty_enhancement_preservation(self):
        before, after = self.pair()
        before['rows']['boosts'] = after['rows']['boosts'] = []
        result = analyzer.compare(before, after)
        self.assertEqual(result['status'], 'observed_equal')
        self.assertFalse(result['nonempty_enhancements_observed'])
        self.assertFalse(result['enhancement_persistence_verified'])

    def test_wrong_character_identity_or_nonconsecutive_login_count_is_refused(self):
        for mutation in ('identity', 'count'):
            before, after = self.pair()
            if mutation == 'identity': after['identity']['authid'] = 124
            else: after['login_count'] = 4
            with self.subTest(mutation=mutation), self.assertRaises(analyzer.EvidenceError):
                analyzer.compare(before, after)

    def test_duplicate_boost_location_and_foreign_boost_rows_are_refused(self):
        for mutation in ('location', 'foreign', 'slot_bound', 'subid'):
            before, after = self.pair()
            boost = after['rows']['boosts'][0]
            if mutation in ('location', 'subid'):
                extra = copy.deepcopy(boost)
                extra['subid'] = 1 if mutation == 'location' else 0
                after['rows']['boosts'].append(extra)
            if mutation == 'foreign': boost['containerid'] = 2
            if mutation == 'slot_bound': boost['idx'] = 6
            with self.subTest(mutation=mutation), self.assertRaises(analyzer.EvidenceError):
                analyzer.compare(before, after)

    def test_nonfinite_boolean_negative_and_oversized_rows_are_refused(self):
        for mutation in ('nan', 'bool', 'negative', 'rows'):
            before, after = self.pair()
            boost = after['rows']['boosts'][0]
            if mutation == 'nan': boost['var0'] = float('nan')
            if mutation == 'bool': boost['level'] = True
            if mutation == 'negative': boost['numcombines'] = -1
            if mutation == 'rows': after['rows']['boosts'] *= 6011
            with self.subTest(mutation=mutation), self.assertRaises(analyzer.EvidenceError):
                analyzer.compare(before, after)

    def test_duplicate_json_keys_and_nonfinite_json_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'observation.json'
            for raw in ('{"rows":{},"rows":{"boosts":[]}}', '{"number":NaN}'):
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(analyzer.EvidenceError):
                    analyzer.read_json(path)


if __name__ == '__main__':
    unittest.main()
