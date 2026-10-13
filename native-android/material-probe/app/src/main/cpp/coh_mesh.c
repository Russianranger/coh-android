#include "coh_mesh.h"
#include <float.h>
#include <math.h>
#include <string.h>
_Static_assert(sizeof(float)==4, "Fixture requires IEEE binary32-sized float");
_Static_assert(sizeof(CohMeshVertex)==COH_MESH_VERTEX_BYTES, "Canonical vertex upload layout mismatch");
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static float lef32(const uint8_t *p) { uint32_t u=le32(p); float f; memcpy(&f,&u,4); return f; }
static int span(size_t n,size_t off,size_t count,size_t stride) {
    return off<=n && (!stride || count<=(n-off)/stride);
}
static int valid_vertex(const CohMeshVertex *v,uint32_t bone_count) {
    if(!v || !bone_count || bone_count>COH_MESH_MAX_BONES) return 0;
    for(unsigned i=0;i<3;i++) if(!isfinite(v->position[i]) || !isfinite(v->normal[i])) return 0;
    for(unsigned i=0;i<2;i++) {
        if(!isfinite(v->uv[i]) || !isfinite(v->weights[i]) || v->weights[i]<0 ||
           v->weights[i]>1 || v->bones[i]>=bone_count) return 0;
    }
    float length2=v->normal[0]*v->normal[0]+v->normal[1]*v->normal[1]+v->normal[2]*v->normal[2];
    return isfinite(length2) && length2>FLT_MIN && fabsf(v->weights[0]+v->weights[1]-1.f)<=2e-6f;
}
int coh_mesh_vertex(const CohMeshView *m,uint32_t index,CohMeshVertex *out) {
    if(!m || !out || !m->bytes || index>=m->vertex_count ||
       !span(m->byte_count,m->vertices_offset,m->vertex_count,COH_MESH_VERTEX_BYTES)) return 1;
    const uint8_t *p=m->bytes+m->vertices_offset+(size_t)index*COH_MESH_VERTEX_BYTES;
    CohMeshVertex v;
    for(unsigned i=0;i<3;i++) { v.position[i]=lef32(p+i*4); v.normal[i]=lef32(p+12+i*4); }
    for(unsigned i=0;i<2;i++) { v.uv[i]=lef32(p+24+i*4); v.weights[i]=lef32(p+32+i*4); v.bones[i]=le32(p+40+i*4); }
    if(!valid_vertex(&v,m->bone_count)) return 1;
    *out=v; return 0;
}
int coh_mesh_index(const CohMeshView *m,uint32_t index,uint32_t *out) {
    if(!m || !out || !m->bytes || index>=m->index_count ||
       !span(m->byte_count,m->indices_offset,m->index_count,4)) return 1;
    uint32_t v=le32(m->bytes+m->indices_offset+(size_t)index*4);
    if(v>=m->vertex_count) return 1;
    *out=v; return 0;
}
int coh_mesh_global_bone(const CohMeshView *m,uint32_t index,uint32_t *out) {
    if(!m || !out || !m->bytes || index>=m->bone_count ||
       !span(m->byte_count,m->bone_ids_offset,m->bone_count,4)) return 1;
    uint32_t id=le32(m->bytes+m->bone_ids_offset+(size_t)index*4);
    if(id>=COH_MESH_GLOBAL_BONE_COUNT) return 1;
    *out=id; return 0;
}
int coh_mesh_parse(const uint8_t *p,size_t n,CohMeshView *out) {
    if(!p || !out || n<COH_MESH_HEADER_BYTES || n>8u*1024u*1024u || memcmp(p,"COHMESH1",8) ||
       le32(p+8)!=1 || le32(p+12)!=COH_MESH_HEADER_BYTES || le32(p+28)!=COH_MESH_VERTEX_BYTES ||
       le32(p+48) || le32(p+52) || le32(p+56) || le32(p+60)) return 1;
    CohMeshView m={p,n,le32(p+16),le32(p+20),le32(p+24),le32(p+32),le32(p+36),le32(p+40)};
    if(!m.vertex_count || m.vertex_count>COH_MESH_MAX_VERTICES || !m.index_count ||
       m.index_count>COH_MESH_MAX_INDICES || m.index_count%3 || !m.bone_count || m.bone_count>COH_MESH_MAX_BONES ||
       m.vertices_offset!=COH_MESH_HEADER_BYTES ||
       !span(n,m.vertices_offset,m.vertex_count,COH_MESH_VERTEX_BYTES)) return 1;
    size_t indices=(size_t)m.vertices_offset+(size_t)m.vertex_count*COH_MESH_VERTEX_BYTES;
    if(m.indices_offset!=indices || !span(n,indices,m.index_count,4)) return 1;
    size_t bones=indices+(size_t)m.index_count*4;
    if(m.bone_ids_offset!=bones || !span(n,bones,m.bone_count,4) ||
       bones+(size_t)m.bone_count*4!=n || le32(p+44)!=n) return 1;
    for(uint32_t i=0;i<m.bone_count;i++) {
        uint32_t id; if(coh_mesh_global_bone(&m,i,&id)) return 1;
        for(uint32_t j=0;j<i;j++) if(id==le32(p+bones+(size_t)j*4)) return 1;
    }
    for(uint32_t i=0;i<m.vertex_count;i++) { CohMeshVertex v; if(coh_mesh_vertex(&m,i,&v)) return 1; }
    for(uint32_t i=0;i<m.index_count;i++) { uint32_t value; if(coh_mesh_index(&m,i,&value)) return 1; }
    *out=m; return 0;
}
int coh_mesh_skin_vertex(const CohMeshVertex *v,const float *palette,uint32_t count,CohSkinnedVertex *out) {
    if(!out || !palette || !valid_vertex(v,count)) return 1;
    for(size_t i=0;i<(size_t)count*12;i++) if(!isfinite(palette[i])) return 1;
    CohSkinnedVertex result;
    for(unsigned r=0;r<3;r++) {
        const float *a=palette+(size_t)v->bones[0]*12+r*4;
        const float *b=palette+(size_t)v->bones[1]*12+r*4;
        float p0=a[0]*v->position[0]+a[1]*v->position[1]+a[2]*v->position[2]+a[3];
        float p1=b[0]*v->position[0]+b[1]*v->position[1]+b[2]*v->position[2]+b[3];
        float n0=a[0]*v->normal[0]+a[1]*v->normal[1]+a[2]*v->normal[2];
        float n1=b[0]*v->normal[0]+b[1]*v->normal[1]+b[2]*v->normal[2];
        result.position[r]=p0+(p1-p0)*v->weights[1];
        result.normal[r]=n0+(n1-n0)*v->weights[1];
        if(!isfinite(result.position[r]) || !isfinite(result.normal[r])) return 1;
    }
    float length2=result.normal[0]*result.normal[0]+result.normal[1]*result.normal[1]+result.normal[2]*result.normal[2];
    if(!isfinite(length2) || length2<=FLT_MIN) return 1;
    float inverse=1.f/sqrtf(length2);
    for(unsigned r=0;r<3;r++) { result.normal[r]*=inverse; if(!isfinite(result.normal[r])) return 1; }
    *out=result; return 0;
}
