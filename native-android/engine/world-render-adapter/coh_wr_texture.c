#include "coh_wr_texture.h"
#include <stdlib.h>
#include <string.h>
#define MAX_BYTES (256u*1024u*1024u)
#define MAX_LEVELS 32u
typedef struct {uint32_t width,height;CohBytes rgba;} Mip;
struct CohWrTextureResource {
    CohAssetLoader *loader;const CohAssetBlob *blob;CohWrTextureReport report;
    char path[COH_ASSET_PATH_MAX+1];Mip mip[MAX_LEVELS];
};
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static int add(size_t *a,size_t n){if(n>SIZE_MAX-*a)return 0;*a+=n;return 1;}
static int room(CohAssetLoader*l,const CohWrTextureLimits*b,size_t owned,size_t *peak){
    size_t n=b->external_bytes;
    if(coh_asset_stats(l).peak_allocated_bytes>b->loader_reservation||
       !add(&n,b->loader_reservation)||!add(&n,owned)||n>b->aggregate_limit)return 0;
    if(n>*peak)*peak=n;
    return 1;
}
void coh_wr_texture_release(CohWrTextureResource **p){
    if(!p||!*p)return;
    CohWrTextureResource*r=*p;coh_asset_release(r->loader,r->blob);free(r);*p=NULL;
}
CohStatus coh_wr_texture_identity(const CohWrTextureResource*r,CohAssetId*out){
    if(!r||!out)return COH_INVALID;
    *out=(CohAssetId){r->path,r->report.asset_generation};return COH_OK;
}
CohStatus coh_wr_texture_report(const CohWrTextureResource*r,CohWrTextureReport*out){
    if(!r||!out)return COH_INVALID;
    *out=r->report;return COH_OK;
}
CohStatus coh_wr_texture_mip(const CohWrTextureResource*r,uint32_t i,uint32_t*w,uint32_t*h,CohBytes*out){
    if(!r||!w||!h||!out||i>=r->report.levels)return COH_INVALID;
    *w=r->mip[i].width;*h=r->mip[i].height;*out=r->mip[i].rgba;return COH_OK;
}
CohStatus coh_wr_texture_acquire(CohAssetLoader*l,const CohWrTextureRequest*q,const CohWrTextureLimits*b,CohCancel cancel,CohWrTextureResource **out){
    if(!l||!q||!b||!out||!q->asset.path||!q->asset.generation||!q->digest)return COH_INVALID;
    if(*out)return COH_STATE;
    size_t pathlen=0;while(pathlen<=COH_ASSET_PATH_MAX&&q->asset.path[pathlen])pathlen++;
    unsigned nonzero=0;for(unsigned i=0;i<32;i++)nonzero|=q->sha256[i];
    if(!pathlen||pathlen>COH_ASSET_PATH_MAX||!nonzero)return COH_INVALID;
    if(!b->aggregate_limit||b->aggregate_limit>MAX_BYTES||!b->loader_reservation||!b->max_rgba_bytes||
       !b->max_dimension||b->max_dimension>16384||!b->max_levels||b->max_levels>MAX_LEVELS)return COH_LIMIT;
    size_t owned=sizeof(CohWrTextureResource),rgba_bytes=0,peak=0;
    if(cancelled(cancel))return COH_CANCELLED;
    if(!room(l,b,owned,&peak))return COH_LIMIT;
    const CohAssetBlob*blob=NULL;CohWrTextureResource*r=NULL;
    CohStatus status=coh_asset_acquire(l,q->asset,cancel,&blob);if(status!=COH_OK)return status;
    if(!room(l,b,owned,&peak)){status=COH_LIMIT;goto fail;}
    CohAssetId identity=coh_asset_identity(blob);
    if(!identity.path||identity.generation!=q->asset.generation||strcmp(identity.path,q->asset.path)){status=COH_INVALID;goto fail;}
    CohBytes bytes=coh_asset_bytes(blob);uint8_t digest[32];
    status=q->digest(q->digest_context,bytes,digest);if(status!=COH_OK)goto fail;
    if(memcmp(q->sha256,digest,32)){status=COH_INVALID;goto fail;}
    if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}
    CohAssetTexture texture;status=coh_asset_texture(bytes,&texture);if(status!=COH_OK)goto fail;
    CohDdsMip m;if(coh_dds_mip(texture.dds.data,texture.dds.size,0,&m)){status=COH_INVALID;goto fail;}
    uint32_t levels=m.mip_count,format=m.format;
    if(m.width>b->max_dimension||m.height>b->max_dimension||levels>b->max_levels){status=COH_LIMIT;goto fail;}
    for(uint32_t i=0;i<levels;i++){
        if(coh_dds_mip(texture.dds.data,texture.dds.size,i,&m)){status=COH_INVALID;goto fail;}
        if(!add(&rgba_bytes,m.rgba_bytes)){status=COH_LIMIT;goto fail;}
    }
    if(rgba_bytes>b->max_rgba_bytes||!add(&owned,rgba_bytes)||!room(l,b,owned,&peak)){status=COH_LIMIT;goto fail;}
    r=calloc(1,owned);if(!r){status=COH_LIMIT;goto fail;}
    r->loader=l;r->blob=blob;memcpy(r->path,q->asset.path,pathlen+1);
    r->report=(CohWrTextureReport){q->asset.generation,texture.width,texture.height,levels,format,texture.flags,
        owned,rgba_bytes,b->loader_reservation,b->external_bytes,peak,{0}};
    memcpy(r->report.sha256,digest,32);uint8_t*cursor=(uint8_t*)(r+1);
    for(uint32_t i=0;i<levels;i++){
        if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}
        if(coh_dds_mip(texture.dds.data,texture.dds.size,i,&m)){status=COH_INVALID;goto fail;}
        status=coh_asset_texture_rgba(&texture,i,cursor,m.rgba_bytes);if(status!=COH_OK)goto fail;
        r->mip[i]=(Mip){m.width,m.height,{cursor,m.rgba_bytes}};cursor+=m.rgba_bytes;
    }
    if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}
    *out=r;return COH_OK;
fail:
    free(r);coh_asset_release(l,blob);return status;
}
