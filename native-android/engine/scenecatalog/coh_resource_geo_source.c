#include "coh_resource_geo_source.h"
#include <string.h>
#include <math.h>
#include <limits.h>
#include <zlib.h>
#define INFLATE_ARENA 65536u
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static float f32(const uint8_t *p){uint32_t v=u32(p);
float f;
memcpy(&f,&v,4);
return f;
}
static int span(size_t n,size_t o,size_t s){return o<=n&&s<=n-o;
}
static int disjoint(const void *a,size_t an,const void *b,size_t bn){
 if(!an||!bn)return 1;
 uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-av||bn>UINTPTR_MAX-bv)return 0;
 return av+an<=bv||bv+bn<=av;
}
static const char *name(CohBytes b,size_t off){if(off>=b.size)return NULL;
size_t n=b.size-off;
if(n>COH_ASSET_PATH_MAX+1)n=COH_ASSET_PATH_MAX+1;
const uint8_t *end=memchr(b.data+off,0,n);
return end&&end>b.data+off?(const char*)b.data+off:NULL;
}
typedef struct { uint8_t *p;
 size_t used,capacity;
 } Arena;

static voidpf za(voidpf ctx,uInt count,uInt size){Arena *a=ctx;
if(size&&count>SIZE_MAX/size)return NULL;
size_t bytes=(size_t)count*size;
size_t pad=(16-(uintptr_t)(a->p+a->used)%16)%16;
if(pad>a->capacity-a->used||bytes>a->capacity-a->used-pad)return NULL;
void *p=a->p+a->used+pad;
a->used+=pad+bytes;
memset(p,0,bytes);
return p;
}
static void zf(voidpf ctx,voidpf p){(void)ctx;
(void)p;
}
static CohStatus inflate_exact(CohBytes in,uint8_t *out,size_t n,void *scratch,size_t cap){
    if(in.size>UINT_MAX||n>UINT_MAX||!scratch||(!out&&n))return COH_INVALID;

    Arena a={(uint8_t*)scratch,0,cap};
z_stream z;
memset(&z,0,sizeof(z));
z.zalloc=za;
z.zfree=zf;
z.opaque=&a;

    if(inflateInit(&z)!=Z_OK)return COH_LIMIT;
z.next_in=(Bytef*)in.data;
z.avail_in=(uInt)in.size;
z.next_out=out;
z.avail_out=(uInt)n;
int r=inflate(&z,Z_FINISH);

    CohStatus s=r==Z_STREAM_END&&z.total_out==n&&z.total_in==in.size?COH_OK:r==Z_MEM_ERROR?COH_LIMIT:COH_INVALID;
inflateEnd(&z);
return s;

}
static CohStatus envelope(CohBytes b,uint32_t *version,size_t *packedoff,size_t *packed,size_t *decoded,size_t *payloadoff){
    if(!b.data||b.size<8)return COH_INVALID;
uint32_t bias=u32(b.data),n=u32(b.data+4);
size_t start,bytes,data;
uint32_t v;

    if(n){if(bias<4)return COH_INVALID;
v=0;
start=8;
bytes=bias-4;
data=(size_t)bias+8;
}
    else {if(b.size<16||bias<12)return COH_INVALID;
v=u32(b.data+8);
n=u32(b.data+12);
if(v<2||v>8)return COH_UNSUPPORTED;
start=16;
bytes=bias-12;
data=(size_t)bias+4;
}
    if(!n||!span(b.size,start,bytes)||data>b.size)return COH_INVALID;
*version=v;
*packedoff=start;
*packed=bytes;
*decoded=n;
*payloadoff=data;
return COH_OK;

}
static CohStatus record(const CohAssetGeo *g,uint32_t index,CohBytes *out){
 if(!g||index>=g->model_count||g->version!=8)return COH_INVALID;
 size_t at=g->records_offset;
 for(uint32_t k=0;k<=index;k++){if(!span(g->header.size,at,4))return COH_INVALID;uint32_t bytes=u32(g->header.data+at);if(bytes<204||bytes>4096||!span(g->header.size,at,bytes))return COH_INVALID;if(k==index){*out=(CohBytes){g->header.data+at,bytes};return COH_OK;}at+=bytes;}
 return COH_INVALID;
}
CohStatus coh_resource_geo_source_model(const CohAssetGeo *g,uint32_t index,CohAssetGeoModel *out,uint32_t *zero){
 if(!g||!out||!zero)return COH_INVALID;
 const void *inputs[]={g,g->header.data,g->payload.data,g->texture_names.data,g->model_names.data,g->material_ids.data};
 size_t lengths[]={sizeof(*g),g->header.size,g->payload.size,g->texture_names.size,g->model_names.size,g->material_ids.size};
 if(!disjoint(out,sizeof(*out),zero,sizeof(*zero)))return COH_INVALID;
 for(unsigned k=0;k<6;k++)if(!disjoint(out,sizeof(*out),inputs[k],lengths[k])||!disjoint(zero,sizeof(*zero),inputs[k],lengths[k]))return COH_INVALID;
 CohAssetGeoModel m;CohStatus status=coh_asset_geo_model(g,index,&m);
 if(status==COH_OK){*out=m;*zero=0;return COH_OK;}
 if(status!=COH_INVALID||g->version!=8)return status;
 CohBytes raw;if(record(g,index,&raw)!=COH_OK)return COH_INVALID;CohGeoModel disk;
 if(coh_geo_model(raw.data,raw.size,8,&disk)||disk.vertex_count||disk.triangle_count||disk.texture_count||disk.reflection_count||disk.bone_info_offset||!span(g->material_ids.size,disk.texture_index_offset,0))return COH_INVALID;
 memset(&m,0,sizeof(m));m.name=name(g->model_names,disk.name_offset);if(!m.name)return COH_INVALID;
 m.material_offset=disk.texture_index_offset;m.pack_count=disk.pack_count;
 for(unsigned k=0;k<3;k++){m.scale[k]=f32(raw.data+72+4*k);float lo=f32(raw.data+84+4*k),hi=f32(raw.data+96+4*k);if(!isfinite(m.scale[k])||!isfinite(lo)||!isfinite(hi)||lo>hi)return COH_INVALID;}
 for(uint32_t k=0;k<disk.pack_count;k++){m.packs[k]=disk.packs[k];CohPack32 p=disk.packs[k];if(!span(g->payload.size,p.offset,p.packed_bytes?p.packed_bytes:p.unpacked_bytes))return COH_INVALID;if(k!=7&&k!=8&&(p.packed_bytes||p.unpacked_bytes))return COH_INVALID;}
 /* api is a payload-relative alternate pivot, not an actual disk pointer. */
 uint32_t api=u32(raw.data+68);if(api&&!span(g->payload.size,api,4))return COH_INVALID;
 *out=m;*zero=1;return COH_OK;
}
CohStatus coh_resource_geo_source_open(CohBytes bytes,uint8_t *workspace,size_t cap,uint32_t maxmodels,CohAssetGeo *out,uint32_t *zero){
 if(!out||!zero)return COH_INVALID;
 const void *starts[]={bytes.data,workspace,out,zero};
 size_t lengths[]={bytes.size,cap,sizeof(*out),sizeof(*zero)};
 for(unsigned n=0;n<4;n++)for(unsigned k=n+1;k<4;k++)if(!disjoint(starts[n],lengths[n],starts[k],lengths[k]))return COH_INVALID;
 CohAssetGeo g;CohStatus status=coh_asset_geo_open(bytes,workspace,cap,maxmodels,&g);
 if(status==COH_OK){*out=g;*zero=0;return COH_OK;}
 if(status!=COH_INVALID)return status;
 if(!workspace||!maxmodels||maxmodels>(1u<<20))return COH_INVALID;
 uint32_t version;size_t packedoff,packed,decoded,payloadoff;status=envelope(bytes,&version,&packedoff,&packed,&decoded,&payloadoff);if(status!=COH_OK)return status;
 if(version!=8)return COH_INVALID;
 if(decoded>cap||cap-decoded<INFLATE_ARENA)return COH_LIMIT;
 status=inflate_exact((CohBytes){bytes.data+packedoff,packed},workspace,decoded,workspace+decoded,cap-decoded);if(status!=COH_OK)return status;
 memset(&g,0,sizeof(g));g.version=8;g.header=(CohBytes){workspace,decoded};g.payload=(CohBytes){bytes.data+payloadoff,bytes.size-payloadoff};
 if(decoded<16||u32(workspace)!=g.payload.size)return COH_INVALID;
 size_t at=16;CohBytes *blocks[]={&g.texture_names,&g.model_names,&g.material_ids};for(unsigned k=0;k<3;k++){uint32_t n=u32(workspace+4*(k+1));if(!span(decoded,at,n))return COH_INVALID;*blocks[k]=(CohBytes){workspace+at,n};at+=n;}
 if(!span(decoded,at,140)||g.texture_names.size<4)return COH_INVALID;
 g.model_count=u32(workspace+at+136);g.records_offset=at+140;g.texture_count=u32(g.texture_names.data);
 if(!g.model_count||g.model_count>maxmodels||!g.texture_count||g.texture_count>(g.texture_names.size-4)/4)return COH_INVALID;
 size_t base=4+(size_t)g.texture_count*4;
 for(uint32_t k=0;k<g.texture_count;k++){uint32_t off=u32(g.texture_names.data+4+4*k);if(!span(g.texture_names.size,base,off)||!name(g.texture_names,base+off))return COH_INVALID;}
 uint32_t empty=0;at=g.records_offset;
 for(uint32_t k=0;k<g.model_count;k++){CohAssetGeo one=g;one.records_offset=at;one.model_count=1;CohAssetGeoModel model;uint32_t iszero;status=coh_resource_geo_source_model(&one,0,&model,&iszero);if(status!=COH_OK)return status;empty+=iszero;CohBytes row;if(record(&one,0,&row)!=COH_OK)return COH_INVALID;at+=row.size;}
 if(at!=decoded||!empty)return COH_INVALID;
 *out=g;*zero=empty;return COH_OK;
}
