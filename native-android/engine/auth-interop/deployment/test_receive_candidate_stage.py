#!/usr/bin/env python3
"""Host admission tests only; synthetic PE bytes are never executed."""
import copy
import json
from pathlib import Path
import struct
import tarfile
import io
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import hosted_receive_candidate as stage
import receive_candidate as candidate

ROOT = Path(__file__).resolve().parents[4]
QUALIFICATION = ROOT / 'native-android/engine/auth-interop/evidence/receive-candidate-20261017/candidate-qualification.json'


class StageTests(unittest.TestCase):
    def test_exact_external_staging(self):
        originals = candidate.sources(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = root / 'AuthServer/src'; dest.mkdir(parents=True)
            for path in (candidate.SOCKET, candidate.IO):
                (dest / Path(path).name).write_bytes(originals[path])
            result = stage.stage_source(originals, root)
            self.assertEqual(result['SocketServerEx.cpp'], candidate.digest(candidate.replace_offset(originals[candidate.SOCKET])))
            with self.assertRaises(ValueError):
                stage.stage_source(originals, root)

    def test_build_commands_compile_only(self):
        configure, build = stage.commands(Path('source'), Path('build'), Path('patch.exe'))
        self.assertIn('Win32', configure)
        self.assertIn('-DCOX_BUILD_MAPSERVER=OFF', configure)
        self.assertIn('-DCOX_BUILD_BEACONSERVER=OFF', configure)
        self.assertEqual(build[-2:], ['--target', 'AuthServer'])
        self.assertEqual(stage.POLICY['service_execution'], False)

    def test_host_receipt_and_mutations(self):
        original = json.loads(QUALIFICATION.read_text())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'host.json'; file.write_text(json.dumps(original))
            stage.admit_host_qualification(file, stage.prior.sha(file), ROOT)
            with self.assertRaises(ValueError):
                stage.admit_host_qualification(file, '0'*64, ROOT)
            for name, value in [('passed',False), ('encrypted_account_login_verified',True),
                                ('candidate_source_sha256','0'*64), ('qualifier_sha256','0'*64),
                                ('boundary_fixture_sha256','0'*64), ('original_source_tree','0'*40),
                                ('executions',{}), ('boundary_executions',{})]:
                changed = copy.deepcopy(original); changed[name] = value; file.write_text(json.dumps(changed))
                with self.assertRaises(ValueError, msg=name):
                    stage.admit_host_qualification(file, stage.prior.sha(file), ROOT)

    def test_exact_corpus_fields(self):
        original = json.loads(QUALIFICATION.read_text())
        stage.validate_corpus(original)
        for group in ('executions', 'boundary_executions'):
            for mode in ('release', 'asan_ubsan'):
                record = original[group][mode]
                for field, value in record['result'].items():
                    changed = copy.deepcopy(original)
                    changed[group][mode]['result'][field] = (not value) if type(value) is bool else value+1
                    with self.assertRaises(ValueError,msg=f'{group}/{mode}/{field}'):
                        stage.validate_corpus(changed)
                for altered in ('0', 'G'*64, 123, None):
                    changed = copy.deepcopy(original);changed[group][mode]['binary_sha256'] = altered
                    with self.assertRaises(ValueError): stage.validate_corpus(changed)
        for field, value in [('source_mutation_rejections',True), ('source_mutation_rejections',3),
                              ('general_tcp_segmentation_accepted',True),('leak_sanitizer_enabled',True)]:
            changed=copy.deepcopy(original);changed[field]=value
            with self.assertRaises(ValueError,msg=field): stage.validate_corpus(changed)
        changed=copy.deepcopy(original);changed['boundary_executions']['release']['result']['minimum_body']=True
        with self.assertRaises(ValueError): stage.validate_corpus(changed)

    def test_build_orchestration_with_fake_compiler(self):
        # Exercise the compile orchestration without Windows, a compiler or SQL.
        originals = candidate.sources(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            temporary = Path(temp); patch_tool=temporary/'Git/usr/bin/patch.exe'
            patch_tool.parent.mkdir(parents=True);patch_tool.write_bytes(b'fixture')
            output=temporary/'output'
            class FakeCommands:
                def __init__(self, target): self.output,self.records=target,[]
                def run(self, name, command, **kwargs):
                    self.records.append({'name':name,'returncode':0})
                    (self.output/(name+'.log')).write_bytes(b'fixture')
                    if name=='archive-original-source':
                        archive=next(str(x).split('=',1)[1] for x in command if str(x).startswith('--output='))
                        with tarfile.open(archive,'w') as tar:
                            for path,data in originals.items():
                                member=tarfile.TarInfo(path);member.size=len(data);tar.addfile(member,io.BytesIO(data))
                    elif name=='build-receive-candidate':
                        build_dir=Path(command[2]); binary=build_dir/'bin/OptDebug/AuthServer.exe'
                        binary.parent.mkdir(parents=True)
                        pe=bytearray(160);pe[:2]=b'MZ';struct.pack_into('<I',pe,60,64)
                        pe[64:68]=b'PE\0\0';struct.pack_into('<H',pe,68,0x14c)
                        struct.pack_into('<H',pe,88,0x10b);struct.pack_into('<H',pe,156,2)
                        binary.write_bytes(pe);(build_dir/'CMakeCache.txt').write_text('fixture')
            args=SimpleNamespace(source_root=ROOT,output=output,expected_commit='0'*40,
                host_qualification=QUALIFICATION,expected_host_qualification_sha256=stage.prior.sha(QUALIFICATION))
            with patch.object(stage.prior,'require_hosted',return_value={'original_source_tree':stage.prior.ORIGINAL_TREE}), \
                 patch.object(stage.prior,'Commands',FakeCommands), \
                 patch.object(stage.prior,'capture',return_value=''), \
                 patch.dict(stage.os.environ,{'ProgramFiles':temp,'RUNNER_TEMP':temp}):
                proof=stage.build(args)
            self.assertTrue(proof['passed'],proof)
            self.assertFalse(proof['service_executed'])
            self.assertTrue(stage.admit(output,stage.prior.sha(output/'receipt.json'),stage.prior.sha(output/stage.BINARY))['admitted'])

    def test_binary_admission_and_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); candidate.prepare(ROOT, root/'candidate')
            directory = root/'candidate'
            # Minimal bounded PE32 fixture; header identity is all the production
            # admission claims. It is deliberately not a Windows executable.
            pe = bytearray(160); pe[:2]=b'MZ';struct.pack_into('<I',pe,60,64)
            pe[64:68]=b'PE\0\0';struct.pack_into('<H',pe,68,0x14c)
            struct.pack_into('<H',pe,88,0x10b);struct.pack_into('<H',pe,156,2)
            (directory/stage.BINARY).write_bytes(pe)
            (directory/'candidate-host-qualification.json').write_bytes(QUALIFICATION.read_bytes())
            for name in ('candidate-CMakeCache.txt','configure-receive-candidate.log','build-receive-candidate.log','archive-original-source.log'):
                (directory/name).write_bytes(b'fixture\n')
            receipt = {'schema':stage.SCHEMA,'passed':True,'build_policy':stage.POLICY,
                'original_source_tree':stage.prior.ORIGINAL_TREE,'source_inputs_unchanged':True,
                'candidate_sources_unchanged_after_build':True,'service_executed':False,
                'encrypted_account_login_verified':False,'candidate_binary':stage.prior.pe_identity(directory/stage.BINARY,2)}
            receipt['files'] = {p.name:{'bytes':p.stat().st_size,'sha256':stage.prior.sha(p)} for p in directory.iterdir()}
            file=directory/'receipt.json';file.write_text(json.dumps(receipt))
            binary_sha = stage.prior.sha(directory/stage.BINARY)
            self.assertTrue(stage.admit(directory,stage.prior.sha(file),binary_sha)['admitted'])
            with self.assertRaises(ValueError): stage.admit(directory,'0'*64,binary_sha)
            with self.assertRaises(ValueError): stage.admit(directory,stage.prior.sha(file),'0'*64)
            for name in list(receipt['files']):
                path=directory/name;data=path.read_bytes();path.write_bytes(data+b'x')
                with self.assertRaises(ValueError,msg=name): stage.admit(directory,stage.prior.sha(file),binary_sha)
                path.write_bytes(data)
            changed=copy.deepcopy(receipt);changed['service_executed']=True;file.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): stage.admit(directory,stage.prior.sha(file),binary_sha)


if __name__ == '__main__':
    unittest.main()
