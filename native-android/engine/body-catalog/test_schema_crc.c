/* Controlled source schema-CRC fixture; no current Map/catalog/generation authority. */
#include "schema-crc-provider.h"
#include "schema-crc-qualification-identity.h"
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
typedef struct{unsigned char source[32],build[32],profile[32],run[32],input[32],executable[32],input_ledger[32],compile_profile[32];} Ledger;
typedef char ledger_size[(sizeof(Ledger)==256)?1:-1];
typedef struct{unsigned char build[32],executable[32],input_ledger[32],fixture[32];} Measured;
/* All claims here are fixture associations. Compiled labels and a self-hash do
 * not authenticate an original runtime, operating system, profile or Map owner. */
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],SchemaCrcIdentity*observed,SchemaCrcIdentity*expected){
 if(memcmp(raw,"COHSCR1\0",8))return 1;
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
static void diagnostic(const SchemaCrcReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=SCHEMA_CRC_STAGE_INPUT&&r->stage<=SCHEMA_CRC_STAGE_COMPLETE);
 CHECK(r->failure_byte<=SCHEMA_CRC_WIRE_MAX&&r->mutation_count<=4&&r->source_calls<=1&&r->update_calls<=64&&r->stream_bytes<=512&&r->visited_fields<=14&&r->interpret_calls<=15);
 CHECK(r->crypto_cleanup_complete==1&&r->fixture_identity_matched<=1&&r->cleanup_complete==1&&schema_crc_is_idle());
}
static void call(CohBytes b,const SchemaCrcIdentity*observed,const SchemaCrcIdentity*expected,SchemaCrcResult*out,SchemaCrcReceipt*r,CohStatus status,unsigned stage){
 SchemaCrcResult before=*out;unsigned char*input=malloc(b.size?b.size:1);CHECK(input);memcpy(input,b.data,b.size);SchemaCrcIdentity old_observed=*observed,old_expected=*expected,observed_arg=*observed,expected_arg=*expected;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(schema_crc_is_idle());CohStatus got=schema_crc_apply(b,&observed_arg,&expected_arg,&d,out,r,SCHEMA_CRC_BUDGET_MAX,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"schema CRC mismatch wanted=%u got=%u stage=%u wanted_stage=%u bytes=%llu\n",(unsigned)status,(unsigned)got,r->stage,stage,(unsigned long long)b.size);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(b.data,input,b.size)&&!memcmp(observed,&old_observed,sizeof(old_observed))&&!memcmp(expected,&old_expected,sizeof(old_expected))&&!memcmp(&observed_arg,&old_observed,sizeof(old_observed))&&!memcmp(&expected_arg,&old_expected,sizeof(old_expected)));
 if(status==COH_OK){CHECK(r->source_calls==1&&r->fixture_identity_matched&&r->update_calls==out->update_calls&&r->stream_bytes==out->stream_bytes&&r->visited_fields==out->visited_fields&&r->interpret_calls==out->interpret_calls);loads++;}
 else{CHECK(!memcmp(out,&before,sizeof(*out)));refusals++;}
 wipe(input,b.size);free(input);wipe(&before,sizeof(before));
}
static CohStatus fail_digest(void*context,CohBytes b,uint8_t out[32]){(void)context;(void)b;(void)out;return COH_IO;}
static void controls(CohBytes raw,const SchemaCrcIdentity*good,SchemaCrcResult*out,SchemaCrcReceipt*r){
 for(unsigned field=0;field<5;field++){
  SchemaCrcIdentity bad=*good;((unsigned char*)(void*)&bad)[field*32]^=1;call(raw,&bad,good,out,r,COH_STATE,SCHEMA_CRC_STAGE_IDENTITY);CHECK(!r->source_calls&&!r->fixture_identity_matched);identity_controls++;
  bad=*good;memset((unsigned char*)(void*)&bad+field*32,0,32);call(raw,&bad,&bad,out,r,COH_STATE,SCHEMA_CRC_STAGE_IDENTITY);CHECK(!r->source_calls);identity_controls++;
 }
 SchemaCrcIdentity wrong=*good;wrong.input_sha256[0]^=1;call(raw,&wrong,&wrong,out,r,COH_STATE,SCHEMA_CRC_STAGE_DIGEST);CHECK(!r->source_calls);
 SchemaCrcResult saved=*out;CohCostumeImportDigest d={digest,NULL,0,65536};SchemaCrcIdentity separate=*good;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?SCHEMA_CRC_BUDGET_MAX+1u:SCHEMA_CRC_BUDGET_MAX;size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(schema_crc_apply(raw,good,&separate,&limited,out,r,budget,retained)==COH_LIMIT);
  CHECK(!memcmp(out,&saved,sizeof(*out))&&r->status==COH_LIMIT&&r->stage==SCHEMA_CRC_STAGE_INPUT&&!r->source_calls);diagnostic(r);budget_controls++;refusals++;
 }
 CohCostumeImportDigest bad_digest=d;bad_digest.sha256=fail_digest;
 CHECK(schema_crc_apply(raw,good,&separate,&bad_digest,out,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_IO&&r->stage==SCHEMA_CRC_STAGE_DIGEST&&!r->source_calls&&!memcmp(out,&saved,sizeof(saved)));diagnostic(r);refusals++;
 CHECK(schema_crc_apply(raw,NULL,good,&d,out,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());refusals++;
 CHECK(schema_crc_apply(raw,good,NULL,&d,out,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());refusals++;
 CHECK(schema_crc_apply(raw,good,&separate,&d,NULL,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&schema_crc_is_idle());refusals++;
 CHECK(schema_crc_apply(raw,good,&separate,&d,out,NULL,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());refusals++;
 CHECK(schema_crc_apply(raw,good,good,&d,out,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());alias_controls++;
 CHECK(schema_crc_apply(raw,good,&separate,&d,out,(SchemaCrcReceipt*)(void*)out,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());alias_controls++;
 SchemaCrcIdentity old=*good;CHECK(schema_crc_apply(raw,good,&separate,&d,(SchemaCrcResult*)(void*)good,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(good,&old,sizeof(old))&&schema_crc_is_idle());alias_controls++;
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);CHECK(schema_crc_apply(raw,good,&separate,&d,(SchemaCrcResult*)(void*)raw.data,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(raw.data,copy,raw.size)&&schema_crc_is_idle());alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)raw.data;alias.context_bytes=1;CHECK(schema_crc_apply(raw,good,&separate,&alias,out,r,SCHEMA_CRC_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&schema_crc_is_idle());alias_controls++;
 free(copy);wipe(&saved,sizeof(saved));
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],131072,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],65536,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x31464353u);unsigned count=word(f),retained_crc=word(f);CHECK(count>=50&&count<=128);SchemaCrcIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));unsigned exact_schemas=0,synthetic=0,profile_refusals=0,zero_updates=0,ignored_controls=0,source_cleanups=0;uint32_t baseline_crc=0,numeric_crc=0,default_crc=0,redundant_crc=0;
 SchemaCrcResult out,want;SchemaCrcReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f),stage=word(f),failure=word(f),mutations=word(f);size_t bytes=word(f);unsigned success=word(f);unsigned char sum[32];CHECK(number==n&&bytes<=357&&success==(status==COH_OK)&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;SchemaCrcIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));SchemaCrcIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&schema_crc_is_idle());ledger_controls++;}}
  memset(&want,0,sizeof(want));if(success){want.crc=word(f);want.stream_bytes=word(f);want.update_calls=word(f);want.visited_fields=word(f);want.interpret_calls=word(f);CHECK(want.stream_bytes<=512&&want.update_calls<=64);for(unsigned i=0;i<want.update_calls;i++)want.update_lengths[i]=word(f);CHECK(fread(want.stream,1,want.stream_bytes,f)==want.stream_bytes);}
  SchemaCrcIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(&out,0xa5,sizeof(out));memset(&receipt,0x5a,sizeof(receipt));
  call((CohBytes){raw,bytes},&case_id,&case_id,&out,&receipt,(CohStatus)status,stage);CHECK(receipt.failure_byte==failure&&receipt.mutation_count==mutations);
  if(success){
   CHECK(!memcmp(&out,&want,sizeof(out))&&receipt.source_calls==1);source_cleanups++;
   for(unsigned i=0;i<out.update_calls;i++)if(!out.update_lengths[i])zero_updates++;
   if(!mutations){exact_schemas++;if(!n){baseline_crc=out.crc;CHECK(out.stream_bytes==171&&out.update_calls==35&&out.visited_fields==14&&out.interpret_calls==15&&bytes==8);controls((CohBytes){raw,bytes},&identity,&out,&receipt);}else CHECK(out.crc==baseline_crc&&out.stream_bytes==171&&out.update_calls==35);}
   else synthetic++;
   if(n>=1&&n<=4){CHECK(out.crc==baseline_crc&&out.stream_bytes==171&&out.update_calls==35);ignored_controls++;}
   if(n==5)numeric_crc=out.crc;
   if(n==6){CHECK(out.crc==numeric_crc&&out.crc!=baseline_crc);ignored_controls++;}
   if(n==9||n==14||n==20||n==24||n==25){CHECK(out.crc==baseline_crc&&out.update_calls==35);ignored_controls++;}
   if(n==11)default_crc=out.crc;
   if(n==12){CHECK(out.crc==baseline_crc&&out.update_calls==36&&out.stream_bytes==171);ignored_controls++;}
   if(n==13){CHECK(out.crc==default_crc);ignored_controls++;}
   if(n==16)redundant_crc=out.crc;
   if(n==17||n==26){CHECK(out.crc==redundant_crc);ignored_controls++;}
   if(n==18||n==19){CHECK(out.crc==0x01000000u&&!out.stream_bytes&&!out.update_calls&&!out.visited_fields&&!out.interpret_calls);ignored_controls++;}
   if(n==23)CHECK(out.stream_bytes==423&&out.update_calls==39&&bytes==356);
  }else{CHECK(!receipt.source_calls&&!receipt.update_calls&&!receipt.stream_bytes&&!receipt.visited_fields&&!receipt.interpret_calls);profile_refusals++;}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&exact_schemas==2&&synthetic>=25&&profile_refusals>=25&&source_cleanups==loads&&ignored_controls>=15&&zero_updates>50&&schema_crc_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"exact_original_schema_runs\":%u,\"baseline_crc\":%u,\"baseline_stream_bytes\":171,\"baseline_update_calls\":35,\"baseline_visited_fields\":14,\"baseline_interpret_calls\":15,\"retained_CLIENT_crc_word\":%u,\"retained_CLIENT_word_matches_source_crc\":%s,\"synthetic_schema_runs\":%u,\"bounded_wire_profile_refusals\":%u,\"source_context_cleanups\":%u,\"zero_length_source_updates\":%u,\"ignored_or_prefix_or_redundant_controls\":%u,\"source_successes\":%lu,\"bounded_refusals\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"body_or_cache_selection_executed\":false,\"dynamic_or_static_defines_executed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"runtime_default_admitted\":false,\"dictionary_imported\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"server_identity_bound\":false,\"selected_owner_bound\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,exact_schemas,baseline_crc,retained_crc,baseline_crc==retained_crc?"true":"false",synthetic,profile_refusals,source_cleanups,zero_updates,ignored_controls,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&observed,sizeof(observed));wipe(&identity,sizeof(identity));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(&out,sizeof(out));wipe(&want,sizeof(want));wipe(&receipt,sizeof(receipt));return 0;
}
