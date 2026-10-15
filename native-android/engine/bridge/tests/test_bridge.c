#include "../coh_asset_render.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static unsigned checks;
#define CHECK(x) do { checks++;assert(x); } while(0)
typedef struct { unsigned char *bytes;size_t size; } File;
static const char *files[]={"misc.geo","trainstation.geo","bench.texture","sign.texture",
    "white.texture","grey.texture","mono_station_infloor.texture","mono_station_infloor_sml.texture"};
static const char *paths[]={
    "data/object_library/streets/elements/misc_sm/misc_sm.geo",
    "data/object_library/special_buildings/trainstation/trainstation.geo",
    "data/texture_library/world/streets/elements/monorail/modern_bench.texture",
    "data/texture_library/world/swappables_and_decals/signs/billboard/billboard_structure/signmetal.texture",
    "assets/texture_library/world/filler/white.texture",
    "assets/texture_library/world/filler/grey.texture",
    "data/texture_library/world/streets/elements/monorail/mono_station_infloor.texture",
    "data/texture_library/world/streets/elements/monorail/mono_station_infloor_sml.texture"};
static CohStatus read_at(void *ctx,uint64_t offset,void *out,size_t count) {
    File *f=ctx;if(offset>f->size||count>f->size-(size_t)offset)return COH_IO;
    memcpy(out,f->bytes+(size_t)offset,count);return COH_OK;
}
typedef struct { uint32_t next,uploads,releases,lost_releases,draws;int fail;float mv[16],pr[16];const char *directory; } Backend;
static CohStatus upload(void *ctx,CohAssetId id,uint32_t w,uint32_t h,CohBytes rgba,uint32_t gen,uint32_t *handle) {
    Backend *b=ctx;CHECK(id.path&&id.generation==1&&w&&h&&rgba.size==(size_t)w*h*4&&gen<=1);
    if(!b->fail&&gen==0) {
        unsigned i;for(i=2;i<8;i++)if(strcmp(paths[i],id.path)==0)break;CHECK(i<8);
        char path[4096];CHECK(snprintf(path,sizeof(path),"%s/%s.rgba",b->directory,files[i])>0);
        FILE *f=fopen(path,"wb");CHECK(f!=NULL);CHECK(fwrite(rgba.data,1,rgba.size,f)==rgba.size);CHECK(fclose(f)==0);
    }
    *handle=++b->next;b->uploads++;return b->fail?COH_IO:COH_OK;
}
static void release_texture(void *ctx,uint32_t handle,int alive) {
    Backend *b=ctx;CHECK(handle!=0);b->releases++;if(!alive)b->lost_releases++;
}
static CohStatus resolve(void *ctx,const char *name,CohBridgeMaterial *out) {
    int bad=ctx?*(int *)ctx:0;memset(out,0,sizeof(*out));
    unsigned primary=0,secondary=5;CohMaterialFamily family=COH_MAT_MULTIPLY;float scale=1;
    if(strcmp(name,"Signmetal.tga")==0)primary=3;
    else if(strcmp(name,"modern_bench.tga")==0){primary=2;secondary=4;family=COH_MAT_DUAL;}
    else if(strcmp(name,"mono_station_infloor.tga")==0){primary=6;scale=14;}
    else if(strcmp(name,"mono_station_infloor_sml.tga")==0){primary=7;scale=8;}
    else return COH_NOT_FOUND;
    out->material=coh_renderer_default_material(family);
    out->material.lighting=COH_LIGHT_DIFFUSE;
    for(unsigned j=0;j<3;j++) {out->material.ambient[j]=.25f;out->material.diffuse[j]=0;}
    for(unsigned i=0;i<2;i++) {
        out->material.textures[i].wrap_s=out->material.textures[i].wrap_t=COH_WRAP_REPEAT;
        out->material.textures[i].min_filter=out->material.textures[i].mag_filter=COH_FILTER_LINEAR;
        out->uv_scale[i][0]=out->uv_scale[i][1]=i?1:scale;
    }
    out->textures[0]=(CohAssetId){paths[primary],1};out->textures[1]=(CohAssetId){paths[secondary],1};
    if(bad==1)out->uv_scale[0][0]=NAN;
    if(bad==2)out->textures[1].path="missing.texture";
    if(bad==3)out->material.textures[0].min_filter=COH_FILTER_MIP_LINEAR;
    return COH_OK;
}
static CohStatus compile(void *ctx,CohMaterialFamily family,const char *v,const char *f,uint32_t *out) {
    Backend *b=ctx;CHECK(v&&f&&family<=COH_MAT_ADDGLOW);*out=++b->next;return COH_OK;
}
static void destroy_program(void *ctx,uint32_t p) {(void)ctx;CHECK(p!=0);}
static CohStatus bind(void *ctx,uint32_t p,const CohRenderMaterial *m) {(void)ctx;CHECK(p&&m->textures[0].handle&&m->textures[1].handle);return COH_OK;}
static CohStatus draw(void *ctx,uint32_t program,const CohRenderDraw *d) {
    Backend *b=ctx;CHECK(program&&d->geometry.vertex_count&&d->geometry.index_count);
    CHECK(memcmp(b->mv,d->model_view,sizeof(b->mv))==0&&memcmp(b->pr,d->projection,sizeof(b->pr))==0);
    b->draws++;return COH_OK;
}
static int yes(void *p){(void)p;return 1;}
static void dump(const CohBridgeMesh *m,const char *dir,const char *name) {
    char path[4096];CHECK(snprintf(path,sizeof(path),"%s/%s",dir,name)>0);
    FILE *f=fopen(path,"wb");CHECK(f!=NULL);
    uint32_t count=coh_bridge_mesh_parts(m);CHECK(fwrite(&count,4,1,f)==1);
    for(uint32_t p=0;p<count;p++) {
        CohRenderGeometry g;CohRenderMaterial mat;CHECK(coh_bridge_mesh_part(m,p,&g,&mat)==COH_OK);
        uint32_t header[3]={(uint32_t)g.vertex_count,(uint32_t)g.index_count,(uint32_t)mat.family};
        CHECK(fwrite(header,sizeof(header),1,f)==1);
        CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,f)==g.vertex_count);
        CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,f)==g.index_count);
    }
    CHECK(fclose(f)==0);
}
int main(int argc,char **argv) {
    CHECK(argc==3);File file[8];memset(file,0,sizeof(file));
    CohAssetLoader *loader=NULL;CohAssetLimits al={8u<<20,512u<<10,2u<<20,2u<<20,16,16,8};
    CHECK(coh_asset_create(&al,&loader)==COH_OK);
    for(unsigned i=0;i<8;i++) {
        char path[4096];CHECK(snprintf(path,sizeof(path),"%s/%s",argv[1],files[i])>0);
        FILE *f=fopen(path,"rb");CHECK(f!=NULL);CHECK(fseek(f,0,SEEK_END)==0);
        long size=ftell(f);CHECK(size>0&&size<(2<<20));file[i].size=(size_t)size;
        CHECK(fseek(f,0,SEEK_SET)==0);file[i].bytes=malloc(file[i].size);CHECK(file[i].bytes!=NULL);
        CHECK(fread(file[i].bytes,1,file[i].size,f)==file[i].size);CHECK(fclose(f)==0);
        CohAssetSource source={read_at,file+i,file[i].size,1};CHECK(coh_asset_mount_file(loader,paths[i],source)==COH_OK);
    }
    Backend mock;memset(&mock,0,sizeof(mock));
    mock.directory=argv[2];
    for(unsigned i=0;i<16;i++)mock.mv[i]=mock.pr[i]=(i%5==0)?1.f:0.f;
    mock.mv[12]=582.5f;mock.mv[13]=74;mock.mv[14]=-1380;mock.pr[0]=.25f;
    CohBridgeTextureBackend tb={upload,release_texture,&mock};CohBridgeLimits limits=coh_bridge_default_limits();
    CohAssetRenderBridge *bridge=NULL;CHECK(coh_bridge_create(loader,&limits,&tb,&bridge)==COH_OK);
    size_t baseline=coh_bridge_stats(bridge).allocated_bytes;
    CohRenderBackend backend={compile,destroy_program,bind,draw,&mock};CohRenderer *renderer=NULL;
    CohRendererConfig rc=coh_renderer_default_config();CHECK(coh_renderer_create(&rc,&backend,&renderer)==COH_OK);
    const CohBridgeMesh *bench=NULL,*bench4=NULL,*floor=NULL,*again=NULL,*sentinel=(const CohBridgeMesh *)(uintptr_t)1;
    CohAssetId bench_id={paths[0],1},floor_id={paths[1],1};CohCancel cancel={0};
    CHECK(coh_bridge_acquire(bridge,bench_id,"missing-model",1,resolve,NULL,cancel,&sentinel)==COH_NOT_FOUND&&sentinel==(const CohBridgeMesh *)(uintptr_t)1);
    CHECK(coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",1,resolve,NULL,(CohCancel){yes,NULL},&sentinel)==COH_CANCELLED);
    for(int bad=1;bad<=3;bad++) {
        CohStatus s=coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",(uint32_t)bad+10,resolve,&bad,cancel,&sentinel);
        CHECK(s==(bad==2?COH_NOT_FOUND:COH_UNSUPPORTED));CHECK(sentinel==(const CohBridgeMesh *)(uintptr_t)1);
        CHECK(coh_asset_stats(loader).pinned_blobs==0&&coh_bridge_stats(bridge).pins==0);
    }
    coh_bridge_trim(bridge,1);CHECK(coh_bridge_stats(bridge).allocated_bytes==baseline);
    uint64_t initial_texture_loads=coh_bridge_stats(bridge).texture_loads;
    CohStatus first=coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",1,resolve,NULL,cancel,&bench);
    if(first!=COH_OK)fprintf(stderr,"authentic bench admission status: %d\n",(int)first);
    CHECK(first==COH_OK);
    CHECK(coh_bridge_acquire(bridge,bench_id,"modern_bench_4wide__mbench",1,resolve,NULL,cancel,&bench4)==COH_OK);
    CHECK(coh_bridge_acquire(bridge,floor_id,"_trnstation_infloor",1,resolve,NULL,cancel,&floor)==COH_OK);
    CHECK(coh_bridge_mesh_parts(bench)==2&&coh_bridge_mesh_parts(floor)==2);
    CHECK(coh_bridge_acquire(bridge,(CohAssetId){paths[0],0},"MODERN_BENCH_2WIDE__MBENCH",1,resolve,NULL,cancel,&again)==COH_OK&&again==bench);
    coh_bridge_release(bridge,again);CHECK(coh_bridge_stats(bridge).mesh_hits==1);
    CHECK(coh_bridge_destroy(&bridge,1)==COH_STATE&&bridge!=NULL);
    coh_asset_trim(loader);CHECK(coh_asset_stats(loader).pinned_blobs==0&&coh_asset_stats(loader).resident_bytes==0);
    coh_bridge_trim(bridge,1);CHECK(coh_bridge_stats(bridge).meshes==3);
    CHECK(coh_renderer_begin(renderer,0)==COH_OK);
    CHECK(coh_bridge_submit(bridge,bench,renderer,mock.mv,mock.pr)==COH_STATE);
    mock.fail=1;CHECK(coh_bridge_prepare(bridge,bench,cancel)==COH_IO&&mock.releases==1);mock.fail=0;
    CHECK(coh_bridge_prepare(bridge,bench,cancel)==COH_OK);
    CHECK(coh_bridge_prepare(bridge,floor,cancel)==COH_OK);
    uint32_t uploads=mock.uploads;CHECK(uploads==7); /* six unique + failed owned handle */
    CHECK(coh_bridge_prepare(bridge,bench,cancel)==COH_OK&&mock.uploads==uploads);
    CHECK(coh_bridge_submit(bridge,bench,renderer,mock.mv,mock.pr)==COH_OK);
    CHECK(coh_bridge_submit(bridge,floor,renderer,mock.mv,mock.pr)==COH_OK);
    CHECK(coh_renderer_flush(renderer,cancel)==COH_OK&&mock.draws==4);
    dump(bench,argv[2],"bench.packet");dump(bench4,argv[2],"bench4.packet");dump(floor,argv[2],"floor.packet");
    coh_renderer_surface_lost(renderer,1,0);CHECK(coh_bridge_surface_lost(bridge,1,0)==COH_OK);
    CHECK(mock.lost_releases==6);CHECK(coh_bridge_surface_lost(bridge,1,0)==COH_STATE);
    CHECK(coh_renderer_begin(renderer,1)==COH_OK);
    CHECK(coh_bridge_submit(bridge,floor,renderer,mock.mv,mock.pr)==COH_STATE);
    CHECK(coh_bridge_prepare(bridge,bench,cancel)==COH_OK&&coh_bridge_prepare(bridge,floor,cancel)==COH_OK);
    CHECK(mock.uploads==uploads+6);CHECK(coh_bridge_submit(bridge,floor,renderer,mock.mv,mock.pr)==COH_OK);
    CHECK(coh_renderer_flush(renderer,cancel)==COH_OK&&mock.draws==6);
    CHECK(coh_bridge_stats(bridge).texture_loads==initial_texture_loads+6);
    CohBridgeStats steady=coh_bridge_stats(bridge);
    for(unsigned i=0;i<1000;i++) {
        CHECK(coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",1,resolve,NULL,cancel,&again)==COH_OK);
        coh_bridge_release(bridge,again);CHECK(coh_bridge_stats(bridge).allocated_bytes==steady.allocated_bytes);
    }
    coh_bridge_release(bridge,bench);coh_bridge_release(bridge,bench4);coh_bridge_release(bridge,floor);coh_bridge_trim(bridge,1);
    CHECK(coh_bridge_stats(bridge).allocated_bytes==baseline&&coh_bridge_stats(bridge).meshes==0&&coh_bridge_stats(bridge).textures==0);
    CHECK(coh_bridge_destroy(&bridge,1)==COH_OK&&bridge==NULL&&coh_bridge_destroy(&bridge,1)==COH_OK);
    coh_renderer_destroy(renderer);CHECK(coh_asset_destroy(&loader)==COH_OK);
    /* Pin pressure cannot evict a borrowed packet; transactional output stays. */
    CHECK(coh_asset_create(&al,&loader)==COH_OK);
    for(unsigned i=0;i<8;i++)CHECK(coh_asset_mount_file(loader,paths[i],(CohAssetSource){read_at,file+i,file[i].size,1})==COH_OK);
    limits.meshes=1;CHECK(coh_bridge_create(loader,&limits,&tb,&bridge)==COH_OK);
    CHECK(coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",1,resolve,NULL,cancel,&bench)==COH_OK);
    CHECK(coh_bridge_acquire(bridge,floor_id,"_trnstation_infloor",1,resolve,NULL,cancel,&sentinel)==COH_LIMIT);
    CHECK(coh_bridge_mesh_parts(bench)==2);coh_bridge_release(bridge,bench);
    CHECK(coh_bridge_acquire(bridge,floor_id,"_trnstation_infloor",1,resolve,NULL,cancel,&floor)==COH_OK);
    CHECK(coh_bridge_stats(bridge).evictions>=1);coh_bridge_release(bridge,floor);
    CHECK(coh_bridge_destroy(&bridge,1)==COH_OK);
    limits=coh_bridge_default_limits();limits.total_bytes=80u<<10;
    CHECK(coh_bridge_create(loader,&limits,&tb,&bridge)==COH_OK);
    size_t bounded_baseline=coh_bridge_stats(bridge).allocated_bytes;
    CHECK(coh_bridge_acquire(bridge,bench_id,"modern_bench_2wide__mbench",1,resolve,NULL,cancel,&sentinel)==COH_LIMIT);
    coh_bridge_trim(bridge,1);
    CHECK(coh_bridge_stats(bridge).allocated_bytes==bounded_baseline&&coh_bridge_stats(bridge).peak_allocated_bytes<=limits.total_bytes);
    CHECK(coh_bridge_destroy(&bridge,1)==COH_OK&&coh_asset_destroy(&loader)==COH_OK);
    for(unsigned i=0;i<8;i++)free(file[i].bytes);
    printf("{\"passed\":true,\"assertions\":%u,\"authentic_meshes\":3,\"material_parts\":6,\"unique_textures\":6,\"texture_loads\":%llu,\"sustained_cache_cycles\":1000,\"peak_counted_bytes\":%zu,\"android_execution\":false}\n",checks,(unsigned long long)steady.texture_loads,steady.peak_allocated_bytes);
    return 0;
}
