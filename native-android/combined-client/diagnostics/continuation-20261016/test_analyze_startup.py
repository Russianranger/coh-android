#!/usr/bin/env python3
"""Negative, provenance and privacy contracts for the offline analyzer."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile
from unittest import mock
import zlib

import analyze_startup as a

SID = 'a' * 32
OLD = 'b' * 32
SECRET = 'DO_NOT_EXPORT_PASSWORD_OR_PRIVATE_PATH'


def app(session=SID):
    return {'schema': 'coh-native-combined-app-v1', 'package': a.APP,
        'version_code': 7, 'message': SECRET, 'imports': SECRET,
        'server': {'session_id': session, 'phase': 'ready', 'ready': True,
            'owned_process_alive': True, 'elapsed_ms': 999999,
            'stage_elapsed_ms': 998899, 'stages': [
                {'stage': 'guest_starting', 'elapsed_ms': 0},
                {'stage': 'local_dbserver_startup', 'elapsed_ms': 100},
                {'stage': 'local_atlas_startup', 'elapsed_ms': 400},
                {'stage': 'server_running_manual_native_client', 'elapsed_ms': 1100}]},
        'server_memory': {'samples': 12, 'invalid_samples': 0,
            'pressure_samples': 0, 'admitted': True, 'stop_requested': False},
        'guest_resources': [{'rss_kib': 100, 'peak_rss_kib': 200,
            'children_peak_rss_kib': 300, 'cgroup_current_bytes': None}],
        'android_process_exits': [{'reason': 3, 'description': SECRET}]}


def guest(session=SID, warm=False):
    return {'format': 1, 'app_id': a.APP, 'session_id': session, 'account': SECRET,
        'server_preparation_phase_seconds': {
            'warm_schema_restore' if warm else 'cold_server_data_mirror': 12.5,
            SECRET: 100}, 'cleanup': {'owned_processes_reaped': True},
        'processes': [{'label': SECRET, 'output_bytes': 10}]}


class AnalysisTests(unittest.TestCase):
    def docs(self):
        return {'combined-report.json': app()}

    def test_current_ready_uses_boundary_not_age(self):
        d = a.analyze(self.docs())['current']
        self.assertEqual(d['ready_boundary_ms'], 1100)
        self.assertEqual([v['next_boundary_delta_ms'] for v in d['stages']], [100, 300, 700, None])

    def test_no_guest_means_cache_unknown(self):
        d = a.analyze(self.docs())['current']
        self.assertIsNone(d['guest_detail'])
        self.assertEqual(d['cache_classification'], 'unknown')

    def test_stale_guest_filename_cannot_bind_current(self):
        docs = self.docs()
        docs['combined-server-latest-report.json'] = guest(OLD)
        d = a.analyze(docs)
        self.assertEqual(d['current']['cache_classification'], 'unknown')
        self.assertEqual(d['standalone_historical_guest_count'], 1)

    def test_identity_not_filename_controls_binding(self):
        docs = self.docs()
        docs['previous-session-combined-server-latest-report.json'] = guest(SID, True)
        self.assertEqual(a.analyze(docs)['current']['cache_classification'], 'warm_schema_restore_observed')

    def test_historical_cold_receipt_stays_historical(self):
        docs = self.docs()
        docs['combined-server-previous-attempts.json'] = {'attempts': [
            {'session_id': OLD, 'app': app(OLD), 'guest': guest(OLD)}]}
        docs['previous-session-combined-server-latest-report.json'] = guest(OLD)
        d = a.analyze(docs)
        self.assertEqual(d['current']['cache_classification'], 'unknown')
        self.assertEqual(d['historical_attempts'][0]['guest_detail']['cache_classification'], 'cold_mirror_observed')
        self.assertEqual(d['standalone_historical_guest_matches_attempt'], [True])

    def test_mismatched_historical_guest_not_summarized(self):
        docs = self.docs()
        docs['combined-server-previous-attempts.json'] = {'attempts': [
            {'session_id': OLD, 'app': app(OLD), 'guest': guest()}]}
        self.assertIsNone(a.analyze(docs)['historical_attempts'][0]['guest_detail'])

    def test_current_in_history_rejected(self):
        docs = self.docs()
        docs['combined-server-previous-attempts.json'] = {'attempts': [
            {'session_id': SID, 'app': app()}]}
        with self.assertRaisesRegex(a.Rejected, 'CURRENT_IN_HISTORY'):
            a.analyze(docs)

    def test_duplicate_current_guests_rejected(self):
        docs = self.docs()
        for name in ('combined-server-latest-report.json', 'previous-session-combined-server-latest-report.json'):
            docs[name] = guest()
        with self.assertRaisesRegex(a.Rejected, 'MULTIPLE_CURRENT_GUESTS'):
            a.analyze(docs)

    def test_invalid_guest_format_does_not_bind(self):
        docs = self.docs(); docs['combined-server-latest-report.json'] = guest()
        docs['combined-server-latest-report.json']['format'] = True
        with self.assertRaisesRegex(a.Rejected, 'GUEST_SCHEMA'):
            a.analyze(docs)

    def test_conflicting_cache_evidence_is_unknown(self):
        g = guest(); g['server_preparation_phase_seconds']['warm_schema_restore'] = 1
        self.assertEqual(a.guest_summary(g)['cache_classification'], 'unknown')

    def test_redaction_is_allowlist_not_blacklist(self):
        docs = self.docs(); docs['combined-server-latest-report.json'] = guest()
        docs['combined-report.json']['server']['stages'][1]['stage'] = SECRET
        out = json.dumps(a.analyze(docs))
        for secret in (SID, OLD, SECRET):
            self.assertNotIn(secret, out)
        self.assertIn('unknown_stage', out)

    def test_typed_stage_values_redacted_without_exception(self):
        for value in ([SECRET], {SECRET: SECRET}, None, 42, True):
            docs = self.docs()
            docs['combined-report.json']['server']['stages'][1]['stage'] = value
            out = a.analyze(docs)
            self.assertEqual(out['current']['stages'][1]['stage'], 'unknown_stage')
            self.assertNotIn(SECRET, json.dumps(out))

    def test_foreign_standalone_guest_schema_rejected(self):
        docs = self.docs()
        docs['previous-session-combined-server-latest-report.json'] = guest(OLD)
        docs['previous-session-combined-server-latest-report.json']['app_id'] = 'different.application'
        with self.assertRaisesRegex(a.Rejected, 'GUEST_SCHEMA'):
            a.analyze(docs)
        with self.assertRaisesRegex(a.Rejected, 'GUEST_SCHEMA'):
            a.guest_summary(docs['previous-session-combined-server-latest-report.json'])

    def test_memory_peaks_not_added(self):
        d = a.analyze(self.docs())['current']['guest_resources']
        self.assertEqual(d['peak_rss_kib_sample_max'], 200)
        self.assertEqual(d['children_peak_rss_kib_sample_max'], 300)
        self.assertIsNone(d['cgroup_current_bytes_sample_max'])
        self.assertNotIn('total_peak', d)

    def test_exit_history_does_not_become_current_kill(self):
        d = a.analyze(self.docs())['current']['android_exit_history']
        self.assertEqual(d['reason_3_records'], 1)
        self.assertFalse(d['allocation_cause_established'])
        self.assertEqual(d['temporal_attribution'], 'unknown_without_bound_wall_clock_origin')

    def test_invalid_numbers_not_coerced(self):
        for value in (True, -1, 1.5, '42', 1 << 60):
            self.assertIsNone(a.number(value))
        for value in (True, -1, float('nan'), float('inf')):
            self.assertIsNone(a.seconds(value))

    def test_backwards_boolean_and_duplicate_ready_clock_rejected(self):
        for value in (-1, True):
            d = self.docs(); d['combined-report.json']['server']['stages'][2]['elapsed_ms'] = value
            with self.assertRaisesRegex(a.Rejected, 'STAGE_CLOCK'):
                a.analyze(d)
        d = self.docs(); d['combined-report.json']['server']['stages'][2]['stage'] = 'server_running_manual_native_client'
        with self.assertRaisesRegex(a.Rejected, 'MULTIPLE_READY'):
            a.analyze(d)

    def test_array_bounds(self):
        for field, count in (('guest_resources', 33), ('android_process_exits', 9)):
            d = self.docs(); d['combined-report.json'][field] = [{}] * count
            with self.assertRaisesRegex(a.Rejected, 'ARRAY_BOUND'):
                a.analyze(d)

    def test_json_duplicates_nonfinite_depth_and_root(self):
        for raw in (b'{"x":0,"x":1}', b'{"x":NaN}', b'{"x":Infinity}', b'[]',
                    ('{"x":' + '[' * 40 + '0' + ']' * 40 + '}').encode()):
            with self.assertRaises(a.Rejected):
                a.parse(raw)

    def test_invalid_current_identity_and_schema(self):
        for key, value in (('session_id', SECRET), ('session_id', ''), ('session_id', None)):
            d = self.docs(); d['combined-report.json']['server'][key] = value
            with self.assertRaises(a.Rejected): a.analyze(d)
        d = self.docs(); d['combined-report.json']['package'] = SECRET
        with self.assertRaises(a.Rejected): a.analyze(d)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.zip'

    def write(self, entries):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for name, body in entries: z.writestr(name, body)

    def test_reads_crc_and_bound_provenance(self):
        self.write([('combined-report.json', json.dumps(app())), ('native-client-report.json', SECRET),
                     ('previous-app-native-client-report.json', SECRET)])
        docs, proof = a.read_archive(self.path)
        self.assertNotIn('native-client-report.json', docs)
        self.assertEqual(len(proof['members']), 3)
        self.assertEqual(len(proof['archive_sha256']), 64)
        self.assertEqual(a.analyze(docs)['current']['ready_boundary_ms'], 1100)

    def test_unknown_traversal_absolute_backslash_and_duplicate_members(self):
        for name in ('../combined-report.json', '/combined-report.json', 'secret.json', 'x\\combined-report.json'):
            self.write([(name, '{}')])
            with self.assertRaisesRegex(a.Rejected, 'MEMBER_NAME'): a.read_archive(self.path)
        self.write([('combined-report.json', '{}')] * 2)
        with self.assertRaisesRegex(a.Rejected, 'DUPLICATE_MEMBER'): a.read_archive(self.path)

    def test_symlink_and_oversized_members(self):
        info = zipfile.ZipInfo('combined-report.json'); info.create_system = 3
        info.external_attr = (0o120777 << 16)
        self.write([(info, '{}')])
        with self.assertRaisesRegex(a.Rejected, 'MEMBER_TYPE'): a.read_archive(self.path)
        self.write([('combined-report.json', 'x' * (a.LIMIT + 1))])
        with self.assertRaisesRegex(a.Rejected, 'MEMBER_SIZE_BOUND'): a.read_archive(self.path)

    def test_crc_failure_and_invalid_archive(self):
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_STORED) as z:
            z.writestr('combined-report.json', json.dumps(app()))
        raw = self.path.read_bytes(); self.path.write_bytes(raw.replace(b'999999', b'999998'))
        with self.assertRaisesRegex(a.Rejected, 'INVALID_ARCHIVE'): a.read_archive(self.path)
        self.path.write_bytes(b'not zip')
        with self.assertRaisesRegex(a.Rejected, 'INVALID_ARCHIVE'): a.read_archive(self.path)

    def test_deflate_failure_is_bounded_error(self):
        self.write([('combined-report.json', json.dumps(app()))])
        with mock.patch.object(zipfile.ZipExtFile, 'read', side_effect=zlib.error(SECRET)):
            with self.assertRaisesRegex(a.Rejected, '^INVALID_ARCHIVE$'):
                a.read_archive(self.path)

    def test_cli_error_never_exports_input_path_or_json(self):
        self.write([('combined-report.json', SECRET)])
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(a.main([str(self.path)]), 2)
        self.assertNotIn(SECRET, stream.getvalue())
        self.assertNotIn(self.temp.name, stream.getvalue())


if __name__ == '__main__':
    unittest.main()
