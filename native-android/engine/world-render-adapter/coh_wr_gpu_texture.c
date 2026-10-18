#include "coh_wr_gpu_texture.h"
#include <stdlib.h>
#include <string.h>
#define TEXTURE_BINDING_2D 0x8069u
#define PIXEL_UNPACK_BUFFER_BINDING 0x88efu
#define MAX_TEXTURE_SIZE 0x0d33u
#define UNPACK_ALIGNMENT 0x0cf5u
#define UNPACK_ROW_LENGTH 0x0cf2u
#define UNPACK_SKIP_ROWS 0x0cf3u
#define UNPACK_SKIP_PIXELS 0x0cf4u
#define TEXTURE_WRAP_S 0x2802u
#define TEXTURE_WRAP_T 0x2803u
#define TEXTURE_MIN_FILTER 0x2801u
#define TEXTURE_MAG_FILTER 0x2800u
struct CohWrGpuTexture {CohWrGpuReport report;CohRenderTexture texture;CohWrGpuOps operations;char path[COH_ASSET_PATH_MAX+1];};
static const uint32_t state_enum[]={TEXTURE_BINDING_2D,PIXEL_UNPACK_BUFFER_BINDING,UNPACK_ALIGNMENT,UNPACK_ROW_LENGTH,UNPACK_SKIP_ROWS,UNPACK_SKIP_PIXELS};
static int same(CohWrGpuToken a,CohWrGpuToken b){return a.surface_generation==b.surface_generation&&a.context_generation==b.context_generation&&a.render_thread==b.render_thread;}
static int valid(CohWrGpuToken t){return t.surface_generation&&t.context_generation&&t.render_thread;}
static int ops_valid(const CohWrGpuOps*o){return o&&o->current&&o->retire_current&&o->destroyed&&o->get_integer&&o->generate&&o->bind_texture&&o->bind_unpack_buffer&&o->pixel_store&&o->image_rgba8&&o->parameter&&o->delete_texture;}
static int same_ops(const CohWrGpuOps*a,const CohWrGpuOps*b){
    return a->context==b->context&&a->current==b->current&&a->retire_current==b->retire_current&&a->destroyed==b->destroyed&&
        a->get_integer==b->get_integer&&a->generate==b->generate&&a->bind_texture==b->bind_texture&&
        a->bind_unpack_buffer==b->bind_unpack_buffer&&a->pixel_store==b->pixel_store&&
        a->image_rgba8==b->image_rgba8&&a->parameter==b->parameter&&a->delete_texture==b->delete_texture;
}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static CohStatus restore(CohWrGpuJournal*j,const CohWrGpuOps*o){
    if(!j->restore_needed)return COH_OK;
    CohStatus failure=COH_OK;
    for(unsigned i=0;i<6;i++){
        CohStatus s=o->retire_current(o->context,j->token);
        if(s==COH_OK){
            if(i==0)s=o->bind_texture(o->context,(uint32_t)j->saved[i]);
            else if(i==1)s=o->bind_unpack_buffer(o->context,(uint32_t)j->saved[i]);
            else s=o->pixel_store(o->context,state_enum[i],j->saved[i]);
        }
        if(s!=COH_OK)failure=s;
    }
    if(failure==COH_OK)j->restore_needed=0;
    return failure;
}
CohStatus coh_wr_gpu_retry_cleanup(CohWrGpuJournal*j,const CohWrGpuOps*o){
    if(!j||!ops_valid(o))return COH_INVALID;
    if(!j->pending)return COH_OK;
    if(!same_ops(o,&j->operations))return COH_STATE;
    if(!valid(j->token))return COH_INVALID;
    CohStatus s=restore(j,o),d=COH_OK;
    if(j->name){d=o->retire_current(o->context,j->token);if(d==COH_OK)d=o->delete_texture(o->context,&j->name);}
    if(!j->name&&!j->restore_needed){memset(j,0,sizeof(*j));return s!=COH_OK?s:d;}
    return COH_STATE;
}
CohStatus coh_wr_gpu_discard_destroyed_journal(CohWrGpuJournal*j,const CohWrGpuOps*o){
    if(!j||!ops_valid(o))return COH_INVALID;
    if(!j->pending)return COH_OK;
    if(!same_ops(o,&j->operations))return COH_STATE;
    CohStatus s=o->destroyed(o->context,j->token);if(s!=COH_OK)return s;
    memset(j,0,sizeof(*j));return COH_OK;
}
CohStatus coh_wr_gpu_view(const CohWrGpuTexture*r,CohWrGpuToken t,const CohWrGpuOps*o,CohRenderTexture*out){
    if(!r||!out||!ops_valid(o))return COH_INVALID;
    if(!same_ops(o,&r->operations)||!r->texture.handle||!same(t,r->report.token))return COH_STATE;
    CohStatus s=o->current(o->context,t);if(s!=COH_OK)return s;
    *out=r->texture;return COH_OK;
}
CohStatus coh_wr_gpu_report(const CohWrGpuTexture*r,CohWrGpuReport*out){if(!r||!out)return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_wr_gpu_release(CohWrGpuTexture**p,const CohWrGpuOps*o){
    if(!p||!ops_valid(o))return COH_INVALID;
    if(!*p)return COH_OK;
    CohWrGpuTexture*r=*p;if(!same_ops(o,&r->operations))return COH_STATE;CohStatus s=o->retire_current(o->context,r->report.token);if(s!=COH_OK)return s;
    if(r->texture.handle){s=o->delete_texture(o->context,&r->texture.handle);if(s!=COH_OK)return s;}
    free(r);*p=NULL;return COH_OK;
}
CohStatus coh_wr_gpu_discard_destroyed(CohWrGpuTexture**p,const CohWrGpuOps*o){
    if(!p||!ops_valid(o))return COH_INVALID;
    if(!*p)return COH_OK;
    if(!same_ops(o,&(*p)->operations))return COH_STATE;
    CohStatus s=o->destroyed(o->context,(*p)->report.token);if(s!=COH_OK)return s;
    free(*p);*p=NULL;return COH_OK;
}
CohStatus coh_wr_gpu_identity(const CohWrGpuTexture*r,CohAssetId*out){
    if(!r||!out)return COH_INVALID;
    *out=(CohAssetId){r->path,r->report.source.asset_generation};return COH_OK;
}
static int32_t wrap(CohWrap v){return v==COH_WRAP_REPEAT?0x2901:v==COH_WRAP_CLAMP?0x812f:0x8370;}
static int32_t filter(CohFilter v){return v==COH_FILTER_NEAREST?0x2600:v==COH_FILTER_LINEAR?0x2601:0x2703;}
CohStatus coh_wr_gpu_upload(const CohWrTextureResource*source,const CohWrSamplerSource*sampler,CohWrGpuToken token,const CohWrGpuOps*o,const CohWrGpuLimits*b,CohCancel cancel,CohWrGpuTexture**out,CohWrGpuJournal*j){
    if(!source||!sampler||!ops_valid(o)||!b||!out||!j||!valid(token))return COH_INVALID;
    if(*out||j->pending||j->name||j->restore_needed)return COH_STATE;
    CohWrTextureReport report;CohRenderTexture texture;CohStatus s=coh_wr_texture_report(source,&report);if(s!=COH_OK)return s;
    s=coh_wr_sampler_project(sampler,&texture);if(s!=COH_OK)return s;
    if(sampler->width!=report.width||sampler->height!=report.height||sampler->available_levels!=report.levels)return COH_INVALID;
    if(!b->aggregate_limit||b->aggregate_limit>256u*1024u*1024u||!b->max_dimension||
       report.width>b->max_dimension||report.height>b->max_dimension||b->gpu_reservation<report.rgba_bytes||
       b->external_bytes>b->aggregate_limit||b->gpu_reservation>b->aggregate_limit-b->external_bytes||
       sizeof(CohWrGpuTexture)>b->aggregate_limit-b->external_bytes-b->gpu_reservation)return COH_LIMIT;
    if(cancelled(cancel))return COH_CANCELLED;
    s=o->current(o->context,token);if(s!=COH_OK)return s;
    int32_t limit;s=o->get_integer(o->context,MAX_TEXTURE_SIZE,&limit);if(s!=COH_OK)return s;
    if(limit<=0||report.width>(uint32_t)limit||report.height>(uint32_t)limit)return COH_LIMIT;
    CohWrGpuJournal staging={0};staging.token=token;staging.operations=*o;
    for(unsigned i=0;i<6;i++){
        s=o->current(o->context,token);if(s!=COH_OK)return s;
        s=o->get_integer(o->context,state_enum[i],staging.saved+i);if(s!=COH_OK)return s;
    }
    if((staging.saved[2]!=1&&staging.saved[2]!=2&&staging.saved[2]!=4&&staging.saved[2]!=8)||staging.saved[3]<0||staging.saved[4]<0||staging.saved[5]<0)return COH_INVALID;
    CohAssetId identity;s=coh_wr_texture_identity(source,&identity);if(s!=COH_OK)return s;
    CohWrGpuTexture*r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;
    staging.pending=1;
#define CALL(expr) do{s=o->current(o->context,token);if(s!=COH_OK)goto fail;s=(expr);if(s!=COH_OK)goto fail;}while(0)
    CALL(o->generate(o->context,&staging.name));if(!staging.name){s=COH_IO;goto fail;}
    staging.restore_needed=1;
    CALL(o->bind_texture(o->context,staging.name));
    CALL(o->bind_unpack_buffer(o->context,0));
    for(unsigned i=2;i<6;i++)CALL(o->pixel_store(o->context,state_enum[i],i==2?1:0));
    for(uint32_t level=0;level<report.levels;level++){
        if(cancelled(cancel)){s=COH_CANCELLED;goto fail;}
        uint32_t w,h;CohBytes rgba;s=coh_wr_texture_mip(source,level,&w,&h,&rgba);if(s!=COH_OK)goto fail;
        CALL(o->image_rgba8(o->context,level,w,h,rgba));
    }
    const uint32_t pname[]={TEXTURE_WRAP_S,TEXTURE_WRAP_T,TEXTURE_MIN_FILTER,TEXTURE_MAG_FILTER};
    int32_t value[]={wrap(texture.wrap_s),wrap(texture.wrap_t),filter(texture.min_filter),filter(texture.mag_filter)};
    for(unsigned i=0;i<4;i++)CALL(o->parameter(o->context,pname[i],value[i]));
    s=restore(&staging,o);if(s!=COH_OK)goto fail;
    if(cancelled(cancel)){s=COH_CANCELLED;goto fail;}
    CALL(COH_OK);
    texture.handle=staging.name;r->texture=texture;r->operations=*o;strcpy(r->path,identity.path);
    r->report=(CohWrGpuReport){token,report,b->gpu_reservation,b->external_bytes+b->gpu_reservation+sizeof(*r),report.levels,COH_WR_GPU_SOURCE_LEGACY_DXT,{0},sizeof(*r)};
    *out=r;return COH_OK;
fail:
    *j=staging;free(r);(void)coh_wr_gpu_retry_cleanup(j,o);return j->pending?COH_STATE:s;
#undef CALL
}
static int rgba32_apart(const void*a,size_t an,const void*b,size_t bn){
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);
}
static int rgba32_add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
CohStatus coh_wr_gpu_upload_rgba32(const CohWrTexRgba32*source,const CohWrSamplerSource*sampler,CohWrGpuToken token,const CohWrGpuOps*o,const CohWrGpuLimits*b,CohCancel cancel,CohWrGpuTexture**out,CohWrGpuJournal*j){
    if(!source||!sampler||!o||!b||!out||!j)return COH_INVALID;
    const void*inputs[]={sampler,o,b};const size_t sizes[]={sizeof(*sampler),sizeof(*o),sizeof(*b)};
    if(!rgba32_apart(out,sizeof(*out),j,sizeof(*j)))return COH_INVALID;
    for(unsigned i=0;i<3;i++)if(!rgba32_apart(inputs[i],sizes[i],out,sizeof(*out))||!rgba32_apart(inputs[i],sizes[i],j,sizeof(*j)))return COH_INVALID;
    CohWrTexRgba32View view;CohStatus s=coh_wr_tex_rgba32_view(source,&view);if(s!=COH_OK)return s;
    if(!view.asset.path||!view.asset.generation||!view.mip_count||view.mip_count>COH_WR_TEX_RGBA32_MAX_MIPS)return COH_STATE;
    size_t path_bytes=0;while(path_bytes<=COH_ASSET_PATH_MAX&&view.asset.path[path_bytes])path_bytes++;
    if(!path_bytes||path_bytes>COH_ASSET_PATH_MAX)return COH_STATE;
    if(!rgba32_apart(view.asset.path,path_bytes+1,out,sizeof(*out))||!rgba32_apart(view.asset.path,path_bytes+1,j,sizeof(*j)))return COH_INVALID;
    for(unsigned i=0;i<3;i++)if(!rgba32_apart(view.asset.path,path_bytes+1,inputs[i],sizes[i]))return COH_INVALID;
    size_t rgba_bytes=0;uint32_t width=view.mips[0].width,height=view.mips[0].height;
    for(uint32_t level=0;level<view.mip_count;level++){
        const CohWrTexRgba32Mip*m=view.mips+level;
        if(!m->rgba.data||!width||!height||m->width!=width||m->height!=height||width>16384||height>16384||m->rgba.size!=(size_t)width*height*4u||!rgba32_add(&rgba_bytes,m->rgba.size))return COH_STATE;
        if(!rgba32_apart(m->rgba.data,m->rgba.size,out,sizeof(*out))||!rgba32_apart(m->rgba.data,m->rgba.size,j,sizeof(*j)))return COH_INVALID;
        for(unsigned i=0;i<3;i++)if(!rgba32_apart(m->rgba.data,m->rgba.size,inputs[i],sizes[i]))return COH_INVALID;
        width=width>1?width/2:1;height=height>1?height/2:1;
    }
    if(*out||j->pending||j->name||j->restore_needed)return COH_STATE;
    if(!ops_valid(o)||!valid(token))return COH_INVALID;
    size_t minimum=view.aggregate_reserved_bytes;
    if(!rgba32_add(&minimum,sizeof(*sampler)+sizeof(*o)+sizeof(*b)+sizeof(*out)+sizeof(*j)+sizeof(cancel))||b->external_bytes<minimum)return COH_LIMIT;
    size_t aggregate=b->external_bytes;
    if(!b->aggregate_limit||b->aggregate_limit>256u*1024u*1024u||!b->max_dimension||view.mips[0].width>b->max_dimension||view.mips[0].height>b->max_dimension||b->gpu_reservation<rgba_bytes||!rgba32_add(&aggregate,b->gpu_reservation)||!rgba32_add(&aggregate,sizeof(CohWrGpuTexture))||!rgba32_add(&aggregate,COH_WR_GPU_RGBA32_PREPARATION_RESERVE)||aggregate>b->aggregate_limit)return COH_LIMIT;
    CohRenderTexture texture;s=coh_wr_sampler_project(sampler,&texture);if(s!=COH_OK)return s;
    if(sampler->width!=view.mips[0].width||sampler->height!=view.mips[0].height||sampler->available_levels!=view.mip_count)return COH_INVALID;
    if(cancelled(cancel))return COH_CANCELLED;
    s=o->current(o->context,token);if(s!=COH_OK)return s;
    int32_t limit;s=o->get_integer(o->context,MAX_TEXTURE_SIZE,&limit);if(s!=COH_OK)return s;
    if(limit<=0||view.mips[0].width>(uint32_t)limit||view.mips[0].height>(uint32_t)limit)return COH_LIMIT;
    CohWrGpuJournal staging={0};staging.token=token;staging.operations=*o;
    for(unsigned i=0;i<6;i++){
        s=o->current(o->context,token);if(s!=COH_OK)return s;
        s=o->get_integer(o->context,state_enum[i],staging.saved+i);if(s!=COH_OK)return s;
    }
    if((staging.saved[2]!=1&&staging.saved[2]!=2&&staging.saved[2]!=4&&staging.saved[2]!=8)||staging.saved[3]<0||staging.saved[4]<0||staging.saved[5]<0)return COH_INVALID;
    CohWrGpuTexture*r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;
    staging.pending=1;
#define RGBA_STEP(expr) do{s=o->current(o->context,token);if(s!=COH_OK)goto rgba_fail;s=(expr);if(s!=COH_OK)goto rgba_fail;}while(0)
    RGBA_STEP(o->generate(o->context,&staging.name));if(!staging.name){s=COH_IO;goto rgba_fail;}
    staging.restore_needed=1;
    RGBA_STEP(o->bind_texture(o->context,staging.name));RGBA_STEP(o->bind_unpack_buffer(o->context,0));
    for(unsigned i=2;i<6;i++)RGBA_STEP(o->pixel_store(o->context,state_enum[i],i==2?1:0));
    for(uint32_t level=0;level<view.mip_count;level++){
        if(cancelled(cancel)){s=COH_CANCELLED;goto rgba_fail;}
        const CohWrTexRgba32Mip*m=view.mips+level;
        RGBA_STEP(o->image_rgba8(o->context,level,m->width,m->height,m->rgba));
    }
    const uint32_t pname[]={TEXTURE_WRAP_S,TEXTURE_WRAP_T,TEXTURE_MIN_FILTER,TEXTURE_MAG_FILTER};
    int32_t value[]={wrap(texture.wrap_s),wrap(texture.wrap_t),filter(texture.min_filter),filter(texture.mag_filter)};
    for(unsigned i=0;i<4;i++)RGBA_STEP(o->parameter(o->context,pname[i],value[i]));
    s=restore(&staging,o);if(s!=COH_OK)goto rgba_fail;
    if(cancelled(cancel)){s=COH_CANCELLED;goto rgba_fail;}
    RGBA_STEP(COH_OK);
    texture.handle=staging.name;r->texture=texture;r->operations=*o;memcpy(r->path,view.asset.path,path_bytes+1);
    CohWrTextureReport report={0};report.asset_generation=view.asset.generation;report.width=view.mips[0].width;report.height=view.mips[0].height;report.levels=view.mip_count;report.owned_bytes=view.owned_bytes;report.rgba_bytes=rgba_bytes;report.aggregate_peak_bytes=view.aggregate_reserved_bytes;memcpy(report.sha256,view.sha256,32);
    r->report=(CohWrGpuReport){token,report,b->gpu_reservation,aggregate,view.mip_count,COH_WR_GPU_SOURCE_NAMESPACE_RGBA32,{view.source_row,view.source_input_generation,view.source_mip_count,view.skipped_mips,view.aggregate_reserved_bytes},sizeof(*r)};
    *out=r;return COH_OK;
rgba_fail:
    *j=staging;free(r);(void)coh_wr_gpu_retry_cleanup(j,o);return j->pending?COH_STATE:s;
#undef RGBA_STEP
}
