#!/usr/bin/env python3
"""Private preparation/orchestration against original world producer; no server."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def unchanged(admitted):
 if any(path.read_bytes()!=raw for path,raw in admitted.items()):raise RuntimeError('qualification dependency changed')
def module(path,admitted):
 unchanged(admitted);m=types.ModuleType(path.stem);m.__file__=str(path)
 try:exec(compile(admitted[path],str(path),'exec'),m.__dict__)
 finally:unchanged(admitted)
 return m
def struct(raw,name):
 s=raw.decode();begin=s.index('typedef struct '+name);return s[begin:s.index('} '+name+';',begin)+len('} '+name+';')]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 local=['check_groups_boundary.py','stage_groups_boundary.py','test_groups_boundary.c','source_groups_boundary.inc','source_groups_owner.inc','source_groups_eligibility.inc','source_groups_transaction.inc','source_snapshot.inc','source_resources.inc','source_resource_quiescence.inc','GROUPS_BOUNDARY.md','stage_groups_transaction.py','groups-owner-source-pins.json','resource-source-pins.json']
 paths=[HERE/n for n in local]+[HERE.parent/'scenecatalog/source_export.inc']+[ROOT/n for n in ['native-android/engine/replication/groups_oracle.py','native-android/engine/replication/groups-source-pins.json','native-android/engine/replication/tests/groups_oracle_shim.h','native-android/engine/replication/tests/groups_oracle_harness.c','native-android/tools/protocol_fixture/prepare.py']]
 admitted={path:path.read_bytes() for path in paths}
 original_dependencies={**json.loads(admitted[HERE/'groups-owner-source-pins.json'])['original_sha256_lf'],**json.loads(admitted[HERE/'resource-source-pins.json'])['sha256_lf']}
 def verify_original_dependencies():
  for path,expected in original_dependencies.items():
   raw=subprocess.check_output(['git','show','HEAD:upstream/ouroboros/'+path],cwd=ROOT).replace(b'\r\n',b'\n')
   if sha(raw)!=expected:raise RuntimeError('original supplier/owner dependency changed: '+path)
 verify_original_dependencies()
 frozen={str(path.relative_to(ROOT)):sha(raw) for path,raw in admitted.items()};modes={};binaries={};stack={}
 with tempfile.TemporaryDirectory(prefix='coh-groups-boundary-') as tmp:
  directory=Path(tmp);sys.pycache_prefix=str(directory/'fresh-pycache');sys.dont_write_bytecode=True
  oracle=module(HERE.parent/'replication/groups_oracle.py',admitted);sources,pins=oracle.sources_and_pins(ROOT)
  assert pins==json.loads(admitted[HERE.parent/'replication/groups-source-pins.json'])
  stage=module(HERE/'stage_groups_boundary.py',admitted);staged=stage.stage(sources['MapServer/src/group/groupnetsend.c']);unchanged(admitted)
  # Pure staging preserves every original producer byte except two calls.
  original=sources['MapServer/src/group/groupnetsend.c'];marker='void worldSendUpdate(NetLink *link,int full_update)\n{'
  prefix=staged[staged.index('\n#include "svr/svr_base.h"'):staged.index(marker)]
  assert staged.replace(prefix,'',1).replace('    coh_groups_transaction_begin(link,full_update);\n','',1).replace('    coh_groups_transaction_finish(pak);\n','',1)==original
  for changed in [original+'\n',original.replace('pktSend(&pak,link);','pktSend(&pak,NULL);')]:
   try:stage.stage(changed)
   except ValueError:pass
   else:raise AssertionError('changed original source accepted')
  oracle.compile_oracle(ROOT,directory,sources);unchanged(admitted)
  source=(directory/'groups-original.c').read_text();world=oracle.extract(original,'worldSendUpdate');hooked=oracle.extract(staged,'worldSendUpdate')
  for path,names in oracle.SOURCE_FUNCTIONS.items():
   for name in names:
    body=oracle.extract(sources[path],name);assert source.count(body)==1
    source=source.replace(body,'__attribute__((no_sanitize("undefined")))\n'+body)
  source=source.replace('__attribute__((no_sanitize("undefined")))\n'+world,'void worldSendUpdate(NetLink*,int);\n')
  defs='typedef int (*CohSourceCatalogOutputFn)(void*,const unsigned char*,unsigned);\n'
  for path,name in [(HERE.parent/'scenecatalog/source_export.inc','CohSourceCatalogExportReport'),(HERE/'source_snapshot.inc','CohSourceSnapshotReport'),(HERE/'source_resources.inc','CohSourceResourceReport'),(HERE/'source_groups_owner.inc','CohSourceGroupsOwner')]:defs+=struct(admitted[path],name)+'\n'
  defs='#define COH_SOURCE_GROUPS_OWNER_BYTES 192u\n'+defs+'\n#define COH_SOURCE_CATALOG_MAX_BYTES (32u*1024u*1024u)\n#define COH_SNAPSHOT_MAX_BYTES (16u*1024u*1024u)\n#define COH_RESOURCE_TOTAL_MAX (64u*1024u*1024u)\n#define COH_RESOURCE_RECORD_MAX (128u*1024u)\n'
  test=admitted[HERE/'test_groups_boundary.c'].decode().replace('BOUNDARY_REPORT_TYPES',defs).replace('BOUNDARY_ORIGINAL_WORLD','__attribute__((no_sanitize("undefined")))\n'+hooked)
  (directory/'test.c').write_text(source+'\n'+test)
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=directory/mode;run(['cc','-std=c99','-w','-fno-strict-aliasing','-fstack-usage',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),directory/'test.c','-lm','-lz','-o',binary]);modes[mode]=json.loads(run([binary]));binaries[mode]=sha(binary.read_bytes());frames={}
   for line in binary.with_name(mode+'-test.su').read_text().splitlines():
    loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
    if name.startswith('coh_groups_boundary_'):
     if 'unbounded' in kind:raise ValueError('unbounded helper stack')
     frames[name]=int(size)
   stack[mode]={'helper_frames':frames,'conservative_helper_bytes':sum(frames.values())+4096}
  assert oracle.sources_and_pins(ROOT)[1]==pins
 unchanged(admitted);verify_original_dependencies();assert all(x==modes['release'] for x in modes.values())
 receipt={'schema':'coh-source-groups-boundary-preparation-v1','passed':True,'source_sha256':frozen,'original_sources':pins,'original_supplier_owner_sha256_lf':original_dependencies,'staged_group_sha256_lf':sha(staged.encode()),'modes':modes,'binary_sha256':binaries,'stack':stack,'host_static_helper_bytes':modes['release']['static_helper_bytes'],'fresh_admitted_helper_execution':True,'output_limit_bytes':128*1024*1024,'record_scratch_bytes':128*1024,'output_caps_are_not_original_allocator_bound':True,'quiet_export_owner_dependencies_substituted':True,'original_legacy_ubsan':False,'hook_installed':False,'sink_installed':False,'original_win32_compiled':False,'real_server_executed':False,'live_groups_captured':False,'source_generation_admitted':False,'crypto_auth_verified':False,'native_entity_decode_verified':False,'world_authority':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
