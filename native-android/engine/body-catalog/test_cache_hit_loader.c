/* New original production cache-hit loader fixture only. */
#include "cache-hit-loader-provider.h"
#include "cache-hit-loader-qualification-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,successes,refusals,entered,crc_contexts,identity_controls,ledger_controls,alias_controls,budget_controls,prefix_controls,reservation_controls;
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
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],CacheHitLoaderIdentity*observed,CacheHitLoaderIdentity*expected){
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

static void trace_check(const CacheHitLoaderReceipt*r,unsigned fault){
 static const uint32_t success[]={1,2,3,4,5,6,7,8,5,9,5,10,11,14,15,12,16};
 static const uint32_t body_failure[]={1,2,3,4,5,6,7,8,5,9,5,10,11,14,15,12,5,13,16};
 static const uint32_t header_failure[]={1,2,3,4,5,6,7,8,5,9,12,5,13,16};
 static const uint32_t open_failure[]={1,2,3,4,5,6,7,8,5,9,5,13,16};
 static const uint32_t missing[]={1,2,3,4,5,6,5,13,16};
 if(!r->entry_calls){CHECK(!r->trace_count&&!r->source_calls&&!r->crc_calls&&!r->mode_calls&&!r->open_calls&&!r->source_close_calls&&!r->struct_clear_calls);return;}
 const uint32_t*want;size_t n;
 if(fault==4){want=missing;n=sizeof(missing)/4;}
 else if(r->loader_return){want=success;n=sizeof(success)/4;}
 else if(r->binary_calls){want=body_failure;n=sizeof(body_failure)/4;}
 else if(fault==1){want=open_failure;n=sizeof(open_failure)/4;}
 else{want=header_failure;n=sizeof(header_failure)/4;}
 if(r->trace_count!=n||memcmp(r->trace,want,n*4)){fprintf(stderr,"trace wanted%lu got%u: ",(unsigned long)n,r->trace_count);for(unsigned i=0;i<r->trace_count;i++)fprintf(stderr,"%u,",r->trace[i]);fprintf(stderr,"\n");}
 CHECK(r->trace_count==n&&!memcmp(r->trace,want,n*4));
 for(size_t i=n;i<32;i++)CHECK(!r->trace[i]);
 CHECK(r->source_calls==1&&r->entry_calls==1&&r->shared_calls==1&&r->acquire_calls==1&&r->load_calls==1&&r->locate_calls==1&&!r->callback_calls);
 CHECK(r->persist_calls==(fault==4?0u:1u)&&r->crc_calls==r->persist_calls&&r->open_calls==r->persist_calls);
 CHECK(r->binary_calls==r->selected_handle&&r->binary_calls==r->supplied_handle_matched);
 CHECK(r->struct_clear_calls==!r->loader_return&&r->loader_diagnostics==!r->loader_return);
 CHECK(r->selector_diagnostics==(r->persist_calls&&!r->binary_calls));
 CHECK(r->mode_calls==(fault==4?2u:r->binary_calls&&!r->loader_return?4u:3u));
 entered++;
}
static void diagnostic(const CacheHitLoaderReceipt*r,unsigned fault){
 CHECK(r->status<=COH_STATE&&r->stage>=1&&r->stage<=CACHE_HIT_LOADER_STAGE_COMPLETE&&r->failure_byte<=65536);
 CHECK(r->open_calls<=1&&r->source_close_calls<=1&&!r->wrapper_close_calls&&r->header_accepted<=1&&r->filelist_calls<=1&&r->table_calls<=31&&r->source_node_count<=30);
 CHECK(r->crypto_cleanup_complete&&r->cleanup_complete&&cache_hit_loader_is_idle());trace_check(r,fault);
 if(r->crc_calls){crc_contexts++;CHECK(r->source_crc==0xcf27aba3u&&r->update_calls==35&&r->stream_bytes==171&&r->visited_fields==14&&r->interpret_calls==15);}
 else CHECK(!r->source_crc&&!r->update_calls&&!r->stream_bytes&&!r->visited_fields&&!r->interpret_calls);
 CHECK(r->loader_return==r->source_result&&r->getter_count==(r->loader_return?r->source_node_count:0));
}
static void call(CohBytes bytes,const CacheHitLoaderIdentity*id,unsigned fault,unsigned mode,CacheHitLoaderResult*out,CacheHitLoaderReceipt*r,CohStatus status,unsigned stage){
 CacheHitLoaderIdentity observed=*id,expected=*id,before_id=*id;CohCostumeImportDigest digest_api={digest,NULL,0,65536};
 CacheHitLoaderResult*before=malloc(sizeof(*before));unsigned char*input=malloc(bytes.size?bytes.size:1);CHECK(before&&input);memcpy(before,out,sizeof(*before));memcpy(input,bytes.data,bytes.size);
 CHECK(cache_hit_loader_is_idle());CohStatus got=cache_hit_loader_apply(bytes,&observed,&expected,&digest_api,fault,mode,out,r,1048576,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"cache-hit case fault%u mode%u bytes%lu wanted%u/%u got%u/%u\n",fault,mode,(unsigned long)bytes.size,(unsigned)status,stage,(unsigned)got,r->stage);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r,fault);
 CHECK(!memcmp(bytes.data,input,bytes.size)&&!memcmp(&observed,&before_id,sizeof(observed))&&!memcmp(&expected,&before_id,sizeof(expected)));
 if(status==COH_OK){CHECK(r->loader_return&&r->binary_calls==1&&r->source_close_calls==1&&r->header_accepted&&r->getter_count==out->part_count);successes++;}
 else{CHECK(!memcmp(out,before,sizeof(*out)));refusals++;}
 wipe(before,sizeof(*before));free(before);wipe(input,bytes.size);free(input);
}
static CohStatus fail_digest(void*c,CohBytes b,uint8_t out[32]){(void)c;(void)b;(void)out;return COH_IO;}
static void controls(CohBytes raw,const CacheHitLoaderIdentity*id,CacheHitLoaderResult*out,CacheHitLoaderReceipt*r){
 CacheHitLoaderIdentity observed=*id,expected=*id;CohCostumeImportDigest d={digest,NULL,0,65536};CacheHitLoaderResult*saved=malloc(sizeof(*saved));CHECK(saved);memcpy(saved,out,sizeof(*saved));
 for(unsigned field=0;field<5;field++)for(unsigned kind=0;kind<2;kind++){
  observed=expected=*id;if(kind){memset((unsigned char*)&observed+32*field,0,32);expected=observed;}else((unsigned char*)&observed)[32*field]^=1;
  CHECK(cache_hit_loader_apply(raw,&observed,&expected,&d,0,1,out,r,1048576,65536)==COH_STATE&&r->stage==CACHE_HIT_LOADER_STAGE_IDENTITY&&!r->entry_calls&&!memcmp(out,saved,sizeof(*out)));diagnostic(r,0);identity_controls++;
 }
 observed=expected=*id;observed.input_sha256[0]^=1;expected=observed;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&d,0,1,out,r,1048576,65536)==COH_STATE&&r->stage==CACHE_HIT_LOADER_STAGE_DIGEST&&!r->entry_calls&&!memcmp(out,saved,sizeof(*out)));diagnostic(r,0);
 observed=expected=*id;
 for(unsigned i=0;i<6;i++){
  size_t budget=i==0?0:i==1?1:i==2?1048577:i==5?262144:1048576,retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(cache_hit_loader_apply(raw,&observed,&expected,&limited,0,1,out,r,budget,retained)==COH_LIMIT&&r->stage==CACHE_HIT_LOADER_STAGE_INPUT&&!r->entry_calls&&!memcmp(out,saved,sizeof(*out)));diagnostic(r,0);budget_controls++;
 }
 CohCostumeImportDigest bad=d;bad.sha256=fail_digest;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&bad,0,1,out,r,1048576,65536)==COH_IO&&r->stage==CACHE_HIT_LOADER_STAGE_DIGEST&&!r->entry_calls&&!memcmp(out,saved,sizeof(*out)));diagnostic(r,0);
 CHECK(cache_hit_loader_apply(raw,&observed,&observed,&d,0,1,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());alias_controls++;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&d,0,1,out,(CacheHitLoaderReceipt*)out,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());alias_controls++;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&d,0,1,(CacheHitLoaderResult*)raw.data,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)raw.data;alias.context_bytes=1;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&alias,0,1,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());alias_controls++;
 alias=d;alias.context=(void*)(uintptr_t)(UINTPTR_MAX-3);alias.context_bytes=8;
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&alias,0,1,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());alias_controls++;
 CHECK(cache_hit_loader_apply(raw,NULL,&expected,&d,0,1,out,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());
 CHECK(cache_hit_loader_apply(raw,&observed,&expected,&d,0,1,NULL,r,1048576,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*out))&&cache_hit_loader_is_idle());
 for(size_t n=0;n<raw.size;n++){
  CohBytes prefix={raw.data,n};CHECK(cache_hit_loader_apply(prefix,&observed,&expected,&bad,0,1,out,r,1048576,65536)==COH_INVALID&&r->failure_byte==n&&r->stage>=4&&r->stage<=13&&!r->entry_calls&&!memcmp(out,saved,sizeof(*out)));diagnostic(r,0);prefix_controls++;
 }
 wipe(saved,sizeof(*saved));free(saved);
}
static void expected_part(FILE*f,CacheHitLoaderPart*p){
 char*fields[5]={p->name,p->source_file,p->geometry_name,p->texture_name,p->base_name};
 for(unsigned i=0;i<5;i++){unsigned length=word(f);CHECK(length<260&&fread(fields[i],1,length,f)==length);}
 for(unsigned i=0;i<7;i++)p->raw[i]=word(f);
 p->final_num_parts=word(f);p->final_influence_cost=word(f);p->final_dont_clear=word(f);p->final_bones[0]=word(f);p->final_bones[1]=word(f);p->final_index=word(f);p->string_null_mask=word(f);
}

static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[2*i]=digits[raw[i]>>4];out[2*i+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],1048576,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],131072,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x314c4843u);unsigned count=word(f);CHECK(count>=45&&count<=64);CacheHitLoaderIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));
 CacheHitLoaderResult*out=malloc(sizeof(*out)),*want=malloc(sizeof(*want));CHECK(out&&want);CacheHitLoaderReceipt r;unsigned authentic=0,crc_mismatches=0,header_refusals=0,body_refusals=0,missing=0;
 for(unsigned c=0;c<count;c++){
  unsigned number=word(f),status=word(f),stage=word(f),failure=word(f),fault=word(f),mode=word(f),header_end=word(f),dependency_end=word(f),body_end=word(f),array_count=word(f),declared=word(f),nodes=word(f),reads=word(f),seeks=word(f),tables=word(f),capacity=word(f),strings=word(f),ints=word(f),u8=word(f),warnings=word(f),header_accepted=word(f),called=word(f),source_result=word(f);size_t bytes=word(f);unsigned char sum[32];CHECK(number==c&&bytes<=65536&&nodes<=30&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!c){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;CacheHitLoaderIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));CacheHitLoaderIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&cache_hit_loader_is_idle());ledger_controls++;}}
  memset(want,0,sizeof(*want));if(!status){want->source_crc=0xcf27aba3u;want->header_end=header_end;want->dependency_end=dependency_end;want->body_end=body_end;want->part_count=nodes;want->raw_array_count=array_count;want->body_declared_size=declared;for(unsigned i=0;i<nodes;i++)expected_part(f,want->parts+i);}
  CacheHitLoaderIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(out,0xa5,sizeof(*out));memset(&r,0x5a,sizeof(r));call((CohBytes){raw,bytes},&case_id,fault,mode,out,&r,(CohStatus)status,stage);
  CHECK(r.failure_byte==failure&&r.header_end==header_end&&r.dependency_end==dependency_end&&r.body_end==body_end&&r.header_accepted==header_accepted&&r.filelist_calls==called);
  CHECK(r.raw_array_count==array_count&&r.body_declared_size==declared&&r.source_node_count==nodes&&r.read_calls==reads&&r.seek_calls==seeks&&r.warning_calls==warnings&&r.table_calls==tables&&r.capacity_calls==capacity&&r.string_calls==strings&&r.int_calls==ints&&r.u8_calls==u8&&r.source_result==source_result);
  if(!status){CHECK(!memcmp(out,want,sizeof(*out))&&r.getter_count==28);if(!c){authentic++;CHECK(bytes==2584&&header_end==20&&dependency_end==64&&body_end==2584&&out->part_count==28&&!strcmp(out->parts[0].name,"Pants")&&!strcmp(out->parts[27].name,"Tail"));controls((CohBytes){raw,bytes},&identity,out,&r);}if(c>=2&&c<=35)crc_mismatches++;}
  else if(fault==4){missing++;CHECK(!r.crc_calls&&!r.open_calls&&!r.source_close_calls&&r.struct_clear_calls==1);}
  else if(fault==2||fault==3){reservation_controls++;CHECK(!r.entry_calls);}
  else if(r.binary_calls){body_refusals++;CHECK(r.source_close_calls==1&&r.struct_clear_calls==1);}
  else if(r.entry_calls){header_refusals++;CHECK(r.source_close_calls==(fault==1?0u:1u)&&r.struct_clear_calls==1);}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&authentic==1&&crc_mismatches==34&&body_refusals==2&&header_refusals==3&&missing==1&&reservation_controls==2&&prefix_controls==2584&&identity_controls==10&&ledger_controls==9&&alias_controls==5&&budget_controls==6&&cache_hit_loader_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"provider_owner_bytes\":%lu,\"crypto_object_bytes\":%lu,\"authentic_CLIENT_loader_successes\":%u,\"authentic_header_end\":20,\"authentic_dependency_end\":64,\"authentic_body_end\":2584,\"authentic_rows\":28,\"production_CRC_mismatch_full_body_successes\":%u,\"source_loader_successes\":%lu,\"source_loader_transactions\":%lu,\"safe_production_header_refusals\":%u,\"safe_production_body_refusals\":%u,\"safe_missing_cache_refusals\":%u,\"bounded_refusals\":%lu,\"all_authentic_prefix_preflight_refusals\":%lu,\"fixed_reservation_refusals\":%lu,\"cleaned_actual_CRC_contexts\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"same_live_handle_open_close_once_verified\":true,\"source_call_order_verified\":true,\"source_ParseBoneNames_calls\":0,\"nativeDTO_or_fixture_token_bridge_emitted\":false,\"NULL_dependency_contents_observed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"runtime_default_admitted\":false,\"dictionary_imported\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"server_identity_bound\":false,\"selected_owner_bound\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,(unsigned long)cache_hit_loader_owner_bytes(),(unsigned long)cache_hit_loader_crypto_object_bytes(),authentic,crc_mismatches,successes,entered,header_refusals,body_refusals,missing,refusals,prefix_controls,reservation_controls,crc_contexts,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(out,sizeof(*out));wipe(want,sizeof(*want));wipe(&r,sizeof(r));wipe(&identity,sizeof(identity));wipe(&observed,sizeof(observed));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(fields,sizeof(fields));free(out);free(want);return 0;
}
