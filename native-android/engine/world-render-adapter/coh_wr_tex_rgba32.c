#include "coh_wr_tex_rgba32.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>

struct CohWrTexRgba32 {CohWrTexRgba32View view;char path[260];uint8_t pixels[];};
typedef struct {uint32_t width,height,count,source_count;size_t offset,bytes,total;} Layout;
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int separate(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int stopped(CohCancel cancel){return cancel.poll&&cancel.poll(cancel.context);}
static CohStatus layout(CohBytes body,const CohWrTexNamespaceBasic*b,uint32_t skip,Layout*out){
 if(!body.data||b->file_offset>body.size||b->file_bytes!=body.size-b->file_offset||b->file_bytes<128)return COH_INVALID;
 if(!(b->initial_basic_flags&(1u<<6)))return COH_UNSUPPORTED;
 const uint8_t*p=body.data+b->file_offset;
 if(memcmp(p,"DDS ",4)||word(p+4)!=124||word(p+76)!=32)return COH_INVALID;
 uint32_t w=word(p+16),h=word(p+12),m=word(p+28),flags=word(p+8),pitch=word(p+20);
 if(!w||!h||w>16384||h>16384||w!=b->width||h!=b->height)return COH_INVALID;
 if(word(p+24)>1||word(p+112))return COH_UNSUPPORTED;
 if(word(p+80)!=0x41||word(p+84)||word(p+88)!=32||word(p+92)!=0x00ff0000||word(p+96)!=0x0000ff00||word(p+100)!=0x000000ff||word(p+104)!=0xff000000)return COH_UNSUPPORTED;
 if((flags&8u)&&(flags&0x80000u))return COH_UNSUPPORTED;
 if(((flags&8u)&&pitch!=w*4u)||((flags&0x80000u)&&pitch!=(uint64_t)w*h*4u))return COH_UNSUPPORTED;
 uint32_t maximum=1,t=w>h?w:h;while(t>1){maximum++;t>>=1;}
 if(m&&m!=maximum)return COH_UNSUPPORTED;
 uint32_t count=m?m:1;if(skip>=count)return COH_INVALID;
 size_t total=128,offset=128,selected=0;uint32_t sw=w,sh=h;
 for(uint32_t i=0;i<count;i++){
  size_t bytes=(size_t)w*h*4u;
  if(!add(&total,bytes))return COH_LIMIT;
  if(i<skip)offset=total;else if(!add(&selected,bytes))return COH_LIMIT;
  if(i==skip){sw=w;sh=h;}
  w=w>1?w/2:1;h=h>1?h/2:1;
 }
 if(total!=b->file_bytes)return COH_INVALID;
 *out=(Layout){sw,sh,count-skip,m,offset,selected,total};return COH_OK;
}
CohStatus coh_wr_tex_rgba32_build(CohWrTexNamespace*source,uint32_t row,uint32_t skip,const CohWrTexRgba32Limits*limits,CohCancel cancel,CohWrTexRgba32**out){
 if(!source||!limits||!out||*out||!separate(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 CohWrTexRgba32Limits bound=*limits;
 if(!bound.owned_limit||bound.owned_limit>256u*1024u*1024u||!bound.aggregate_limit)return COH_LIMIT;
 CohWrTexNamespaceReport report;CohStatus status=coh_wr_tex_namespace_report(source,&report);if(status!=COH_OK)return status;
 if(bound.external_bytes<report.aggregate_reserved_bytes)return COH_LIMIT;
 size_t aggregate=bound.external_bytes;
 if(!add(&aggregate,COH_WR_TEX_RGBA32_PREPARATION_RESERVE)||!add(&aggregate,sizeof(CohWrTexRgba32))||aggregate>bound.aggregate_limit||sizeof(CohWrTexRgba32)>bound.owned_limit)return COH_LIMIT;
 CohWrTexNamespaceBasic basic;status=coh_wr_tex_namespace_basic(source,row,&basic);if(status!=COH_OK)return status;
 size_t path_bytes=strlen(basic.asset.path)+1;
 if(path_bytes>260||!separate(basic.asset.path,path_bytes,out,sizeof(*out))||!separate(basic.original_name,strlen(basic.original_name)+1,out,sizeof(*out))||!separate(basic.directory,strlen(basic.directory)+1,out,sizeof(*out))||!separate(basic.basic_key,strlen(basic.basic_key)+1,out,sizeof(*out))||!separate(basic.cached_mips.data,basic.cached_mips.size,out,sizeof(*out)))return COH_INVALID;
 const CohWrTexNamespaceBody*lease=NULL;CohWrTexRgba32*r=NULL;
 /* Namespace acquire pins before its cancellation/read/digest callbacks. */
 status=coh_wr_tex_namespace_acquire(source,row,cancel,&lease);if(status!=COH_OK)return status;
 CohBytes body;status=coh_wr_tex_namespace_body(lease,&body);if(status!=COH_OK)goto done;
 if(!separate(body.data,body.size,out,sizeof(*out))){status=COH_INVALID;goto done;}
 Layout plan;status=layout(body,&basic,skip,&plan);if(status!=COH_OK)goto done;
 size_t owned=sizeof(*r);if(!add(&owned,plan.bytes)||owned>bound.owned_limit||!add(&aggregate,plan.bytes)||aggregate>bound.aggregate_limit){status=COH_LIMIT;goto done;}
 if(stopped(cancel)){status=COH_CANCELLED;goto done;}
 r=calloc(1,owned);if(!r){status=COH_LIMIT;goto done;}
 r->view.asset=(CohAssetId){r->path,basic.asset.generation};memcpy(r->path,basic.asset.path,path_bytes);memcpy(r->view.sha256,basic.sha256,32);
 r->view.source_row=row;r->view.source_input_generation=report.source_input_generation;r->view.source_mip_count=plan.source_count;r->view.skipped_mips=skip;r->view.mip_count=plan.count;r->view.owned_bytes=owned;r->view.aggregate_reserved_bytes=aggregate;
 const uint8_t*input=body.data+basic.file_offset+plan.offset;uint8_t*target=r->pixels;uint32_t w=plan.width,h=plan.height;
 for(uint32_t i=0;i<plan.count;i++){
  size_t bytes=(size_t)w*h*4u;r->view.mips[i]=(CohWrTexRgba32Mip){w,h,i+skip,{target,bytes}};
  for(uint32_t y=0;y<h;y++){
   if(stopped(cancel)){status=COH_CANCELLED;goto done;}
   for(uint32_t x=0;x<w;x++){size_t at=((size_t)y*w+x)*4;target[at]=input[at+2];target[at+1]=input[at+1];target[at+2]=input[at];target[at+3]=input[at+3];}
  }
  input+=bytes;target+=bytes;w=w>1?w/2:1;h=h>1?h/2:1;
 }
 if(stopped(cancel))status=COH_CANCELLED;
done:
 {CohStatus released=coh_wr_tex_namespace_release(source,&lease);if(released!=COH_OK&&status==COH_OK)status=released;}
 if(status!=COH_OK){free(r);return status;}
 *out=r;return COH_OK;
}
CohStatus coh_wr_tex_rgba32_view(const CohWrTexRgba32*r,CohWrTexRgba32View*out){if(!r||!out||!separate(r,r->view.owned_bytes,out,sizeof(*out)))return COH_INVALID;*out=r->view;return COH_OK;}
CohStatus coh_wr_tex_rgba32_destroy(CohWrTexRgba32**pointer){if(!pointer||!*pointer)return COH_INVALID;CohWrTexRgba32*r=*pointer;if(!separate(r,r->view.owned_bytes,pointer,sizeof(*pointer)))return COH_INVALID;free(r);*pointer=NULL;return COH_OK;}
