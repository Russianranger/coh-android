#include "coh_source_material_plan.h"
#include <string.h>
#define RESERVE (32u*1024u)
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!n||a)&&(!m||b)&&n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);}
static CohStatus add(size_t*n,size_t v,size_t limit){if(*n>limit||v>limit-*n)return COH_LIMIT;*n+=v;return COH_OK;}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static CohStatus name(const char*s,CohSourceMaterialName*out){
 memset(out,0,sizeof(*out));if(!s)return COH_OK;
 out->present=1;for(size_t n=0;n<COH_SOURCE_MATERIAL_NAME;n++){unsigned c=(unsigned char)s[n];if(c&& (c<32||c>126))return COH_UNSUPPORTED;out->name[n]=(char)c;if(!c)return COH_OK;}return COH_LIMIT;
}
static int equal(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return !*a&&!*b;}
_Static_assert(sizeof(CohSourceMaterialPlan)+sizeof(CohWrTexOptView)+sizeof(CohSourceSealedEntry)+sizeof(CohSourceMeshPart)+8192<RESERVE,"material plan stack reserve");
CohStatus coh_source_material_plan(const CohSourceSealed*s,uint32_t slot,uint32_t part,
 const CohWrTexOptRecord*r,const CohSourceMaterialBudget*b,CohSourceMaterialPlan*out){
 if(!s||!r||!b||!out||!apart(b,sizeof(*b),out,sizeof(*out)))return COH_INVALID;
 CohSourceSealedReport sr;CohSourceSealedIdentity sid;CohWrTexOptView v;
 TRY(coh_source_sealed_report(s,&sr));TRY(coh_source_sealed_identity(s,&sid));TRY(coh_wr_texopt_record_view(r,&v));
 CohBytes spans[]={sid.join.catalog_bytes,sid.join.snapshot_bytes,sid.join.resource_bytes,{(const uint8_t*)s,sr.owned_bytes},{(const uint8_t*)r,v.owned_bytes}};
 for(unsigned i=0;i<sizeof(spans)/sizeof(*spans);i++)if(!apart(spans[i].data,spans[i].size,b,sizeof(*b))||!apart(spans[i].data,spans[i].size,out,sizeof(*out)))return COH_INVALID;
 if(!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
 size_t total=b->retained_bytes;TRY(add(&total,sr.owned_bytes,b->aggregate_limit));TRY(add(&total,sr.shared_source_bytes,b->aggregate_limit));TRY(add(&total,v.owned_bytes,b->aggregate_limit));TRY(add(&total,sizeof(*b),b->aggregate_limit));TRY(add(&total,sizeof(*out),b->aggregate_limit));TRY(add(&total,RESERVE,b->aggregate_limit));
 if(!v.original_CLIENT_postprocessed||!v.is_table_owner||v.source_ordinal!=v.table_owner_ordinal)return COH_STATE;
 CohSourceSealedEntry e;CohSourceMeshPart p;TRY(coh_source_sealed_entry(s,slot,&e));TRY(coh_source_sealed_part(s,slot,part,&p));
 if(!e.unscaled_base_uv||!e.material_binding_required||!e.parts||p.index_count%3u)return COH_STATE;
 CohSourceMaterialPlan value;memset(&value,0,sizeof(value));CohSourceMaterialName key={0},selected={0};
 TRY(name(p.source_material.texture_name,&key));TRY(name(v.name,&selected));
 if(!key.present||!*key.name||!selected.present||!*selected.name||!equal(key.name,selected.name))return COH_NOT_FOUND;
 value.source_ordinal=e.source_ordinal;value.source_part=part;value.texture_index=p.source_material.texture_id;value.triangles=p.index_count/3u;
 value.graph_generation=e.graph_generation;value.catalog_generation=e.catalog_generation;value.source_asset_generation=e.binding.asset_generation;value.historical_client_generation=v.historical_input_generation;value.texopt_ordinal=v.source_ordinal;value.table_owner_ordinal=v.table_owner_ordinal;
 memcpy(value.partition_key,key.name,sizeof(value.partition_key));memcpy(value.texopt_key,selected.name,sizeof(value.texopt_key));memcpy(value.resources_sha256,e.resources_sha256,32);memcpy(value.resource_record_sha256,e.resource_record_sha256,32);memcpy(value.texopt_cache_sha256,v.cache_sha256,32);
 TRY(name(v.source_file,&value.texopt_source_file));value.texopt_source_age=v.source_age;value.texopt_flags=v.flags;value.texopt_blend=v.blend_mode;
 for(unsigned i=0;i<13;i++)TRY(name(v.layers[i].name,&value.slots[i]));
 if(v.fallback.use_fallback){TRY(name(v.fallback.base,&value.slots[13]));TRY(name(v.fallback.blend,&value.slots[14]));TRY(name(v.fallback.bumpmap,&value.slots[15]));}
 value.fallback_enabled=v.fallback.use_fallback;value.original_CLIENT_postprocessed=v.original_CLIENT_postprocessed;
 value.sealed_owned_bytes=sr.owned_bytes;value.shared_source_bytes=sr.shared_source_bytes;value.record_owned_bytes=v.owned_bytes;value.aggregate_reserved_bytes=total;value.preparation_reserve=RESERVE;
 *out=value;return COH_OK;
}
