#!/usr/bin/env python3
"""Original raw supplier in disabled boundary orchestration; no server or capture."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def unchanged(admitted):
 if any(path.read_bytes()!=raw for path,raw in admitted.items()):raise RuntimeError('qualification source changed')
def module(path,admitted):
 unchanged(admitted);m=types.ModuleType(path.stem);m.__file__=str(path)
 try:exec(compile(admitted[path],str(path),'exec'),m.__dict__)
 finally:unchanged(admitted)
 return m
def struct(raw,name):
 s=raw.decode();begin=s.index('typedef struct '+name);return s[begin:s.index('} '+name+';',begin)+len('} '+name+';')]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 local=['check_groups_boundary_raw.py','source_groups_boundary.inc','stage_groups_boundary.py','source_groups_owner.inc','source_groups_eligibility.inc','source_groups_transaction.inc','source_snapshot.inc','source_resources.inc','source_public_bounds.inc','test_groups_boundary_raw.c','test_snapshot.c','snapshot_oracle.py','GROUPS_BOUNDARY.md','GROUPS_BOUNDARY_RAW_BOUNDS.md','PUBLIC_BOUNDS.md','check_groups_boundary.py','test_groups_boundary.c','groups-owner-source-pins.json','resource-source-pins.json']
 deps=[HERE/n for n in local]+[HERE.parent/'scenecatalog/source_export.inc']+[ROOT/n for n in ['native-android/engine/replication/groups_oracle.py','native-android/engine/replication/groups-source-pins.json','native-android/engine/replication/tests/groups_oracle_shim.h','native-android/engine/replication/tests/groups_oracle_harness.c','native-android/tools/protocol_fixture/prepare.py']]
 for directory in [ROOT/'native-android/engine',ROOT/'native-android/include',ROOT/'native-android/protocol',ROOT/'native-android/src']:deps.extend(directory.rglob('*.h'))
 admitted={path:path.read_bytes() for path in sorted(set(deps))};frozen={str(path.relative_to(ROOT)):sha(raw) for path,raw in admitted.items()};modes={};binaries={};stack={}
 original_owner={**json.loads(admitted[HERE/'groups-owner-source-pins.json'])['original_sha256_lf'],**json.loads(admitted[HERE/'resource-source-pins.json'])['sha256_lf']}
 def verify_original_owner():
  for path,expected in original_owner.items():
   raw=subprocess.check_output(['git','show','HEAD:upstream/ouroboros/'+path],cwd=ROOT).replace(b'\r\n',b'\n')
   if sha(raw)!=expected:raise ValueError('source owner dependency changed')
 verify_original_owner()
 with tempfile.TemporaryDirectory(prefix='coh-groups-boundary-raw-') as directory:
  d=Path(directory);sys.pycache_prefix=str(d/'fresh-pycache');sys.dont_write_bytecode=True
  oracle=module(HERE.parent/'replication/groups_oracle.py',admitted);original,pins=oracle.sources_and_pins(ROOT);assert pins==json.loads(admitted[HERE.parent/'replication/groups-source-pins.json'])
  stage=module(HERE/'stage_groups_boundary.py',admitted);staged=stage.stage(original['MapServer/src/group/groupnetsend.c']);assert staged.count(admitted[HERE/'source_public_bounds.inc'].decode())==1
  original_path,source_pins=module(HERE/'snapshot_oracle.py',admitted).prepare(ROOT,d)
  code=original_path.read_text().replace('int main(','int snapshot_unused_main(')
  assert code.count('modified_on_disk,pre_alloc;GroupDef **defs;')==1;code=code.replace('modified_on_disk,pre_alloc;GroupDef **defs;','modified_on_disk,pre_alloc,idx;GroupDef **defs;')
  world=oracle.extract(original['MapServer/src/group/groupnetsend.c'],'worldSendUpdate');hooked=oracle.extract(staged,'worldSendUpdate')
  code=code.replace('__attribute__((no_sanitize("undefined")))\n'+world,'void worldSendUpdate(NetLink*,int);\n')
  functions=[];public_pins={};public_full={}
  source=oracle.read_source(ROOT,'Common/group/group.c');public_full['Common/group/group.c']=sha(source.encode())
  for name in ['groupInLib','groupIsPrivate','groupIsPublic']:
   body=oracle.extract(source,name);functions.append(body);public_pins[name]=sha(body.encode())
  defs='#define COH_SOURCE_GROUPS_OWNER_BYTES 192u\n'+struct(admitted[HERE/'source_groups_owner.inc'],'CohSourceGroupsOwner')+'\n'+struct(admitted[HERE/'source_resources.inc'],'CohSourceResourceReport')
  code+='\n'+admitted[HERE/'test_groups_boundary_raw.c'].decode().replace('/* ORIGINAL_PUBLIC_FUNCTIONS */','\n'.join(functions)).replace('BOUNDARY_EXTRA_TYPES',defs).replace('BOUNDARY_ORIGINAL_WORLD','__attribute__((no_sanitize("undefined")))\n'+hooked)
  original_path.write_text(code);unchanged(admitted)
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=d/mode;run(['cc','-std=c99','-w','-fno-strict-aliasing','-fstack-usage',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),original_path,'-lm','-lz','-o',binary]);modes[mode]=json.loads(run([binary]));binaries[mode]=sha(binary.read_bytes());frames={}
   for line in binary.with_name(mode+'-groups-original.su').read_text().splitlines():
    loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
    if name.startswith('coh_groups_boundary_') or name.startswith('coh_source_public_bounds_') or name.startswith('coh_raw_bounds_'):
     if 'unbounded' in kind:raise ValueError('unbounded helper stack')
     frames[name]=int(size)
   stack[mode]={'frames':frames,'conservative_boundary_raw_bytes':sum(frames.values())+8192}
  assert oracle.sources_and_pins(ROOT)[1]==pins
  assert {path:sha(oracle.read_source(ROOT,path).encode()) for path in public_full}==public_full
 unchanged(admitted);verify_original_owner();assert all(x==modes['release'] for x in modes.values())
 r={'schema':'coh-source-groups-boundary-raw-v1','passed':True,'source_sha256':frozen,'original_source':source_pins,'original_owner_sha256_lf':original_owner,'original_public_full_sha256_lf':public_full,'original_public_function_sha256_lf':public_pins,'staged_group_sha256_lf':sha(staged.encode()),'modes':modes,'stack':stack,'binary_sha256':binaries,'fresh_admitted_helper_execution':True,'raw_output_precharged_before_sink':True,'actual_raw_capture_count':0,'actual_win32_layout_verified':False,'quiet_owner_resource_dependencies_substituted':True,'original_legacy_ubsan':False,'hook_installed':False,'sink_installed':False,'real_server_executed':False,'live_groups_captured':False,'source_generation_admitted':False,'cache_equivalence_verified':False,'world_authority':False,'android_executed':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
