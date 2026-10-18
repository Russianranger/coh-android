#include "coh_bd_resources.h"
#include <openssl/evp.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const uint8_t*body;size_t size;CohStatus status;uint8_t projection[32];} Fixture;
#include "resource_fixtures.h"
typedef struct {unsigned calls,target,digests;CohStatus error;} Context;
static int cancel(void*v){Context*c=v;c->calls++;return c->target&&c->calls==c->target;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){Context*c=v;c->digests++;if(c->error)return c->error;SHA256(b.data,b.size,out);return COH_OK;}
static void add_word(EVP_MD_CTX*c,uint32_t n){uint8_t b[4]={(uint8_t)n,(uint8_t)(n>>8),(uint8_t)(n>>16),(uint8_t)(n>>24)};CHECK(EVP_DigestUpdate(c,b,4)==1);}
static void projection(const CohBdResources*d,uint8_t out[32]){EVP_MD_CTX*c=EVP_MD_CTX_new();CHECK(c&&EVP_DigestInit_ex(c,EVP_sha256(),NULL)==1);add_word(c,d->count);for(unsigned i=0;i<d->count;i++){const CohBdResourceRow*r=&d->rows[i];add_word(c,(uint32_t)r->surface);add_word(c,r->mounted);add_word(c,r->animated);for(unsigned j=0;j<7;j++){CohBdResourceText t=j?r->groups[j-1]:r->name;add_word(c,t.size);CHECK(EVP_DigestUpdate(c,d->text+t.offset,t.size)==1);}}unsigned n=0;CHECK(EVP_DigestFinal_ex(c,out,&n)==1&&n==32);EVP_MD_CTX_free(c);}
int main(void){
 CohBdResources*out=malloc(sizeof(*out));CohBdResourcesWorkspace*w=malloc(sizeof(*w));uint8_t*saved=malloc(sizeof(*out));CHECK(out&&w&&saved);
 CohBdResourcePins pins={{0},UINT64_C(0xBD6001)};Context dc={0},cc={0};CohCostumeImportDigest dp={digest,&dc,sizeof(dc),4096};CohBdResourceControl cp={{cancel,&cc},sizeof(cc),2048};unsigned authentic_rows=0,successes=0;size_t minimum=0;
 for(unsigned f=0;f<sizeof(fixtures)/sizeof(*fixtures);f++){
  const Fixture*t=&fixtures[f];CohBytes b={t->body,t->size};SHA256(b.data,b.size,pins.expected_sha256);cc=(Context){0};dc=(Context){0};memset(out,0x5d,sizeof(*out));memcpy(saved,out,sizeof(*out));CohStatus status=coh_bd_resources_read(b,&pins,&dp,&cp,out,w,COH_BD_RESOURCE_RAM_MAX,0);CHECK(status==t->status);
  if(status!=COH_OK){CHECK(!memcmp(saved,out,sizeof(*out)));continue;}
  successes++;CHECK(out->complete==1&&out->provenance==pins.provenance&&!out->runtime_generation&&!out->actor_authority);CHECK(!memcmp(out->sha256,pins.expected_sha256,32));uint8_t got[32];projection(out,got);CHECK(!memcmp(got,t->projection,32));
  if(!f)authentic_rows=out->count;
  for(unsigned i=0;i<out->count;i++)for(unsigned k=0;k<6;k++){CohBdResourceText text=out->rows[i].groups[k];CohBytes value={(const uint8_t*)"unchanged",9},before=value;CohStatus s=coh_bd_resources_group(out,i,(CohBdGroupKind)k,&value);CHECK(s==(text.size?COH_OK:COH_NOT_FOUND));if(text.size)CHECK(value.size==text.size&&value.data==(const uint8_t*)out->text+text.offset);else CHECK(!memcmp(&value,&before,sizeof(value)));}
  if(f==1){/* Focus policy/lifetime controls on one small complete valid body. */
   unsigned polls=cc.calls;CHECK(polls>10&&dc.digests==1);memcpy(saved,out,sizeof(*out));minimum=COH_BD_RESOURCE_STACK_RESERVE+sizeof(pins)+sizeof(dp)+sizeof(cp)+sizeof(*out)+sizeof(*w)+b.size+sizeof(dc)+sizeof(cc)+dp.scratch_reserve+cp.scratch_reserve;
   cc=(Context){0};dc=(Context){0};CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum-1,0)==COH_LIMIT);CHECK(!cc.calls&&!dc.digests&&!memcmp(saved,out,sizeof(*out)));
   CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==COH_OK);CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum+4096,4096)==COH_OK);CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum+4096,4097)==COH_LIMIT);
   unsigned stages[]={1,2,polls/2,polls-1,polls};for(unsigned j=0;j<sizeof(stages)/sizeof(*stages);j++){cc=(Context){0,stages[j],0,0};CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==COH_CANCELLED);CHECK(!memcmp(saved,out,sizeof(*out)));}cc=(Context){0};
   pins.expected_sha256[0]^=1;CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==COH_STATE);CHECK(!memcmp(saved,out,sizeof(*out)));pins.expected_sha256[0]^=1;
   dc.error=COH_IO;CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==COH_IO);CHECK(!memcmp(saved,out,sizeof(*out)));dc.error=COH_OK;
   for(unsigned error=COH_INVALID;error<=COH_STATE;error++){dc.error=(CohStatus)error;CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==(CohStatus)error);CHECK(!memcmp(saved,out,sizeof(*out)));}
   int invalid_statuses[]={-1,8,2147483647};for(unsigned j=0;j<sizeof(invalid_statuses)/sizeof(*invalid_statuses);j++){dc.error=(CohStatus)invalid_statuses[j];CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,w,minimum,0)==COH_INVALID);CHECK(!memcmp(saved,out,sizeof(*out)));}dc.error=COH_OK;
   cc=(Context){0};dc=(Context){0};CHECK(coh_bd_resources_read(b,&pins,&dp,&cp,out,(CohBdResourcesWorkspace*)out,minimum,0)==COH_INVALID);CHECK(!cc.calls&&!dc.digests&&!memcmp(saved,out,sizeof(*out)));
   CohBytes alias={(const uint8_t*)out,16};CHECK(coh_bd_resources_read(alias,&pins,&dp,&cp,out,w,minimum,0)==COH_INVALID);CHECK(!memcmp(saved,out,sizeof(*out)));
   /* Declared short bodies are sampled at header, record and final boundaries. */
   size_t cuts[]={0,1,7,11,12,15,23,31,35,39,43,b.size/2,b.size-1};for(unsigned j=0;j<sizeof(cuts)/sizeof(*cuts);j++){CohBytes cut={b.data,cuts[j]};CHECK(coh_bd_resources_read(cut,&pins,&dp,&cp,out,w,minimum,0)!=COH_OK);CHECK(!memcmp(saved,out,sizeof(*out)));}
   uint8_t*copy=malloc(b.size);CHECK(copy);memcpy(copy,b.data,b.size);CHECK(coh_bd_resources_read((CohBytes){copy,b.size},&pins,&dp,&cp,out,w,minimum,0)==COH_OK);memset(copy,0,b.size);free(copy);projection(out,got);CHECK(!memcmp(got,t->projection,32));
   CohBytes value={(const uint8_t*)"saved",5},prior=value;CHECK(coh_bd_resources_group(out,out->count,COH_BD_GROUP,&value)==COH_NOT_FOUND&&!memcmp(&value,&prior,sizeof(value)));CHECK(coh_bd_resources_group(out,0,(CohBdGroupKind)99,&value)==COH_INVALID&&!memcmp(&value,&prior,sizeof(value)));CHECK(coh_bd_resources_group(out,0,COH_BD_GROUP,(CohBytes*)out)==COH_INVALID);out->runtime_generation=1;CHECK(coh_bd_resources_group(out,0,COH_BD_GROUP,&value)==COH_STATE&&!memcmp(&value,&prior,sizeof(value)));out->runtime_generation=0;
  }
 }
 free(saved);free(w);free(out);printf("{\"checks\":%u,\"fixtures\":%u,\"successes\":%u,\"authentic_rows\":%u,\"owner_bytes\":%zu,\"workspace_bytes\":%zu,\"small_fixture_minimum_budget\":%zu,\"world_authority\":false}\n",checks,(unsigned)(sizeof(fixtures)/sizeof(*fixtures)),successes,authentic_rows,sizeof(CohBdResources),sizeof(CohBdResourcesWorkspace),minimum);return 0;
}
