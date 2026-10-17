#include "coh_wr_rigid.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
typedef struct {CohRenderGeometry geometry;CohWrRigidMaterial material;} Part;
struct CohWrRigidResource {
    CohAssetLoader *loader;const CohAssetBlob *blob;
    CohWrRigidMaterialRelease release;void *context;
    CohWrRigidReport report;uint32_t acquired;Part *parts;
    char geo_path[COH_ASSET_PATH_MAX+1],model_name[COH_ASSET_PATH_MAX+1];
};
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int bounded_name(const char*p){if(!p)return 0;size_t n=0;while(n<=COH_ASSET_PATH_MAX&&p[n])n++;return n>0&&n<=COH_ASSET_PATH_MAX;}
static int nonzero(const uint8_t *p){unsigned n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static int add(size_t *a,size_t n,size_t s){if(n&&s>(SIZE_MAX-*a)/n)return 0;*a+=n*s;return 1;}
static int room(CohAssetLoader*l,const CohWrRigidLimits*b,size_t owned,size_t temp,size_t *peak){
    size_t n=b->external_bytes,loader=coh_asset_stats(l).peak_allocated_bytes;
    if(loader>b->loader_reservation)return 0;
    if(!add(&n,b->loader_reservation,1)||!add(&n,owned,1)||!add(&n,temp,1)||n>b->aggregate_limit)return 0;
    if(n>*peak)*peak=n;
    return 1;
}
static int material_valid(const CohWrRigidMaterial*r,uint32_t generation){
    const CohRenderMaterial*m=&r->material;
    if(!r->pin||!r->geometry_id||r->generation!=generation||r->unsupported_semantics||!nonzero(r->source_sha256)||
       m->family<COH_MAT_MULTIPLY||m->family>COH_MAT_ADDGLOW||
       m->lighting<COH_LIGHT_VERTEX||m->lighting>COH_LIGHT_FIXED||m->blend<COH_BLEND_OPAQUE||m->blend>COH_BLEND_ADDITIVE||
       m->depth_test>1||m->depth_write>1||m->cull_back>1||m->front_cw>1||
       m->alpha_ref<0||m->alpha_ref>1||m->shininess<0||m->shininess>128)return 0;
    const float *v[]={m->const0,m->const1,m->fog_params,m->fog_color,m->glow_params,m->light,m->diffuse,m->ambient,m->specular,&m->shininess,&m->alpha_ref};
    const unsigned n[]={4,4,4,4,4,3,4,4,3,1,1};
    for(unsigned i=0;i<sizeof(n)/sizeof(n[0]);i++)for(unsigned j=0;j<n[i];j++)if(!isfinite(v[i][j]))return 0;
    unsigned textures=m->family==COH_MAT_ADDGLOW?3:2;
    for(unsigned i=0;i<3;i++){
        const CohRenderTexture*t=m->textures+i;
        if(t->handle||t->wrap_s<0||t->wrap_s>COH_WRAP_MIRROR||t->wrap_t<0||t->wrap_t>COH_WRAP_MIRROR||
           t->min_filter<0||t->min_filter>COH_FILTER_LINEAR||t->mag_filter<0||t->mag_filter>COH_FILTER_LINEAR||
           (i<textures?!r->texture_id[i]:r->texture_id[i]!=0))return 0;
    }
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)if(!isfinite(r->uv_scale[i][j])||fabsf(r->uv_scale[i][j])>1000000.f)return 0;
    return 1;
}
CohStatus coh_wr_rigid_identity(const CohWrRigidResource*r,CohAssetId*geo,const char**model){
    if(!r||!geo||!model)return COH_INVALID;
    *geo=(CohAssetId){r->geo_path,r->report.asset_generation};*model=r->model_name;return COH_OK;
}
void coh_wr_rigid_release(CohWrRigidResource **p){
    if(!p||!*p)return;
    CohWrRigidResource*r=*p;
    for(uint32_t i=0;i<r->acquired;i++)if(r->parts[i].material.pin)r->release(r->context,r->parts[i].material.pin);
    coh_asset_release(r->loader,r->blob);free(r);*p=NULL;
}
CohStatus coh_wr_rigid_report(const CohWrRigidResource*r,CohWrRigidReport*out){if(!r||!out)return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_wr_rigid_part(const CohWrRigidResource*r,uint32_t i,CohRenderGeometry*g,CohWrRigidMaterial*m){
    if(!r||!g||!m||i>=r->report.parts)return COH_INVALID;
    *g=r->parts[i].geometry;*m=r->parts[i].material;return COH_OK;
}
CohStatus coh_wr_rigid_acquire(CohAssetLoader*l,const CohWrRigidRequest*q,const CohWrRigidLimits*b,CohCancel cancel,CohWrRigidResource **out){
    const CohAssetBlob*blob=NULL;CohWrRigidResource*r=NULL;uint8_t *temp=NULL,*streams=NULL;CohStatus s;
    size_t workspace=0,max_stream=0,owned=sizeof(*r),temporary=0,peak=0;
    if(!l||!q||!b||!out||!q->geo.path||!q->geo.generation||!bounded_name(q->model)||
       !q->material_generation||!q->digest||!q->acquire||!q->release||!nonzero(q->geo_sha256))return COH_INVALID;
    if(*out)return COH_STATE;
    if(!b->loader_reservation||!b->aggregate_limit||b->aggregate_limit>COH_WR_MAX_MEMORY||b->external_bytes>b->aggregate_limit||
       !b->max_models||b->max_models>65536||!b->max_vertices||b->max_vertices>COH_WR_MAX_VERTICES||
       !b->max_triangles||b->max_triangles>COH_WR_MAX_INDICES/3||!b->max_parts||b->max_parts>COH_WR_MAX_DRAWS)return COH_LIMIT;
    if(cancelled(cancel))return COH_CANCELLED;
    if(!room(l,b,0,0,&peak))return COH_LIMIT;
    s=coh_asset_acquire(l,q->geo,cancel,&blob);if(s!=COH_OK)return s;
    CohBytes bytes=coh_asset_bytes(blob);uint8_t digest[32];CohAssetGeo geo;CohAssetGeoModel model;
    if(!room(l,b,0,0,&peak)){s=COH_LIMIT;goto fail;}
    s=q->digest(q->digest_context,bytes,digest);if(s!=COH_OK)goto fail;
    if(memcmp(digest,q->geo_sha256,32)){s=COH_INVALID;goto fail;}
    s=coh_asset_geo_workspace(bytes,&workspace);if(s!=COH_OK)goto fail;
    if(workspace>b->max_workspace_bytes||!room(l,b,0,workspace,&peak)){s=COH_LIMIT;goto fail;}
    temp=malloc(workspace);if(!temp){s=COH_LIMIT;goto fail;}
    s=coh_asset_geo_open(bytes,temp,workspace,b->max_models,&geo);if(s!=COH_OK)goto fail;
    if(geo.version!=8){s=COH_UNSUPPORTED;goto fail;}
    uint32_t matches=0,selected=0;
    for(uint32_t i=0;i<geo.model_count;i++){
        CohAssetGeoModel m;if(cancelled(cancel)){s=COH_CANCELLED;goto fail;}
        s=coh_asset_geo_model(&geo,i,&m);if(s!=COH_OK)goto fail;
        if(!strcmp(m.name,q->model)){model=m;selected=i;matches++;}
    }
    if(matches!=1){s=matches?COH_INVALID:COH_NOT_FOUND;goto fail;}
    /* Public parser validates every variable record; inspect the selected
     * protected low-level metadata to refuse v8 reflection/pivot tails too. */
    size_t record=geo.records_offset;
    for(uint32_t i=0;i<selected;i++)record+=u32(geo.header.data+record);
    CohGeoModel metadata;
    if(coh_geo_model(geo.header.data+record,geo.header.size-record,geo.version,&metadata)){s=COH_INVALID;goto fail;}
    if(metadata.reflection_count||metadata.alternate_pivot_offset){s=COH_UNSUPPORTED;goto fail;}
    if(model.vertex_count>b->max_vertices||model.triangle_count>b->max_triangles||model.material_count>b->max_parts){s=COH_LIMIT;goto fail;}
    if(model.bone_info_offset||model.scale[0]!=1.f||model.scale[1]!=1.f||model.scale[2]!=1.f||
       model.packs[4].unpacked_bytes||model.packs[5].unpacked_bytes||model.packs[6].unpacked_bytes||model.packs[9].unpacked_bytes){s=COH_UNSUPPORTED;goto fail;}
    for(unsigned i=0;i<4;i++){
        if(!model.packs[i].unpacked_bytes){s=COH_UNSUPPORTED;goto fail;}
        if(model.packs[i].unpacked_bytes>max_stream)max_stream=model.packs[i].unpacked_bytes;
    }
    if(max_stream>b->max_stream_bytes){s=COH_LIMIT;goto fail;}
    if(!add(&owned,model.material_count,sizeof(Part))||
       !add(&owned,(size_t)model.material_count*model.vertex_count,sizeof(CohRenderVertex))||
       !add(&owned,(size_t)model.triangle_count*3,sizeof(uint32_t))||
       !add(&temporary,workspace,1)||!add(&temporary,65536,1)||!add(&temporary,max_stream,1)||
       !add(&temporary,(size_t)model.vertex_count*8,sizeof(float))||
       !add(&temporary,(size_t)model.triangle_count*3,sizeof(uint32_t))||
       !room(l,b,owned,temporary,&peak)){s=COH_LIMIT;goto fail;}
    size_t stage_bytes=(size_t)model.vertex_count*8*sizeof(float)+(size_t)model.triangle_count*3*sizeof(uint32_t);
    /* Separate arenas avoid an unaccounted realloc old+new transient. The
     * inflated header/model names remain pinned until all callbacks finish. */
    streams=malloc(max_stream+65536);if(!streams){s=COH_LIMIT;goto fail;}
    r=calloc(1,owned);if(!r){s=COH_LIMIT;goto fail;}
    r->loader=l;r->blob=blob;r->release=q->release;r->context=q->material_context;r->parts=(Part*)(r+1);
    uint8_t*encoded=streams,*scratch=encoded+max_stream;
    /* workspace and packed stream lengths need not align: staging uses memcpy
     * only until protected delta APIs write aligned, separately allocated spans. */
    void*staging=malloc(stage_bytes);
    if(!staging){s=COH_LIMIT;goto fail;}
    /* The separate aligned staging allocation is included in temporary. */
    float*positions=staging,*normals=positions+model.vertex_count*3,*uv=normals+model.vertex_count*3;
    uint32_t*indices=(uint32_t*)(uv+model.vertex_count*2);
    for(unsigned pack=0;pack<4;pack++){
        size_t got=0;if(cancelled(cancel)){s=COH_CANCELLED;goto staged_fail;}
        s=coh_asset_geo_stream(&geo,&model,pack,encoded,max_stream,scratch,65536,&got);if(s!=COH_OK)goto staged_fail;
        CohBytes stream={encoded,got};
        s=pack==0?coh_asset_delta_indices(stream,model.triangle_count,indices,(size_t)model.triangle_count*3):
          coh_asset_delta_floats(stream,model.vertex_count,pack==3?2:3,pack==1?positions:pack==2?normals:uv,(size_t)model.vertex_count*(pack==3?2:3));
        if(s!=COH_OK)goto staged_fail;
    }
    for(size_t i=0;i<(size_t)model.triangle_count*3;i++)if(indices[i]>=model.vertex_count){s=COH_INVALID;goto staged_fail;}
    CohRenderVertex*vertices=(CohRenderVertex*)(r->parts+model.material_count);
    uint32_t*stored_indices=(uint32_t*)(vertices+(size_t)model.material_count*model.vertex_count);
    for(uint32_t part=0;part<model.material_count;part++){
        CohAssetGeoMaterial original;Part*p=r->parts+part;
        if(cancelled(cancel)){s=COH_CANCELLED;goto staged_fail;}
        s=coh_asset_geo_material(&geo,&model,part,&original);if(s!=COH_OK)goto staged_fail;
        s=q->acquire(q->material_context,coh_asset_identity(blob),model.name,part,&original,&p->material);
        if(s!=COH_OK)goto staged_fail;
        r->acquired++;
        if(!original.triangle_count||!material_valid(&p->material,q->material_generation)){s=COH_UNSUPPORTED;goto staged_fail;}
        for(uint32_t j=0;j<part;j++)if(r->parts[j].material.geometry_id==p->material.geometry_id){s=COH_INVALID;goto staged_fail;}
        if(!room(l,b,owned,temporary,&peak)){s=COH_LIMIT;goto staged_fail;}
        for(uint32_t i=0;i<model.vertex_count;i++){
            CohRenderVertex*v=vertices+i;memcpy(v->position,positions+i*3,12);memcpy(v->normal,normals+i*3,12);
            float flipped=1.f-uv[i*2+1];
            for(unsigned j=0;j<2;j++){
                float*u=j?v->uv1:v->uv0;u[0]=uv[i*2]*p->material.uv_scale[j][0];u[1]=flipped*p->material.uv_scale[j][1];
                if(!isfinite(u[0])||!isfinite(u[1])){s=COH_INVALID;goto staged_fail;}
            }
            for(unsigned j=0;j<4;j++)v->color[j]=1;
        }
        size_t n=(size_t)original.triangle_count*3;memcpy(stored_indices,indices+(size_t)original.first_triangle*3,n*sizeof(uint32_t));
        p->geometry=(CohRenderGeometry){vertices,model.vertex_count,stored_indices,n,p->material.geometry_id,q->geo.generation};
        vertices+=model.vertex_count;stored_indices+=n;
    }
    if(cancelled(cancel)){s=COH_CANCELLED;goto staged_fail;}
    CohAssetId actual=coh_asset_identity(blob);
    memcpy(r->geo_path,actual.path,strlen(actual.path)+1);memcpy(r->model_name,q->model,strlen(q->model)+1);
    r->report=(CohWrRigidReport){geo.version,q->geo.generation,q->material_generation,model.material_count,model.vertex_count,model.triangle_count,owned,temporary,coh_asset_stats(l).peak_allocated_bytes,b->loader_reservation,b->external_bytes,peak,{0}};
    memcpy(r->report.geo_sha256,digest,32);free(staging);free(streams);free(temp);*out=r;return COH_OK;
 staged_fail:free(staging);
 fail:free(streams);free(temp);if(r)coh_wr_rigid_release(&r);else if(blob)coh_asset_release(l,blob);return s;
}
