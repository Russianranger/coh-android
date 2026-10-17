#!/usr/bin/env python3
"""Scripted actualOSUDP observer→sourcegraph diagnostic composition; no server."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,os,random,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
producer=HERE.parent/'scenecatalog-server';mapdir=HERE.parent/'mapclient';native=ROOT/'native-android'
sources=[HERE/'coh_runtime_groups.c',HERE/'runtime_snapshot.c',HERE/'tests/runtime_matrix_bridge.c',HERE/'tests/test_runtime_groups_udp.c',HERE.parent/'scenecatalog/coh_catalog_owner.c',HERE.parent/'scenecatalog/coh_scenecatalog.c',mapdir/'coh_mapclient.c',native/'engine/replication/coh_replication.c',native/'engine/replication/coh_groups.c',native/'engine/network/coh_net.c',native/'engine/network/coh_net_frame.c',native/'engine/network/coh_net_zip.c',native/'engine/network/coh_net_udp.c',native/'protocol/coh_protocol.c',native/'src/coh_blowfish.c']
deps=sources+[HERE/'coh_runtime_groups.h',HERE/'check_runtime_groups.py',mapdir/'coh_mapclient.h',mapdir/'tests/test_mapclient.c',mapdir/'tests/large_scene_fixture.h',Path(__file__)]
# Freeze helper implementations, fixture includes and every candidate native
# transitive header BEFORE executing/importing any producer. This conservative
# header superset avoids trusting upstream function-only pins for mutable shims.
for directory in [native/'engine',native/'include',native/'protocol',native/'src']:
 deps.extend(directory.rglob('*.h'))
for directory in [producer,mapdir,HERE.parent/'replication',native/'tools/protocol_fixture',HERE.parent/'scenecatalog']:
 for extension in ['*.py','*.inc','*.json']:
  deps.extend(x for x in directory.rglob(extension) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
deps.extend([producer/'test_snapshot.c',HERE.parent/'replication/tests/groups_oracle_harness.c',HERE/'coh_scenegraph.c'])
for manifest in [mapdir/'source-pins.json',HERE.parent/'replication/source-pins.json',HERE.parent/'replication/groups-source-pins.json']:
 deps.extend(ROOT/'upstream/ouroboros'/name for name in json.loads(manifest.read_text())['sha256_lf'])
deps.extend(ROOT/'upstream/ouroboros'/name for name in ['Common/group/group.h','MapServer/src/cmdparse/cmdserver.c'])
deps=sorted(set(deps));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps};modes={}
with tempfile.TemporaryDirectory(prefix='coh-groups-udp-') as directory:
 d=Path(directory);original,source=module(producer/'snapshot_oracle.py','snapshot_original').prepare(ROOT,d)
 run(['cc','-std=c99','-O0','-fno-strict-aliasing','-w','-I'+str(producer),'-I'+str(native/'include'),original,'-lm','-lz','-o',d/'original']);original_checks=json.loads(run([d/'original',d]))
 checker=module(mapdir/'check.py','mapclient_checker');lib,protocol_pins=checker.oracle(ROOT,d);checker.fixtures(lib,d);checker.command_fixtures(ROOT,d);groups_receipt=checker.groups_fixtures(ROOT,d)
 # Reuse the byte-identical existing source-derived composite builder, without
 # executing its standalone commandline driver on import.
 tree=ast.parse((HERE/'check_runtime_groups.py').read_text());namespace={'struct':struct};exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['u32','pk','composite']],type_ignores=[]),'source_composite','exec'),namespace)
 cat=d/'snapshot-7.cohcat';snap=cat.with_suffix('.cohrts');wire=namespace['composite'](cat.read_bytes(),snap.read_bytes());assert wire[32:34]==b'\0\0'
 # Legal prefix loadscreen pages enlarge the SAME exact source graph body;
 # deterministic printable names add real compressed fragment pressure.
 rng=random.Random(20261017);pages=b''.join(bytes(rng.randrange(33,127) for _ in range(255))+b'\0' for _ in range(32));wire=wire[:32]+b'\1\1'+struct.pack('<H',32)+pages+wire[33:];body=d/'snapshot-7.groups';body.write_bytes(wire);assert len(wire)>16384
 for mode,flags in [('release',['-O1'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=d/mode;objects=[]
  for n,s in enumerate(sources):
   obj=d/f'{mode}-{n}.o';objects.append(obj);run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*(['-O0'] if s==native/'protocol/coh_protocol.c' else []),'-I'+str(d),'-I'+str(HERE),'-I'+str(mapdir),'-I'+str(native/'include'),'-c',s,'-o',obj])
  run(['cc',*flags,*objects,'-lz','-lm','-lcrypto','-o',binary]);modes[mode]=json.loads(run([binary,cat,snap,body],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 result={'passed':True,'source_sha256':pins,'original_snapshot_producer':source,'original_checks':original_checks,'map_protocol_source_pins':protocol_pins,'groups_producer':groups_receipt,'synthetic_body_bytes':len(wire),'synthetic_body_sha256':hashlib.sha256(wire).hexdigest(),'modes':modes,'scope':'actual OSUDP scripted source-derived envelope with explicit graph/catalog lifetime leases; not realserver/Thorbody/authentication','source_generation_admitted':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'body_bytes':result['synthetic_body_bytes'],'modes':modes}))
