#!/usr/bin/env python3
"""Focused current verifier regression; all generated observations are synthetic.

This exercises the changed private preparation path only. It neither starts an
original service nor admits source, actor, ACK, world, Android or process RSS.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import zlib
import check_source_snapshot_verifier as core

HARNESS=r'''
#define main streaming_verifier_main
#include "VERIFY_SOURCE"
#undef main
static size_t t_calls,t_live,t_fail,t_decodes,t_eager;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void *);
void *__wrap_malloc(size_t n){t_calls++;if(t_calls==t_fail)return NULL;void*p=__real_malloc(n);if(p)t_live++;return p;}
void *__wrap_calloc(size_t n,size_t z){t_calls++;if(t_calls==t_fail)return NULL;void*p=__real_calloc(n,z);if(p)t_live++;return p;}
void __wrap_free(void*p){if(p){if(!t_live)abort();t_live--;}__real_free(p);}
CohStatus __real_coh_scenegraph_definition_read(CohSgDefinition*,CohRepReader*,uint32_t,size_t,size_t*);
CohStatus __wrap_coh_scenegraph_definition_read(CohSgDefinition*d,CohRepReader*r,uint32_t f,size_t a,size_t*n){t_decodes++;return __real_coh_scenegraph_definition_read(d,r,f,a,n);}
CohStatus __real_coh_scenecatalog_load(CohSceneCatalog**,CohBytes,uint32_t,CohCatalogReport*);
CohStatus __wrap_coh_scenecatalog_load(CohSceneCatalog**c,CohBytes b,uint32_t g,CohCatalogReport*r){t_eager++;return __real_coh_scenecatalog_load(c,b,g,r);}
static int t_predicates(const char*directory){
 CohBytes input={0};CohCatalogReport report;CohSceneCatalog*eager=NULL;
 if(v_file(directory,"catalog.cohcat",COH_CATALOG_INPUT_MAX,V_RESERVE,&input)||coh_scenecatalog_load(&eager,input,7,&report))return 3;
 CohGroupsInspection good={0};good.new_world=1;good.files=report.files;good.footer_defs_crc=report.source_defs_crc;good.footer_refs_crc=report.source_refs_crc;good.footer_active_roots=report.source_active_roots;
 unsigned checks=0;
 for(unsigned flags=0;flags<32;flags++){
  CohGroupsInspection groups=good;if(flags&1)groups.new_world=0;if(flags&2)groups.files++;if(flags&4)groups.footer_defs_crc^=1;if(flags&8)groups.footer_refs_crc^=1;if(flags&16)groups.footer_active_roots++;
  CohStatus old=coh_scenecatalog_match(eager,&groups),current=v_catalog_match(&report,&groups);
  if(old!=current||current!=(flags?COH_STATE:COH_OK))return 3;checks++;
 }
 if(v_catalog_match(NULL,&good)!=COH_INVALID||v_catalog_match(&report,NULL)!=COH_INVALID)return 3;checks+=2;
 coh_scenecatalog_free(eager);v_drop(&input);if(t_live)return 3;
 printf("{\"passed\":true,\"predicate_checks\":%u,\"live_allocations\":%zu}\n",checks,t_live);return 0;
}
int main(int argc,char**argv){
 if(argc!=4)return 3;
 if(!strcmp(argv[2],"predicates"))return t_predicates(argv[1]);
 t_fail=(size_t)strtoul(argv[3],NULL,10);
 if(!strcmp(argv[2],"eager")){
  CohBytes input={0};CohCatalogReport report={0};CohSceneCatalog*catalog=NULL;
  CohStatus status=v_file(argv[1],"catalog.cohcat",COH_CATALOG_INPUT_MAX,V_RESERVE,&input);
  if(status==COH_OK)status=coh_scenecatalog_load(&catalog,input,7,&report);
  coh_scenecatalog_free(catalog);v_drop(&input);
  printf("{\"status\":%u,\"minimum_exceeds_eager_cap\":%s,\"live_allocations\":%zu}\n",status,report.minimum_owned_bytes>COH_CATALOG_MEMORY_MAX?"true":"false",t_live);return t_live?3:0;
 }
 int result=streaming_verifier_main(2,argv);
 fprintf(stderr,"{\"calls\":%zu,\"live\":%zu,\"decodes\":%zu,\"eager\":%zu}\n",t_calls,t_live,t_decodes,t_eager);
 return t_live?3:result;
}
'''
WRAPS=('malloc','calloc','free','coh_scenegraph_definition_read','coh_scenecatalog_load')


def need(value,reason):
 if not value:raise ValueError('COH_STREAMING_VERIFIER_'+reason)


def u32(n):return struct.pack('<I',n)
def checksum(raw):return int.from_bytes(u32(zlib.adler32(raw)),'big')


def fixture(directory,records,kind='tombstone',mismatch=None):
 directory.mkdir(mode=0o700)
 name=b'synthetic_file.txt\0';definition=b'synthetic_definition\0';parts=[]
 for slot in range(records):
  wire=u32(slot+1)+b'\0'
  if kind in ('active','invalid_body'):
   wire=u32(slot+1)+b'\1'+definition+u32(0)+u32(0)+b'\0'*5+u32(0)+b'\0'+bytes([2 if kind=='invalid_body' else 0])
  if kind=='tail' and slot+1==records:wire+=b'\0'
  parts.append(struct.pack('<4I',slot,len(wire)*8,len(wire),1)+wire)
 crc=checksum((definition[:-1] if kind in ('active','invalid_body') else b'NAMELESS')*records)
 refs=0
 cat=bytearray(b'COHCAT01'+struct.pack('<10I',1,48,0,7,1,records,crc,refs,0,0)+struct.pack('<5I',0,0,records,records,len(name))+name+b''.join(parts));struct.pack_into('<I',cat,16,len(cat))
 # Aligned compressed GROUPS with saved definitions omitted. A later ledger
 # would have to authenticate those omissions; stage3 is intentionally absent.
 new_world=0 if mismatch=='new_world' else 1
 packet=u32(6)+u32(0)+u32(0)+bytes([new_world])
 if new_world:packet+=b'\0'+u32(0)*3+b'\0\0'+u32(0)+b'\0\0\0'
 packet+=b'\0'+u32(2 if mismatch=='files' else 1)+b'\1'+name+u32(0)+b'\0'+u32(0)
 if mismatch=='files':packet+=b'\0'
 packet+=u32(0xffffffff)+u32(2 if mismatch=='files' else 1)+u32(1 if mismatch=='roots' else 0)+u32(crc^(1 if mismatch=='defs_crc' else 0))+u32(refs^(1 if mismatch=='refs_crc' else 0))
 meta=bytearray(192);meta[:8]=b'COHGPAK1';struct.pack_into('<6I',meta,8,1,192,7,len(packet)*8,1,1)
 owner=bytearray(192);owner[:8]=b'COHOWN01';struct.pack_into('<5I',owner,8,1,192,1,1,1);struct.pack_into('<I',owner,48,5)
 for file,raw in (('catalog.cohcat',cat),('packet.bin',packet),('packet-metadata.bin',meta),('owner.cohown',owner)):
  path=directory/file;path.write_bytes(raw);path.chmod(0o600)
 return directory


def qualify(output):
 owned=(core.HERE/'verify_source_snapshot.c',Path(__file__).resolve())
 pins={str(p.relative_to(core.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in owned}
 dependency_pins=core.source_pins(False);modes={}
 with tempfile.TemporaryDirectory(prefix='coh-streaming-verifier-') as tmp:
  root=Path(tmp);small=fixture(root/'small',3);large=fixture(root/'large',40000)
  active=fixture(root/'active',1,'active');bad=fixture(root/'bad-body',1,'invalid_body');tail=fixture(root/'tail',3,'tail')
  mismatches={key:fixture(root/key,3,mismatch=key) for key in ('new_world','files','defs_crc','refs_crc','roots')}
  harness=root/'streaming.c';harness.write_text(HARNESS.replace('VERIFY_SOURCE',str(core.HERE/'verify_source_snapshot.c')))
  for mode in ('release','asan','ubsan'):
   flags=list(core.FLAGS)
   if mode!='release':flags=[x for x in flags if x!='-O2']+['-O1','-g','-fsanitize='+('address' if mode=='asan' else 'undefined'),'-no-pie' if mode=='asan' else '-fno-sanitize-recover=all']
   binary=root/mode
   core.run(['cc',*flags,'-Wno-misleading-indentation','-I'+str(core.ROOT/'native-android/include'),harness,*[core.ROOT/'native-android'/s for s in core.SOURCES[1:]],*[f'-Wl,--wrap={name}' for name in WRAPS],'-lcrypto','-lz','-lm','-o',binary])
   def run(directory,kind='verify',fail=0):
    p=subprocess.run([str(binary),str(directory),kind,str(fail)],capture_output=True,timeout=30,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    need(p.returncode in (0,2),'NATIVE_TERMINAL');result=json.loads(p.stdout)
    if kind!='verify':need(p.returncode==0 and not p.stderr,'SPECIAL_TERMINAL');return result
    allocations=json.loads(p.stderr);need(allocations['live']==0 and allocations['eager']==0,'OWNER_RETIREMENT_AND_NO_EAGER')
    need(p.returncode==2 and result['passed'] is False and result['source_generation_admitted'] is False and result['world_authority'] is False,'DELIBERATE_POST_STAGE2_SCOPE');return result,allocations
   parity=run(small,'predicates');need(parity['predicate_checks']==34 and parity['live_allocations']==0,'PREDICATE_PARITY')
   eager=run(large,'eager');need(eager=={'status':4,'minimum_exceeds_eager_cap':True,'live_allocations':0},'ACTUAL_EAGER_LIMIT')
   cases=2
   for directory,records in ((small,3),(large,40000),(active,1)):
    result,allocations=run(directory);need(result['stage']==3 and result['status']==6 and allocations['decodes']==records,'COMPLETE_STREAMING_DECODE');cases+=1
   large_result,large_allocations=run(large);cases+=1
   for directory in mismatches.values():
    result,_=run(directory);need(result['stage']==2 and result['status']==7 and result['operation']=='GROUPS_MATCH','MATCH_REFUSAL');cases+=1
   for directory,records in ((bad,1),(tail,3)):
    result,allocations=run(directory);need(result['stage']==2 and result['operation']=='CATALOG_OWNER_CREATE' and allocations['decodes']==records,'FULL_BODY_REFUSAL');cases+=1
   # First eight allocations cover every stage1/source/owner/index allocation;
   # first/middle/final record samples cover decoder ownership without O(N^2)
   # replay of the synthetic 40,000-record corpus.
   failures=sorted(set(range(1,10))|{large_allocations['calls']//2,large_allocations['calls']})
   for fail in failures:
    result,_=run(large,fail=fail);need(result['stage']<=2 and result['status']==4,'ALLOCATION_REFUSAL');cases+=1
   # Actual existing span guard refuses over-cap input before any decode.
   original=(small/'catalog.cohcat').read_bytes()
   with (small/'catalog.cohcat').open('wb') as stream:stream.truncate(32*1024**2+1)
   result,allocations=run(small);need(result['stage']==2 and result['operation']=='CATALOG_INPUT' and result['status']==4 and allocations['decodes']==0,'EXISTING_INPUT_LIMIT');cases+=1
   (small/'catalog.cohcat').write_bytes(original)
   modes[mode]={'cases':cases,'predicate_checks':34,'complete_large_records_decoded':40000,'large_allocation_calls':large_allocations['calls'],'sampled_allocation_failures':failures,'actual_eager_minimum_limit_refused':True,'whole_body_and_tail_refusals':2,'match_mismatches':5,'final_live_allocations_each_case':0,'eager_calls_in_current_verifier_each_case':0,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
 core.verify_pins(dependency_pins)
 need(pins=={str(p.relative_to(core.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in owned},'OWN_SOURCE_CHANGED')
 proof={'schema':'coh-streaming-private-verifier-focused-v1','passed':True,'source_sha256':pins,'compiler_dependency_sha256':dependency_pins,'modes':modes,'fixture_source':'generated explicit synthetic records only','limits_changed':False,'old_full_suites_replayed':False,'original_service_executed':False,'source_generation_admitted':False,'world_authority':False,'process_rss_fit_established':False,'leak_sanitizer':False}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.output)
