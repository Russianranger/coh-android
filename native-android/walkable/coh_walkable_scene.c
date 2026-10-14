#include "coh_walkable_scene.h"
#include <math.h>
#include <string.h>
#include <stdint.h>
_Static_assert(sizeof(CohWalkTriangle)==40,"collision record ABI differs");
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const uint8_t*p){uint32_t b=u32(p);float f;memcpy(&f,&b,4);return f;}
static int zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
int coh_walkable_scene_parse(const uint8_t*b,size_t n,CohWalkableScene*out){
    const uint32_t endian=1;
    if(!b||!out||*(const uint8_t*)&endian!=1||n<128||n>16u*1024u*1024u||memcmp(b,"COHWALK1",8)||u32(b+8)!=1||u32(b+12)!=128||!u32(b+16)||u32(b+16)>COH_WALKABLE_PARTS||!u32(b+20)||u32(b+20)>COH_WALKABLE_TEXTURES||!u32(b+24)||u32(b+24)>COH_WALK_MAX_TRIANGLES||u32(b+36)!=128||u32(b+40)!=96||u32(b+44)!=128+u32(b+16)*96||u32(b+48)!=32||u32(b+52)!=u32(b+44)+u32(b+20)*32||u32(b+56)!=40||u32(b+60)!=u32(b+52)+u32(b+24)*40||u32(b+64)!=n||!zero(b+108,20))return 1;
    size_t cursor=u32(b+60);if(cursor>n||((uintptr_t)(b+u32(b+52))&3))return 1;
    CohWalkableScene s={0};s.bytes=b;s.byte_count=n;s.part_count=u32(b+16);s.texture_count=u32(b+20);s.triangle_count=u32(b+24);
    for(unsigned k=0;k<3;k++){
        s.bounds_min[k]=f32(b+68+k*4);s.bounds_max[k]=f32(b+80+k*4);s.spawn[k]=f32(b+92+k*4);
        if(!isfinite(s.bounds_min[k])||!isfinite(s.bounds_max[k])||!isfinite(s.spawn[k])||s.bounds_min[k]>s.bounds_max[k]||s.bounds_max[k]-s.bounds_min[k]>4096||s.spawn[k]<s.bounds_min[k]||s.spawn[k]>s.bounds_max[k])return 1;
    }
    s.spawn_yaw=f32(b+104);if(!isfinite(s.spawn_yaw)||fabsf(s.spawn_yaw)>6.284f)return 1;
    for(unsigned t=0;t<s.triangle_count;t++){
        const uint8_t*r=b+u32(b+52)+40*t;uint32_t flags=u32(r+36);
        /* Source CollFlags only; runtime query decides which flags collide. */
        if(flags&~((1u<<5)|(1u<<6)|(1u<<9)|(1u<<10)|(1u<<11)|(1u<<19)|(1u<<20)|(1u<<21)|(1u<<22)|(1u<<25)))return 1;
        for(unsigned v=0;v<3;v++)for(unsigned k=0;k<3;k++){float x=f32(r+(v*3+k)*4);if(!isfinite(x)||x<s.bounds_min[k]-.001f||x>s.bounds_max[k]+.001f)return 1;}
    }
    s.triangles=(const CohWalkTriangle*)(b+u32(b+52));
    for(unsigned i=0;i<s.part_count;i++){
        const uint8_t*r=b+128+i*96;CohWalkablePart*w=&s.parts[i];CohWorldPart*p=&w->material;uint32_t bytes=u32(r+4);
        if(u32(r)!=cursor||!bytes||bytes>n-cursor||u32(r+8)||u32(r+12)>=s.texture_count||u32(r+16)>=s.texture_count||(u32(r+20)&~3u)||u32(r+68)>1||!zero(r+88,8))return 1;
        if(coh_mesh_parse(b+cursor,bytes,&p->mesh)||p->mesh.bone_count!=1)return 1;
        p->node=0;p->base_texture=u32(r+12);p->dual_texture=u32(r+16);p->flags=u32(r+20);p->mode=u32(r+68);
        for(unsigned k=0;k<4;k++){p->const0[k]=f32(r+24+k*4);p->const1[k]=f32(r+40+k*4);if(!isfinite(p->const0[k])||!isfinite(p->const1[k])||p->const0[k]<0||p->const0[k]>1||p->const1[k]<0||p->const1[k]>1)return 1;}
        p->diffuse_scale=f32(r+56);p->ambient_scale=f32(r+60);p->alpha_ref=f32(r+64);
        if(!isfinite(p->diffuse_scale)||!isfinite(p->ambient_scale)||p->diffuse_scale<0||p->diffuse_scale>2||p->ambient_scale<0||p->ambient_scale>2||!isfinite(p->alpha_ref)||p->alpha_ref<0||p->alpha_ref>1)return 1;
        for(unsigned k=0;k<2;k++){w->uv_scale0[k]=f32(r+72+k*4);w->uv_scale1[k]=f32(r+80+k*4);if(!isfinite(w->uv_scale0[k])||!isfinite(w->uv_scale1[k])||w->uv_scale0[k]<=0||w->uv_scale0[k]>64||w->uv_scale1[k]<=0||w->uv_scale1[k]>64)return 1;}
        if(p->mesh.vertex_count>65536-s.vertices||p->mesh.index_count>196608-s.indices)return 1;
        s.vertices+=p->mesh.vertex_count;s.indices+=p->mesh.index_count;
        for(uint32_t v=0;v<p->mesh.vertex_count;v++){CohMeshVertex x;if(coh_mesh_vertex(&p->mesh,v,&x)||x.weights[0]!=1||x.weights[1]!=0||x.bones[0]||x.bones[1])return 1;for(unsigned k=0;k<3;k++)if(x.position[k]<s.bounds_min[k]-.001f||x.position[k]>s.bounds_max[k]+.001f)return 1;}
        cursor+=bytes;
    }
    for(unsigned i=0;i<s.texture_count;i++){
        const uint8_t*r=b+u32(b+44)+i*32;CohWorldTexture*t=&s.textures[i];t->bytes=u32(r+4);t->width=u32(r+8);t->height=u32(r+12);
        if(!t->width||!t->height||t->width>4096||t->height>4096||u32(r)!=cursor||t->bytes!=(size_t)t->width*t->height*4||t->bytes>n-cursor||!zero(r+16,16))return 1;
        t->rgba=b+cursor;cursor+=t->bytes;
    }
    if(cursor!=n||s.vertices!=u32(b+28)||s.indices!=u32(b+32))return 1;
    *out=s;return 0;
}
