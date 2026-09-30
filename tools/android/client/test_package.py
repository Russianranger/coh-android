"""Exact graphical client profile, immutable donor and payload boundary tests."""
import hashlib,importlib.util,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest import mock
HERE=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
package=load('client_profile_test','package_client_runtime.py')
assets=load('client_assets_test','prepare_assets.py')
build=load('client_builder_test','build_apk.py')
host=load('client_host_test','host_smoke.py')

class ProfileTests(unittest.TestCase):
    def test_client_profile_preserves_exact_dynamic_dependencies_and_excludes_servers(self):
        value=package.package_contract('a'*40)
        self.assertEqual(21,len(value['files']))
        self.assertEqual(22680432,sum(r['size'] for r in value['files'].values()))
        self.assertEqual({'CityOfHeroes.exe'},{n for n in value['files'] if n.endswith('.exe')})
        self.assertEqual([],value['dependency_report']['unresolved'])
        for name in value['dependency_report']['explicit_dynamic_dependencies']:self.assertIn(name,value['files'])
        self.assertEqual('81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca',value['files']['CityOfHeroes.exe']['sha256'])

    def test_archive_rejects_metadata_tamper_and_payload_corruption(self):
        data=b'payload';document=package.package_contract('a'*40)
        document['files']={f'file{i}.dll':{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for i in range(21)}
        with tempfile.TemporaryDirectory() as temporary,mock.patch.object(package,'package_contract',return_value=document):
            path=Path(temporary)/'client.zip'
            def write(manifest,corrupt=False):
                with zipfile.ZipFile(path,'w') as archive:
                    archive.writestr(package.MANIFEST,json.dumps(manifest))
                    for name in document['files']:archive.writestr(name,b'changed' if corrupt else data)
            write(document);package.verify_archive(path,'a'*40)
            write(document,True)
            with self.assertRaisesRegex(ValueError,'hash differs'):package.verify_archive(path,'a'*40)
            changed=dict(document,source_commit='b'*40);write(changed)
            with self.assertRaisesRegex(ValueError,'provenance'):package.verify_archive(path,'a'*40)

    def test_import_pins_use_original_accepted_commit(self):
        donor=build.import_donor()
        self.assertEqual(36638344040,donor['run_id'])
        self.assertEqual('e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce',donor['repository_commit'])
        self.assertEqual(set(build.IMPORT_NAMES),{Path(name).name for name in donor['payloads']})
        self.assertEqual('e502b80d91c92164021684d2ea311e9e9d5c99c1b9ac178c67619844f3c5d547',donor['apk_sha256'])

    def test_client_manifest_is_separate_private_sdk35_app(self):
        path=build.ROOT/'android/client/src/main/AndroidManifest.xml';build.verify_source_manifest(path)
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)/'manifest.xml';original=path.read_text()
            for change in (original.replace('cohclienttest','cohatlastest'),original.replace('android:allowBackup="false"','android:allowBackup="true"'),original.replace('android:exported="false"','android:exported="true"')):
                target.write_text(change)
                with self.assertRaises(ValueError):build.verify_source_manifest(target)

    def test_guest_inventory_contains_actual_client_and_launcher_no_server(self):
        self.assertIn('client-runtime.zip',assets.PROBE_FILES)
        self.assertIn('client-launcher.exe',assets.PROBE_FILES)
        self.assertIn('client_startup_diagnostic.py',assets.PROBE_FILES)
        self.assertIn('presentation_diagnostic.py',assets.PROBE_FILES)
        self.assertNotIn('presentation-probe.exe',assets.PROBE_FILES)
        self.assertFalse(assets.bundle_contract()['server_packages_included'])

    def test_exact_apk_assets_reject_extra_server(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);files=[]
            names=['assets/runtime/runtime-manifest.json','assets/runtime/client-runtime.zip',*build.NATIVE_MEMBERS]
            names += ['assets/atlas/'+n for n in build.IMPORT_NAMES]
            for i,name in enumerate(names):
                path=root/str(i);path.write_bytes(b'fixture'+name.encode());files.append((path,name))
            pins={name:build.file_pin(path) for path,name in files};apk=root/'sample.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                archive.writestr('classes.dex',b'fixture');build.append_payloads(archive,files)
            build.verify_packaged_payloads(apk,pins)
            with zipfile.ZipFile(apk,'a') as archive:archive.writestr('assets/runtime/MapServer.exe',b'server')
            with self.assertRaisesRegex(ValueError,'payload set'):build.verify_packaged_payloads(apk,pins)

    def test_png_is_bounded_exact_size_and_valid_chunks(self):
        import struct,zlib
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'frame.png';host.save_png(path,bytes((0,0,255,0))*800*600)
            data=path.read_bytes();self.assertEqual(b'\x89PNG\r\n\x1a\n',data[:8]);at=8;encoded=b''
            while at<len(data):
                size=struct.unpack_from('!I',data,at)[0];kind=data[at+4:at+8];payload=data[at+8:at+8+size]
                self.assertEqual(zlib.crc32(kind+payload)&0xffffffff,struct.unpack_from('!I',data,at+8+size)[0])
                if kind==b'IDAT':encoded+=payload
                at+=12+size
            raw=zlib.decompress(encoded);self.assertEqual(600*(800*3+1),len(raw));self.assertEqual(b'\0\xff\0\0',raw[:4])

if __name__=='__main__':unittest.main()
