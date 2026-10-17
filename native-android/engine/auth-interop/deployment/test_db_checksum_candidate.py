"""Compile-only orchestration/admission controls; synthetic PE is never executed."""
import copy
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import hosted_db_checksum_candidate as stage

ROOT=Path(__file__).resolve().parents[4]
HOST=ROOT/'native-android/engine/auth-interop/evidence/db-handoff-profile-contract-20261017/db-policy-matrix.json'


class BuildTests(unittest.TestCase):
    def test_single_external_source_change_and_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);candidate=directory/'candidate';manifest=stage.prepare(ROOT,candidate)
            raw=(candidate/'original-clientcommLogin.c').read_bytes()
            self.assertEqual(manifest['changed_paths'],[stage.RELATIVE])
            source=directory/'external';file=source/stage.RELATIVE;file.parent.mkdir(parents=True);file.write_bytes(raw)
            self.assertEqual(stage.stage_source(raw,source),manifest['candidate_source_sha256'])
            self.assertEqual(file.read_bytes(),(candidate/'candidate-clientcommLogin.c').read_bytes())
            with self.assertRaises(ValueError):stage.stage_source(raw,source)
            with self.assertRaises(ValueError):stage.replace_checksum(raw+b'\n')
            with self.assertRaises(ValueError):stage.prepare(ROOT,candidate)
            file.unlink();file.symlink_to(candidate/'original-clientcommLogin.c')
            with self.assertRaises(ValueError):stage.stage_source(raw,source)

    def test_exact_host_corpus_and_mutations(self):
        original=json.loads(HOST.read_text());stage.admit_host(HOST,stage.prior.sha(HOST),ROOT)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'host.json'
            for name,row in original['executions'].items():
                for key,value in row['result'].items():
                    changed=copy.deepcopy(original)
                    changed['executions'][name]['result'][key]=not value if type(value) is bool else value+1
                    with self.subTest(execution=name,key=key),self.assertRaises(ValueError):stage.validate_corpus(changed)
            for key,value in (('qualifier_sha256','0'*64),('nondevelopment_profile_deployed',True),
                              ('live_authenticated_db_login_verified',True),('executions',{})):
                changed=copy.deepcopy(original);changed[key]=value;path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):stage.admit_host(path,stage.prior.sha(path),ROOT)
            for key in ('candidate_function_sha256','original_function_sha256','patch_sha256','original_db_login_policy_block_sha256'):
                changed=copy.deepcopy(original);changed['base_checksum_source_qualification'][key]='0'*64;path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):stage.admit_host(path,stage.prior.sha(path),ROOT)
            with self.assertRaises(ValueError):stage.admit_host(HOST,'0'*64,ROOT)

    def test_commands_no_service_or_accepted_overlays(self):
        configure,build=stage.commands(Path('source'),Path('build'),Path('patch.exe'))
        self.assertEqual(build[-2:],['--target','DbServer'])
        self.assertIn('Win32',configure);self.assertIn('-DCOX_BUILD_MAPSERVER=OFF',configure)
        self.assertIn('-DCOX_BUILD_BEACONSERVER=OFF',configure)
        for key in ('postgresql_overlay','wine_overlay','persistence_fixture','service_execution'):
            self.assertIs(stage.POLICY[key],False)

    def compile_fixture(self,directory,mutation=None):
        raw,_=stage.source_bytes(ROOT)
        tool=directory/'Git/usr/bin/patch.exe';tool.parent.mkdir(parents=True);tool.write_bytes(b'fixture')
        output=directory/'output'
        class FakeCommands:
            def __init__(self,target):self.output,self.records=target,[]
            def run(self,name,command,**kwargs):
                log=self.output/(name+'.log');log.write_bytes(b'fixture')
                self.records.append({'name':name,'argv':list(map(str,command)),'returncode':0,'log_sha256':stage.prior.sha(log),'log_truncated':False})
                if name=='archive-original-source':
                    path=next(str(x).split('=',1)[1] for x in command if str(x).startswith('--output='))
                    with tarfile.open(path,'w') as tar:
                        for name,data in ((stage.RELATIVE,raw),('Other/original.c',b'original fixture source')):
                            item=tarfile.TarInfo('upstream/ouroboros/'+name);item.size=len(data);tar.addfile(item,io.BytesIO(data))
                elif name=='build-db-candidate':
                    build=Path(command[2]);file=build/'bin/OptDebug/DbServer.exe';file.parent.mkdir(parents=True)
                    pe=bytearray(160);pe[:2]=b'MZ';struct.pack_into('<I',pe,60,64);pe[64:68]=b'PE\0\0'
                    struct.pack_into('<H',pe,68,0x14c);struct.pack_into('<H',pe,88,0x10b);struct.pack_into('<H',pe,156,3)
                    file.write_bytes(pe);(build/'CMakeCache.txt').write_bytes(b'fixture')
                    if mutation=='archived_file':(build.parent/'source/upstream/ouroboros/Other/original.c').write_bytes(b'changed')
        args=SimpleNamespace(source_root=ROOT,output=output,expected_commit=stage.prior.capture(['git','-C',ROOT,'rev-parse','HEAD']),host_qualification=HOST,expected_host_qualification_sha256=stage.prior.sha(HOST))
        real_capture=stage.prior.capture
        initial=stage.input_state(ROOT,HOST);after=copy.deepcopy(initial)
        if mutation=='head':after['repository_commit']='0'*40
        if mutation=='helper':after['helper_inputs']['deployment/checksum_candidate.py']='0'*64
        with patch.object(stage.prior,'require_hosted',return_value={'original_source_tree':stage.prior.ORIGINAL_TREE,'repository_commit':args.expected_commit}),patch.object(stage,'BuildCommands',FakeCommands),patch.object(stage.prior,'capture',side_effect=lambda argv: '' if 'status' in argv else real_capture(argv)),patch.object(stage,'input_state',side_effect=[initial,after]),patch.dict(os.environ,{'ProgramFiles':str(directory),'RUNNER_TEMP':str(directory)}):
            # source_bytes needs the genuine tree identity while final status is empty.
            with patch.object(stage,'source_bytes',return_value=(raw,stage.pinned_sources(ROOT)[1])):
                proof=stage.build(args)
        self.assertEqual(proof['passed'],mutation is None,proof)
        return output,proof

    def test_compile_orchestration_and_exact_artifact_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            output,proof=self.compile_fixture(Path(temp));receipt=output/'receipt.json';binary_sha=stage.prior.sha(output/stage.BINARY)
            accepted=stage.admit(output,stage.prior.sha(receipt),binary_sha)
            self.assertTrue(accepted['admitted']);self.assertFalse(accepted['live_authenticated_db_login_verified'])
            self.assertFalse(accepted['accepted_runtime_compatibility_verified']);self.assertFalse(accepted['nondevelopment_version_observed'])
            for name in proof['files']:
                file=output/name;data=file.read_bytes();file.write_bytes(data+b'x')
                with self.subTest(name=name),self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),binary_sha)
                file.write_bytes(data)
            with self.assertRaises(ValueError):stage.admit(output,'0'*64,binary_sha)
            with self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),'0'*64)
            for key,value in (('service_executed',True),('source_inputs_unchanged',False),('live_authenticated_db_login_verified',True),('commands',[]),('build_policy',{})):
                changed=copy.deepcopy(proof);changed[key]=value;receipt.write_text(json.dumps(changed))
                with self.subTest(key=key),self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),binary_sha)
                receipt.write_text(json.dumps(proof))

    def test_all_original_files_and_head_helper_stability(self):
        for mutation in ('archived_file','head','helper'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                output,proof=self.compile_fixture(Path(temp),mutation)
                self.assertFalse(proof['passed'])
                if mutation=='archived_file':
                    self.assertFalse(proof['all_original_source_files_unchanged_after_build'])
                    self.assertEqual(json.loads((output/'source-file-map.json').read_text())['changed_original_paths'],['Other/original.c'])
                else:self.assertFalse(proof['helper_and_head_unchanged'])
                with self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(output/'receipt.json'),stage.prior.sha(output/stage.BINARY))

    def test_exact_command_argv_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            output,proof=self.compile_fixture(Path(temp));receipt=output/'receipt.json';binary_sha=stage.prior.sha(output/stage.BINARY)
            for index,old,new in ((2,'DbServer','AuthServer'),(2,'OptDebug','Release'),(2,'2','20'),
                                  (1,'Win32','x64'),(1,'-DCOX_BUILD_MAPSERVER=OFF','-DCOX_BUILD_MAPSERVER=ON'),
                                  (0,'upstream/ouroboros','upstream')):
                changed=copy.deepcopy(proof);argv=changed['commands'][index]['argv'];argv[argv.index(old)]=new;receipt.write_text(json.dumps(changed))
                with self.subTest(old=old,new=new),self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),binary_sha)
            changed=copy.deepcopy(proof);changed['commands'][2]['argv'].append('--clean-first');receipt.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),binary_sha)
            changed=copy.deepcopy(proof);changed['command_paths']['source']='unrelated/source';receipt.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):stage.admit(output,stage.prior.sha(receipt),binary_sha)

    def test_command_recorder_preserves_argv_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder=stage.BuildCommands(Path(temp))
            def failed(owner,name,command,**kwargs):
                owner.records.append({'name':name,'returncode':1})
                raise ValueError('fixture compiler failure')
            with patch.object(stage.prior.Commands,'run',failed),self.assertRaises(ValueError):
                recorder.run('fixture',['cmake','--build',Path('build'),'--target','DbServer'])
            self.assertEqual(recorder.records[0]['argv'],['cmake','--build','build','--target','DbServer'])

    def test_hosted_guard_refuses_local_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            args=SimpleNamespace(source_root=ROOT,output=Path(temp)/'out',expected_commit='0'*40)
            with self.assertRaises(ValueError):stage.build(args)

if __name__=='__main__':unittest.main()
