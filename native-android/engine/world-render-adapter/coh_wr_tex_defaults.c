#include "coh_wr_tex_defaults.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

struct CohWrTexDefaults {
 CohWrTexNamespace *source;
 CohWrTexDefaultsReport report;
 uint32_t rows[COH_WR_TEX_DEFAULT_COUNT];
 const CohWrTexNamespaceBody *leases[COH_WR_TEX_DEFAULT_COUNT];
};
static const char *const keys[COH_WR_TEX_DEFAULT_COUNT]={
 "white","grey","invisible","black","dummy_bump",
 "dummy_dynamic_cubemap_face0","buildingLightPattern"
};
static int disjoint(const void*a,size_t n,const void*b,size_t m){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 return n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);
}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int stopped(CohCancel c){return c.poll&&c.poll(c.context);}
static int basic_separate(const CohWrTexNamespaceBasic*b,const void*out,size_t n){
 return disjoint(b->asset.path,strlen(b->asset.path)+1,out,n)&&
  disjoint(b->original_name,strlen(b->original_name)+1,out,n)&&
  disjoint(b->directory,strlen(b->directory)+1,out,n)&&
  disjoint(b->basic_key,strlen(b->basic_key)+1,out,n)&&
  disjoint(b->cached_mips.data,b->cached_mips.size,out,n);
}
static CohStatus release_all(CohWrTexDefaults*r){
 CohStatus first=COH_OK;
 for(uint32_t i=0;i<COH_WR_TEX_DEFAULT_COUNT;i++)if(r->leases[i]){
  CohStatus s=coh_wr_tex_namespace_release(r->source,&r->leases[i]);
  if(first==COH_OK&&s!=COH_OK)first=s;
 }
 return first;
}
CohStatus coh_wr_tex_defaults_build(CohWrTexNamespace*source,const CohWrTexDefaultsProfile*profile,const CohWrTexDefaultsLimits*limits,CohCancel cancel,CohWrTexDefaults**out){
 if(!source||!profile||!limits||!out||
  !disjoint(profile,sizeof(*profile),out,sizeof(*out))||
  !disjoint(limits,sizeof(*limits),out,sizeof(*out))||*out)return COH_INVALID;
 CohWrTexDefaultsProfile p=*profile;CohWrTexDefaultsLimits bound=*limits;
 if(p.cold_initial!=1||p.guarded_short_keys!=1)return COH_UNSUPPORTED;
 if(bound.owned_limit<sizeof(CohWrTexDefaults)||!bound.aggregate_limit)return COH_LIMIT;
 CohWrTexNamespaceReport ns;CohStatus status=coh_wr_tex_namespace_report(source,&ns);
 if(status!=COH_OK)return status;
 if(bound.external_bytes<ns.aggregate_reserved_bytes)return COH_LIMIT;
 size_t aggregate=bound.external_bytes;
 if(!add(&aggregate,sizeof(CohWrTexDefaults))||
  !add(&aggregate,sizeof(*profile)+sizeof(*limits)+sizeof(*out)+sizeof(cancel))||
  !add(&aggregate,COH_WR_TEX_DEFAULT_PREPARATION_RESERVE)||aggregate>bound.aggregate_limit)return COH_LIMIT;
 /* Check every public source span before any callback. Unknown opaque storage
  * is explicitly caller-disjoint; no private namespace layout is imported. */
 for(uint32_t i=0;i<ns.basic_rows;i++){
  CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_basic(source,i,&basic);
  if(status!=COH_OK)return status;
  if(!basic_separate(&basic,out,sizeof(*out)))return COH_INVALID;
 }
 CohWrTexDefaults*r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;
 r->source=source;r->report.source_input_generation=ns.source_input_generation;
 r->report.basic_rows=ns.basic_rows;r->report.cold_initial=1;
 r->report.guarded_short_keys=1;r->report.unresolved_client_semantics=1;
 r->report.owned_bytes=sizeof(*r);r->report.aggregate_reserved_bytes=aggregate;
 for(uint32_t i=0;i<COH_WR_TEX_DEFAULT_COUNT;i++){
  CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_find(source,keys[i],&basic);
  if(status==COH_NOT_FOUND){r->rows[i]=UINT32_MAX;continue;}
  if(status!=COH_OK)goto fail;
  r->rows[i]=basic.row;
  /* Acquire provides the first cancellation poll only while the source is
   * busy; later polls are also protected by real held body leases. */
  status=coh_wr_tex_namespace_acquire(source,basic.row,cancel,&r->leases[i]);
  if(status!=COH_OK)goto fail;
  CohBytes body;status=coh_wr_tex_namespace_body(r->leases[i],&body);
  if(status!=COH_OK)goto fail;
  if(!disjoint(body.data,body.size,out,sizeof(*out))){status=COH_INVALID;goto fail;}
  r->report.selected_mask|=1u<<i;r->report.selected_count++;
 }
 if((r->report.selected_mask&COH_WR_TEX_DEFAULT_REQUIRED_MASK)!=COH_WR_TEX_DEFAULT_REQUIRED_MASK){status=COH_NOT_FOUND;goto fail;}
 if(stopped(cancel)){status=COH_CANCELLED;goto fail;}
 *out=r;return COH_OK;
fail:
 /* With a valid same-thread immutable source, release has no callback and all
  * these handles were acquired here: it cannot refuse. Public destruction below
  * retains ownership on refusal, including a namespace-busy callback attempt. */
 {CohStatus released=release_all(r);assert(released==COH_OK);(void)released;}
 free(r);return status;
}
static CohStatus output_ok(const CohWrTexDefaults*r,const void*out,size_t n){
 if(!r||!out||!disjoint(r,sizeof(*r),out,n))return COH_INVALID;
 for(uint32_t i=0;i<r->report.basic_rows;i++){
  CohWrTexNamespaceBasic basic;CohStatus s=coh_wr_tex_namespace_basic(r->source,i,&basic);
  if(s!=COH_OK)return s;
  if(!basic_separate(&basic,out,n))return COH_INVALID;
 }
 for(uint32_t i=0;i<COH_WR_TEX_DEFAULT_COUNT;i++)if(r->leases[i]){
  CohBytes body;CohStatus s=coh_wr_tex_namespace_body(r->leases[i],&body);
  if(s!=COH_OK)return s;
  if(!disjoint(body.data,body.size,out,n))return COH_INVALID;
 }
 return COH_OK;
}
CohStatus coh_wr_tex_defaults_report(const CohWrTexDefaults*r,CohWrTexDefaultsReport*out){
 CohStatus s=output_ok(r,out,sizeof(*out));if(s!=COH_OK)return s;
 *out=r->report;return COH_OK;
}
CohStatus coh_wr_tex_defaults_basic(const CohWrTexDefaults*r,uint32_t row,CohWrTexDefaultsBasic*out){
 CohStatus s=output_ok(r,out,sizeof(*out));if(s!=COH_OK)return s;
 CohWrTexDefaultsBasic value;memset(&value,0,sizeof(value));
 s=coh_wr_tex_namespace_basic(r->source,row,&value.source);if(s!=COH_OK)return s;
 value.effective_basic_flags=value.source.initial_basic_flags;
 if((r->report.selected_mask&(1u<<COH_WR_TEX_DEFAULT_INVISIBLE))&&row==r->rows[COH_WR_TEX_DEFAULT_INVISIBLE])value.effective_basic_flags&=~1u;
 *out=value;return COH_OK;
}
CohStatus coh_wr_tex_defaults_role(const CohWrTexDefaults*r,uint32_t role,CohWrTexDefaultsBasic*out){
 CohStatus s=output_ok(r,out,sizeof(*out));if(s!=COH_OK)return s;
 if(role>=COH_WR_TEX_DEFAULT_COUNT)return COH_INVALID;
 if(!(r->report.selected_mask&(1u<<role)))return COH_NOT_FOUND;
 return coh_wr_tex_defaults_basic(r,r->rows[role],out);
}
CohStatus coh_wr_tex_defaults_body(const CohWrTexDefaults*r,uint32_t role,CohBytes*out){
 CohStatus s=output_ok(r,out,sizeof(*out));if(s!=COH_OK)return s;
 if(role>=COH_WR_TEX_DEFAULT_COUNT)return COH_INVALID;
 if(!r->leases[role])return COH_NOT_FOUND;
 return coh_wr_tex_namespace_body(r->leases[role],out);
}
CohStatus coh_wr_tex_defaults_destroy(CohWrTexDefaults**p){
 if(!p||!*p)return COH_INVALID;
 CohWrTexDefaults*r=*p;CohStatus s=output_ok(r,p,sizeof(*p));if(s!=COH_OK)return s;
 s=release_all(r);if(s!=COH_OK)return s;
 free(r);*p=NULL;return COH_OK;
}
