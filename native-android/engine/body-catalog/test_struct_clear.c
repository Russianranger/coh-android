/* New original production cache-hit loader fixture only. */
#include "struct-clear-provider.h"
#include "struct-clear-qualification-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,successes,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,direct_successes,strings_released,rows_released;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static uint32_t word(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static void hash(const void*p,size_t n,unsigned char out[32]){CHECK(SHA256(p,n,out)!=NULL);}
static CohStatus digest(void*context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_STATE;}
static void file_hash(const char*path,size_t maximum,unsigned char out[32]){
 FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long size=ftell(f);CHECK(size>=0&&(unsigned long)size<=maximum&&!fseek(f,0,SEEK_SET));unsigned char*raw=malloc(size?(size_t)size:1);CHECK(raw&&fread(raw,1,(size_t)size,f)==(size_t)size&&fgetc(f)==EOF&&!fclose(f));hash(raw,(size_t)size,out);wipe(raw,(size_t)size);free(raw);
}
typedef struct{unsigned char source[32],build[32],profile[32],run[32],input[32],executable[32],input_ledger[32],compile_profile[32];} Ledger;
typedef char ledger_size[(sizeof(Ledger)==256)?1:-1];
typedef struct{unsigned char build[32],executable[32],input_ledger[32],fixture[32];} Measured;
/* All claims here are fixture associations. Compiled labels and a self-hash do
 * not authenticate an original runtime, operating system, profile or Map owner. */
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],StructClearIdentity*observed,StructClearIdentity*expected){
 if(memcmp(raw,"COHUB1\0\0",8))return 1;
 Ledger l;memcpy(&l,raw+8,sizeof(l));
 if(memcmp(l.source,fixture_source_id,32))return 2;
 if(memcmp(l.build,m->build,32))return 3;
 if(memcmp(l.profile,fixture_profile_id,32))return 4;
 if(memcmp(l.run,fixture_run_id,32))return 5;
 if(memcmp(l.input,input,32)||memcmp(input,fixture_input_sha256,32))return 6;
 if(memcmp(l.executable,m->executable,32))return 7;
 if(memcmp(l.input_ledger,m->input_ledger,32)||memcmp(l.input_ledger,fixture_input_ledger_id,32))return 8;
 if(memcmp(l.compile_profile,fixture_compile_profile_id,32))return 9;
 memcpy(observed,&l,sizeof(*observed));memcpy(expected->source_id,fixture_source_id,32);memcpy(expected->build_id,m->build,32);memcpy(expected->profile_id,fixture_profile_id,32);memcpy(expected->run_id,fixture_run_id,32);memcpy(expected->input_sha256,input,32);wipe(&l,sizeof(l));return 0;
}


static void diagnostics(const StructClearReceipt*r){
 CHECK(r->cleanup_complete&&r->crypto_cleanup_complete&&struct_clear_is_idle());
 CHECK(r->clear_nodes<=30&&r->clear_strings<=150&&r->clear_arrays<=1&&r->clear_order_count==r->clear_nodes&&r->clear_numeric_preserved==r->clear_nodes);
 CHECK(r->status<=COH_STATE&&r->source_close_calls<=1&&!r->wrapper_close_calls);
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[2*i]=digits[raw[i]>>4];out[2*i+1]=digits[raw[i]&15];}out[64]=0;}
static CohStatus fail_digest(void*c,CohBytes b,uint8_t out[32]){(void)c;(void)b;(void)out;return COH_IO;}
static void direct_controls(const StructClearRequest*request,const StructClearIdentity*id,StructClearFixtureResult*out,StructClearReceipt*r){
 StructClearFixtureResult saved=*out;StructClearIdentity observed=*id,expected=*id;CohCostumeImportDigest d={digest,NULL,0,65536};
 for(unsigned i=0;i<5;i++)for(unsigned kind=0;kind<2;kind++){
  observed=expected=*id;if(kind){memset((unsigned char*)&observed+i*32u,0,32);expected=observed;}else((unsigned char*)&observed)[i*32u]^=1;
  CHECK(struct_clear_fixture(request,&observed,&expected,&d,out,r,1048576,65536)==COH_STATE&&r->stage==2&&!memcmp(out,&saved,sizeof(saved)));diagnostics(r);identity_controls++;
 }
 observed=expected=*id;observed.input_sha256[0]^=1;expected=observed;CHECK(struct_clear_fixture(request,&observed,&expected,&d,out,r,1048576,65536)==COH_STATE&&r->stage==14&&!memcmp(out,&saved,sizeof(saved)));diagnostics(r);observed=expected=*id;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?1048577:1048576,retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(struct_clear_fixture(request,&observed,&expected,&limited,out,r,budget,retained)==COH_LIMIT&&r->stage==1&&!memcmp(out,&saved,sizeof(saved)));diagnostics(r);budget_controls++;
 }
 CohCostumeImportDigest broken=d;broken.sha256=fail_digest;CHECK(struct_clear_fixture(request,&observed,&expected,&broken,out,r,1048576,65536)==COH_IO&&r->stage==14&&!memcmp(out,&saved,sizeof(saved)));diagnostics(r);
 CHECK(struct_clear_fixture(request,&observed,&observed,&d,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved)));alias_controls++;
 CHECK(struct_clear_fixture(request,&observed,&expected,&d,out,(StructClearReceipt*)(void*)out,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved)));alias_controls++;
 CHECK(struct_clear_fixture(request,&observed,&expected,&d,(StructClearFixtureResult*)(void*)request,r,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved)));alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)request;alias.context_bytes=1;CHECK(struct_clear_fixture(request,&observed,&expected,&alias,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved)));alias_controls++;
 alias=d;alias.context=(void*)(uintptr_t)(UINTPTR_MAX-1);alias.context_bytes=4;CHECK(struct_clear_fixture(request,&observed,&expected,&alias,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved)));alias_controls++;
 uintptr_t wrap=UINTPTR_MAX-7u;
 for(unsigned i=0;i<6;i++){
  CHECK(struct_clear_fixture(i==0?(const StructClearRequest*)wrap:request,i==1?(const StructClearIdentity*)wrap:&observed,i==2?(const StructClearIdentity*)wrap:&expected,i==3?(const CohCostumeImportDigest*)wrap:&d,i==4?(StructClearFixtureResult*)wrap:out,i==5?(StructClearReceipt*)wrap:r,1048576,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&struct_clear_is_idle());alias_controls++;
 }
 for(unsigned i=0;i<6;i++)CHECK(struct_clear_fixture(i?request:NULL,i==1?NULL:&observed,i==2?NULL:&expected,i==3?NULL:&d,i==4?NULL:out,i==5?NULL:r,1048576,65536)==COH_INVALID&&struct_clear_is_idle());
 wipe(&saved,sizeof(saved));
}
typedef char direct_width[(sizeof(StructClearRequest)==856)?1:-1];
typedef char result_width[(sizeof(StructClearFixtureResult)==148)?1:-1];
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],1048576,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],131072,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x31435343);unsigned loaders=word(f),direct=word(f);CHECK(loaders==8&&direct>40&&direct<64);StructClearIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));
 StructClearFixtureResult*out=malloc(sizeof(*out)),*want=malloc(sizeof(*want));CHECK(out&&want);StructClearReceipt r;
 for(unsigned c=0;c<loaders;c++){
  unsigned number=word(f),status=word(f),stage=word(f),fault=word(f),rows=word(f),strings=word(f),arrays=word(f),bytes=word(f);unsigned char sum[32];CHECK(number==c&&bytes<=65536&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!c){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;StructClearIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));StructClearIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&struct_clear_is_idle());ledger_controls++;}}
  StructClearIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);StructClearResult*loaded=malloc(sizeof(*loaded)),*expected=malloc(sizeof(*expected));CHECK(loaded&&expected);memset(loaded,0xa5,sizeof(*loaded));memset(expected,0xa5,sizeof(*expected));if(!status)CHECK(fread(expected,1,sizeof(*expected),f)==sizeof(*expected));
  CohCostumeImportDigest api={digest,NULL,0,65536};StructClearIdentity before_id=case_id;unsigned char*before=malloc(bytes?bytes:1);CHECK(before);memcpy(before,raw,bytes);
  CohStatus got=struct_clear_apply((CohBytes){raw,bytes},&case_id,&before_id,&api,fault,1,loaded,&r,1048576,65536);
  if(got!=status||r.stage!=stage)fprintf(stderr,"loader case%u status%u/%u stage%u/%u\n",c,(unsigned)got,status,r.stage,stage);
  CHECK(got==status&&r.stage==stage&&!memcmp(raw,before,bytes));diagnostics(&r);
  CHECK(r.clear_nodes==rows&&r.clear_strings==strings&&r.clear_arrays==arrays&&r.clear_order_count==rows);
  for(unsigned i=0;i<rows;i++)CHECK(r.clear_order[i]==rows-1-i);
  if(!status){CHECK(!memcmp(loaded,expected,sizeof(*loaded))&&r.source_close_calls==1&&!r.struct_clear_calls&&r.clear_root_null&&r.source_crc==0xcf27aba3u);successes++;}
  else{CHECK(!memcmp(loaded,expected,sizeof(*loaded)));refusals++;if(c<7)CHECK(r.struct_clear_calls==1&&r.clear_root_null);else CHECK(!r.entry_calls&&!r.clear_root_null);}
  rows_released+=rows;strings_released+=strings;wipe(loaded,sizeof(*loaded));wipe(expected,sizeof(*expected));free(loaded);free(expected);wipe(raw,bytes);wipe(before,bytes);free(raw);free(before);
 }
 for(unsigned c=0;c<direct;c++){
  unsigned number=word(f),status=word(f),stage=word(f);unsigned char sum[32];StructClearRequest request;CHECK(number==c&&fread(sum,1,32,f)==32&&fread(&request,1,sizeof(request),f)==sizeof(request));unsigned char actual[32];hash(&request,sizeof(request),actual);CHECK(!memcmp(actual,sum,32));StructClearIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);StructClearIdentity observed_id=case_id;StructClearRequest before=request;memset(out,0xa5,sizeof(*out));memset(want,0xa5,sizeof(*want));if(!status)CHECK(fread(want,1,sizeof(*want),f)==sizeof(*want));CohCostumeImportDigest api={digest,NULL,0,65536};
  CohStatus got=struct_clear_fixture(&request,&case_id,&observed_id,&api,out,&r,1048576,65536);if(got!=status||r.stage!=stage)fprintf(stderr,"direct case%u wanted%u/%u got%u/%u\n",c,status,stage,(unsigned)got,r.stage);
  CHECK(got==status&&r.stage==stage&&!memcmp(&request,&before,sizeof(before))&&!memcmp(out,want,sizeof(*out)));diagnostics(&r);
  if(!status){CHECK(out->root_null&&out->repeat_no_releases&&out->numeric_preserved==out->rows);direct_successes++;rows_released+=out->rows;strings_released+=out->strings;if(c==0)direct_controls(&request,&case_id,out,&r);}
  else{CHECK(!r.clear_nodes&&!r.clear_strings&&!r.clear_arrays&&!r.clear_root_null);refusals++;}
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&successes==2&&direct_successes>35&&refusals>10&&identity_controls==10&&ledger_controls==9&&alias_controls==11&&budget_controls==5&&struct_clear_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"provider_owner_bytes\":%lu,\"crypto_object_bytes\":%lu,\"loader_cases\":%u,\"direct_fixtures\":%u,\"loader_successes\":%lu,\"direct_successes\":%lu,\"bounded_refusals\":%lu,\"rows_released\":%lu,\"strings_released\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"exact_reverse_array_and_source_string_order\":true,\"original_destructors_integrated_in_new_loader\":true,\"engine_allocator_qualified\":false,\"runtime_catalog_admitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,(unsigned long)struct_clear_owner_bytes(),(unsigned long)struct_clear_crypto_object_bytes(),loaders,direct,successes,direct_successes,refusals,rows_released,strings_released,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(out,sizeof(*out));wipe(want,sizeof(*want));free(out);free(want);return 0;
}
