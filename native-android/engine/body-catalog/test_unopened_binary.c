/* Controlled source unopened-binary fixture; no current Map/catalog/generation authority. */
#include "unopened-binary-provider.h"
#include "unopened-binary-qualification-identity.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned long checks,loads,refusals,identity_controls,ledger_controls,alias_controls,budget_controls,truncation_controls,reservation_controls,crc_contexts,string_length_controls,row_length_controls,extent_length_controls;
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
static unsigned binding(const unsigned char raw[264],const Measured*m,const unsigned char input[32],UnopenedBinaryIdentity*observed,UnopenedBinaryIdentity*expected){
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
static void diagnostic(const UnopenedBinaryReceipt*r){
 CHECK(r->status<=COH_STATE&&r->stage>=UNOPENED_BINARY_STAGE_INPUT&&r->stage<=UNOPENED_BINARY_STAGE_COMPLETE);
 CHECK(r->failure_byte<=UNOPENED_BINARY_INPUT_MAX&&r->open_calls<=1&&r->read_calls<=548&&r->seek_calls<=154);
 CHECK(r->source_close_calls<=1&&r->wrapper_close_calls<=1&&r->source_close_calls+r->wrapper_close_calls<=1);
 CHECK(r->header_accepted<=1&&r->header_end<=4112&&r->dependency_end<=UNOPENED_BINARY_INPUT_MAX&&r->body_end<=UNOPENED_BINARY_INPUT_MAX&&r->filelist_calls<=1);
 CHECK(r->table_calls<=31&&r->capacity_calls<=1&&r->allocation_calls<=30&&r->string_calls<=150&&r->int_calls<=180&&r->u8_calls<=30);
 CHECK(r->crypto_cleanup_complete==1);
 CHECK(r->source_calls<=1&&r->crc_calls==r->source_calls&&r->mode_calls==r->source_calls);
 if(r->source_calls){crc_contexts++;CHECK(r->source_crc==0xcf27aba3u&&r->update_calls==35&&r->stream_bytes==171&&r->visited_fields==14&&r->interpret_calls==15);}
 CHECK(r->warning_calls<=4&&r->source_result<=1&&r->source_node_count<=30&&r->fixture_identity_matched<=1&&r->cleanup_complete==1&&unopened_binary_is_idle());
}
static void call(CohBytes b,const UnopenedBinaryIdentity*observed,const UnopenedBinaryIdentity*expected,unsigned build,unsigned ignore,UnopenedBinaryResult*out,UnopenedBinaryReceipt*r,CohStatus status,unsigned stage){
 UnopenedBinaryResult*before=malloc(sizeof(*before));CHECK(before);memcpy(before,out,sizeof(*before));unsigned char*input=malloc(b.size?b.size:1);CHECK(input);memcpy(input,b.data,b.size);UnopenedBinaryIdentity old_observed=*observed,old_expected=*expected,observed_arg=*observed,expected_arg=*expected;CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(unopened_binary_is_idle());CohStatus got=unopened_binary_apply(b,&observed_arg,&expected_arg,&d,build,ignore,out,r,UNOPENED_BINARY_BUDGET_MAX,65536);
 if(got!=status||r->stage!=stage)fprintf(stderr,"unopened-binary mismatch wanted=%u got=%u stage=%u wanted_stage=%u bytes=%llu\n",(unsigned)status,(unsigned)got,r->stage,stage,(unsigned long long)b.size);
 CHECK(got==status&&r->status==(unsigned)status&&r->stage==stage);diagnostic(r);
 CHECK(!memcmp(b.data,input,b.size)&&!memcmp(observed,&old_observed,sizeof(old_observed))&&!memcmp(expected,&old_expected,sizeof(old_expected))&&!memcmp(&observed_arg,&old_observed,sizeof(old_observed))&&!memcmp(&expected_arg,&old_expected,sizeof(old_expected)));
 if(status==COH_OK){CHECK(r->header_accepted&&r->source_result&&r->fixture_identity_matched&&r->header_end==out->header_end&&r->dependency_end==out->dependency_end&&r->body_end==out->body_end&&r->source_close_calls==1&&!r->wrapper_close_calls);loads++;}
 else{CHECK(!memcmp(out,before,sizeof(*out)));refusals++;}
 wipe(input,b.size);free(input);wipe(before,sizeof(*before));free(before);
}
static CohStatus fail_digest(void*context,CohBytes b,uint8_t out[32]){(void)context;(void)b;(void)out;return COH_IO;}
static void controls(CohBytes raw,const UnopenedBinaryIdentity*good,UnopenedBinaryResult*out,UnopenedBinaryReceipt*r){
 for(unsigned field=0;field<5;field++){
  UnopenedBinaryIdentity bad=*good;((unsigned char*)(void*)&bad)[field*32]^=1;call(raw,&bad,good,0,1,out,r,COH_STATE,UNOPENED_BINARY_STAGE_IDENTITY);CHECK(!r->open_calls&&!r->fixture_identity_matched);identity_controls++;
  bad=*good;memset((unsigned char*)(void*)&bad+field*32,0,32);call(raw,&bad,&bad,0,1,out,r,COH_STATE,UNOPENED_BINARY_STAGE_IDENTITY);CHECK(!r->open_calls);identity_controls++;
 }
 UnopenedBinaryIdentity wrong=*good;wrong.input_sha256[0]^=1;call(raw,&wrong,&wrong,0,1,out,r,COH_STATE,UNOPENED_BINARY_STAGE_DIGEST);CHECK(!r->open_calls);
 UnopenedBinaryResult*saved=malloc(sizeof(*saved));CHECK(saved);memcpy(saved,out,sizeof(*saved));CohCostumeImportDigest d={digest,NULL,0,65536};UnopenedBinaryIdentity separate=*good;
 for(unsigned i=0;i<5;i++){
  size_t budget=i==0?0:i==1?1:i==2?UNOPENED_BINARY_BUDGET_MAX+1u:UNOPENED_BINARY_BUDGET_MAX;size_t retained=i==3?SIZE_MAX:65536;CohCostumeImportDigest limited=d;if(i==4)limited.scratch_reserve=SIZE_MAX;
  CHECK(unopened_binary_apply(raw,good,&separate,&limited,0,1,out,r,budget,retained)==COH_LIMIT);
  CHECK(!memcmp(out,saved,sizeof(*out))&&r->status==COH_LIMIT&&r->stage==UNOPENED_BINARY_STAGE_INPUT&&!r->open_calls);diagnostic(r);budget_controls++;refusals++;
 }
 CohCostumeImportDigest bad_digest=d;bad_digest.sha256=fail_digest;
 CHECK(unopened_binary_apply(raw,good,&separate,&bad_digest,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_IO&&r->stage==UNOPENED_BINARY_STAGE_DIGEST&&!r->open_calls&&!memcmp(out,saved,sizeof(*saved)));diagnostic(r);refusals++;
 CHECK(unopened_binary_apply(raw,NULL,good,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());refusals++;
 CHECK(unopened_binary_apply(raw,good,NULL,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());refusals++;
 CHECK(unopened_binary_apply(raw,good,&separate,&d,0,1,NULL,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&unopened_binary_is_idle());refusals++;
 CHECK(unopened_binary_apply(raw,good,&separate,&d,0,1,out,NULL,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());refusals++;
 CHECK(unopened_binary_apply(raw,good,good,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());alias_controls++;
 CHECK(unopened_binary_apply(raw,good,&separate,&d,0,1,out,(UnopenedBinaryReceipt*)(void*)out,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());alias_controls++;
 UnopenedBinaryIdentity old=*good;CHECK(unopened_binary_apply(raw,good,&separate,&d,0,1,(UnopenedBinaryResult*)(void*)good,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(good,&old,sizeof(old))&&unopened_binary_is_idle());alias_controls++;
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);CHECK(unopened_binary_apply(raw,good,&separate,&d,0,1,(UnopenedBinaryResult*)(void*)raw.data,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(raw.data,copy,raw.size)&&unopened_binary_is_idle());alias_controls++;
 CohCostumeImportDigest alias=d;alias.context=(void*)raw.data;alias.context_bytes=1;CHECK(unopened_binary_apply(raw,good,&separate,&alias,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID&&!memcmp(out,saved,sizeof(*saved))&&unopened_binary_is_idle());alias_controls++;
 free(copy);wipe(saved,sizeof(*saved));free(saved);
}
/* Every authentic prefix truncation must refuse before CRC/open/body source
 * entry. A deliberately failing digest also proves preflight precedes digest. */
static void all_truncations(CohBytes raw,const UnopenedBinaryIdentity*good,UnopenedBinaryResult*out,UnopenedBinaryReceipt*r){
 UnopenedBinaryResult*saved=malloc(sizeof(*saved));CHECK(saved);memcpy(saved,out,sizeof(*saved));
 UnopenedBinaryIdentity separate=*good;CohCostumeImportDigest d={fail_digest,NULL,0,65536};
 for(size_t n=0;n<raw.size;n++){
  memset(r,0xa5,sizeof(*r));
  CHECK(unopened_binary_apply((CohBytes){raw.data,n},good,&separate,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_INVALID);
  CHECK(r->status==COH_INVALID&&r->stage>=UNOPENED_BINARY_STAGE_HEADER&&r->stage<=UNOPENED_BINARY_STAGE_SCALAR&&r->failure_byte==n);
  CHECK(!r->source_calls&&!r->crc_calls&&!r->mode_calls&&!r->open_calls&&!r->read_calls&&!r->seek_calls&&!r->source_close_calls&&!r->wrapper_close_calls);
  CHECK(!memcmp(out,saved,sizeof(*saved)));diagnostic(r);truncation_controls++;refusals++;
 }
 wipe(saved,sizeof(*saved));free(saved);
}
static uint32_t load16(const unsigned char*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8;}
static uint32_t load32(const unsigned char*p){return load16(p)|load16(p+2)<<16;}
static void store32(unsigned char*p,uint32_t v){for(unsigned k=0;k<4;k++)p[k]=(unsigned char)(v>>(8*k));}
static void malformed_lengths(CohBytes raw,const UnopenedBinaryIdentity*good,UnopenedBinaryResult*out,UnopenedBinaryReceipt*r){
 unsigned char*changed=malloc(raw.size);UnopenedBinaryResult*saved=malloc(sizeof(*saved));CHECK(changed&&saved);memcpy(saved,out,sizeof(*saved));size_t at=72;
 /* Independently walk all28 retained record extents and mutate every one of
  * the140 Pascal length words, plus every row accounting word. */
 for(unsigned row=0;row<28;row++){
  size_t row_at=at;CHECK(at+4<=raw.size);uint32_t declared=load32(raw.data+at);at+=4;size_t begin=at;
  for(unsigned field=0;field<12;field++){
   if(field==0||field==1||field==4||field==5||field==6){
    CHECK(at+2<=raw.size);uint32_t len=load16(raw.data+at);size_t amount=2+len+(4-(len+2)%4)%4;CHECK(amount<=raw.size-at);
    memcpy(changed,raw.data,raw.size);changed[at]=4;changed[at+1]=1;UnopenedBinaryIdentity separate=*good;CohCostumeImportDigest d={fail_digest,NULL,0,65536};
    CHECK(unopened_binary_apply((CohBytes){changed,raw.size},good,&separate,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==COH_LIMIT);
    CHECK(r->stage==UNOPENED_BINARY_STAGE_STRING&&r->failure_byte==at&&!r->source_calls&&!r->crc_calls&&!r->open_calls);CHECK(!memcmp(out,saved,sizeof(*saved)));diagnostic(r);string_length_controls++;refusals++;at+=amount;
   }else{CHECK(raw.size-at>=4);at+=4;}
  }
  CHECK(at-begin==declared);
  const uint32_t bad_sizes[4]={0,0x7fffffffu,0x80000000u,0xffffffffu};
  for(unsigned k=0;k<4;k++){
   memcpy(changed,raw.data,raw.size);store32(changed+row_at,bad_sizes[k]);UnopenedBinaryIdentity id=*good;hash(changed,raw.size,id.input_sha256);
   call((CohBytes){changed,raw.size},&id,&id,0,1,out,r,COH_UNSUPPORTED,UNOPENED_BINARY_STAGE_SOURCE_REJECT);
   CHECK(r->source_node_count==row+1&&r->allocation_calls==row+1&&r->warning_calls==3&&r->source_close_calls==1&&r->body_end==at);row_length_controls++;
  }
 }
 CHECK(at==raw.size);
 /* Header type, opaque dependency Pascal and signed skip length bounds. */
 for(unsigned k=0;k<4;k++){
  memcpy(changed,raw.data,raw.size);unsigned stage;size_t failure;
  if(k==0){changed[12]=0;changed[13]=16;stage=UNOPENED_BINARY_STAGE_TYPE_LENGTH;failure=12;}
  else if(k==1){changed[20]=255;changed[21]=255;stage=UNOPENED_BINARY_STAGE_DEPENDENCY_HEADER;failure=raw.size;}
  else{store32(changed+28,k==2?0xffffffffu:0x7fffffffu);stage=UNOPENED_BINARY_STAGE_DEPENDENCY_SIZE;failure=k==2?28:raw.size;}
  UnopenedBinaryIdentity separate=*good;CohCostumeImportDigest d={fail_digest,NULL,0,65536};CohStatus want=k==0?COH_LIMIT:k==2?COH_UNSUPPORTED:COH_INVALID;
  CHECK(unopened_binary_apply((CohBytes){changed,raw.size},good,&separate,&d,0,1,out,r,UNOPENED_BINARY_BUDGET_MAX,65536)==want);
  CHECK(r->stage==stage&&r->failure_byte==failure&&!r->source_calls&&!r->crc_calls&&!r->open_calls);CHECK(!memcmp(out,saved,sizeof(*saved)));diagnostic(r);extent_length_controls++;refusals++;
 }
 wipe(changed,raw.size);free(changed);wipe(saved,sizeof(*saved));free(saved);
}
static void hex(const unsigned char*raw,char out[65]){static const char digits[]="0123456789abcdef";for(unsigned i=0;i<32;i++){out[i*2]=digits[raw[i]>>4];out[i*2+1]=digits[raw[i]&15];}out[64]=0;}
static void expected_part(FILE*f,UnopenedBinaryPart*p){
 char*fields[5]={p->name,p->source_file,p->geometry_name,p->texture_name,p->base_name};
 for(unsigned i=0;i<5;i++){unsigned length=word(f);CHECK(length<260&&fread(fields[i],1,length,f)==length);}
 for(unsigned i=0;i<7;i++)p->raw[i]=word(f);
 p->final_num_parts=word(f);p->final_influence_cost=word(f);p->final_dont_clear=word(f);p->final_bones[0]=word(f);p->final_bones[1]=word(f);p->final_index=word(f);p->string_null_mask=word(f);
}
int main(int argc,char**argv){
 if(argc!=5)return 2;
 Measured measured;file_hash(argv[0],8u*1024u*1024u,measured.executable);file_hash(argv[1],1048576,measured.fixture);CHECK(!memcmp(measured.fixture,fixture_wire_sha256,32));file_hash(argv[3],65536,measured.build);file_hash(argv[4],131072,measured.input_ledger);
 unsigned char ledger[264],ledger_sha[32];FILE*l=fopen(argv[2],"rb");CHECK(l&&fread(ledger,1,sizeof(ledger),l)==sizeof(ledger)&&fgetc(l)==EOF&&!fclose(l));hash(ledger,sizeof(ledger),ledger_sha);
 FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==0x31524442u);unsigned count=word(f);CHECK(count>=35&&count<=128);UnopenedBinaryIdentity observed,identity;memset(&observed,0,sizeof(observed));memset(&identity,0,sizeof(identity));unsigned authentic=0,synthetic=0,header_rejections=0,source_rejections=0,framing_refusals=0,partial_rollbacks=0,source_warnings=0,negative_count_successes=0,overwrite_controls=0,string_controls=0;
 UnopenedBinaryResult*out=malloc(sizeof(*out)),*want=malloc(sizeof(*want));CHECK(out&&want);UnopenedBinaryReceipt receipt;
 for(unsigned n=0;n<count;n++){
  unsigned number=word(f),status=word(f),stage=word(f),failure=word(f),build=word(f),ignore=word(f),header_end=word(f),dependency_end=word(f),body_end=word(f),array_count=word(f),declared=word(f),nodes=word(f),reads=word(f),seeks=word(f),tables=word(f),capacity=word(f),strings=word(f),ints=word(f),u8=word(f),warnings=word(f),header_accepted=word(f),called=word(f),source_result=word(f);size_t bytes=word(f);unsigned char sum[32];CHECK(number==n&&bytes<=65537&&nodes<=30&&fread(sum,1,32,f)==32);unsigned char*raw=malloc(bytes?bytes:1);CHECK(raw&&fread(raw,1,bytes,f)==bytes);unsigned char actual[32];hash(raw,bytes,actual);CHECK(!memcmp(actual,sum,32));
  if(!n){CHECK(!binding(ledger,&measured,actual,&observed,&identity));for(unsigned i=0;i<9;i++){unsigned char changed[264];memcpy(changed,ledger,sizeof(changed));changed[i?8+(i-1)*32:0]^=1;UnopenedBinaryIdentity a,b;memset(&a,0xa5,sizeof(a));memset(&b,0x5a,sizeof(b));UnopenedBinaryIdentity olda=a,oldb=b;CHECK(binding(changed,&measured,actual,&a,&b)==i+1&&!memcmp(&a,&olda,sizeof(a))&&!memcmp(&b,&oldb,sizeof(b))&&unopened_binary_is_idle());ledger_controls++;}}
  memset(want,0,sizeof(*want));
  if(status==COH_OK){want->source_crc=0xcf27aba3u;want->header_end=header_end;want->dependency_end=dependency_end;want->body_end=body_end;want->part_count=nodes;want->raw_array_count=array_count;want->body_declared_size=declared;for(unsigned i=0;i<nodes;i++)expected_part(f,&want->parts[i]);}
  UnopenedBinaryIdentity case_id=identity;memcpy(case_id.input_sha256,sum,32);memset(out,0xa5,sizeof(*out));memset(&receipt,0x5a,sizeof(receipt));
  call((CohBytes){raw,bytes},&case_id,&case_id,build,ignore,out,&receipt,(CohStatus)status,stage);
  if(receipt.failure_byte!=failure||receipt.read_calls!=reads||receipt.seek_calls!=seeks||receipt.warning_calls!=warnings)fprintf(stderr,"case%u diagnostic mismatch failure%u/%u reads%u/%u seeks%u/%u warnings%u/%u\n",n,receipt.failure_byte,failure,receipt.read_calls,reads,receipt.seek_calls,seeks,receipt.warning_calls,warnings);
  CHECK(receipt.failure_byte==failure&&receipt.header_end==header_end&&receipt.dependency_end==dependency_end&&receipt.body_end==body_end);
  CHECK(receipt.header_accepted==header_accepted&&receipt.filelist_calls==called&&receipt.raw_array_count==array_count&&receipt.body_declared_size==declared);
  CHECK(receipt.read_calls==reads&&receipt.seek_calls==seeks&&receipt.warning_calls==warnings&&receipt.source_node_count==nodes&&receipt.allocation_calls==nodes&&receipt.table_calls==tables&&receipt.capacity_calls==capacity&&receipt.string_calls==strings&&receipt.int_calls==ints&&receipt.u8_calls==u8&&receipt.source_result==source_result);source_warnings+=warnings;
  if(status==COH_OK){
   CHECK(!memcmp(out,want,sizeof(*out))&&receipt.open_calls==1&&receipt.source_close_calls==1&&!receipt.wrapper_close_calls);
   if(!n){authentic++;CHECK(out->header_end==20&&out->dependency_end==64&&out->body_end==2584&&bytes==2584&&out->part_count==28&&out->raw_array_count==28&&out->body_declared_size==2516);CHECK(!strcmp(out->parts[0].name,"Pants")&&!strcmp(out->parts[27].name,"Tail")&&out->parts[27].final_index==27);controls((CohBytes){raw,bytes},&identity,out,&receipt);all_truncations((CohBytes){raw,bytes},&identity,out,&receipt);malformed_lengths((CohBytes){raw,bytes},&identity,out,&receipt);}else synthetic++;
   if(n==1){UnopenedBinaryPart*p=&out->parts[0];CHECK(p->raw[0]==1&&p->raw[2]==3&&p->final_num_parts==3&&p->raw[3]==0xdeadbeefu&&p->final_dont_clear==0xefu&&p->final_bones[0]==0xffffffffu&&p->final_bones[1]==0x80000000u&&p->final_index==0x11223344u);overwrite_controls++;}
   if(n==2){UnopenedBinaryPart*p=&out->parts[0];CHECK(p->string_null_mask==19&&!p->name[0]&&!p->source_file[0]&&!strcmp(p->geometry_name,"Geo")&&(unsigned char)p->texture_name[0]==255&&!p->base_name[0]);string_controls++;}
   if(array_count&0x80000000u){CHECK(!nodes&&!out->part_count&&out->raw_array_count==array_count);negative_count_successes++;}
  }else if(stage==UNOPENED_BINARY_STAGE_HEADER_REJECT){CHECK(receipt.open_calls==1&&receipt.source_close_calls==(build==1?0u:1u)&&!receipt.wrapper_close_calls&&!receipt.filelist_calls);header_rejections++;}
  else if(stage==UNOPENED_BINARY_STAGE_SOURCE_REJECT){CHECK(receipt.open_calls==1&&receipt.source_close_calls==1&&!receipt.wrapper_close_calls&&receipt.filelist_calls==1&&!receipt.source_result);source_rejections++;if(nodes)partial_rollbacks++;}
  else{if(stage==UNOPENED_BINARY_STAGE_RESERVATION){CHECK(build==2||build==3);reservation_controls++;}CHECK(!receipt.open_calls&&!receipt.read_calls&&!receipt.seek_calls&&!receipt.source_close_calls&&!receipt.wrapper_close_calls);framing_refusals++;}
  wipe(raw,bytes);free(raw);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f)&&authentic==1&&synthetic>=8&&header_rejections==2&&source_rejections>=7&&framing_refusals>20&&partial_rollbacks>=7&&source_warnings>=15&&negative_count_successes==2&&overwrite_controls==1&&string_controls==1&&truncation_controls==2584&&reservation_controls==2&&string_length_controls==140&&row_length_controls==112&&extent_length_controls==4&&unopened_binary_is_idle());
 char fields[10][65];hex(identity.source_id,fields[0]);hex(identity.build_id,fields[1]);hex(identity.profile_id,fields[2]);hex(identity.run_id,fields[3]);hex(identity.input_sha256,fields[4]);hex(measured.fixture,fields[5]);hex(measured.executable,fields[6]);hex(measured.input_ledger,fields[7]);hex(fixture_compile_profile_id,fields[8]);hex(ledger_sha,fields[9]);
 printf("{\"checks\":{\"checks\":%lu,\"provider_owner_bytes\":%lu,\"crypto_object_bytes\":%lu,\"authentic_CLIENT_body_successes\":%u,\"authentic_header_end\":20,\"authentic_dependency_end\":64,\"authentic_body_end\":2584,\"authentic_rows\":28,\"NULL_dependencies_unobserved\":true,\"synthetic_body_successes\":%u,\"source_header_rejections\":%u,\"source_body_rejections\":%u,\"framing_profile_refusals\":%u,\"partial_body_rollbacks\":%u,\"numeric_source_warnings\":%u,\"source_successes\":%lu,\"bounded_refusals\":%lu,\"source_negative_count_empty_successes\":%u,\"duplicate_overwrite_U8_and_cached_bits_controls\":%u,\"source_NULL_and_Cstring_controls\":%u,\"identity_controls\":%lu,\"child_ledger_controls\":%lu,\"alias_controls\":%lu,\"budget_overflow_controls\":%lu,\"all_authentic_prefix_truncation_controls\":%lu,\"fixed_allocation_reservation_failures\":%lu,\"cleaned_actual_CRC_contexts\":%lu,\"all_original_string_length_controls\":%lu,\"all_original_row_length_controls\":%lu,\"header_dependency_length_controls\":%lu,\"ParseBoneNames_calls\":0,\"ParseTableCRC_executed\":true,\"native_prior_body_decoder_executed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"runtime_default_admitted\":false,\"dictionary_imported\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"server_identity_bound\":false,\"selected_owner_bound\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false},\"fixture_binding\":{\"source_id\":\"%s\",\"build_id\":\"%s\",\"profile_id\":\"%s\",\"run_id\":\"%s\",\"input_sha256\":\"%s\",\"fixture_sha256\":\"%s\",\"executable_sha256\":\"%s\",\"input_ledger_sha256\":\"%s\",\"compile_profile_sha256\":\"%s\",\"run_ledger_sha256\":\"%s\"}}\n",checks,(unsigned long)unopened_binary_owner_bytes(),(unsigned long)unopened_binary_crypto_object_bytes(),authentic,synthetic,header_rejections,source_rejections,framing_refusals,partial_rollbacks,source_warnings,loads,refusals,negative_count_successes,overwrite_controls,string_controls,identity_controls,ledger_controls,alias_controls,budget_controls,truncation_controls,reservation_controls,crc_contexts,string_length_controls,row_length_controls,extent_length_controls,fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],fields[8],fields[9]);
 wipe(fields,sizeof(fields));wipe(&observed,sizeof(observed));wipe(&identity,sizeof(identity));wipe(&measured,sizeof(measured));wipe(ledger,sizeof(ledger));wipe(ledger_sha,sizeof(ledger_sha));wipe(out,sizeof(*out));wipe(want,sizeof(*want));wipe(&receipt,sizeof(receipt));free(out);free(want);return 0;
}
