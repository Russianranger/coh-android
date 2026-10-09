"""Bounded failed-save evidence without accepting unwitnessed DayJob grants."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_reopen_diagnostic as guest
import test_character_reopen_guest as reopen


def power_change():
    fixture = json.loads((ROOT / 'tools/android/interactive/fixtures/'
        'thor-training-normalization-0.13.13-20261005.json').read_text())
    before = fixture['sessions'][0]['saved_rows']['powers']
    attributes = fixture['attributes'] + [dict(id=2344, name='day_job_powers'),
                                         dict(id=2449, name='day_job_movement_increase_lesser')]
    added = dict(containerid=1, subid=0, powerid=1, categoryname=2312,
        powersetname=2344, powername=2449, powerlevelbought=1,
        powernumboostsbought=None, powersetlevelbought=None, buildnum=None,
        uniqueid=680838905)
    after = [added] + copy.deepcopy(before)
    for i, row in enumerate(after):
        row.update(subid=i, powerid=i + 1)
    return before, after, attributes


class StockPowerDeltaTests(unittest.TestCase):
    def test_exact_commuter_candidate_retains_all_fifteen_original_semantic_powers_without_grant_claim(self):
        before, after, attributes = power_change()
        original = copy.deepcopy((before, after, attributes))
        result = server.stock_power_delta(before, after, attributes)
        self.assertEqual((result['before_power_count'], result['after_power_count']), (15, 16))
        self.assertEqual(result['stock_compatible_candidate'], server.COMMUTER_POWER)
        self.assertTrue(result['prior_powers_preserved_by_uniqueid'])
        self.assertTrue(result['all_prior_semantic_fields_preserved'])
        self.assertTrue(result['current_native_indexes_contiguous'])
        self.assertEqual(result['added_powers'][0]['uniqueid'], 680838905)
        self.assertEqual(result['deleted_uniqueids'], [])
        self.assertEqual(result['changed_prior_powers'], [])
        for field in ('save_acceptance_changed', 'dayjob_grant_verified', 'login_eligibility_verified',
                      'spatial_predicates_verified', 'badge_predicates_verified', 'sql_game_mutations_performed'):
            self.assertIs(result[field], False)
        self.assertEqual((before, after, attributes), original)

    def test_change_or_delete_of_any_original_semantic_field_is_never_preserved(self):
        before, after, attributes = power_change()
        for field in set(server.evidence.SELECTED['powers']) - {'subid', 'powerid', 'uniqueid'}:
            changed = copy.deepcopy(after)
            changed[1][field] = 1 if changed[1][field] is None else changed[1][field] + 1
            with self.subTest(field=field):
                result = server.stock_power_delta(before, changed, attributes)
                self.assertNotIn('stock_compatible_candidate', result)
                self.assertIsNot(result.get('all_prior_semantic_fields_preserved'), True)
        deleted = after[:1] + after[2:]
        result = server.stock_power_delta(before, deleted, attributes)
        self.assertFalse(result['prior_powers_preserved_by_uniqueid'])
        self.assertEqual(result['deleted_uniqueids'], [before[0]['uniqueid']])
        self.assertNotIn('stock_compatible_candidate', result)

    def test_only_positive_unique_typed_identifiers_and_finite_counts_describe_preservation(self):
        before, after, attributes = power_change()
        for value in (None, True, 0, -1, '1', 2**31):
            changed = copy.deepcopy(after); changed[1]['uniqueid'] = value
            with self.subTest(value=value):
                self.assertEqual(server.stock_power_delta(before, changed, attributes)['status'], 'unavailable')
        duplicate = copy.deepcopy(after); duplicate[2]['uniqueid'] = duplicate[1]['uniqueid']
        for changed in (duplicate, after * 9, [], [dict(after[0], extra=1)]):
            self.assertEqual(server.stock_power_delta(before, changed, attributes)['status'], 'unavailable')

    def test_wrong_name_extra_addition_or_noncontiguous_packing_cannot_label_commuter_candidate(self):
        before, after, attributes = power_change()
        wrong_names = copy.deepcopy(attributes); wrong_names[-1]['name'] = 'day_job_movement_increase_greater'
        self.assertNotIn('stock_compatible_candidate', server.stock_power_delta(before, after, wrong_names))
        unknown = copy.deepcopy(after); unknown[0]['powername'] = 987654321
        self.assertEqual(server.stock_power_delta(before, unknown, attributes)['status'], 'unavailable')
        extra = copy.deepcopy(after) + [dict(after[0], uniqueid=680838906, subid=16, powerid=17)]
        self.assertNotIn('stock_compatible_candidate', server.stock_power_delta(before, extra, attributes))
        for field, value in (('subid', 1), ('powerid', 2), ('powerlevelbought', True),
                             ('powerlevelbought', 2), ('powernumboostsbought', 0),
                             ('powersetlevelbought', 0), ('buildnum', 0)):
            changed = copy.deepcopy(after); changed[0][field] = value
            with self.subTest(field=field, value=value):
                self.assertNotIn('stock_compatible_candidate', server.stock_power_delta(before, changed, attributes))

    def test_attribute_identity_must_be_unique_typed_and_bounded(self):
        before, after, attributes = power_change()
        for mapping in (attributes * 2, [dict(attributes[0], id=True)] + attributes[1:],
                        [dict(attributes[0], name='x' * 256)] + attributes[1:]):
            self.assertEqual(server.stock_power_delta(before, after, mapping)['status'], 'unavailable')

    def test_stock_candidate_contract_is_bound_to_retained_native_and_data_bytes(self):
        for prefix, files in ((ROOT / 'upstream/ouroboros', server.STOCK_DAYJOB_NATIVE_INPUTS),
                              (ROOT / 'upstream/i24', server.STOCK_DAYJOB_DATA_INPUTS)):
            for name, digest in files.items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256((prefix / name).read_bytes()).hexdigest(), digest)
        jobs = (ROOT / 'upstream/i24/data/defs/generic/jobs.dayjobs').read_text()
        powers = (ROOT / 'upstream/i24/data/defs/powers/temporary_powers_day_job_powers.powers').read_text()
        self.assertIn('VolumeName DJ_TrainStation', jobs)
        self.assertIn(server.COMMUTER_POWER, jobs)
        self.assertTrue(re.search(r'LifeTimeInGame\s+7200\b', powers))


class FailedSnapshotTests(unittest.TestCase):
    def instance(self):
        return reopen.ReopenServerTests.instance(self)

    def changed_save(self, d):
        rows = reopen.ReopenServerTests.prepare_normal_logout(self, d)
        d.schema['expected_attributes']['attributes'] += [dict(id=2312, name='temporary_powers'),
            dict(id=2344, name='day_job_powers'), dict(id=2449, name='day_job_movement_increase_lesser')]
        _, added, _ = power_change()
        rows['powers'].insert(0, added[0])
        for i, row in enumerate(rows['powers']): row.update(subid=i, powerid=i + 1)
        return rows

    def test_typed_after_snapshot_and_semantic_delta_export_but_strict_gate_still_fails(self):
        d = self.instance(); rows = self.changed_save(d)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'after reopen: powers'):
            d.validate_saved_rows(rows, self.inventory)
        self.assertFalse(guest.save_verified(d.creation_report, reopen.SESSION))
        self.assertFalse(d.creation_report['verified'])
        self.assertFalse(d.creation_report['committed_sql_verified'])
        self.assertFalse(d.creation_report['powers_preserved'])
        self.assertFalse(d.creation_report['costume_preserved'])
        self.assertIsNone(d.snapshot)
        failure = d.creation_report['save_comparison_failure']
        self.assertEqual(failure['failed_table'], 'powers')
        self.assertFalse(failure['save_verified'])
        self.assertTrue(failure['power_delta']['prior_powers_preserved_by_uniqueid'])
        target = d.owner.args.state / 'export'; target.mkdir()
        calls = d.sql_rows.call_count
        with patch.object(server.LocalCharacterServer, 'collect'):
            d.collect(target)
        exported = json.loads((target / 'character-reopen-failed-after-snapshot.json').read_text())
        self.assertEqual(exported['snapshot']['rows'], rows)
        self.assertEqual(exported['snapshot_sha256'], failure['after_snapshot_sha256'])
        self.assertEqual(exported['status'], 'failed')
        self.assertFalse(exported['save_verified'])
        self.assertFalse((target / 'character-saved-snapshot.json').exists())
        self.assertEqual(d.sql_rows.call_count, calls)

    def test_malformed_sql_never_produces_a_typed_failure_snapshot(self):
        for change in ('foreign', 'bad_attribute', 'extra_field'):
            d = self.instance(); rows = self.changed_save(d)
            if change == 'foreign': rows['powers'][0]['containerid'] = 2
            if change == 'bad_attribute': rows['powers'][0]['powername'] = 987654321
            if change == 'extra_field': rows['powers'][0]['password'] = 'not_exported'
            with self.subTest(change=change), self.assertRaises(server.base.DiagnosticError):
                d.validate_saved_rows(rows, self.inventory)
            self.assertIsNone(d.failed_after_snapshot)
            self.assertNotIn('save_comparison_failure', d.creation_report)

    def test_unchanged_original_save_still_passes_without_any_failure_artifact(self):
        d = self.instance(); rows = reopen.ReopenServerTests.prepare_normal_logout(self, d)
        result = d.validate_saved_rows(rows, self.inventory)
        self.assertEqual(result['rows'], rows)
        self.assertIsNone(d.failed_after_snapshot)
        self.assertNotIn('save_comparison_failure', d.creation_report)

    def test_snapshot_export_bound_does_not_mask_the_original_strict_comparison_failure(self):
        d = self.instance(); rows = self.changed_save(d)
        with patch.object(server, 'SNAPSHOT_LIMIT', 32), \
                self.assertRaisesRegex(server.base.DiagnosticError, 'after reopen: powers'):
            d.validate_saved_rows(rows, self.inventory)
        self.assertIsNone(d.failed_after_snapshot)
        self.assertEqual(d.creation_report['save_comparison_failure']['after_snapshot_export_status'],
                         'exceeded_bounded_export_scope')
        self.assertFalse(d.creation_report['verified'])


class StockLifecycleTests(unittest.TestCase):
    def instance(self):
        return reopen.ReopenServerTests.instance(self)

    def enable(self, d):
        d.owner.client_renderer_attribution = True
        d.owner.client_executable_sha256 = 'a' * 64
        d.ctx.report['client_renderer_attribution'] = dict(verified=True, client_executable_sha256='a' * 64,
            manifest_sha256='b' * 64, repository_commit='c' * 40,
            source_freshness_preserved=True, renderer_changed=False)

    def fixture(self, d):
        observations = {
            'ents': [dict(containerid=1, lastactive='2026-10-08T00:00:00')],
            'ents2': [dict(containerid=1, subid=0, lastdayjobsstart='2026-10-08T00:00:00')],
            'powers': [dict(containerid=1, subid=row['subid'], uniqueid=row['uniqueid'],
                numcharges=None, usagetime=120.5, availabletime=0, creationtime=844000000)
                for row in self.rows['powers']]}
        d.sql_rows = Mock(side_effect=lambda table, *args: copy.deepcopy(observations[table]))
        return observations

    def test_legacy_or_unverified_producer_cannot_add_supplemental_sql_queries(self):
        d = self.instance(); original = d.sql_rows.call_count
        for activate in (False, True):
            d.owner.client_renderer_attribution = activate
            self.assertEqual(d.stock_power_lifecycle(self.rows)['status'], 'unavailable')
            self.assertEqual(d.sql_rows.call_count, original)
        self.enable(d)
        for field, value in (('verified', 1), ('client_executable_sha256', 'd' * 64),
                             ('manifest_sha256', 'bad'), ('repository_commit', 'bad'),
                             ('source_freshness_preserved', False), ('renderer_changed', True)):
            valid = copy.deepcopy(d.ctx.report['client_renderer_attribution'])
            d.ctx.report['client_renderer_attribution'][field] = value
            with self.subTest(field=field):
                self.assertEqual(d.stock_power_lifecycle(self.rows)['status'], 'unavailable')
                self.assertEqual(d.sql_rows.call_count, original)
            d.ctx.report['client_renderer_attribution'] = valid

    def test_current_producer_captures_only_three_finite_read_only_observations_and_no_grant_proof(self):
        d = self.instance(); self.enable(d); observations = self.fixture(d)
        before = copy.deepcopy((self.rows, observations))
        result = d.stock_power_lifecycle(self.rows)
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(d.sql_rows.call_count, 3)
        self.assertEqual(result['powers'], observations['powers'])
        self.assertEqual(result['timestamps']['lastdayjobsstart'], '2026-10-08T00:00:00')
        self.assertEqual(result['native_last_time_column'], 'ents.lastactive')
        self.assertFalse(result['dayjob_grant_verified'])
        self.assertFalse(result['login_eligibility_verified'])
        self.assertFalse(result['spatial_predicates_verified'])
        self.assertFalse(result['sql_game_mutations_performed'])
        self.assertEqual((self.rows, observations), before)
        for call in d.sql_rows.call_args_list:
            self.assertEqual(call.args[-1], 'containerid=1')
            self.assertNotIn('password', call.args[1])

    def test_new_lane_captures_baseline_and_after_logout_but_optional_failure_cannot_change_save_acceptance(self):
        d = self.instance(); self.enable(d)
        # Keep the original selected rows and position query fixture. Only the
        # new, finite supplemental SELECT shapes get a diagnostic response.
        original = d.sql_rows.side_effect
        observations = {
            ('containerid', 'lastactive'): [dict(containerid=1, lastactive=None)],
            ('containerid', 'subid', 'lastdayjobsstart'): [dict(containerid=1, subid=0, lastdayjobsstart=None)],
            ('containerid', 'subid', 'uniqueid', 'numcharges', 'usagetime', 'availabletime', 'creationtime'):
                [dict(containerid=1, subid=0, uniqueid=1, numcharges=None, usagetime=None,
                      availabletime=None, creationtime=None)]}
        d.sql_rows.side_effect = lambda table, fields, *args: copy.deepcopy(observations[fields]) \
            if fields in observations else original(table, fields, *args)
        rows = reopen.ReopenServerTests.prepare_normal_logout(self, d)
        self.assertEqual(d.creation_report['stock_power_lifecycle_before_login']['status'], 'observed')
        result = d.validate_saved_rows(rows, self.inventory)
        self.assertEqual(d.creation_report['stock_power_lifecycle_after_logout']['status'], 'observed')
        self.assertEqual(result['rows'], rows)
        self.assertIsNone(d.failed_after_snapshot)
        observations[('containerid', 'lastactive')][0]['containerid'] = 2
        result = d.validate_saved_rows(rows, self.inventory)
        self.assertEqual(d.creation_report['stock_power_lifecycle_after_logout']['status'], 'unavailable')
        self.assertEqual(result['rows'], rows)
        self.assertTrue(d.creation_report['committed_native_position_verified'])

    def test_foreign_identity_extra_columns_nonfinite_values_and_sql_failure_remain_optional_unavailable(self):
        for failure in ('identity', 'uid', 'extra', 'timestamp', 'number', 'sql'):
            d = self.instance(); self.enable(d); observations = self.fixture(d)
            if failure == 'identity': observations['ents'][0]['containerid'] = True
            if failure == 'uid': observations['powers'][0]['uniqueid'] += 1
            if failure == 'extra': observations['powers'][0]['extra'] = 1
            if failure == 'timestamp': observations['ents2'][0]['lastdayjobsstart'] = 'bad'
            if failure == 'number': observations['powers'][0]['usagetime'] = float('inf')
            if failure == 'sql': d.sql_rows.side_effect = OSError('not exported')
            with self.subTest(failure=failure):
                result = d.stock_power_lifecycle(self.rows)
                self.assertEqual(result['status'], 'unavailable')
                self.assertNotIn('timestamps', result)
                self.assertNotIn('powers', result)
                self.assertNotIn('not exported', result['reason'])


if __name__ == '__main__':
    unittest.main()
