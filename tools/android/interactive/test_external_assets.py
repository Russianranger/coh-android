"""Adversarial transport and compatibility tests for independent asset volumes."""
import copy
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
import package_external_assets as package

class ExternalAssets(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.inputs={}
        for name,data in (('runtime/a.zip',b'a'*311),('atlas/b.zip',b'b'*509)):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);self.inputs[name]=path
        self.manifest=package.make_manifest(self.inputs,{'base':['runtime/a.zip'],'reference':['atlas/b.zip']})

    def test_real_two_volume_zip32_roundtrip_and_same_apk_trust_root(self):
        for volume in self.manifest['volumes']:
            path=self.root/(volume+'.zip');package.write_volume(path,self.manifest,volume,self.inputs)
            self.assertEqual(package.verify_volume(path,self.manifest),volume)
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(archive.read(package.MANIFEST),package.encoded(self.manifest))
                self.assertTrue(all(stat.S_IFMT(item.external_attr>>16)==stat.S_IFREG for item in archive.infolist()))
                self.assertTrue(all(item.extract_version<45 for item in archive.infolist()))

    def test_identical_pack_is_reusable_independent_of_apk_version(self):
        self.assertNotIn('apk_version',self.manifest)
        a=self.root/'a.zip';b=self.root/'b.zip'
        package.write_volume(a,self.manifest,'base',self.inputs);package.write_volume(b,self.manifest,'base',self.inputs)
        self.assertEqual(package.file_pin(a),package.file_pin(b))

    def test_reject_missing_duplicate_and_overlapping_volume_membership(self):
        for mutation in ('missing','duplicate','foreign'):
            value=copy.deepcopy(self.manifest)
            if mutation=='missing':del value['volumes']['reference']
            elif mutation=='duplicate':value['volumes']['base'].append('atlas/b.zip');value['volumes']['base'].sort()
            else:value['volumes']['base']=['runtime/foreign.zip']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):package.validate_manifest(value)

    def test_reject_path_escape_case_identity_and_oversized_transport(self):
        for name in ('../out','runtime/../out','runtime//out','runtime/./out','/runtime/a','runtime/a\\b','runtime/colon:foo'):
            with self.subTest(name=name),self.assertRaises(ValueError):package.safe_name(name)
        value=copy.deepcopy(self.manifest);value['files']['runtime/a.zip']['bytes']=package.MAX_VOLUME_BYTES-1
        with self.assertRaises(ValueError):package.validate_manifest(value)

    def test_corruption_and_manifest_relabel_are_rejected(self):
        path=self.root/'wrong.zip'
        with zipfile.ZipFile(path,'w') as archive:
            raw=package.encoded(self.manifest);archive.writestr(package.zip_info(package.MANIFEST,len(raw)),raw)
            archive.writestr(package.zip_info('payloads/runtime/a.zip',311),b'x'*311)
        with self.assertRaises(ValueError):package.verify_volume(path,self.manifest)
        value=copy.deepcopy(self.manifest);value['version']='1.0.1'
        with self.assertRaises(ValueError):package.verify_volume(path,value)

    def test_reject_symbolic_payload_duplicate_and_partial_volume(self):
        for variant in ('link','duplicate','missing','foreign'):
            path=self.root/(variant+'.zip')
            with zipfile.ZipFile(path,'w') as archive:
                raw=package.encoded(self.manifest);archive.writestr(package.zip_info(package.MANIFEST,len(raw)),raw)
                if variant!='missing':
                    item=package.zip_info('payloads/runtime/a.zip',311)
                    if variant=='link':item.external_attr=(stat.S_IFLNK|0o777)<<16
                    archive.writestr(item,b'a'*311)
                if variant=='duplicate':
                    with self.assertWarns(UserWarning):archive.writestr('payloads/runtime/a.zip',b'a'*311)
                if variant=='foreign':archive.writestr('payloads/runtime/other',b'x')
            with self.subTest(variant=variant),self.assertRaises(ValueError):package.verify_volume(path,self.manifest)

    def test_changed_source_leaves_no_partial_output(self):
        self.inputs['runtime/a.zip'].write_bytes(b'changed')
        path=self.root/'candidate.zip'
        with self.assertRaises(ValueError):package.write_volume(path,self.manifest,'base',self.inputs)
        self.assertFalse(path.exists())

    def test_new_audio_volume_is_separate_and_exactly_owned(self):
        self.assertEqual(package.AUDIO_FILES,{'runtime/zones-audio-supplement.zip','runtime/zones-audio-supplement-manifest.json'})
        self.assertFalse(package.AUDIO_FILES & package.ZONE_FILES)
        self.assertEqual(package.volume_filename('1.0.0','audio'),'COH-Assets-1.0.0-Audio.zip')
