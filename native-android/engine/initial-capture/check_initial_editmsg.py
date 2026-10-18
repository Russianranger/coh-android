#!/usr/bin/env python3
"""New focused EDITMSG parser/transaction controls; no historical suite replay."""
from pathlib import Path
import argparse,hashlib,importlib.abc,importlib.util,json,os,shlex,subprocess,tempfile
HERE=Path(__file__).resolve().parent
def require(ok,why):
 if not ok:raise ValueError(why)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def run(args,**kwargs):
 result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kwargs)
 if result.returncode:raise RuntimeError(repr(args)+'\n'+result.stdout+result.stderr)
 return result.stdout
def main():
 require(__debug__,'Python optimization disables fixture assertions')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true');a=parser.parse_args();root=a.source_root.resolve();native=root/'native-android';require(not a.output.exists(),'fresh output required')
 project=[native/p for p in ('engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_session.c','engine/mapclient/coh_mapclient_owned.c','engine/replication/coh_replication.c','engine/replication/coh_groups.c','engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c','engine/network/coh_net_udp.c','engine/auth/coh_auth.c','protocol/coh_protocol.c','src/coh_blowfish.c')]
 test=HERE/'test_initial_editmsg.c';helpers=[HERE/'editmsg_fixtures.py',native/'engine/dbclient/check.py',native/'tools/protocol_fixture/prepare.py',native/'engine/replication/groups_oracle.py'];manifests=[HERE/'editmsg-source-pins.json',native/'engine/dbclient/source-pins.json',native/'engine/replication/groups-source-pins.json']
 files=set(project+[test,Path(__file__).resolve(),*helpers,*manifests,HERE/'test_initial_peer.c',HERE/'test_initial_editmsg_peer.c',HERE/'test_initial_capture_owner.c',native/'engine/replication/tests/groups_oracle_shim.h',native/'engine/replication/tests/groups_oracle_harness.c'])
 for manifest in manifests:
  for name in json.loads(manifest.read_bytes())['sha256_lf']:files.add(root/'upstream/ouroboros'/name)
 for source in project+[test]:
  deps=run(['cc','-std=c11','-I'+str(native/'include'),'-MG','-MM',source]).replace('\\\n',' ').split(':',1)[1]
  for name in shlex.split(deps):
   path=Path(name)
   if path.is_file():files.add(path.resolve())
 frozen={p.resolve():p.read_bytes()for p in files};revision=run(['git','-C',root,'rev-parse','HEAD']).strip()
 def verify():
  require(run(['git','-C',root,'rev-parse','HEAD']).strip()==revision,'source revision changed')
  for path,raw in frozen.items():require(path.read_bytes()==raw,'source changed '+str(path.relative_to(root)))
 for path,raw in frozen.items():require(subprocess.check_output(['git','-C',str(root),'show',revision+':'+str(path.relative_to(root))])==raw,'uncommitted source '+str(path.relative_to(root)))
 loaded=[]
 class FrozenLoader(importlib.abc.Loader):
  def __init__(self,path):self.path=path
  def create_module(self,spec):return None
  def exec_module(self,module):
   verify();require(self.path in frozen and self.path.suffix=='.py','unadmitted helper');module.__file__=str(self.path);module.__cached__=None;exec(compile(frozen[self.path],str(self.path),'exec',dont_inherit=True),module.__dict__);loaded.append(str(self.path.relative_to(root)));verify()
 original=importlib.util.spec_from_file_location
 def spec(name,location,*args,**kwargs):
  path=Path(location).resolve()
  return original(name,str(path),loader=FrozenLoader(path))if path.is_relative_to(root)else original(name,location,*args,**kwargs)
 def load(name,path):
  s=spec(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 modes=[('release',['-O2'])]
 if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 results={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 importlib.util.spec_from_file_location=spec
 try:
  with tempfile.TemporaryDirectory(prefix='coh-editmsg-')as tmp:
   work=Path(tmp);oracle=load('initial_editmsg_original',helpers[0]);editmsg_proof=oracle.produce_fixtures(root,work)
   db=load('initial_editmsg_db_fixture',helpers[1]);lib,_=db.oracle(root,work);db.fixtures(lib,work)
   groups=load('initial_editmsg_groups_fixture',helpers[3]);fixtures,groups_proof=groups.produce_fixtures(root,work/'groups');fixture=next(f for f in fixtures if f['name']=='minimal_world_packed');payload=bytes.fromhex(fixture['payload_hex']);(work/'groups-fixtures.h').write_text('static const unsigned char source_groups_minimal_world_packed[]={'+','.join(map(str,payload))+'};\n#define source_groups_minimal_world_packed_bits '+str(fixture['payload_bits'])+'u\n')
   generated={name:digest((work/name).read_bytes())for name in ('fixtures.h','groups-fixtures.h','editmsg-fixtures.h')};flags=['-std=c11','-Wall','-Wextra','-Werror','-I'+str(native/'include'),'-I'+str(work)]
   for mode,options in modes:
    verify();objects=[]
    for index,source in enumerate(project):
     obj=work/(mode+str(index)+'.o');extra=['-O0']if source.name in ('coh_protocol.c','coh_blowfish.c')else[];run(['cc',*flags,*options,*extra,'-c',source,'-o',obj]);objects.append(obj)
    exe=work/mode;run(['cc',*flags,*options,test,*objects,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free,--wrap=coh_net_udp_owned_release','-lz','-lm','-o',exe]);results[mode]=json.loads(run([exe],env=env));binaries[mode]=digest(exe.read_bytes());verify();require(generated=={name:digest((work/name).read_bytes())for name in generated},'generated fixtures changed')
 finally:importlib.util.spec_from_file_location=original
 verify();proof={'schema':'coh-initial-editmsg-focused-tests-v1','passed':True,'source_revision':revision,'source_sha256':{str(p.relative_to(root)):digest(raw)for p,raw in sorted(frozen.items())},'all_inputs_equal_committed_HEAD':True,'loaded_frozen_helpers':loaded,'editmsg_original_sender_fixture':editmsg_proof,'groups_setup_fixture_producer':groups_proof,'generated_fixture_sha256':generated,'modes':results,'binary_sha256':binaries,'old_public_capture_suite_executed':False,'old_owner_capture_suite_executed':False,'root_cli_checker_executed':False,'real_server':False,'actual_witness_subtype_or_text_inferred':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'global_aggregate_budget_admitted':False,'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor proc task walk unavailable; wrapped allocation and per-scenario descriptors checked.'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'source_inputs':len(frozen),'modes':results}))
if __name__=='__main__':main()
