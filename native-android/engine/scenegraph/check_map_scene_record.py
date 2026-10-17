#!/usr/bin/env python3
"""Actual decoded-loan recorder over scripted source-derived UDP fixtures."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,tempfile,sys,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];MAP=HERE.parent/'mapclient';NATIVE=ROOT/'native-android'
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
paths=[Path(__file__),HERE/'LIVE_GROUPS_CAPTURE.md']
for directory in [NATIVE/'engine',NATIVE/'include',NATIVE/'protocol',NATIVE/'src',NATIVE/'tools/protocol_fixture']:
 for ext in ['*.c','*.h','*.py','*.inc','*.json']:paths.extend(x for x in directory.rglob(ext) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
for manifest in [MAP/'source-pins.json',MAP.parent/'replication/source-pins.json',MAP.parent/'replication/groups-source-pins.json']:
 paths.extend(ROOT/'upstream/ouroboros'/name for name in json.loads(manifest.read_text())['sha256_lf'])
paths=sorted(set(paths));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
m=types.ModuleType('map_record_oracle');m.__file__=str(MAP/'check.py');exec(compile((MAP/'check.py').read_bytes(),m.__file__,'exec'),m.__dict__)
stack_modes={}
sources=[HERE/'coh_map_scene_record.c',HERE/'tests/test_map_scene_record.c',MAP/'coh_mapclient.c',MAP.parent/'replication/coh_replication.c',MAP.parent/'replication/coh_groups.c',MAP.parent/'network/coh_net.c',MAP.parent/'network/coh_net_frame.c',MAP.parent/'network/coh_net_zip.c',MAP.parent/'network/coh_net_udp.c',NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c'];modes={};binaries={}
with tempfile.TemporaryDirectory(prefix='coh-map-record-') as directory:
 d=Path(directory);sys.pycache_prefix=str(d/'pycache');sys.dont_write_bytecode=True;lib,original=m.oracle(ROOT,d);m.fixtures(lib,d);m.command_fixtures(ROOT,d);groups=m.groups_fixtures(ROOT,d)
 for mode,flags in [('release',['-O1']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  objs=[]
  for i,s in enumerate(sources):
   o=d/f'{mode}-{i}.o';run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fstack-usage',*flags,*(['-O0'] if s==NATIVE/'protocol/coh_protocol.c' else []),'-I'+str(d),'-I'+str(HERE),'-I'+str(MAP),'-I'+str(NATIVE/'include'),'-c',s,'-o',o]);objs.append(o)
  frames={}
  for stem in [f'{mode}-0',f'{mode}-2']:
   for line in (d/(stem+'.su')).read_text().splitlines():
    location,size,kind=line.split('\t');name=location.rsplit(':',1)[-1]
    if stem.endswith('-0') or name in ['coh_map_client_scene_lease','scene_disjoint']:
     if 'unbounded' in kind:raise ValueError('unbounded recorder stack')
     frames[name]=int(size)
  bound=sum(frames.values())+4096
  if bound>65536:raise ValueError('recorder/getter stack reservation exceeded')
  stack_modes[mode]={'frames':frames,'conservative_bound':bound,'reserved_bytes':65536,'external_digest_callback_and_parent_stack_included':False}
  binary=d/mode;run(['cc',*flags,*objs,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-Wl,--wrap=free','-lz','-lm','-lcrypto','-o',binary]);modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=hashlib.sha256(binary.read_bytes()).hexdigest()
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
r={'schema':'coh-map-scene-record-v1','passed':True,'source_sha256':pins,'original_sha256_lf':original,'groups_oracle':groups,'modes':modes,'stack_modes':stack_modes,'binary_sha256':binaries,'actual_client_loan_verified':True,'scripted_peer_only':True,'session_owner_retained':False,'selected_dbid_owner_bound':False,'source_generation_admitted':False,'world_authority':False,'android_executed':False,'real_server_capture':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'checks':{k:v['checks'] for k,v in modes.items()},'inputs':len(pins)}))
