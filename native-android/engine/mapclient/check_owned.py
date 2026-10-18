#!/usr/bin/env python3
"""Source-owned DB→Map bridge, actual scripted UDP and exact ELF linkage controls."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile,types,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];NATIVE=ROOT/'native-android';DB=HERE.parent/'dbclient'
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(list(map(str,args)))+'\n'+p.stdout+p.stderr)
 return p.stdout
def source_module(path,name):
 m=types.ModuleType(name);m.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
paths=[Path(__file__),HERE/'OWNED-BEGIN.md',DB/'OWNED-HANDOFF.md']
for directory in [NATIVE/'engine',NATIVE/'include',NATIVE/'protocol',NATIVE/'src',NATIVE/'tools/protocol_fixture']:
 for ext in ['*.c','*.cpp','*.h','*.py','*.inc','*.json']:paths.extend(x for x in directory.rglob(ext) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
for manifest in [DB/'source-pins.json',HERE/'source-pins.json',HERE.parent/'replication/source-pins.json',HERE.parent/'replication/groups-source-pins.json']:
 paths.extend(ROOT/'upstream/ouroboros'/n for n in json.loads(manifest.read_text())['sha256_lf'])
paths=sorted(set(paths));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
core=[HERE/'coh_mapclient.c',*[HERE.parent/'network'/n for n in ['coh_net.c','coh_net_udp.c','coh_net_frame.c','coh_net_zip.c']],*[HERE.parent/'replication'/n for n in ['coh_replication.c','coh_groups.c']],NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c']
owned=[HERE/'coh_mapclient_owned.c',DB/'coh_db_session.c',DB/'coh_db_account_controls.c',DB/'coh_dbclient.c',HERE.parent/'auth/coh_auth.c'];results={};linkage={};stack={}
probe='''#include "coh_mapclient_owned_private.h"
#include <string.h>
int main(void){CohMapConfig c;memset(&c,0,sizeof(c));c.udp.link=coh_net_default_config();c.udp.peer.address[0]=127;c.udp.peer.address[3]=1;c.udp.peer.port=7002;c.udp.local.address[0]=127;c.udp.local.address[3]=1;c.udp.receive_budget=1;c.application_timeout_ms=1000;c.message_budget=1;CohMapClient*m=coh_map_client_create(&c);if(!m)return1;CohMapOwnedBegin o={1,1,1,0,0,1};CohStatus s=coh_map_client_owned_preflight(m,&o,0);coh_map_client_destroy(m);return s!=COH_UNSUPPORTED;}'''.replace('return1','return 1')
fullprobe='''#include "coh_mapclient_owned.h"
int main(void){return coh_map_client_begin_owned(0,0,0,0)!=COH_INVALID;}'''
with tempfile.TemporaryDirectory(prefix='coh-map-owned-') as directory:
 d=Path(directory);sys.pycache_prefix=str(d/'pycache');sys.dont_write_bytecode=True;dm=source_module(DB/'check.py','db_owned_oracle');mm=source_module(HERE/'check.py','map_owned_oracle');dd=d/'db';md=d/'map';dd.mkdir();md.mkdir();dl,dbpins=dm.oracle(ROOT,dd);dm.fixtures(dl,dd);ml,mappins=mm.oracle(ROOT,md);mm.fixtures(ml,md);mm.command_fixtures(ROOT,md);groups=mm.groups_fixtures(ROOT,md)
 (d/'probe.c').write_text(probe);(d/'fullprobe.c').write_text(fullprobe);(d/'partial.c').write_text('#include "coh_mapclient_owned.h"\n#include <stdlib.h>\nvoid coh_db_handoff_owner_retire(CohDbHandoffOwner*p){(void)p;abort();}\n')
 for mode,flags in [('release',['-O1']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');co=[];ow=[]
  def compile(s,label,includes,extra=[]):
   target=d/(mode+'-'+label+'.o');run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fstack-usage',*flags,*(['-O0'] if s in [NATIVE/'protocol/coh_protocol.c',HERE.parent/'auth/coh_auth.c'] else []),*extra,*['-I'+str(p) for p in includes+[HERE,NATIVE/'include']],'-c',s,'-o',target]);return target
  for i,s in enumerate(core):co.append(compile(s,'core'+str(i),[md]))
  for i,s in enumerate(owned):ow.append(compile(s,'owned'+str(i),[dd]))
  rawtest=compile(HERE/'tests/test_mapclient.c','rawtest',[md]);ownedtest=compile(HERE/'tests/test_mapclient_owned.c','ownedtest',[dd,md]);pr=compile(d/'probe.c','probe',[md]);fp=compile(d/'fullprobe.c','fullprobe',[md]);partial=compile(d/'partial.c','partial',[md])
  libcore=d/(mode+'-core.a');libowned=d/(mode+'-owned.a');run(['ar','rcs',libcore,*co]);run(['ar','rcs',libowned,*ow]);checks={}
  for label,objects in [('raw-direct',[rawtest,*co]),('owned-direct',[ownedtest,*ow,*co]),('owned-archive',[ownedtest,libowned,libcore])]:
   binary=d/(mode+'-'+label);run(['cc',*flags,*objects,*(['-Wl,--wrap=calloc'] if label.startswith('owned-') else []),'-lz','-lm','-o',binary]);checks[label]=json.loads(run([binary],env=env))
  probes={}
  for label,objects in [('raw-archive',[pr,libcore]),('incomplete-direct',[pr,partial,*co]),('strong-owned-extraction',[fp,libowned,libcore])]:
   binary=d/(mode+'-'+label);run(['cc',*flags,*objects,'-lz','-lm','-o',binary]);run([binary],env=env);symbols=run(['nm','-g',binary]);defined=' T coh_db_handoff_owner_claim' in symbols
   if label=='strong-owned-extraction':assert defined and ' T coh_map_client_begin_owned' in symbols
   else:assert not defined
   probes[label]={'passed':True,'db_claim_definition_extracted':defined,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
  missing=subprocess.run(['cc',*flags,str(fp),str(libcore),'-lz','-lm','-o',str(d/(mode+'-missing-bridge'))],capture_output=True,text=True)
  assert missing.returncode and 'coh_map_client_begin_owned' in missing.stderr
  probes['missing-owned-bridge-link']={'refused':True,'reason':'undefined owned entry without bridge TU'}
  cpp=d/(mode+'-cpp.o');run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(HERE),'-I'+str(NATIVE/'include'),'-c',HERE/'tests/test_mapclient_owned_cpp.cpp','-o',cpp])
  for label,objects in [('cpp-direct',[cpp,*ow,*co]),('cpp-archive',[cpp,libowned,libcore])]:
   binary=d/(mode+'-'+label);run(['c++',*flags,*objects,'-lz','-lm','-o',binary]);run([binary],env=env);probes[label]={'passed':True,'real_c_objects':True,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
  core_without_guard=compile(core[0],'guard-disabled',[md],['-U__ELF__']);binary=d/(mode+'-guard-disabled');run(['cc',*flags,pr,core_without_guard,*co[1:],'-lz','-lm','-o',binary]);run([binary],env=env);probes['unsupported-format-guard']={'passed':True}
  frames={}
  for o in [co[0],ow[0]]:
   for line in o.with_suffix('.su').read_text().splitlines():
    location,size,kind=line.split('\t');name=location.rsplit(':',1)[-1]
    if o==ow[0] or name in ['coh_map_client_owned_preflight','coh_map_client_owned_attach','owned_metadata','coh_map_client_begin','authorization','clear_authorization']:
     if 'unbounded' in kind:raise ValueError('unbounded owner bridge stack')
     frames[name]=int(size)
  stack[mode]={'frames':frames,'bound_without_network_allocator_and_external_cancel':sum(frames.values())+4096};results[mode]=checks;linkage[mode]=probes
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
r={'schema':'coh-map-owned-db-handoff-v1','passed':True,'source_sha256':pins,'db_original_sha256_lf':dbpins,'map_original_sha256_lf':mappins,'groups_oracle':groups,'modes':results,'linkage':linkage,'stack':stack,'crypto_auth_verified':False,'character_identity_verified':False,'source_generation_admitted':False,'world_authority':False,'scripted_peer_only':True,'android_executed':False,'real_server_acceptance':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'inputs':len(pins),'checks':{k:{n:x['checks'] for n,x in v.items()} for k,v in results.items()}}))
