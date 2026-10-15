#include "../../../support-client/src/support_physics.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,failed;static int hot;static uint64_t calls,live;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){void *p=__real_malloc(n);if(hot)calls++;if(p)live++;return p;}
void *__wrap_calloc(size_t n,size_t m){void *p=__real_calloc(n,m);if(hot)calls++;if(p)live++;return p;}
void *__wrap_realloc(void *p,size_t n){void *q=__real_realloc(p,n);if(hot)calls++;if(!p&&q)live++;else if(p&&!n)live--;return q;}
void __wrap_free(void *p){if(hot)calls++;if(p)live--;__real_free(p);}
#define CHECK(x) do{checks++;if(!(x)){failed++;fprintf(stderr,"adapter check line %d: %s\n",__LINE__,#x);}}while(0)
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const unsigned char *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
int main(int argc,char **argv){
    CHECK(argc==2);if(argc!=2)return 2;FILE *f=fopen(argv[1],"rb");CHECK(f!=NULL);if(!f)return 2;
    if(fseek(f,0,SEEK_END)){fclose(f);return 2;}long n=ftell(f);
    if(n<128||n>16*1024*1024||fseek(f,0,SEEK_SET)){fclose(f);return 2;}
    unsigned char *bytes=malloc((size_t)n);if(!bytes){fclose(f);return 2;}
    if(fread(bytes,1,(size_t)n,f)!=(size_t)n){free(bytes);fclose(f);return 2;}fclose(f);
    if(memcmp(bytes,"COHWALK1",8)||u32(bytes+8)!=1){free(bytes);return 2;}
    uint32_t count=u32(bytes+24),off=u32(bytes+52);
    if(!count||count>8192||off>(uint32_t)n||count>((uint32_t)n-off)/40){free(bytes);return 2;}
    CohWalkTriangle *tri=malloc(count*sizeof(*tri));if(!tri){free(bytes);return 2;}
    for(unsigned i=0;i<count;i++){
        for(unsigned v=0;v<3;v++)for(unsigned k=0;k<3;k++)tri[i].v[v][k]=f32(bytes+off+i*40+(v*3+k)*4);
        tri[i].flags=u32(bytes+off+i*40+36);
    }
    float lo[3],hi[3],spawn[3],yaw=f32(bytes+104);
    for(unsigned k=0;k<3;k++){lo[k]=f32(bytes+68+k*4);hi[k]=f32(bytes+80+k*4);spawn[k]=f32(bytes+92+k*4);}free(bytes);
    CohSupportPhysics *p=NULL,*bad=NULL;CohSupportPhysicsSnapshot snapshot={0};CohWalkWorld direct={0};CohWalkState state;
    CHECK(coh_support_physics_create(&bad,tri,count,(float[]){NAN,0,0},yaw)==COH_INVALID&&bad==NULL);
    CHECK(coh_support_physics_create(&bad,tri,8193,spawn,yaw)==COH_LIMIT&&bad==NULL);
    CHECK(coh_support_physics_create(&bad,tri,0,spawn,yaw)==COH_INVALID&&bad==NULL);
    CHECK(coh_support_physics_step(NULL,0,yaw)==COH_STATE);CHECK(coh_support_physics_state(NULL)==NULL);
    CHECK(coh_support_physics_snapshot(NULL,&snapshot)==COH_INVALID);CHECK(coh_support_physics_refresh(NULL)==COH_STATE);
    CHECK(coh_walk_world_init(&direct,tri,count,lo,hi));CHECK(coh_walk_init(&state,&direct,spawn,yaw));
    CHECK(coh_support_physics_create(&p,tri,count,spawn,yaw)==COH_OK);free(tri);
    if(!p){coh_walk_world_destroy(&direct);return 1;}
    CHECK(!memcmp(coh_support_physics_state(p),&state,sizeof state));
    CHECK(coh_support_physics_snapshot(p,&snapshot)==COH_OK);
    CHECK(snapshot.scene.segment_count==3&&snapshot.scene.triangle_count==count&&snapshot.neighborhood_triangles==count);
    CHECK(snapshot.diagnostic_ground.hit&&snapshot.query.nodes>0&&snapshot.query.triangles>0);
    hot=1;
    for(unsigned tick=0;tick<250;tick++){
        unsigned directions=tick<70?COH_MOTION_FORWARD:tick<108?COH_MOTION_FORWARD|COH_MOTION_RIGHT:tick<128?COH_MOTION_BACKWARD:0;
        CHECK(coh_walk_step(&state,&direct,directions,yaw));CHECK(coh_support_physics_step(p,directions,yaw)==COH_OK);
        CHECK(!memcmp(coh_support_physics_state(p),&state,sizeof state));
        if(tick==128){coh_walk_clear(&state);coh_support_physics_clear(p);}
        CHECK(coh_support_physics_snapshot(p,&snapshot)==COH_OK);
    }
    hot=0;
    CohWalkState prior=*coh_support_physics_state(p);
    CHECK(coh_support_physics_refresh(p)==COH_OK);CHECK(!memcmp(coh_support_physics_state(p),&prior,sizeof prior));
    CHECK(coh_support_physics_snapshot(p,&snapshot)==COH_OK);
    CHECK(snapshot.steps==250&&snapshot.refreshes==1&&snapshot.refresh_requests==0);
    CHECK(coh_support_physics_step(p,16,yaw)==COH_INVALID);
    CHECK(!memcmp(coh_support_physics_state(p),&prior,sizeof prior));
    CHECK(coh_support_physics_step(p,0,NAN)==COH_INVALID);
    CHECK(!memcmp(coh_support_physics_state(p),&prior,sizeof prior));
    coh_support_physics_destroy(p);coh_walk_world_destroy(&direct);CHECK(calls==0);CHECK(live==0);
    printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u,\"authentic_triangles\":%u,\"deterministic_segments\":3,"
        "\"exact_walk_ticks\":250,\"hot_allocator_calls\":%llu,\"outstanding_tracked_allocations\":%llu,"
        "\"source_query_nodes\":%u,\"source_query_triangles\":%u}\n",failed?"false":"true",checks,failed,count,
        (unsigned long long)calls,(unsigned long long)live,snapshot.query.nodes,snapshot.query.triangles);
    return failed?1:0;
}
