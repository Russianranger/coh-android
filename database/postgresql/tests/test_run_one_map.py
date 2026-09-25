"""Acceptance tests for stock map status and exact comparison provenance."""
import copy
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import run_one_map as driver

READY = ' 1 City_01_01.txt          S: 2/3  Ip:127.0.0.1:7001 Mem: 400M Cpu:0:03.00 = 1.00 1.00 Up: 0:01 Info \n'
NOT_STARTED = '1 maps/City_Zones/City_01_01/City_01_01.txt NotReady 1 (Not started) Info \n'


class OneMapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = {'status': 'staged_not_gameplay_validated',
            'source_commit': driver.generation.SOURCE_COMMIT, 'data_commit': driver.generation.DATA_COMMIT,
            'binary_assets_supplied': True, 'executables_supplied': True,
            'binary_asset_files': {'player_library/test.anim': 'a' * 64},
            'build_file_sha256': {'MapServer.exe': 'b' * 64},
            'reference_repository_commit': 'c' * 40, 'postgresql_build_input': {'patch_sha256': 'd' * 64}}
        self.package = {'repository_commit': 'c' * 40, 'postgresql_build_input': self.inputs['postgresql_build_input']}
        self.hashes = {'MapServer.exe': 'b' * 64}
        self.report = {'status': driver.comparison.SUCCESS, 'exit_code': 0, 'failures': [],
            'output_differences': [], 'identical_fresh_output_count': 56, 'expected_output_count': 56,
            'serializer_equivalence': '56_generated_files_byte_equal_for_checked_inputs',
            'runtime_inputs_sha256': 'e' * 64, 'schema_report_sha256': 'f' * 64,
            'source_commit': driver.generation.SOURCE_COMMIT, 'data_commit': driver.generation.DATA_COMMIT,
            'reference_repository_commit': 'c' * 40, 'postgresql_build_input': self.inputs['postgresql_build_input'],
            'mapserver_sha256': 'b' * 64, 'verified_asset_files': 1}

    def accept(self, *, report=None, original=None, fresh=None, original_sha=None):
        return driver.accept_comparison(report or self.report, original or self.inputs,
            original_sha or 'e' * 64, fresh or self.inputs, self.package, self.hashes, 'f' * 64)

    def test_source_contract_uses_atlas_park_not_outbreak_or_legacy_launcher_map(self):
        contract = driver.source_map_contract()
        self.assertEqual(contract['map_id'], 1)
        self.assertEqual(contract['map_key'], 'atlaspark')
        self.assertEqual(contract['map_path'], 'maps/City_Zones/City_01_01/City_01_01.txt')
        args = driver.map_command(self.root)
        self.assertEqual(args[args.index('-map_id') + 1], '1')
        self.assertEqual(args[args.index('-udp') + 1], '7001')
        self.assertEqual(args[args.index('-tcp') + 1], '0')
        self.assertNotIn('-templates', args)
        self.assertNotIn('-dbquery', args)

    def test_baseline_and_connected_but_starting_are_not_ready(self):
        baseline = driver.parse_status(NOT_STARTED)
        self.assertFalse(baseline['ready'])
        self.assertTrue(baseline['not_started'])
        starting = driver.parse_status(READY.rstrip() + ' NotReady 1\n')
        self.assertFalse(starting['ready'])
        self.assertFalse(starting['not_started'])

    def test_protocol_status_retains_map_endpoint_and_both_heartbeat_ages(self):
        parsed = driver.parse_status(READY)
        self.assertTrue(parsed['ready'])
        self.assertEqual(parsed['network_age_seconds'], 2)
        self.assertEqual(parsed['stats_age_seconds'], 3)
        self.assertEqual(parsed['port'], 7001)
        self.assertEqual(parsed['address'], '127.0.0.1')

    def test_missing_map_is_only_transient_before_launch(self):
        text = 'invalid container request\n'
        with self.assertRaisesRegex(ValueError, 'container is missing'):
            driver.parse_status(text)
        parsed = driver.parse_status(text, allow_missing=True)
        self.assertTrue(parsed['missing'])
        self.assertFalse(parsed['ready'])
        for malformed in (text + READY, text * 2, text + 'ERROR: broken\n'):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                driver.parse_status(malformed, allow_missing=True)

    def test_console_ready_exit_zero_wrong_map_and_ambiguous_replies_cannot_pass(self):
        for text in ('Server ready.\n', '', 'connected\n', READY.replace('City_01_01', 'City_00_01'),
                     READY.replace(' 1 ', ' 29 ', 1), READY * 2, '1 City_01_01.txt nonsense\n',
                     READY + 'SQLERROR: database broken\n', READY.replace('127.0.0.1', '999.0.0.1')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.parse_status(text)

    def test_successful_comparison_still_requires_exact_original_manifest_hash(self):
        self.accept()
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.accept(original_sha='0' * 64)

    def test_failed_partial_or_timed_out_comparison_cannot_launch_game(self):
        mutations = [{'status': 'reference_template_comparison_failed'}, {'failures': ['missing map']},
            {'exit_code': 3}, {'identical_fresh_output_count': 55}, {'output_differences': ['wrong']},
            {'timed_out': True}, {'capture_error': 'lost'}, {'serializer_equivalence': 'unverified'}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.accept(report=dict(self.report, **mutation))

    def test_new_assets_or_changed_build_not_covered_by_earlier_comparison(self):
        fresh = copy.deepcopy(self.inputs)
        fresh['binary_asset_files']['player_library/test.anim'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'binary_asset_files'):
            self.accept(fresh=fresh)
        for mutation in ({'mapserver_sha256': '0' * 64}, {'reference_repository_commit': '0' * 40},
                         {'postgresql_build_input': {}}, {'data_commit': '0' * 40}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.accept(report=dict(self.report, **mutation))

    def test_preflight_rejection_occurs_before_credentials_output_or_services(self):
        work, output = self.root / 'work', self.root / 'evidence'
        with patch.object(driver, 'preflight', side_effect=ValueError('Comparison rejected')), \
             patch.object(driver, 'initialize') as cluster, patch.object(driver.network, 'Process') as process:
            with self.assertRaisesRegex(ValueError, 'Comparison rejected'):
                driver.run(self.root / 'runtime', self.root / 'reference', self.root / 'schema.json',
                           self.root / 'comparison.json', self.root / 'comparison-inputs.json',
                           work, output, 'unused', 'unused')
            cluster.assert_not_called()
            process.assert_not_called()
        self.assertFalse(work.exists())
        self.assertFalse(output.exists())

    def test_observed_fatal_and_critical_asset_failures_remain_failures(self):
        for message in ('SQLERROR: unexpected relation', 'PG_FIFO_FAILED command=1', 'assertion failed',
                        'Unable to load missing.geo', 'Cannot find maps/City_01_01.txt', 'Missing animation foo'):
            with self.subTest(message=message):
                self.assertEqual(driver.diagnostic_failures(message), [message])
        self.assertEqual(driver.diagnostic_failures('No zone launchers connected.'), [])

    def test_occupied_map_udp_port_rejected(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied, \
             socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unused:
            occupied.bind(('127.0.0.1', 0))
            unused.bind(('127.0.0.1', 0))
            pg_port = unused.getsockname()[1]
            unused.close()
            with patch.object(driver, 'MAP_UDP_PORT', occupied.getsockname()[1]), \
                 self.assertRaisesRegex(ValueError, 'map_client port'):
                driver.preflight_ports(pg_port)

    def test_catalog_alone_cannot_permit_first_protocol_query(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            listener.listen(4)
            with patch.object(driver.network, 'DB_PORT', port), \
                 patch.object(driver, 'catalog_snapshot', return_value={'columns': [
                     {'table_name': 'example', 'column_name': 'containerid'}]}) as catalog:
                self.assertTrue(driver.database_query_possible(None, {'example': ['containerid']}))
                self.assertFalse(driver.database_query_possible(None, {'example': ['wrong']}))
                listener.close()
                catalog.reset_mock()
                self.assertFalse(driver.database_query_possible(None, {'example': ['containerid']}))
                catalog.assert_not_called()


if __name__ == '__main__':
    unittest.main()
