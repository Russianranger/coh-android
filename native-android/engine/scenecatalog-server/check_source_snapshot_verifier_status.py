#!/usr/bin/env python3
"""Fixed public failure status around the byte-exact original private verifier.

The original checker owns every association and successful private receipt.
Only its exact native child call is intercepted to preserve a bounded refusal
stage/status. This adapter grants no source-generation or world authority.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
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
CORE_RELATIVE='native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py'
WRAPPER_RELATIVE='native-android/engine/scenecatalog-server/check_source_snapshot_verifier_status.py'
CORE_SHA256='6285a25fb727c86d6d2b9cd1eeacc3c1f398058f4dceb4821122a30a97600d6d'
SOURCE_LIMIT=1024*1024
FAILURE_PHASES=frozenset(('INPUTS','BUILD','EXTRACTION','PACKET_IDENTITY','NATIVE_EXECUTION','NATIVE_RESULT','FINAL_IDENTITIES','RECEIPT','UNKNOWN'))

STAGE2_OPERATIONS=frozenset(('CATALOG_INPUT','CATALOG_HEADER','CATALOG_PREFLIGHT','EAGER_RESERVATION','EAGER_LOAD','GROUPS_MATCH','CATALOG_DIGEST','OWNER_DIGEST','METADATA_DIGEST','CATALOG_OWNER_CREATE','CATALOG_OWNER_RESERVATION','CATALOG_OWNER_VIEW'))

class SnapshotFailure(Exception):
 def __init__(self,phase,native_stage=None,native_status=None,native_operation=None):
  super().__init__('COH_SOURCE_SNAPSHOT_VERIFICATION_REFUSED')
  self.phase=phase;self.native_stage=native_stage;self.native_status=native_status;self.native_operation=native_operation

@contextmanager
def failure_scope(phase):
 try:yield
 except SnapshotFailure:raise
 except Exception:raise SnapshotFailure(phase) from None

def public_failure(error):
 phase='UNKNOWN';stage=None;status=None
 if type(error) is SnapshotFailure:
  fields=vars(error);candidate=fields.get('phase');candidate_stage=fields.get('native_stage');candidate_status=fields.get('native_status')
  if type(candidate) is str and candidate in FAILURE_PHASES:phase=candidate
  if phase=='NATIVE_EXECUTION' and type(candidate_stage) is int and 0<=candidate_stage<=7 and type(candidate_status) is int and 1<=candidate_status<=7:
   stage=candidate_stage;status=candidate_status
 result={'schema':SCHEMA,'passed':False,'failure':'verification_refused','phase':phase,'native_stage':stage,'native_status':status,'source_generation_admitted':False,'world_authority':False}
 if type(error) is SnapshotFailure and stage==2:
  operation=vars(error).get('native_operation')
  if type(operation) is str and operation in STAGE2_OPERATIONS:result['native_operation']=operation
 return result

def unique_object(pairs):
 result={}
 for key,value in pairs:
  require(key not in result,'DUPLICATE_NATIVE_RESULT');result[key]=value
 return result

def run_native(binary,extracted):
 # Only this fixed failure projection may leave the private verifier boundary.
 # Successful output (including all counts) remains private and is validated by
 # the unchanged association checks below. No child stderr/exception is exposed.
 with failure_scope('NATIVE_EXECUTION'):
  p=subprocess.run(list(map(str,(binary,extracted))),cwd=ROOT,capture_output=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
  require(len(p.stdout)+len(p.stderr)<=1024**2,'CHILD_OUTPUT_LIMIT')
  if p.returncode:
   stage=None;status=None;operation=None
   try:
    result=json.loads(p.stdout,object_pairs_hook=unique_object)
    original_fields={'schema','passed','status','stage','source_generation_admitted','world_authority'}
    require(p.returncode==2 and not p.stderr and type(result) is dict and set(result) in (original_fields,original_fields|{'operation'}),'FIXED_NATIVE_FAILURE')
    require(result['schema']=='coh-source-snapshot-native-result-v1' and result['passed'] is False and result['source_generation_admitted'] is False and result['world_authority'] is False,'FIXED_NATIVE_FAILURE_SCOPE')
    require(type(result['stage']) is int and 0<=result['stage']<=7 and type(result['status']) is int and 1<=result['status']<=7,'FIXED_NATIVE_FAILURE_ENUM')
    if 'operation' in result:
     require(result['stage']==2 and type(result['operation']) is str and result['operation'] in STAGE2_OPERATIONS,'FIXED_NATIVE_OPERATION')
     operation=result['operation']
    stage=result['stage'];status=result['status']
   except Exception:pass
   raise SnapshotFailure('NATIVE_EXECUTION',stage,status,operation)
  return p.stdout

def require(value,code):
 if not value:raise ValueError('COH_SOURCE_SNAPSHOT_'+code)

def source_bytes(value):
 """Read one bounded regular source without following a replacement link."""
 path=Path(os.path.abspath(value))
 require(not any(p.is_symlink() for p in (path,*path.parents)),'SOURCE_SYMLINK')
 def key(info):return (info.st_dev,info.st_ino,info.st_uid,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
 before=path.lstat()
 require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=SOURCE_LIMIT,'SOURCE_FILE')
 with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
  opened=os.fstat(stream.fileno());require(key(opened)==key(before),'SOURCE_REPLACED')
  raw=stream.read(SOURCE_LIMIT+1)
  require(len(raw)==before.st_size and key(os.fstat(stream.fileno()))==key(before),'SOURCE_CHANGED')
 require(key(path.lstat())==key(before),'SOURCE_PATH_CHANGED')
 return raw

def source_binding():
 """Admit this exact adapter and original core against current Git bytes."""
 require(Path(__file__).resolve()==ROOT/WRAPPER_RELATIVE,'OWN_CHECKOUT')
 revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,timeout=30)
 require(revision.returncode==0 and not revision.stderr and len(revision.stdout)==41,'SOURCE_REVISION')
 head=revision.stdout.decode('ascii').strip()
 require(len(head)==40 and all(c in '0123456789abcdef' for c in head),'SOURCE_REVISION')
 sources={name:source_bytes(ROOT/name) for name in (WRAPPER_RELATIVE,CORE_RELATIVE)}
 require(hashlib.sha256(sources[CORE_RELATIVE]).hexdigest()==CORE_SHA256,'ORIGINAL_CORE_PIN')
 for name,raw in sources.items():
  committed=subprocess.run(['git','show',head+':'+name],cwd=ROOT,capture_output=True,timeout=30)
  require(committed.returncode==0 and not committed.stderr and len(committed.stdout)<=SOURCE_LIMIT and committed.stdout==raw,'CURRENT_COMMITTED_SOURCE')
 require(source_bytes(ROOT/WRAPPER_RELATIVE)==sources[WRAPPER_RELATIVE] and source_bytes(ROOT/CORE_RELATIVE)==sources[CORE_RELATIVE],'SOURCE_BINDING_CHANGED')
 return head,sources

def load_core(raw):
 require(type(raw) is bytes and hashlib.sha256(raw).hexdigest()==CORE_SHA256,'ORIGINAL_CORE_PIN')
 path=ROOT/CORE_RELATIVE
 module=types.ModuleType('coh_byte_exact_private_source_snapshot_core')
 module.__file__=str(path)
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module

def run_inspection(capture,native_packet,work,output):
 binding=source_binding()
 core=load_core(binding[1][CORE_RELATIVE])
 original_run=core.run
 directory=Path(os.path.abspath(work))
 binary=directory/'build/verify-source-snapshot';extracted=directory/'source'
 expected=(str(binary),str(extracted));native_calls=0
 def proxy(command,timeout=180):
  nonlocal native_calls
  # The source-admitted original inspect supplies a two-Path list here. Other
  # commands retain the exact original object and timeout on delegation.
  if type(command) in (list,tuple) and len(command)==2 and all(type(item) in (str,type(binary)) for item in command) and tuple(map(str,command))==expected:
   with failure_scope('NATIVE_EXECUTION'):
    require(type(timeout) is int and timeout==180,'NATIVE_TIMEOUT')
    require(native_calls==0,'REPEATED_NATIVE_CALL');native_calls+=1
    return run_native(binary,extracted)
  return original_run(command,timeout)
 core.run=proxy
 try:
  result=core.inspect(capture,native_packet,work,output)
 finally:
  core.run=original_run
  require(source_binding()==binding,'SOURCE_CHANGED_DURING_INSPECTION')
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--native-packet',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:run_inspection(a.capture,a.native_packet,a.work,a.output)
 except Exception as error:print(json.dumps(public_failure(error)));return 2
 print(json.dumps({'schema':SCHEMA,'passed':True,'private_receipt_written':True,'source_generation_admitted':False,'world_authority':False}));return 0
if __name__=='__main__':sys.exit(main())
