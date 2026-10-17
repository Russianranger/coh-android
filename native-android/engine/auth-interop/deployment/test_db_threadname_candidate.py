"""New two-file composition/admission controls; no compiler/service/old suite runs."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import hosted_db_threadname_candidate as stage

ROOT=Path(__file__).resolve().parents[4]


class CompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='coh-threadname-composition-tests-')
        cls.prepared=Path(cls.temporary.name)/'prepared'
        cls.manifest=stage.prepare(ROOT,cls.prepared)
        cls.originals,cls.candidate=stage.expected_source_map(ROOT)
        cls.state=stage.input_state(ROOT)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_exact_existing_hunk_and_strict_checksum_composition(self):
        self.assertEqual(set(p.name for p in self.prepared.iterdir()),stage.PREPARED)
        self.assertEqual(stage.digest((self.prepared/'retained-threadname.patch').read_bytes()),stage.HUNK_SHA)
        self.assertEqual(stage.digest((self.prepared/'original-utils.c').read_bytes()),stage.THREAD_ORIGINAL)
        self.assertEqual(stage.digest((self.prepared/'candidate-utils.c').read_bytes()),stage.THREAD_FIXED)
        original=(self.prepared/'original-utils.c').read_text();fixed=(self.prepared/'candidate-utils.c').read_text()
        signature='uintptr_t x_beginthreadex(';following='\nint isHexChar('
        self.assertEqual(original.split(signature)[0],fixed.split(signature)[0])
        self.assertEqual(original.split(following)[1],fixed.split(following)[1])
        raw=(self.prepared/'original-clientcommLogin.c').read_bytes()
        self.assertEqual((self.prepared/'candidate-clientcommLogin.c').read_bytes(),stage.base.replace_checksum(raw))
        self.assertEqual(self.manifest['checksum_manifest']['candidate_function_sha256'],
                         stage.digest(stage.base.checksum_candidate.CANDIDATE.encode()))
        # The retained matrix includes original/current release+ASan/UBSan
        # 1056-check rows; validate its bytes and corpus without executing it.
        stage.base.validate_corpus(json.loads((self.prepared/'retained-policy-matrix.json').read_bytes()))
        self.assertIs(self.manifest['checksum_version_or_auth_policy_changed_by_threadname_repair'],False)
        self.assertIs(stage.POLICY['global_formatter_changed'],False)

    def test_full_inventory_exactly_two_changes_and_stage_refusals(self):
        self.assertEqual(len(self.originals),5995)
        self.assertEqual([n for n in self.originals if self.originals[n]!=self.candidate[n]],stage.CHANGED)
        for name in ('libs/UtilitiesLib/src/utils/quick_sprintf.c','Common/sql/sqlconn.c','DBServer/src/sql_fifo.c','DBServer/src/container_sql.c'):
            self.assertEqual(self.originals[name],self.candidate[name])
        names=(*stage.CHANGED,'libs/UtilitiesLib/src/utils/quick_sprintf.c')
        original={n:self.originals[n] for n in names};candidate={n:self.candidate[n] for n in names}
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)
            for name in names:
                path=source/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'upstream/ouroboros'/name,path)
            with patch.object(stage,'expected_source_map',return_value=(original,candidate)):
                self.assertEqual(stage.stage_source(ROOT,source,self.prepared),candidate)
                with self.assertRaises(ValueError):stage.stage_source(ROOT,source,self.prepared)
                (source/names[-1]).write_bytes(b'changed global formatter')
                with self.assertRaises(ValueError):stage.stage_source(ROOT,source,self.prepared)

    def test_reference_patch_and_old_candidate_reject_modified_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/stage.PATCH;path.parent.mkdir(parents=True)
            raw=(ROOT/stage.PATCH).read_bytes();path.write_bytes(raw)
            self.assertEqual(stage.repair_hunk(root),stage.repair_hunk(ROOT))
            for changed in (raw+b'\n',raw.replace(b'estrDestroy',b'free'),raw[:raw.index(b'--- a/libs/')]):
                path.write_bytes(changed)
                with self.subTest(control='patch_bytes'),self.assertRaises(ValueError):stage.repair_hunk(root)
            archive=root/stage.OLD_ARCHIVE;archive.parent.mkdir(parents=True);archive.write_bytes(b'wrong old binary archive')
            with self.assertRaises(ValueError):stage.old_evidence(root)
        with patch.object(stage,'OLD_BINARY_SHA','0'*64),self.assertRaises(ValueError):stage.old_evidence(ROOT)

    def test_prepared_bytes_cannot_be_relabelled_as_composed_source(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'output';shutil.copytree(self.prepared,target)
            with patch.object(stage,'prepare',side_effect=lambda root,out:shutil.copytree(self.prepared,out)):
                stage.check_artifacts(ROOT,target)
                for name in stage.PREPARED:
                    path=target/name;raw=path.read_bytes();path.write_bytes(raw+b'changed')
                    with self.subTest(file=name),self.assertRaises(ValueError):stage.check_artifacts(ROOT,target)
                    path.write_bytes(raw)
            with self.assertRaises(ValueError):stage.prepare(ROOT,target)

    def test_real_git_ownership_rejects_untracked_and_modified_new_helpers(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);names=stage.INPUTS
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
            git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
            git('add','--',*names);git('commit','-qm','Owned source fixture');commit=git('rev-parse','HEAD')
            with patch.object(stage.base.prior,'capture',return_value=stage.base.prior.ORIGINAL_TREE):
                self.assertEqual(stage.committed_inputs(root,commit),self.state['project_inputs_sha256'])
                name=stage.PREFIX+'deployment/hosted_db_threadname_candidate.py';path=root/name;raw=path.read_bytes()
                path.write_bytes(raw+b'\n')
                with self.assertRaises(ValueError):stage.committed_inputs(root,commit)
                path.write_bytes(raw);git('rm','--cached','-q','--',name);git('commit','-qm','Leave helper untracked')
                with self.assertRaises(ValueError):stage.committed_inputs(root,git('rev-parse','HEAD'))

    def compile_fixture(self,directory):
        output=directory/'output';tool=directory/'Git/usr/bin/patch.exe';tool.parent.mkdir(parents=True);tool.write_bytes(b'fixture')
        original={n:self.originals[n] for n in (*stage.CHANGED,'libs/UtilitiesLib/src/utils/quick_sprintf.c')}
        candidate={n:self.candidate[n] for n in original}
        class Commands:
            def __init__(owner,target):owner.output,owner.records=target,[]
            def run(owner,name,command,**kwargs):
                log=owner.output/(name+'.log');log.write_bytes(b'new composition command shell fixture')
                owner.records.append({'name':name,'argv':list(map(str,command)),'returncode':0,'log_sha256':stage.base.prior.sha(log),'log_truncated':False})
                if name=='archive-original-source':
                    archive=Path(next(str(x).split('=',1)[1] for x in command if str(x).startswith('--output=')))
                    with tarfile.open(archive,'w') as tar:
                        for name in original:
                            raw=(ROOT/'upstream/ouroboros'/name).read_bytes();item=tarfile.TarInfo('upstream/ouroboros/'+name);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
                elif name=='build-db-candidate':
                    build=Path(command[2]);pe=bytearray(4096);pe[:2]=b'MZ';struct.pack_into('<I',pe,60,64);pe[64:68]=b'PE\0\0'
                    struct.pack_into('<HH',pe,68,0x14c,1);struct.pack_into('<H',pe,84,224);struct.pack_into('<H',pe,88,0x10b)
                    struct.pack_into('<H',pe,156,3);struct.pack_into('<I',pe,144,0x3000);struct.pack_into('<I',pe,180,16)
                    struct.pack_into('<IIII',pe,320,3584,0x1000,3584,512)
                    struct.pack_into('<II',pe,192,0x1000,180)
                    for i,name in enumerate(sorted(stage.PLATFORM_DLLS)):
                        struct.pack_into('<IIIII',pe,512+20*i,0x1300+8*i,0,0,0x1600+64*i,0x1300+8*i)
                        struct.pack_into('<II',pe,1280+8*i,0x80000001,0)
                        name=name.encode()+b'\0';pe[2048+64*i:2048+64*i+len(name)]=name
                    binary=build/'bin/OptDebug/DbServer.exe';binary.parent.mkdir(parents=True);binary.write_bytes(pe)
                    (build/'CMakeCache.txt').write_bytes(b'fixture only; no compiler runs')
        qualification=directory/'composition.json';qualification.write_text(json.dumps(qualification_record(7,0,0,0)))
        args=SimpleNamespace(source_root=ROOT,output=output,expected_commit=self.state['repository_commit'],composition_qualification=qualification,
                             expected_composition_qualification_sha256=stage.base.prior.sha(qualification))
        with patch.object(stage.base.prior,'require_hosted',return_value={'repository_commit':args.expected_commit,'original_source_tree':stage.base.prior.ORIGINAL_TREE}),\
             patch.object(stage,'committed_inputs',return_value=self.state['project_inputs_sha256']),\
             patch.object(stage.base,'BuildCommands',Commands),\
             patch.object(stage,'expected_source_map',return_value=(original,candidate)),\
             patch.dict(os.environ,{'ProgramFiles':str(directory),'RUNNER_TEMP':str(directory)}):
            proof=stage.build(args)
        self.assertTrue(proof['passed'],proof)
        return output,proof,original,candidate

    def test_compile_only_shell_admission_and_composition_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            output,proof,original,candidate=self.compile_fixture(Path(temp));receipt=output/'receipt.json';binary_sha=stage.base.prior.sha(output/stage.BINARY)
            with patch.object(stage,'committed_inputs',return_value=self.state['project_inputs_sha256']),\
                 patch.object(stage,'expected_source_map',return_value=(original,candidate)):
                admitted=stage.admit(ROOT,output,stage.base.prior.sha(receipt),binary_sha)
                self.assertTrue(admitted['admitted']);self.assertFalse(admitted['service_executed'])
                for key,value in (('service_executed',True),('accepted_runtime_replaced',True),('all_staged_original_files_unchanged_after_build',False),('build_policy',stage.base.POLICY)):
                    changed=copy.deepcopy(proof);changed[key]=value;receipt.write_text(json.dumps(changed))
                    with self.subTest(key=key),self.assertRaises(ValueError):stage.admit(ROOT,output,stage.base.prior.sha(receipt),binary_sha)
                receipt.write_text(json.dumps(proof))
                path=output/'source-file-map.json';value=json.loads(path.read_text());value['files']['DBServer/src/unexpected.c']='0'*64;path.write_text(json.dumps(value))
                proof['files'][path.name]={'bytes':path.stat().st_size,'sha256':stage.base.prior.sha(path)};receipt.write_text(json.dumps(proof))
                with self.assertRaises(ValueError):stage.admit(ROOT,output,stage.base.prior.sha(receipt),binary_sha)

    def test_source_only_qualification_and_local_build_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'proof.json';value=qualification_record(7,0,0,0);path.write_text(json.dumps(value))
            with patch.object(stage,'committed_inputs',return_value=self.state['project_inputs_sha256']):
                stage.admit_composition(ROOT,path,stage.base.prior.sha(path),self.state['repository_commit'])
                for key,bad in (('tests_run',True),('tests_run',6),('failures',False),('service_executed',True),('old_policy_or_formatter_suites_repeated',True),('source_inputs_sha256',{})):
                    changed=dict(value);changed[key]=bad;path.write_text(json.dumps(changed))
                    with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_composition(ROOT,path,stage.base.prior.sha(path),self.state['repository_commit'])
            args=SimpleNamespace(source_root=ROOT,output=Path(temp)/'out',expected_commit=self.state['repository_commit'])
            with patch.dict(os.environ,{'RUNNER_ENVIRONMENT':'local-test'}),self.assertRaises(ValueError):stage.build(args)
            self.assertFalse(args.output.exists())


def qualification_record(tests,failures,errors,skipped):
    return {'schema':'coh-db-threadname-composition-tests-v1','passed':not(failures or errors or skipped),
      'tests_run':tests,'failures':failures,'errors':errors,'skipped':skipped,
      'source_inputs_sha256':stage.input_state(ROOT)['project_inputs_sha256'],
      'original_source_tree':stage.base.prior.ORIGINAL_TREE,'changed_source_paths':stage.CHANGED,
      'reference_patch_sha256':stage.PATCH_SHA,'reference_threadname_section_sha256':stage.HUNK_SHA,
      'old_candidate_archive_sha256':stage.OLD_ARCHIVE_SHA,'old_candidate_binary_sha256':stage.OLD_BINARY_SHA,
      'old_policy_or_formatter_suites_repeated':False,'service_executed':False,
      'actual_win32_compile_verified':False,'accepted_runtime_replaced':False}


if __name__=='__main__':
    receipt=None
    if '--receipt' in sys.argv:
        index=sys.argv.index('--receipt');receipt=Path(sys.argv[index+1]);del sys.argv[index:index+2]
        if receipt.exists() or receipt.is_symlink():raise ValueError('new_composition_receipt_required')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests))
    if receipt:
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps(qualification_record(result.testsRun,len(result.failures),len(result.errors),len(result.skipped)),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
