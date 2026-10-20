"""Candidate identity, prior-package and qualification routing controls."""
import copy
import gzip
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from audit_catalog_publication import admit_framework_package
from package_check import BUILD_PROFILES, check_build_identity, client_slot_assets, CLIENT_SLOT_ASSET, CLIENT_SLOT_PIN, neighborhood_assets, NEIGHBORHOOD_ASSETS, frame_capture_jni
from interop_package_audit import required_methods
from upgrade_emulator_check import PREVIOUS_INPUTS, package_receipt, pin, SIGNER, PACKAGE

ROOT = Path(__file__).resolve().parents[3]


class CatalogPackagingTests(unittest.TestCase):
    def test_capture_package_requires_defined_visible_session_jni(self):
        entry = 'Java_org_coh_sessionclient_SessionNative_frameCapture'
        with tempfile.TemporaryDirectory() as directory:
            readelf = Path(directory) / 'llvm-readelf'
            readelf.write_text('explicit host symbol-output double')
            symbol = '  7: 00000001 20 FUNC GLOBAL DEFAULT 12 ' + entry + '\n'
            with patch('package_check.run', return_value=symbol):
                self.assertEqual(frame_capture_jni(b'explicit ELF symbol-audit control', readelf), entry)
            for missing in ('', symbol.replace('DEFAULT', 'HIDDEN'), symbol.replace('12 ', 'UND ')):
                with patch('package_check.run', return_value=missing), self.assertRaises(AssertionError):
                    frame_capture_jni(b'explicit ELF symbol-audit control', readelf)
        with self.assertRaises(ValueError):
            frame_capture_jni(b'control', None)

    def test_preview_uses_additive_neighborhood_pins_without_replacing_historical_manifest(self):
        source = (ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java').read_text()
        self.assertIn('readAsset("combined/build-inputs.json")', source)
        self.assertIn('.getJSONObject("neighborhood").getJSONObject("assets") : null;', source)
        self.assertIn('sceneAssetPin(records, neighborhoodRecords, names[i])', source)
        start = source.index('    private static JSONObject sceneAssetPin(')
        end = source.index('    private byte[] readAsset(', start)
        method = source[start:end]
        java = '''import java.util.HashMap;
public final class SceneAssetPinTest {
    private static class JSONObject {
        final HashMap<String,JSONObject> entries = new HashMap<>();
        JSONObject put(String key, JSONObject value) { entries.put(key,value); return this; }
        JSONObject getJSONObject(String key) throws Exception {
            if(!entries.containsKey(key)) throw new Exception("missing " + key);
            return entries.get(key);
        }
    }
''' + method + '''
    public static void main(String[] args) throws Exception {
        JSONObject original=new JSONObject(), neighborhood=new JSONObject();
        JSONObject oldPin=new JSONObject(), newPin=new JSONObject();
        String[] names={"world.bin","character.bin","rig.bin","morph.bin","locomotion.bin","walkable.bin","map.bin"};
        for(String name:names) original.put(name,oldPin);
        neighborhood.put("neighborhood-map.bin",newPin);
        for(String name:names) {
            if(sceneAssetPin(original,null,name)!=oldPin) throw new AssertionError("legacy lookup changed");
            if(sceneAssetPin(original,neighborhood,name)!=oldPin) throw new AssertionError("original pin replaced");
        }
        if(sceneAssetPin(original,neighborhood,"neighborhood-map.bin")!=newPin) throw new AssertionError("new map used original manifest");
        if(original.entries.size()!=7 || original.entries.containsKey("neighborhood-map.bin")) throw new AssertionError("original manifest mutated");
        try { sceneAssetPin(original,new JSONObject(),"neighborhood-map.bin"); throw new AssertionError("missing neighborhood pin accepted"); }
        catch(Exception expected) { }
        try { sceneAssetPin(original,neighborhood,"unknown.bin"); throw new AssertionError("unknown asset accepted"); }
        catch(Exception expected) { }
        System.out.println("18 asset pin checks passed");
    }
}
'''
        with tempfile.TemporaryDirectory(prefix='combined-scene-pin-') as directory:
            path = Path(directory) / 'SceneAssetPinTest.java'
            path.write_text(java)
            subprocess.run(['java', '-Xmx128m', 'com.sun.tools.javac.Main', '--release', '8', '-d', directory, path], check=True, capture_output=True, text=True, timeout=60)
            result = subprocess.run(['java', '-Xmx64m', '-cp', directory, 'SceneAssetPinTest'], check=True, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.stdout.strip(), '18 asset pin checks passed')

    def test_neighborhood_profile_preserves_historical_identity_and_exports(self):
        self.assertEqual(BUILD_PROFILES['entity-diagnostic'], ('15', '0.1.14-entity-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['neighborhood-diagnostic'], ('16', '0.1.15-neighborhood-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['capture-diagnostic'], ('17', '0.1.16-capture-diagnostic-test'))
        self.assertEqual(required_methods(capture_diagnostic=True), required_methods(neighborhood_diagnostic=True) | {'exportInitialReplay'})
        self.assertEqual(len(required_methods()), 9)
        self.assertEqual(len(required_methods(entity_diagnostic=True)), 11)
        self.assertEqual(required_methods(neighborhood_diagnostic=True), required_methods(entity_diagnostic=True) | {'configureClientSlots'})

    def test_entity_update_predecessor_uses_the_accepted_artifact_and_executed_apk(self):
        folder = ROOT / 'native-android/combined-client/diagnostics/entity-20261020'
        accepted = json.loads((folder / 'iteration.json').read_bytes())['next_APK14']
        executed = json.loads((folder / 'android13-0.1.14-receipt.json').read_bytes())['checks'][1]
        previous = PREVIOUS_INPUTS['entity-diagnostic']
        self.assertEqual(previous['artifact'], str(accepted['CI_artifact_id']))
        self.assertEqual(previous['archive_sha256'], accepted['CI_artifact_sha256'])
        self.assertEqual(previous['revision'], accepted['source_commit'])
        self.assertEqual(previous['apk_bytes'], executed['installed_apk_bytes'])
        self.assertEqual(previous['apk_sha256'], executed['installed_apk_sha256'])

    def test_neighborhood_slots_require_exact_uncompressed_source_bytes(self):
        source = ROOT / 'native-android/engine/entities/qualification/costume-builder-20261017/offline-primary-slots.bin.gz'
        raw = gzip.decompress(source.read_bytes())
        receipt = {'client_slots': dict(CLIENT_SLOT_PIN, asset=CLIENT_SLOT_ASSET, source=str(source.relative_to(ROOT)))}
        member = 'assets/' + CLIENT_SLOT_ASSET
        def archive(payload, compression=zipfile.ZIP_STORED):
            result = io.BytesIO()
            with zipfile.ZipFile(result, 'w', compression=compression) as output:
                output.writestr(member, payload)
            result.seek(0)
            return zipfile.ZipFile(result)
        with archive(raw) as zipped:
            self.assertEqual(client_slot_assets(zipped, receipt, 'neighborhood-diagnostic'), {member})
            with self.assertRaises(AssertionError):
                client_slot_assets(zipped, receipt, 'entity-diagnostic')
            with self.assertRaises(KeyError):
                client_slot_assets(zipped, {}, 'neighborhood-diagnostic')
        for payload, compression in [(raw[:-1], zipfile.ZIP_STORED), (b'X' + raw[1:], zipfile.ZIP_STORED), (raw, zipfile.ZIP_DEFLATED)]:
            with archive(payload, compression) as zipped, self.assertRaises(AssertionError):
                client_slot_assets(zipped, receipt, 'neighborhood-diagnostic')

    def test_neighborhood_asset_admission_keeps_historical_scene_separate(self):
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as output:
            output.writestr('assets/neighborhood-map.bin', b'incomplete source bundle')
        result.seek(0)
        receipt = {'neighborhood': {'assets': copy.deepcopy(NEIGHBORHOOD_ASSETS)}}
        with zipfile.ZipFile(result) as zipped:
            self.assertEqual(neighborhood_assets(zipped, {}, 'entity-diagnostic'), set())
            with self.assertRaises(AssertionError):
                neighborhood_assets(zipped, receipt, 'entity-diagnostic')
            with self.assertRaises(KeyError):
                neighborhood_assets(zipped, {}, 'neighborhood-diagnostic')
            with self.assertRaises(AssertionError):
                neighborhood_assets(zipped, receipt, 'neighborhood-diagnostic')

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
