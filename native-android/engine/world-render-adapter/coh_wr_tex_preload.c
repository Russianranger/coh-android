#include "coh_wr_tex_preload.h"
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#define PREP_RESERVE 32768u
#define RAW_MAX 1024u
#define RGBA_MAX 4096u
#define LEVELS_MAX 4u
typedef struct{uint32_t width,height;size_t offset,size;}PreloadMip;
struct CohWrTexPreload{CohWrTexPreloadReport report;char path[256],name[256];uint8_t raw[RAW_MAX],rgba[RGBA_MAX];PreloadMip mip[LEVELS_MAX];};
typedef struct{CohAssetTexture texture;CohDdsMip mip[LEVELS_MAX];CohBytes raw;uint32_t first,count,format;size_t source_header,rgba_bytes;}PreloadInput;
_Static_assert(2*sizeof(PreloadInput)+sizeof(CohWrTexPreloadReport)+4096<16384,"bounded preparation/control frames");
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static uint32_t word(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
static uint32_t levels(uint32_t w,uint32_t h){uint32_t n=0,x=w>h?w:h;while(x){n++;x>>=1;}return n;}
static CohStatus inspect(CohBytes body,PreloadInput*out){
 if(!body.data||body.size<33||!out)return COH_INVALID;
 PreloadInput r;memset(&r,0,sizeof(r));CohStatus status=coh_asset_texture(body,&r.texture);if(status!=COH_OK)return status;if(!r.texture.name)return COH_UNSUPPORTED;if(r.texture.alpha>1)return COH_INVALID;
 r.source_header=word(body.data);if(r.source_header<33||r.source_header>body.size||r.source_header-32>1024)return COH_LIMIT;
 size_t name_len=strlen(r.texture.name);if(!name_len||name_len>255)return COH_LIMIT;for(size_t i=0;i<name_len;i++)if((unsigned char)r.texture.name[i]<32||(unsigned char)r.texture.name[i]>126)return COH_UNSUPPORTED;
 size_t begin=32+name_len+1;if(begin>r.source_header)return COH_INVALID;if(memcmp(body.data+29,"TX2",3)||begin==r.source_header)return COH_NOT_FOUND;
 size_t bytes=r.source_header-begin;if(bytes<16||bytes>RAW_MAX)return COH_INVALID;const uint8_t*p=body.data+begin;if(word(p)!=16)return COH_UNSUPPORTED;
 CohDdsMip base;if(coh_dds_mip(r.texture.dds.data,r.texture.dds.size,0,&base))return COH_INVALID;uint32_t full=levels(base.width,base.height);if(!word(r.texture.dds.data+28)||base.mip_count!=full)return COH_UNSUPPORTED;r.count=full<4?full:4;r.first=full-r.count;r.format=base.format;
 uint32_t gl=base.format==1?33777u:base.format==3?33778u:base.format==5?33779u:0;if(!gl||word(p+12)!=gl)return COH_UNSUPPORTED;
 size_t packed=0;for(uint32_t i=0;i<r.count;i++){if(coh_dds_mip(r.texture.dds.data,r.texture.dds.size,r.first+i,r.mip+i))return COH_INVALID;if(!add(&packed,r.mip[i].block_bytes)||!add(&r.rgba_bytes,r.mip[i].rgba_bytes)||r.rgba_bytes>RGBA_MAX)return COH_LIMIT;}
 if(word(p+4)!=r.mip[0].width||word(p+8)!=r.mip[0].height||packed!=bytes-16||r.mip[r.count-1].blocks+r.mip[r.count-1].block_bytes!=r.texture.dds.data+r.texture.dds.size||memcmp(p+16,r.mip[0].blocks,packed))return COH_INVALID;
 r.raw=(CohBytes){p,bytes};*out=r;return COH_OK;
}
void coh_wr_tex_preload_release(CohWrTexPreload**out){if(out&&*out){free(*out);*out=NULL;}}
CohStatus coh_wr_tex_preload_report(const CohWrTexPreload*r,CohWrTexPreloadReport*out){if(!r||!out||!apart(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_wr_tex_preload_identity(const CohWrTexPreload*r,CohAssetId*out){if(!r||!out||!apart(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;*out=(CohAssetId){r->path,r->report.asset_generation};return COH_OK;}
CohStatus coh_wr_tex_preload_name(const CohWrTexPreload*r,const char**out){if(!r||!out||!apart(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;*out=r->name;return COH_OK;}
CohStatus coh_wr_tex_preload_raw(const CohWrTexPreload*r,CohBytes*out){if(!r||!out||!apart(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;*out=(CohBytes){r->raw,r->report.raw_bytes};return COH_OK;}
CohStatus coh_wr_tex_preload_mip(const CohWrTexPreload*r,uint32_t i,uint32_t*w,uint32_t*h,CohBytes*out){if(!r||!w||!h||!out||!apart(r,sizeof(*r),w,sizeof(*w))||!apart(r,sizeof(*r),h,sizeof(*h))||!apart(r,sizeof(*r),out,sizeof(*out))||!apart(w,sizeof(*w),h,sizeof(*h))||!apart(w,sizeof(*w),out,sizeof(*out))||!apart(h,sizeof(*h),out,sizeof(*out)))return COH_INVALID;if(i>=r->report.levels)return COH_NOT_FOUND;PreloadMip m=r->mip[i];*w=m.width;*h=m.height;*out=(CohBytes){r->rgba+m.offset,m.size};return COH_OK;}
CohStatus coh_wr_tex_preload_acquire(CohAssetLoader*loader,const CohWrTextureRequest*q,const CohWrTexPreloadLimits*limits,CohCancel cancel,CohWrTexPreload**out){
 if(!loader||!q||!limits||!out||!q->digest||!q->asset.path||!q->asset.generation||!apart(q,sizeof(*q),out,sizeof(*out))||!apart(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 size_t n;for(n=0;n<=255;n++){unsigned c=(unsigned char)q->asset.path[n];if(!c)break;if(c<32||c>126)return COH_UNSUPPORTED;}if(!n||n>255||!apart(q->asset.path,n+1,out,sizeof(*out)))return COH_INVALID;unsigned nonzero=0;for(unsigned i=0;i<32;i++)nonzero|=q->sha256[i];if(!nonzero)return COH_INVALID;
 size_t total=limits->external_bytes;if(!limits->loader_reservation||sizeof(CohWrTexPreload)>limits->owned_limit||!add(&total,limits->loader_reservation)||!add(&total,sizeof(CohWrTexPreload))||!add(&total,PREP_RESERVE)||!add(&total,sizeof(*q)+n+1)||total>limits->aggregate_limit||coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 const CohAssetBlob*blob=NULL;CohWrTexPreload*r=NULL;CohStatus status=coh_asset_acquire(loader,q->asset,cancel,&blob);if(status!=COH_OK)return status;CohBytes body=coh_asset_bytes(blob);CohAssetId id=coh_asset_identity(blob);if(coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation){status=COH_LIMIT;goto fail;}if(!id.path||strcmp(id.path,q->asset.path)||id.generation!=q->asset.generation||!apart(body.data,body.size,out,sizeof(*out))){status=COH_INVALID;goto fail;}
 uint8_t hash[32];status=q->digest(q->digest_context,body,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,q->sha256,32)){status=COH_INVALID;goto fail;}if(stop(cancel)){status=COH_CANCELLED;goto fail;}PreloadInput input;status=inspect(body,&input);if(status!=COH_OK)goto fail;
 r=calloc(1,sizeof(*r));if(!r){status=COH_LIMIT;goto fail;}memcpy(r->path,q->asset.path,n+1);memcpy(r->name,input.texture.name,strlen(input.texture.name)+1);memcpy(r->raw,input.raw.data,input.raw.size);CohWrTexPreloadReport report;memset(&report,0,sizeof(report));report.asset_generation=id.generation;report.source_width=input.texture.width;report.source_height=input.texture.height;report.width=input.mip[0].width;report.height=input.mip[0].height;report.levels=input.count;report.first_DDS_level=input.first;report.format=input.format;report.cached_texopt_flags=input.texture.flags;report.source_header_bytes=input.source_header;report.source_payload_bytes=input.texture.dds.size;report.source_preload_offset=(size_t)(input.raw.data-body.data);report.raw_bytes=input.raw.size;report.rgba_bytes=input.rgba_bytes;report.owned_bytes=sizeof(*r);report.aggregate_reserved_bytes=total;report.preparation_loader_reservation=limits->loader_reservation;memcpy(report.asset_sha256,hash,32);status=q->digest(q->digest_context,(CohBytes){r->raw,input.raw.size},report.preload_sha256);if(status!=COH_OK)goto fail;
 size_t offset=0;for(uint32_t i=0;i<input.count;i++){if(stop(cancel)){status=COH_CANCELLED;goto fail;}status=coh_asset_texture_rgba(&input.texture,input.first+i,r->rgba+offset,input.mip[i].rgba_bytes);if(status!=COH_OK)goto fail;r->mip[i]=(PreloadMip){input.mip[i].width,input.mip[i].height,offset,input.mip[i].rgba_bytes};offset+=input.mip[i].rgba_bytes;}r->report=report;if(stop(cancel)){status=COH_CANCELLED;goto fail;}coh_asset_release(loader,blob);*out=r;return COH_OK;
 fail:coh_asset_release(loader,blob);free(r);return status;
}
