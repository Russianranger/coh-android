/* Fixture production header selection only. No dates/Map/catalog/authority. */
#include "persist-newer-provider.h"
#include "persist-newer-qualification-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static uint32_t word(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static void hash(const void*p,size_t n,unsigned char out[32]){CHECK(SHA256(p,n,out)!=NULL);}
static CohStatus digest(void*context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_STATE;}
static void file_hash(const char*path,size_t maximum,unsigned char out[32]){
 FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long size=ftell(f);CHECK(size>=0&&(unsigned long)size<=maximum&&!fseek(f,0,SEEK_SET));unsigned char*raw=malloc(size?(size_t)size:1);CHECK(raw&&fread(raw,1,(size_t)size,f)==(size_t)size&&fgetc(f)==EOF&&!fclose(f));hash(raw,(size_t)size,out);wipe(raw,(size_t)size);free(raw);
}
typedef struct{unsigned char source[32],build[32],profile[32],run[32],input[32],executable[32],input_ledger[32],compile_profile[32];}Ledger;
typedef char ledger_size[(sizeof(Ledger)==256)?1:-1];
typedef struct{unsigned char build[32],executable[32],input_ledger[32],fixture[32];}Measured;
/* Fixture consistency only: neither labels nor self-hash authenticates an engine. */
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],PersistNewerIdentity*observed,PersistNewerIdentity*expected){
 if(memcmp(raw,"COHPN1\0\0",8))return 1;
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
static void diagnostic(const PersistNewerReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=PERSIST_NEWER_STAGE_INPUT&&r->stage<=PERSIST_NEWER_STAGE_DIGEST);
 CHECK(r->failure_byte<=PERSIST_NEWER_INPUT_MAX&&r->source_calls<=1&&r->crc_calls<=1&&r->mode_calls<=2&&r->open_calls<=1&&r->read_calls<=4&&r->seek_calls<=1&&r->source_close_calls<=1&&r->wrapper_close_calls<=1&&r->source_accepted<=1&&r->header_end<=PERSIST_NEWER_INPUT_MAX);
 CHECK(r->update_calls<=64&&r->stream_bytes<=512&&r->visited_fields<=14&&r->interpret_calls<=15&&r->failure_diagnostics<=1&&r->fixture_identity_matched<=1);
 CHECK(r->crypto_cleanup_complete==1&&r->cleanup_complete==1&&persist_newer_is_idle());
}
static void call(CohBytes b,const PersistNewerIdentity*observed,const PersistNewerIdentity*expected,unsigned route,unsigned production,unsigned fault,PersistNewerResult*out,PersistNewerReceipt*r,CohStatus status,unsigned stage){
 PersistNewerResult before=*out;unsigned char*input=malloc(b.size?b.size:1);CHECK(input);memcpy(input,b.data,b.size);PersistNewerIdentity old_observed=*observed,old_expected=*expected,observed_arg=*observed,expected_arg=*expected;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(persist_newer_is_idle());CohStatus got=persist_newer_apply(b,&observed_arg,&expected_arg,&d,route,production,fault,out,r,PERSIST_NEWER_BUDGET_MAX,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"persist mismatch wanted=%u got=%u stage=%u wanted_stage=%u bytes=%llu route=%u mode=%u fault=%u\n",(unsigned)status,(unsigned)got,r->stage,stage,(unsigned long long)b.size,route,production,fault);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(b.data,input,b.size)&&!memcmp(observed,&old_observed,sizeof(old_observed))&&!memcmp(expected,&old_expected,sizeof(old_expected))&&!memcmp(&observed_arg,&old_observed,sizeof(old_observed))&&!memcmp(&expected_arg,&old_expected,sizeof(old_expected)));
 if(status==COH_OK){CHECK(r->fixture_identity_matched&&r->source_accepted&&r->header_end==out->header_end);loads++;}
 else{CHECK(!memcmp(out,&before,sizeof(*out)));refusals++;}
 wipe(input,b.size);free(input);wipe(&before,sizeof(before));
}
static CohStatus fail_digest(void*context,CohBytes b,uint8_t out[32]){(void)context;(void)b;(void)out;return COH_IO;}
static void controls(CohBytes raw,const PersistNewerIdentity*good,PersistNewerResult*out,PersistNewerReceipt*r){
 for(unsigned field=0;field<5;field++){
  PersistNewerIdentity bad=*good;((unsigned char*)(void*)&bad)[field*32]^=1;call(raw,&bad,good,0,1,0,out,r,COH_STATE,PERSIST_NEWER_STAGE_IDENTITY);CHECK(!r->source_calls&&!r->crc_calls&&!r->fixture_identity_matched);identity_controls++;
  bad=*good;memset((unsigned char*)(void*)&bad+field*32,0,32);call(raw,&bad,&bad,0,1,0,out,r,COH_STATE,PERSIST_NEWER_STAGE_IDENTITY);CHECK(!r->source_calls&&!r->crc_calls);identity_controls++;
 }
 PersistNewerIdentity wrong=*good;wrong.input_sha256[0]^=1;call(raw,&wrong,&wrong,0,1,0,out,r,COH_STATE,PERSIST_NEWER_STAGE_DIGEST);CHECK(!r->source_calls&&!r->crc_calls);
 PersistNewerResult saved=*out;CohCostumeImportDigest d={digest,NULL,0,65536};PersistNewerIdentity separate=*good;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?PERSIST_NEWER_BUDGET_MAX+1u:PERSIST_NEWER_BUDGET_MAX;size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(persist_newer_apply(raw,good,&separate,&limited,0,1,0,out,r,budget,retained)==COH_LIMIT);
  CHECK(!memcmp(out,&saved,sizeof(*out))&&r->status==COH_LIMIT&&r->stage==PERSIST_NEWER_STAGE_INPUT&&!r->source_calls&&!r->crc_calls);diagnostic(r);budget_controls++;refusals++;
 }
 CohCostumeImportDigest bad_digest=d;bad_digest.sha256=fail_digest;
 CHECK(persist_newer_apply(raw,good,&separate,&bad_digest,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_IO&&r->stage==PERSIST_NEWER_STAGE_DIGEST&&!r->source_calls&&!r->crc_calls&&!memcmp(out,&saved,sizeof(saved)));diagnostic(r);refusals++;
 CHECK(persist_newer_apply(raw,NULL,good,&d,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());refusals++;
 CHECK(persist_newer_apply(raw,good,NULL,&d,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());refusals++;
 CHECK(persist_newer_apply(raw,good,&separate,&d,0,1,0,NULL,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&persist_newer_is_idle());refusals++;
 CHECK(persist_newer_apply(raw,good,&separate,&d,0,1,0,out,NULL,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());refusals++;
 CHECK(persist_newer_apply(raw,good,good,&d,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());alias_controls++;
 CHECK(persist_newer_apply(raw,good,&separate,&d,0,1,0,out,(PersistNewerReceipt*)(void*)out,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());alias_controls++;
 PersistNewerIdentity old=*good;CHECK(persist_newer_apply(raw,good,&separate,&d,0,1,0,(PersistNewerResult*)(void*)good,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(good,&old,sizeof(old))&&persist_newer_is_idle());alias_controls++;
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);CHECK(persist_newer_apply(raw,good,&separate,&d,0,1,0,(PersistNewerResult*)(void*)raw.data,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(raw.data,copy,raw.size)&&persist_newer_is_idle());alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)raw.data;alias.context_bytes=1;CHECK(persist_newer_apply(raw,good,&separate,&alias,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());alias_controls++;
 alias=d;alias.context=(void*)out;alias.context_bytes=1;CHECK(persist_newer_apply(raw,good,&separate,&alias,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());alias_controls++;
 alias=d;alias.context=(void*)(uintptr_t)(UINTPTR_MAX-1u);alias.context_bytes=4;CHECK(persist_newer_apply(raw,good,&separate,&alias,0,1,0,out,r,PERSIST_NEWER_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&persist_newer_is_idle());alias_controls++;
 free(copy);wipe(&saved,sizeof(saved));
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],262144,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],65536,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x31464e50u);unsigned count=word(f),baseline_crc=word(f);CHECK(count>=30&&count<=256);PersistNewerIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));unsigned caller_acceptances=0,caller_rejections=0,strict_acceptances=0,strict_rejections=0,profile_refusals=0,source_cleanups=0,source_crc_runs=0;
 PersistNewerResult out;PersistNewerReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f),stage=word(f),failure=word(f);size_t bytes=word(f);unsigned route=word(f),production=word(f),fault=word(f),source_calls=word(f),mode_calls=word(f),open_calls=word(f),source_closes=word(f),wrapper_closes=word(f);unsigned char sum[32];CHECK(number==n&&bytes<=65537&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;PersistNewerIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));PersistNewerIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&persist_newer_is_idle());ledger_controls++;}}
  PersistNewerIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(&out,0xa5,sizeof(out));memset(&receipt,0x5a,sizeof(receipt));
  call((CohBytes){raw,bytes},&case_id,&case_id,route,production,fault,&out,&receipt,(CohStatus)status,stage);
  CHECK(receipt.failure_byte==failure&&receipt.source_calls==source_calls&&receipt.mode_calls==mode_calls&&receipt.open_calls==open_calls&&receipt.source_close_calls==source_closes&&receipt.wrapper_close_calls==wrapper_closes&&receipt.failure_diagnostics==(source_calls&&status!=COH_OK?1u:0u));
  if(open_calls){CHECK(receipt.crc_calls==1&&receipt.update_calls==35&&receipt.stream_bytes==171&&receipt.visited_fields==14&&receipt.interpret_calls==15);source_crc_runs++;source_cleanups++;if(route==0){CHECK(source_calls==1&&production==1&&mode_calls==(status==COH_OK?2u:1u));if(status==COH_OK)caller_acceptances++;else caller_rejections++;}else{CHECK(route==1&&!source_calls&&!production&&!mode_calls);if(status==COH_OK)strict_acceptances++;else strict_rejections++;}}
  else{CHECK(!receipt.crc_calls&&!receipt.update_calls&&!receipt.stream_bytes&&!receipt.visited_fields&&!receipt.interpret_calls&&!receipt.source_calls&&!receipt.mode_calls);profile_refusals++;}
  if(status==COH_OK){unsigned type_bytes=(unsigned)raw[12]|(unsigned)raw[13]<<8;size_t header_end=14u+type_bytes+(4u-(type_bytes+2u)%4u)%4u;CHECK(out.source_crc==baseline_crc&&out.header_end==header_end&&receipt.header_end==header_end&&receipt.source_accepted);}
  if(!n){CHECK(route==0&&production==1&&!fault&&status==COH_OK&&bytes==2584&&out.header_end==20);controls((CohBytes){raw,bytes},&identity,&out,&receipt);}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&caller_acceptances>=10&&caller_rejections>=5&&strict_acceptances>=1&&strict_rejections>=3&&profile_refusals>=10&&source_cleanups==source_crc_runs&&persist_newer_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"fixture_cases\":%u,\"baseline_crc\":%u,\"source_successes\":%lu,\"bounded_refusals\":%lu,\"caller_acceptances\":%u,\"caller_rejections\":%u,\"strict_header_acceptances\":%u,\"strict_header_rejections\":%u,\"bounded_wire_profile_refusals\":%u,\"source_context_cleanups\":%u,\"source_crc_runs\":%u,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"provider_owner_bytes\":%llu,\"crypto_object_bytes\":%llu,\"development_or_filesystem_freshness_executed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"runtime_default_admitted\":false,\"dictionary_imported\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"server_identity_bound\":false,\"selected_owner_bound\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,count,baseline_crc,loads,refusals,caller_acceptances,caller_rejections,strict_acceptances,strict_rejections,profile_refusals,source_cleanups,source_crc_runs,identity_controls,ledger_controls,alias_controls,budget_controls,(unsigned long long)persist_newer_owner_bytes(),(unsigned long long)persist_newer_crypto_object_bytes(),fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&observed,sizeof(observed));wipe(&identity,sizeof(identity));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(&out,sizeof(out));wipe(&receipt,sizeof(receipt));return 0;
}
