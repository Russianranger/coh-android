#include "coh_offline_world.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
static unsigned checks;
#define CHECK(x) do { checks++;if(!(x)){fprintf(stderr,"check failed line %d: %s\n",__LINE__,#x);return 1;} } while(0)
static const unsigned char payload[4]={1,2,3,4};
static CohStatus read_at(void *ctx,uint64_t offset,void *out,size_t bytes) {
    (void)ctx;if(offset>4||bytes>4-offset)return COH_IO;memcpy(out,payload+offset,bytes);return COH_OK;
}
static int cancelled(void *context){unsigned *n=context;return (*n)--==0;}
int main(void) {
    CohAssetLoader *loader=NULL;CohAssetLimits limits={65536,4096,4096,4096,16,16,16};
    CohAssetId assets[2]={{"data/a.geo",1},{"data/b.texture",1}};
    uint32_t dependencies[4]={0,1,0,1};
    CohOfflineCell cells[2]={{{-2,-2,-2},{2,2,2},0,1},{{98,-2,-2},{102,2,2},1,1}};
    CohOfflineInstance instances[2]={{1,0,0,2,1,{1,0,0,0,1,0,0,0,1,0,0,0},{0,0,0},1},
                                   {2,1,2,2,1,{1,0,0,0,1,0,0,0,1,100,0,0},{100,0,0},1}};
    CohOfflineWorld world={1,2,2,2,4,instances,cells,assets,dependencies};
    CohOfflineSelection selected={0},before;CohOfflineSelectionStats stats;float center[3]={0,0,0},matrix[12];
    CohCancel no={0};unsigned i,n;CohAssetStats cache;
    CHECK(coh_asset_create(&limits,&loader)==COH_OK);
    for(i=0;i<2;i++){CohAssetSource s={read_at,NULL,4,1};CHECK(coh_asset_mount_file(loader,assets[i].path,s)==COH_OK);}
    CHECK(coh_offline_validate(&world)==COH_OK);
    CHECK(coh_offline_select(&world,loader,1,center,5,8,no,&selected,&stats)==COH_OK);
    CHECK(selected.count==1&&selected.pin_count==2&&selected.resident_bytes==8);
    CHECK(stats.tested_cells==2&&stats.visible_cells==1&&stats.tested_instances==1);
    CHECK(coh_offline_transform(&world,1,0,matrix)==COH_OK&&memcmp(matrix,instances[0].world,sizeof matrix)==0);
    before=selected;CHECK(coh_offline_select(&world,loader,2,center,5,8,no,&selected,&stats)==COH_STATE);CHECK(memcmp(&before,&selected,sizeof before)==0);
    CHECK(coh_offline_select(&world,loader,1,center,5,7,no,&selected,&stats)==COH_LIMIT);CHECK(memcmp(&before,&selected,sizeof before)==0);
    instances[0].ready=0;CHECK(coh_offline_select(&world,loader,1,center,5,8,no,&selected,&stats)==COH_NOT_FOUND);CHECK(stats.unavailable_instances==1&&memcmp(&before,&selected,sizeof before)==0);instances[0].ready=1;
    for(n=0;n<5;n++){unsigned cut=n;CohCancel stop={cancelled,&cut};CHECK(coh_offline_select(&world,loader,1,center,5,8,stop,&selected,&stats)==COH_CANCELLED);CHECK(memcmp(&before,&selected,sizeof before)==0);}
    CHECK(coh_offline_select(&world,loader,1,center,200,8,no,&selected,&stats)==COH_OK);CHECK(selected.count==2&&selected.pin_count==2&&stats.required_bytes==8);
    for(i=0;i<1000;i++) { center[0]=(i&1)?100:0;CHECK(coh_offline_select(&world,loader,1,center,1,8,no,&selected,&stats)==COH_OK);CHECK(selected.count==1&&selected.instances[0]==(i&1));CHECK(coh_offline_transform(&world,1,selected.instances[0],matrix)==COH_OK);CHECK(!memcmp(matrix,instances[i&1].world,sizeof matrix)); }
    cache=coh_asset_stats(loader);CHECK(cache.resident_bytes==8&&cache.cache_misses==2&&cache.cache_hits>=2000);
    cells[1].first=0;CHECK(coh_offline_validate(&world)==COH_INVALID);cells[1].first=1;
    cells[1].minimum[0]=100;CHECK(coh_offline_validate(&world)==COH_INVALID);cells[1].minimum[0]=98;
    instances[1].source_id=1;CHECK(coh_offline_validate(&world)==COH_INVALID);instances[1].source_id=2;
    instances[1].world[0]=NAN;CHECK(coh_offline_validate(&world)==COH_INVALID);instances[1].world[0]=1;
    instances[1].radius=INFINITY;CHECK(coh_offline_validate(&world)==COH_INVALID);instances[1].radius=1;
    dependencies[0]=2;CHECK(coh_offline_validate(&world)==COH_INVALID);dependencies[0]=0;
    assets[1].path="data/A.geo";CHECK(coh_offline_validate(&world)==COH_INVALID);assets[1].path="data/../secret";CHECK(coh_offline_validate(&world)==COH_INVALID);assets[1].path="data/b.texture";
    center[0]=NAN;CHECK(coh_offline_select(&world,loader,1,center,1,8,no,&selected,&stats)==COH_INVALID);center[0]=0;
    CHECK(coh_offline_transform(&world,2,0,matrix)==COH_STATE);
    { char unterminated[COH_ASSET_PATH_MAX];memset(unterminated,'a',sizeof unterminated);assets[1].path=unterminated;CHECK(coh_offline_validate(&world)==COH_INVALID);assets[1].path="data/b.texture"; }
    { CohOfflineInstance many[257];CohOfflineCell cell={{-2,-2,-2},{2,2,2},0,257};CohOfflineWorld crowded=world;before=selected;
      for(i=0;i<257;i++){many[i]=instances[0];many[i].source_id=i+1;}
      crowded.instance_count=257;crowded.instances=many;crowded.cell_count=1;crowded.cells=&cell;
      CHECK(coh_offline_validate(&crowded)==COH_OK);CHECK(coh_offline_select(&crowded,loader,1,center,5,8,no,&selected,&stats)==COH_LIMIT);CHECK(memcmp(&before,&selected,sizeof before)==0);
    }
    { CohOfflineInstance many[1024];CohOfflineCell spatial[256];CohOfflineWorld large=world;
      for(i=0;i<1024;i++){many[i]=instances[0];many[i].source_id=i+1;many[i].cell=i/4;many[i].center[0]=(float)(i/4)*1000+(float)(i%4);many[i].world[9]=many[i].center[0];}
      for(i=0;i<256;i++){spatial[i]=cells[0];spatial[i].first=i*4;spatial[i].count=4;spatial[i].minimum[0]=(float)i*1000-2;spatial[i].maximum[0]=(float)i*1000+5;}
      large.instance_count=1024;large.instances=many;large.cell_count=256;large.cells=spatial;
      CHECK(coh_offline_validate(&large)==COH_OK);CHECK(coh_offline_select(&large,loader,1,center,10,8,no,&selected,&stats)==COH_OK);CHECK(stats.tested_cells==256&&stats.tested_instances==4&&selected.count==4);
    }
    CHECK(coh_offline_validate(&world)==COH_OK);coh_offline_release(&selected);coh_asset_trim(loader);cache=coh_asset_stats(loader);CHECK(cache.resident_bytes==0&&cache.pinned_blobs==0);CHECK(coh_asset_destroy(&loader)==COH_OK);
    printf("{\"passed\":true,\"assertions\":%u,\"stream_cycles\":1000,\"spatial_scale_instances\":1024,\"spatial_scale_cells\":256,\"spatial_scale_instances_tested\":4,\"real_cache_misses\":2,\"peak_raw_residency_bytes\":8,\"runtime_allocations\":0,\"runtime_allocation_scope\":\"planner source has no allocation calls; loader uses bounded existing cache\",\"exact_matrix_copy_checks\":1001}\n",checks);
    return 0;
}
