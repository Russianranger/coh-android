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


if __name__ == '__main__': unittest.main()
