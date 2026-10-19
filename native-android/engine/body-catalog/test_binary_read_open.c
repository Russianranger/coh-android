/* Controlled source binary-header fixture; no current Map/catalog/generation authority. */
#include "binary-read-open-provider.h"
#include "binary-open-qualification-identity.h"
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
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],BinaryOpenIdentity*observed,BinaryOpenIdentity*expected){
 if(memcmp(raw,"COHBRO1\0",8))return 1;
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
static void diagnostic(const BinaryOpenReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=BINARYOPEN_STAGE_INPUT&&r->stage<=BINARYOPEN_STAGE_COMPLETE);
 CHECK(r->failure_byte<=BINARYOPEN_INPUT_MAX&&r->open_calls<=1&&r->read_calls<=4&&r->seek_calls<=1);
 CHECK(r->source_close_calls<=1&&r->wrapper_close_calls<=1&&r->source_close_calls+r->wrapper_close_calls<=1);
 CHECK(r->source_accepted<=1&&r->header_end<=4112&&r->fixture_identity_matched<=1&&r->cleanup_complete==1&&binaryopen_is_idle());
}
static void call(CohBytes b,const BinaryOpenIdentity*observed,const BinaryOpenIdentity*expected,unsigned build,unsigned ignore,unsigned fault,BinaryOpenResult*out,BinaryOpenReceipt*r,CohStatus status,unsigned stage){
 BinaryOpenResult before=*out;unsigned char*input=malloc(b.size?b.size:1);CHECK(input);memcpy(input,b.data,b.size);BinaryOpenIdentity old_observed=*observed,old_expected=*expected,observed_arg=*observed,expected_arg=*expected;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(binaryopen_is_idle());CohStatus got=binaryopen_apply(b,&observed_arg,&expected_arg,&d,build,ignore,fault,out,r,BINARYOPEN_BUDGET_MAX,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"binary-open mismatch wanted=%u got=%u stage=%u wanted_stage=%u bytes=%llu\n",(unsigned)status,(unsigned)got,r->stage,stage,(unsigned long long)b.size);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(b.data,input,b.size)&&!memcmp(observed,&old_observed,sizeof(old_observed))&&!memcmp(expected,&old_expected,sizeof(old_expected))&&!memcmp(&observed_arg,&old_observed,sizeof(old_observed))&&!memcmp(&expected_arg,&old_expected,sizeof(old_expected)));
 if(status==COH_OK){CHECK(r->source_accepted&&r->fixture_identity_matched&&r->header_end==out->header_end&&r->wrapper_close_calls==1&&!r->source_close_calls);loads++;}
 else{CHECK(!memcmp(out,&before,sizeof(*out)));refusals++;}
 wipe(input,b.size);free(input);
}
static CohStatus fail_digest(void*context,CohBytes b,uint8_t out[32]){(void)context;(void)b;(void)out;return COH_IO;}
static void controls(CohBytes raw,const BinaryOpenIdentity*good,BinaryOpenResult*out,BinaryOpenReceipt*r){
 for(unsigned field=0;field<5;field++){
  BinaryOpenIdentity bad=*good;((unsigned char*)(void*)&bad)[field*32]^=1;call(raw,&bad,good,0,1,0,out,r,COH_STATE,BINARYOPEN_STAGE_IDENTITY);CHECK(!r->open_calls&&!r->fixture_identity_matched);identity_controls++;
  bad=*good;memset((unsigned char*)(void*)&bad+field*32,0,32);call(raw,&bad,&bad,0,1,0,out,r,COH_STATE,BINARYOPEN_STAGE_IDENTITY);CHECK(!r->open_calls);identity_controls++;
 }
 BinaryOpenIdentity wrong=*good;wrong.input_sha256[0]^=1;call(raw,&wrong,&wrong,0,1,0,out,r,COH_STATE,BINARYOPEN_STAGE_DIGEST);CHECK(!r->open_calls);
 BinaryOpenResult saved=*out;CohCostumeImportDigest d={digest,NULL,0,65536};BinaryOpenIdentity separate=*good;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?BINARYOPEN_BUDGET_MAX+1u:BINARYOPEN_BUDGET_MAX;size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(binaryopen_apply(raw,good,&separate,&limited,0,1,0,out,r,budget,retained)==COH_LIMIT);
  CHECK(!memcmp(out,&saved,sizeof(*out))&&r->status==COH_LIMIT&&r->stage==BINARYOPEN_STAGE_INPUT&&!r->open_calls);diagnostic(r);budget_controls++;refusals++;
 }
 CohCostumeImportDigest bad_digest=d;bad_digest.sha256=fail_digest;
 CHECK(binaryopen_apply(raw,good,&separate,&bad_digest,0,1,0,out,r,BINARYOPEN_BUDGET_MAX,65536)==COH_IO&&r->stage==BINARYOPEN_STAGE_DIGEST&&!r->open_calls&&!memcmp(out,&saved,sizeof(saved)));diagnostic(r);refusals++;
 CHECK(binaryopen_apply(raw,NULL,good,&d,0,1,0,out,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&binaryopen_is_idle());refusals++;
 CHECK(binaryopen_apply(raw,good,NULL,&d,0,1,0,out,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&binaryopen_is_idle());refusals++;
 CHECK(binaryopen_apply(raw,good,&separate,&d,0,1,0,NULL,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&binaryopen_is_idle());refusals++;
 CHECK(binaryopen_apply(raw,good,&separate,&d,0,1,0,out,NULL,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&binaryopen_is_idle());refusals++;
 CHECK(binaryopen_apply(raw,good,good,&d,0,1,0,out,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&binaryopen_is_idle());alias_controls++;
 CHECK(binaryopen_apply(raw,good,&separate,&d,0,1,0,out,(BinaryOpenReceipt*)(void*)out,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&saved,sizeof(saved))&&binaryopen_is_idle());alias_controls++;
 BinaryOpenIdentity old=*good;CHECK(binaryopen_apply(raw,good,&separate,&d,0,1,0,(BinaryOpenResult*)(void*)good,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(good,&old,sizeof(old))&&binaryopen_is_idle());alias_controls++;
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);CHECK(binaryopen_apply(raw,good,&separate,&d,0,1,0,(BinaryOpenResult*)(void*)raw.data,r,BINARYOPEN_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(raw.data,copy,raw.size)&&binaryopen_is_idle());alias_controls++;
 free(copy);
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],262144,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],65536,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x314f5242u);unsigned count=word(f);CHECK(count>30&&count<=128);BinaryOpenIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));unsigned authentic=0,synthetic=0,source_rejections=0,framing_refusals=0,open_refusals=0;
 BinaryOpenResult out;BinaryOpenReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f),stage=word(f),failure=word(f),end=word(f),build=word(f),ignore=word(f),fault=word(f),accepted=word(f);size_t bytes=word(f);unsigned char sum[32];CHECK(number==n&&bytes<=65537&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;BinaryOpenIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));BinaryOpenIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&binaryopen_is_idle());ledger_controls++;}}
  BinaryOpenIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(&out,0xa5,sizeof(out));memset(&receipt,0x5a,sizeof(receipt));
  call((CohBytes){raw,bytes},&case_id,&case_id,build,ignore,fault,&out,&receipt,(CohStatus)status,stage);CHECK(receipt.failure_byte==failure&&receipt.source_accepted==accepted);
  if(accepted){CHECK(out.header_end==end&&receipt.header_end==end&&receipt.open_calls==1&&receipt.read_calls==4&&receipt.seek_calls==1&&!receipt.source_close_calls&&receipt.wrapper_close_calls==1);if(!n){authentic++;CHECK(end==20&&bytes==2584);controls((CohBytes){raw,bytes},&identity,&out,&receipt);}else synthetic++;}
  else if(stage==BINARYOPEN_STAGE_SOURCE_REJECT){CHECK(receipt.open_calls==1&&receipt.read_calls==4&&receipt.seek_calls==1&&receipt.source_close_calls==1&&!receipt.wrapper_close_calls);source_rejections++;}
  else if(stage==BINARYOPEN_STAGE_OPEN){CHECK(receipt.open_calls==1&&!receipt.read_calls&&!receipt.seek_calls&&!receipt.source_close_calls&&!receipt.wrapper_close_calls);open_refusals++;}
  else{CHECK(!receipt.open_calls&&!receipt.read_calls&&!receipt.seek_calls&&!receipt.source_close_calls&&!receipt.wrapper_close_calls);framing_refusals++;}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&authentic==1&&synthetic>5&&source_rejections>5&&framing_refusals>20&&open_refusals==1&&binaryopen_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"authentic_CLIENT_header_acceptances\":%u,\"authentic_header_end\":20,\"synthetic_header_acceptances\":%u,\"source_header_rejections\":%u,\"framing_profile_refusals\":%u,\"open_refusals\":%u,\"source_header_successes\":%lu,\"bounded_refusals\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"Files1_or_FileListRead_calls\":0,\"whole_Parse6_reader_executed\":false,\"ParseTableCRC_executed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,authentic,synthetic,source_rejections,framing_refusals,open_refusals,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&observed,sizeof(observed));wipe(&identity,sizeof(identity));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(&out,sizeof(out));wipe(&receipt,sizeof(receipt));return 0;
}
