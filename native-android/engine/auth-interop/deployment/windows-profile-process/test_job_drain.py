"""New source-extracted job-drain model/admission controls, never Windows APIs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


p=load('job_drain_preparation','prepare_job_drain.py')
s=load('job_drain_supervisor','supervise_inert.py')


class JobDrainControls(unittest.TestCase):
    def test_exact_one_replacement_preserves_query_and_result_guards(self):
        before=p.source_bytes();after=p.prepare(before)
        self.assertEqual(hashlib.sha256(before).hexdigest(),p.BASE_PROFILE_SHA256)
        self.assertEqual(hashlib.sha256(after).hexdigest(),s.JOB_DRAIN_SOURCE_SHA256)
        self.assertEqual(len(after),50561)
        self.assertEqual(after.decode().count(p.NEW),1)
        self.assertEqual(after.decode().replace(p.NEW,p.OLD,1).encode(),before)
        a,b='  bool JobIsEmpty()','  public void Job('
        self.assertEqual(before.decode()[before.decode().index(a):before.decode().index(b)],after.decode()[after.decode().index(a):after.decode().index(b)])
        tail='   byte[] bytes=resultPin.Bytes(64);'
        self.assertEqual(before.decode()[before.decode().index(tail):],after.decode()[after.decode().index(tail):])
        for bad in (before+b'\n',before[:-1],b'x'+before[1:]):
            with self.assertRaises(ValueError):p.prepare(bad)

    def test_source_extracted_poll_model_bounds_and_query_refusals(self):
        # The exact new C# loop is transplanted into a C++ clock/job double.
        # Only its Watch declaration type changes; statements/predicates stay
        # exact. This is a temporal model, not CLR/Windows/API qualification.
        prefix=r'''
#include <cstdio>
#include <vector>
#include <cstdlib>
static unsigned checks,cases,queries,sleeps,results;static long now_ms,advance_ms;
static std::vector<int> answers;static bool last_empty;
static void check(bool ok){++checks;if(!ok)std::abort();}
struct Refusal{int code;};
struct Milliseconds{long start;operator long()const{return now_ms-start;}};
struct Watch{Milliseconds ElapsedMilliseconds;};
struct StopwatchFactory{Watch StartNew(){Watch w={{now_ms}};return w;}} Stopwatch;
struct ThreadFactory{void Sleep(int value){check(value==20);++sleeps;now_ms+=advance_ms;}} Thread;
struct CauseFactory{int JOB;} Cause={7};
static void Need(bool ok,int code){if(!ok)throw Refusal{code};}
static bool JobIsEmpty(){
 unsigned at=queries++;int value=answers[at<answers.size()?at:answers.size()-1];
 if(value<0){throw Refusal{99};}last_empty=value!=0;return last_empty;
}
struct ResultFactory{void Same(){check(last_empty);++results;}} resultPin;
static void candidate(){
'''
        suffix=r'''
}
static void scenario(std::vector<int> input,int expected,unsigned q,unsigned nap,unsigned result,long step=20){
 ++cases;answers=input;queries=sleeps=results=0;now_ms=0;advance_ms=step;last_empty=false;int actual=0;
 try{candidate();}catch(Refusal refusal){actual=refusal.code;}
 check(actual==expected);check(queries==q);check(sleeps==nap);check(results==result);
}
int main(){
 scenario({1},0,1,0,1);scenario({0,0,1},0,3,2,1);scenario({0},7,500,500,0);
 scenario({-1},99,1,0,0);scenario({0,-1},99,2,1,0);scenario({0,1},7,1,1,0,10000);
 std::printf("{\"passed\":true,\"scenarios\":%u,\"checks\":%u,\"Windows_API\":false,\"original_owner_or_probe\":false}\n",cases,checks);return 0;
}
'''
        source=(prefix+p.NEW.replace('Stopwatch drain=','Watch drain=',1)+suffix).encode()
        output=Path(os.environ['COH_JOB_DRAIN_MODEL_OUT']);output.mkdir(exist_ok=True)
        model=output/'job-drain-model.cpp';model.write_bytes(source)
        compiler=shutil.which('c++');self.assertIsNotNone(compiler)
        image=output/'job-drain-model-elf'
        compiled=subprocess.run([compiler,'-std=c++11','-O2','-Wall','-Wextra','-Werror','-pedantic',str(model),'-o',str(image)],capture_output=True)
        (output/'model-compile.stdout').write_bytes(compiled.stdout);(output/'model-compile.stderr').write_bytes(compiled.stderr)
        self.assertEqual(compiled.returncode,0,compiled.stderr.decode())
        child=subprocess.run([str(image)],capture_output=True)
        (output/'model.stdout').write_bytes(child.stdout);(output/'model.stderr').write_bytes(child.stderr)
        self.assertEqual(child.returncode,0);self.assertFalse(child.stderr)
        result=json.loads(child.stdout);self.assertTrue(result['passed']);self.assertEqual(result['scenarios'],6)
        (output/'model-proof.json').write_text(json.dumps({'schema':'coh-job-drain-source-extracted-model-v1','source_sha256':hashlib.sha256(source).hexdigest(),'generated_CSharp_sha256':s.JOB_DRAIN_SOURCE_SHA256,'only_translation':'Stopwatch declaration type -> Watch','compiler_sha256':hashlib.sha256(Path(compiler).read_bytes()).hexdigest(),'ELF_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'result':result,'CSharp_or_Windows_API_or_old_model_execution':False},indent=2)+'\n')

    def test_new_helper_admission_refuses_source_or_scope_mutations(self):
        actual=Path(__file__).parent.parent/'qualification'/'windows-profile-path-diagnostic-20261018'/'run-39154121730'/'profile-build.json'
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);target=directory/'job-drain';target.mkdir();image=target/'OwnedProfileProcess.exe';image.write_bytes(b'new-job-drain-image-fixture')
            value=s.decode_json(actual.read_bytes());value.update(schema='coh-wpp-job-drain-build-v1',profile_source_sha256=s.PROFILE_SOURCE_SHA256,generated_source_sha256=s.JOB_DRAIN_SOURCE_SHA256,generated_source_bytes=50561,bounded_job_drain_repair=True,helper_image=dict(bytes=image.stat().st_size,sha256=s.sha(image)))
            del value['profile_path_observation_only']
            receipt=target/'job-drain-build.json';receipt.write_text(json.dumps(value));self.assertEqual(s.admit_job_drain(directory),(image,s.sha(image)))
            changes=[('schema','coh-wpp-profile-path-build-v1'),('compiler_invocations',3),('generated_source_bytes',50395)]
            changes += [(key,'0'*64) for key in value if key.endswith('_sha256')]
            changes += [(key,not item) for key,item in value.items() if type(item) is bool]
            for key,replacement in changes:
                receipt.write_text(json.dumps({**value,key:replacement}))
                with self.subTest(key=key),self.assertRaises(s.Refusal):s.admit_job_drain(directory)
            receipt.write_text(json.dumps(value));image.write_bytes(b'replaced')
            with self.assertRaises(s.Refusal):s.admit_job_drain(directory)

    def test_other_modes_conflict_before_artifact_or_windows_calls(self):
        for old in ('file_diagnostic','file_owner','identity_diagnostic','profile_diagnostic','profile_system_drive'):
            with mock.patch.object(s,'admit_artifact') as artifact,mock.patch.object(s,'Native') as native:
                status,receipt=s.execute('UNREAD','UNCREATED',job_drain=True,**{old:True})
            artifact.assert_not_called();native.assert_not_called();self.assertIsNone(receipt);self.assertFalse(status['passed'])

    def test_actual_job_refusal_keeps_observed_progress_and_cleanup_scope(self):
        path=Path(__file__).parent.parent/'qualification'/'windows-profile-system-drive-20261018'/'run-39154927985'/'inert-result.json'
        value=s.decode_json(path.read_bytes());receipt=s.parse_receipt(json.dumps(value,separators=(',',':')).encode()+b'\n',profile_diagnostic=True)
        self.assertEqual(receipt['first_failure'],'JOB')
        for name in ('new_private_acl_verified','new_private_desktop_verified','created_suspended','process_thread_token_identity_verified','owned_job_assigned','resume_previous_count_one','cleanup_complete'):
            self.assertTrue(receipt[name])
        self.assertFalse(receipt['inert_hkcu_probe_verified']);self.assertFalse(receipt['world_authority'])


if __name__=='__main__':unittest.main()
