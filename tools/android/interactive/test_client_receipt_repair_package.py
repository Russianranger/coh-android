"""The hotfix retains every .28 native, guest, DEX and external asset byte."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import build_client_receipt_repair_apk as package


class ReceiptRepairPackageTests(unittest.TestCase):
    def test_only_three_packaged_payloads_change_and_version_is_monotonic(self):
        self.assertEqual(package.VERSION_NAME, '0.13.29')
        self.assertEqual(package.VERSION_CODE, 44)
        self.assertEqual(package.REPLACED_PAYLOADS, {
            'assets/runtime/game-package.tar.gz', 'assets/runtime/client-manifest.json',
            'assets/runtime/runtime-manifest.json'})
        for name in ('java_or_dex_recompiled', 'guest_helpers_changed', 'native_mapserver_recompiled',
                     'native_client_recompiled', 'world_assets_changed', 'asset_reimport_required'):
            self.assertIn(name, package.FALSE_FLAGS)

    def test_payload_boundary_refuses_native_guest_asset_loss_or_mutation(self):
        kept = {'assets/runtime/'+name for name in ('client-runtime.zip', 'hardware-renderer.zip',
            'dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game_diagnostic.py',
            'asset-pack-manifest.json', 'kings-row-beacon-lock.json')}
        names = set(package.REPLACED_PAYLOADS) | kept
        names.update('assets/runtime/retained-%02d' % index for index in range(69-len(names)))
        donor = {'payloads': {name: package.pin(name.encode()) for name in names}}
        candidate = copy.deepcopy(donor['payloads'])
        candidate.update({name: package.pin(b'reviewed repair') for name in package.REPLACED_PAYLOADS})
        package.payload_boundaries(candidate, donor)
        for name in kept:
            bad = copy.deepcopy(candidate); bad[name] = package.pin(b'unreviewed bytes')
            with self.subTest(name=name), self.assertRaises(ValueError):
                package.payload_boundaries(bad, donor)
            bad = copy.deepcopy(candidate); del bad[name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                package.payload_boundaries(bad, donor)
        with self.assertRaises(ValueError):
            package.payload_boundaries(dict(candidate, foreign=package.pin(b'foreign')), donor)

    def test_manifest_update_keeps_native_and_external_asset_ownership(self):
        donor = {'_client_verification': {'files': {'game-package.tar.gz': package.pin(b'old')}},
            'runtime_manifest': {'files': {'game-package.tar.gz': package.pin(b'old')},
                'client_bundle': {'local_server': {'mapserver': {
                    'package_repository_commit': 'c'*40, 'monorail_native_repository_commit': 'd'*40,
                    'monorail_native_run_id': 123}}},
                'external_asset_pack': {'version': '1.0.0', 'manifest_sha256': 'a'*64},
                'client_monorail': {'repository_commit': package.DONOR_COMMIT}}}
        original = copy.deepcopy(donor)
        game, manifest = package.pin(b'repaired archive'), package.pin(b'repaired serialized manifest')
        client, runtime = package.verification_manifests(donor, game, manifest, 'e'*40, {'status': 'passed'})
        mapped = runtime['client_bundle']['local_server']['mapserver']
        self.assertEqual(mapped['package_manifest_sha256'], manifest['sha256'])
        self.assertEqual(mapped['archive_pin'], game)
        self.assertEqual(mapped['package_repository_commit'], 'c'*40)
        self.assertEqual(mapped['monorail_native_repository_commit'], 'd'*40)
        self.assertEqual(mapped['monorail_native_run_id'], 123)
        self.assertEqual(runtime['client_monorail'], donor['runtime_manifest']['client_monorail'])
        self.assertEqual(runtime['external_asset_pack'], donor['runtime_manifest']['external_asset_pack'])
        self.assertEqual(runtime['files']['client-manifest.json'], package.pin(package.shared.encoded(client)))
        self.assertEqual(donor, original)

    def test_actual_published_donor_reconstructs_identically_in_independent_processes(self):
        apk = Path(os.environ.get('COH_RECEIPT_REPAIR_TEST_DONOR_APK', package.ROOT/'out/donor.apk')).resolve()
        self.assertTrue(apk.is_file(),
            'Stage authenticated .28 or .29 donor for the retained actual serialization gate')
        # This historical regression authenticates the immutable APK and recovers
        # the original .28 game archive from retained .29 native members. It does
        # not require downloading every prior APK or comparing today's reviewed
        # guest helper sources to the historical publication source pins.
        script = '''import json,sys,tempfile,zipfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import build_client_receipt_repair_apk as p
import repair_game_receipt_order as r
apk=Path(sys.argv[2])
actual=p.builder().file_pin(apk)
accepted029={'bytes':41199716,'sha256':'b417827778f451335ec5299b92e4ba2f6d2a30d6c7706d4a2a4405139236171b'}
r.require(actual in (p.DONOR_APK,accepted029),'Exact public .28 or .29 APK required')
with tempfile.TemporaryDirectory() as td,zipfile.ZipFile(apk) as archive:
    root=Path(td)
    game=root/'game-package.tar.gz';candidate=root/'native-responsiveness.json'
    game.write_bytes(archive.read('assets/runtime/game-package.tar.gz'))
    candidate.write_bytes(archive.read('assets/runtime/native-responsiveness.json'))
    if actual==accepted029:
        r.validate_archive(game,candidate)
        members=r.archive_members(game)
        members['game-package.json']=(r.ROOT/r.DONOR_GAME_FIXTURE).read_bytes()
        r.write_game_archive(game,members)
    r.require(r.pin(game.read_bytes())==r.DONOR_ARCHIVE,'Reconstructed exact .28 archive differs')
    proof=r.repair_archive(game,candidate)
    print(json.dumps({'preflight':{'receipt_order':proof}},sort_keys=True))
'''
        results = []
        for seed in ('1', '73422'):
            environment = dict(os.environ, PYTHONHASHSEED=seed)
            result = subprocess.run([sys.executable, '-c', script, str(Path(package.__file__).parent),
                str(apk)], env=environment, capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            results.append(json.loads(result.stdout))
        self.assertEqual(results[0], results[1])
        proof = results[0]['preflight']['receipt_order']
        self.assertTrue(proof['semantic_manifest_unchanged'])
        self.assertTrue(proof['fresh_create_payload_verified'])
        self.assertTrue(proof['saved_reopen_payload_verified'])
        self.assertEqual(len(proof['native_members']), 25)


if __name__ == '__main__': unittest.main()
