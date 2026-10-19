#!/usr/bin/env python3
"""Independent, nonshipping audit; does not execute Windows or original server."""
import hashlib,json,pathlib,re,subprocess,tempfile,zipfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REV='c624352e889749f293a559003d5ae9b01a258b1c'
def sha(v):return hashlib.sha256(v).hexdigest()
def command(argv,**kw):return subprocess.run(argv,capture_output=True,**kw)
def git(path):return subprocess.check_output(['git','show',REV+':'+path],cwd=ROOT)
def record(path):
 p=pathlib.Path(path);v=p.read_bytes();return {'bytes':len(v),'sha256':sha(v)}
def main():
 failure=ROOT.parent/'failure-12154344394'
 admission=json.loads((failure/'fresh-groups-source-admission.json').read_bytes())
 entries=admission['source_sha256'];assert admission['passed'] and not admission['runtime_executed']
 assert admission['source_revision']==REV
 source_mismatches=[]
 for name,pin in entries.items():
  if sha(git(name))!=pin:source_mismatches.append(name)
 assert not source_mismatches
 ledger='native-android/engine/initial-capture/server-initial-observer/coh_server_initial_ledger.c'
 old=git(ledger);new=(ROOT/ledger).read_bytes()
 # Only formatter spelling plus its explanatory local comment may differ.
 reverse=new.replace(b' /* Original stdtypes.h wraps snprintf with an array-only size check. This\n  * API has an explicit pointer/capacity pair, so call the C99 CRT function\n  * without expanding that function-like macro in the containing server TU. */\n',b'').replace(b'n=(snprintf)(out,cap,',b'n=snprintf(out,cap,')
 assert reverse==old
 header=(ROOT/'native-android/engine/initial-capture/server-initial-observer/coh_server_initial_ledger.h').read_bytes()
 test=(ROOT/'native-android/engine/initial-capture/server-initial-observer/test_ledger.c').read_bytes()
 std=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/stdtypes.h').read_text()
 assert '#define ARRAY_SIZE_CHECKED(n)                    (sizeof(n) / ((sizeof(n)==sizeof(void*) || sizeof(n)==0)?0:sizeof((n)[0])))' in std
 assert '#define snprintf(buffer, maxlen, ...) \\\n\tsnprintf_s(buffer, ARRAY_SIZE_CHECKED(buffer), maxlen, __VA_ARGS__)' in std
 # These are the exact three original macro definitions, with only a mock
 # declaration added to make the reproducer independent of Win32 headers.
 poison='''#include <stdio.h>\nint quick_snprintf(char*,size_t,size_t,const char*,...);\n#define ARRAY_SIZE_CHECKED(n) (sizeof(n) / ((sizeof(n)==sizeof(void*) || sizeof(n)==0)?0:sizeof((n)[0])))\n#define snprintf_s quick_snprintf\n#define snprintf(buffer, maxlen, ...) snprintf_s(buffer, ARRAY_SIZE_CHECKED(buffer), maxlen, __VA_ARGS__)\n'''
 runs={}
 with tempfile.TemporaryDirectory(prefix='coh-f-ledger-') as tmp:
  work=pathlib.Path(tmp);(work/'coh_server_initial_ledger.h').write_bytes(header);(work/'test.c').write_bytes(test)
  for name,data,macro in [('checkpoint-portable',old,False),('repair-portable',new,False),('checkpoint-original-macro',old,True),('repair-original-macro',new,True)]:
   src=work/(name+'.c');src.write_bytes((poison.encode() if macro else b'')+data)
   binary=work/name
   build=command(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror=div-by-zero','-I',str(work),str(src),str(work/'test.c'),'-o',str(binary)])
   (HERE/(name+'-build.stderr')).write_bytes(build.stderr)
   item={'build_returncode':build.returncode,'build_stderr_sha256':sha(build.stderr)}
   if name=='checkpoint-original-macro':assert build.returncode!=0 and b'division by zero' in build.stderr
   else:
    assert build.returncode==0
    ran=command([str(binary)]);assert ran.returncode==0 and not ran.stderr
    (HERE/(name+'.stdout')).write_bytes(ran.stdout)
    item.update({'runtime_returncode':ran.returncode,'stdout_sha256':sha(ran.stdout),'binary':record(binary)})
   runs[name]=item
 assert len({runs[k]['stdout_sha256'] for k in ('checkpoint-portable','repair-portable','repair-original-macro')})==1
 archive=ROOT.parent/'failure-12154344394.zip'
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  members=[{'name':i.filename,'bytes':i.file_size,'sha256':sha(z.read(i))} for i in z.infolist()]
 buildlog=(failure/'fresh-groups-build-logs/build.log').read_text()
 configurelog=(failure/'fresh-groups-build-logs/configure.log').read_text()
 assert len(re.findall(r'error C2124: divide or mod by zero',buildlog))==1
 assert 'coh_server_initial_ledger.c(54,4)' in buildlog
 result={'schema':'coh-independent-observer-repair-review-v1','passed':True,'checkpoint':REV,'failed_workflow':39177526093,'artifact_id':12154344394,'artifact':record(archive),'artifact_CRC_pass':True,'artifact_members':members,'source_gate_exact_checkpoint_git_pins_verified':len(entries),'source_gate_source_mismatches':source_mismatches,'source_gate_claims_runtime':False,'repair_source':record(ROOT/ledger),'changed_runtime_semantics':'Function-like snprintf macro bypass only; formatter, explicit pointer/capacity, minimum 4096 bound, return-length check, schema, refusal flags, and original server hook semantics are unchanged. No global macro is undefined.','compiler_failure_cause':'Original stdtypes.h snprintf expands ARRAY_SIZE_CHECKED(out), whose sizeof(pointer)==sizeof(void*) branch produces denominator 0. No original intentional arithmetic exists at the ledger source call.','portable_macro_model_runs':runs,'portable_output_byte_equal_to_checkpoint':True,'portable_ledger_controls':105,'real_Windows_compilation_executed_by_this_review':False,'original_server_runtime_executed':False,'original_world_state_accepted':False,'gates_25_27':'OPEN','whole_process_RSS_or_GPU_fit_verified':False,'accepted_release_modified':False}
 (HERE/'observer-repair-review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'passed':True,'checkpoint_pins':len(entries),'equal_ledger_checks':105,'original_macro_negative':True,'real_Windows_executed':False}))
if __name__=='__main__':main()
