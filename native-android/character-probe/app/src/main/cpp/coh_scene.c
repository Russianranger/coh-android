#include "coh_scene.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const uint8_t*p){uint32_t b=u32(p);float f;memcpy(&f,&b,4);return f;}
static int zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
int coh_scene_parse(const uint8_t*b,size_t n,CohScene*out){
    if(!b||!out||n<128||n>16u*1024u*1024u||memcmp(b,"COHCHAR8",8)||u32(b+8)!=1||u32(b+12)!=128||u32(b+16)!=COH_SCENE_PARTS||!u32(b+20)||u32(b+20)>COH_SCENE_TEXTURES||u32(b+24)!=128||u32(b+28)!=128||u32(b+32)!=1536||u32(b+36)!=32||u32(b+40)!=1536+u32(b+20)*32||u32(b+44)!=n||u32(b+48)!=2626||u32(b+52)!=8958||u32(b+56)!=620||!zero(b+60,68))return 1;
    size_t cursor=u32(b+40);if(cursor>n)return 1;
    CohScene s={0};s.bytes=b;s.byte_count=n;s.part_count=COH_SCENE_PARTS;s.texture_count=u32(b+20);
    for(unsigned i=0;i<s.part_count;i++){
        const uint8_t*r=b+128+i*128;CohScenePart*p=&s.parts[i];uint32_t bytes=u32(r+4);
        if(u32(r)!=cursor||!bytes||bytes>n-cursor||u32(r+8)>=99||u32(r+12)>=s.texture_count||u32(r+16)>=s.texture_count||u32(r+20)!=(i==7?3u:i==8?1u:0u)||u32(r+24)!=i||u32(r+28)||!zero(r+76,52))return 1;
        if(coh_mesh_parse(b+cursor,bytes,&p->mesh))return 1;
        p->socket=u32(r+8);p->base_texture=u32(r+12);p->dual_texture=u32(r+16);
        p->flags=u32(r+20);
        for(unsigned k=0;k<4;k++){p->const0[k]=f32(r+32+k*4);p->const1[k]=f32(r+48+k*4);if(!isfinite(p->const0[k])||!isfinite(p->const1[k])||p->const0[k]<0||p->const0[k]>1||p->const1[k]<0||p->const1[k]>1)return 1;}
        p->diffuse_scale=f32(r+64);p->ambient_scale=f32(r+68);p->alpha_ref=f32(r+72);
        if(p->diffuse_scale!=1||p->ambient_scale!=1||!isfinite(p->alpha_ref)||p->alpha_ref!=0)return 1;
        s.vertices+=p->mesh.vertex_count;s.indices+=p->mesh.index_count;
        for(uint32_t v=0;v<p->mesh.vertex_count;v++){CohMeshVertex x;if(coh_mesh_vertex(&p->mesh,v,&x))return 1;if(x.weights[1]>0&&x.weights[1]<1)s.blended_vertices++;}
        cursor+=bytes;
    }
    for(unsigned i=0;i<s.texture_count;i++){
        const uint8_t*r=b+1536+i*32;CohSceneTexture*t=&s.textures[i];t->width=u32(r);t->height=u32(r+4);t->bytes=u32(r+12);
        if(!t->width||!t->height||t->width>4096||t->height>4096||u32(r+8)!=cursor||t->bytes!=(size_t)t->width*t->height*4||t->bytes>n-cursor||!zero(r+16,16))return 1;
        t->rgba=b+cursor;cursor+=t->bytes;
    }
    if(cursor!=n||s.vertices!=2626||s.indices!=8958||s.blended_vertices!=620)return 1;
    *out=s;return 0;
}
