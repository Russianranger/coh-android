#include "coh_wr_tex_seed.h"
#include <stdint.h>
#include <string.h>
#define OWN_RESERVE 32768u
#define BASIC_RESERVE 16384u
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int equal(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static int prefix(const char*a,const char*b){for(;*b;a++,b++)if(!*a||fold((unsigned char)*a)!=fold((unsigned char)*b))return 0;return 1;}
static int valid(const char*s){return s&&*s&&*s!='%'&&!equal(s,"swappable")&&!equal(s,"none");}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
/* Frozen inputs expose original_name at protected header body+32. Recover only
 * the already admitted whole immutable span for alias checks, not new parsing. */
static int input_output(const CohWrTexInputs*c,const CohWrTexInputsReport*r,const void*out,size_t n){
 if(!apart(c,r->owned_bytes,out,n))return 0;
 for(uint32_t i=0;i<r->texture_count;i++){CohWrTexHeaderInput h;if(coh_wr_tex_inputs_header(c,i,&h)!=COH_OK||!h.original_name||(uintptr_t)h.original_name<32)return 0;const uint8_t*b=(const uint8_t*)h.original_name-32;size_t size=word(b);if(!add(&size,word(b+4))||!apart(b,size,out,n))return 0;}
 for(uint32_t i=0;i<r->raw_trick_count;i++){CohWrRawTrickInput t;if(coh_wr_tex_inputs_raw_trick(c,i,&t)!=COH_OK||!apart(t.raw.data,t.raw.size,out,n))return 0;}return 1;
}
_Static_assert(sizeof(CohWrTexSeed)+sizeof(CohWrTexOptView)+sizeof(CohWrTexBasicLookup)+sizeof(CohWrTexInputsReport)+4096<OWN_RESERVE,"bounded seed control frames");
/* Private view adapter is also exercised by explicitly synthetic branch
 * controls. The public entry accepts only the existing opaque record owner. */
static CohStatus project(const CohWrTexOptView*v,const void*record,size_t record_size,const CohWrTexInputs*inputs,const CohWrTexSeedLimits*l,CohCancel cancel,CohWrTexSeed*out){
 if(!apart(record,record_size,out,sizeof(*out))||!apart(l,sizeof(*l),out,sizeof(*out)))return COH_INVALID;
 if(l->guarded_short_key_policy>1)return COH_UNSUPPORTED;
 CohWrTexInputsReport ir;CohStatus status=coh_wr_tex_inputs_report(inputs,&ir);if(status!=COH_OK)return status;
 if(!input_output(inputs,&ir,out,sizeof(*out)))return COH_INVALID;
 if(ir.input_generation!=v->historical_input_generation)return COH_STATE;
 size_t minimum=record_size,total=l->external_bytes;if(!add(&minimum,ir.owned_bytes)||!add(&minimum,ir.loader_reservation)||!add(&minimum,16384)||l->external_bytes<minimum||!add(&total,OWN_RESERVE)||!add(&total,BASIC_RESERVE)||total>l->aggregate_limit)return COH_LIMIT;
 if(!v->original_CLIENT_postprocessed||!v->name||!*v->name||v->layers[COH_WR_TEXOPT_OLD_BASE].name)return COH_UNSUPPORTED;
 if(stop(cancel))return COH_CANCELLED;
 CohWrTexSeed result;memset(&result,0,sizeof(result));result.source_ordinal=v->source_ordinal;result.table_owner_ordinal=v->table_owner_ordinal;result.historical_input_generation=v->historical_input_generation;result.guarded_short_key_policy=l->guarded_short_key_policy;result.aggregate_reserved_bytes=total;memcpy(result.cache_sha256,v->cache_sha256,32);
 const char*base=v->layers[COH_WR_TEXOPT_BASE1].name;
 if(!base)result.classification=COH_WR_TEX_SEED_NO_BASE1;
 else if(prefix(base,v->name))result.classification=COH_WR_TEX_SEED_NAME_MATCHES_BASE1;
 else{
  result.classification=COH_WR_TEX_SEED_CREATE_CANDIDATE;
  const char*fallback[3]={v->fallback.base,v->fallback.blend,v->fallback.bumpmap};
  CohWrTexBasicLookupLimits nested={l->aggregate_limit,l->external_bytes+OWN_RESERVE};
  uint32_t slots=v->fallback.use_fallback?16u:13u;
  for(uint32_t i=0;i<slots;i++){
   const char*name=i<13?v->layers[i].name:fallback[i-13];if(!valid(name))continue;
   if(stop(cancel))return COH_CANCELLED;
   CohWrTexBasicLookup found;status=l->guarded_short_key_policy?coh_wr_tex_basic_lookup_guarded(inputs,name,&nested,&found):coh_wr_tex_basic_lookup(inputs,name,&nested,&found);if(status!=COH_OK)return status;
   if(found.branch!=COH_WR_BASIC_OBSERVED_HEADER)return COH_NOT_FOUND;
   CohWrTexSeedDependency*d=&result.dependencies[result.query_count++];d->source_slot=i;d->header_ordinal=found.header_ordinal;d->format_flags=found.format_flags;memcpy(d->key,found.key,sizeof(d->key));memcpy(d->header_sha256,found.header_sha256,32);
  }
 }
 if(stop(cancel))return COH_CANCELLED;
 *out=result;return COH_OK;
}
CohStatus coh_wr_tex_seed(const CohWrTexOptRecord*r,const CohWrTexInputs*i,const CohWrTexSeedLimits*l,CohCancel cancel,CohWrTexSeed*out){
 if(!r||!i||!l||!out)return COH_INVALID;
 CohWrTexOptView view;CohStatus status=coh_wr_texopt_record_view(r,&view);if(status!=COH_OK)return status;
 return project(&view,r,view.owned_bytes,i,l,cancel,out);
}
