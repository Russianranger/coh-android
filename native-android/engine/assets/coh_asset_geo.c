#include "coh_asset_geo.h"
#include <string.h>
#include <math.h>
#include <limits.h>
#include <zlib.h>
#define INFLATE_ARENA 65536u
static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);
}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static float f32(const uint8_t *p){uint32_t v=u32(p);
float f;
memcpy(&f,&v,4);
return f;
}
static int span(size_t n,size_t o,size_t s){return o<=n&&s<=n-o;
}
static int overlap(const void *a,size_t an,const void *b,size_t bn){
    uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    if(!an||!bn)return 0;
    return av<=bv?bv-av<an:av-bv<bn;
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
CohStatus coh_asset_geo_workspace(CohBytes b,size_t *required){uint32_t v;
size_t o,p,n,d;
if(!required)return COH_INVALID;
CohStatus s=envelope(b,&v,&o,&p,&n,&d);
if(s!=COH_OK)return s;
if(n>SIZE_MAX-INFLATE_ARENA)return COH_LIMIT;
*required=n+INFLATE_ARENA;
return COH_OK;
}
static CohStatus record_at(const CohAssetGeo *g,uint32_t index,CohBytes *rec){
    if(!g||!rec||index>=g->model_count)return COH_INVALID;
size_t pos=g->records_offset;

    for(uint32_t i=0;i<=index;i++){size_t bytes=216;
if(g->version>=3){if(!span(g->header.size,pos,4))return COH_INVALID;
bytes=u32(g->header.data+pos);
}
        if(bytes<204||bytes>4096||!span(g->header.size,pos,bytes))return COH_INVALID;
if(i==index){rec->data=g->header.data+pos;
rec->size=bytes;
return COH_OK;
}pos+=bytes;
}
    return COH_INVALID;

}
static CohStatus model_read(const CohAssetGeo *g,uint32_t index,CohAssetGeoModel *out,int scale_only){
    if(!out)return COH_INVALID;
CohBytes rec;
CohStatus s=record_at(g,index,&rec);
if(s!=COH_OK)return s;
const uint8_t *p=rec.data;
CohAssetGeoModel m;
memset(&m,0,sizeof(m));
size_t nameoff,scaleoff,packoff;

    if(g->version<3){nameoff=80;
scaleoff=92;
packoff=132;
m.material_count=u32(p+12);
m.bone_info_offset=u32(p+20);
m.vertex_count=u32(p+28);
m.triangle_count=u32(p+32);
m.material_offset=u32(p+36);
m.pack_count=8;
}
    else {CohGeoModel old;
int r=coh_geo_model(p,rec.size,g->version,&old);
if(r)return r==2?COH_UNSUPPORTED:COH_INVALID;
m.material_count=old.texture_count;
m.bone_info_offset=old.bone_info_offset;
m.vertex_count=old.vertex_count;
m.triangle_count=old.triangle_count;
m.material_offset=old.texture_index_offset;
m.pack_count=old.pack_count;
nameoff=old.version>=8?64:60;
scaleoff=old.version>=8?72:68;
packoff=old.version>=8?108:104;
}
    int metadata_only=scale_only&&g->version==0&&!m.vertex_count&&!m.triangle_count&&!m.material_count;
if(!metadata_only&&(!m.vertex_count||!m.triangle_count||!m.material_count))return COH_INVALID;
if(m.vertex_count>INT32_MAX||m.triangle_count>INT32_MAX||!span(g->material_ids.size,m.material_offset,(size_t)m.material_count*4))return COH_INVALID;

    m.name=name(g->model_names,u32(p+nameoff));
if(!m.name)return COH_INVALID;

    for(unsigned i=0;i<3;i++){m.scale[i]=f32(p+scaleoff+i*4);
if(!isfinite(m.scale[i]))return COH_INVALID;
}
    if(g->version<3){for(unsigned i=0;i<7;i++){const uint8_t *q=p+packoff+i*12;
unsigned j=i>=4?i+1:i;
m.packs[j]=(CohPack32){u32(q),u32(q+4),u32(q+8)};
}}
    else {for(uint32_t i=0;i<m.pack_count;i++){const uint8_t *q=p+packoff+i*12;
m.packs[i]=(CohPack32){u32(q),u32(q+4),u32(q+8)};
}}
    for(uint32_t i=0;i<m.pack_count;i++){CohPack32 a=m.packs[i];
if((!metadata_only&&a.packed_bytes&&!a.unpacked_bytes)||!span(g->payload.size,a.offset,a.packed_bytes?a.packed_bytes:a.unpacked_bytes))return COH_INVALID;
}
    uint64_t triangles=0;
for(uint32_t i=0;i<m.material_count;i++){const uint8_t *q=g->material_ids.data+m.material_offset+i*4;
if(u16(q)>=g->texture_count)return COH_INVALID;
triangles+=u16(q+2);
}
    if(triangles!=m.triangle_count)return COH_INVALID;
*out=m;
return COH_OK;

}
CohStatus coh_asset_geo_model(const CohAssetGeo*g,uint32_t i,CohAssetGeoModel*out){return model_read(g,i,out,0);}
CohStatus coh_asset_geo_scale_model(const CohAssetGeo*g,uint32_t i,CohAssetGeoModel*out){return model_read(g,i,out,1);}
static CohStatus geo_open(CohBytes b,uint8_t *workspace,size_t cap,uint32_t maxmodels,CohAssetGeo *out,int scale_only){
    if(!workspace||!out||!maxmodels||maxmodels>(1u<<20))return COH_INVALID;
uint32_t v;
size_t o,p,n,d;
CohStatus s=envelope(b,&v,&o,&p,&n,&d);
if(s!=COH_OK)return s;

    if(n>cap||cap-n<INFLATE_ARENA)return COH_LIMIT;
if(overlap(workspace,cap,b.data,b.size))return COH_INVALID;

    CohBytes compressed={b.data+o,p};
s=inflate_exact(compressed,workspace,n,workspace+n,cap-n);
if(s!=COH_OK)return s;

    CohAssetGeo g;
memset(&g,0,sizeof(g));
g.version=v;
g.header=(CohBytes){workspace,n};
unsigned fields=(v>=2&&v<=6)?5:4;
size_t pos=fields*4;

    if(n<pos||u32(workspace)!=b.size-d)return COH_INVALID;
g.payload=(CohBytes){b.data+d,b.size-d};

    CohBytes *blocks[3]={&g.texture_names,&g.model_names,&g.material_ids};

    for(unsigned i=0;i<3;i++){uint32_t size=u32(workspace+(i+1)*4);
if(!span(n,pos,size))return COH_INVALID;
*blocks[i]=(CohBytes){workspace+pos,size};
pos+=size;
}
    if(fields==5){uint32_t lod=u32(workspace+16);
if(!span(n,pos,lod))return COH_INVALID;
pos+=lod;
}
    if(!span(n,pos,140)||g.texture_names.size<4)return COH_INVALID;
g.model_count=u32(workspace+pos+136);
g.records_offset=pos+140;
g.texture_count=u32(g.texture_names.data);

    if(!g.model_count||g.model_count>maxmodels||g.texture_count>(g.texture_names.size-4)/4)return COH_LIMIT;

    for(uint32_t i=0;i<g.texture_count;i++){size_t base=4+(size_t)g.texture_count*4;
uint32_t off=u32(g.texture_names.data+4+i*4);
if(!span(g.texture_names.size,base,off)||!name(g.texture_names,base+off))return COH_INVALID;
}
    size_t cursor=g.records_offset;
    for(uint32_t i=0;i<g.model_count;i++){
        CohAssetGeo one=g; one.records_offset=cursor; one.model_count=1;
        CohAssetGeoModel model; CohBytes record;
        s=model_read(&one,0,&model,scale_only);
        if(s!=COH_OK)return s;
        s=record_at(&one,0,&record);
        if(s!=COH_OK)return s;
        cursor+=record.size;
    }
    if(cursor!=n)return COH_INVALID;
*out=g;
return COH_OK;

}
CohStatus coh_asset_geo_open(CohBytes b,uint8_t*w,size_t n,uint32_t max,CohAssetGeo*out){return geo_open(b,w,n,max,out,0);}
CohStatus coh_asset_geo_open_scales(CohBytes b,uint8_t*w,size_t n,uint32_t max,CohAssetGeo*out){return geo_open(b,w,n,max,out,1);}
CohStatus coh_asset_geo_material(const CohAssetGeo *g,const CohAssetGeoModel *m,uint32_t index,CohAssetGeoMaterial *out){
    if(!g||!m||!out||index>=m->material_count||!span(g->material_ids.size,m->material_offset,(size_t)m->material_count*4))return COH_INVALID;

    uint32_t first=0;
for(uint32_t i=0;i<index;i++)first+=u16(g->material_ids.data+m->material_offset+i*4+2);

    const uint8_t *p=g->material_ids.data+m->material_offset+index*4;
uint32_t id=u16(p);
if(id>=g->texture_count)return COH_INVALID;

    const char *path=name(g->texture_names,4+(size_t)g->texture_count*4+u32(g->texture_names.data+4+id*4));
if(!path)return COH_INVALID;

    CohAssetGeoMaterial material={path,id,first,u16(p+2)};
*out=material;
return COH_OK;

}
CohStatus coh_asset_geo_stream(const CohAssetGeo *g,const CohAssetGeoModel *m,uint32_t index,uint8_t *out,size_t cap,void *scratch,size_t sn,size_t *bytes){
    if(!g||!m||!bytes||index>=m->pack_count)return COH_INVALID;
CohPack32 p=m->packs[index];
if(p.unpacked_bytes>cap)return COH_LIMIT;

    if(!span(g->payload.size,p.offset,p.packed_bytes?p.packed_bytes:p.unpacked_bytes)||(!out&&p.unpacked_bytes))return COH_INVALID;

    CohStatus s=COH_OK;
if(p.packed_bytes){CohBytes in={g->payload.data+p.offset,p.packed_bytes};
s=inflate_exact(in,out,p.unpacked_bytes,scratch,sn);
}else if(p.unpacked_bytes)memmove(out,g->payload.data+p.offset,p.unpacked_bytes);

    if(s==COH_OK)*bytes=p.unpacked_bytes;
return s;

}
static CohStatus delta(CohBytes b,uint32_t count,uint32_t stride,int floats,void *out,size_t capacity){
    if(!b.data||!out||!count||!stride||stride>3||count>SIZE_MAX/stride)return COH_INVALID;
size_t elements=(size_t)count*stride;
if(elements>capacity||elements>(SIZE_MAX-7)/2||elements>SIZE_MAX/4)return COH_LIMIT;
if(overlap(b.data,b.size,out,elements*4))return COH_INVALID;

    size_t codes=(elements*2+7)/8;
if(!span(b.size,codes,1)||b.data[codes]>30)return COH_INVALID;
float inverse=1.f/(float)(1u<<b.data[codes]);

    for(unsigned pass=0;pass<2;pass++){
        size_t pos=codes+1;
float lastf[3]={0,0,0};
int64_t lasti[3]={0,0,0};

        for(size_t i=0;i<elements;i++){
            unsigned code=(b.data[i/4]>>(2*(i%4)))&3u,width=code==3?4:code;
int64_t integer=0;
float value=0;

            if(!span(b.size,pos,width))return COH_INVALID;

            if(code==1)integer=(int)b.data[pos]-127;
else if(code==2)integer=(int)u16(b.data+pos)-32767;
else if(code==3){uint32_t v=u32(b.data+pos);
integer=v<=INT32_MAX?v:(int64_t)v-4294967296LL;
if(floats)value=f32(b.data+pos);
}pos+=width;
unsigned j=(unsigned)(i%stride);

            if(floats){if(code!=3)value=(float)integer*inverse;
value=lastf[j]+value;
if(!isfinite(value))return COH_INVALID;
lastf[j]=value;
if(pass)((float*)out)[i]=value;
}
            else {integer+=lasti[j]+1;
if(integer<0||integer>UINT32_MAX)return COH_INVALID;
lasti[j]=integer;
if(pass)((uint32_t*)out)[i]=(uint32_t)integer;
}
        }
        if(pos!=b.size)return COH_INVALID;

    }return COH_OK;

}
CohStatus coh_asset_delta_floats(CohBytes b,uint32_t n,uint32_t stride,float *out,size_t cap){return delta(b,n,stride,1,out,cap);
}
CohStatus coh_asset_delta_indices(CohBytes b,uint32_t n,uint32_t *out,size_t cap){return delta(b,n,3,0,out,cap);
}
