#!/usr/bin/env python3
"""Raw source bounds fixtures and bounded native ownership; no capture/server."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];GRAPH=HERE.parent/'scenegraph'
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
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 sources=[GRAPH/'coh_public_bounds.c',HERE.parent/'scenecatalog/coh_catalog_owner.c',HERE.parent/'scenecatalog/coh_scenecatalog.c',GRAPH/'coh_scenegraph.c',HERE.parent/'replication/coh_replication.c',HERE.parent/'replication/coh_groups.c',GRAPH/'tests/test_public_bounds.c']
 deps=sources+[Path(__file__),HERE/'source_public_bounds.inc',HERE/'test_public_bounds.c',HERE/'PUBLIC_BOUNDS.md',HERE/'snapshot_oracle.py',HERE/'test_snapshot.c',HERE/'source_snapshot.inc',HERE.parent/'scenecatalog/source_export.inc',HERE.parent/'replication/groups_oracle.py',HERE.parent/'replication/groups-source-pins.json',HERE.parent/'replication/tests/groups_oracle_shim.h',HERE.parent/'replication/tests/groups_oracle_harness.c',ROOT/'native-android/tools/protocol_fixture/prepare.py']
 for directory in [ROOT/'native-android/engine',ROOT/'native-android/include',ROOT/'native-android/protocol',ROOT/'native-android/src']:deps.extend(directory.rglob('*.h'))
 admitted={path:path.read_bytes() for path in sorted(set(deps))};frozen={str(path.relative_to(ROOT)):sha(raw) for path,raw in admitted.items()};modes={};source_modes={};binaries={};fixtures=[];function_pins={};stack={};source_stack={}
 with tempfile.TemporaryDirectory(prefix='coh-public-bounds-') as directory:
  d=Path(directory);sys.pycache_prefix=str(d/'fresh-pycache');sys.dont_write_bytecode=True
  oracle=module(HERE.parent/'replication/groups_oracle.py',admitted);upstream,pins=oracle.sources_and_pins(ROOT);assert pins==json.loads(admitted[HERE.parent/'replication/groups-source-pins.json'])
  original,original_pins=module(HERE/'snapshot_oracle.py',admitted).prepare(ROOT,d)
  code=original.read_text().replace('int main(', 'int snapshot_unused_main(')
  assert code.count('modified_on_disk,pre_alloc;GroupDef **defs;')==1
  code=code.replace('modified_on_disk,pre_alloc;GroupDef **defs;','modified_on_disk,pre_alloc,idx;GroupDef **defs;')
  functions=[];full_sources={}
  for path,names in [('Common/group/group.c',['groupInLib','groupIsPrivate','groupIsPublic']),('Common/group/groupfilelib.c',['objectLibraryWriteBoundsFileIfDifferent'])]:
   source=oracle.read_source(ROOT,path);full_sources[path]=sha(source.encode())
   for name in names:
    body=oracle.extract(source,name);functions.append(body);function_pins[name]={'source':path,'sha256_lf':sha(body.encode())}
  code+='\n'+admitted[HERE/'test_public_bounds.c'].decode().replace('/* ORIGINAL_PUBLIC_FUNCTIONS */','\n'.join(functions));original.write_text(code)
  unchanged(admitted)
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   sbinary=d/(mode+'-original');run(['cc','-std=c99','-w','-fno-strict-aliasing','-fstack-usage',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),original,'-lm','-lz','-o',sbinary]);source_modes[mode]=json.loads(run([sbinary,d]));binaries[mode+'-original']=sha(sbinary.read_bytes())
   source_frames={}
   for line in sbinary.with_name(mode+'-original-groups-original.su').read_text().splitlines():
    loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
    if name.startswith('coh_source_public_bounds_') or name.startswith('coh_raw_bounds_'):
     if 'unbounded' in kind:raise ValueError('unbounded source supplier stack')
     source_frames[name]=int(size)
   source_stack[mode]={'supplier_frames':source_frames,'conservative_supplier_bytes':sum(source_frames.values())+8192};assert source_stack[mode]['conservative_supplier_bytes']<=65536
   current=[{str(n):sha((d/n).read_bytes()) for n in [f'public-{n}.{ext}' for n in range(8) for ext in ['cohcat','cohrbw']]}]
   if fixtures:assert current==fixtures
   else:fixtures=current
   binary=d/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fstack-usage',*flags,'-I'+str(GRAPH),*sources,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-Wl,--wrap=free','-lm','-lcrypto','-o',binary]);modes[mode]=[json.loads(run([binary,d/f'public-{n}.cohcat',d/f'public-{n}.cohrbw',int(n in (1,7))])) for n in range(8)];binaries[mode]=sha(binary.read_bytes());frames={}
   for line in binary.with_name(mode+'-coh_public_bounds.su').read_text().splitlines():
    loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
    if 'unbounded' in kind:raise ValueError('unbounded native stack')
    frames[name]=int(size)
   stack[mode]={'native_frames':frames,'conservative_native_bytes':sum(frames.values())+8192};assert stack[mode]['conservative_native_bytes']<=65536
  assert oracle.sources_and_pins(ROOT)[1]==pins
  assert {path:sha(oracle.read_source(ROOT,path).encode()) for path in full_sources}==full_sources
 unchanged(admitted);assert all(x==modes['release'] for x in modes.values());assert all(x==source_modes['release'] for x in source_modes.values())
 r={'schema':'coh-public-bounds-source-host-v1','passed':True,'source_sha256':frozen,'original_sources':original_pins,'original_public_full_sources_sha256_lf':full_sources,'original_public_functions':function_pins,'fixtures_sha256':fixtures,'modes':modes,'source_modes':source_modes,'stack':stack,'source_stack':source_stack,'binary_sha256':binaries,'helper_sources_admitted_before_execution':True,'fresh_pycache_prefix':True,'legacy_original_ubsan':False,'native_owner_sanitized':True,'new_raw_supplier_sanitized':True,'actual_win32_layout_verified':False,'actual_raw_public_rows_captured':0,'hook_installed':False,'boundary_caller_integrated':False,'live_groups_captured':False,'real_server_executed':False,'source_generation_admitted':False,'cache_equivalence_verified':False,'world_authority':False,'android_executed':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'native_checks_per_mode':{mode:sum(x['checks'] for x in cases) for mode,cases in modes.items()},'source_fixtures_per_mode':source_modes['release']['fixtures']}))
if __name__=='__main__':main()
