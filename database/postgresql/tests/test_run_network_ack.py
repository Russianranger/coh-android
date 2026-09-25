"""Fail-closed ACK acceptance, preflight and real subprocess lifecycle checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_network_ack as driver


def marker(identifier=42, *, count=1, list_id=23, callback=0):
    return f'COH_DBQUERY_CONTAINER_ACK list={list_id} callback={callback} count={count} id={identifier}\n'


class NetworkAckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_exit_zero_without_received_ack_is_not_success(self):
        for text in ('', 'connected\n', 'File not found.', 'timeout', 'Detected dbserver shut down, shutting down.'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.require_ack(text, 0)

    def test_received_ack_requires_matching_packet_fields_and_clean_exit(self):
        self.assertEqual(driver.require_ack('startup\n' + marker() + 'done\n', 0, 42)['id'], 42)
        for text, exit_code in ((marker(43), 0), (marker(list_id=8), 0), (marker(callback=1), 0),
                                (marker(count=2), 0), (marker(0), 0), (marker(), 3),
                                (marker() * 2, 0), (marker() + 'SQLSTATE=42501\n', 0)):
            with self.subTest(text=text, exit_code=exit_code), self.assertRaises(ValueError):
                driver.require_ack(text, exit_code, 42)

    def test_batch_requires_one_two_id_packet_not_partial_garbage_or_duplicates(self):
        correct = marker(42, count=2) + marker(43, count=2)
        self.assertEqual(len(driver.require_batch_ack(correct, 0, (42, 43))), 2)
        for text in (marker(42, count=2), marker(42, count=2) + marker(0, count=2),
                     marker(42, count=2) * 2, correct * 2, marker(42) + marker(43),
                     correct + 'ERROR: bad protocol\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.require_batch_ack(text, 0, (42, 43))

    def test_actual_odbc_error_prefix_rejects_otherwise_valid_ack(self):
        diagnostic = 'SQLERROR: 0 42501 permission denied\n'
        self.assertTrue(driver.is_failure_line(diagnostic))
        with self.assertRaisesRegex(ValueError, 'failure diagnostics'):
            driver.require_ack(marker() + diagnostic, 0, 42)
        with self.assertRaisesRegex(ValueError, 'failure diagnostics'):
            driver.require_batch_ack(marker(42, count=2) + marker(43, count=2) + diagnostic, 0, (42, 43))

    def test_received_ack_allows_only_reviewed_catalog_notices(self):
        notice = 'SQLERROR: -1 00000 NOTICE: relation "ents2" does not exist, skipping\n'
        self.assertEqual(driver.require_ack(marker() + notice, 0, 42)['id'], 42)
        self.assertEqual(len(driver.require_batch_ack(marker(42, count=2) + marker(43, count=2) + notice, 0, (42, 43))), 2)
        for diagnostic in (notice.replace('NOTICE:', 'ERROR:'), notice + 'SQLERROR: 0 42501 permission denied\n'):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(ValueError, 'failure diagnostics'):
                driver.require_ack(marker() + diagnostic, 0, 42)

    def test_premature_or_failed_write_rejects_even_malformed_ack_marker(self):
        driver.require_no_ack('SQLSTATE=42501; save not acknowledged')
        for value in (marker(), 'COH_DBQUERY_CONTAINER_ACK truncated'):
            with self.assertRaises(ValueError):
                driver.require_no_ack(value)

    def test_fixture_contract_matches_actual_source_enumeration_and_sql_registration(self):
        actual = driver.fixture_source_contract()
        self.assertEqual(actual['list_id'], 23)
        self.assertEqual(actual['table'], 'miningaccumulator')
        self.assertEqual(actual['containers_per_batch_request'], 2)

    def test_fixture_rejects_quotes_newlines_and_sql_text(self):
        self.assertEqual(driver.fixture_text('network_initial'), 'Name "network_initial"\n')
        for value in ('bad"\nName x', 'a\nb', "');DROP", '', 'a' * 49):
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.fixture_text(value)

    def test_private_service_configuration_retains_required_fakeauth_and_disables_dumps(self):
        config = 'UseFakeAuth 1\nUseQueueServer 0\nSqlAllowDDL 1\nAssertMode Fulldump\nSqlLogin "Password=old"\nNoStats 0\n'
        value = driver.service_config(config, 'SqlLogin "Password=new"\n')
        self.assertIn('AssertMode Exit\n', value)
        self.assertNotIn('Fulldump', value)
        self.assertNotIn('Password=old', value)
        self.assertEqual(value.count('SqlLogin '), 1)
        self.assertIn('UseFakeAuth 1', value)
        with self.assertRaises(ValueError):
            driver.service_config(config.replace('UseFakeAuth 1', 'UseFakeAuth 0'), '')

    def test_work_and_publishable_evidence_are_separate(self):
        for work, output in ((self.root / 'same', self.root / 'same'),
                             (self.root / 'work', self.root / 'work/public'),
                             (self.root / 'output/private', self.root / 'output')):
            with self.subTest(work=work, output=output), self.assertRaisesRegex(ValueError, 'separate'):
                driver.new_paths(self.root / 'runtime', self.root / 'reference', work, output, self.root)

    def test_rejected_schema_cannot_create_cluster_credentials_or_work(self):
        runtime = self.root / 'runtime'
        runtime.mkdir()
        (runtime / 'runtime-inputs.json').write_text(json.dumps({
            'source_commit': driver.schema.generation.SOURCE_COMMIT,
            'data_commit': driver.schema.generation.DATA_COMMIT, 'binary_assets_supplied': False}))
        report = self.root / 'schema.json'
        report.write_text(json.dumps({'status': 'schema_data_only_generation_failed'}))
        work, output = self.root / 'work', self.root / 'output'
        with patch.object(driver, 'initialize') as initialize:
            with self.assertRaisesRegex(ValueError, 'has not passed acceptance'):
                driver.run(runtime, report, self.root / 'reference', work, output, 'unused', 'unused')
            initialize.assert_not_called()
        self.assertFalse(work.exists())
        self.assertFalse(output.exists())

    def test_independent_sql_postcondition_not_inferred_from_ack(self):
        class Cluster:
            meta = {'database': 'coh_network_ack'}
            def sql(self, sql, **kwargs):
                return '[{"containerid":42,"name":"old"}]'
        with self.assertRaisesRegex(ValueError, 'Independent SQL row differs'):
            driver.require_row(Cluster(), 42, 'network_modified')
        self.assertEqual(driver.require_row(Cluster(), 42, 'old')[0]['name'], 'old')
        with self.assertRaises(ValueError):
            driver.read_row(Cluster(), '42;DROP')

    def test_process_capture_and_exit_are_real(self):
        process = driver.Process([sys.executable, '-c', 'print("captured")'], self.root, self.root, 'capture')
        self.addCleanup(process.stop)
        self.assertEqual(process.wait(10), 0)
        self.assertIn('captured', process.text())
        self.assertFalse(process.record()['forced_stop'])

    def test_ack_is_observed_before_client_disconnect_finishes(self):
        code = 'import time;print(' + repr(marker().strip()) + ',flush=True);time.sleep(60)'
        process = driver.Process([sys.executable, '-u', '-c', code], self.root, self.root, 'ack-before-exit')
        self.addCleanup(process.stop)
        ack, observed = driver.observe_ack(process, 10, 42)
        self.assertEqual(ack['id'], 42)
        self.assertIsNone(process.child.poll())

    def test_timed_out_process_can_be_stopped_and_reaped(self):
        process = driver.Process([sys.executable, '-c', 'import time;time.sleep(60)'], self.root, self.root, 'sleep')
        self.addCleanup(process.stop)
        with self.assertRaisesRegex(ValueError, 'timed out'):
            process.wait(0.1)
        process.stop()
        self.assertIsNotNone(process.child.poll())
        self.assertTrue(process.record()['forced_stop'])

    def test_process_output_bound_is_enforced(self):
        process = driver.Process([sys.executable, '-c', 'print("x"*2048)'], self.root, self.root, 'large')
        self.addCleanup(process.stop)
        process.child.wait(timeout=10)
        with patch.object(driver, 'LOG_LIMIT', 64), self.assertRaisesRegex(ValueError, 'capture bound'):
            process.text()

    def test_interactive_process_uses_file_capture_and_exits(self):
        process = driver.Process([sys.executable, '-u', '-c', 'import sys;print(sys.stdin.readline().strip())'],
                                 self.root, self.root, 'interactive', interactive=True)
        self.addCleanup(process.stop)
        process.send('private handshake\n')
        self.assertEqual(process.wait(10), 0)
        self.assertIn('private handshake', process.text())


if __name__ == '__main__':
    unittest.main()
