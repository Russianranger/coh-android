"""Current report-profile identity, omission and exact upgrade driver controls."""
import copy
import unittest
from pathlib import Path
from package_check import BUILD_PROFILES, check_build_identity
from report_diagnostic_contract import REPORT_KEYS, separate_report_extension
from test_fragment_driver import sample
from interop_probe_contract import PROBE_KEYS
from fragment_interop_emulator_check import current_snapshot
from upgrade_emulator_check import PREVIOUS_INPUTS, package_receipt, pin


def report():
    value = sample()
    value.update(dict.fromkeys(PROBE_KEYS))
    value.update(owner_present=True, owner_terminal=True, initial_observation_known=True,
        initial_observed=value['raw_allents_observed'], groups_present_files=508, groups_roots=33,
        report_limit_bytes=7168, report_truncated=False, report_omitted_mask=0,
        report_invalid_mask=0, report_omitted_fields=[])
    return value


class ReportQualification(unittest.TestCase):
    def test_report_profile_is_additive_and_current_identity_is_exact(self):
        self.assertEqual(BUILD_PROFILES['original-fragment'], ('10', '0.1.9-gates25-27-test'))
        self.assertEqual(BUILD_PROFILES['memory-diagnostic'], ('11', '0.1.10-memory-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['report-diagnostic'], ('12', '0.1.11-report-diagnostic-test'))
        for code, name in BUILD_PROFILES.values():
            if code != '12':
                with self.assertRaises(AssertionError):
                    check_build_identity(code, name, 'report-diagnostic')
        source = (Path(__file__).resolve().parents[1] / 'app/build.gradle').read_text()
        self.assertIn('versionCode 12', source)
        self.assertIn("versionName '0.1.11-report-diagnostic-test'", source)

    def test_report_projection_preserves_numeric_core_and_checks_explicit_omission(self):
        value = report()
        core = separate_report_extension(value, required=True)
        self.assertEqual(set(value) - set(core), REPORT_KEYS)
        current_snapshot(value)
        value.update(first_create=None, report_truncated=True, report_omitted_mask=1,
                     report_invalid_mask=1, report_omitted_fields=['first_create'])
        current_snapshot(value)
        for key, bad in [('report_truncated', False), ('report_omitted_mask', 512),
                         ('report_invalid_mask', 3), ('report_omitted_fields', ['private']),
                         ('report_limit_bytes', 8192), ('initial_observed', None),
                         ('initial_observation_known', False), ('owner_terminal', False),
                         ('groups_roots', -1), ('owner_present', 1)]:
            changed = copy.deepcopy(value)
            changed[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                current_snapshot(changed)
        for key in REPORT_KEYS:
            changed = dict(value)
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                current_snapshot(changed)
        changed = dict(value, private_character='sensitive')
        with self.assertRaises(ValueError):
            current_snapshot(changed)

    def test_unknown_observation_is_nullable_and_cannot_be_mislabeled_known_false(self):
        value = report()
        value.update(phase='OWNER_BUSY', initial_observation_known=False, initial_observed=None)
        separate_report_extension(value, required=True)
        value['initial_observed'] = False
        with self.assertRaises(ValueError):
            separate_report_extension(value, required=True)

    def test_upgrade_pins_exact_accepted_010_and_preserves_historical_default(self):
        old = PREVIOUS_INPUTS['memory-diagnostic']
        self.assertEqual(old['artifact'], '12226012507')
        self.assertEqual(old['apk_sha256'], '4cba32800790112c22146f6f6f8f773436a816de44c3e83d1c9503b0e9ec4d49')
        self.assertEqual(PREVIOUS_INPUTS['original-fragment']['artifact'], '12159047135')
        raw = b'not an APK; exact version/receipt gate fixture only'
        receipt = dict(status='passed', abi='x86_64', package='org.coh.nativecombined',
            version_code='11', version_name='0.1.10-memory-diagnostic-test',
            source_commit=old['revision'], tracked_source_clean=True,
            signer_certificate_sha256='9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522',
            apk=pin(raw))
        package_receipt(receipt, raw, 'memory-diagnostic', old['revision'])
        with self.assertRaises(AssertionError):
            package_receipt(receipt, raw, 'report-diagnostic', old['revision'])


if __name__ == '__main__':
    unittest.main()
