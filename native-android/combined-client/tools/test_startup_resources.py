#!/usr/bin/env python3
"""Attribution, privacy and malformed-input tests for offline additions."""
import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path

import analyze_startup_resources as a
import startup_operation_oracles as oracle
import startup_bench_resources as benchmark
sys.path.insert(0, str(a._BASE_PATH.parent))
from test_analyze_startup import app, guest, SID, OLD, SECRET


class ResourceTests(unittest.TestCase):
    def docs(self):
        return {'combined-report.json': app(), 'combined-server-latest-report.json': guest(SID, True)}

    def test_observed_warm_does_not_prove_beacon_reuse(self):
        out = a.analyze(self.docs(), None)
        now = out['attempts'][0]
        self.assertEqual(now['cache_classification'], 'warm_schema_restore_observed')
        self.assertEqual(now['detail']['cache_projection']['beacon']['status'], 'unknown')
        self.assertFalse(out['interpretation']['startup_improvement_measured'])

    def test_stale_receipt_not_bound(self):
        docs = self.docs(); docs['combined-server-latest-report.json'] = guest(OLD)
        now = a.analyze(docs, None)['attempts'][0]
        self.assertIsNone(now['detail'])
        self.assertEqual(now['cache_classification'], 'unknown')

    def test_geometry_exact_status(self):
        docs = self.docs(); docs['combined-server-latest-report.json']['geometry_preparation'] = {
            'status': 'reused_verified_required_geometry', 'worker_used': False, 'elapsed_seconds': 1.3}
        self.assertEqual(a.analyze(docs, None)['attempts'][0]['detail']['geometry']['status'],
                         'reused_verified_required_geometry')

    def test_refusal_is_fixed_allowlist(self):
        source = {'private_map_data': {'server_data_cache': {'reuse_refused': SECRET,
            'private_bytes': 5, 'immutable_directory_checks': True}},
            'atlas_beacon_graph': {'status': SECRET, 'archive_decoded': True},
            'prepared_server_caches': {'status': 'skipped_native_fallback', 'reason': SECRET}}
        out = a.projected_caches(source)
        self.assertNotIn(SECRET, json.dumps(out))
        self.assertEqual(out['server_data']['refusal_code'], 'unknown')
        self.assertIsNone(out['server_data']['immutable_directory_checks'])
        source['private_map_data']['server_data_cache']['reuse_refused'] = 'invalid_cache_pointer'
        self.assertEqual(a.projected_caches(source)['server_data']['refusal_code'], 'invalid_cache_pointer')

    def test_typed_refusals_not_echoed(self):
        for value in ([], {}, 42, True, None):
            out = a.projected_caches({'private_map_data': {'server_data_cache': {'reuse_refused': value}}})
            self.assertEqual(out['server_data']['refusal_code'], 'unknown')

    def test_oversize_output_rejected(self):
        docs = self.docs(); docs['combined-server-latest-report.json']['processes'][0]['output_bytes'] = a.base.LIMIT + 1
        with self.assertRaisesRegex(a.base.Rejected, 'PROCESS_OUTPUT_BOUND'):
            a.analyze(docs, None)

    def test_missing_output_bytes_rejected(self):
        docs = self.docs(); docs['combined-server-latest-report.json']['processes'][0].pop('output_bytes')
        with self.assertRaisesRegex(a.base.Rejected, 'PROCESS_OUTPUT_BOUND'):
            a.analyze(docs, None)

    def test_guest_elapsed_cannot_be_nonfinite_or_negative(self):
        for value in (float('nan'), -1, True, SECRET):
            docs = self.docs(); docs['combined-server-latest-report.json']['stage_history'] = [
                {'stage': 'local_atlas_startup', 'elapsed_seconds': value}]
            with self.assertRaisesRegex(a.base.Rejected, 'GUEST_STAGE_TIME'):
                a.analyze(docs, None)

    def test_sum_does_not_establish_aggregate_live_peak(self):
        detail = a.guest_detail(guest())
        self.assertEqual(detail['process_output']['sum_recorded_bytes'], 10)
        self.assertFalse(detail['process_output']['aggregate_live_peak_measured'])
        self.assertFalse(detail['process_output']['concurrent_process_overlap_measured'])

    def test_history_remains_separate_and_cross_version(self):
        docs = self.docs(); previous = app(OLD); previous['version_code'] = 5
        docs['combined-server-previous-attempts.json'] = {'attempts': [
            {'session_id': OLD, 'app': previous, 'guest': guest(OLD, True)}]}
        out = a.analyze(docs, None)
        self.assertEqual(len(out['attempts']), 2)
        self.assertFalse(out['observational_cohorts']['warm_schema_restore_observed']['same_version_code'])
        self.assertFalse(out['interpretation']['cohorts_are_matched_repeatable_experiments'])

    def test_private_values_and_ids_absent(self):
        docs = self.docs(); docs['combined-server-latest-report.json']['stage_history'] = [
            {'stage': SECRET, 'elapsed_seconds': 3, 'status': SECRET}]
        out = json.dumps(a.analyze(docs, None))
        for value in (SECRET, SID, OLD): self.assertNotIn(value, out)

    def test_input_documents_unchanged(self):
        docs = self.docs(); before = copy.deepcopy(docs)
        a.analyze(docs, None)
        self.assertEqual(docs, before)

    def test_cli_error_path_redacted(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output): code = a.main(['/no/' + SECRET])
        self.assertEqual(code, 2)
        self.assertNotIn(SECRET, output.getvalue())

    def test_duplicate_stage_is_not_summed(self):
        summary = a.base.app_summary(app())
        summary['stages'].append(summary['stages'][1].copy())
        self.assertIsNone(a.timing(summary)['db_and_atlas_ms'])

    def test_ready_uses_boundary_not_age(self):
        out = a.analyze(self.docs(), None)['attempts'][0]
        self.assertEqual(out['ready_boundary_ms'], 1100)
        self.assertEqual(out['timing']['db_and_atlas_ms'], 1000)
        self.assertEqual(out['timing']['other_startup_boundary_ms'], 100)

    def test_operation_unknowns_remain_unknown(self):
        out = a.cache_operations(a.projected_caches({}))['beacon']
        self.assertIsNone(out['decoded_without_graph_payload_write'])
        self.assertIsNone(out['marker_write_source_implied'])
        self.assertIsNone(out['suboperation_elapsed_seconds'])

    def test_operations_never_export_unknown_proof_or_fallback_text(self):
        p = a.projected_caches({'atlas_beacon_graph': {'input_full_byte_proof_reuse_policy': SECRET},
                               'prepared_server_caches': {'reason': SECRET}})
        self.assertNotIn(SECRET, json.dumps(a.cache_operations(p)))
        self.assertEqual(p['beacon']['shared_proof_policy'], 'unknown')

    def test_conflicting_cache_receipts_refused(self):
        for source in (
            {'status': 'reused_verified_graph', 'installed_files': 1},
            {'status': 'reused_verified_graph', 'input_payload_bytes_hashed': 1},
            {'status': 'reused_verified_graph', 'archive_decoded': True},
            {'status': 'installed_verified_graph', 'archive_decoded': False},
            {'input_full_byte_proof_reused_files': 0, 'input_full_byte_proof_reused_bytes': 12},
            {'input_full_byte_proof_reused_files': 3, 'input_files_checked': 2}):
            with self.subTest(source=source), self.assertRaisesRegex(a.base.Rejected, 'CACHE_RECEIPT_CONFLICT'):
                a.cache_operations(a.projected_caches({'atlas_beacon_graph': source}))
        with self.assertRaisesRegex(a.base.Rejected, 'CACHE_RECEIPT_CONFLICT'):
            a.cache_operations(a.projected_caches({'prepared_server_caches':
                {'status': 'preserved_existing_native_caches', 'installed_files': 1}}))

    def test_boundary_self_delta_is_not_combined_memory(self):
        row = {'stage': 'local_atlas_startup', 'boundary': 'entered', 'elapsed_ms': 100,
               'rss_kib': 120, 'peak_rss_kib': 900, 'children_peak_rss_kib': 700}
        out = a.resource_boundaries({'guest_resources': [row, {**row, 'boundary': 'leaving',
                                     'elapsed_ms': 1100, 'rss_kib': 115}]})
        pair = out['paired_stages'][0]
        self.assertEqual(pair['coordinator_rss_delta_kib'], -5)
        self.assertEqual(pair['receiver_boundary_interval_ms'], 1000)
        self.assertEqual(out['largest_adjacent_sample_gap_ms'], 1000)
        self.assertFalse(out['high_waters_summed'])
        self.assertFalse(out['android_server_overlap_measured'])

    def test_boundary_unknown_or_mismatched_row_breaks_pair(self):
        start = {'stage': 'local_atlas_startup', 'boundary': 'entered', 'elapsed_ms': 10, 'rss_kib': 5}
        end = {**start, 'boundary': 'leaving', 'elapsed_ms': 20}
        for middle in ({**start, 'stage': SECRET, 'elapsed_ms': 15},
                       {**start, 'elapsed_ms': None},
                       {**start, 'boundary': 'leaving', 'stage': 'local_dbserver_startup', 'elapsed_ms': 15}):
            out = a.resource_boundaries({'guest_resources': [start, middle, end]})
            self.assertEqual(out['paired_stages'], [])
            self.assertNotIn(SECRET, json.dumps(out))

    def test_boundary_clock_and_ring_bounds(self):
        row = {'stage': 'local_atlas_startup', 'boundary': 'entered', 'elapsed_ms': 10}
        with self.assertRaisesRegex(a.base.Rejected, 'RESOURCE_CLOCK_ORDER'):
            a.resource_boundaries({'guest_resources': [row, {**row, 'elapsed_ms': 9}]})
        with self.assertRaisesRegex(a.base.Rejected, 'ARRAY_BOUND_OR_TYPE'):
            a.resource_boundaries({'guest_resources': [row] * 33})
        self.assertEqual(a.resource_boundaries({'guest_resources': [row]})['paired_stages'], [])

    def test_missing_and_boolean_memory_never_become_zero(self):
        start = {'stage': 'local_atlas_startup', 'boundary': 'entered', 'elapsed_ms': 10, 'rss_kib': True}
        end = {**start, 'boundary': 'leaving', 'elapsed_ms': 20, 'rss_kib': 12}
        out = a.resource_boundaries({'guest_resources': [start, end]})
        self.assertIsNone(out['paired_stages'][0]['coordinator_rss_delta_kib'])

    def test_benchmark_rejects_unbounded_work_before_opening_input(self):
        for repeats, iterations in ((0, 1), (10, 1), (1, 0), (1, 101), (True, 1)):
            with self.assertRaisesRegex(a.base.Rejected, 'BENCHMARK_BOUND'):
                benchmark.benchmark('/no/' + SECRET, repeats, iterations)

    def test_benchmark_cli_error_path_redacted(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output): code = benchmark.main(['/no/' + SECRET])
        self.assertEqual(code, 2)
        self.assertNotIn(SECRET, output.getvalue())


class OriginalOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.fixture = oracle.original_beacon_cases()

    def test_original_beacon_counters_match_independent_file_operations(self):
        for case in self.fixture['cases']:
            with self.subTest(case=case['case']):
                receipt, observed = case['receipt'], case['observed']
                result = a.cache_operations(a.projected_caches({'atlas_beacon_graph': receipt}))['beacon']
                self.assertEqual(result['input_payload_bytes_hashed'], observed['input_hash_bytes'])
                self.assertEqual(result['graph_payload_files_written'], observed['graph_writes'])
                self.assertEqual(result['archive_decode_reported'], observed['archive_opens'] == 1)
                self.assertEqual(result['marker_write_source_implied'], observed['marker_writes'] == 1)
                self.assertTrue(observed['inventory_walks'] > 0)
                self.assertTrue(result['input_inventory_walk_reported'])

    def test_retained_graph_files_do_not_mean_archive_work_skipped(self):
        case = next(c for c in self.fixture['cases'] if c['case'] == 'existing_graph_missing_marker')
        result = a.cache_operations(a.projected_caches({'atlas_beacon_graph': case['receipt']}))['beacon']
        self.assertTrue(result['decoded_without_graph_payload_write'])
        self.assertGreater(case['observed']['archive_payload_read_bytes'], 0)
        self.assertEqual(case['observed']['marker_writes'], 1)

    def test_exact_source_shared_proof_refusal_reasons(self):
        by_case = {case['case']: case for case in self.fixture['cases']}
        expected = {'existing_graph_missing_marker': 'no_current_process_owned_atlas_proof',
                    'changed_generation': 'owned_source_generation_or_contract_changed',
                    'missing_generation': 'owned_source_generation_or_contract_missing',
                    'shared_proof': 'exact_full_byte_proved_owned_immutable_provider',
                    'changed_provider': 'exact_full_byte_proved_owned_immutable_provider'}
        for case, policy in expected.items():
            projection = a.projected_caches({'atlas_beacon_graph': by_case[case]['receipt']})
            self.assertEqual(projection['beacon']['shared_proof_policy'], policy)
        self.assertEqual(by_case['shared_proof']['observed']['input_hash_bytes'], 0)
        self.assertEqual(by_case['changed_provider']['observed']['input_hash_files'], 1)
        self.assertEqual(by_case['changed_provider']['receipt']['input_full_byte_proof_reused_files'], 1)

    def test_original_resource_producer_never_sums_reaped_children_with_self(self):
        fixture = oracle.original_resource_semantics()
        self.assertEqual(fixture['getrusage_sources'], ['self', 'children'])
        self.assertEqual(fixture['observed']['rss_kib'], 29)
        self.assertEqual(fixture['observed']['peak_rss_kib'], 41)
        self.assertEqual(fixture['observed']['children_peak_rss_kib'], 73)
        for key in ('cgroup_current_bytes', 'cgroup_max_bytes', 'cgroup_oom_kill_count'):
            self.assertIsNone(fixture['observed'][key])


if __name__ == '__main__': unittest.main()
