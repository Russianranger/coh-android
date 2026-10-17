#include "coh_wr_tex_permutation.h"
#include <string.h>
#include <stdint.h>
#define OWN_RESERVE 32768u
#define BASIC_RESERVE 16384u
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int output_ok(const CohWrTexInputs*c,const CohWrTexInputsReport*r,const void*out,size_t n){
 if(!apart(c,r->owned_bytes,out,n))return 0;
 for(uint32_t i=0;i<r->texture_count;i++){CohWrTexHeaderInput h;if(coh_wr_tex_inputs_header(c,i,&h)!=COH_OK||!h.original_name||(uintptr_t)h.original_name<32)return 0;const uint8_t*b=(const uint8_t*)h.original_name-32;size_t size=word(b);if(!add(&size,word(b+4))||!apart(b,size,out,n))return 0;}
 for(uint32_t i=0;i<r->raw_trick_count;i++){CohWrRawTrickInput h;if(coh_wr_tex_inputs_raw_trick(c,i,&h)!=COH_OK||!apart(h.raw.data,h.raw.size,out,n))return 0;}return 1;
}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int equal(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return!*a&&!*b;}
static CohStatus length(const char*s,size_t cap,int tabs,size_t*n){if(!s)return COH_INVALID;for(size_t i=0;i<=cap;i++){unsigned c=(unsigned char)s[i];if(!c){*n=i;return COH_OK;}if((c<32||c>126)&&!(tabs&&c==9))return COH_UNSUPPORTED;}return COH_LIMIT;}
static int delimiter(unsigned c){return c==';'||c==','||c==' '||c=='\t';}
static CohStatus query(const CohWrTexInputs*c,const char*key,const CohWrTexBasicLookupLimits*l,int guarded,CohWrTexBasicLookup*out){return guarded?coh_wr_tex_basic_lookup_guarded(c,key,l,out):coh_wr_tex_basic_lookup(c,key,l,out);}
/* texCheckSwapList ignores texFixName's format return and does NOT strip!. */
static CohStatus normalize(const char*raw,int guarded,char key[128]){size_t n=strlen(raw);memset(key,0,128);memcpy(key,raw,n+1);if(n>=4){if(key[n-4]=='.')key[n-4]=0;else if(n<8){if(!guarded)return COH_UNSUPPORTED;}else if(key[n-8]=='.')key[n-8]=0;}return COH_OK;}

_Static_assert(2*sizeof(CohWrTexPermutationPlan)+4*sizeof(CohWrTexHeaderInput)+2*sizeof(CohWrTexBasicLookup)+4096<OWN_RESERVE,"bounded nested permutation control storage");
CohStatus coh_wr_tex_permutation_plan(const CohWrTexInputs*c,const CohWrTexPermutationInput*q,const CohWrTexPermutationLimits*limits,CohCancel cancel,CohWrTexPermutationPlan*out){
 if(!c||!q||!limits||!out||!apart(q,sizeof(*q),out,sizeof(*out))||!apart(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 if(q->guarded_short_key_policy>1)return COH_INVALID;
 if(q->initial_load_state)return COH_UNSUPPORTED;
 if(q->swap_count>COH_WR_TEX_PERMUTATION_SWAPS_MAX)return COH_LIMIT;
 if((q->swap_count&&!q->swaps)||!apart(q->swaps,(size_t)q->swap_count*sizeof(*q->swaps),out,sizeof(*out)))return COH_INVALID;
 CohWrTexInputsReport report;CohStatus status=coh_wr_tex_inputs_report(c,&report);if(status!=COH_OK)return status;if(!output_ok(c,&report,out,sizeof(*out)))return COH_INVALID;
 CohWrTexHeaderInput base;status=coh_wr_tex_inputs_header(c,q->base_header_ordinal,&base);if(status!=COH_OK)return status;
 size_t bytes=sizeof(*q),search_size;if(!add(&bytes,(size_t)q->swap_count*sizeof(*q->swaps)))return COH_LIMIT;status=length(q->search_path,1024,1,&search_size);if(status!=COH_OK)return status;if(!apart(q->search_path,search_size+1,out,sizeof(*out)))return COH_INVALID;if(!add(&bytes,search_size+1))return COH_LIMIT;
 for(uint32_t i=0;i<q->swap_count;i++){const char*names[]={q->swaps[i].source,q->swaps[i].destination};for(unsigned j=0;j<2;j++){size_t n;status=length(names[j],127,0,&n);if(status!=COH_OK)return status;if(!apart(names[j],n+1,out,sizeof(*out)))return COH_INVALID;if(!add(&bytes,n+1))return COH_LIMIT;}}
 size_t minimum=report.owned_bytes,total=limits->external_bytes,nested_external=limits->external_bytes;if(!add(&minimum,report.loader_reservation)||!add(&minimum,16384)||limits->external_bytes<minimum||!add(&nested_external,bytes)||!add(&nested_external,OWN_RESERVE)||!add(&total,bytes)||!add(&total,OWN_RESERVE+BASIC_RESERVE)||total>limits->aggregate_limit)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 CohWrTexBasicLookupLimits nested={limits->aggregate_limit,nested_external};CohWrTexPermutationPlan result;memset(&result,0,sizeof(result));result.input_generation=report.input_generation;result.configuration_label=q->configuration_label;result.base_header_ordinal=q->base_header_ordinal;result.scene_swap_index=UINT32_MAX;result.after_scene_header_ordinal=q->base_header_ordinal;result.candidate_header_ordinal=q->base_header_ordinal;result.frontier_locale_index=UINT32_MAX;result.guarded_short_key_policy=q->guarded_short_key_policy;result.unresolved_client_semantics=1;result.input_bytes=bytes;result.aggregate_reserved_bytes=total;
 for(size_t p=0;p<search_size;){if(stop(cancel))return COH_CANCELLED;while(p<search_size&&delimiter((unsigned char)q->search_path[p]))p++;if(p==search_size)break;size_t start=p;while(p<search_size&&!delimiter((unsigned char)q->search_path[p]))p++;while(start<p&&q->search_path[start]=='#')start++;size_t n=p-start;if(n>127||result.locale_count==COH_WR_TEX_PERMUTATION_LOCALES_MAX)return COH_LIMIT;memcpy(result.locale_keys[result.locale_count],q->search_path+start,n);result.locale_keys[result.locale_count++][n]=0;}
 for(uint32_t i=0;i<q->swap_count;i++){if(stop(cancel))return COH_CANCELLED;char source[128],destination[128];status=normalize(q->swaps[i].source,(int)q->guarded_short_key_policy,source);if(status!=COH_OK)return status;status=normalize(q->swaps[i].destination,(int)q->guarded_short_key_policy,destination);if(status!=COH_OK)return status;if(equal(base.basic_key,source)){result.scene_swap_index=i;memcpy(result.scene_destination,destination,sizeof(destination));}}
 if(result.scene_swap_index!=UINT32_MAX){if(stop(cancel))return COH_CANCELLED;status=query(c,result.scene_destination,&nested,(int)q->guarded_short_key_policy,result.queries);if(status!=COH_OK)return status;result.query_count=1;if(result.queries[0].branch!=COH_WR_BASIC_OBSERVED_HEADER){result.frontier=COH_WR_TEX_PERMUTATION_SCENE_NAMESPACE_UNKNOWN;result.after_scene_header_ordinal=result.candidate_header_ordinal=UINT32_MAX;goto done;}result.after_scene_header_ordinal=result.candidate_header_ordinal=result.queries[0].header_ordinal;}
 if(result.locale_count){CohWrTexHeaderInput actual;status=coh_wr_tex_inputs_header(c,result.after_scene_header_ordinal,&actual);if(status!=COH_OK)return status;size_t a=strlen(actual.basic_key),b=strlen(result.locale_keys[0]);if(a+1+b>127)return COH_LIMIT;char key[128];memcpy(key,actual.basic_key,a);key[a]='#';memcpy(key+a+1,result.locale_keys[0],b+1);if(stop(cancel))return COH_CANCELLED;CohWrTexBasicLookup*lookup=result.queries+result.query_count;status=query(c,key,&nested,(int)q->guarded_short_key_policy,lookup);if(status!=COH_OK)return status;result.query_count++;result.frontier_locale_index=0;result.candidate_header_ordinal=UINT32_MAX;if(lookup->branch==COH_WR_BASIC_OBSERVED_HEADER){result.frontier=COH_WR_TEX_PERMUTATION_WHITE_IDENTITY_UNKNOWN;}else result.frontier=COH_WR_TEX_PERMUTATION_LOCALE_NAMESPACE_UNKNOWN;}
 done:if(stop(cancel))return COH_CANCELLED;*out=result;return COH_OK;
}
