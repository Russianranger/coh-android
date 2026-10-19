/* Controlled source sorted-list operations fixture; no current Map/catalog/generation authority. */
#include "file-list-ops-provider.h"
#include "file-list-ops-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned long checks,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,reservation_faults;
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
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],FileOpsIdentity*observed,FileOpsIdentity*expected){
 if(memcmp(raw,"COHFLO1\0",8))return 1;
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
typedef char request_width[(sizeof(FileOpsRequest)==17296)?1:-1];
typedef char result_width[(sizeof(FileOpsResult)==4932)?1:-1];
static void diagnostic(const FileOpsReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=FLO_INPUT&&r->stage<=FLO_COMPLETE);
 CHECK(r->failed_operation<FLO_OP_MAX&&r->identity_matched<=1&&r->create_calls<=1&&r->insert_calls<=16&&r->find_calls<=32&&r->search_calls<=32);
 CHECK(r->allocation_calls<=16&&r->earray_insert_calls==r->allocation_calls&&r->directory_calls==r->insert_calls&&r->normalization_calls==r->insert_calls+r->find_calls);
 CHECK(r->reservation_calls<=17&&r->reserved_nodes<=16&&r->node_count==r->allocation_calls&&r->cleanup_complete==1&&fileops_is_idle());
}
static void call(const FileOpsRequest*request,const FileOpsIdentity*good,FileOpsResult*out,FileOpsReceipt*r,CohStatus status,unsigned stage){
 FileOpsRequest before=*request;FileOpsResult old=*out;FileOpsIdentity observed=*good,expected=*good;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(fileops_is_idle());CohStatus got=fileops_apply(request,&observed,&expected,&d,out,r,FLO_BUDGET_MAX,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"FileList ops mismatch wanted%u got%u stage%u wanted%u\n",(unsigned)status,(unsigned)got,r->stage,stage);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(request,&before,sizeof(before))&&!memcmp(&observed,good,sizeof(*good))&&!memcmp(&expected,good,sizeof(*good)));
 if(status==COH_OK){CHECK(r->create_calls==1&&r->identity_matched&&r->node_count==out->count&&r->reservation_calls==1+r->reserved_nodes);loads++;}
 else{CHECK(!memcmp(out,&old,sizeof(old))&&!r->create_calls&&!r->insert_calls&&!r->find_calls&&!r->search_calls&&!r->allocation_calls);refusals++;if(stage==FLO_RESERVE)reservation_faults++;}
 wipe(&before,sizeof(before));wipe(&old,sizeof(old));
}
static CohStatus fail_digest(void*context,CohBytes b,uint8_t out[32]){(void)context;(void)b;(void)out;return COH_IO;}
static void controls(const FileOpsRequest*request,const FileOpsIdentity*good,FileOpsResult*out,FileOpsReceipt*r){
 FileOpsResult old=*out;FileOpsIdentity expected=*good,observed=*good;CohCostumeImportDigest d={digest,NULL,0,65536};
 for(unsigned i=0;i<5;i++){
  observed=*good;((unsigned char*)&observed)[i*32]^=1;CHECK(fileops_apply(request,&observed,&expected,&d,out,r,FLO_BUDGET_MAX,65536)==COH_STATE&&r->stage==FLO_IDENTITY&&!memcmp(out,&old,sizeof(old)));diagnostic(r);identity_controls++;
  observed=*good;memset((unsigned char*)&observed+i*32,0,32);expected=observed;CHECK(fileops_apply(request,&observed,&expected,&d,out,r,FLO_BUDGET_MAX,65536)==COH_STATE&&r->stage==FLO_IDENTITY&&!memcmp(out,&old,sizeof(old)));diagnostic(r);identity_controls++;expected=*good;
 }
 observed=*good;observed.input_sha256[0]^=1;expected=observed;CHECK(fileops_apply(request,&observed,&expected,&d,out,r,FLO_BUDGET_MAX,65536)==COH_STATE&&r->stage==FLO_DIGEST&&!memcmp(out,&old,sizeof(old)));diagnostic(r);observed=*good;expected=*good;
 for(unsigned i=0;i<5;i++){size_t budget=i==0?0:i==1?1:i==2?FLO_BUDGET_MAX+1:FLO_BUDGET_MAX;size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;CHECK(fileops_apply(request,&observed,&expected,&limited,out,r,budget,retained)==COH_LIMIT&&r->stage==FLO_INPUT&&!memcmp(out,&old,sizeof(old)));diagnostic(r);budget_controls++;}
 CohCostumeImportDigest broken=d;broken.sha256=fail_digest;CHECK(fileops_apply(request,&observed,&expected,&broken,out,r,FLO_BUDGET_MAX,65536)==COH_IO&&r->stage==FLO_DIGEST&&!memcmp(out,&old,sizeof(old)));diagnostic(r);
 CHECK(fileops_apply(request,&observed,&observed,&d,out,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 CHECK(fileops_apply(request,&observed,&expected,&d,out,(FileOpsReceipt*)(void*)out,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 CHECK(fileops_apply(request,&observed,&expected,&d,(FileOpsResult*)(void*)request,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)request;alias.context_bytes=1;CHECK(fileops_apply(request,&observed,&expected,&alias,out,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 alias=d;alias.context=r;alias.context_bytes=sizeof(*r);FileOpsReceipt saved=*r;CHECK(fileops_apply(request,&observed,&expected,&alias,out,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old))&&!memcmp(r,&saved,sizeof(saved)));alias_controls++;
 for(unsigned i=0;i<6;i++){CHECK(fileops_apply(i==0?NULL:request,i==1?NULL:&observed,i==2?NULL:&expected,i==3?NULL:&d,i==4?NULL:out,i==5?NULL:r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old))&&fileops_is_idle());}
 alias=d;alias.context=(void*)(uintptr_t)(UINTPTR_MAX-1u);alias.context_bytes=4;CHECK(fileops_apply(request,&observed,&expected,&alias,out,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 alias=d;alias.context=NULL;alias.context_bytes=1;CHECK(fileops_apply(request,&observed,&expected,&alias,out,r,FLO_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,&old,sizeof(old)));alias_controls++;
 wipe(&old,sizeof(old));
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],4u*1024u*1024u,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],131072,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x31504f46u);unsigned count=word(f);CHECK(count>50&&count<=128);FileOpsIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));FileOpsRequest request;FileOpsResult out,want;FileOpsReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f),stage=word(f),failed=word(f),reservations=word(f),reserved=word(f);unsigned char sum[32];CHECK(number==n&&fread(sum,1,32,f)==32&&fread(&request,1,sizeof(request),f)==sizeof(request));unsigned char actual[32];hash(&request,sizeof(request),actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;FileOpsIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));FileOpsIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&fileops_is_idle());ledger_controls++;}}
  memset(&want,0,sizeof(want));if(status==COH_OK)CHECK(fread(&want,1,sizeof(want),f)==sizeof(want));FileOpsIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(&out,0xa5,sizeof(out));memset(&receipt,0x5a,sizeof(receipt));
  call(&request,&case_id,&out,&receipt,(CohStatus)status,stage);CHECK(receipt.failed_operation==failed&&receipt.reservation_calls==reservations&&receipt.reserved_nodes==reserved);
  if(status==COH_OK){if(memcmp(&out,&want,sizeof(out)))fprintf(stderr,"result mismatch case%u\n",n);CHECK(!memcmp(&out,&want,sizeof(out)));unsigned inserts=0,finds=0;for(unsigned i=0;i<request.count;i++){inserts+=request.operations[i].kind==FLO_INSERT;finds+=request.operations[i].kind==FLO_FIND;}CHECK(receipt.insert_calls==inserts&&receipt.find_calls==finds&&receipt.search_calls==request.count);if(!n)controls(&request,&identity,&out,&receipt);}
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&loads>20&&refusals>20&&reservation_faults==17&&fileops_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"fixture_cases\":%u,\"owned_fixed_bytes\":%llu,\"source_transactions\":%lu,\"pre_source_refusals\":%lu,\"owned_reservation_faults\":%lu,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"real_filesystem_calls\":0,\"original_allocator_OOM_recovery_claimed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"source_generation_admitted\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,count,(unsigned long long)fileops_owned_bytes(),loads,refusals,reservation_faults,identity_controls,ledger_controls,alias_controls,budget_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&request,sizeof(request));wipe(&out,sizeof(out));wipe(&want,sizeof(want));wipe(&receipt,sizeof(receipt));wipe(&identity,sizeof(identity));wipe(&observed,sizeof(observed));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));return 0;
}
