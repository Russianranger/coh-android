#include "coh_world_stream.h"
#include "../bridge/coh_asset_render.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(v) do { checks++; if(!(v)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#v);return 1;} } while(0)
static unsigned checks;
static CohStatus material(void *ctx,const char *name,CohBridgeMaterial *out) {
    CohWorldMaterial src;CohStatus s=coh_world_material(ctx,name,&src);if(s!=COH_OK)return s;
    memset(out,0,sizeof *out);out->material=coh_renderer_default_material((CohMaterialFamily)src.family);
    out->material.alpha_ref=src.alpha_ref;out->material.cull_back=(uint8_t)src.cull_back;
    memcpy(out->material.const0,src.const0,sizeof src.const0);memcpy(out->material.const1,src.const1,sizeof src.const1);
    memcpy(out->uv_scale,src.uv_scale,sizeof src.uv_scale);
    for(unsigned i=0;i<2;i++){out->textures[i]=src.textures[i];out->material.textures[i].wrap_s=out->material.textures[i].wrap_t=(CohWrap)src.wrap[i];out->material.textures[i].min_filter=out->material.textures[i].mag_filter=COH_FILTER_LINEAR;}
    return COH_OK;
}
static CohStatus upload(void *ctx,CohAssetId id,uint32_t w,uint32_t h,CohBytes bytes,uint32_t generation,uint32_t *out) {
    (void)ctx;(void)id;(void)w;(void)h;(void)bytes;(void)generation;*out=1;return COH_OK;
}
static void release(void *ctx,uint32_t handle,int alive){(void)ctx;(void)handle;(void)alive;}
static int cancelled(void *ctx){(void)ctx;return 1;}
static void point(const float m[12],const float v[3],double p[3]){for(unsigned i=0;i<3;i++)p[i]=(double)m[i]*v[0]+(double)m[3+i]*v[1]+(double)m[6+i]*v[2]+m[9+i];}
int main(int argc,char **argv) {
    CHECK(argc==3);FILE *f=fopen(argv[1],"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long length=ftell(f);CHECK(length>0&&length<2*1024*1024);rewind(f);
    unsigned char *raw=malloc((size_t)length);CHECK(raw&&fread(raw,1,(size_t)length,f)==(size_t)length);CHECK(!fclose(f));
    CohWorldBundle bundle;CHECK(coh_world_bundle_open((CohBytes){raw,(size_t)length},&bundle)==COH_OK);
    CohWorldMap *map=NULL;CHECK(coh_world_map_create(bundle.index,&map)==COH_OK);CohWorldStats ms=coh_world_map_stats(map);CHECK(ms.nodes<=512&&ms.endpoints==4&&ms.assets==11);
    uint32_t unchanged=73;CHECK(coh_world_endpoint_part_mask(map,ms.endpoints,&unchanged)==COH_INVALID&&unchanged==73);
    CHECK(coh_world_endpoint_part_mask(map,0,(uint32_t *)(uintptr_t)map)==COH_INVALID);
    CHECK(coh_world_endpoint_part_mask(map,0,(uint32_t *)(UINTPTR_MAX-1))==COH_INVALID);
    unsigned char *bad_index=malloc(bundle.index.size);CHECK(bad_index);memcpy(bad_index,bundle.index.data,bundle.index.size);bad_index[8]=1;
    CohWorldMap *unpublished=NULL;CHECK(coh_world_map_create((CohBytes){bad_index,bundle.index.size},&unpublished)==COH_INVALID&&!unpublished);free(bad_index);
    CohAssetLimits limits={4u<<20,512u<<10,1u<<20,1u<<20,128,64,32};CohAssetLoader *loader=NULL;
    CHECK(coh_asset_create(&limits,&loader)==COH_OK&&coh_world_bundle_mount(&bundle,loader,(CohCancel){0})==COH_OK);
    CohBridgeLimits bl=coh_bridge_default_limits();bl.total_bytes=4u<<20;bl.meshes=16;bl.textures=16;bl.max_vertices=8192;bl.max_triangles=8192;
    CohBridgeTextureBackend backend={upload,release,NULL};CohAssetRenderBridge *bridge=NULL;CHECK(coh_bridge_create(loader,&bl,&backend,&bridge)==COH_OK);
    /* Old preview dependencies remain alive during the next atomic selection. */
    const float old_center[3]={582.5f,74,-1380},pose[3]={131.453125f,.25f,-114.953125f};uint32_t ids[64],count=0;
    CohWorldSelection selection={0};CHECK(coh_world_query(map,old_center,24,ids,64,&count)==COH_OK&&count==6);
    CHECK(coh_world_select(map,loader,ids,count,512u<<10,(CohCancel){0},&selection)==COH_OK);
    CHECK(coh_world_query(map,pose,24,ids,64,&count)==COH_OK&&count>0);
    unsigned old_count=selection.count;CHECK(coh_world_select(map,loader,ids,count,328538,(CohCancel){0},&selection)==COH_LIMIT&&selection.count==old_count);
    CHECK(coh_world_select(map,loader,ids,count,512u<<10,(CohCancel){cancelled,NULL},&selection)==COH_CANCELLED&&selection.count==old_count);
    CHECK(coh_world_select(map,loader,ids,count,328539,(CohCancel){0},&selection)==COH_OK&&selection.resident_bytes==328539);
    unsigned ground=0,parts=0;size_t packet_bytes=0;
    for(uint32_t i=0;i<selection.count;i++) {
        CohWorldEndpoint ep;uint32_t mask=0;CHECK(coh_world_endpoint(map,selection.instances[i].endpoint,&ep)==COH_OK&&coh_world_endpoint_part_mask(map,selection.instances[i].endpoint,&mask)==COH_OK&&mask==1);
        const CohBridgeMesh *mesh=NULL;CHECK(coh_bridge_acquire_parts(bridge,ep.geometry,ep.model,1,mask,material,&bundle,(CohCancel){0},&mesh)==COH_OK&&coh_bridge_mesh_parts(mesh)==1);
        CohRenderGeometry geo;CohRenderMaterial mat;CHECK(coh_bridge_mesh_part(mesh,0,&geo,&mat)==COH_OK&&geo.vertex_count==120&&geo.index_count==36);parts++;
        if(i==0){FILE *packet=fopen(argv[2],"wb");CHECK(packet&&fwrite(geo.vertices,sizeof(*geo.vertices),geo.vertex_count,packet)==geo.vertex_count&&fwrite(geo.indices,sizeof(*geo.indices),geo.index_count,packet)==geo.index_count&&!fclose(packet));packet_bytes=(size_t)geo.vertex_count*sizeof(*geo.vertices)+(size_t)geo.index_count*sizeof(*geo.indices);}
        for(uint32_t t=0;t<geo.index_count;t+=3){double p[3][3];for(unsigned v=0;v<3;v++)point(selection.instances[i].world,geo.vertices[geo.indices[t+v]].position,p[v]);double den=(p[1][2]-p[2][2])*(p[0][0]-p[2][0])+(p[2][0]-p[1][0])*(p[0][2]-p[2][2]);if(fabs(den)<1e-9)continue;double u=((p[1][2]-p[2][2])*(pose[0]-p[2][0])+(p[2][0]-p[1][0])*(pose[2]-p[2][2]))/den,v=((p[2][2]-p[0][2])*(pose[0]-p[2][0])+(p[0][0]-p[2][0])*(pose[2]-p[2][2]))/den;if(u>=0&&v>=0&&u+v<=1){double y=u*p[0][1]+v*p[1][1]+(1-u-v)*p[2][1];if(y<=pose[1]&&pose[1]-y<.5)ground++;}}
        coh_bridge_release(bridge,mesh);
    }
    CHECK(ground>0);CohBridgeStats bs=coh_bridge_stats(bridge);CohAssetStats as=coh_asset_stats(loader);CHECK(bs.mesh_loads==1&&bs.texture_loads==2&&as.peak_resident_bytes<=512u*1024u);
    CohBridgeLimits tiny=bl;tiny.total_bytes=32u<<10;CohAssetRenderBridge *limited=NULL;
    CHECK(coh_bridge_create(loader,&tiny,&backend,&limited)==COH_OK);
    CohWorldEndpoint endpoint;CHECK(coh_world_endpoint(map,selection.instances[0].endpoint,&endpoint)==COH_OK);
    const CohBridgeMesh *sentinel=(const CohBridgeMesh *)(uintptr_t)1;
    CHECK(coh_bridge_acquire_parts(limited,endpoint.geometry,endpoint.model,1,1,material,&bundle,(CohCancel){0},&sentinel)==COH_LIMIT&&sentinel==(const CohBridgeMesh *)(uintptr_t)1);
    CHECK(coh_bridge_stats(limited).pins==0&&coh_bridge_stats(limited).peak_allocated_bytes<=tiny.total_bytes&&coh_asset_stats(loader).pinned_blobs==as.pinned_blobs);
    CHECK(coh_bridge_destroy(&limited,1)==COH_OK);
    size_t named=(size_t)length+ms.allocated_bytes+bs.peak_allocated_bytes+as.peak_allocated_bytes+sizeof bundle+sizeof selection+65536;
    CHECK(named<96u*1024u*1024u);CHECK(coh_world_map_destroy(&map)==COH_STATE);
    coh_world_release(&selection);CHECK(coh_bridge_destroy(&bridge,1)==COH_OK&&coh_asset_stats(loader).pinned_blobs==0&&coh_asset_destroy(&loader)==COH_OK&&coh_world_map_destroy(&map)==COH_OK);free(raw);
    printf("{\"passed\":true,\"checks\":%u,\"selected_instances\":%u,\"source_parts\":%u,\"ground_triangles_under_pose\":%u,\"dependency_bytes\":328539,\"peak_resident_bytes\":%zu,\"bridge_peak_bytes\":%zu,\"named_peak_with_source_map_and_64KiB_stack\":%zu,\"source_packet_bytes\":%zu,\"scope\":\"host source/owner payload; excludes parent session and driver RSS/PSS\"}\n",checks,count,parts,ground,as.peak_resident_bytes,bs.peak_allocated_bytes,named,packet_bytes);return 0;
}
