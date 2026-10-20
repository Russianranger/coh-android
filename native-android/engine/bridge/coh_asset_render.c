#include "coh_asset_render.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <limits.h>

#define NO_TEXTURE UINT32_MAX
typedef struct { size_t size; } Allocation;
typedef struct {
    char path[COH_ASSET_PATH_MAX+1]; uint32_t generation,width,height,refs,handle;
    uint8_t *rgba; size_t bytes; uint64_t last;
} Texture;
typedef struct {
    CohRenderGeometry geometry; CohRenderMaterial material;
    uint32_t textures[3],texture_count;
} Part;
struct CohBridgeMesh {
    CohAssetRenderBridge *owner;
    char path[COH_ASSET_PATH_MAX+1],name[COH_ASSET_PATH_MAX+1];
    uint32_t generation,resolver_generation,pins,part_count,source_part_mask;
    uint64_t last; Part parts[];
};
struct CohAssetRenderBridge {
    CohAssetLoader *loader; CohBridgeLimits limits;
    CohBridgeTextureBackend backend; CohBridgeStats stats;
    CohBridgeMesh **meshes; Texture *textures; uint64_t clock;
};
static int cancelled(CohCancel c) { return c.poll&&c.poll(c.context); }
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
CohStatus coh_bridge_argb8888(CohBytes d,uint8_t *rgba,size_t cap,uint32_t *width,uint32_t *height) {
    if(!d.data||!width||!height||d.size<128||memcmp(d.data,"DDS ",4)||
       u32(d.data+4)!=124||u32(d.data+76)!=32)return COH_INVALID;
    const uint8_t *p=d.data;
    if(u32(p+80)!=65||u32(p+84)||u32(p+88)!=32||u32(p+92)!=0xff0000||
       u32(p+96)!=0xff00||u32(p+100)!=0xff||u32(p+104)!=0xff000000||
       u32(p+24)>1||u32(p+112))return COH_UNSUPPORTED;
    uint32_t w=u32(p+16),h=u32(p+12),levels=u32(p+28);
    if(!w||!h||w>16384||h>16384)return COH_INVALID;
    if(!levels)levels=1;
    uint32_t maxlevels=1,n=w>h?w:h;while(n>1){n>>=1;maxlevels++;}
    if(levels>maxlevels)return COH_INVALID;
    size_t total=128;uint32_t mw=w,mh=h;
    for(uint32_t i=0;i<levels;i++) {
        size_t bytes=(size_t)mw*mh*4;
        if(bytes>d.size-total)return COH_INVALID;
        total+=bytes;mw=mw>1?mw/2:1;mh=mh>1?mh/2:1;
    }
    if(total!=d.size)return COH_INVALID;
    size_t bytes=(size_t)w*h*4;
    if(!rgba&&cap)return COH_INVALID;
    if(rgba) {
        if(cap<bytes)return COH_LIMIT;
        uintptr_t a=(uintptr_t)d.data,b=(uintptr_t)rgba;
        if(a<=b?b-a<d.size:a-b<bytes)return COH_INVALID;
        for(size_t i=0;i<bytes;i+=4) {
            rgba[i]=p[128+i+2];rgba[i+1]=p[128+i+1];rgba[i+2]=p[128+i];rgba[i+3]=p[128+i+3];
        }
    }
    *width=w;*height=h;return COH_OK;
}
static CohStatus texture_view(CohBytes bytes,CohAssetTexture *out,int *argb) {
    CohStatus s=coh_asset_texture(bytes,out);*argb=0;if(s!=COH_UNSUPPORTED)return s;
    CohAssetTexture tex;memset(&tex,0,sizeof(tex));tex.dds=bytes;
    if(bytes.size<4)return COH_INVALID;
    if(memcmp(bytes.data,"DDS ",4)) {
        if(bytes.size<33)return COH_INVALID;
        const uint8_t *p=bytes.data;uint32_t off=u32(p);
        if(off<33||off>bytes.size||off>COH_ASSET_PATH_MAX+32+65536||
           u32(p+4)!=bytes.size-off||!memchr(p+32,0,off-32))return COH_INVALID;
        if(memcmp(p+29,"TEX",3)&&memcmp(p+29,"TX2",3))return COH_UNSUPPORTED;
        tex.dds=(CohBytes){p+off,bytes.size-off};tex.name=(const char *)p+32;
        tex.flags=u32(p+16);memcpy(tex.fade,p+20,8);tex.alpha=p[28];
        if(!isfinite(tex.fade[0])||!isfinite(tex.fade[1]))return COH_INVALID;
    }
    s=coh_bridge_argb8888(tex.dds,NULL,0,&tex.width,&tex.height);if(s!=COH_OK)return s;
    if(tex.name&&(tex.width!=u32(bytes.data+8)||tex.height!=u32(bytes.data+12)))return COH_INVALID;
    *argb=1;*out=tex;return COH_OK;
}
static int same(const char *a,const char *b) {
    if(!a||!b)return 0;
    for(;;a++,b++) {
        unsigned char x=(unsigned char)*a,y=(unsigned char)*b;
        if(x=='\\')x='/';
        if(y=='\\')y='/';
        if(x>='A'&&x<='Z')x=(unsigned char)(x+32);
        if(y>='A'&&y<='Z')y=(unsigned char)(y+32);
        if(x!=y)return 0;
        if(!x)return 1;
    }
}
static int copy_path(char out[COH_ASSET_PATH_MAX+1],const char *in) {
    if(!in)return 0;
    size_t n=0;while(n<=COH_ASSET_PATH_MAX&&in[n])n++;
    if(!n||n>COH_ASSET_PATH_MAX)return 0;
    memcpy(out,in,n+1);return 1;
}
static void *allocate(CohAssetRenderBridge *b,size_t n) {
    if(!n||n>SIZE_MAX-sizeof(Allocation))return NULL;
    size_t bytes=n+sizeof(Allocation);
    if(bytes>b->limits.total_bytes-b->stats.allocated_bytes)return NULL;
    Allocation *a=calloc(1,bytes);if(!a)return NULL;
    a->size=bytes;b->stats.allocated_bytes+=bytes;
    if(b->stats.allocated_bytes>b->stats.peak_allocated_bytes)
        b->stats.peak_allocated_bytes=b->stats.allocated_bytes;
    return a+1;
}
static void deallocate(CohAssetRenderBridge *b,void *p) {
    if(p) { Allocation *a=(Allocation *)p-1;b->stats.allocated_bytes-=a->size;free(a); }
}
static void texture_free(CohAssetRenderBridge *b,uint32_t i,int alive) {
    Texture *t=b->textures+i;
    if(t->handle)b->backend.release(b->backend.context,t->handle,alive);
    if(t->rgba) { deallocate(b,t->rgba);b->stats.textures--; }
    memset(t,0,sizeof(*t));
}
static void mesh_free(CohAssetRenderBridge *b,CohBridgeMesh *m) {
    if(!m)return;
    for(uint32_t p=0;p<m->part_count;p++) {
        Part *part=m->parts+p;
        for(uint32_t j=0;j<part->texture_count;j++)
            if(part->textures[j]!=NO_TEXTURE)b->textures[part->textures[j]].refs--;
        deallocate(b,(void *)part->geometry.vertices);
        deallocate(b,(void *)part->geometry.indices);
    }
    deallocate(b,m);
}
static int evict_mesh(CohAssetRenderBridge *b) {
    uint32_t at=UINT32_MAX;uint64_t last=UINT64_MAX;
    for(uint32_t i=0;i<b->limits.meshes;i++) {
        CohBridgeMesh *m=b->meshes[i];
        if(m&&!m->pins&&m->last<last) {at=i;last=m->last;}
    }
    if(at==UINT32_MAX)return 0;
    mesh_free(b,b->meshes[at]);b->meshes[at]=NULL;
    b->stats.meshes--;b->stats.evictions++;return 1;
}
static int evict_texture(CohAssetRenderBridge *b) {
    uint32_t at=UINT32_MAX;uint64_t last=UINT64_MAX;
    for(uint32_t i=0;i<b->limits.textures;i++) {
        Texture *t=b->textures+i;
        if(t->rgba&&!t->refs&&t->last<last) {at=i;last=t->last;}
    }
    if(at==UINT32_MAX)return 0;
    texture_free(b,at,1);b->stats.evictions++;return 1;
}
static void *room(CohAssetRenderBridge *b,size_t n) {
    void *p=allocate(b,n);
    while(!p&&(evict_texture(b)||evict_mesh(b)))p=allocate(b,n);
    return p;
}
CohBridgeLimits coh_bridge_default_limits(void) {
    CohBridgeLimits v={32u<<20,2u<<20,4u<<20,32,64,8192,65536,65536,64};return v;
}
CohStatus coh_bridge_create(CohAssetLoader *l,const CohBridgeLimits *limits,
    const CohBridgeTextureBackend *backend,CohAssetRenderBridge **out) {
    if(!l||!limits||!backend||!backend->upload||!backend->release||!out)return COH_INVALID;
    if(!limits->meshes||limits->meshes>4096||!limits->textures||limits->textures>4096||
       !limits->max_models||limits->max_models>(1u<<20)||!limits->max_vertices||
       limits->max_vertices>(1u<<24)||!limits->max_triangles||limits->max_triangles>(1u<<24)||
       !limits->max_materials||limits->max_materials>4096||!limits->max_workspace_bytes||
       !limits->max_stream_bytes||limits->total_bytes<sizeof(CohAssetRenderBridge))return COH_INVALID;
    CohAssetRenderBridge *b=calloc(1,sizeof(*b));if(!b)return COH_LIMIT;
    b->loader=l;b->limits=*limits;b->backend=*backend;
    b->stats.allocated_bytes=b->stats.peak_allocated_bytes=sizeof(*b);
    b->meshes=allocate(b,(size_t)limits->meshes*sizeof(*b->meshes));
    b->textures=allocate(b,(size_t)limits->textures*sizeof(*b->textures));
    if(!b->meshes||!b->textures) {
        deallocate(b,b->meshes);deallocate(b,b->textures);free(b);return COH_LIMIT;
    }
    *out=b;return COH_OK;
}
CohStatus coh_bridge_destroy(CohAssetRenderBridge **ptr,int alive) {
    if(!ptr)return COH_INVALID;
    if(!*ptr)return COH_OK;
    CohAssetRenderBridge *b=*ptr;if(b->stats.pins)return COH_STATE;
    for(uint32_t i=0;i<b->limits.meshes;i++)mesh_free(b,b->meshes[i]);
    for(uint32_t i=0;i<b->limits.textures;i++)texture_free(b,i,alive);
    deallocate(b,b->meshes);deallocate(b,b->textures);free(b);*ptr=NULL;return COH_OK;
}
static CohStatus texture_get(CohAssetRenderBridge *b,CohAssetId id,CohCancel cancel,uint32_t *out) {
    CohAssetInfo info;CohStatus s=coh_asset_lookup(b->loader,id,&info);if(s!=COH_OK)return s;
    for(uint32_t i=0;i<b->limits.textures;i++) {
        Texture *t=b->textures+i;
        if(t->rgba&&t->generation==info.id.generation&&same(t->path,info.id.path)) {
            if(t->refs==UINT32_MAX)return COH_LIMIT;
            t->refs++;t->last=++b->clock;b->stats.texture_hits++;*out=i;return COH_OK;
        }
    }
    uint32_t slot=UINT32_MAX;
    for(;;) {
        for(uint32_t i=0;i<b->limits.textures;i++)if(!b->textures[i].rgba){slot=i;break;}
        if(slot!=UINT32_MAX)break;
        if(!evict_texture(b)&&!evict_mesh(b))return COH_LIMIT;
    }
    const CohAssetBlob *blob=NULL;s=coh_asset_acquire(b->loader,info.id,cancel,&blob);
    if(s!=COH_OK)return s;
    CohAssetTexture tex;int argb=0;s=texture_view(coh_asset_bytes(blob),&tex,&argb);
    uint8_t *rgba=NULL;size_t bytes=0;
    if(s==COH_OK) {
        if(!tex.width||!tex.height||tex.width>SIZE_MAX/4/tex.height)s=COH_LIMIT;
        else { bytes=(size_t)tex.width*tex.height*4;rgba=room(b,bytes);if(!rgba)s=COH_LIMIT; }
    }
    if(s==COH_OK)s=argb?coh_bridge_argb8888(tex.dds,rgba,bytes,&tex.width,&tex.height):
        coh_asset_texture_rgba(&tex,0,rgba,bytes);
    if(s==COH_OK&&cancelled(cancel))s=COH_CANCELLED;
    if(s==COH_OK) {
        Texture *t=b->textures+slot;
        if(!copy_path(t->path,info.id.path))s=COH_INVALID;
        else {
            t->generation=info.id.generation;t->width=tex.width;t->height=tex.height;
            t->refs=1;t->rgba=rgba;t->bytes=bytes;t->last=++b->clock;
            b->stats.textures++;b->stats.texture_loads++;*out=slot;
        }
    }
    coh_asset_release(b->loader,blob);if(s!=COH_OK)deallocate(b,rgba);return s;
}
static uint64_t identity(const char *path,const char *model,uint32_t generation,uint32_t resolver) {
    uint64_t h=UINT64_C(1469598103934665603);
    const char *v[2]={path,model};
    for(unsigned j=0;j<2;j++)for(const unsigned char *p=(const unsigned char *)v[j];*p;p++) {
        unsigned char c=*p;if(c=='\\')c='/';if(c>='A'&&c<='Z')c=(unsigned char)(c+32);
        h=(h^c)*UINT64_C(1099511628211);
    }
    h=(h^generation)*UINT64_C(1099511628211);return (h^resolver)*UINT64_C(1099511628211);
}
static CohStatus stream(CohAssetRenderBridge *b,const CohAssetGeo *g,const CohAssetGeoModel *m,
    uint32_t pack,uint8_t *scratch,void *out,uint32_t count,uint32_t stride,int indices) {
    size_t n=m->packs[pack].unpacked_bytes;
    if(!n||n>b->limits.max_stream_bytes)return n?COH_LIMIT:COH_UNSUPPORTED;
    uint8_t *encoded=room(b,n);if(!encoded)return COH_LIMIT;
    size_t got=0;CohStatus s=coh_asset_geo_stream(g,m,pack,encoded,n,scratch,65536,&got);
    if(s==COH_OK) {
        CohBytes bytes={encoded,got};
        s=indices?coh_asset_delta_indices(bytes,count,out,(size_t)count*stride):
            coh_asset_delta_floats(bytes,count,stride,out,(size_t)count*stride);
    }
    deallocate(b,encoded);return s;
}
static int valid_material(const CohBridgeMaterial *r) {
    const CohRenderMaterial *m=&r->material;
    if(m->family<COH_MAT_MULTIPLY||m->family>COH_MAT_ADDGLOW||
       m->lighting<COH_LIGHT_VERTEX||m->lighting>COH_LIGHT_FIXED||
       m->blend<COH_BLEND_OPAQUE||m->blend>COH_BLEND_ADDITIVE)return 0;
    if(m->depth_test>1||m->depth_write>1||m->cull_back>1||m->front_cw>1)return 0;
    if(m->alpha_ref<0||m->alpha_ref>1||m->shininess<0||m->shininess>128)return 0;
    const float *values[]={m->const0,m->const1,m->fog_params,m->fog_color,
        m->glow_params,m->light,m->diffuse,m->ambient,m->specular,&m->shininess,&m->alpha_ref};
    const unsigned counts[]={4,4,4,4,4,3,4,4,3,1,1};
    for(unsigned i=0;i<sizeof(counts)/sizeof(counts[0]);i++)
        for(unsigned j=0;j<counts[i];j++)if(!isfinite(values[i][j]))return 0;
    for(unsigned i=0;i<3;i++) {
        CohRenderTexture t=m->textures[i];
        if(t.handle||t.wrap_s<0||t.wrap_s>COH_WRAP_MIRROR||t.wrap_t<0||t.wrap_t>COH_WRAP_MIRROR||
           t.min_filter<0||t.min_filter>COH_FILTER_LINEAR||t.mag_filter<0||t.mag_filter>COH_FILTER_LINEAR)return 0;
    }
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)
        if(!isfinite(r->uv_scale[i][j])||fabsf(r->uv_scale[i][j])>1000000.f)return 0;
    return 1;
}
CohStatus coh_bridge_acquire(CohAssetRenderBridge *b,CohAssetId id,const char *model,
    uint32_t resolver_generation,CohBridgeResolveMaterial resolve,void *context,CohCancel cancel,
    const CohBridgeMesh **out) {
    return coh_bridge_acquire_parts(b,id,model,resolver_generation,UINT32_MAX,resolve,context,cancel,out);
}
CohStatus coh_bridge_acquire_parts(CohAssetRenderBridge *b,CohAssetId id,const char *model,
    uint32_t resolver_generation,uint32_t source_part_mask,CohBridgeResolveMaterial resolve,
    void *context,CohCancel cancel,const CohBridgeMesh **out) {
    if(!b||!model||!resolve||!out||!source_part_mask)return COH_INVALID;
    if(cancelled(cancel))return COH_CANCELLED;
    CohAssetInfo info;CohStatus s=coh_asset_lookup(b->loader,id,&info);if(s!=COH_OK)return s;
    for(uint32_t i=0;i<b->limits.meshes;i++) {
        CohBridgeMesh *m=b->meshes[i];
        if(m&&m->generation==info.id.generation&&m->resolver_generation==resolver_generation&&
           m->source_part_mask==source_part_mask&&
           same(m->path,info.id.path)&&same(m->name,model)) {
            if(m->pins==UINT32_MAX||b->stats.pins==UINT32_MAX)return COH_LIMIT;
            m->pins++;m->last=++b->clock;b->stats.pins++;b->stats.mesh_hits++;*out=m;return COH_OK;
        }
    }
    uint32_t slot=UINT32_MAX;
    for(;;) {
        for(uint32_t i=0;i<b->limits.meshes;i++)if(!b->meshes[i]){slot=i;break;}
        if(slot!=UINT32_MAX)break;
        if(!evict_mesh(b))return COH_LIMIT;
    }
    const CohAssetBlob *blob=NULL;uint8_t *workspace=NULL,*scratch=NULL;
    float *positions=NULL,*normals=NULL,*uv=NULL;uint32_t *indices=NULL;CohBridgeMesh *built=NULL;
    s=coh_asset_acquire(b->loader,info.id,cancel,&blob);if(s!=COH_OK)return s;
    size_t workspace_bytes=0;s=coh_asset_geo_workspace(coh_asset_bytes(blob),&workspace_bytes);
    if(s==COH_OK&&(workspace_bytes>b->limits.max_workspace_bytes))s=COH_LIMIT;
    if(s==COH_OK) {workspace=room(b,workspace_bytes);if(!workspace)s=COH_LIMIT;}
    CohAssetGeo geo;CohAssetGeoModel gm;
    if(s==COH_OK)s=coh_asset_geo_open(coh_asset_bytes(blob),workspace,workspace_bytes,b->limits.max_models,&geo);
    if(s==COH_OK&&geo.version!=0&&geo.version!=7)s=COH_UNSUPPORTED;
    if(s==COH_OK) {
        s=COH_NOT_FOUND;
        for(uint32_t i=0;i<geo.model_count;i++) {
            CohStatus ms=coh_asset_geo_model(&geo,i,&gm);
            if(ms!=COH_OK){s=ms;break;}
            if(same(gm.name,model)){s=COH_OK;break;}
        }
    }
    uint32_t selected_parts=0;
    if(s==COH_OK) {
        if(gm.vertex_count>b->limits.max_vertices||gm.triangle_count>b->limits.max_triangles||
           gm.material_count>b->limits.max_materials||gm.material_count>32)s=COH_LIMIT;
        else if(gm.bone_info_offset||gm.scale[0]!=1.f||gm.scale[1]!=1.f||gm.scale[2]!=1.f||
                gm.packs[4].unpacked_bytes||gm.packs[5].unpacked_bytes||gm.packs[6].unpacked_bytes)s=COH_UNSUPPORTED;
        else if(source_part_mask!=UINT32_MAX&&gm.material_count<32&&
                (source_part_mask>>gm.material_count))s=COH_INVALID;
        else for(uint32_t p=0;p<gm.material_count;p++)if(source_part_mask&(UINT32_C(1)<<p))selected_parts++;
    }
    if(s==COH_OK) {
        built=room(b,sizeof(*built)+(size_t)selected_parts*sizeof(Part));
        positions=room(b,(size_t)gm.vertex_count*3*sizeof(float));
        normals=room(b,(size_t)gm.vertex_count*3*sizeof(float));
        uv=room(b,(size_t)gm.vertex_count*2*sizeof(float));
        indices=room(b,(size_t)gm.triangle_count*3*sizeof(uint32_t));scratch=room(b,65536);
        if(!built||!positions||!normals||!uv||!indices||!scratch)s=COH_LIMIT;
    }
    if(built) {
        built->owner=b;built->part_count=selected_parts;
        for(uint32_t i=0;i<built->part_count;i++)for(unsigned j=0;j<3;j++)built->parts[i].textures[j]=NO_TEXTURE;
    }
    if(s==COH_OK)s=stream(b,&geo,&gm,0,scratch,indices,gm.triangle_count,3,1);
    if(s==COH_OK)s=stream(b,&geo,&gm,1,scratch,positions,gm.vertex_count,3,0);
    if(s==COH_OK)s=stream(b,&geo,&gm,2,scratch,normals,gm.vertex_count,3,0);
    if(s==COH_OK)s=stream(b,&geo,&gm,3,scratch,uv,gm.vertex_count,2,0);
    if(s==COH_OK)for(size_t i=0;i<(size_t)gm.triangle_count*3;i++)if(indices[i]>=gm.vertex_count){s=COH_INVALID;break;}
    uint32_t target_part=0;
    for(uint32_t p=0;s==COH_OK&&p<gm.material_count;p++) {
        if(!(source_part_mask&(UINT32_C(1)<<p)))continue;
        if(cancelled(cancel)){s=COH_CANCELLED;break;}
        CohAssetGeoMaterial original;s=coh_asset_geo_material(&geo,&gm,p,&original);if(s!=COH_OK)break;
        CohBridgeMaterial r;memset(&r,0,sizeof(r));s=resolve(context,original.texture_name,&r);
        if(s!=COH_OK)break;
        if(!valid_material(&r)){s=COH_UNSUPPORTED;break;}
        Part *part=built->parts+target_part++;part->material=r.material;
        part->texture_count=r.material.family==COH_MAT_ADDGLOW?3:2;
        char paths[3][COH_ASSET_PATH_MAX+1];
        for(uint32_t j=0;j<part->texture_count;j++) {
            if(!copy_path(paths[j],r.textures[j].path)){s=COH_INVALID;break;}
            r.textures[j].path=paths[j];
        }
        for(uint32_t j=0;s==COH_OK&&j<part->texture_count;j++)
            s=texture_get(b,r.textures[j],cancel,part->textures+j);
        if(s!=COH_OK)break;
        CohRenderVertex *vertices=room(b,(size_t)gm.vertex_count*sizeof(*vertices));
        part->geometry.vertices=vertices;
        uint32_t *part_indices=room(b,(size_t)original.triangle_count*3*sizeof(*part_indices));
        part->geometry.indices=part_indices;
        if(!vertices||!part_indices){s=COH_LIMIT;break;}
        for(uint32_t i=0;i<gm.vertex_count;i++) {
            CohRenderVertex *v=vertices+i;memcpy(v->position,positions+i*3,12);memcpy(v->normal,normals+i*3,12);
            float flipped=1.f-uv[i*2+1];
            v->uv0[0]=uv[i*2]*r.uv_scale[0][0];v->uv0[1]=flipped*r.uv_scale[0][1];
            v->uv1[0]=uv[i*2]*r.uv_scale[1][0];v->uv1[1]=flipped*r.uv_scale[1][1];
            if(!isfinite(v->uv0[0])||!isfinite(v->uv0[1])||!isfinite(v->uv1[0])||!isfinite(v->uv1[1])){s=COH_INVALID;break;}
            for(unsigned j=0;j<4;j++)v->color[j]=1.f;
        }
        memcpy(part_indices,indices+(size_t)original.first_triangle*3,(size_t)original.triangle_count*3*sizeof(uint32_t));
        part->geometry.vertex_count=gm.vertex_count;part->geometry.index_count=(size_t)original.triangle_count*3;
        part->geometry.identity=identity(info.id.path,gm.name,info.id.generation,resolver_generation)^(uint64_t)p;
        part->geometry.generation=info.id.generation;
    }
    if(s==COH_OK&&(!copy_path(built->path,info.id.path)||!copy_path(built->name,gm.name)))s=COH_INVALID;
    deallocate(b,indices);deallocate(b,uv);deallocate(b,normals);deallocate(b,positions);
    deallocate(b,scratch);deallocate(b,workspace);coh_asset_release(b->loader,blob);
    if(s!=COH_OK){mesh_free(b,built);b->stats.rejections++;return s;}
    built->generation=info.id.generation;built->resolver_generation=resolver_generation;
    built->source_part_mask=source_part_mask;
    built->pins=1;built->last=++b->clock;b->meshes[slot]=built;
    b->stats.meshes++;b->stats.pins++;b->stats.mesh_loads++;*out=built;return COH_OK;
}
static int owned(const CohAssetRenderBridge *b,const CohBridgeMesh *m) {
    if(!b||!m)return 0;
    for(uint32_t i=0;i<b->limits.meshes;i++)if(b->meshes[i]==m)return m->pins!=0;
    return 0;
}
void coh_bridge_release(CohAssetRenderBridge *b,const CohBridgeMesh *m) {
    if(owned(b,m)) { ((CohBridgeMesh *)m)->pins--;b->stats.pins--; }
}
uint32_t coh_bridge_mesh_parts(const CohBridgeMesh *m) {return m?m->part_count:0;}
const char *coh_bridge_mesh_name(const CohBridgeMesh *m) {return m?m->name:NULL;}
CohStatus coh_bridge_mesh_part(const CohBridgeMesh *m,uint32_t p,CohRenderGeometry *g,CohRenderMaterial *mat) {
    if(!m||!m->pins||!g||!mat||p>=m->part_count)return COH_INVALID;
    Part *part=(Part *)m->parts+p;*g=part->geometry;*mat=part->material;
    for(uint32_t j=0;j<part->texture_count;j++)mat->textures[j].handle=m->owner->textures[part->textures[j]].handle;
    return COH_OK;
}
CohStatus coh_bridge_prepare(CohAssetRenderBridge *b,const CohBridgeMesh *m,CohCancel cancel) {
    if(!owned(b,m))return COH_STATE;
    for(uint32_t p=0;p<m->part_count;p++)for(uint32_t j=0;j<m->parts[p].texture_count;j++) {
        if(cancelled(cancel))return COH_CANCELLED;
        Texture *t=b->textures+m->parts[p].textures[j];
        if(!t->handle) {
            CohAssetId id={t->path,t->generation};uint32_t handle=0;CohBytes rgba={t->rgba,t->bytes};
            CohStatus s=b->backend.upload(b->backend.context,id,t->width,t->height,rgba,b->stats.surface_generation,&handle);
            if(s!=COH_OK||!handle) {if(handle)b->backend.release(b->backend.context,handle,1);return s==COH_OK?COH_INVALID:s;}
            t->handle=handle;b->stats.uploads++;
        }
    }
    return COH_OK;
}
CohStatus coh_bridge_submit(CohAssetRenderBridge *b,const CohBridgeMesh *m,CohRenderer *renderer,
    const float mv[16],const float projection[16]) {
    if(!owned(b,m)||!renderer||!mv||!projection)return COH_INVALID;
    if(coh_renderer_stats(renderer).surface_generation!=b->stats.surface_generation)return COH_STATE;
    for(uint32_t p=0;p<m->part_count;p++) {
        CohRenderDraw d;memset(&d,0,sizeof(d));
        CohStatus s=coh_bridge_mesh_part(m,p,&d.geometry,&d.material);if(s!=COH_OK)return s;
        for(uint32_t j=0;j<m->parts[p].texture_count;j++)if(!d.material.textures[j].handle)return COH_STATE;
        memcpy(d.model_view,mv,sizeof(d.model_view));memcpy(d.projection,projection,sizeof(d.projection));
        s=coh_renderer_submit(renderer,&d);if(s!=COH_OK)return s;
    }
    return COH_OK;
}
CohStatus coh_bridge_surface_lost(CohAssetRenderBridge *b,uint32_t generation,int alive) {
    if(!b)return COH_INVALID;
    if(generation==b->stats.surface_generation)return COH_STATE;
    for(uint32_t i=0;i<b->limits.textures;i++) {
        Texture *t=b->textures+i;
        if(t->handle)b->backend.release(b->backend.context,t->handle,alive);
        t->handle=0;
    }
    b->stats.surface_generation=generation;return COH_OK;
}
void coh_bridge_trim(CohAssetRenderBridge *b,int alive) {
    if(!b)return;
    while(evict_mesh(b)) {}
    for(uint32_t i=0;i<b->limits.textures;i++)if(!b->textures[i].refs)texture_free(b,i,alive);
}
CohBridgeStats coh_bridge_stats(const CohAssetRenderBridge *b) {
    CohBridgeStats s;memset(&s,0,sizeof(s));return b?b->stats:s;
}
