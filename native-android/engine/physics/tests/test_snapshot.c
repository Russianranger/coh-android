#include "../coh_physics_snapshot.h"
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static unsigned checks,failed,walk_steps,refreshes;
static uint64_t alloc_calls,live_allocations;static int track_allocs;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){void *p;if(track_allocs)alloc_calls++;p=__real_malloc(n);if(p)live_allocations++;return p;}
void *__wrap_calloc(size_t n,size_t m){void *p;if(track_allocs)alloc_calls++;p=__real_calloc(n,m);if(p)live_allocations++;return p;}
void *__wrap_realloc(void *p,size_t n){void *q;if(track_allocs)alloc_calls++;q=__real_realloc(p,n);if(!p&&q)live_allocations++;else if(p&&!n)live_allocations--;return q;}
void __wrap_free(void *p){if(track_allocs)alloc_calls++;if(p)live_allocations--;__real_free(p);}
#define CHECK(c) do{checks++;if(!(c)){failed++;fprintf(stderr,"snapshot check line %d: %s\n",__LINE__,#c);}}while(0)
static const CohPhysicsBudget budget={1000000,COH_PHYSICS_MAX_TRIANGLES};
static int cancel_now(void *p){(void)p;return 1;}
static void quad(CohWalkTriangle *t,float x,float z,float y0,float y1){
    t[0]=(CohWalkTriangle){{{x,y0,z},{x,y0,z+128},{x+128,y1,z}},COH_WALK_NORMALTRI};
    t[1]=(CohWalkTriangle){{{x+128,y1,z},{x,y0,z+128},{x+128,y1,z+128}},COH_WALK_NORMALTRI};
}
/* Each reader receives an owned ref before publication. Release the publisher's
 * ref while queries are executing, then retire each reader's ref independently. */
typedef struct {CohPhysicsSnapshot *s;unsigned failed,queries;} Reader;
static void *reader(void *p){Reader *r=p;
    for(unsigned i=0;i<2000;i++){
        CohPhysicsContact c={0};CohPhysicsQueryStats st;CohPhysicsAdmission a;
        if(coh_physics_snapshot_retain(r->s)!=COH_OK){r->failed++;break;}
        if(coh_physics_snapshot_query(r->s,(float[]){-32,8,-32},(float[]){-32,-8,-32},0,
            COH_PHYSICS_FROM_START|COH_PHYSICS_BOTH_SIDES,budget,&c,&st,&a)!=COH_OK||!c.hit)r->failed++;
        coh_physics_snapshot_release(r->s);r->queries++;
    }
    coh_physics_snapshot_release(r->s);return NULL;
}
int main(void){
    CohWalkTriangle triangles[8];CohPhysicsSegment segments[4];CohPhysicsCoverageCell cells[16];
    CohPhysicsCoverageGrid grid={-128,-128,64,-128,128,4,4,cells};
    CohPhysicsSnapshot *s=NULL,*missing=NULL,*replacement=NULL;CohPhysicsSnapshotInfo info;
    CohPhysicsContact c={0},prior;CohPhysicsQueryStats st;CohPhysicsAdmission a;
    CohPhysicsWalker w={0};CohWalkWorld direct={0};CohWalkState oracle;
    float lo[3]={-128,-2,-128},hi[3]={128,2,128},spawn[3]={-64,-1,-32},extents[3]={32,32,32};
    /* Four connected source-qualified synthetic regions: a continuous X slope
     * split at X/Z seams. These are not claimed to be authentic game terrain. */
    for(unsigned i=0;i<4;i++){
        unsigned x=i%2,z=i/2;quad(triangles+2*i,x?0:-128,z?0:-128,x?0:-2,x?2:0);
        segments[i]=(CohPhysicsSegment){100+i,7,triangles+2*i,2};
    }
    for(unsigned z=0;z<4;z++)for(unsigned x=0;x<4;x++)
        cells[z*4+x]=(CohPhysicsCoverageCell){100+(z/2)*2+x/2,7,COH_PHYSICS_CELL_LOADED};
    CHECK(coh_physics_snapshot_create(&s,segments,4,101,&grid,1024*1024,NULL)==COH_OK);
    CHECK(coh_physics_snapshot_info(s,&info)==COH_OK);CHECK(info.loaded_cells==16&&info.missing_cells==0);
    size_t memory=info.owned_bytes;CHECK(memory>info.scene.owned_bytes&&memory<16384);
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,102,&grid,memory-1,NULL)==COH_LIMIT);CHECK(!replacement);
    CohCancel cancel={cancel_now,NULL};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,102,&grid,1024*1024,&cancel)==COH_CANCELLED);CHECK(!replacement);
    cells[6]=(CohPhysicsCoverageCell){0,0,COH_PHYSICS_CELL_MISSING};
    CHECK(coh_physics_snapshot_create(&missing,segments,4,102,&grid,1024*1024,NULL)==COH_OK);
    cells[6]=(CohPhysicsCoverageCell){0,0,COH_PHYSICS_CELL_EMPTY};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&grid,1024*1024,NULL)==COH_OK);
    CHECK(coh_physics_snapshot_info(replacement,&info)==COH_OK&&info.empty_cells==1);
    coh_physics_snapshot_release(replacement);replacement=NULL;
    /* External mutable inputs can change or disappear after synchronous copy. */
    cells[6]=(CohPhysicsCoverageCell){9999,7,COH_PHYSICS_CELL_LOADED};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&grid,1024*1024,NULL)==COH_NOT_FOUND);
    cells[6]=(CohPhysicsCoverageCell){101,8,COH_PHYSICS_CELL_LOADED};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&grid,1024*1024,NULL)==COH_NOT_FOUND);
    cells[6]=(CohPhysicsCoverageCell){101,7,COH_PHYSICS_CELL_EMPTY};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&grid,1024*1024,NULL)==COH_INVALID);
    cells[6]=(CohPhysicsCoverageCell){0,0,3};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&grid,1024*1024,NULL)==COH_INVALID);
    CohPhysicsCoverageGrid bad=grid;bad.rows=UINT32_MAX;
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&bad,1024*1024,NULL)==COH_INVALID);
    bad=grid;bad.cell_size=NAN;
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,103,&bad,1024*1024,NULL)==COH_INVALID);
    prior=c;
    CHECK(coh_physics_snapshot_query(missing,(float[]){32,8,-32},(float[]){32,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_NOT_FOUND);
    CHECK(!memcmp(&prior,&c,sizeof c)&&st.nodes==0&&a.cells_checked==1&&a.missing_cells==1);
    /* Both sides of a seam must be present, including a zero-width query. */
    CHECK(coh_physics_snapshot_query(missing,(float[]){0,8,-32},(float[]){0,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_NOT_FOUND);
    CHECK(a.cells_checked==2&&a.missing_cells==1);
    CHECK(coh_physics_snapshot_query(s,(float[]){128,8,-32},(float[]){128,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_NOT_FOUND);
    CHECK(coh_physics_snapshot_query(s,(float[]){-128,8,-32},(float[]){-128,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_NOT_FOUND);
    CHECK(coh_physics_snapshot_query(s,(float[]){-32,129,-32},(float[]){-32,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_NOT_FOUND);
    CHECK(coh_physics_snapshot_query(s,(float[]){NAN,8,-32},(float[]){-32,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_INVALID);
    CHECK(coh_physics_snapshot_query(s,(float[]){-32,8,-32},(float[]){-32,-8,-32},0,
        COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_OK&&c.hit);
    CohPhysicsCoverageCell *large_cells=malloc(COH_PHYSICS_MAX_COVERAGE_CELLS*sizeof(*large_cells));
    CHECK(large_cells!=NULL);
    if(large_cells){
        for(unsigned i=0;i<COH_PHYSICS_MAX_COVERAGE_CELLS;i++)large_cells[i]=(CohPhysicsCoverageCell){100,7,COH_PHYSICS_CELL_LOADED};
        CohPhysicsCoverageGrid large_grid={-512,-512,4,-128,128,256,256,large_cells};
        CHECK(coh_physics_snapshot_create(&replacement,segments,4,105,&large_grid,2*1024*1024,NULL)==COH_OK);
        free(large_cells);
        track_allocs=1;
        CHECK(coh_physics_snapshot_query(replacement,(float[]){-511.75f,8,-511.75f},(float[]){511.75f,-8,511.75f},0,
            COH_PHYSICS_FROM_START,budget,&c,&st,&a)==COH_OK);
        CHECK(a.cells_checked==COH_PHYSICS_MAX_COVERAGE_CELLS&&a.missing_cells==0);
        track_allocs=0;coh_physics_snapshot_release(replacement);replacement=NULL;
    }
    CHECK(coh_walk_world_init(&direct,triangles,8,lo,hi));CHECK(coh_walk_init(&oracle,&direct,spawn,0));
    CHECK(coh_physics_snapshot_walker_prepare(&w,s,spawn,extents,spawn,0,budget,NULL,&a)==COH_OK);
    CHECK(coh_physics_snapshot_walker_prepare(&w,missing,(float[]){16,-1,-32},(float[]){128,32,32},spawn,0,budget,NULL,&a)==COH_NOT_FOUND);
    CHECK(w.generation==101&&!memcmp(&oracle,&w.state,sizeof oracle));
    for(unsigned i=0;i<160;i++){
        unsigned directions=i<100?COH_MOTION_RIGHT:COH_MOTION_LEFT;CohWalkState before=w.state;
        track_allocs=1;
        CohStatus status=coh_physics_walker_step(&w,101,directions,0);
        track_allocs=0;
        if(status==COH_NOT_FOUND){
            CHECK(!memcmp(&before,&w.state,sizeof before));
            CHECK(coh_physics_snapshot_walker_prepare(&w,s,w.state.position,extents,spawn,0,budget,NULL,&a)==COH_OK);
            CHECK(!memcmp(&before,&w.state,sizeof before));refreshes++;
            track_allocs=1;status=coh_physics_walker_step(&w,101,directions,0);track_allocs=0;
        }
        CHECK(status==COH_OK);CHECK(coh_walk_step(&oracle,&direct,directions,0));
        CHECK(!memcmp(&oracle,&w.state,sizeof oracle));walk_steps++;
    }
    CHECK(refreshes>0);CHECK(w.state.bounded_steps==0);
    CohWalkState before=w.state;void *prepared=w.world.prepared;
    CHECK(coh_physics_snapshot_walker_prepare(&w,missing,(float[]){32,0,-32},(float[]){128,32,32},spawn,0,budget,NULL,&a)==COH_NOT_FOUND);
    CHECK(prepared==w.world.prepared&&!memcmp(&before,&w.state,sizeof before));
    /* Fixed-storage query/admission paths and source WALK allocate nothing. */
    clock_t begin=clock();track_allocs=1;
    for(unsigned i=0;i<10000;i++){
        CohStatus status=coh_physics_snapshot_query(s,(float[]){-32,8,-32},(float[]){-32,-8,-32},0,
            COH_PHYSICS_FROM_START|COH_PHYSICS_BOTH_SIDES,budget,&c,&st,&a);
        CHECK(status==COH_OK&&c.hit);
    }
    track_allocs=0;double query_seconds=(double)(clock()-begin)/CLOCKS_PER_SEC;
    CHECK(alloc_calls==0);
    Reader readers[4];pthread_t threads[4];
    for(unsigned i=0;i<4;i++){CHECK(coh_physics_snapshot_retain(s)==COH_OK);readers[i]=(Reader){s,0,0};CHECK(!pthread_create(&threads[i],NULL,reader,&readers[i]));}
    coh_physics_snapshot_release(s);s=NULL;
    unsigned threaded=0;for(unsigned i=0;i<4;i++){CHECK(!pthread_join(threads[i],NULL));CHECK(!readers[i].failed);threaded+=readers[i].queries;}
    CHECK(threaded==8000);
    /* Walker's owned prepared copy remains usable after the snapshot retires. */
    CHECK(coh_physics_walker_step(&w,101,0,0)==COH_OK);
    cells[6]=(CohPhysicsCoverageCell){101,7,COH_PHYSICS_CELL_LOADED};
    CHECK(coh_physics_snapshot_create(&replacement,segments,4,104,&grid,1024*1024,NULL)==COH_OK);
    before=w.state;
    CHECK(coh_physics_snapshot_walker_prepare(&w,replacement,w.state.position,extents,spawn,0,budget,NULL,&a)==COH_OK);
    CHECK(w.generation==104&&!memcmp(&before,&w.state,sizeof before));
    CHECK(coh_physics_walker_step(&w,101,0,0)==COH_STATE);
    CHECK(!memcmp(&before,&w.state,sizeof before));
    coh_physics_snapshot_release(replacement);
    CHECK(coh_physics_walker_step(&w,104,0,0)==COH_OK);
    coh_physics_walker_destroy(&w);coh_physics_snapshot_release(missing);coh_walk_world_destroy(&direct);
    CHECK(live_allocations==0);
    printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u,\"source_walk_exact_steps\":%u,\"state_preserving_refreshes\":%u,\"connected_regions\":4,\"max_coverage_cells_tested\":65536,\"snapshot_owned_bytes\":%zu,\"query_and_walk_allocator_calls\":%llu,\"outstanding_tracked_allocations\":%llu,\"concurrent_source_queries\":%u,\"query_batch_cpu_seconds\":%.9f}\n",
        failed?"false":"true",checks,failed,walk_steps,refreshes,memory,(unsigned long long)alloc_calls,(unsigned long long)live_allocations,threaded,query_seconds);
    return failed?1:0;
}
