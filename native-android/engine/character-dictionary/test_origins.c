#include "coh_origins.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/sha.h>
static unsigned long long checks,cuts,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"origin check %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t size;unsigned count,refused;const char*text;const uint32_t*indices;}Fixture;
#include "fixtures.h"
typedef struct{unsigned calls;CohStatus status;}Digest;
static CohStatus digest(void*ctx,CohBytes bytes,uint8_t out[32]){Digest*d=ctx;d->calls++;SHA256(bytes.data,bytes.size,out);return d->status;}
static CohOriginDictionary out,before;static CohOriginWorkspace work;
static CohStatus parse(CohBytes input,const uint8_t hash[32],CohCostumeImportDigest*d,size_t budget,size_t retained){memset(&out,0xa5,sizeof(out));before=out;CohStatus s=coh_origins_read(input,1,hash,d,&out,&work,budget,retained);if(s!=COH_OK)CHECK(!memcmp(&out,&before,sizeof(out)));return s;}
int main(void){for(unsigned f=0;f<sizeof(fixtures)/sizeof(fixtures[0]);f++){const Fixture*v=&fixtures[f];uint8_t hash[32];SHA256(v->data,v->size,hash);Digest ctx={0,COH_OK};CohCostumeImportDigest d={digest,&ctx,sizeof(ctx),0};if(v->refused){CHECK(parse((CohBytes){v->data,v->size},hash,&d,COH_ORIGIN_RAM_MAX,0)==COH_LIMIT&&ctx.calls==0);continue;}CHECK(parse((CohBytes){v->data,v->size},hash,&d,COH_ORIGIN_RAM_MAX,0)==COH_OK&&ctx.calls==1);CHECK(out.count==v->count&&out.raw_schema_validated&&out.schema_crc_matched&&!out.runtime_generation&&!out.actor_authority);const char*text=v->text;
 for(unsigned i=0;i<v->count;i++)for(unsigned k=0;k<5;k++){CohOriginText t=out.entries[i].fields[k];CHECK(t.size==strlen(text)&&!memcmp(out.text+t.offset,text,t.size+1));text+=t.size+1;}
 for(unsigned i=0;i<v->count;i++){CohOriginText t=out.entries[i].fields[0];char lower[260],upper[260];for(unsigned j=0;j<t.size;j++){unsigned c=(unsigned char)out.text[t.offset+j];lower[j]=(char)(c>='A'&&c<='Z'?c+32:c);upper[j]=(char)(c>='a'&&c<='z'?c-32:c);}uint32_t idx=999;CHECK(coh_origins_find(&out,(CohBytes){(const uint8_t*)lower,t.size},&idx)==COH_OK&&idx==v->indices[2*i]);idx=999;CHECK(coh_origins_find(&out,(CohBytes){(const uint8_t*)upper,t.size},&idx)==COH_OK&&idx==v->indices[2*i+1]);}
 uint32_t idx=999;CHECK(coh_origins_find(&out,(CohBytes){(const uint8_t*)"unknown_missing_origin",22},&idx)==COH_NOT_FOUND&&idx==999);CHECK(coh_origins_find(&out,(CohBytes){(const uint8_t*)"\xff",1},&idx)==COH_UNSUPPORTED&&idx==999);CHECK(coh_origins_find(&out,(CohBytes){(const uint8_t*)"a",1},&out.count)==COH_INVALID);
 /* Copied names survive source retirement; no retained input pointer in owner. */
 CHECK(!memcmp(out.input_sha256,hash,32));
 for(size_t n=1;n<v->size;n++){ctx.calls=0;CHECK(parse((CohBytes){v->data,n},hash,&d,COH_ORIGIN_RAM_MAX,0)!=COH_OK&&ctx.calls==0);cuts++;}
 uint8_t*changed=malloc(v->size);CHECK(changed);for(size_t n=0;n<v->size;n++){memcpy(changed,v->data,v->size);changed[n]^=255;CHECK(parse((CohBytes){changed,v->size},hash,&d,COH_ORIGIN_RAM_MAX,0)!=COH_OK);mutations++;}free(changed);
 ctx.status=COH_CANCELLED;CHECK(parse((CohBytes){v->data,v->size},hash,&d,COH_ORIGIN_RAM_MAX,0)==COH_CANCELLED);ctx.status=COH_OK;CHECK(parse((CohBytes){v->data,v->size},hash,&d,1024,0)==COH_LIMIT);CHECK(parse((CohBytes){v->data,v->size},hash,&d,COH_ORIGIN_RAM_MAX,SIZE_MAX)==COH_LIMIT);d.scratch_reserve=SIZE_MAX;CHECK(parse((CohBytes){v->data,v->size},hash,&d,COH_ORIGIN_RAM_MAX,0)==COH_LIMIT);d.scratch_reserve=0;
 CHECK(coh_origins_read((CohBytes){v->data,v->size},1,hash,&d,&out,(CohOriginWorkspace*)&out,COH_ORIGIN_RAM_MAX,0)==COH_INVALID);d.context=&out;d.context_bytes=1;CHECK(coh_origins_read((CohBytes){v->data,v->size},1,hash,&d,&out,&work,COH_ORIGIN_RAM_MAX,0)==COH_INVALID);
 }
 printf("{\"checks\":%llu,\"fixtures\":%zu,\"cuts\":%llu,\"mutations\":%llu,\"runtime_generation\":false,\"actor_authority\":false}\n",checks,sizeof(fixtures)/sizeof(fixtures[0]),cuts,mutations);return 0;}
