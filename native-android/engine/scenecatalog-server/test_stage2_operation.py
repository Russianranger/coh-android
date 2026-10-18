#!/usr/bin/env python3
"""Focused stage-2 diagnostic qualification; the source-layout fixture is synthetic.

No original service, capture, source admission, world authority or old verifier
suite is run. Link-time refusals exercise the actual production verifier's first
failed operation. Raw fixture records and native output remain private.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from unittest import mock

import check_source_snapshot_verifier as core
import check_source_snapshot_verifier_status as adapter

HARNESS=r'''
#define main operation_verifier_main
#include "VERIFY_SOURCE"
#undef main
static const char *t_target;
static unsigned t_digests;
#define TARGET(name) (!strcmp(t_target,name))
unsigned char *__real_SHA256(const unsigned char *,size_t,unsigned char *);
unsigned char *__wrap_SHA256(const unsigned char *b,size_t n,unsigned char *out){t_digests++;if((TARGET("CATALOG_DIGEST")&&t_digests==1)||(TARGET("OWNER_DIGEST")&&t_digests==2)||(TARGET("METADATA_DIGEST")&&t_digests==3))return NULL;return __real_SHA256(b,n,out);}
CohStatus __real_coh_catalog_owner_create(const CohCatalogOwner *,CohBytes,const CohCatalogBinding *,const CohCatalogOwnerBudget *,const CohCatalogDigest *,CohCatalogOwner **,CohCatalogOwnerReport *);
CohStatus __wrap_coh_catalog_owner_create(const CohCatalogOwner *old,CohBytes b,const CohCatalogBinding *binding,const CohCatalogOwnerBudget *budget,const CohCatalogDigest *digest,CohCatalogOwner **o,CohCatalogOwnerReport *r){if(TARGET("CATALOG_OWNER_CREATE"))return COH_LIMIT;CohStatus s=__real_coh_catalog_owner_create(old,b,binding,budget,digest,o,r);if(s==COH_OK&&TARGET("GROUPS_MATCH"))r->walk.catalog.files++;if(s==COH_OK&&TARGET("CATALOG_OWNER_RESERVATION"))r->peak_aggregate_bytes=V_LIMIT+1u;return s;}
CohStatus __real_coh_catalog_owner_bytes(const CohCatalogOwner *,CohBytes *);
CohStatus __wrap_coh_catalog_owner_bytes(const CohCatalogOwner *o,CohBytes *b){if(TARGET("CATALOG_OWNER_VIEW"))return COH_STATE;return __real_coh_catalog_owner_bytes(o,b);}
int main(int argc,char **argv){if(argc!=3)return 3;t_target=argv[2];return operation_verifier_main(2,argv);}
'''
WRAPS=('SHA256','coh_catalog_owner_create','coh_catalog_owner_bytes')
BASE_FIELDS={'schema','passed','status','stage','source_generation_admitted','world_authority'}
PRIVATE='CONTROLLED_PRIVATE_PACKET_RECORD_NAME_729c'

def need(value,reason):
 if not value:raise ValueError('COH_STAGE2_DIAGNOSTIC_'+reason)

def projection_checks():
 checks=0
 def result(operation='ABSENT',stage=2):
  r={'schema':'coh-source-snapshot-native-result-v1','passed':False,'status':4,'stage':stage,'source_generation_admitted':False,'world_authority':False}
  if operation!='ABSENT':r['operation']=operation
  return r
 def execute(r,stderr=b'',code=2):
  p=subprocess.CompletedProcess([],code,json.dumps(r).encode(),stderr)
  with mock.patch.object(adapter.subprocess,'run',return_value=p) as child:
   try:adapter.run_native(Path('/controlled/binary'),Path('/controlled/source'))
   except adapter.SnapshotFailure as e:public=adapter.public_failure(e)
   else:raise ValueError('COH_STAGE2_DIAGNOSTIC_MISSING_REFUSAL')
  need(child.call_count==1,'ONE_CHILD');need(PRIVATE not in json.dumps(public),'PRIVATE_PROJECTION');return public
 for operation in sorted(adapter.STAGE2_OPERATIONS):
  r=execute(result(operation));need(r.get('native_operation')==operation and r['native_stage']==2 and r['native_status']==4,'FIXED_OPERATION');checks+=1
 r=execute(result());need('native_operation' not in r and r['native_stage']==2,'HISTORICAL_FAILURE');checks+=1
 for bad in (PRIVATE,'',None,True,1,[],{},'CATALOG_INPUT\n'+PRIVATE):
  r=execute(result(bad));need(r['native_stage'] is None and 'native_operation' not in r,'INVALID_OPERATION');checks+=1
 for stage in (0,1,3,7):
  r=execute(result('EAGER_LOAD',stage));need(r['native_stage'] is None and 'native_operation' not in r,'WRONG_STAGE');checks+=1
 for extra in ({'path':PRIVATE},{'bytes':123},{'record':PRIVATE}):
  r=result('EAGER_LOAD');r.update(extra);r=execute(r);need(r['native_stage'] is None and 'native_operation' not in r,'EXTRA_FIELD');checks+=1
 for stderr,code in ((PRIVATE.encode(),2),(b'',1),(b'',-11)):
  r=execute(result('EAGER_LOAD'),stderr,code);need(r['native_stage'] is None and 'native_operation' not in r,'INVALID_CHILD');checks+=1
 for error in (adapter.SnapshotFailure('BUILD',2,4,'EAGER_LOAD'),adapter.SnapshotFailure('NATIVE_EXECUTION',3,4,'EAGER_LOAD'),adapter.SnapshotFailure('NATIVE_EXECUTION',2,4,PRIVATE)):
  need('native_operation' not in adapter.public_failure(error),'PUBLIC_STRICT_SCOPE');checks+=1
 return checks

def qualify(fixture,output):
 root=core.ROOT;source=core.HERE/'verify_source_snapshot.c';before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,core.HERE/'check_source_snapshot_verifier_status.py',Path(__file__).resolve())}
 checks=projection_checks();modes={}
 with tempfile.TemporaryDirectory(prefix='coh-stage2-operation-') as tmp:
  private=Path(tmp);data=private/'synthetic';core.load_inspector(core.source_pins(False)).inspect(fixture,data)
  raw=bytearray((data/'owner.cohown').read_bytes());struct.pack_into('<I',raw,48,5);(data/'owner.cohown').write_bytes(raw)
  catalog=(data/'catalog.cohcat').read_bytes();harness=private/'operation.c';harness.write_text(HARNESS.replace('VERIFY_SOURCE',str(source)))
  def run(binary,target,expected,status):
   p=subprocess.run([str(binary),str(data),target],capture_output=True,timeout=30,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
   need(p.returncode==2 and not p.stderr,'NATIVE_TERMINAL');r=json.loads(p.stdout);need(r['passed'] is False and r['source_generation_admitted'] is False and r['world_authority'] is False,'NATIVE_SCOPE')
   if expected is None:need(set(r)==BASE_FIELDS and r['stage']==4,'UNCHANGED_POST_STAGE2_REFUSAL')
   else:need(set(r)==BASE_FIELDS|{'operation'} and r['stage']==2 and r['status']==status and r['operation']==expected,'ACTUAL_OPERATION')
  for mode in ('release','asan','ubsan'):
   flags=list(core.FLAGS)
   if mode!='release':flags=[x for x in flags if x!='-O2']+['-O1','-g','-fsanitize='+('address' if mode=='asan' else 'undefined'),'-no-pie' if mode=='asan' else '-fno-sanitize-recover=all']
   binary=private/mode
   core.run(['cc',*flags,'-I'+str(root/'native-android/include'),harness,*[root/'native-android'/s for s in core.SOURCES[1:]],*[f'-Wl,--wrap={name}' for name in WRAPS],'-lcrypto','-lz','-lm','-o',binary])
   run(binary,'NONE',None,7);cases=1
   for target,status in (('GROUPS_MATCH',7),('CATALOG_DIGEST',6),('OWNER_DIGEST',6),('METADATA_DIGEST',6),('CATALOG_OWNER_CREATE',4),('CATALOG_OWNER_RESERVATION',4),('CATALOG_OWNER_VIEW',7)):
    run(binary,target,target,status);cases+=1
   (data/'catalog.cohcat').unlink();run(binary,'NONE','CATALOG_INPUT',6);cases+=1;(data/'catalog.cohcat').write_bytes(catalog)
   for at,value,target,status in ((20,0,'CATALOG_HEADER',7),(16,0,'CATALOG_PREFLIGHT',1)):
    raw=bytearray(catalog);struct.pack_into('<I',raw,at,value);(data/'catalog.cohcat').write_bytes(raw);run(binary,'NONE',target,status);cases+=1;(data/'catalog.cohcat').write_bytes(catalog)
   modes[mode]={'cases':cases,'baseline_passed_stage2_then_refused_synthetic_ledger':True,'forced_stage2_refusals':cases-1,'original_service_executed':False}
 # Historical eager labels remain accepted by the adapter for retained fixed
 # receipts, but the current verifier no longer executes either eager operation.
 need(before=={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in before},'SOURCE_CHANGED')
 proof={'schema':'coh-stage2-operation-focused-v1','passed':True,'source_sha256':before,'projection_checks':checks,'modes':modes,'stage2_operation_names':sorted(adapter.STAGE2_OPERATIONS),'historical_eager_operations_not_executed':True,'fixture':{'sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'synthetic_source_layout_only':True},'old_verifier_or_adapter_suites_reexecuted':False,'original_capture_replayed':False,'source_generation_admitted':False,'world_authority':False,'limits_or_authority_predicates_changed':False}
 output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'projection_checks':checks,'native_cases_per_mode':11,'modes':list(modes)}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();qualify(a.fixture,a.output)
