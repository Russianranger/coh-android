#!/usr/bin/env python3
"""Source-derived synthetic GROUPS/catalog/snapshot correlation controls; no service."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def module(p):
 s=importlib.util.spec_from_file_location('source_oracle',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def pk(n):return struct.pack('<I',n)
def composite(cat,snap):
 files=[];at=48
 for f in range(u32(cat,24)):
  idx,crc,slots,records,n=struct.unpack_from('<5I',cat,at);at+=20;name=cat[at:at+n];at+=n;rows=[]
  for _ in range(records):
   slot,bits,size,aligned=struct.unpack_from('<4I',cat,at);at+=16;assert aligned==1 and bits==size*8;rows.append(cat[at:at+size]);at+=size
  files.append((name,crc,rows))
 assert at==len(cat)
 # Pure synthetic envelope, carrying exact unchanged original sendDef/sendMat4
 # bytes from the qualified source capture fixture. It is not a worldSendUpdate
 # execution or a retained live GROUPS message.
 b=pk(0)+pk(0)+b'\1\0'+pk(0)+pk(0)+pk(1)+b'\0\0'+pk(0)+b'\0\0'+(files[0][0] if files else b'\0')+b'\1'+pk(len(files))
 for f in [*range(1,len(files)),0] if files else []:
  name,crc,rows=files[f];b+=b'\1'+name+pk(crc)+b'\0'+b''.join(rows)+pk(0)
 at=80
 for r in range(u32(snap,44)):
  row=struct.unpack_from('<8I',snap,at);at+=32;assert row[0]==r;b+=pk(r)
  if row[1]:
   name=snap[at:at+row[5]];at+=row[5]+48;b+=name+snap[at:at+row[7]];at+=row[7]
  else:b+=b'\0'
 b+=pk(0xffffffff)+pk(len(files))+pk(u32(snap,48))+pk(u32(cat,32))+pk(u32(cat,36));return pk(6)+b
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
producer=HERE.parent/'scenecatalog-server';sources=[HERE/'coh_catalog_seed.c',HERE/'coh_runtime_groups.c',HERE/'coh_runtime_groups_witness.c',HERE/'runtime_snapshot.c',HERE/'tests/runtime_matrix_bridge.c',HERE/'tests/test_catalog_seed.c',HERE.parent/'scenecatalog/coh_catalog_owner.c',HERE.parent/'scenecatalog/coh_scenecatalog.c',HERE.parent/'replication/coh_replication.c',HERE.parent/'replication/coh_groups.c'];deps=sources+[HERE/'coh_runtime_groups.h',HERE.parent/'replication/coh_groups.h',Path(__file__)]
native=ROOT/'native-android';mapdir=HERE.parent/'mapclient'
# Freeze helper implementations, fixture includes and every candidate native
# transitive header BEFORE executing/importing any producer. This conservative
# header superset avoids trusting upstream function-only pins for mutable shims.
for directory in [native/'engine',native/'include',native/'protocol',native/'src']:
 deps.extend(directory.rglob('*.h'))
for directory in [producer,mapdir,HERE.parent/'replication',native/'tools/protocol_fixture',HERE.parent/'scenecatalog']:
 for extension in ['*.py','*.inc','*.json']:
  deps.extend(x for x in directory.rglob(extension) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
deps.extend([HERE/'tests/runtime_catalog_seed_fixture.c',producer/'test_snapshot.c',HERE.parent/'replication/tests/groups_oracle_harness.c',HERE/'coh_scenegraph.c'])
for manifest in [mapdir/'source-pins.json',HERE.parent/'replication/source-pins.json',HERE.parent/'replication/groups-source-pins.json']:
 deps.extend(ROOT/'upstream/ouroboros'/name for name in json.loads(manifest.read_text())['sha256_lf'])
deps.extend(ROOT/'upstream/ouroboros'/name for name in ['Common/group/group.h','MapServer/src/cmdparse/cmdserver.c'])
deps.extend([HERE/'CATALOG_SEED.md',HERE/'tests/source_bounds_checksum_fixture.c',HERE/'tests/test_source_bounds_checksum.c',ROOT/'upstream/ouroboros/Common/group/groupfilelib.c',HERE/'GROUPS_WITNESS.md',ROOT/'upstream/ouroboros/Common/group/groupfileload.c'])
deps=sorted(set(deps));initial={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps};modes={};binaries={};fixture_pins=[];checksum_modes={};checksum_function_pins={}
source_oracle=module(HERE.parent/'replication/groups_oracle.py')
with tempfile.TemporaryDirectory(prefix='coh-runtime-groups-') as directory:
 d=Path(directory);original,source=module(producer/'snapshot_oracle.py').prepare(ROOT,d)
 code=original.read_text();assert code.count('int main(')==1;code=code.replace('int main(', 'int snapshot_unused_main(');code+='\n'+(HERE/'tests/runtime_catalog_seed_fixture.c').read_text();original.write_text(code)
 run(['cc','-std=c99','-O0','-fno-strict-aliasing','-w','-I'+str(producer),'-I'+str(ROOT/'native-android/include'),original,'-lm','-lz','-o',d/'original']);original_checks=json.loads(run([d/'original',d]));fixtures=[]
 for n in range(4):
  cat=d/f'witness-{n}.cohcat';fixture=(cat,cat.with_suffix('.cohrts'),cat.with_suffix('.groups'),cat.with_suffix('.eligibility'),str(n));fixtures.append(fixture);fixture_pins.append({'case':n,'sha256':{p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture[:4]},'bytes':{p.suffix:p.stat().st_size for p in fixture[:4]}})
 boundsdir=d/'bounds';boundsdir.mkdir();bounds_original,_=module(producer/'snapshot_oracle.py').prepare(ROOT,boundsdir)
 bcode=bounds_original.read_text().replace('int main(', 'int snapshot_unused_main(')
 assert bcode.count('modified_on_disk,pre_alloc;GroupDef **defs;')==1;bcode=bcode.replace('modified_on_disk,pre_alloc;GroupDef **defs;','modified_on_disk,pre_alloc,idx;GroupDef **defs;')
 funcs=[]
 for path,names in [('Common/group/group.c',['groupInLib','groupIsPrivate','groupIsPublic']),('Common/group/groupfilelib.c',['objectLibraryWriteBoundsFileIfDifferent'])]:
  for name in names:
   body=source_oracle.extract(source_oracle.read_source(ROOT,path),name);funcs.append(body);checksum_function_pins[name]=hashlib.sha256(body.encode()).hexdigest()
 bfixture=(HERE/'tests/source_bounds_checksum_fixture.c').read_text().replace('/* ORIGINAL_FUNCTIONS_HERE */','\n'.join(funcs));bcode+='\n'+bfixture;bounds_original.write_text(bcode)
 run(['cc','-std=c99','-O0','-fno-strict-aliasing','-w','-I'+str(producer),'-I'+str(ROOT/'native-android/include'),bounds_original,'-lm','-lz','-o',boundsdir/'original']);checksum_original=json.loads(run([boundsdir/'original',d/'bounds-fixtures.bin']));checksum_fixture_sha256=hashlib.sha256((d/'bounds-fixtures.bin').read_bytes()).hexdigest()
 for mode,flags in [('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=d/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(HERE),*sources,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-Wl,--wrap=free','-lm','-lcrypto','-o',binary]);modes[mode]=[json.loads(run([binary,*fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))) for fixture in fixtures];binaries[mode]=hashlib.sha256(binary.read_bytes()).hexdigest()
  cbinary=d/(mode+'-checksum');csources=[x for x in sources if x.name!='test_catalog_seed.c']+[HERE/'tests/test_source_bounds_checksum.c'];run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(HERE),*csources,'-lm','-lcrypto','-o',cbinary]);checksum_modes[mode]=json.loads(run([cbinary,d/'bounds-fixtures.bin'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))

result={'passed':True,'checksum_modes':checksum_modes,'checksum_function_pins':checksum_function_pins,'checksum_original':checksum_original,'checksum_fixture_sha256':checksum_fixture_sha256,'binary_sha256':binaries,'fixture_pins':fixture_pins,'original_producer_sanitized':False,'file_idx_function_sha256_lf':{name:hashlib.sha256(source_oracle.extract(source_oracle.read_source(ROOT,path),name).encode()).hexdigest() for path,name in [('Common/group/group.c','autoGroupSelection'),('Common/group/groupfileload.c','addFileIdx')]},'file_idx_source_audit':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'upstream/ouroboros/Common/group/group.c',ROOT/'upstream/ouroboros/Common/group/groupfileload.c',ROOT/'upstream/ouroboros/Common/group/group.h']},'source_sha256':initial,'original_producer':source,'original_checks':original_checks,'modes':modes,'scope':'complete source protocol-wire seed projection plus original raw GroupBounds checksum oracle; no CLIENT-derived state or actual live GROUPS capture','source_generation_admitted':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
assert initial=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':{k:sum(x['checks'] for x in v) for k,v in modes.items()}}))
