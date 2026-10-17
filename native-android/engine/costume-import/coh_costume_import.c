#include "coh_costume_import.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "source_id.h"
typedef struct {const void *p;size_t n;} Span;
typedef struct {CohBytes b;size_t at;} Cursor;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:s.n==0;}
static int disjoint(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int nonzero(const uint8_t *p){unsigned i;uint8_t v=0;for(i=0;i<32;i++)v|=p[i];return v!=0;}
static int take(Cursor *c,size_t n,const uint8_t **p){if(n>c->b.size-c->at)return 0;*p=c->b.data+c->at;c->at+=n;return 1;}
static uint32_t word(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int sizeok(uint32_t n){return n>=2&&n<=COH_COSTUME_DICTIONARY_SLOT_MAX&&!(n&(n-1));}
static CohStatus slots(Cursor *c,uint32_t n,CohBytes *dst,uint32_t *count){
 uint32_t i;const uint8_t *p;*count=0;
 for(i=0;i<n;i++){
  uint32_t len;if(!take(c,2,&p))return COH_INVALID;len=(uint32_t)p[0]|((uint32_t)p[1]<<8);
  if(len==65535){if(dst)dst[i]=(CohBytes){NULL,0};continue;}
  if(len>259)return COH_LIMIT;
  if(!take(c,len,&p))return COH_INVALID;
  if(memchr(p,0,len))return COH_INVALID;
  if(dst)dst[i]=(CohBytes){p,len};
  (*count)++;
 }return COH_OK;
}
static CohStatus palette(Cursor *c,uint32_t n,uint32_t *keys,uint8_t *present,uint32_t *count){
 const uint8_t *p;uint32_t i;*count=0;
 for(i=0;i<n;i++){
  uint32_t value;if(!take(c,5,&p))return COH_INVALID;value=word(p+1);
  if(p[0]>1||(!p[0]&&value)||(p[0]&&!value))return COH_INVALID;
  if(keys)keys[i]=value;
  if(present)present[i]=p[0];
  *count+=p[0];
 }return COH_OK;
}
CohStatus coh_costume_import(CohBytes bytes,const CohCostumeImportPins *pins,
 const CohCostumeImportDigest *digest,CohEntCostumeDictionary **out,CohCostumeImportReceipt *receipt,size_t budget,size_t retained){
 Span spans[7];size_t i,j,temp,charged;const uint8_t *p;Cursor c;uint32_t header[10],counts[3],again[3];
 CohStatus status;CohCostumeImportReceipt result;CohEntCostumeDictionaryInput input;
 CohEntCostumeDictionary *candidate=NULL;void *storage;CohBytes *strings,*extra;uint32_t *keys;uint8_t *presence,hash[32];
 if(!bytes.data||bytes.size<176||bytes.size>COH_COSTUME_IMPORT_INPUT_MAX||!pins||!digest||!out||!receipt)return COH_INVALID;
 spans[0]=(Span){bytes.data,bytes.size};spans[1]=(Span){pins,sizeof(*pins)};spans[2]=(Span){digest,sizeof(*digest)};
 spans[3]=(Span){out,sizeof(*out)};spans[4]=(Span){receipt,sizeof(*receipt)};
 /* Validate direct spans before dereferencing callback context metadata. */
 for(i=0;i<5;i++){if(!valid(spans[i]))return COH_INVALID;for(j=0;j<i;j++)if(!disjoint(spans[i],spans[j]))return COH_INVALID;}
 if(*out||!digest->sha256||(!digest->context&&digest->context_bytes))return COH_STATE;
 spans[5]=(Span){digest->context,digest->context_bytes};if(!valid(spans[5]))return COH_INVALID;
 for(j=0;j<5;j++)if(!disjoint(spans[5],spans[j]))return COH_INVALID;
 if(!pins->generation||!pins->body_parts||pins->body_parts>=COH_COSTUME_PART_MAX||pins->body_types!=9)return COH_STATE;
 if(memcmp(pins->source_sha256,coh_costume_import_source_id,32)||!nonzero(pins->payload_sha256)||!nonzero(pins->inventory_sha256)||!nonzero(pins->profile_sha256)||!nonzero(pins->run_sha256))return COH_STATE;
 c=(Cursor){bytes,0};if(!take(&c,8,&p)||memcmp(p,"COHCDI1\0",8))return COH_INVALID;
 for(i=0;i<10;i++){if(!take(&c,4,&p))return COH_INVALID;header[i]=word(p);}
 if(header[0]!=1)return COH_UNSUPPORTED;
 if(header[1]!=pins->generation||header[2]!=pins->body_parts||header[3]!=pins->body_types)return COH_STATE;
 for(i=4;i<7;i++)if(!sizeok(header[i]))return COH_LIMIT;
 for(i=0;i<3;i++)if(header[7+i]>header[4+i])return COH_INVALID;
 if(!take(&c,32,&p)||memcmp(p,pins->source_sha256,32)||!take(&c,32,&p)||memcmp(p,pins->inventory_sha256,32)||!take(&c,32,&p)||memcmp(p,pins->profile_sha256,32)||!take(&c,32,&p)||memcmp(p,pins->run_sha256,32))return COH_STATE;
 status=slots(&c,header[4],NULL,&counts[0]);if(status!=COH_OK)return status;
 status=slots(&c,header[5],NULL,&counts[1]);if(status!=COH_OK)return status;
 status=palette(&c,header[6],NULL,NULL,&counts[2]);if(status!=COH_OK)return status;
 if(c.at!=bytes.size||memcmp(counts,header+7,sizeof(counts)))return COH_INVALID;
 temp=((size_t)header[4]+header[5])*sizeof(CohBytes)+(size_t)header[6]*5;
 if(!budget||budget>COH_COSTUME_IMPORT_BUDGET_MAX)return COH_LIMIT;
 charged=COH_COSTUME_IMPORT_STACK_RESERVE+COH_COSTUME_DICTIONARY_BYTES_MAX+temp;
 for(i=0;i<6;i++){if(spans[i].n>budget||charged>budget-spans[i].n)return COH_LIMIT;charged+=spans[i].n;}
 if(digest->scratch_reserve>budget||charged>budget-digest->scratch_reserve)return COH_LIMIT;
 charged+=digest->scratch_reserve;
 if(retained>budget||charged>budget-retained)return COH_LIMIT;
 charged+=retained;
 status=digest->sha256(digest->context,bytes,hash);if(status!=COH_OK)return status;
 if(memcmp(hash,pins->payload_sha256,32))return COH_STATE;
 storage=calloc(1,temp);if(!storage)return COH_LIMIT;
 strings=(CohBytes*)storage;extra=strings+header[4];keys=(uint32_t*)(extra+header[5]);presence=(uint8_t*)(keys+header[6]);
 c.at=176;status=slots(&c,header[4],strings,&again[0]);
 if(status==COH_OK)status=slots(&c,header[5],extra,&again[1]);
 if(status==COH_OK)status=palette(&c,header[6],keys,presence,&again[2]);
 if(status==COH_OK&&(c.at!=bytes.size||memcmp(counts,again,sizeof(counts))))status=COH_STATE;
 memset(&input,0,sizeof(input));input.generation=pins->generation;input.body_parts=pins->body_parts;input.body_types=pins->body_types;
 memcpy(input.manifest_sha256,hash,32);input.strings=(CohEntCostumeStringTable){header[4],strings};input.extra_strings=(CohEntCostumeStringTable){header[5],extra};input.palette_max_size=header[6];input.palette=keys;input.palette_present=presence;
 if(status==COH_OK)status=coh_ent_costume_dictionary_load(&candidate,&input,pins->generation,hash);
 free(storage);if(status!=COH_OK){coh_ent_costume_dictionary_free(candidate);return status;}
 memset(&result,0,sizeof(result));result.generation=pins->generation;result.body_parts=pins->body_parts;result.body_types=pins->body_types;
 memcpy(result.slots,header+4,sizeof(result.slots));memcpy(result.present,counts,sizeof(counts));
 result.input_bytes=bytes.size;result.temporary_bytes=temp;result.dictionary_bytes=coh_ent_costume_dictionary_bytes(candidate);result.charged_peak_bytes=charged;
 memcpy(result.payload_sha256,hash,32);memcpy(result.source_sha256,pins->source_sha256,32);memcpy(result.inventory_sha256,pins->inventory_sha256,32);memcpy(result.profile_sha256,pins->profile_sha256,32);memcpy(result.run_sha256,pins->run_sha256,32);
 *receipt=result;*out=candidate;return COH_OK;
}
