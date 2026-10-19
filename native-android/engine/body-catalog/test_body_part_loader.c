/* Controlled source loader fixture; no current Map/catalog/generation authority. */
#include "body-part-loader-provider.h"
#include "loader-qualification-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned long checks,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static uint32_t word(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static void text(FILE*f,char*out){unsigned n=word(f);CHECK(n<260&&fread(out,1,n,f)==n);out[n]=0;}
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
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],BodyLoaderIdentity*observed,BodyLoaderIdentity*expected){
 if(memcmp(raw,"COHBLD1\0",8))return 1;
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
static void diagnostic(const BodyLoaderReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=BODYLOADER_STAGE_INPUT&&r->stage<=BODYLOADER_STAGE_COMPLETE);
 CHECK(r->entry_calls<=2&&r->shared_calls<=2&&r->acquire_calls<=2&&r->load_calls<=2&&r->locate_calls<=2&&r->persist_calls<=2&&r->binary_calls<=2);
 CHECK(!r->callback_calls&&r->getter_count<=29&&r->cache_hit<=1&&r->source_return<=1&&r->fixture_identity_matched<=1&&r->loaded_fields_verified<=29&&r->struct_clear_calls<=2&&r->cleanup_complete==1&&sourceloader_is_idle());
}
static void call(CohBytes b,const BodyLoaderIdentity*observed,const BodyLoaderIdentity*expected,unsigned fault,CohCostumeInput*out,BodyLoaderReceipt*r,CohStatus status,unsigned stage){
 CohCostumeInput*before=malloc(sizeof(*before));CHECK(before);memcpy(before,out,sizeof(*before));unsigned char*input=malloc(b.size?b.size:1);CHECK(input);memcpy(input,b.data,b.size);BodyLoaderIdentity old_observed=*observed,old_expected=*expected,observed_arg=*observed,expected_arg=*expected;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(sourceloader_is_idle());CohStatus got=sourceloader_apply(b,&observed_arg,&expected_arg,&d,fault,out,r,COH_COSTUME_INPUT_BUDGET_MAX,65536);
 if(got!=status)fprintf(stderr,"loader status mismatch wanted=%u got=%u stage=%u wanted_stage=%u fault=%u bytes=%llu entry=%u load=%u binary=%u clear=%u\n",(unsigned)status,(unsigned)got,r->stage,stage,fault,(unsigned long long)b.size,r->entry_calls,r->load_calls,r->binary_calls,r->struct_clear_calls);
 CHECK(got==status);CHECK(r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(b.data,input,b.size)&&!memcmp(observed,&old_observed,sizeof(old_observed))&&!memcmp(expected,&old_expected,sizeof(old_expected))&&!memcmp(&observed_arg,&old_observed,sizeof(old_observed))&&!memcmp(&expected_arg,&old_expected,sizeof(old_expected)));
 if(status==COH_OK){CHECK(r->cache_hit&&r->source_return&&r->fixture_identity_matched&&r->loaded_fields_verified==out->part_count&&r->getter_count==out->part_count);loads++;}
 else{CHECK(!memcmp(out,before,sizeof(*out)));refusals++;}
 wipe(input,b.size);free(input);wipe(before,sizeof(*before));free(before);
}
static void expected(FILE*f,CohCostumeInput*out,unsigned rows){
 memset(out,0,sizeof(*out));out->kind=COH_COSTUME_INPUT_BODY_PARTS;out->schema_crc=0xcf27aba3u;out->dependency_count=word(f);CHECK(out->dependency_count==1);for(unsigned i=0;i<out->dependency_count;i++){text(f,out->dependencies[i].path);out->dependencies[i].timestamp=word(f);}out->part_count=rows;
 for(unsigned i=0;i<rows;i++){CohCostumeInputPart*p=out->parts+i;text(f,p->name);text(f,p->source_file);text(f,p->geometry_name);text(f,p->texture_name);text(f,p->base_name);p->bone_count_first=word(f);p->influence_cost=word(f);p->bone_count_last=word(f);p->dont_clear_word=word(f);p->bones[0]=word(f);p->bones[1]=word(f);p->part_index=word(f);}
}
static void controls(CohBytes raw,const BodyLoaderIdentity*good,CohCostumeInput*out,BodyLoaderReceipt*r){
 for(unsigned field=0;field<5;field++){
  BodyLoaderIdentity bad=*good;((unsigned char*)(void*)&bad)[field*32]^=1;call(raw,&bad,good,BODYLOADER_FAULT_NONE,out,r,COH_STATE,BODYLOADER_STAGE_IDENTITY);CHECK(!r->entry_calls&&!r->shared_calls&&!r->binary_calls&&!r->fixture_identity_matched);identity_controls++;
  bad=*good;memset((unsigned char*)(void*)&bad+field*32,0,32);call(raw,&bad,&bad,BODYLOADER_FAULT_NONE,out,r,COH_STATE,BODYLOADER_STAGE_IDENTITY);CHECK(!r->entry_calls&&!r->binary_calls);identity_controls++;
 }
 for(unsigned fault=BODYLOADER_FAULT_MISSING_CACHE;fault<=BODYLOADER_FAULT_BINARY_REFUSE;fault++){
  unsigned stage=fault==BODYLOADER_FAULT_MISSING_CACHE?BODYLOADER_STAGE_LOCATE:fault==BODYLOADER_FAULT_PERSIST_REFUSE?BODYLOADER_STAGE_PERSIST:BODYLOADER_STAGE_BINARY;call(raw,good,good,fault,out,r,COH_UNSUPPORTED,stage);CHECK(!r->cache_hit&&!r->source_return&&!r->loaded_fields_verified);
 }
 call(raw,good,good,4,out,r,COH_UNSUPPORTED,BODYLOADER_STAGE_PROFILE);
 BodyLoaderIdentity wrong=*good;wrong.input_sha256[0]^=1;call(raw,&wrong,&wrong,BODYLOADER_FAULT_NONE,out,r,COH_STATE,BODYLOADER_STAGE_DECODE);CHECK(r->binary_calls==1&&!r->cache_hit);
 CohCostumeInput*saved=malloc(sizeof(*saved));CHECK(saved);memcpy(saved,out,sizeof(*saved));CohCostumeImportDigest d={digest,NULL,0,65536};BodyLoaderIdentity separate=*good;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?COH_COSTUME_INPUT_BUDGET_MAX+1u:COH_COSTUME_INPUT_BUDGET_MAX;
  size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(sourceloader_apply(raw,good,&separate,&limited,0,out,r,budget,retained)==COH_LIMIT);
  CHECK(!memcmp(out,saved,sizeof(*out))&&r->status==COH_LIMIT&&r->stage==BODYLOADER_STAGE_INPUT&&!r->entry_calls&&!r->binary_calls);diagnostic(r);budget_controls++;refusals++;
 }
 CHECK(sourceloader_apply(raw,NULL,good,&d,0,out,r,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&sourceloader_is_idle());refusals++;
 CHECK(sourceloader_apply(raw,good,NULL,&d,0,out,r,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&sourceloader_is_idle());refusals++;
 CHECK(sourceloader_apply(raw,good,&separate,&d,0,NULL,r,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&sourceloader_is_idle());refusals++;
 CHECK(sourceloader_apply(raw,good,&separate,&d,0,out,NULL,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&sourceloader_is_idle());refusals++;
 CHECK(sourceloader_apply(raw,good,&separate,&d,0,out,(BodyLoaderReceipt*)(void*)out,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&sourceloader_is_idle());alias_controls++;
 BodyLoaderIdentity old=*good;CHECK(sourceloader_apply(raw,good,&separate,&d,0,(CohCostumeInput*)(void*)good,r,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(good,&old,sizeof(old))&&sourceloader_is_idle());alias_controls++;
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);CHECK(sourceloader_apply(raw,good,&separate,&d,0,(CohCostumeInput*)(void*)raw.data,r,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(raw.data,copy,raw.size)&&sourceloader_is_idle());alias_controls++;
 free(copy);wipe(saved,sizeof(*saved));free(saved);
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],65536,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],65536,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x314c5042u);unsigned count=word(f);CHECK(count==7);BodyLoaderIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));unsigned authentic=0,synthetic=0,decode_refusals=0;
 CohCostumeInput*out=malloc(sizeof(*out)),*want=malloc(sizeof(*want));CHECK(out&&want);BodyLoaderReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f);size_t bytes=word(f);unsigned rows=word(f);unsigned char sum[32];CHECK(number==n&&bytes<=65536&&rows<=29&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;BodyLoaderIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));BodyLoaderIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&sourceloader_is_idle());ledger_controls++;}}
  BodyLoaderIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(out,0xa5,sizeof(*out));memset(&receipt,0x5a,sizeof(receipt));
  if(!status){expected(f,want,rows);want->end_byte=bytes;memcpy(want->payload_sha256,sum,32);call((CohBytes){raw,bytes},&case_id,&case_id,0,out,&receipt,COH_OK,BODYLOADER_STAGE_COMPLETE);CHECK(!memcmp(out,want,sizeof(*out)));CHECK(receipt.entry_calls==1&&receipt.shared_calls==1&&receipt.acquire_calls==1&&receipt.load_calls==1&&receipt.locate_calls==1&&receipt.persist_calls==1&&receipt.binary_calls==1&&!receipt.callback_calls);if(!n){authentic++;controls((CohBytes){raw,bytes},&identity,out,&receipt);}else synthetic++;}
  else{unsigned stage=n==6?BODYLOADER_STAGE_LOADED:BODYLOADER_STAGE_DECODE;call((CohBytes){raw,bytes},&case_id,&case_id,0,out,&receipt,(CohStatus)status,stage);CHECK(!receipt.cache_hit&&!receipt.source_return);decode_refusals++;}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&authentic==1&&synthetic==2&&decode_refusals==4&&sourceloader_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"authentic_CLIENT_rows\":28,\"authentic_cache_hits\":%u,\"synthetic_cache_hits\":%u,\"cache_decode_or_adapter_refusals\":%u,\"source_loader_successes\":%lu,\"bounded_refusals\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"preprocess_callback_calls\":0,\"all_raw_fields_preserved\":true,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,authentic,synthetic,decode_refusals,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&observed,sizeof(observed));wipe(&identity,sizeof(identity));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(out,sizeof(*out));wipe(want,sizeof(*want));free(out);free(want);return 0;
}
