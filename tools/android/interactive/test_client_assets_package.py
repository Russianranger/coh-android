"""Independent asset trust roots and the MapServer-only native change boundary."""
import copy
import json
import unittest
import build_client_assets_apk as package

class AssetsPublication(unittest.TestCase):
    def test_exact_published_027_donor_is_pinned(self):
        evidence=json.loads((package.ROOT/'docs/android-evidence/recovery-0.13.27-publication.json').read_text())
        self.assertEqual(package.DONOR_APK,{k:evidence['apk'][k] for k in ('bytes','sha256')})
        receipt=evidence['artifacts']['packaging']
        self.assertEqual(package.DONOR_BUILD,{k:receipt['receipt'][k] for k in ('bytes','sha256')})
        self.assertEqual(package.DONOR_EVIDENCE_ID,receipt['id'])
        self.assertEqual(package.DONOR_EVIDENCE,{'bytes':receipt['zip_bytes'],'sha256':receipt['zip_sha256']})
        self.assertEqual(package.VERSION_NAME,'0.13.28');self.assertEqual(package.VERSION_CODE,43)
        self.assertEqual(package.ASSET_RELEASE_TAG,'coh-assets-v1.0.0')

    def test_only_mapserver_native_archive_may_change(self):
        self.assertIn('assets/runtime/game-package.tar.gz',package.REPLACED_PAYLOADS)
        for name in ('client-runtime.zip','hardware-renderer.zip','dbserver-package.tar.gz','dbserver-schema.tar.gz',
                'startup-dbserver.exe','client_gpu_profile.py','native_responsiveness_contract.py'):
            self.assertNotIn('assets/runtime/'+name,package.REPLACED_PAYLOADS)
        self.assertIn('native_client_recompiled',package.FALSE_FLAGS)
        self.assertIn('native_mapserver_recompiled',package.TRUE_FLAGS)
        self.assertIn('physical_fps_gain_validated',package.FALSE_FLAGS)

    def test_payload_boundary_rejects_silent_native_loss_and_foreign_additions(self):
        donor={'payloads':{name:package.pin(b'old') for name in package.EXTERNAL_PAYLOADS|package.REPLACED_PAYLOADS|{
            'assets/runtime/client-runtime.zip','assets/runtime/hardware-renderer.zip'}}}
        payload={name:expected for name,expected in donor['payloads'].items() if name not in package.EXTERNAL_PAYLOADS}
        payload.update({name:package.pin(b'new') for name in package.REPLACED_PAYLOADS|package.ADDED_PAYLOADS})
        package.payload_boundaries(payload,donor)
        for name in payload:
            wrong=copy.deepcopy(payload);wrong.pop(name)
            with self.subTest(name=name),self.assertRaises(ValueError):package.payload_boundaries(wrong,donor)
        for name in ('assets/runtime/client-runtime.zip','assets/runtime/hardware-renderer.zip','assets/runtime/foreign.py'):
            wrong=copy.deepcopy(payload);wrong[name]=package.pin(b'foreign')
            with self.subTest(name=name),self.assertRaises(ValueError):package.payload_boundaries(wrong,donor)

    def test_apk_manifest_pins_new_zone_assets_and_keeps_native_game_history(self):
        helpers=package.HELPERS|package.ADDED_HELPERS|{'game-package.tar.gz','asset-pack-manifest.json','kings-row-beacon-lock.json'}
        updates={name:package.pin(name.encode()) for name in helpers}
        original={'files':{'client-runtime.zip':package.DONOR_GAME},'client_render_queue':{'commit':package.NATIVE_COMMIT}}
        donor={'_client_verification':copy.deepcopy(original),'runtime_manifest':copy.deepcopy(original)}
        assets={'files':{'runtime/zones-world-supplement.zip':package.pin(b'world')}}
        client,runtime=package.verification_manifests(donor,updates,'a'*40,assets,{'repository_commit':'b'*40})
        self.assertEqual(runtime['files']['client-runtime.zip'],package.DONOR_GAME)
        self.assertEqual(runtime['client_render_queue'],original['client_render_queue'])
        self.assertEqual(client['files']['zones-world-supplement.zip'],package.pin(b'world'))
        self.assertEqual(runtime['external_asset_pack']['manifest_sha256'],updates['asset-pack-manifest.json']['sha256'])
        self.assertTrue(runtime['character_monorail_enabled'])
        self.assertEqual(donor['runtime_manifest'],original)
