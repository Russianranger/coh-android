#define _POSIX_C_SOURCE 200809L
#include "coh_world_live.h"
#include "../assets/coh_asset_zip.h"
#include "../bridge/coh_asset_render.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#v);return 1;}}while(0)
static unsigned checks;
typedef struct {FILE *file;uint64_t size,reads,fail_at;uint64_t corrupt_at;int corrupt;} Source;
static CohStatus file_read(void *context,uint64_t offset,void *out,size_t bytes){Source *s=context;s->reads++;if(s->fail_at&&s->reads>=s->fail_at)return COH_IO;if(offset>s->size||bytes>s->size-offset||offset>LONG_MAX||fseek(s->file,(long)offset,SEEK_SET)||fread(out,1,bytes,s->file)!=bytes)return COH_IO;if(s->corrupt&&offset<=s->corrupt_at&&s->corrupt_at-offset<bytes)((unsigned char *)out)[s->corrupt_at-offset]^=0x40;return COH_OK;}
static int source(const char *path,Source *s){memset(s,0,sizeof *s);s->file=fopen(path,"rb");if(!s->file||fseek(s->file,0,SEEK_END))return 0;long n=ftell(s->file);if(n<=0)return 0;s->size=(uint64_t)n;return 1;}
static CohAssetSource provider(Source *s){return(CohAssetSource){file_read,s,s->size,1};}
static int cancel(void *context){unsigned *ticks=context;return (*ticks)--==0;}
static CohStatus material(void *context,const char *name,CohBridgeMaterial *out){CohWorldMaterial src;CohStatus s=coh_world_material(context,name,&src);if(s!=COH_OK)return s;memset(out,0,sizeof *out);out->material=coh_renderer_default_material((CohMaterialFamily)src.family);out->material.cull_back=(uint8_t)src.cull_back;out->material.alpha_ref=src.alpha_ref;memcpy(out->uv_scale,src.uv_scale,sizeof src.uv_scale);for(unsigned i=0;i<2;i++)out->textures[i]=src.textures[i];return COH_OK;}
static CohStatus upload(void *ctx,CohAssetId id,uint32_t w,uint32_t h,CohBytes b,uint32_t gen,uint32_t *out){(void)ctx;(void)id;(void)w;(void)h;(void)b;(void)gen;*out=1;return COH_OK;}
static void release(void *context,uint32_t handle,int alive){(void)context;(void)handle;(void)alive;}
int main(int argc,char **argv){
    CHECK(argc==8);Source sources[4];for(unsigned i=0;i<4;i++)CHECK(source(argv[i+1],&sources[i]));
    size_t length=(size_t)sources[0].size;unsigned char *raw=malloc(length);CHECK(raw&&file_read(&sources[0],0,raw,length)==COH_OK);
    CohWorldBundle bundle;CohWorldMap *map=NULL;CHECK(coh_world_bundle_open((CohBytes){raw,length},&bundle)==COH_OK&&bundle.count==11&&coh_world_map_create(bundle.index,&map)==COH_OK);
    CohAssetZipMember atlas[2],client[1];for(unsigned i=0;i<2;i++)atlas[i]=(CohAssetZipMember){bundle.entries[8+i].id.path,(uint32_t)bundle.entries[8+i].bytes.size};client[0]=(CohAssetZipMember){bundle.entries[10].id.path,(uint32_t)bundle.entries[10].bytes.size};
    CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){0},(CohAssetZip **)(UINTPTR_MAX-1))==COH_INVALID);
    CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){0},(CohAssetZip **)atlas)==COH_INVALID);
    CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){0},(CohAssetZip **)(void *)atlas[0].path)==COH_INVALID);
    CohAssetZip *a=NULL,*b=NULL,*sentinel=(CohAssetZip *)(uintptr_t)1;unsigned ticks=0;
    CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){cancel,&ticks},&sentinel)==COH_CANCELLED&&sentinel==(CohAssetZip *)(uintptr_t)1);
    CohAssetZipMember bad[2]={atlas[0],atlas[0]};CHECK(coh_asset_zip_open(provider(&sources[2]),bad,2,(CohCancel){0},&sentinel)==COH_INVALID&&sentinel==(CohAssetZip *)(uintptr_t)1);
    bad[0]=(CohAssetZipMember){"../wrong",1};CHECK(coh_asset_zip_open(provider(&sources[2]),bad,1,(CohCancel){0},&sentinel)==COH_INVALID);
    bad[0]=(CohAssetZipMember){"data/missing.geo",1};CHECK(coh_asset_zip_open(provider(&sources[2]),bad,1,(CohCancel){0},&sentinel)==COH_NOT_FOUND);
    sources[2].corrupt=1;sources[2].corrupt_at=sources[2].size-22;CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){0},&sentinel)==COH_INVALID);sources[2].corrupt=0;
    CHECK(coh_asset_zip_open(provider(&sources[2]),atlas,2,(CohCancel){0},&a)==COH_OK&&coh_asset_zip_open(provider(&sources[3]),client,1,(CohCancel){0},&b)==COH_OK);
    CohAssetLimits limits={4u<<20,512u<<10,1u<<20,1u<<20,128,64,32};CohAssetLoader *loader=NULL;CHECK(coh_asset_create(&limits,&loader)==COH_OK&&coh_asset_zip_mount(a,loader)==COH_OK&&coh_asset_zip_mount(b,loader)==COH_OK);
    sources[2].corrupt=1;sources[2].corrupt_at=strtoull(argv[7],NULL,10);const CohAssetBlob *bad_blob=(const CohAssetBlob *)(uintptr_t)1;
    CHECK(coh_asset_acquire(loader,bundle.entries[8].id,(CohCancel){0},&bad_blob)==COH_INVALID&&bad_blob==(const CohAssetBlob *)(uintptr_t)1);sources[2].corrupt=0;
    /* Native ZIP decode is compared independently with each retained CLIENT
     * body SHA in the Python driver, not merely with its own directory CRC. */
    for(unsigned i=0;i<3;i++){const CohAssetBlob *blob=NULL;CHECK(coh_asset_acquire(loader,bundle.entries[8+i].id,(CohCancel){0},&blob)==COH_OK);CohBytes bytes=coh_asset_bytes(blob);char path[4096];CHECK(snprintf(path,sizeof path,"%s/%u.body",argv[5],i)>0);FILE *out=fopen(path,"wb");CHECK(out&&fwrite(bytes.data,1,bytes.size,out)==bytes.size&&!fclose(out));coh_asset_release(loader,blob);}coh_asset_trim(loader);CHECK(coh_asset_stats(loader).resident_bytes==0);
    CohWorldLive *live=NULL,*unchanged=(CohWorldLive *)(uintptr_t)1;ticks=0;CHECK(coh_world_live_open(provider(&sources[1]),4,(CohCancel){cancel,&ticks},&unchanged)==COH_CANCELLED&&unchanged==(CohWorldLive *)(uintptr_t)1);
    CHECK(coh_world_live_open(provider(&sources[1]),4,(CohCancel){0},&live)==COH_OK);CohWorldLiveStats ls=coh_world_live_stats(live);CHECK(ls.rows==105&&ls.owned_bytes<1024);
    const float first[3]={131.453125f,.25f,-114.953125f},second[3]={-767.9998779296875f,.25f,639.9998779296875f},empty[3]={1000000,0,1000000};
    CohWorldInstance rows[64];memset(rows,0xa5,sizeof rows);CohWorldInstance saved_rows[64];memcpy(saved_rows,rows,sizeof rows);uint32_t count=777;
    CHECK(coh_world_live_query(live,first,24,rows,0,&count,(CohCancel){0})==COH_LIMIT&&count==777&&!memcmp(rows,saved_rows,sizeof rows));
    CHECK(coh_world_live_query(live,first,24,rows,64,(uint32_t *)rows,(CohCancel){0})==COH_INVALID);
    CHECK(coh_world_live_query(live,first,24,(CohWorldInstance *)(UINTPTR_MAX-3),64,&count,(CohCancel){0})==COH_INVALID);
    for(unsigned cut=0;cut<106;cut++){ticks=cut;CHECK(coh_world_live_query(live,first,24,rows,64,&count,(CohCancel){cancel,&ticks})==COH_CANCELLED&&count==777&&!memcmp(rows,saved_rows,sizeof rows));}
    CHECK(coh_world_live_query(live,first,24,rows,64,&count,(CohCancel){0})==COH_OK&&count==2&&rows[0].node==8&&rows[1].node==13);
    CohWorldSelection selected={0};CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_OK&&selected.resident_bytes==328539&&selected.pin_count==3);CohWorldSelection saved=selected;
    CHECK(coh_world_select_instances(map,loader,rows,count,328538,(CohCancel){0},&selected)==COH_LIMIT&&!memcmp(&selected,&saved,sizeof saved));
    rows[1].node=rows[0].node;CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_INVALID&&!memcmp(&selected,&saved,sizeof saved));
    rows[1].node=13;rows[0].world[0]=NAN;CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_INVALID&&!memcmp(&selected,&saved,sizeof saved));
    CHECK(coh_world_select_instances(map,loader,selected.instances,selected.count,328539,(CohCancel){0},&selected)==COH_INVALID);
    CHECK(coh_world_map_destroy(&map)==COH_STATE);
    CohBridgeLimits bl=coh_bridge_default_limits();bl.total_bytes=4u<<20;bl.meshes=16;bl.textures=16;bl.max_vertices=8192;bl.max_triangles=8192;CohBridgeTextureBackend backend={upload,release,NULL};CohAssetRenderBridge *bridge=NULL;CHECK(coh_bridge_create(loader,&bl,&backend,&bridge)==COH_OK);
    CohWorldEndpoint endpoint;CHECK(coh_world_endpoint(map,3,&endpoint)==COH_OK);const CohBridgeMesh *mesh=NULL;CHECK(coh_bridge_acquire_parts(bridge,endpoint.geometry,endpoint.model,1,1,material,&bundle,(CohCancel){0},&mesh)==COH_OK&&coh_bridge_prepare(bridge,mesh,(CohCancel){0})==COH_OK&&coh_bridge_gpu_bytes(bridge)==1310720);
    CHECK(coh_world_live_query(live,second,24,rows,64,&count,(CohCancel){0})==COH_OK&&count>0&&rows[0].node!=8);unsigned second_count=count;CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_OK);
    coh_bridge_release(bridge,mesh);CHECK(coh_world_live_query(live,empty,24,rows,64,&count,(CohCancel){0})==COH_OK&&count==0&&coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_OK);coh_bridge_trim(bridge,1);coh_asset_trim(loader);CHECK(coh_bridge_gpu_bytes(bridge)==0&&coh_asset_stats(loader).resident_bytes==0);
    CHECK(coh_world_live_query(live,second,24,rows,64,&count,(CohCancel){0})==COH_OK&&count==second_count);CohWorldSelection before=selected;sources[2].fail_at=sources[2].reads+1;CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_IO&&!memcmp(&selected,&before,sizeof before));sources[2].fail_at=0;
    CHECK(coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_OK);
    sources[1].corrupt=1;sources[1].corrupt_at=64;count=777;memcpy(rows,saved_rows,sizeof rows);CHECK(coh_world_live_query(live,second,24,rows,64,&count,(CohCancel){0})==COH_INVALID&&count==777&&!memcmp(rows,saved_rows,sizeof rows));sources[1].corrupt=0;
    for(unsigned i=0;i<64;i++){const float *pose=i%2?first:second;CHECK(coh_world_live_query(live,pose,24,rows,64,&count,(CohCancel){0})==COH_OK&&coh_world_select_instances(map,loader,rows,count,328539,(CohCancel){0},&selected)==COH_OK);}
    CohAssetStats as=coh_asset_stats(loader);CohBridgeStats bs=coh_bridge_stats(bridge);size_t archive_bytes=coh_asset_zip_stats(a).owned_bytes+coh_asset_zip_stats(b).owned_bytes;size_t named=length+coh_world_map_stats(map).allocated_bytes+ls.owned_bytes+archive_bytes+as.peak_allocated_bytes+bs.peak_allocated_bytes+sizeof rows+sizeof saved_rows+sizeof selected+sizeof saved+65536;
    CHECK(as.peak_resident_bytes<=512u<<10&&named<96u*1024u*1024u);
    coh_world_release(&selected);CHECK(coh_bridge_destroy(&bridge,1)==COH_OK&&coh_asset_stats(loader).pinned_blobs==0&&coh_asset_destroy(&loader)==COH_OK&&coh_world_map_destroy(&map)==COH_OK);coh_world_live_free(live);coh_asset_zip_free(a);coh_asset_zip_free(b);free(raw);for(unsigned i=0;i<4;i++)CHECK(!fclose(sources[i].file));
    FILE *report=fopen(argv[6],"w");CHECK(report);CHECK(fprintf(report,"{\"passed\":true,\"controls\":%u,\"source_instances\":105,\"first_pose_instances\":2,\"second_pose_instances\":%u,\"peak_source_resident_bytes\":%zu,\"archive_owned_bytes\":%zu,\"bridge_peak_bytes\":%zu,\"named_scene_peak_bytes\":%zu,\"scope\":\"Source payload/controls/64KiB stack; parent Session and driver RSS/PSS separate\"}\n",checks,second_count,as.peak_resident_bytes,archive_bytes,bs.peak_allocated_bytes,named)>0&&!fclose(report));return 0;
}
