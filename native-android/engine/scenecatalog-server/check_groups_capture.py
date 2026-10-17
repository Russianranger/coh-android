#!/usr/bin/env python3
"""Qualify actual live-boundary sink/staging with original source fixtures.

Does not run a server, admit a generation, or claim actual Win32/Android layout.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,tempfile,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args):
 result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 return result.stdout
def unchanged(admitted):
 if any(path.read_bytes()!=raw for path,raw in admitted.items()):raise RuntimeError('qualification source changed')
def module(path,admitted,name=None):
 unchanged(admitted);value=types.ModuleType(name or path.stem);value.__file__=str(path);sys.modules[value.__name__]=value
 try:exec(compile(admitted[path],str(path),'exec'),value.__dict__)
 finally:unchanged(admitted)
 return value
def struct(raw,name):
 text=raw.decode();begin=text.index('typedef struct '+name);return text[begin:text.index('} '+name+';',begin)+len('} '+name+';')]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture-output',type=Path);args=parser.parse_args()
 names=['check_groups_capture.py','test_groups_capture.c','test_stage_groups_capture.py','source_groups_capture_sink.inc','stage_groups_capture.py','record_groups_compile.py','stage_groups_boundary.py','source_sink.inc','source_groups_boundary.inc','source_groups_owner.inc','source_groups_eligibility.inc','source_groups_transaction.inc','source_snapshot.inc','source_resources.inc','source_public_bounds.inc','source_resource_quiescence.inc','test_groups_boundary_raw.c','test_snapshot.c','snapshot_oracle.py','groups-owner-source-pins.json','resource-source-pins.json','stage_resources.py','stage_snapshot.py','stage_export.py']
 paths=[HERE/name for name in names]+[HERE.parent/'scenecatalog/source_export.inc']+[ROOT/name for name in ['native-android/engine/replication/groups_oracle.py','native-android/engine/replication/groups-source-pins.json','native-android/engine/replication/tests/groups_oracle_shim.h','native-android/engine/replication/tests/groups_oracle_harness.c','native-android/tools/protocol_fixture/prepare.py']]
 admitted={path:path.read_bytes() for path in paths};pins={str(path.relative_to(ROOT)):sha(raw) for path,raw in admitted.items()};modes={};binary_pins={};stack={}
 with tempfile.TemporaryDirectory(prefix='coh-groups-capture-') as directory:
  d=Path(directory);sys.pycache_prefix=str(d/'fresh-pycache');sys.dont_write_bytecode=True
  oracle=module(HERE.parent/'replication/groups_oracle.py',admitted);original,source_pins=oracle.sources_and_pins(ROOT)
  assert source_pins==json.loads(admitted[HERE.parent/'replication/groups-source-pins.json'])
  base=module(HERE/'stage_export.py',admitted);boundary=module(HERE/'stage_groups_boundary.py',admitted);module(HERE/'stage_snapshot.py',admitted);resources=module(HERE/'stage_resources.py',admitted);stage=module(HERE/'stage_groups_capture.py',admitted)
  tests=module(HERE/'test_stage_groups_capture.py',admitted)
  import unittest
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.GroupsCaptureStageTests)
  stage_result=unittest.TestResult();suite.run(stage_result)
  if not stage_result.wasSuccessful():raise RuntimeError(str(stage_result.errors)+str(stage_result.failures))
  init=oracle.read_source(ROOT,base.INIT).encode();anim=oracle.read_source(ROOT,resources.GUARD).encode();group=original[base.GROUP].encode()
  transformed=stage.transform(group,init,anim)
  assert transformed[base.INIT].count(stage.CALL)==2 and transformed[base.GROUP].count(b'coh_groups_transaction_begin(link,full_update);')==1
  assert transformed[base.GROUP].endswith(stage.TAIL) and transformed[resources.GUARD].endswith(resources.GUARD_TAIL)
  for newline in [b'\n',b'\r\n']:
   values=[raw.replace(b'\n',newline) for raw in (group,init,anim)]
   result=stage.transform(*values)
   assert {name:base.lf(raw) for name,raw in result.items()}==transformed
  for index in range(3):
   values=[group,init,anim];values[index]+=b'\n'
   # Init permits unrelated inherited source changes; group/anim are exact pins.
   if index==1:continue
   try:stage.transform(*values)
   except ValueError:pass
   else:raise AssertionError('changed original source accepted')
  path,snapshot_pins=module(HERE/'snapshot_oracle.py',admitted).prepare(ROOT,d)
  code=path.read_text().replace('int main(','int snapshot_unused_main(')
  assert code.count('modified_on_disk,pre_alloc;GroupDef **defs;')==1
  code=code.replace('modified_on_disk,pre_alloc;GroupDef **defs;','modified_on_disk,pre_alloc,idx;GroupDef **defs;')
  world=oracle.extract(original[base.GROUP],'worldSendUpdate');hooked=oracle.extract(boundary.stage(original[base.GROUP]),'worldSendUpdate')
  code=code.replace('__attribute__((no_sanitize("undefined")))\n'+world,'void worldSendUpdate(NetLink*,int);\n')
  public=oracle.read_source(ROOT,'Common/group/group.c');public_functions='\n'.join(oracle.extract(public,name) for name in ['groupInLib','groupIsPrivate','groupIsPublic'])
  extra='#define COH_SOURCE_GROUPS_OWNER_BYTES 192u\n'+struct(admitted[HERE/'source_groups_owner.inc'],'CohSourceGroupsOwner')+'\n'+struct(admitted[HERE/'source_resources.inc'],'CohSourceResourceReport')
  shared=admitted[HERE/'test_groups_boundary_raw.c'].decode().split('static int sink_open(',1)[0]
  shared=shared.replace('/* ORIGINAL_PUBLIC_FUNCTIONS */',public_functions).replace('BOUNDARY_EXTRA_TYPES',extra)
  # Fixture-shaped source owner bytes are explicit substituted input. The real
  # production producer still derives these from actual registered source objects.
  owner='memcpy(out->wire,"fixture-owned-entity",20);'
  assert shared.count(owner)==1
  shared=shared.replace(owner,'memcpy(out->wire,"COHOWN01",8);coh_source_catalog_put_u32(out->wire+8,1);coh_source_catalog_put_u32(out->wire+12,192);coh_source_catalog_put_u32(out->wire+16,99);coh_source_catalog_put_u32(out->wire+20,123);coh_source_catalog_put_u32(out->wire+24,1);coh_source_catalog_put_u32(out->wire+152,1);coh_source_catalog_put_u32(out->wire+156,1);')
  test=admitted[HERE/'test_groups_capture.c'].decode().replace('BOUNDARY_ORIGINAL_WORLD','__attribute__((no_sanitize("undefined")))\n'+hooked)
  path.write_text(code+'\n'+shared+'\n'+test);unchanged(admitted)
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=d/mode;run(['cc','-std=c99','-w','-fno-strict-aliasing','-fstack-usage',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),path,'-lm','-lz','-o',binary]);fixture=d/(mode+'.cohgtx');modes[mode]=json.loads(run([binary,fixture]));binary_pins[mode]=sha(binary.read_bytes())
   if mode=='release':fixture_raw=fixture.read_bytes()
   else:assert fixture.read_bytes()==fixture_raw
   frames={}
   for line in binary.with_name(mode+'-groups-original.su').read_text().splitlines():
    location,size,kind=line.split('\t');name=location.rsplit(':',1)[-1]
    if name.startswith('coh_groups_capture_'):
     if 'unbounded' in kind:raise ValueError('unbounded sink frame')
     frames[name]=int(size)
   stack[mode]=frames
  if args.fixture_output:args.fixture_output.parent.mkdir(parents=True,exist_ok=True);args.fixture_output.write_bytes(fixture_raw)
  assert oracle.sources_and_pins(ROOT)[1]==source_pins
 unchanged(admitted);assert all(value==modes['release'] for value in modes.values())
 report={'schema':'coh-source-groups-capture-sink-host-v1','passed':True,'source_sha256':pins,'original_source':source_pins,'snapshot_source':snapshot_pins,'staged_sha256_lf':{name:sha(raw) for name,raw in transformed.items()},'stage_tests':stage_result.testsRun,'inherited_startup_admission_substituted_in_stage_tests':True,'modes':modes,'binary_sha256':binary_pins,'stack':stack,'fixture':{'bytes':len(fixture_raw),'sha256':sha(fixture_raw)},'fresh_admitted_helper_execution':True,'original_catalog_runtime_raw_world_executed':True,'quiet_owner_resource_winapi_substituted':True,'hook_installed_in_private_transform':True,'sink_installed_in_host_fixture':True,'real_win32_build':False,'real_server_executed':False,'live_groups_captured':False,'source_generation_admitted':False,'world_authority':False,'android_executed':False}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
