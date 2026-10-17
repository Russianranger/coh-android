#include "coh_attribute_dictionary.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long checks,cuts,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"attribute dictionary %u: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{unsigned category,row,count,type,style,key,offset,show,lookup;const char*category_name,*name,*display,*tooltip;}Expected;
typedef struct{const unsigned char*bytes;size_t size;const Expected*rows;unsigned row_count,category_count,scenario;}Fixture;
#include "dictionary-fixtures.h"
typedef struct{CohStatus status;unsigned calls;}DigestOwner;
static CohStatus digest(void*opaque,CohBytes input,uint8_t out[32]){DigestOwner*o=opaque;o->calls++;if(o->status)return o->status;SHA256(input.data,input.size,out);return COH_OK;}
typedef struct{CohAttributeDictionary out;CohAttributeDictionaryWorkspace work;DigestOwner owner;CohCostumeImportDigest digest;uint8_t hash[32];}State;
static int eq(CohBytes v,const char*s){return v.size==strlen(s)&&!memcmp(v.data,s,v.size);}
static void init(State*s,CohBytes input){memset(s,0,sizeof(*s));s->digest=(CohCostumeImportDigest){digest,&s->owner,sizeof(s->owner),0};SHA256(input.data,input.size,s->hash);memset(&s->out,0xa5,sizeof(s->out));}
static CohStatus parse(State*s,CohBytes input,size_t budget,size_t retained){CohAttributeDictionary prior=s->out;CohStatus status=coh_attribute_dictionary_read(input,123,s->hash,&s->digest,&s->out,&s->work,budget,retained);if(status!=COH_OK)CHECK(!memcmp(&prior,&s->out,sizeof(prior)));else CHECK(s->out.raw_schema_validated&&s->out.schema_crc_matched&&!s->out.runtime_cache_branch_verified&&!s->out.current_server_generation&&!s->out.actor_authority);return status;}
int main(void){State*s=malloc(sizeof(*s));CHECK(s);
 for(unsigned i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohBytes input={f->bytes,f->size};init(s,input);CHECK(parse(s,input,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_OK);CHECK(s->out.input.data==input.data&&s->out.input.size==input.size&&s->out.input_lease_token==123&&s->out.row_count==f->row_count&&s->out.category_count==f->category_count);
  for(unsigned j=0;j<f->row_count;j++){const Expected*e=&f->rows[j];CohAttributeDescription*a=&s->out.ordered[j];CHECK(a->category==e->category&&a->row==e->row&&a->category_rows==e->count&&a->type==e->type&&a->style==e->style&&a->key==e->key&&a->offset==e->offset&&a->show_base_word==e->show&&a->lookup_key==e->lookup);CHECK(eq(a->category_name,e->category_name)&&eq(a->name,e->name)&&eq(a->display_name,e->display)&&eq(a->tooltip,e->tooltip));}
  for(unsigned cut=1;cut<f->size;cut++){CohBytes part={input.data,cut};init(s,part);CHECK(parse(s,part,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)!=COH_OK&&s->owner.calls==0);cuts++;}
  if(!i){
   for(unsigned at=0;at<f->size;at++){unsigned char*copy=malloc(f->size);CHECK(copy);memcpy(copy,input.data,f->size);copy[at]^=0x81;CohBytes part={copy,f->size};init(s,part);(void)parse(s,part,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0);free(copy);mutations++;}
   for(unsigned status=COH_INVALID;status<=COH_STATE;status++){init(s,input);s->owner.status=(CohStatus)status;CHECK(parse(s,input,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==(CohStatus)status&&s->owner.calls==1);}
   init(s,input);s->hash[0]^=1;CHECK(parse(s,input,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_STATE);init(s,input);CHECK(parse(s,input,1,0)==COH_LIMIT&&s->owner.calls==0);init(s,input);CHECK(parse(s,input,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,SIZE_MAX)==COH_LIMIT&&s->owner.calls==0);
   init(s,input);CHECK(coh_attribute_dictionary_read(input,0,s->hash,&s->digest,&s->out,&s->work,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_INVALID);init(s,input);s->digest.context=&s->out;CHECK(coh_attribute_dictionary_read(input,123,s->hash,&s->digest,&s->out,&s->work,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_INVALID);init(s,input);CHECK(coh_attribute_dictionary_read(input,123,s->hash,&s->digest,&s->out,(CohAttributeDictionaryWorkspace*)&s->out,COH_ATTRIBUTE_DICTIONARY_RAM_MAX,0)==COH_INVALID);
  }
 }
 free(s);printf("{\"checks\":%lu,\"fixtures\":%zu,\"truncations\":%lu,\"mutations\":%lu,\"runtime_generation\":false,\"actor_authority\":false}\n",checks,sizeof(fixtures)/sizeof(fixtures[0]),cuts,mutations);return 0;}
