#!/usr/bin/env python3
"""Focused complete DB account-control qualification; no old suite or server."""
from pathlib import Path
import argparse,hashlib,importlib.abc,importlib.util,json,os,shlex,subprocess,tempfile
HERE=Path(__file__).resolve().parent
def need(ok,why):
 if not ok:raise ValueError(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def run(argv,**kw):
 p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise ValueError('focused account-control command failed\n'+p.stdout+p.stderr)
 return p.stdout
def main():
 need(__debug__,'Python optimization unsupported')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve();native=root/'native-android';need(not a.output.exists(),'fresh proof output required')
 project=[native/n for n in ['engine/dbclient/coh_db_account_controls.c','engine/dbclient/coh_dbclient.c','engine/auth/coh_auth.c','protocol/coh_protocol.c','src/coh_blowfish.c']];test=HERE/'tests/test_account_controls.c';oracle=HERE/'tests/account_controls_oracle.py';manifest=HERE/'tests/account-controls-source-pins.json';prepare=native/'tools/protocol_fixture/prepare.py'
 files=set(project+[test,oracle,manifest,prepare,Path(__file__).resolve(),HERE/'ACCOUNT_CONTROLS.md',native/'engine/auth-interop/deployment/windows/auth_db_development_owner.c',native/'engine/auth-interop/deployment/windows/auth_db_development_owner.h'])
 for name in json.loads(manifest.read_bytes())['sha256_lf']:files.add(root/'upstream/ouroboros'/name)
 for source in [*project,test]:
  deps=run(['cc','-std=c11','-I'+str(native/'include'),'-MG','-MM',source]).replace('\\\n',' ').split(':',1)[1]
  for name in shlex.split(deps):
   if name=='account-fixtures.h':continue # Fixed generated oracle output below.
   path=Path(name)
   need(path.is_file(),'missing focused project dependency')
   files.add(path.resolve())
 revision=run(['git','-C',root,'rev-parse','HEAD']).strip();frozen={f.resolve():f.read_bytes()for f in files}
 def verify():
  need(run(['git','-C',root,'rev-parse','HEAD']).strip()==revision,'HEAD changed during focused qualification')
  for path,raw in frozen.items():need(path.read_bytes()==raw,'source changed during focused qualification')
 def committed():
  verify()
  for path,raw in frozen.items():need(subprocess.check_output(['git','-C',str(root),'show',revision+':'+str(path.relative_to(root))])==raw,'uncommitted focused source')
 committed();loaded=[]
 class Loader(importlib.abc.Loader):
  def __init__(self,path):self.path=path
  def create_module(self,spec):return None
  def exec_module(self,module):
   verify();need(self.path in frozen and self.path.suffix=='.py','unadmitted fixture import');module.__file__=str(self.path);module.__cached__=None;exec(compile(frozen[self.path],str(self.path),'exec',dont_inherit=True),module.__dict__);loaded.append(str(self.path.relative_to(root)));verify()
 original=importlib.util.spec_from_file_location
 def spec(name,path,*args,**kw):
  path=Path(path).resolve()
  return original(name,str(path),loader=Loader(path))if path.is_relative_to(root)else original(name,path,*args,**kw)
 modes=[('release',['-O2'])]
 if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 results={};elfs={};stack={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 importlib.util.spec_from_file_location=spec
 try:
  with tempfile.TemporaryDirectory(prefix='coh-db-account-controls-')as tmp:
   work=Path(tmp);s=spec('account_original_fixture',oracle);helper=importlib.util.module_from_spec(s);s.loader.exec_module(helper);original_proof=helper.produce(root,work);header_sha=sha((work/'account-fixtures.h').read_bytes());flags=['-std=c11','-Wall','-Wextra','-Werror','-fstack-usage','-I'+str(native/'include'),'-I'+str(work)]
   for mode,opts in modes:
    verify();objects=[]
    for i,source in enumerate(project):
     obj=work/(mode+str(i)+'.o');run(['cc',*flags,*opts,*(['-std=c99','-pedantic']if source.name=='coh_db_account_controls.c'else[]),*(['-O0']if source.name in ('coh_protocol.c','coh_blowfish.c')else[]),'-c',source,'-o',obj]);objects.append(obj)
    exe=work/mode;run(['cc',*flags,*opts,test,*objects,'-lz','-lm','-o',exe]);results[mode]=json.loads(run([exe],env=env));need(results[mode].get('passed')is True,'focused controls failed');elfs[mode]=sha(exe.read_bytes());verify();need(sha((work/'account-fixtures.h').read_bytes())==header_sha,'fixture changed')
    stack[mode]=[line for f in sorted(work.glob(mode+'*.su'))for line in f.read_text().splitlines()if 'coh_db_account_controls.c:'in line or 'coh_db_session.c:'in line]
 finally:importlib.util.spec_from_file_location=original
 committed();proof={'schema':'coh-db-account-controls-focused-tests-v1','passed':True,'source_revision':revision,'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())},'all_inputs_equal_committed_HEAD':True,'project_compilation_inputs':6,'original_trusted_fixture_compilation_inputs':1,'loaded_frozen_helpers':loaded,'original_source_oracle':original_proof,'modes':results,'binary_sha256':elfs,'production_function_stack_usage_rows':stack,'stack_usage_is_not_aggregate_admission':True,'native_bounds':{'whole_packet_bytes':65536,'per_string_bytes_including_nul':16384,'shard_rows':256,'copied_session_packet_bytes':16384},'policy':{'wait_players_only':True,'phase_deadline_uid_list_unchanged':True,'complete_body_before_control_counter_commit':True,'unknown_unsupported_and_owner_predicate_unchanged':True,'unavailable_ignored_string_variant_refused':True,'ui_catalog_transfer_state_not_published':True},'historical_suites_executed':False,'real_auth_or_db':False,'sockets_executed':False,'actual_witness_body_inferred':False,'source_generation_admitted':False,'world_authority':False,'global_aggregate_budget_admitted':False,'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor proc task walking unavailable; no new parser heap; ordinary session cleanup controlled per transaction.'}
 raw=(json.dumps(proof,indent=2)+'\n').encode();a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('xb')as f:f.write(raw)
 print(json.dumps({'passed':True,'source_inputs':len(frozen),'modes':results}))
if __name__=='__main__':main()
