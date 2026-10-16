#include "../coh_physics_neighborhood.h"
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static unsigned checks,failed,source_steps,commits,rejected;
static float minimum_x=1e9f,maximum_x=-1e9f,minimum_y=1e9f,maximum_y=-1e9f;
static atomic_uint_fast64_t live_allocations,hot_calls;
static _Thread_local int hot;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){void *p;if(hot)atomic_fetch_add(&hot_calls,1);p=__real_malloc(n);if(p)atomic_fetch_add(&live_allocations,1);return p;}
void *__wrap_calloc(size_t n,size_t m){void *p;if(hot)atomic_fetch_add(&hot_calls,1);p=__real_calloc(n,m);if(p)atomic_fetch_add(&live_allocations,1);return p;}
void *__wrap_realloc(void *p,size_t n){void *q;if(hot)atomic_fetch_add(&hot_calls,1);q=__real_realloc(p,n);if(!p&&q)atomic_fetch_add(&live_allocations,1);else if(p&&!n)atomic_fetch_sub(&live_allocations,1);return q;}
void __wrap_free(void *p){if(hot)atomic_fetch_add(&hot_calls,1);if(p)atomic_fetch_sub(&live_allocations,1);__real_free(p);}
#define CHECK(c) do{checks++;if(!(c)){failed++;fprintf(stderr,"neighborhood line %d: %s\n",__LINE__,#c);}}while(0)
static const CohPhysicsBudget budget={1000000,COH_PHYSICS_MAX_TRIANGLES};
static int cancel_now(void *p){(void)p;return 1;}
static int cancel_later(void *p){unsigned *calls=p;return --*calls==0;}
static void terrain(CohWalkTriangle *t,float x,float z){
    float h0=x*.02f+(x>=0?.5f:0),h1=(x+256)*.02f+(x>=0?.5f:0);
    t[0]=(CohWalkTriangle){{{x,h0,z},{x,h0,z+256},{x+256,h1,z}},COH_WALK_NORMALTRI};
    t[1]=(CohWalkTriangle){{{x+256,h1,z},{x,h0,z+256},{x+256,h1,z+256}},COH_WALK_NORMALTRI};
}
static void compare(const CohWalkState *a,const CohWalkState *b){
    CHECK(!memcmp(&a->controls,&b->controls,sizeof a->controls));
    CHECK(!memcmp(&a->position,&b->position,sizeof a->position));
    CHECK(!memcmp(&a->physics,&b->physics,sizeof a->physics));
    CHECK(a->ticks==b->ticks&&a->grounded==b->grounded&&a->blocked==b->blocked&&a->sliding==b->sliding);
    CHECK(a->bounded_steps==0&&b->bounded_steps==0);
}
typedef struct {
    CohPhysicsNeighborhoodRequest request;CohPhysicsSnapshot *snapshot;
    CohPhysicsPreparedNeighborhood *prepared;float center[3],extents[3];
    CohStatus status;CohPhysicsAdmission admission;
} Load;
static void *loader(void *v){Load *j=v;
    j->status=coh_physics_neighborhood_build(&j->prepared,&j->request,j->snapshot,
        j->center,j->extents,budget,NULL,&j->admission);
    coh_physics_snapshot_release(j->snapshot);return NULL;
}
static void step(CohPhysicsWalker *w,CohWalkState *oracle,const CohWalkWorld *world,unsigned direction){
    hot=1;CohStatus status=coh_physics_walker_step(w,w->generation,direction,0);hot=0;
    CHECK(status==COH_OK);CHECK(coh_walk_step(oracle,world,direction,0));compare(&w->state,oracle);source_steps++;
    minimum_x=fminf(minimum_x,w->state.position[0]);maximum_x=fmaxf(maximum_x,w->state.position[0]);
    minimum_y=fminf(minimum_y,w->state.position[1]);maximum_y=fmaxf(maximum_y,w->state.position[1]);
}
int main(void){
    CohWalkTriangle triangles[32];CohPhysicsSegment segments[16];CohPhysicsCoverageCell cells[64];
    CohPhysicsCoverageGrid grid={-512,-512,128,-256,256,8,8,cells};
    CohPhysicsSnapshot *s=NULL,*changed=NULL,*missing=NULL;CohPhysicsSnapshotInfo si;
    CohPhysicsWalker w={0};CohWalkWorld direct={0};CohWalkState oracle;
    CohPhysicsNeighborhoodRequest request={0},saved;CohPhysicsPreparedNeighborhood *p=NULL;
    CohPhysicsAdmission admission;CohPhysicsNeighborhoodInfo info;
    const float spawn[3]={-200,-4.f,-32},extents[3]={96,64,96};
    for(unsigned z=0;z<4;z++)for(unsigned x=0;x<4;x++){
        unsigned i=z*4+x;terrain(triangles+i*2,-512+256*(float)x,-512+256*(float)z);
        segments[i]=(CohPhysicsSegment){i+1,1,triangles+i*2,2};
    }
    for(unsigned z=0;z<8;z++)for(unsigned x=0;x<8;x++)cells[z*8+x]=(CohPhysicsCoverageCell){1+(z/2)*4+x/2,1,COH_PHYSICS_CELL_LOADED};
    CHECK(coh_physics_snapshot_create(&s,segments,16,101,&grid,4*1024*1024,NULL)==COH_OK);
    CHECK(coh_physics_snapshot_create(&changed,segments,16,102,&grid,4*1024*1024,NULL)==COH_OK);
    cells[3*8+2]=(CohPhysicsCoverageCell){0,0,COH_PHYSICS_CELL_MISSING};
    CHECK(coh_physics_snapshot_create(&missing,segments,16,103,&grid,4*1024*1024,NULL)==COH_OK);
    CHECK(coh_physics_snapshot_info(s,&si)==COH_OK);
    CHECK(coh_walk_world_init(&direct,triangles,32,(float[]){-512,-11,-512},(float[]){512,11,512}));
    CHECK(coh_walk_init(&oracle,&direct,spawn,0));
    CHECK(coh_physics_snapshot_walker_prepare(&w,s,spawn,extents,spawn,0,budget,NULL,&admission)==COH_OK);
    CHECK(coh_physics_neighborhood_capture(&w,0,&request)==COH_INVALID);
    CHECK(coh_physics_neighborhood_capture(&(CohPhysicsWalker){0},77,&request)==COH_STATE);
    hot=1;CHECK(coh_physics_neighborhood_capture(&w,77,&request)==COH_OK);hot=0;saved=request;
    CHECK(coh_physics_neighborhood_build(&p,&request,missing,spawn,extents,budget,NULL,&admission)==COH_NOT_FOUND&&!p);
    CHECK(admission.missing_cells>0);CHECK(!memcmp(&saved,&request,sizeof request));
    CohCancel cancel={cancel_now,NULL};
    CHECK(coh_physics_neighborhood_build(&p,&request,s,spawn,extents,budget,&cancel,&admission)==COH_CANCELLED&&!p);
    for(unsigned after=2;after<=12;after++){
        unsigned remaining=after;CohCancel delayed={cancel_later,&remaining};
        uint64_t allocations=atomic_load(&live_allocations);
        CohStatus status=coh_physics_neighborhood_build(&p,&request,s,spawn,extents,budget,&delayed,&admission);
        CHECK(status==COH_CANCELLED||status==COH_OK);
        if(status==COH_OK){coh_physics_neighborhood_destroy(p);p=NULL;}
        CHECK(!p&&atomic_load(&live_allocations)==allocations);
    }
    CHECK(coh_physics_neighborhood_build(&p,&request,s,spawn,(float[]){NAN,64,96},budget,NULL,&admission)==COH_INVALID&&!p);
    CHECK(coh_physics_neighborhood_build(&p,&request,s,spawn,extents,(CohPhysicsBudget){1,1},NULL,&admission)==COH_LIMIT&&!p);
    /* Loader receives only a state copy and owned snapshot reference; simulation
     * continues stepping its old cache. Publication is the pthread join here. */
    clock_t begin=clock();
    for(unsigned batch=0;batch<80;batch++){
        Load job={0};pthread_t thread;unsigned direction=batch<40?COH_MOTION_RIGHT:COH_MOTION_LEFT;
        hot=1;CHECK(coh_physics_neighborhood_capture(&w,77,&job.request)==COH_OK);hot=0;
        job.snapshot=s;memcpy(job.center,w.state.position,sizeof job.center);memcpy(job.extents,extents,sizeof extents);
        CHECK(coh_physics_snapshot_retain(s)==COH_OK);CHECK(!pthread_create(&thread,NULL,loader,&job));
        for(unsigned tick=0;tick<6;tick++)step(&w,&oracle,&direct,direction);
        CHECK(!pthread_join(thread,NULL));CHECK(job.status==COH_OK&&job.prepared);
        CohPhysicsWalker before=w;
        hot=1;CHECK(coh_physics_neighborhood_commit(&w,78,job.prepared)==COH_STATE);
        CHECK(!memcmp(&before,&w,sizeof before));
        CHECK(coh_physics_neighborhood_commit(&w,77,job.prepared)==COH_OK);hot=0;
        CHECK(!memcmp(&before.state,&w.state,sizeof w.state)&&before.steps==w.steps);commits++;
        CHECK(coh_physics_neighborhood_info(job.prepared,&info)==COH_OK&&info.committed&&info.target_generation==101);
        before=w;hot=1;CHECK(coh_physics_neighborhood_commit(&w,77,job.prepared)==COH_STATE);hot=0;
        CHECK(!memcmp(&before,&w,sizeof before));coh_physics_neighborhood_destroy(job.prepared);
    }
    double seconds=(double)(clock()-begin)/CLOCKS_PER_SEC;
    /* Changed geometry is admitted only for the original pose; loader cannot
     * silently transplant a moving actor into a scene checked at an old pose. */
    CHECK(coh_physics_neighborhood_capture(&w,77,&request)==COH_OK);
    CHECK(coh_physics_neighborhood_build(&p,&request,changed,w.state.position,extents,budget,NULL,&admission)==COH_OK);
    step(&w,&oracle,&direct,COH_MOTION_RIGHT);CohPhysicsWalker before=w;
    hot=1;CHECK(coh_physics_neighborhood_commit(&w,77,p)==COH_STATE);hot=0;rejected++;
    CHECK(!memcmp(&before,&w,sizeof before));coh_physics_neighborhood_destroy(p);p=NULL;
    CHECK(coh_physics_neighborhood_capture(&w,77,&request)==COH_OK);
    CHECK(coh_physics_neighborhood_build(&p,&request,changed,w.state.position,extents,budget,NULL,&admission)==COH_OK);
    before=w;hot=1;CHECK(coh_physics_neighborhood_commit(&w,77,p)==COH_OK);hot=0;commits++;
    CHECK(w.generation==102&&!memcmp(&before.state,&w.state,sizeof w.state));
    coh_physics_neighborhood_destroy(p);p=NULL;
    /* Same-generation stale prefetch is safe only within its interior margin. */
    CHECK(coh_physics_neighborhood_capture(&w,77,&request)==COH_OK);
    CHECK(coh_physics_neighborhood_build(&p,&request,changed,w.state.position,(float[]){32,64,32},budget,NULL,&admission)==COH_OK);
    for(unsigned tick=0;tick<50;tick++)step(&w,&oracle,&direct,COH_MOTION_RIGHT);
    before=w;hot=1;CHECK(coh_physics_neighborhood_commit(&w,77,p)==COH_NOT_FOUND);hot=0;rejected++;
    CHECK(!memcmp(&before,&w,sizeof before));coh_physics_neighborhood_destroy(p);p=NULL;
    coh_physics_snapshot_release(s);coh_physics_snapshot_release(changed);coh_physics_snapshot_release(missing);
    /* Prepared active cache remains valid after all snapshots have retired. */
    step(&w,&oracle,&direct,0);coh_physics_walker_destroy(&w);coh_walk_world_destroy(&direct);
    CHECK(minimum_x<0&&maximum_x>0&&maximum_y-minimum_y>1);
    CHECK(atomic_load(&hot_calls)==0);CHECK(atomic_load(&live_allocations)==0);
    printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u,\"exact_source_state_steps\":%u,\"loader_thread_builds\":80,\"commits\":%u,\"stale_preparation_rejections\":%u,\"hot_allocator_calls\":%llu,\"outstanding_tracked_allocations\":%llu,\"snapshot_owned_bytes\":%zu,\"request_bytes\":%zu,\"traversed_x_range\":[%.6f,%.6f],\"traversed_y_range\":[%.6f,%.6f],\"threaded_workload_cpu_seconds\":%.9f}\n",failed?"false":"true",checks,failed,source_steps,commits,rejected,(unsigned long long)atomic_load(&hot_calls),(unsigned long long)atomic_load(&live_allocations),si.owned_bytes,sizeof request,minimum_x,maximum_x,minimum_y,maximum_y,seconds);
    return failed?1:0;
}
