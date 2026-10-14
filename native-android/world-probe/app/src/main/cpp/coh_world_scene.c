#include "coh_world_scene.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const uint8_t*p){uint32_t b=u32(p);float f;memcpy(&f,&b,4);return f;}
static int zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
int coh_world_scene_parse(const uint8_t*b,size_t n,CohWorldScene*out){
    if(!b||!out||n<128||n>16u*1024u*1024u||memcmp(b,"COHWOR09",8)||u32(b+8)!=1||u32(b+12)!=128||!u32(b+16)||u32(b+16)>COH_WORLD_PARTS||!u32(b+20)||u32(b+20)>COH_WORLD_TEXTURES||u32(b+32)!=128||u32(b+36)!=96||u32(b+40)!=128+u32(b+16)*96||u32(b+44)!=32||u32(b+48)!=u32(b+40)+u32(b+20)*32||u32(b+52)!=520||u32(b+56)!=u32(b+48)+520||u32(b+60)!=n||!zero(b+64,64))return 1;
    size_t cursor=u32(b+56);if(cursor>n)return 1;
    CohWorldScene s={0};s.bytes=b;s.byte_count=n;s.part_count=u32(b+16);s.texture_count=u32(b+20);
    if(coh_world_parse_inputs(b+u32(b+48),520,&s.inputs))return 1;
    for(unsigned i=0;i<s.part_count;i++){
        const uint8_t*r=b+128+i*96;CohWorldPart*p=&s.parts[i];uint32_t bytes=u32(r+4);
        if(u32(r)!=cursor||!bytes||bytes>n-cursor||u32(r+8)>=6||u32(r+12)>=s.texture_count||u32(r+16)>=s.texture_count||(u32(r+20)&~3u)||u32(r+68)>1||!zero(r+72,24))return 1;
        if(coh_mesh_parse(b+cursor,bytes,&p->mesh)||p->mesh.bone_count!=1)return 1;
        p->node=u32(r+8);p->base_texture=u32(r+12);p->dual_texture=u32(r+16);p->flags=u32(r+20);p->mode=u32(r+68);
        for(unsigned k=0;k<4;k++){p->const0[k]=f32(r+24+k*4);p->const1[k]=f32(r+40+k*4);if(!isfinite(p->const0[k])||!isfinite(p->const1[k])||p->const0[k]<0||p->const0[k]>1||p->const1[k]<0||p->const1[k]>1)return 1;}
        p->diffuse_scale=f32(r+56);p->ambient_scale=f32(r+60);p->alpha_ref=f32(r+64);
        if(!isfinite(p->diffuse_scale)||!isfinite(p->ambient_scale)||p->diffuse_scale<0||p->diffuse_scale>2||p->ambient_scale<0||p->ambient_scale>2||!isfinite(p->alpha_ref)||p->alpha_ref<0||p->alpha_ref>1)return 1;
        if(p->mesh.vertex_count>65536-s.vertices||p->mesh.index_count>196608-s.indices)return 1;
        s.vertices+=p->mesh.vertex_count;s.indices+=p->mesh.index_count;
        for(uint32_t v=0;v<p->mesh.vertex_count;v++){CohMeshVertex x;if(coh_mesh_vertex(&p->mesh,v,&x)||x.weights[0]!=1||x.weights[1]!=0||x.bones[0]||x.bones[1])return 1;}
        cursor+=bytes;
    }
    for(unsigned i=0;i<s.texture_count;i++){
        const uint8_t*r=b+u32(b+40)+i*32;CohWorldTexture*t=&s.textures[i];t->bytes=u32(r+4);t->width=u32(r+8);t->height=u32(r+12);
        if(!t->width||!t->height||t->width>4096||t->height>4096||u32(r)!=cursor||t->bytes!=(size_t)t->width*t->height*4||t->bytes>n-cursor||!zero(r+16,16))return 1;
        t->rgba=b+cursor;cursor+=t->bytes;
    }
    if(cursor!=n||s.vertices!=u32(b+24)||s.indices!=u32(b+28))return 1;
    *out=s;return 0;
}
