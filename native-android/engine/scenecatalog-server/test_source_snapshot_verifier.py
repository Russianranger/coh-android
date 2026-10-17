#!/usr/bin/env python3
"""NEW verifier tests over an explicit synthetic source-layout envelope.

--fixture is the retained original-supplier HOST fixture, never live evidence.
Its deliberately substituted resource/owner stubs are replaced below with
explicit synthetic observations solely to exercise native association refusal.
No live admission/token API is imported or called by this qualification.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess,sys,tempfile
import check_source_snapshot_verifier as v

FIXTURE_C=r'''
#define main retained_verifier_main
#include "VERIFY_SOURCE"
#undef main
static FILE*f_out;static uint32_t f_rows,f_models,f_generation;static size_t f_bytes;
static void f_put(uint8_t*p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static CohStatus f_slot(void*context,const CohCatalogSlotView*s){
 (void)context;if(!s->allocated||!s->definition->in_use)return COH_OK;
 const CohSgDefinition*d=s->definition;const char*geo="synthetic/never-admitted.geo";uint32_t n=(uint32_t)strlen(d->name)+1,m=d->geometry[0]?(uint32_t)strlen(d->geometry)+1:0,g=m?(uint32_t)strlen(geo)+1:0,size=192+n+m+g;
 uint8_t p[192]={0};memcpy(p,"COHRES01",8);f_put(p+8,1);f_put(p+12,192);f_put(p+16,size);f_put(p+20,f_generation);f_put(p+24,1);f_put(p+28,d->file);f_put(p+32,d->id);f_put(p+36,d->id);f_put(p+40,!!m);f_put(p+44,1);f_put(p+48,n);f_put(p+52,m);f_put(p+56,g);f_put(p+68,m?0:UINT32_MAX);
 if(fwrite(p,1,192,f_out)!=192||fwrite(d->name,1,n,f_out)!=n||(m&&fwrite(d->geometry,1,m,f_out)!=m)||(g&&fwrite(geo,1,g,f_out)!=g))return COH_IO;f_rows++;f_models+=!!m;f_bytes+=size;return COH_OK;
}
static int f_finish_once(CohBytes cat,CohBytes eligibility,CohBytes owner,CohBytes meta){
 CohCatalogBinding binding_={0};binding_.owner_generation=1;binding_.catalog_generation=f_generation;binding_.asset_generation=f_generation;v_digest(NULL,cat,binding_.catalog_sha256);v_digest(NULL,owner,binding_.source_sha256);v_digest(NULL,meta,binding_.inventory_sha256);CohCatalogDigest digest_={NULL,v_digest};CohCatalogOwnerBudget budget_={32u<<20,32u<<20,96u<<20,V_RESERVE};CohCatalogOwnerReport report_;CohCatalogOwner*catalog_=NULL;
 if(coh_catalog_owner_create(NULL,cat,&binding_,&budget_,&digest_,&catalog_,&report_))return 0;
 VContext context_={0};context_.catalog=catalog_;context_.eligibility=eligibility;context_.visit_files=1;context_.expected_file=0;CohCatalogFileView file_;int result=0;
 if(coh_catalog_owner_file(catalog_,0,&file_)||!file_.slots)goto done;
 for(uint32_t i=1;i<eligibility.size/64u;i++)if(v_word(v_record(&context_,i),0)==2&&!v_word(v_record(&context_,i),1)){context_.file_at[0]=i;break;}
 if(!context_.file_at[0])goto done;
 context_.expected_slot=file_.slots-1u;uint8_t*p=(uint8_t*)eligibility.data+(context_.file_at[0]+file_.slots)*64u+32u;uint32_t old=v_u32(p);f_put(p,0);
 result=v_finish_file(&context_)==COH_OK&&context_.expected_slot==file_.slots&&v_finish_file(&context_)==COH_OK&&context_.expected_slot==file_.slots;f_put(p,old);
done:coh_catalog_owner_release(catalog_);return result;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;CohBytes cat={0},owner={0},meta={0},elig={0};if(v_file(argv[1],"catalog.cohcat",32u<<20,V_RESERVE,&cat)||v_file(argv[1],"owner.cohown",192,V_RESERVE,&owner)||v_file(argv[1],"packet-metadata.bin",192,V_RESERVE,&meta)||v_file(argv[1],"eligibility.bin",V_ELIGIBILITY_MAX,V_RESERVE,&elig))return 2;
 char path[4096];snprintf(path,sizeof(path),"%s/resources.cohres",argv[1]);f_out=fopen(path,"wb");if(!f_out)return 2;f_generation=v_u32(cat.data+20);CohCatalogWalkBudget budget={32u<<20,96u<<20,V_RESERVE};CohCatalogVisitor visitor={NULL,NULL,f_slot};CohCatalogWalkReport report;
 if(coh_scenecatalog_walk(cat,f_generation,&budget,&visitor,&report)||fclose(f_out)||!f_finish_once(cat,elig,owner,meta))return 2;
 f_put((uint8_t*)owner.data+48,5);for(unsigned i=0;i<3;i++)f_put((uint8_t*)owner.data+(30u+i)*4u,v_word(elig,4u+i));
 f_put((uint8_t*)meta.data+27u*4u,f_rows);f_put((uint8_t*)meta.data+28u*4u,f_models);f_put((uint8_t*)meta.data+29u*4u,f_rows-f_models);f_put((uint8_t*)meta.data+32u*4u,(uint32_t)f_bytes);
 const char*names[]={"owner.cohown","packet-metadata.bin"};CohBytes values[]={owner,meta};for(unsigned i=0;i<2;i++){snprintf(path,sizeof(path),"%s/%s",argv[1],names[i]);FILE*f=fopen(path,"wb");if(!f||fwrite(values[i].data,1,values[i].size,f)!=values[i].size||fclose(f))return 2;}
 v_drop(&elig);v_drop(&meta);v_drop(&owner);v_drop(&cat);return 0;
}
'''
ALLOCATION_C=r'''
#define main retained_verifier_main
#include "VERIFY_SOURCE"
#undef main
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
static size_t t_calls,t_live,t_fail;
void*__wrap_malloc(size_t n){t_calls++;if(t_calls==t_fail)return NULL;void*p=__real_malloc(n);if(p)t_live++;return p;}
void*__wrap_calloc(size_t n,size_t size){t_calls++;if(t_calls==t_fail)return NULL;void*p=__real_calloc(n,size);if(p)t_live++;return p;}
void __wrap_free(void*p){if(p){if(!t_live)abort();t_live--;}__real_free(p);}
int main(int argc,char**argv){if(argc!=3)return 3;t_fail=(size_t)strtoul(argv[2],NULL,10);int result=retained_verifier_main(2,argv);fprintf(stderr,"{\"native_allocation_calls\":%zu,\"native_live_allocations\":%zu}\n",t_calls,t_live);if(t_live)return 3;return result;}
'''
def write(path,raw):path.write_bytes(raw);path.chmod(0o600)
def execute(binary,directory,ok):
 p=subprocess.run([str(binary),str(directory)],capture_output=True,text=True,timeout=30,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 if p.returncode not in (0,2):raise AssertionError('native crashed: '+p.stderr)
 r=json.loads(p.stdout);assert (p.returncode==0)==ok and r['passed']==ok and r['source_generation_admitted'] is False and r['world_authority'] is False,(r,p.stderr)
 assert not p.stderr,p.stderr
 return r
def envelope(directory):
 # Synthetic envelope uses the exact original framing, with explicit replacement
 # test observations. It remains synthetic even when the native result passes.
 observation=struct.unpack_from('<I',(directory/'catalog.cohcat').read_bytes(),20)[0];thread=17
 head=bytearray(64);head[:8]=b'COHGTX01';struct.pack_into('<4I',head,8,1,64,observation,thread);parts=[bytes(head)];sizes={};chunks={};ordinal=0
 order=(1,2,3,4,6,5,7,8)
 names={1:'owner.cohown',2:'catalog.cohcat',3:'runtime.cohrts',4:'resources.cohres',5:'eligibility.bin',6:'public-bounds.cohrbw',7:'packet-metadata.bin',8:'packet.bin'}
 for kind in order:
  raw=(directory/names[kind]).read_bytes();sizes[kind]=len(raw);chunks[kind]=1;parts.extend((struct.pack('<4I',kind,observation,len(raw),ordinal),raw));ordinal+=1
 footer=bytearray(128);footer[:8]=b'COHGEND1';struct.pack_into('<6I',footer,8,1,128,observation,sum(map(len,parts))+144,ordinal+1,thread);struct.pack_into('<8I',footer,32,*(sizes[k] for k in range(1,9)));struct.pack_into('<8I',footer,64,*(chunks[k] for k in range(1,9)));parts.extend((struct.pack('<4I',9,observation,128,ordinal),bytes(footer)));return b''.join(parts)
def qualify(fixture,output):
 v.require(__debug__,'ASSERTIONS_REQUIRED')
 checks=0;modes={};allocation_modes={}
 qualification_revision=v.run(['git','rev-parse','HEAD']).decode().strip()
 qualification_pins=v.source_pins(True);self_name=str(Path(__file__).resolve().relative_to(v.ROOT))
 qualification_pins[self_name]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 assert hashlib.sha256(v.run(['git','show','HEAD:'+self_name])).hexdigest()==qualification_pins[self_name]
 with tempfile.TemporaryDirectory(prefix='coh-new-snapshot-verifier-') as temporary:
  root=Path(temporary);base=root/'synthetic'
  optimized=subprocess.run([sys.executable,'-O',str(Path(__file__).resolve()),'--fixture',str(fixture),'--output',str(root/'optimized-proof.json')],capture_output=True,text=True,timeout=30)
  assert optimized.returncode and 'ASSERTIONS_REQUIRED' in optimized.stderr and not (root/'optimized-proof.json').exists();checks+=1
  v.load_inspector(v.source_pins(False)).inspect(fixture,base)
  helper=root/'fixture.c';helper.write_text(FIXTURE_C.replace('VERIFY_SOURCE',str(v.HERE/'verify_source_snapshot.c')))
  command=['cc',*v.FLAGS,'-Wno-misleading-indentation','-I'+str(v.ROOT/'native-android/include'),helper,*[v.ROOT/'native-android'/s for s in v.SOURCES[1:]],'-lcrypto','-lz','-lm','-o',root/'synthetic-producer'];v.run(command);v.run([root/'synthetic-producer',base])
  for p in base.iterdir():p.chmod(0o600)
  original={name:(base/name).read_bytes() for name in v.NAMES}
  for mode in ('release','asan','ubsan'):
   binary,build=v.build(root/mode,False,mode);baseline=execute(binary,base,True);checks+=1;refusals=0
   for name,raw in original.items():
    write(base/name,raw[:-1]);execute(binary,base,False);checks+=1;refusals+=1;write(base/name,raw)
   mutations=[('eligibility.bin',3*4,0),('eligibility.bin',13*4,0),('eligibility.bin',64+4,0),('eligibility.bin',2*64+8*4,0),('eligibility.bin',2*64+7*4,0),('eligibility.bin',2*64+4*4,101),('resources.cohres',36,99),('resources.cohres',20,99),('public-bounds.cohrbw',92,1),('packet-metadata.bin',27*4,99),('packet-metadata.bin',35*4,99),('packet-metadata.bin',36*4,99),('owner.cohown',48,3),('owner.cohown',32*4,99),('packet.bin',0,11)]
   for name,at,value in mutations:
    raw=bytearray(original[name]);struct.pack_into('<I',raw,at,value);write(base/name,raw);execute(binary,base,False);checks+=1;refusals+=1;write(base/name,original[name])
   # Change active mod_time consistently in catalog+eligibility: GROUPS alone
   # now disagrees, while catalog name CRC/runtime/topology still validate.
   raw=bytearray(original['catalog.cohcat']);at=48;selected=None
   for _ in range(struct.unpack_from('<I',raw,24)[0]):
    file,_,_,records,n=struct.unpack_from('<5I',raw,at);at+=20+n
    for _ in range(records):
     slot,_,size,_=struct.unpack_from('<4I',raw,at);start=at+16
     if raw[start+4] and selected is None:selected=(file,slot,raw.index(0,start+5)+1)
     at=start+size
   assert selected is not None;file,slot,mod_at=selected;struct.pack_into('<I',raw,mod_at,101)
   ledger=bytearray(original['eligibility.bin'])
   for at in range(0,len(ledger),64):
    if struct.unpack_from('<3I',ledger,at)==(3,file,slot):struct.pack_into('<I',ledger,at+16,101);break
   else:raise AssertionError('missing test ledger identity')
   write(base/'catalog.cohcat',raw);write(base/'eligibility.bin',ledger);result=execute(binary,base,False);assert result['stage']==4,result;checks+=1;refusals+=1;write(base/'catalog.cohcat',original['catalog.cohcat']);write(base/'eligibility.bin',original['eligibility.bin'])
   # Preserve all grammar/count/footer fields but substitute an actual root
   # name in the packet: only same-snapshot visitor matching can reject it.
   side=original['runtime.cohrts'];at=80
   for _ in range(struct.unpack_from('<I',side,44)[0]):
    _,active,_,_,_,n,_,size=struct.unpack_from('<8I',side,at)
    if active:root_name=side[at+32:at+32+n];break
    at+=32
   raw=bytearray(original['packet.bin']);at=raw.rfind(root_name);assert at>=0;raw[at]=ord('x') if raw[at]!=ord('x') else ord('y');write(base/'packet.bin',raw);result=execute(binary,base,False);assert result['stage']==4,result;checks+=1;refusals+=1;write(base/'packet.bin',original['packet.bin'])
   # Sparse over-cap resources refuse before allocation or body decoding.
   with (base/'resources.cohres').open('wb') as f:f.truncate(32*1024**2+1)
   execute(binary,base,False);checks+=1;refusals+=1;write(base/'resources.cohres',original['resources.cohres'])
   again=execute(binary,base,True);checks+=1;assert again==baseline
   # A genuine saved-tail omission shape retains its source catalog/resource
   # owner but sends no last-slot definition. Four roots follow that skipped
   # tail; the direct helper above asserts completion state advances just once.
   cat=original['catalog.cohcat'];at=48;tail=None
   for _ in range(struct.unpack_from('<I',cat,24)[0]):
    file,_,slots,records,n=struct.unpack_from('<5I',cat,at);at+=20+n
    for _ in range(records):
     slot,_,size,_=struct.unpack_from('<4I',cat,at);start=at+16
     if file==0 and slot+1==slots:tail=(slot,cat[start:start+size])
     at=start+size
   assert tail is not None;slot,wire=tail;packet=original['packet.bin'];at=packet.find(wire);assert at>=0 and at==packet.rfind(wire);write(base/'packet.bin',packet[:at]+packet[at+len(wire):])
   ledger=bytearray(original['eligibility.bin'])
   for at in range(0,len(ledger),64):
    if struct.unpack_from('<3I',ledger,at)==(3,0,slot):struct.pack_into('<I',ledger,at+20,1);struct.pack_into('<I',ledger,at+24,1);struct.pack_into('<I',ledger,at+32,0)
   struct.pack_into('<I',ledger,len(ledger)-64+24,baseline['counts']['emitted_definitions']-1);write(base/'eligibility.bin',ledger)
   meta=bytearray(original['packet-metadata.bin']);struct.pack_into('<I',meta,20,len((base/'packet.bin').read_bytes())*8);struct.pack_into('<I',meta,52,baseline['counts']['emitted_definitions']-1);write(base/'packet-metadata.bin',meta)
   omitted=execute(binary,base,True);assert omitted['counts']['emitted_definitions']+1==baseline['counts']['emitted_definitions'] and omitted['counts']['emitted_roots']==4;checks+=1
   for name in ('packet.bin','eligibility.bin','packet-metadata.bin'):write(base/name,original[name])
   modes[mode]={'checks':refusals+3,'refusals':refusals,'counts':baseline['counts'],'saved_tail_with_four_roots_passed':True,'binary':v.identity(binary,16*1024**2),'maximum_static_frame_bytes':build['maximum_static_frame_bytes']}
   # Each real native malloc/calloc site is failed in turn in a fresh process.
   # This counts linked adapter ownership, not libc/OpenSSL internal allocation.
   harness=root/(mode+'-allocation.c');harness.write_text(ALLOCATION_C.replace('VERIFY_SOURCE',str(v.HERE/'verify_source_snapshot.c')))
   wrapped=root/(mode+'-allocation');v.run(['cc',*build['flags'],'-I'+str(v.ROOT/'native-android/include'),harness,*[v.ROOT/'native-android'/s for s in v.SOURCES[1:]],'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',wrapped])
   def allocation_case(fail):
    p=subprocess.run([str(wrapped),str(base),str(fail)],capture_output=True,text=True,timeout=30,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    assert p.returncode==(2 if fail else 0),(p.returncode,p.stdout,p.stderr)
    result=json.loads(p.stdout);owned=json.loads(p.stderr);assert result['passed']==(not fail) and owned['native_live_allocations']==0;return owned['native_allocation_calls']
   allocations=allocation_case(0);checks+=1
   for fail in range(1,allocations+1):allocation_case(fail);checks+=1
   allocation_modes[mode]={'successful_native_allocation_calls':allocations,'allocation_failure_refusals':allocations,'final_live_native_allocations_each_case':0}
  assert modes['release']['counts']==modes['asan']['counts']==modes['ubsan']['counts']
  cap=root/'synthetic.cohgtx';write(cap,envelope(base));inspection=v.load_inspector(v.source_pins(False)).inspect(cap);assert inspection['files']['packet.bin']['sha256']==hashlib.sha256(original['packet.bin']).hexdigest();checks+=1
  # Current-byte build guard must refuse any changed committed dependency. The
  # normal CLI also rejects public inputs, symlinks and reused output ownership.
  public=root/'public';public.write_bytes(b'x')
  try:v.identity(public)
  except ValueError:checks+=1
  else:raise AssertionError('public input accepted')
  link=root/'link';link.symlink_to(cap)
  try:v.identity(link)
  except ValueError:checks+=1
  else:raise AssertionError('symlink accepted')
  try:v.inspect(cap,base/'packet.bin',base,base/'existing.json')
  except ValueError:checks+=1
  else:raise AssertionError('reused output accepted')
  expected=dict(v.source_pins(False));expected[next(iter(expected))]='0'*64
  try:v.verify_pins(expected)
  except ValueError:checks+=1
  else:raise AssertionError('changed source pin accepted')
  # Once these three new files are committed, run the actual private checker
  # end-to-end against synthetic bytes and assert its deliberate authority
  # refusal. No external live token admission is invoked.
  receipt=v.inspect(cap,base/'packet.bin',root/'checked',(root/'checked'/'verification.json'))
  assert receipt['checks']==dict.fromkeys(v.CHECKS,True) and receipt['source_generation_admitted'] is False and receipt['world_authority'] is False and receipt['build']['current_committed_sources_verified'] is True
  assert (root/'checked'/'verification.json').stat().st_mode&0o777==0o600;checks+=1
 v.verify_pins(qualification_pins)
 assert v.run(['git','rev-parse','HEAD']).decode().strip()==qualification_revision
 assert v.source_pins(True)=={k:value for k,value in qualification_pins.items() if k!=self_name}
 assert hashlib.sha256(v.run(['git','show','HEAD:'+self_name])).hexdigest()==qualification_pins[self_name]
 result={'schema':'coh-source-snapshot-verifier-host-v1','passed':True,'checks':checks,'source_revision':qualification_revision,'source_sha256':qualification_pins,'fixture':v.identity(fixture,private=False),'modes':modes,'allocation_modes':allocation_modes,'fixtures_synthetic_only':True,'original_source_layout_fixture_reused':True,'owner_and_resource_observations_synthetic':True,'live_capture_executed':False,'source_generation_admitted':False,'world_authority':False,'named_memory_only_not_process_rss':True,'leak_sanitizer':False,'qualification_helper_committed_before_run_and_unchanged':True}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'refusals_per_mode':modes['release']['refusals'],'fixtures_synthetic_only':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();qualify(a.fixture,a.output)
