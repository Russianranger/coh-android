#include "coh_wr_tex_basic_lookup.h"
#include <string.h>
#include <stdint.h>
#define RESERVE 16384u
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
/* Exact same validated-header alias boundary as frozen dependency adapter.
 * This does not reinterpret header flags or mint new body/material authority. */
static int output_ok(const CohWrTexInputs*c,const CohWrTexInputsReport*r,const void*out,size_t n){
 if(!apart(c,r->owned_bytes,out,n))return 0;
 for(uint32_t i=0;i<r->texture_count;i++){CohWrTexHeaderInput h;if(coh_wr_tex_inputs_header(c,i,&h)!=COH_OK||!h.original_name||(uintptr_t)h.original_name<32)return 0;const uint8_t*body=(const uint8_t*)h.original_name-32;size_t bytes=word(body);if(!add(&bytes,word(body+4))||!apart(body,bytes,out,n))return 0;}
 for(uint32_t i=0;i<r->raw_trick_count;i++){CohWrRawTrickInput h;if(coh_wr_tex_inputs_raw_trick(c,i,&h)!=COH_OK||!apart(h.raw.data,h.raw.size,out,n))return 0;}return 1;
}
_Static_assert(2*sizeof(CohWrTexBasicLookup)+2*sizeof(CohWrTexHeaderInput)+sizeof(CohWrTexInputsReport)+4096<RESERVE,"bounded query control frames");
static CohStatus lookup(const CohWrTexInputs*c,const char*query,const CohWrTexBasicLookupLimits*limits,CohWrTexBasicLookup*out,int guarded){
 if(!c||!limits||!out||!apart(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 CohWrTexInputsReport source;CohStatus status=coh_wr_tex_inputs_report(c,&source);if(status!=COH_OK)return status;if(!output_ok(c,&source,out,sizeof(*out)))return COH_INVALID;
 size_t minimum=source.owned_bytes,total=limits->external_bytes;if(!add(&minimum,source.loader_reservation)||!add(&minimum,16384)||limits->external_bytes<minimum||!add(&total,RESERVE)||total>limits->aggregate_limit)return COH_LIMIT;
 CohWrTexBasicLookup result;memset(&result,0,sizeof(result));result.input_generation=source.input_generation;result.header_ordinal=UINT32_MAX;result.guarded_short_key_policy=(uint32_t)guarded;result.unresolved_client_semantics=1;result.aggregate_reserved_bytes=total;
 if(!query){result.branch=COH_WR_BASIC_NULL_REQUEST;*out=result;return COH_OK;}
 size_t n;for(n=0;n<=128;n++){unsigned x=(unsigned char)query[n];if(!x)break;if(x<32||x>126)return COH_UNSUPPORTED;}if(n>128)return COH_LIMIT;if(!apart(query,n+1,out,sizeof(*out)))return COH_INVALID;
 if(query[0]=='!'){query++;n--;}if(n>127)return COH_LIMIT;memcpy(result.key,query,n+1);
 /* Source TexFlags from tex.h, not ordinal/codec capability labels. */
 if(n<4)result.format_flags=1u<<5;
 else if(result.key[n-4]=='.'){const char*ext=result.key+n-3;if(!strcmp(ext,"tga"))result.format_flags=1u<<5;else if(!strcmp(ext,"jpg"))result.format_flags=1u<<13;else if(!strcmp(ext,"dds"))result.format_flags=1u<<6;result.key[n-4]=0;}
 else if(n<8){if(!guarded)return COH_UNSUPPORTED;}
 else if(result.key[n-8]=='.'){if(!strcmp(result.key+n-7,"texture"))result.format_flags=1u<<6;result.key[n-8]=0;}
 result.branch=COH_WR_BASIC_NAMESPACE_UNKNOWN;
 if(result.key[0]){CohWrTexHeaderInput header;status=coh_wr_tex_inputs_find_basic(c,result.key,&header);if(status==COH_OK){result.branch=COH_WR_BASIC_OBSERVED_HEADER;result.header_ordinal=header.input_ordinal;memcpy(result.header_sha256,header.sha256,32);}else if(status!=COH_NOT_FOUND)return status;}
 *out=result;return COH_OK;
}
CohStatus coh_wr_tex_basic_lookup(const CohWrTexInputs*c,const char*q,const CohWrTexBasicLookupLimits*l,CohWrTexBasicLookup*out){return lookup(c,q,l,out,0);}
CohStatus coh_wr_tex_basic_lookup_guarded(const CohWrTexInputs*c,const char*q,const CohWrTexBasicLookupLimits*l,CohWrTexBasicLookup*out){return lookup(c,q,l,out,1);}
