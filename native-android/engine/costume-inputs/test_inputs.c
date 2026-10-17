#define OPENSSL_API_COMPAT 0x10100000L
#include "coh_costume_inputs.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,calls,cuts,mutations;
#define CHECK(x)do{checks++;if(!(x)){fprintf(stderr,"%d %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{unsigned offset;unsigned char value;}Pair;
typedef struct{const unsigned char*data;size_t size;unsigned kind;const Pair*pairs;size_t pair_count;size_t result_size;unsigned actual_donor;}Fixture;
#include "fixtures.h"
static CohCostumeInputWorkspace workspace;static CohCostumeInput output,prior,expected,compare;
static unsigned char mutated[8192],digest_word[32];static unsigned fault;
static CohStatus digest(void*c,CohBytes b,uint8_t out[32]){SHA256_CTX s;(void)c;calls++;if(fault)return COH_IO;return SHA256_Init(&s)&&SHA256_Update(&s,b.data,b.size)&&SHA256_Final(out,&s)?COH_OK:COH_IO;}
static CohCostumeImportDigest provider={digest,NULL,0,16384};
static CohStatus parse(const unsigned char*b,size_t n,unsigned kind,size_t budget,size_t retained){return coh_costume_input_read((CohBytes){b,n},kind,digest_word,&provider,&workspace,&output,budget,retained);}
static void refuse(const unsigned char*b,size_t n,unsigned kind,size_t budget,size_t retained){prior=output;CHECK(parse(b,n,kind,budget,retained)!=COH_OK);CHECK(!memcmp(&prior,&output,sizeof(output)));}
int main(void){
 for(size_t f=0;f<sizeof(fixtures)/sizeof(fixtures[0]);f++){
  const Fixture*fixture=&fixtures[f];CHECK(fixture->result_size==sizeof(expected));memset(&expected,0,sizeof(expected));for(size_t i=0;i<fixture->pair_count;i++){CHECK(fixture->pairs[i].offset<sizeof(expected));((unsigned char*)&expected)[fixture->pairs[i].offset]=fixture->pairs[i].value;}
  CHECK(digest(NULL,(CohBytes){fixture->data,fixture->size},digest_word)==COH_OK);CHECK(parse(fixture->data,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0)==COH_OK);
  CHECK(output.end_byte==fixture->size&&output.dependency_count==1);CHECK(!output.original_callbacks_applied&&!output.authentic_stash_slots&&!output.actor_authority);CHECK(!memcmp(output.payload_sha256,digest_word,32));CHECK(output.dependencies[0].path[0]!=0);CHECK(output.schema_crc==(fixture->kind==1?0xcf27aba3u:0xf0095ef2u));
  compare=output;compare.schema_crc=compare.dependency_count=0;memset(compare.dependencies,0,sizeof(compare.dependencies));memset(compare.payload_sha256,0,sizeof(compare.payload_sha256));compare.end_byte=0;CHECK(!memcmp(&compare,&expected,sizeof(compare)));
  if(fixture->actual_donor){CHECK(output.kind==1?output.part_count==28:output.color_count==160);}
  for(size_t n=0;n<fixture->size;n++){CHECK(digest(NULL,(CohBytes){fixture->data,n},digest_word)==COH_OK);refuse(fixture->data,n,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);cuts++;}
  CHECK(fixture->size+1<=sizeof(mutated));memcpy(mutated,fixture->data,fixture->size);mutated[fixture->size]=0;CHECK(digest(NULL,(CohBytes){mutated,fixture->size+1},digest_word)==COH_OK);refuse(mutated,fixture->size+1,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);
  for(size_t n=0;n<fixture->size;n++){
   mutated[n]^=0x80;CHECK(digest(NULL,(CohBytes){mutated,fixture->size},digest_word)==COH_OK);prior=output;CohStatus status=parse(mutated,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);if(status!=COH_OK)CHECK(!memcmp(&output,&prior,sizeof(output)));else CHECK(output.end_byte==fixture->size&&!output.actor_authority&&!output.authentic_stash_slots);mutated[n]^=0x80;mutations++;
  }
  CHECK(digest(NULL,(CohBytes){fixture->data,fixture->size},digest_word)==COH_OK);digest_word[0]^=1;refuse(fixture->data,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);digest_word[0]^=1;
  size_t exact=COH_COSTUME_INPUT_STACK_RESERVE+provider.scratch_reserve+sizeof(provider)+sizeof(workspace)+sizeof(output)+32+fixture->size;
  calls=0;refuse(fixture->data,fixture->size,fixture->kind,exact-1,0);CHECK(!calls);CHECK(parse(fixture->data,fixture->size,fixture->kind,exact,0)==COH_OK);
  if(fixture->actual_donor&&fixture->kind==2){memcpy(mutated,fixture->data,fixture->size);uint32_t inf=0x7f800000;for(unsigned i=0;i<4;i++)mutated[fixture->size-8+i]=(unsigned char)(inf>>(i*8));CHECK(digest(NULL,(CohBytes){mutated,fixture->size},digest_word)==COH_OK);refuse(mutated,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);}
  if(fixture->actual_donor&&fixture->kind==1){memcpy(mutated,fixture->data,fixture->size);mutated[68]=30;mutated[69]=mutated[70]=mutated[71]=0;CHECK(digest(NULL,(CohBytes){mutated,fixture->size},digest_word)==COH_OK);refuse(mutated,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);}
  CHECK(digest(NULL,(CohBytes){fixture->data,fixture->size},digest_word)==COH_OK);
  calls=0;refuse(fixture->data,fixture->size,fixture->kind,100,0);CHECK(!calls);refuse(fixture->data,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,SIZE_MAX);CHECK(!calls);fault=1;refuse(fixture->data,fixture->size,fixture->kind,COH_COSTUME_INPUT_BUDGET_MAX,0);fault=0;
 }
 const Fixture*f=&fixtures[0];CHECK(digest(NULL,(CohBytes){f->data,f->size},digest_word)==COH_OK);refuse(f->data,f->size,3,COH_COSTUME_INPUT_BUDGET_MAX,0);
 prior=output;CHECK(coh_costume_input_read((CohBytes){f->data,f->size},1,digest_word,&provider,&workspace,&workspace.candidate,COH_COSTUME_INPUT_BUDGET_MAX,0)==COH_INVALID);CHECK(!memcmp(&prior,&output,sizeof(output)));
 CohCostumeImportDigest bad=provider;bad.context=&output;bad.context_bytes=sizeof(output);CHECK(coh_costume_input_read((CohBytes){f->data,f->size},1,digest_word,&bad,&workspace,&output,COH_COSTUME_INPUT_BUDGET_MAX,0)==COH_INVALID);
 CHECK(coh_costume_input_read((CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-3),10},1,digest_word,&provider,&workspace,&output,COH_COSTUME_INPUT_BUDGET_MAX,0)==COH_INVALID);
 printf("{\"passed\":true,\"checks\":%u,\"truncations\":%u,\"byte_mutations\":%u,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"actual_donor_body_parts\":28,\"actual_donor_colors\":160,\"actor_authority\":false}\n",checks,cuts,mutations,sizeof(output),sizeof(workspace));return 0;
}
