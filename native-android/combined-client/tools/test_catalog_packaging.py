"""Candidate identity, prior-package and qualification routing controls."""
import copy
import json
from pathlib import Path
import unittest
from audit_catalog_publication import admit_framework_package
from package_check import BUILD_PROFILES, check_build_identity
from upgrade_emulator_check import PREVIOUS_INPUTS, package_receipt, pin, SIGNER, PACKAGE

ROOT = Path(__file__).resolve().parents[3]


class CatalogPackagingTests(unittest.TestCase):
    def test_additive_candidate_identity_and_separate_build_selection(self):
        self.assertEqual(BUILD_PROFILES['catalog-diagnostic'], ('13', '0.1.12-catalog-diagnostic-test'))
        check_build_identity('13', '0.1.12-catalog-diagnostic-test', 'catalog-diagnostic')
        for name, (code, version) in BUILD_PROFILES.items():
            if name != 'catalog-diagnostic':
                with self.assertRaises(AssertionError):
                    check_build_identity(code, version, 'catalog-diagnostic')
        gradle = (ROOT / 'native-android/combined-client/app/build.gradle').read_text()
        self.assertIn("if (candidateProfile == 'catalog-diagnostic')", gradle)
        self.assertIn("versionName '0.1.12-catalog-diagnostic-test'", gradle)
        self.assertIn("getOrElse('report-diagnostic')", gradle)

    def test_previous_011_pins_match_existing_independent_package_review(self):
        previous = PREVIOUS_INPUTS['report-diagnostic']
        review = json.loads((ROOT / 'native-android/combined-client/diagnostics/report-regression-20261020/INDEPENDENT-PACKAGE-REVIEW.json').read_bytes())
        self.assertEqual(previous['artifact'], str(review['package_artifact']['id']))
        self.assertEqual(previous['archive_bytes'], review['package_artifact']['bytes'])
        self.assertEqual(previous['archive_sha256'], review['package_artifact']['sha256'])
        for key in ('bytes', 'sha256'):
            self.assertEqual(previous['apk_' + key], review['x86_64_qualification_apk'][key])
        self.assertEqual(previous['apk'], review['x86_64_qualification_apk']['name'])

    def test_previous_receipt_rejects_version_signer_revision_and_bytes_mismatch(self):
        previous = PREVIOUS_INPUTS['report-diagnostic']
        raw = b'synthetic package receipt control; never installed'
        receipt = dict(status='passed', abi='x86_64', package=PACKAGE, version_code='12',
            version_name='0.1.11-report-diagnostic-test', source_commit=previous['revision'],
            tracked_source_clean=True, signer_certificate_sha256=SIGNER, apk=pin(raw))
        package_receipt(receipt, raw, 'report-diagnostic', previous['revision'])
        for key, bad in [('status', 'failed'), ('abi', 'arm64-v8a'), ('package', 'other'),
                         ('version_code', '13'), ('version_name', '0.1.12-catalog-diagnostic-test'),
                         ('source_commit', '0' * 40), ('tracked_source_clean', False),
                         ('signer_certificate_sha256', '0' * 64)]:
            changed = copy.deepcopy(receipt)
            changed[key] = bad
            with self.subTest(key=key), self.assertRaises((ValueError, AssertionError)):
                package_receipt(changed, raw, 'report-diagnostic', previous['revision'])
        with self.assertRaises(ValueError):
            package_receipt(receipt, raw + b'changed', 'report-diagnostic', previous['revision'])

    def test_framework_must_execute_exact_current_candidate(self):
        head = 'a' * 40
        identity = dict(name='CoH-Native-Combined-0.1.12-catalog-diagnostic-x86_64.apk', bytes=1234, sha256='b' * 64)
        x86 = dict(status='passed', package=PACKAGE, abi='x86_64', source_commit=head,
            tracked_source_clean=True, version_code='13', version_name='0.1.12-catalog-diagnostic-test',
            build_profile='catalog-diagnostic', signer_certificate_sha256=SIGNER, apk=identity)
        framework = dict(status='passed', device={'api': '33'}, checks=[dict(
            check='current launcher APK identity matches exact installed package', passed=True,
            installed_apk_status='ready', installed_apk_bytes=1234, installed_apk_sha256='b' * 64)])
        admit_framework_package(framework, x86, head)
        for key, bad in [('status', 'failed'), ('package', 'wrong'), ('abi', 'arm64-v8a'),
                         ('source_commit', 'c' * 40), ('tracked_source_clean', False),
                         ('version_code', '12'), ('version_name', 'old'), ('build_profile', 'report-diagnostic'),
                         ('signer_certificate_sha256', 'c' * 64)]:
            changed = copy.deepcopy(x86)
            changed[key] = bad
            with self.subTest(package_field=key), self.assertRaises(ValueError):
                admit_framework_package(framework, changed, head)
        for key, bad in [('passed', False), ('check', 'unrelated'), ('installed_apk_status', 'pending'),
                         ('installed_apk_bytes', 1235), ('installed_apk_sha256', 'c' * 64)]:
            changed = copy.deepcopy(framework)
            changed['checks'][0][key] = bad
            with self.subTest(framework_field=key), self.assertRaises(ValueError):
                admit_framework_package(changed, x86, head)
        for checks in ([], framework['checks'] * 2):
            changed = copy.deepcopy(framework)
            changed['checks'] = checks
            with self.assertRaises(ValueError):
                admit_framework_package(changed, x86, head)

    def test_new_workflow_qualifies_all_jobs_before_test_publication(self):
        workflow = (ROOT / '.github/workflows/native-combined-catalog-diagnostic.yml').read_text()
        self.assertIn('paths: [.github/workflows/native-combined-catalog-diagnostic.yml]', workflow)
        self.assertIn('uses: ./.github/workflows/native-five-milestone-qualification.yml', workflow)
        self.assertIn('package:\n    needs: accepted-contracts', workflow)
        self.assertIn('needs: [package, android13-framework, android13-fragment-interop, android13-package-upgrade]', workflow)
        self.assertIn('--build-profile catalog-diagnostic --previous-profile report-diagnostic', workflow)
        self.assertIn('--exercise-debuggable-downgrade', workflow)
        self.assertIn('--prerelease', workflow)
        self.assertIn('audit_catalog_publication.py', workflow)
        self.assertEqual(workflow.count('-PcohBuildProfile=catalog-diagnostic'), 2)
        self.assertNotIn('gh release create coh-native-combined-v0.1.11', workflow)


if __name__ == '__main__':
    unittest.main()
