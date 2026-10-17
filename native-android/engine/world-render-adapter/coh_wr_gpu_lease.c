#include "coh_wr_gpu_lease.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
typedef struct { uint64_t id; CohWrGpuTexture *gpu; } Item;
_Static_assert(COH_ASSET_PATH_MAX<UINT16_MAX,"bounded path length workspace");
struct CohWrGpuLease {
    pthread_mutex_t mutex;
    pthread_t control;
    CohWrGpuLeaseBackend backend;
    CohWrGpuLeaseReport report;
    Item items[];
};
static int apart(const void *a,size_t n,const void *b,size_t m) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=UINTPTR_MAX-n && y<=UINTPTR_MAX-m && (x+n<=y || y+m<=x);
}
static int add(size_t *n,size_t v) { if (v>SIZE_MAX-*n) return 0; *n+=v; return 1; }
static int stopped(CohCancel c) { return c.poll && c.poll(c.context); }
static int same(CohWrGpuToken a,CohWrGpuToken b) {
    return a.surface_generation==b.surface_generation && a.context_generation==b.context_generation && a.render_thread==b.render_thread;
}
static int nonzero(const uint8_t *p) { unsigned n=0; for(unsigned i=0;i<32;i++)n|=p[i]; return n!=0; }
static int backend_valid(const CohWrGpuLeaseBackend *b) {
    const CohWrGpuOps *o=&b->gpu;
    return b->retain_registry && b->release_registry && b->begin_retirement && b->end_retirement && o->context &&
        o->current && o->retire_current && o->destroyed && o->get_integer && o->generate && o->bind_texture &&
        o->bind_unpack_buffer && o->pixel_store && o->image_rgba8 && o->parameter && o->delete_texture;
}
static int control(CohWrGpuLease *r) { return r->report.attached && pthread_equal(r->control,pthread_self()); }
static void fault(CohWrGpuLease *r) { if(r->report.callback_faults<UINT32_MAX)r->report.callback_faults++; }
static CohStatus hold(void *v) {
    CohWrGpuLease *r=v; CohStatus s=COH_STATE;
    if(!r)return COH_INVALID;
    pthread_mutex_lock(&r->mutex);
    if(control(r) && !r->report.retired && r->report.leases<UINT32_MAX) { r->report.leases++; s=COH_OK; }
    pthread_mutex_unlock(&r->mutex); return s;
}
static void drop(void *v) {
    CohWrGpuLease *r=v;if(!r)return;
    pthread_mutex_lock(&r->mutex);
    if(control(r) && r->report.leases)r->report.leases--;else fault(r);
    pthread_mutex_unlock(&r->mutex);
}
static CohStatus resolve(void *v,uint64_t id,uint32_t asset,uint32_t surface,uint32_t *out) {
    CohWrGpuLease *r=v;CohStatus s=COH_STATE;CohRenderTexture texture;
    if(!r || !out || !id)return COH_INVALID;
    if(!apart(r,r->report.owned_bytes,out,sizeof(*out)))return COH_INVALID;
    pthread_mutex_lock(&r->mutex);
    if(r->report.leases && !r->report.drained && !r->report.cleanup_gate &&
       asset==r->report.asset_generation && surface==r->report.token.surface_generation) {
        size_t lo=0,hi=r->report.textures;
        while(lo<hi) {size_t mid=lo+(hi-lo)/2;if(r->items[mid].id<id)lo=mid+1;else hi=mid;}
        s=COH_NOT_FOUND;
        if(lo<r->report.textures && r->items[lo].id==id) {
            s=coh_wr_gpu_view(r->items[lo].gpu,r->report.token,&r->backend.gpu,&texture);
            if(s==COH_OK) {if(!texture.handle)s=COH_STATE;else *out=texture.handle;}
        }
    }
    pthread_mutex_unlock(&r->mutex);return s;
}
CohStatus coh_wr_gpu_lease_adopt(const CohWrGpuLeaseInput *in,size_t count,
    const CohWrGpuLeaseBackend *backend,const CohWrGpuLeaseLimits *limits,CohCancel cancel,CohWrGpuLease **out) {
    if(!in || !count || count>COH_WR_GPU_LEASE_MAX_TEXTURES || !backend || !limits || !out || !backend_valid(backend))return COH_INVALID;
    if(!apart(in,count*sizeof(*in),out,sizeof(*out)) || !apart(backend,sizeof(*backend),out,sizeof(*out)) ||
       !apart(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
    if(*out)return COH_STATE;
    size_t bytes=sizeof(CohWrGpuLease)+count*sizeof(Item),minimum=count*sizeof(*in)+sizeof(*backend)+sizeof(*limits)+sizeof(*out);
    size_t gpu_bytes=0,total=limits->external_bytes;
    uint16_t path_bytes[COH_WR_GPU_LEASE_MAX_TEXTURES];
    CohWrGpuToken token={0};uint32_t generation=0;
    if(!limits->aggregate_limit || limits->aggregate_limit>COH_WR_MAX_MEMORY ||
       limits->gpu_owner_cpu_reservation<count*sizeof(CohWrGpuReport) || !limits->registry_reservation)return COH_LIMIT;
    for(size_t i=0;i<count;i++) {
        if(!in[i].texture_id || (i && in[i-1].texture_id>=in[i].texture_id) || !in[i].take || !*in[i].take ||
           !in[i].asset.path || !in[i].asset.generation || !nonzero(in[i].source_sha256))return COH_INVALID;
        if(!apart(in,count*sizeof(*in),in[i].take,sizeof(*in[i].take)) ||
           !apart(backend,sizeof(*backend),in[i].take,sizeof(*in[i].take)) ||
           !apart(limits,sizeof(*limits),in[i].take,sizeof(*in[i].take)) ||
           !apart(out,sizeof(*out),in[i].take,sizeof(*in[i].take)))return COH_INVALID;
        size_t n=0;while(n<=COH_ASSET_PATH_MAX && in[i].asset.path[n])n++;
        if(!n || n>COH_ASSET_PATH_MAX || !apart(in[i].asset.path,n+1,out,sizeof(*out)))return COH_INVALID;
        path_bytes[i]=(uint16_t)(n+1);
        if(!add(&minimum,n+1+sizeof(*in[i].take)))return COH_LIMIT;
        for(size_t j=0;j<i;j++)if(in[j].take==in[i].take || *in[j].take==*in[i].take)return COH_INVALID;
    }
    /* Read each path once; the bounded quadratic pass compares spans only.
     * No final NULL store may overwrite any other immutable source path. */
    for(size_t i=0;i<count;i++)for(size_t j=0;j<count;j++)
        if(!apart(in[i].take,sizeof(*in[i].take),in[j].asset.path,path_bytes[j]))return COH_INVALID;
    for(size_t i=0;i<count;i++) {
        CohWrGpuReport report;CohAssetId identity;
        CohStatus s=coh_wr_gpu_report(*in[i].take,&report);if(s!=COH_OK)return s;
        s=coh_wr_gpu_identity(*in[i].take,&identity);if(s!=COH_OK)return s;
        if(identity.generation!=in[i].asset.generation || strcmp(identity.path,in[i].asset.path) ||
           report.source.asset_generation!=identity.generation || memcmp(report.source.sha256,in[i].source_sha256,32) ||
           !report.token.surface_generation || report.token.surface_generation>UINT32_MAX || !report.token.context_generation ||
           !report.token.render_thread || !report.uploaded_levels || report.uploaded_levels!=report.source.levels ||
           report.gpu_reservation<report.source.rgba_bytes)return COH_STATE;
        if(i && (generation!=identity.generation || !same(token,report.token)))return COH_STATE;
        token=report.token;generation=identity.generation;
        if(!add(&gpu_bytes,report.gpu_reservation))return COH_LIMIT;
    }
    if(!add(&minimum,gpu_bytes) || !add(&minimum,limits->gpu_owner_cpu_reservation) || !add(&minimum,limits->registry_reservation) ||
       limits->external_bytes<minimum || !add(&total,bytes) || !add(&total,COH_WR_GPU_LEASE_CONTROL_RESERVE) || total>limits->aggregate_limit)return COH_LIMIT;
    if(stopped(cancel))return COH_CANCELLED;
    CohWrGpuLease *r=calloc(1,bytes);if(!r)return COH_LIMIT;
    if(pthread_mutex_init(&r->mutex,NULL)) {free(r);return COH_STATE;}
    CohStatus s=backend->retain_registry(backend->gpu.context);
    if(s!=COH_OK) {pthread_mutex_destroy(&r->mutex);free(r);return s;}
    for(size_t i=0;i<count;i++) {
        CohRenderTexture view;
        if(stopped(cancel)) {s=COH_CANCELLED;goto failed;}
        s=coh_wr_gpu_view(*in[i].take,token,&backend->gpu,&view);if(s!=COH_OK)goto failed;
        if(!view.handle) {s=COH_STATE;goto failed;}
        r->items[i]=(Item){in[i].texture_id,*in[i].take};
    }
    if(stopped(cancel)) {s=COH_CANCELLED;goto failed;}
    r->backend=*backend;r->report.token=token;r->report.asset_generation=generation;
    r->report.textures=r->report.remaining_textures=(uint32_t)count;r->report.owned_bytes=bytes;
    r->report.gpu_reservation=gpu_bytes;r->report.aggregate_reserved_bytes=total;
    for(size_t i=0;i<count;i++)*in[i].take=NULL;
    *out=r;return COH_OK;
failed:
    backend->release_registry(backend->gpu.context);pthread_mutex_destroy(&r->mutex);free(r);return s;
}
CohStatus coh_wr_gpu_lease_resources(CohWrGpuLease *r,CohWrPresentationResources *out) {
    if(!r || !out || !apart(r,r->report.owned_bytes,out,sizeof(*out)))return COH_INVALID;
    pthread_mutex_lock(&r->mutex);
    CohStatus s=COH_STATE;
    if(!r->report.retired && (!r->report.attached || control(r))) {
        r->control=pthread_self();r->report.attached=1;
        *out=(CohWrPresentationResources){r,hold,drop,resolve};s=COH_OK;
    }
    pthread_mutex_unlock(&r->mutex);return s;
}
CohStatus coh_wr_gpu_lease_retire(CohWrGpuLease *r) {
    if(!r)return COH_INVALID;
    pthread_mutex_lock(&r->mutex);CohStatus s=COH_STATE;
    if(control(r) && !r->report.retired) {r->report.retired=1;s=COH_OK;}
    pthread_mutex_unlock(&r->mutex);return s;
}
CohStatus coh_wr_gpu_lease_drain(CohWrGpuLease *r) {
    if(!r)return COH_INVALID;
    pthread_mutex_lock(&r->mutex);CohStatus failure=COH_STATE;
    if(!r->report.retired || r->report.leases)goto done;
    if(r->report.drained) {failure=COH_OK;goto done;}
    if(!r->report.cleanup_gate) {
        failure=r->backend.begin_retirement(r->backend.gpu.context,r->report.token);
        if(failure!=COH_OK)goto done;
        r->report.cleanup_gate=1;
    }
    failure=COH_OK;
    for(size_t i=0;i<r->report.textures;i++)if(r->items[i].gpu) {
        CohStatus s=coh_wr_gpu_release(&r->items[i].gpu,&r->backend.gpu);
        if(s==COH_STATE)s=coh_wr_gpu_discard_destroyed(&r->items[i].gpu,&r->backend.gpu);
        if(s!=COH_OK && failure==COH_OK)failure=s;
        if(!r->items[i].gpu)r->report.remaining_textures--;
    }
    if(!r->report.remaining_textures) {
        CohStatus s=r->backend.end_retirement(r->backend.gpu.context,r->report.token);
        if(s==COH_OK) {r->report.cleanup_gate=0;r->report.drained=1;}
        if(failure==COH_OK)failure=s;
    }
done:
    pthread_mutex_unlock(&r->mutex);return failure;
}
CohStatus coh_wr_gpu_lease_collect(CohWrGpuLease **owner) {
    if(!owner || !*owner)return COH_INVALID;
    CohWrGpuLease *r=*owner;
    if(!apart(r,r->report.owned_bytes,owner,sizeof(*owner)))return COH_INVALID;
    pthread_mutex_lock(&r->mutex);
    if(!control(r) || !r->report.retired || !r->report.drained || r->report.leases || r->report.remaining_textures || r->report.cleanup_gate) {
        pthread_mutex_unlock(&r->mutex);return COH_STATE;
    }
    pthread_mutex_unlock(&r->mutex);
    r->backend.release_registry(r->backend.gpu.context);
    pthread_mutex_destroy(&r->mutex);free(r);*owner=NULL;return COH_OK;
}
CohStatus coh_wr_gpu_lease_report(const CohWrGpuLease *owner,CohWrGpuLeaseReport *out) {
    if(!owner || !out || !apart(owner,owner->report.owned_bytes,out,sizeof(*out)))return COH_INVALID;
    CohWrGpuLease *r=(CohWrGpuLease *)owner;
    pthread_mutex_lock(&r->mutex);*out=r->report;pthread_mutex_unlock(&r->mutex);return COH_OK;
}
