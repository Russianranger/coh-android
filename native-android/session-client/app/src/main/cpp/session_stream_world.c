#include "session_stream_world.h"
#include "session_world_imports.h"
#include "session_stream_qualify.h"
#include "coh_asset_render.h"
#include "coh_world_live.h"
#include "coh_asset_zip.h"
#include "coh_renderer_gles.h"
#include "coh_debug_entity.h"
#include <GLES3/gl3.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define STREAM_DRAWS 64u
#define STREAM_BUDGET (512u*1024u)
#define SCENE_CAP (96ull*1024u*1024u)
struct CohSessionWorld {
    CohWorldBundle bundle;
    CohWorldMap *map;
    CohWorldLive *live;
    CohSessionWorldImports *imports;
    CohAssetZip *archives[2];
    uint64_t parent_retained_bytes;
    CohAssetLoader *loader;
    CohAssetRenderBridge *bridge;
    CohWorldSelection selection;
    const CohBridgeMesh *meshes[COH_WORLD_MAX_INSTANCES];
    CohRenderer *renderer;
    CohGlesRenderer *gles;
    CohRenderDraw draws[STREAM_DRAWS];
    uint32_t draw_count,debug_white,live_selection;
    float last_center[3],last_radius;
    CohSessionWorldStats stats;
};
uint64_t coh_session_world_live_reservation_bytes(void){
    /* Actual target-ABI control allocations, not duplicated source catalogs.
     * ZIP owners include both 65,568-byte inflate arenas and 8KiB input/output
     * buffers; the source placement index stays on its borrowed immutable FD. */
    uint64_t controls=sizeof(CohSessionWorld)+coh_world_map_allocation_bytes()+
        coh_world_live_allocation_bytes()+coh_asset_zip_allocation_bytes(2)+
        coh_asset_zip_allocation_bytes(1)+coh_renderer_allocation_bytes(STREAM_DRAWS,2)+
        coh_renderer_gles_allocation_bytes();
    /* Each ceiling covers that module's simultaneous old+candidate allocations:
     * loader4MiB includes its one512KiB old+next raw cache and decode scratch;
     * bridge4MiB includes old+next geometry, retained RGBA and bridge workspace.
     * Every old/new uploaded texture still owns its RGBA inside the same bridge,
     * so their overlapping GPU payloads are bounded by that single4MiB ceiling.
     * Borrowed draw spans duplicate no bytes; queued consumers block retirement. */
    uint64_t overlapping_owners=3ull*(4u<<20);
    /* Persistent VBO/IBO+white and the maximum existing source qualification
     * VBO+13-float TF stream+256x256RGBA8/depth24(aligned32) FBO. Readback CPU
     * pixels are separately charged; all dimensions match the existing code. */
    uint64_t gpu=(uint64_t)8192*sizeof(CohRenderVertex)+(uint64_t)24576*sizeof(uint32_t)+4u+
        (uint64_t)8192*(sizeof(CohRenderVertex)+13u*sizeof(float))+256u*256u*8u;
    uint64_t readback=256u*256u*4u;
    /* Both query/next selections, dependency IDs, parser/callback frames and
     * rollback arrays use this charged64KiB call reserve. The parent supplies
     * its retained bundle bytes, FD contexts, old whole-world owner and capture
     * reservation. Driver allocations and actual RSS/PSS remain separate. */
    return controls+overlapping_owners+gpu+readback+65536u;
}
static int problem(CohSessionWorld *w,char *error,size_t cap,const char *stage,CohStatus status) {
    if(w)w->stats.errors++;
    if(error&&cap)snprintf(error,cap,"%s (status %d)",stage,(int)status);
    return 0;
}
static void restore_accepted_state(void) {
    for(unsigned unit=0;unit<3;unit++)glBindSampler(unit,0);
    glActiveTexture(GL_TEXTURE0);glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);
    glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);
    glFrontFace(GL_CW);glCullFace(GL_BACK);
}
static CohStatus upload(void *context,CohAssetId id,uint32_t width,uint32_t height,
                        CohBytes rgba,uint32_t generation,uint32_t *handle) {
    (void)context;(void)id;(void)generation;
    if(!handle||!rgba.data||!width||!height||width>2048||height>2048||
       rgba.size!=(size_t)width*height*4)return COH_INVALID;
    GLuint texture=0;glGenTextures(1,&texture);if(!texture)return COH_LIMIT;
    glBindTexture(GL_TEXTURE_2D,texture);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,(GLsizei)width,(GLsizei)height);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,(GLsizei)width,(GLsizei)height,GL_RGBA,GL_UNSIGNED_BYTE,rgba.data);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
    if(glGetError()!=GL_NO_ERROR){glDeleteTextures(1,&texture);return COH_STATE;}
    *handle=texture;return COH_OK;
}
static void texture_release(void *context,uint32_t handle,int alive) {
    (void)context;if(alive&&handle){GLuint name=handle;glDeleteTextures(1,&name);}
}
static CohStatus material(void *context,const char *name,CohBridgeMaterial *out) {
    CohSessionWorld *w=context;CohWorldMaterial source;
    CohStatus status=coh_world_material(&w->bundle,name,&source);
    if(status!=COH_OK)return status;
    if(source.family>COH_MAT_DUAL)return COH_UNSUPPORTED;
    CohBridgeMaterial result;memset(&result,0,sizeof result);
    result.material=coh_renderer_default_material((CohMaterialFamily)source.family);
    /* Same explicit no-fog diagnostic profile as the accepted session. Atlas
     * scene light grids/fog environments are outside this admitted subset. */
    result.material.fog_params[2]=1000000.f;
    result.material.lighting=COH_LIGHT_DIFFUSE;
    result.material.light[0]=.188144f;result.material.light[1]=.282216f;result.material.light[2]=.940721f;
    memcpy(result.material.diffuse,source.diffuse,sizeof source.diffuse);
    memcpy(result.material.ambient,source.ambient,sizeof source.ambient);
    memcpy(result.material.const0,source.const0,sizeof source.const0);
    memcpy(result.material.const1,source.const1,sizeof source.const1);
    result.material.cull_back=(uint8_t)source.cull_back;result.material.alpha_ref=source.alpha_ref;
    for(unsigned i=0;i<2;i++) {
        if(source.wrap[i]>COH_WRAP_MIRROR)return COH_UNSUPPORTED;
        result.textures[i]=source.textures[i];
        result.material.textures[i].wrap_s=result.material.textures[i].wrap_t=(CohWrap)source.wrap[i];
        result.material.textures[i].min_filter=result.material.textures[i].mag_filter=COH_FILTER_LINEAR;
    }
    memcpy(result.uv_scale,source.uv_scale,sizeof result.uv_scale);*out=result;return COH_OK;
}
static void publish(CohSessionWorld *w,CohSessionWorldStats *out) {
    CohAssetStats a=coh_asset_stats(w->loader);CohBridgeStats b=coh_bridge_stats(w->bridge);
    w->stats.resident_bytes=a.resident_bytes;w->stats.peak_resident_bytes=a.peak_resident_bytes;
    w->stats.budget_bytes=STREAM_BUDGET;w->stats.cache_hits=a.cache_hits;w->stats.cache_misses=a.cache_misses;
    w->stats.evictions=a.evictions;w->stats.geo_loads=b.mesh_loads;w->stats.texture_loads=b.texture_loads;
    w->stats.owned_cpu_bytes=b.allocated_bytes;w->stats.selected_instances=w->selection.count;
    if(out)*out=w->stats;
}
static int create_world(const void *data,size_t bytes,const CohSessionWorldSources *sources,CohSessionWorld **out,char *error,size_t cap) {
    if(!data||!out)return problem(NULL,error,cap,"Missing indexed map bytes",COH_INVALID);
    if(*out)return problem(NULL,error,cap,"Existing world output",COH_STATE);
    if(sources&&sources->parent_retained_bytes>SCENE_CAP-coh_session_world_live_reservation_bytes())return problem(NULL,error,cap,"Parent scene/capture aggregate memory",COH_LIMIT);
    CohSessionWorld *w=calloc(1,sizeof *w);if(!w)return problem(NULL,error,cap,"Indexed world allocation",COH_LIMIT);
    CohStatus status=coh_world_bundle_open((CohBytes){data,bytes},&w->bundle);
    if(status!=COH_OK)goto failed;
    CohAssetLimits limits={4u<<20,STREAM_BUDGET,1u<<20,1u<<20,128,64,32};
    status=coh_asset_create(&limits,&w->loader);if(status!=COH_OK)goto failed;
    if(!sources){status=coh_world_bundle_mount(&w->bundle,w->loader,(CohCancel){0});if(status!=COH_OK)goto failed;}
    else {
        if(w->bundle.count!=11){status=COH_INVALID;goto failed;}
        /* The callbacks must point into the retained world bundle, not this
         * temporary descriptor. Limit count on the actual owner while mounting. */
        w->bundle.count=8;status=coh_world_bundle_mount(&w->bundle,w->loader,(CohCancel){0});w->bundle.count=11;
        if(status!=COH_OK)goto failed;
        CohAssetZipMember atlas[2],client[1];
        for(unsigned i=0;i<2;i++)atlas[i]=(CohAssetZipMember){w->bundle.entries[8+i].id.path,(uint32_t)w->bundle.entries[8+i].bytes.size};
        client[0]=(CohAssetZipMember){w->bundle.entries[10].id.path,(uint32_t)w->bundle.entries[10].bytes.size};
        status=coh_asset_zip_open(sources->atlas_zip,atlas,2,(CohCancel){0},&w->archives[0]);if(status!=COH_OK)goto failed;
        status=coh_asset_zip_open(sources->client_zip,client,1,(CohCancel){0},&w->archives[1]);if(status!=COH_OK)goto failed;
        for(unsigned i=0;i<2;i++){status=coh_asset_zip_mount(w->archives[i],w->loader);if(status!=COH_OK)goto failed;}
        w->parent_retained_bytes=sources->parent_retained_bytes;
    }
    status=coh_world_map_create(w->bundle.index,&w->map);if(status!=COH_OK)goto failed;
    CohBridgeLimits bridge=coh_bridge_default_limits();bridge.total_bytes=4u<<20;
    bridge.meshes=16;bridge.textures=16;bridge.max_vertices=8192;bridge.max_triangles=8192;
    CohBridgeTextureBackend backend={upload,texture_release,w};
    status=coh_bridge_create(w->loader,&bridge,&backend,&w->bridge);if(status!=COH_OK)goto failed;
    CohWorldStats catalog=coh_world_map_stats(w->map);
    if(sources){status=coh_world_live_open(sources->placements,catalog.endpoints,(CohCancel){0},&w->live);if(status!=COH_OK)goto failed;}
    for(uint32_t i=0;i<catalog.nodes;i++) {
        CohWorldNode node;status=coh_world_node(w->map,i,&node);if(status!=COH_OK)goto failed;
        if(node.endpoint<catalog.endpoints)w->stats.catalog_instances++;
    }
    /* Explicit admission/prewarm, before any frame loop. All permitted model
     * and material endpoints are validated once; per-frame selection is cached. */
    for(uint32_t i=0;!sources&&i<catalog.endpoints;i++) {
        CohWorldEndpoint endpoint;const CohBridgeMesh *mesh=NULL;uint32_t part_mask=0;
        status=coh_world_endpoint(w->map,i,&endpoint);if(status!=COH_OK)goto failed;
        status=coh_world_endpoint_part_mask(w->map,i,&part_mask);if(status!=COH_OK)goto failed;
        status=coh_bridge_acquire_parts(w->bridge,endpoint.geometry,endpoint.model,1,part_mask,material,w,(CohCancel){0},&mesh);
        if(status!=COH_OK)goto failed;
        coh_bridge_release(w->bridge,mesh);
    }
    if(w->live)w->stats.catalog_instances=11u+coh_world_live_stats(w->live).rows;
    publish(w,NULL);*out=w;return 1;
failed:
    problem(w,error,cap,"Source map/geometry/material admission",status);
    coh_session_world_destroy(&w);return 0;
}
int coh_session_world_create(const void *data,size_t bytes,CohSessionWorld **out,char *error,size_t cap){return create_world(data,bytes,NULL,out,error,cap);}
int coh_session_world_create_archives(const void *data,size_t bytes,const CohSessionWorldSources *sources,CohSessionWorld **out,char *error,size_t cap){
    if(!sources)return problem(NULL,error,cap,"Missing imported world sources",COH_INVALID);
    return create_world(data,bytes,sources,out,error,cap);
}
int coh_session_world_create_fds(const void *data,size_t bytes,const CohSessionWorldFd inputs[3],uint64_t parent,CohSessionWorld **out,char *error,size_t cap){
    if(!out||!inputs)return problem(NULL,error,cap,"Missing imported archive descriptors",COH_INVALID);
    uintptr_t a=(uintptr_t)inputs,b=(uintptr_t)out;size_t input_bytes=3u*sizeof *inputs;
    if(a>UINTPTR_MAX-input_bytes||b>UINTPTR_MAX-sizeof *out||(a<b+sizeof *out&&b<a+input_bytes))return problem(NULL,error,cap,"Aliased imported archive descriptors",COH_INVALID);
    if(*out)return problem(NULL,error,cap,"Existing world output",COH_STATE);
    uint64_t charge=coh_session_world_imports_allocation_bytes();
    if(parent>SCENE_CAP-coh_session_world_live_reservation_bytes()-charge)return problem(NULL,error,cap,"Parent scene/capture/import memory",COH_LIMIT);
    CohSessionWorldImports *imports=NULL;CohStatus status=coh_session_world_imports_open(inputs,&imports);
    if(status!=COH_OK)return problem(NULL,error,cap,"Immutable imported archive descriptors",status);
    CohSessionWorldSources sources=coh_session_world_imports_sources(imports,parent+charge);
    if(!create_world(data,bytes,&sources,out,error,cap)){coh_session_world_imports_free(imports);return 0;}
    (*out)->imports=imports;(*out)->parent_retained_bytes=parent;return 1;
}
int coh_session_world_parent_bytes(CohSessionWorld *w,uint64_t bytes,char *error,size_t cap){
    if(!w||!w->live)return problem(w,error,cap,"Runtime world owner",COH_STATE);
    if(bytes>SCENE_CAP-coh_session_world_live_reservation_bytes()-coh_session_world_imports_owned_bytes(w->imports))return problem(w,error,cap,"Parent scene/capture aggregate memory",COH_LIMIT);
    w->parent_retained_bytes=bytes;return 1;
}
static void release_meshes(CohSessionWorld *w) {
    for(uint32_t i=0;i<COH_WORLD_MAX_INSTANCES;i++)if(w->meshes[i]){
        coh_bridge_release(w->bridge,w->meshes[i]);w->meshes[i]=NULL;
    }
}
static int select_live(CohSessionWorld *w,const float center[3],float radius,char *error,size_t cap){
    if(w->parent_retained_bytes>SCENE_CAP-coh_session_world_live_reservation_bytes()-coh_session_world_imports_owned_bytes(w->imports))return problem(w,error,cap,"Parent scene/capture aggregate memory",COH_LIMIT);
    if(w->renderer&&coh_renderer_stats(w->renderer).queued)return problem(w,error,cap,"Previous frame still borrows geometry",COH_STATE);
    float distance=0;
    for(unsigned i=0;i<3;i++){float delta=center[i]-w->last_center[i];if(!isfinite(delta))return problem(w,error,cap,"Invalid runtime source center",COH_INVALID);distance+=delta*delta;}
    if(w->live_selection&&radius==w->last_radius&&distance<16)return 1;
    CohWorldInstance instances[COH_WORLD_MAX_INSTANCES];uint32_t count=0;
    CohStatus status=coh_world_live_query(w->live,center,radius,instances,COH_WORLD_MAX_INSTANCES,&count,(CohCancel){0});
    if(status!=COH_OK)return problem(w,error,cap,"Runtime source placement query",status);
    int same=count==w->selection.count;
    for(uint32_t i=0;same&&i<count;i++)same=instances[i].node==w->selection.instances[i].node&&instances[i].endpoint==w->selection.instances[i].endpoint&&!memcmp(instances[i].world,w->selection.instances[i].world,sizeof instances[i].world);
    if(!same){
        CohWorldSelection next={0};const CohBridgeMesh *meshes[COH_WORLD_MAX_INSTANCES]={0};
        status=coh_world_select_instances(w->map,w->loader,instances,count,STREAM_BUDGET,(CohCancel){0},&next);
        for(uint32_t i=0;status==COH_OK&&i<count;i++){
            CohWorldEndpoint endpoint;uint32_t mask=0;status=coh_world_endpoint(w->map,instances[i].endpoint,&endpoint);
            if(status==COH_OK)status=coh_world_endpoint_part_mask(w->map,instances[i].endpoint,&mask);
            if(status==COH_OK)status=coh_bridge_acquire_parts(w->bridge,endpoint.geometry,endpoint.model,1,mask,material,w,(CohCancel){0},&meshes[i]);
        }
        if(status!=COH_OK){for(uint32_t i=0;i<count;i++)if(meshes[i])coh_bridge_release(w->bridge,meshes[i]);coh_world_release(&next);return problem(w,error,cap,"Runtime source dependencies",status);}
        release_meshes(w);coh_world_release(&w->selection);w->selection=next;memcpy(w->meshes,meshes,sizeof meshes);
        /* Renderer flush has released all borrowed spans. Retire obsolete raw,
         * decoded and uploaded resources only after their final mesh consumer. */
        coh_bridge_trim(w->bridge,1);coh_asset_trim(w->loader);w->stats.selection_updates++;
    }
    memcpy(w->last_center,center,sizeof w->last_center);w->last_radius=radius;w->stats.view_radius=radius;w->live_selection=1;return 1;
}
static int select_world(CohSessionWorld *w,const float center[3],float radius,int allow_empty,char *error,size_t cap) {
    if(!isfinite(radius)||(radius!=24&&radius!=96))return problem(w,error,cap,"Invalid view distance",COH_INVALID);
    if(w->live&&allow_empty)return select_live(w,center,radius,error,cap);
    float d=0;for(unsigned i=0;i<3;i++){float v=center[i]-w->last_center[i];if(!isfinite(v))return problem(w,error,cap,"Invalid query center",COH_INVALID);d+=v*v;}
    if(!w->live_selection&&w->selection.count&&radius==w->last_radius&&d<16)return 1;
    uint32_t nodes[COH_WORLD_MAX_INSTANCES],count=0;
    CohStatus status=coh_world_query(w->map,center,radius,nodes,COH_WORLD_MAX_INSTANCES,&count);
    if(status!=COH_OK||(!count&&!allow_empty))return problem(w,error,cap,"Source map radius selection",status==COH_OK?COH_NOT_FOUND:status);
    if(!count){release_meshes(w);coh_world_release(&w->selection);memcpy(w->last_center,center,sizeof w->last_center);w->last_radius=radius;w->stats.view_radius=radius;w->stats.selection_updates++;w->live_selection=0;return 1;}
    int same=count==w->selection.count;
    for(uint32_t i=0;same&&i<count;i++)same=nodes[i]==w->selection.instances[i].node;
    if(!same||radius!=w->last_radius) {
        status=coh_world_select(w->map,w->loader,nodes,count,STREAM_BUDGET,(CohCancel){0},&w->selection);
        if(status!=COH_OK)return problem(w,error,cap,"Bounded map dependency selection",status);
        release_meshes(w);
        for(uint32_t i=0;i<count;i++) {
            CohWorldEndpoint endpoint;uint32_t part_mask=0;status=coh_world_endpoint(w->map,w->selection.instances[i].endpoint,&endpoint);
            if(status!=COH_OK)return problem(w,error,cap,"Selected endpoint",status);
            status=coh_world_endpoint_part_mask(w->map,w->selection.instances[i].endpoint,&part_mask);
            if(status!=COH_OK)return problem(w,error,cap,"Selected source partition",status);
            status=coh_bridge_acquire_parts(w->bridge,endpoint.geometry,endpoint.model,1,part_mask,material,w,(CohCancel){0},&w->meshes[i]);
            if(status!=COH_OK)return problem(w,error,cap,"Selected cached source mesh",status);
        }
        w->stats.selection_updates++;
    }
    memcpy(w->last_center,center,sizeof w->last_center);w->last_radius=radius;w->stats.view_radius=radius;w->live_selection=0;return 1;
}
static void multiply_source(const float a[12],const float b[12],float out[12]) {
    for(unsigned col=0;col<4;col++)for(unsigned row=0;row<3;row++) {
        out[col*3+row]=(a[row]*b[col*3]+a[3+row]*b[col*3+1])+a[6+row]*b[col*3+2];
        if(col==3)out[col*3+row]+=a[9+row];
    }
}
static void source_gl_matrix(const float source[12],float out[16]) {
    /* Preserve the accepted source 4x3 column layout without importing its
     * unrelated fixed-size CohWorldNode typedef into the streaming frontend. */
    for(unsigned col=0;col<4;col++) {
        for(unsigned row=0;row<3;row++)out[col*4+row]=source[col*3+row];
        out[col*4+3]=col==3?1.f:0.f;
    }
}
static int packets(CohSessionWorld *w,const float view[12],const float projection[16],char *error,size_t cap) {
    w->draw_count=0;
    for(uint32_t i=0;i<w->selection.count;i++) {
        const CohBridgeMesh *mesh=w->meshes[i];
        CohStatus status=coh_bridge_prepare(w->bridge,mesh,(CohCancel){0});
        if(status!=COH_OK)return problem(w,error,cap,"Source texture upload",status);
        float eye[12],gl[16];multiply_source(view,w->selection.instances[i].world,eye);source_gl_matrix(eye,gl);
        for(uint32_t part=0;part<coh_bridge_mesh_parts(mesh);part++) {
            if(w->draw_count==STREAM_DRAWS)return problem(w,error,cap,"Static draw capacity",COH_LIMIT);
            CohRenderDraw *draw=&w->draws[w->draw_count];memset(draw,0,sizeof *draw);
            status=coh_bridge_mesh_part(mesh,part,&draw->geometry,&draw->material);
            if(status!=COH_OK)return problem(w,error,cap,"Static material packet",status);
            /* Source inherited dual colors vary per instance, not cache key. */
            for(unsigned color=0;color<3;color++) {
                draw->material.const0[color]=w->selection.instances[i].tint[color];
                draw->material.const1[color]=w->selection.instances[i].tint[color+3];
            }
            memcpy(draw->model_view,gl,sizeof gl);memcpy(draw->projection,projection,16*sizeof(float));
            w->stats.material_mode_mask|=1u<<(unsigned)draw->material.family;w->draw_count++;
        }
    }
    return 1;
}
int coh_session_world_surface(CohSessionWorld *w,const float view[12],const float projection[16],
                              const float center[3],float radius,CohSessionWorldStats *out,char *error,size_t cap) {
    if(!w||w->renderer)return problem(w,error,cap,"Static Surface ownership",COH_STATE);
    CohRenderBackend backend;CohStatus status=coh_renderer_gles_create(8192,24576,&w->gles,&backend);
    if(status!=COH_OK)return problem(w,error,cap,"Static GLES buffers",status);
    CohRendererConfig config={STREAM_DRAWS,8192,24576,2};status=coh_renderer_create(&config,&backend,&w->renderer);
    if(status!=COH_OK)return problem(w,error,cap,"Static renderer creation",status);
    w->stats.generation++;coh_renderer_surface_lost(w->renderer,w->stats.generation,1);
    if(coh_bridge_stats(w->bridge).surface_generation!=w->stats.generation) {
        status=coh_bridge_surface_lost(w->bridge,w->stats.generation,1);
        if(status!=COH_OK)return problem(w,error,cap,"Static texture generation",status);
    }
    const uint8_t white[4]={255,255,255,255};
    status=upload(w,(CohAssetId){0},1,1,(CohBytes){white,sizeof white},w->stats.generation,&w->debug_white);
    if(status!=COH_OK)return problem(w,error,cap,"Diagnostic entity white resource",status);
    w->stats.gpu_bytes=coh_renderer_gles_buffer_bytes(w->gles)+sizeof white;
    if(!select_world(w,center,radius,0,error,cap)||!packets(w,view,projection,error,cap))return 0;
    CohStreamQualification proof;
    int ok=coh_stream_qualify(w->renderer,w->draws,w->draw_count,&proof,error,cap);
    w->stats.tf_components+=proof.tf_components;w->stats.tf_mismatches+=proof.tf_mismatches;
    w->stats.visible_pixels+=proof.visible_pixels;
    if(proof.max_error>w->stats.tf_max_error)w->stats.tf_max_error=proof.max_error;
    restore_accepted_state();publish(w,out);
    if(!ok){w->stats.errors++;return 0;}return 1;
}
static int frame(CohSessionWorld *w,const float view[12],const float projection[16],
                           const float center[3],float radius,int allow_empty,CohSessionWorldStats *out,char *error,size_t cap) {
    if(!w||!w->renderer)return problem(w,error,cap,"Static renderer not admitted",COH_STATE);
    if(!select_world(w,center,radius,allow_empty,error,cap)||!packets(w,view,projection,error,cap))return 0;
    CohStatus status=coh_renderer_begin(w->renderer,w->stats.generation);
    for(uint32_t i=0;status==COH_OK&&i<w->draw_count;i++)status=coh_renderer_submit(w->renderer,w->draws+i);
    if(status==COH_OK)status=coh_renderer_flush(w->renderer,(CohCancel){0});
    restore_accepted_state();publish(w,out);
    if(status!=COH_OK)return problem(w,error,cap,"Static renderer frame submission",status);
    w->stats.draws+=w->draw_count;w->stats.draw_packets+=w->draw_count;publish(w,out);return 1;
}
int coh_session_world_draw(CohSessionWorld*w,const float view[12],const float projection[16],const float center[3],float radius,CohSessionWorldStats*out,char*error,size_t cap){return frame(w,view,projection,center,radius,0,out,error,cap);}
int coh_session_world_draw_observed(CohSessionWorld*w,const float view[12],const float projection[16],const float center[3],float radius,CohSessionWorldStats*out,char*error,size_t cap){return frame(w,view,projection,center,radius,1,out,error,cap);}
int coh_session_world_observed_entity(CohSessionWorld*w,const float view[12],
 const float projection[16],uint32_t index,const float position[3],CohSessionWorldStats*out,char*error,size_t cap){
    if(!w||!w->renderer||!position||!w->debug_white)return problem(w,error,cap,"Diagnostic entity draw inputs",COH_STATE);
    float matrix[16];source_gl_matrix(view,matrix);
    CohInitialPoseSample sample={.position={position[0],position[1],position[2]},.valid=1};
    CohRenderTexture white={w->debug_white,COH_WRAP_CLAMP,COH_WRAP_CLAMP,COH_FILTER_NEAREST,COH_FILTER_NEAREST};
    CohRenderDraw draw={0};CohStatus status=coh_debug_entity_draw(&sample,index,matrix,projection,white,&draw);
    draw.material.fog_params[2]=1000000.f;
    if(status==COH_OK)status=coh_renderer_begin(w->renderer,w->stats.generation);
    if(status==COH_OK)status=coh_renderer_submit(w->renderer,&draw);
    if(status==COH_OK)status=coh_renderer_flush(w->renderer,(CohCancel){0});
    restore_accepted_state();
    if(status!=COH_OK)return problem(w,error,cap,"Observed server entity box draw",status);
    publish(w,out);return 1;
}
void coh_session_world_surface_lost(CohSessionWorld *w,int alive,CohSessionWorldStats *out) {
    if(!w)return;
    if(w->renderer){coh_renderer_surface_lost(w->renderer,w->stats.generation+1,alive);coh_renderer_destroy(w->renderer);w->renderer=NULL;}
    if(w->bridge&&coh_bridge_stats(w->bridge).surface_generation==w->stats.generation)
        (void)coh_bridge_surface_lost(w->bridge,w->stats.generation+1,alive);
    if(w->debug_white){texture_release(w,w->debug_white,alive);w->debug_white=0;}
    if(w->gles){coh_renderer_gles_destroy(w->gles,alive);w->gles=NULL;}
    w->stats.gpu_bytes=0;if(alive)restore_accepted_state();if(w->bridge&&w->loader)publish(w,out);
}
void coh_session_world_destroy(CohSessionWorld **pointer) {
    if(!pointer||!*pointer)return;
    CohSessionWorld *w=*pointer;
    coh_session_world_surface_lost(w,0,NULL);release_meshes(w);coh_world_release(&w->selection);
    if(w->bridge)(void)coh_bridge_destroy(&w->bridge,0);
    if(w->map)(void)coh_world_map_destroy(&w->map);
    if(w->loader)(void)coh_asset_destroy(&w->loader);
    coh_world_live_free(w->live);for(unsigned i=0;i<2;i++)coh_asset_zip_free(w->archives[i]);
    coh_session_world_imports_free(w->imports);
    free(w);*pointer=NULL;
}

int coh_session_world_owned_bytes(const CohSessionWorld *w,uint64_t *cpu,uint64_t *gpu) {
    if(!w||!cpu||!gpu||cpu==gpu)return 0;
    uintptr_t lo=(uintptr_t)w,hi=lo+sizeof *w,a=(uintptr_t)cpu,b=(uintptr_t)gpu;
    if(hi<lo||a>UINTPTR_MAX-sizeof *cpu||b>UINTPTR_MAX-sizeof *gpu||
       (a<hi&&lo<a+sizeof *cpu)||(b<hi&&lo<b+sizeof *gpu)||
       (a<b+sizeof *gpu&&b<a+sizeof *cpu))return 0;
    uint64_t c=sizeof *w+coh_world_map_stats(w->map).allocated_bytes+
        coh_asset_stats(w->loader).allocated_bytes+coh_bridge_stats(w->bridge).allocated_bytes+
        coh_renderer_stats(w->renderer).owned_bytes+coh_renderer_gles_owned_bytes(w->gles)+
        coh_world_live_stats(w->live).owned_bytes+coh_asset_zip_stats(w->archives[0]).owned_bytes+coh_asset_zip_stats(w->archives[1]).owned_bytes+coh_session_world_imports_owned_bytes(w->imports);
    uint64_t g=coh_renderer_gles_buffer_bytes(w->gles)+coh_bridge_gpu_bytes(w->bridge)+(w->debug_white?4u:0u);
    *cpu=c;*gpu=g;return 1;
}

int coh_session_world_source_io(const CohSessionWorld *w,uint64_t *reads,uint64_t *bytes){
    if(!w||!w->imports||!reads||!bytes)return 0;
    uintptr_t lo=(uintptr_t)w,hi=lo+sizeof *w,a=(uintptr_t)reads,b=(uintptr_t)bytes;
    if(hi<lo||a>UINTPTR_MAX-sizeof *reads||b>UINTPTR_MAX-sizeof *bytes||
       (a<hi&&lo<a+sizeof *reads)||(b<hi&&lo<b+sizeof *bytes)||
       (a<b+sizeof *bytes&&b<a+sizeof *reads))return 0;
    coh_session_world_imports_io(w->imports,reads,bytes);return 1;
}
