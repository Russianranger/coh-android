"""Reject malformed candidate receipts/rows; synthetic inputs are not native proof."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import package_native_map_prefetch as package
import qualify_native_startup_profile as qualification
import test_native_map_metadata_prefetch as fixture
from test_package_reference_runtime import pe_file


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checks_fixture():
    """Model the receipt schema for validation tests, without executing Windows."""
    code = fixture.harness().encode()
    binary = b'synthetic fixture bytes, never an executed Windows binary'
    stdout = (fixture.PASS+' scenarios=16 flags=8 cases=128 tuple_cases=252 pointer_bits=32\n').encode()
    artifacts = {
        'checks.fixture.c': code,
        'checks.fixture.exe': binary,
        'checks.build.log': b'synthetic compiler log\n',
        'checks.stdout.txt': stdout,
        'checks.stderr.txt': b'',
    }
    return {
        'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler': 'cl.exe',
        'compiler_options': fixture.COMPILER_OPTIONS.copy(),
        'build_input': package.source.expected_receipt(), 'harness_sha256': digest(code),
        'fixture_binary_sha256': digest(binary),
        'scope': 'extracted_actual_freshness_and_prefetch_with_external_IO_test_doubles',
        'scenario_count': fixture.SCENARIO_COUNT, 'flag_count': fixture.FLAG_COUNT,
        'cases': fixture.SCENARIO_COUNT*fixture.FLAG_COUNT,
        'equivalence_cases': fixture.SCENARIO_COUNT*fixture.FLAG_COUNT,
        'exact_tuple_cases': fixture.TUPLE_COUNT,
        'equivalence_verified': True, 'operation_order_and_counts_verified': True,
        'after_header_before_checks_verified': True, 'opt_in_and_fallback_verified': True,
        'exact_scope_verified': True, 'freshness_failure_branches_verified': True,
        'ordinary_source_mutation_detection_verified': True,
        'existing_production_behavior_preserved': True, 'observer_macros_are_noops': True,
        'metadata_lookup_model_only': True, 'animation_payload_reads_exercised': False,
        'native_windows_executed': True, 'native_wine_executed': False,
        'world_startup_executed': False, 'physical_device_executed': False,
        'physical_startup_savings_validated': False, 'publication_allowed': False,
        'evidence': {name: {'sha256': digest(data), 'bytes': len(data)} for name, data in artifacts.items()},
    }


def observation(milliseconds='1.234'):
    return ('COH_MAP_ANIMATION_METADATA_PREFETCH_V1 tree=player_library/animations '
            'cache=bin/sequencers.bin milliseconds='+milliseconds+
            ' source_freshness_preserved=1 crc_validation_preserved=1\n').encode()


class NativeMapPrefetchChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = checks_fixture()

    def reject(self, update):
        value = copy.deepcopy(self.valid)
        update(value)
        with self.assertRaises(ValueError):
            package.validate_checks(value)

    def test_complete_synthetic_receipt_schema_is_admitted_without_mutation(self):
        # This exercises receipt admission only. Actual executable/PE validation
        # is a separate packaging gate; these dictionary bytes prove no execution.
        value = copy.deepcopy(self.valid)
        self.assertEqual(package.validate_checks(value), self.valid)
        self.assertEqual(value, self.valid)

    def test_missing_unknown_and_wrong_version_fields_are_rejected(self):
        for key in self.valid:
            with self.subTest(missing=key):
                self.reject(lambda value, key=key: value.pop(key))
        for key, value in [('unverified_claim', True), ('format', 2), ('format', True),
                           ('status', 'skipped')]:
            with self.subTest(key=key, value=value):
                self.reject(lambda receipt, key=key, value=value: receipt.update({key: value}))

    def test_nonmapping_receipts_are_rejected_cleanly(self):
        for value in (None, [], '', 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                package.validate_checks(value)

    def test_host_x64_and_wrong_compiler_receipts_are_rejected(self):
        for key, value in [('platform', 'linux'), ('architecture', 'x64'),
                           ('configuration', 'Debug'), ('compiler', 'cc'),
                           ('compiler_options', ['/O2', '/MT', '/TC']),
                           ('native_windows_executed', False), ('native_windows_executed', 1)]:
            with self.subTest(key=key, value=value):
                self.reject(lambda receipt, key=key, value=value: receipt.update({key: value}))

    def test_every_required_control_flow_guarantee_is_strictly_true(self):
        keys = ('equivalence_verified', 'operation_order_and_counts_verified',
                'after_header_before_checks_verified', 'opt_in_and_fallback_verified',
                'exact_scope_verified', 'freshness_failure_branches_verified',
                'ordinary_source_mutation_detection_verified', 'existing_production_behavior_preserved',
                'observer_macros_are_noops', 'metadata_lookup_model_only')
        for key in keys:
            for value in (False, 1, 'true'):
                with self.subTest(key=key, value=value):
                    self.reject(lambda receipt, key=key, value=value: receipt.update({key: value}))

    def test_world_device_and_savings_claims_cannot_be_added_to_fixture_evidence(self):
        keys = ('animation_payload_reads_exercised', 'native_wine_executed',
                'world_startup_executed', 'physical_device_executed',
                'physical_startup_savings_validated', 'publication_allowed')
        for key in keys:
            for value in (True, 0, 'false'):
                with self.subTest(key=key, value=value):
                    self.reject(lambda receipt, key=key, value=value: receipt.update({key: value}))
        self.reject(lambda value: value.update(scope='actual_world_and_physical_startup_benchmark'))

    def test_partial_extra_and_boolean_case_counts_are_rejected(self):
        for key in ('scenario_count', 'flag_count', 'cases', 'equivalence_cases', 'exact_tuple_cases'):
            for value in (0, self.valid[key]-1, self.valid[key]+1, True, float(self.valid[key])):
                with self.subTest(key=key, value=value):
                    self.reject(lambda receipt, key=key, value=value: receipt.update({key: value}))

    def test_source_recipe_and_exact_harness_identity_are_required(self):
        self.reject(lambda value: value['build_input']['patched_sha256'].update({package.source.SOURCE: '0'*64}))
        self.reject(lambda value: value['build_input']['source_sha256'].update({package.source.SOURCE: '0'*64}))
        self.reject(lambda value: value['build_input']['environment'].update(enabled_value='01'))
        self.reject(lambda value: value.update(harness_sha256='0'*64))
        self.reject(lambda value: value.update(harness_sha256='A'*64))
        self.reject(lambda value: value.update(fixture_binary_sha256='bad'))
        self.reject(lambda value: value.update(fixture_binary_sha256=None))

    def test_staged_sequencer_pin_matches_profiled_source_not_upstream_source(self):
        recipe = package.source.expected_receipt()
        sequencer = package.source.profile.SEQUENCER
        self.assertEqual(recipe['staged_callsites_sha256'][sequencer],
                         package.source.profile.expected_receipt()['patched_sha256'][sequencer])
        self.assertNotEqual(recipe['staged_callsites_sha256'][sequencer],
                            recipe['retained_callsites_sha256'][sequencer])
        self.assertEqual(set(recipe['staged_callsites_sha256']), set(recipe['retained_callsites_sha256']))
        for name in recipe['staged_callsites_sha256']:
            if name != sequencer:
                self.assertEqual(recipe['staged_callsites_sha256'][name],
                                 recipe['retained_callsites_sha256'][name])

    def test_retained_fixture_source_and_binary_pins_match_top_level_identity(self):
        self.reject(lambda value: value['evidence']['checks.fixture.c'].update(sha256='0'*64))
        self.reject(lambda value: value['evidence']['checks.fixture.c'].update(bytes=1))
        self.reject(lambda value: value['evidence']['checks.fixture.exe'].update(sha256='0'*64))
        self.reject(lambda value: value['evidence']['checks.fixture.exe'].update(bytes=0))
        self.reject(lambda value: value['evidence'].pop('checks.fixture.c'))
        self.reject(lambda value: value['evidence'].pop('checks.fixture.exe'))
        self.reject(lambda value: value['evidence'].update({'duplicate.fixture.c': value['evidence']['checks.fixture.c']}))
        self.reject(lambda value: value['evidence'].update({'../escape.fixture.exe': value['evidence'].pop('checks.fixture.exe')}))


class NativeMapPrefetchObservationTests(unittest.TestCase):
    def test_exact_bounded_row_surrounded_by_unrelated_console_is_admitted(self):
        for milliseconds in ('0.000', '1.234', '3600000.000'):
            with self.subTest(milliseconds=milliseconds):
                raw = b'initializing ordinary server\r\n'+observation(milliseconds).replace(b'\n', b'\r\n')+b'preload complete\n'
                result = qualification.prefetch_observation(raw)
                self.assertEqual(result, {'request_count': 1, 'tree': 'player_library/animations',
                                         'cache': 'bin/sequencers.bin', 'milliseconds': float(milliseconds),
                                         'provider_authority_created': False})

    def test_missing_and_duplicate_requests_are_rejected(self):
        for raw in (b'', b'unrelated console\n', observation()+observation()):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                qualification.prefetch_observation(raw)

    def test_wrong_scope_case_or_preservation_claim_is_rejected(self):
        changes = [(b'player_library/animations', b'Menu'),
                   (b'player_library/animations', b'player_library/animations/'),
                   (b'player_library/animations', b'Player_library/animations'),
                   (b'bin/sequencers.bin', b'bin/powers.bin'),
                   (b'bin/sequencers.bin', b'server/bin/sequencers.bin'),
                   (b'bin/sequencers.bin', b'bin/Sequencers.bin'),
                   (b'source_freshness_preserved=1', b'source_freshness_preserved=0'),
                   (b'crc_validation_preserved=1', b'crc_validation_preserved=0')]
        for old, new in changes:
            with self.subTest(new=new), self.assertRaises(ValueError):
                qualification.prefetch_observation(observation().replace(old, new))

    def test_malformed_missing_extra_or_duplicate_fields_are_rejected(self):
        rows = [observation().replace(b' cache=', b'cache='),
                observation().replace(b' milliseconds=1.234', b''),
                observation().replace(b' tree=', b' ignored=1 tree='),
                observation().replace(b' milliseconds=1.234', b' milliseconds=1.234 milliseconds=1.234'),
                observation().replace(b' source_freshness_preserved=1 crc_validation_preserved=1',
                                      b' crc_validation_preserved=1 source_freshness_preserved=1'),
                observation().replace(b'\n', b' trailing=1\n')]
        for raw in rows:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                qualification.prefetch_observation(raw)

    def test_nonfinite_negative_inexact_or_unbounded_times_are_rejected(self):
        for milliseconds in ('nan', 'NaN', 'inf', '-inf', '1e3', '-0.001', '1', '1.2', '1.2345',
                             '3600000.001', '9'*400+'.000'):
            with self.subTest(milliseconds=milliseconds), self.assertRaises(ValueError):
                qualification.prefetch_observation(observation(milliseconds))

    def test_malformed_reserved_marker_cannot_hide_alongside_valid_request(self):
        marker = b'COH_MAP_ANIMATION_METADATA_PREFETCH_V1'
        for malformed in (marker, marker+b'\ttree=player_library/animations', marker+b'_forged=1'):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                qualification.prefetch_observation(observation()+malformed+b'\n')

    def test_console_input_must_be_bounded_bytes(self):
        for raw in (None, observation().decode(), bytearray(observation())):
            with self.subTest(type=type(raw).__name__), self.assertRaises(ValueError):
                qualification.prefetch_observation(raw)
        with self.assertRaises(ValueError):
            qualification.prefetch_observation(b'x'*(64*1024**2+1))


class NativeMapPrefetchPackageFixtureTests(unittest.TestCase):
    """Use synthetic PE headers to exercise packaging gates, never execution."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.output, self.baseline = root/'candidate', root/'retained'
        self.output.mkdir()
        self.baseline.mkdir()
        (self.baseline/package.base.MANIFEST).write_bytes(b'synthetic retained manifest\n')
        (self.output/package.BINARY).write_bytes(pe_file(('KERNEL32.dll',)))
        record = package.base.file_record(self.output/package.BINARY)
        old = {'native_control': {'binary': copy.deepcopy(record)},
               'files': {'MapServer-profile.exe': copy.deepcopy(record)}}
        retained = mock.patch.object(package.retained, 'validate_package', return_value=old)
        retained.start()
        self.addCleanup(retained.stop)
        self.checks = checks_fixture()
        self.commit = '2'*40
        self.manifest = {
            'format': 1, 'role': 'nonshipping_map_metadata_prefetch',
            'repository_commit': self.commit, 'build_targets': ['MapServer'],
            'publication_allowed': False, 'native_world_executed': False,
            'native_preload_executed': False, 'native_game_changed': False,
            'physical_device_executed': False, 'build_input': package.source.expected_receipt(),
            'retained_build': package.retained.provenance(),
            'retained_package': package.base.pin(self.baseline/package.base.MANIFEST),
            'retained_control_binary': old['native_control']['binary'],
            'retained_observed_binary': old['files']['MapServer-profile.exe'],
            'binary': record,
        }
        self.install_fixture(pe_file(('KERNEL32.dll',)))

    def install_fixture(self, data):
        (self.output/package.FIXTURE).write_bytes(data)
        self.checks['fixture_binary_sha256'] = digest(data)
        self.checks['evidence']['checks.fixture.exe'] = {'sha256': digest(data), 'bytes': len(data)}
        self.manifest['native_checks'] = copy.deepcopy(self.checks)
        package.base.write(self.output/package.CHECKS, self.checks)
        package.base.write(self.output/package.MANIFEST, self.manifest)

    def validate(self):
        return package.validate(self.output, self.commit, self.baseline)

    def test_synthetic_win32_pe_bytes_and_bound_receipt_pass_structural_gate(self):
        self.assertEqual(self.validate(), self.manifest)

    def test_fixture_hash_alone_does_not_admit_non_pe_or_non_win32_bytes(self):
        for data in (b'not an executable', pe_file(machine=0x8664)):
            with self.subTest(sha256=digest(data)):
                self.install_fixture(data)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_fixture_bytes_cannot_change_after_receipt_generation(self):
        path = self.output/package.FIXTURE
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaises(ValueError):
            self.validate()

    def test_check_receipt_cannot_diverge_from_packaged_manifest(self):
        changed = copy.deepcopy(self.checks)
        changed['compiler'] = 'CL.EXE'
        package.base.write(self.output/package.CHECKS, changed)
        with self.assertRaises(ValueError):
            self.validate()


if __name__ == '__main__':
    unittest.main()
