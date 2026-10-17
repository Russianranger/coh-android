#!/usr/bin/env python3
"""Private bounded native associations; external live provenance is not granted.

Builds current committed native sources, privately extracts ONE commit-complete
envelope, compares its logical packet to the independently received packet, and
runs the existing native catalog/runtime/resource/bounds/GROUPS validators.
All observations, hashes and numeric counts in this receipt remain PRIVATE.
Offline fixtures exercise the mechanism only and cannot mint any live token.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SCHEMA='coh-source-snapshot-native-verification-v1'
NAMES=('owner.cohown','catalog.cohcat','runtime.cohrts','resources.cohres','eligibility.bin','public-bounds.cohrbw','packet-metadata.bin','packet.bin')
CHECKS=('catalog_groups_match','runtime_catalog_associations','resource_catalog_associations','raw_bounds_catalog_associations','eligibility_groups_associations')
COUNTS=('files','slots','definitions','children','root_slots','active_roots','external_owners','resource_rows','model_rows','public_bounds_rows','emitted_definitions','emitted_roots','definition_scalars_compared','named_peak_reservation_bytes','named_aggregate_limit_bytes')
SOURCES=('engine/scenecatalog-server/verify_source_snapshot.c','engine/scenecatalog/coh_catalog_owner.c','engine/scenecatalog/coh_catalog_snapshot.c','engine/scenecatalog/coh_scenecatalog.c','engine/scenecatalog/coh_resource_join.c','engine/scenecatalog/coh_resource_index.c','engine/scenecatalog/coh_resource_geo_source.c','engine/scenegraph/runtime_snapshot.c','engine/scenegraph/tests/runtime_matrix_bridge.c','engine/scenegraph/coh_public_bounds.c','engine/replication/coh_replication.c','engine/assets/coh_asset_loader.c','engine/assets/coh_asset_geo.c','src/coh_assets.c','src/coh_dds.c')
FLAGS=('-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-fstack-usage')
def require(value,code):
 if not value:raise ValueError('COH_SOURCE_SNAPSHOT_'+code)
def path(value):
 p=Path(os.path.abspath(value));require(not any(x.is_symlink() for x in (p,*p.parents)),'SYMLINK');return p
def identity(value,maximum=160*1024**2,private=True):
 p=path(value)
 with os.fdopen(os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
  before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=maximum,'FILE')
  if private:require(not before.st_mode&0o077,'PRIVATE_FILE')
  h=hashlib.sha256()
  while block:=stream.read(65536):h.update(block)
  after=os.fstat(stream.fileno());require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'CHANGED_FILE')
 return {'bytes':before.st_size,'sha256':h.hexdigest()}
def run(command,timeout=180):
 p=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=timeout,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 require(len(p.stdout)+len(p.stderr)<=1024**2,'CHILD_OUTPUT_LIMIT')
 if p.returncode:raise ValueError('COH_SOURCE_SNAPSHOT_CHILD_REFUSED')
 return p.stdout
def source_files():
 # Compiler-derived transitive project dependencies include the two exact .c
 # grammar bridges, all headers and recursively included implementation bytes.
 command=['cc',*FLAGS,'-I'+str(ROOT/'native-android/include'),'-MM',*[ROOT/'native-android'/s for s in SOURCES]]
 raw=run(command).decode();found={HERE/'check_source_snapshot_verifier.py',HERE/'inspect_groups_capture.py'}
 for line in raw.replace('\\\n',' ').splitlines():
  require(':' in line,'DEPENDENCY_FORMAT')
  for name in line.split(':',1)[1].split():
   p=Path(name).resolve();require(p.is_relative_to(ROOT),'EXTERNAL_PROJECT_SOURCE');found.add(p)
 return tuple(sorted(found))
def source_pins(require_committed=True):
 files=source_files();pins={str(p.relative_to(ROOT)):identity(p,8*1024**2,False)['sha256'] for p in files}
 if require_committed:
  for name,digest in pins.items():
   p=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True,timeout=30)
   require(p.returncode==0 and hashlib.sha256(p.stdout).hexdigest()==digest,'CURRENT_COMMITTED_SOURCE')
 return pins
def verify_pins(pins):
 require(all(identity(ROOT/name,8*1024**2,False)['sha256']==digest for name,digest in pins.items()),'SOURCE_CHANGED')
def build(directory,require_committed=True,mode='release'):
 directory=path(directory);directory.mkdir(mode=0o700);pins=source_pins(require_committed)
 flags=list(FLAGS)
 if mode=='asan':flags=[x for x in flags if x!='-O2']+['-O1','-g','-fsanitize=address','-no-pie']
 elif mode=='ubsan':flags=[x for x in flags if x!='-O2']+['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all']
 else:require(mode=='release','BUILD_MODE')
 binary=directory/'verify-source-snapshot'
 command=['cc',*flags,'-I'+str(ROOT/'native-android/include'),*[ROOT/'native-android'/s for s in SOURCES],'-lcrypto','-lz','-lm','-o',binary]
 run(command);os.chmod(binary,0o700);verify_pins(pins)
 # The verifier owns a512KiB explicit control/digest/stack reserve. Existing
 # native validators additionally charge their own bounded traversal reserves.
 frames={}
 for file in directory.glob('*.su'):
  for line in file.read_text().splitlines():
   location,size,kind=line.split('\t');require('unbounded' not in kind,'UNBOUNDED_STACK');frames[file.name+':'+location.rsplit(':',1)[-1]]=int(size)
 require(frames and max(frames.values())<512*1024,'STACK_RESERVE')
 receipt={'compiler':run(['cc','--version']).decode().splitlines()[0],'flags':flags,'libraries':['crypto','z','m'],'source_sha256':pins,'current_committed_sources_verified':require_committed,'mode':mode,'maximum_static_frame_bytes':max(frames.values()),'control_digest_stack_reserve_bytes':512*1024}
 return binary,receipt
def load_inspector(pins):
 verify_pins(pins);p=HERE/'inspect_groups_capture.py';m=types.ModuleType('coh_private_source_snapshot_inspector');m.__file__=str(p)
 exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);verify_pins(pins);return m
def inspect(capture,native_packet,work,output):
 capture=path(capture);native_packet=path(native_packet);work=path(work);output=path(output)
 require(not work.exists() and not output.exists() and output.parent==work,'NEW_PRIVATE_OUTPUT')
 before_capture=identity(capture);before_native=identity(native_packet,16*1024**2)
 work.mkdir(mode=0o700)
 binary,build_receipt=build(work/'build');pins=build_receipt['source_sha256'];executable=identity(binary,16*1024**2)
 extracted=work/'source';envelope=load_inspector(pins).inspect(capture,extracted)
 inputs={name:identity(extracted/name) for name in NAMES};inputs['native/groups.bin']=before_native
 require(inputs['packet.bin']==before_native,'NATIVE_PACKET_IDENTITY')
 require(envelope['envelope']==before_capture and all(inputs[name]=={k:envelope['files'][name][k] for k in ('bytes','sha256')} for name in NAMES),'EXTRACTION_IDENTITY')
 result=json.loads(run([binary,extracted]))
 require(result.get('schema')=='coh-source-snapshot-native-result-v1' and result.get('passed') is True and type(result.get('status')) is int and result['status']==0 and result.get('stage')==7,'NATIVE_RESULT')
 require(result.get('source_generation_admitted') is False and result.get('world_authority') is False and result.get('checks')==dict.fromkeys(CHECKS,True),'NATIVE_SCOPE')
 counts=result.get('counts');require(type(counts) is dict and set(counts)==set(COUNTS) and all(type(v) is int and 0<=v<=0xffffffff for v in counts.values()),'COUNTS')
 require(counts['named_aggregate_limit_bytes']==96*1024**2 and counts['named_peak_reservation_bytes']<=counts['named_aggregate_limit_bytes'],'BUDGET')
 require(identity(capture)==before_capture and identity(native_packet,16*1024**2)==before_native and identity(binary,16*1024**2)==executable and all(identity(extracted/name)==inputs[name] for name in NAMES),'INPUT_CHANGED');verify_pins(pins)
 receipt={'schema':SCHEMA,'passed':True,'capture':before_capture,'inputs':inputs,'source_sha256':pins,'source_revision':run(['git','rev-parse','HEAD']).decode().strip(),'executable':executable,'build':build_receipt,'checks':result['checks'],'counts':counts,'exact_native_packet_bytes_verified':True,'private_receipt':True,'source_provenance_verified':False,'source_run_identity_verified':False,'source_generation_admitted':False,'cache_equivalence_verified':False,'client_materials_admitted':False,'actor_identity_verified':False,'world_authority':False,'current_after_quiet_release':False}
 with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as stream:json.dump(receipt,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 return receipt
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--native-packet',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:inspect(a.capture,a.native_packet,a.work,a.output)
 except Exception:print(json.dumps({'schema':SCHEMA,'passed':False,'failure':'verification_refused','source_generation_admitted':False,'world_authority':False}));return 2
 print(json.dumps({'schema':SCHEMA,'passed':True,'private_receipt_written':True,'source_generation_admitted':False,'world_authority':False}));return 0
if __name__=='__main__':sys.exit(main())
