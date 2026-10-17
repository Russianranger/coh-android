"""Receipt refusal controls; synthetic ELF headers are never executed."""
import copy
import contextlib
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('rigid_android_runner',Path(__file__).parents[1]/'run_rigid_android.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class Admission(unittest.TestCase):
    def fixture(self,root):
        sources={name:r.c.digest(r.ROOT/name) for name in r.REQUIRED}
        fixtures={kind+'.geo':r.fixture.geo(kind) for kind in r.contract.KINDS}
        (root/'fixtures').mkdir()
        for name,data in fixtures.items():(root/'fixtures'/name).write_bytes(data)
        header=r.contract.digest_header(fixtures);(root/'rigid_fixture_digests.h').write_bytes(header)
        fixture_sha={name:hashlib.sha256(data).hexdigest() for name,data in fixtures.items()}
        builds={}
        for abi,(_,machine) in r.contract.ABIS.items():
            directory=root/'android'/abi;directory.mkdir(parents=True)
            elf=bytearray(64);elf[:7]=b'\x7fELF\x02\x01\x01';struct.pack_into('<HHI',elf,16,3,machine,1)
            binary=directory/'rigid-authored-test';binary.write_bytes(elf)
            build=dict(schema='coh-rigid-android-build-v1',passed=True,abi=abi,api=26,executed=False,
                source_revision='1'*40,source_tree='2'*40,source_sha256=sources,fixtures_sha256=fixture_sha,
                fixture_digest_header_sha256=hashlib.sha256(header).hexdigest(),digest_mode=r.DIGEST_MODE,
                binaries={'authored':dict(binary='rigid-authored-test',binary_sha256=r.c.digest(binary),executed=False,
                    expected_result=r.contract.AUTHORED,expected_packet_sha256='3'*64)},world_authority=False)
            (directory/'build.json').write_text(json.dumps(build));builds[abi]=build
        proof=dict(schema='coh-rigid-v8-qualification-v1',passed=True,clean_source_inputs=True,source_inputs_unchanged=True,
            android_built=True,android_executed=False,world_authority=False,source_revision='1'*40,source_tree='2'*40,
            source_sha256=sources,authentic_geo_v8_fixture_available=False,fixtures_sha256=fixture_sha,
            fixture_digest_header_sha256=hashlib.sha256(header).hexdigest(),
            producer_layout={'original_structs_unchanged':True,'offsets':[244,0,4,8,12,16,20,24,28,32,64,68,72,108,228,240]},
            delta_packet_oracle={'passed':True,'packet_sha256':'3'*64},android_builds=builds,host_fixture_digest_replay_qualified=True,
            host_fixture_digest_replay={'authored':{'binary_sha256':'4'*64,'result':r.contract.AUTHORED,'packet_sha256':'3'*64}},
            modes={name:dict(result=r.contract.AUTHORED,binary_sha256='4'*64) for name in ('release','address','undefined')})
        self.write(root,proof);return proof

    def write(self,root,proof):
        (root/'qualification.json').write_text(json.dumps(proof))

    def test_valid_receipt_is_admission_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);proof,entries,fixtures=r.validate(root,r.ROOT,checkout=False)
            self.assertEqual(set(entries),set(r.contract.ABIS));self.assertEqual(len(fixtures),12)
            self.assertIs(proof['android_executed'],False)

    def test_scope_modes_and_sources_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=self.fixture(root)
            for name,value in [('clean_source_inputs',False),('world_authority',True),('android_executed',True),
                               ('android_built',False),('modes',{}),('source_sha256',{}),('authentic_geo_v8_fixture_available',1)]:
                changed=copy.deepcopy(original);changed[name]=value;self.write(root,changed)
                with self.subTest(name=name),self.assertRaises(ValueError):r.validate(root,r.ROOT,checkout=False)

    def test_every_corpus_field_and_type_refuses(self):
        for actual,expected in ((False,r.contract.AUTHORED),(True,r.contract.ACTUAL)):
            for name in expected:
                changed=dict(expected);del changed[name]
                with self.subTest(actual=actual,name=name),self.assertRaises(ValueError):r.contract.result(changed,actual)
            for name,value in expected.items():
                changed=dict(expected);changed[name]=0 if type(value) is bool else True if type(value) is int else None
                with self.subTest(actual=actual,name=name),self.assertRaises(ValueError):r.contract.result(changed,actual)

    def test_fixture_header_binary_and_receipt_changes_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            names=['fixtures/valid.geo','rigid_fixture_digests.h','android/x86_64/rigid-authored-test','android/arm64-v8a/build.json']
            for name in names:
                path=root/name;data=path.read_bytes();path.write_bytes(data+b'x')
                with self.subTest(name=name),self.assertRaises(ValueError):r.validate(root,r.ROOT,checkout=False)
                path.write_bytes(data)

    def test_executing_runner_hash_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=self.fixture(root)
            for local in (Path(r.__file__),Path(r.contract.__file__),Path(r.base.__file__),Path(r.c.__file__)):
                changed=copy.deepcopy(original);relative=local.resolve().relative_to(r.ROOT).as_posix()
                changed['source_sha256'][relative]='0'*64;self.write(root,changed)
                with self.subTest(name=relative),self.assertRaises(ValueError):r.validate(root,r.ROOT,checkout=False)

    def test_admission_cli_never_calls_adb(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts=root/'artifacts';artifacts.mkdir();self.fixture(artifacts)
            output=root/'out/receipt.json';args=['rigid','--validate-only','--artifacts',str(artifacts),'--output',str(output)]
            with patch.object(r.sys,'argv',args),patch.object(r.base,'validate_checkout'), \
                 patch.object(r.c,'git_state',return_value={'source_revision':'1'*40}),patch.object(r.subprocess,'run') as command:
                self.assertEqual(r.main(),0);command.assert_not_called()
            result=json.loads(output.read_text());self.assertTrue(result['artifact_admitted'])
            for name in ('android_executed','emulator_qualified','gpu_execution','world_authority'):self.assertIs(result[name],False)

    def simulated_device(self,root,packet_bad=False,cleanup_bad=False):
        artifacts=root/'artifacts';artifacts.mkdir();self.fixture(artifacts)
        output=root/'out/receipt.json';files={}
        def execute(command,log,timeout=60):
            parts=[str(x) for x in command][3:]
            if parts==['wait-for-device']:return ''
            if parts[0]=='push':files[parts[2]]=Path(parts[1]).read_bytes();return ''
            self.assertEqual(parts[0],'shell');parts=parts[1:]
            if parts[0]=='getprop':return {'ro.build.version.sdk':'33','ro.kernel.qemu':'1',
                'ro.product.cpu.abilist':'x86_64','ro.build.fingerprint':'fixture-emulator'}[parts[1]]
            if parts[0]=='mktemp':return '/data/local/tmp/coh-rigid.fixture'
            if parts[0] in ('mkdir','chmod'):return ''
            if parts[0]=='sha256sum':
                sha=('0' if packet_bad else '3')*64 if parts[1].endswith('.packet') else hashlib.sha256(files[parts[1]]).hexdigest()
                return sha+'  '+parts[1]
            if parts[0]=='timeout':return json.dumps(r.contract.AUTHORED)
            if parts[:2]==['rm','-rf']:
                if cleanup_bad:raise ValueError('simulated cleanup refusal')
                return ''
            raise AssertionError(parts)
        args=['rigid','--artifacts',str(artifacts),'--output',str(output),'--adb','/fake/adb','--serial','fixture']
        with patch.object(r.sys,'argv',args),patch.object(r.base,'validate_checkout'), \
             patch.object(r.c,'git_state',return_value={'source_revision':'1'*40}), \
             patch.object(r.base,'bounded_execute',side_effect=execute),contextlib.redirect_stdout(io.StringIO()):
            status=r.main()
        return status,json.loads(output.read_text())

    def test_simulated_device_requires_packet_and_cleanup(self):
        # This exercises receipt flow with an in-process fake adb boundary; no
        # Android or ELF execution occurs. Temporary evidence is deleted.
        for packet_bad,cleanup_bad in ((False,False),(True,False),(False,True)):
            with tempfile.TemporaryDirectory() as temp:
                status,receipt=self.simulated_device(Path(temp),packet_bad,cleanup_bad)
                self.assertEqual(status,1 if packet_bad or cleanup_bad else 0)
                self.assertTrue(receipt['android_executed'])
                self.assertEqual(receipt['emulator_qualified'],not(packet_bad or cleanup_bad))
                self.assertEqual(receipt['tests']['authored']['packet_validated'],not packet_bad)
                self.assertIs(receipt['gpu_execution'],False)
                self.assertIs(receipt['world_authority'],False)

if __name__=='__main__':unittest.main()
