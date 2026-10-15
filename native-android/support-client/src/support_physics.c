#include "support_physics.h"
#include <math.h>
#include <stdlib.h>
#define SUPPORT_PHYSICS_MAGIC 0x53504832u
struct CohSupportPhysics {
    uint32_t magic;
    CohPhysicsScene *scene;
    CohPhysicsWalker walker;
    float extents[3];
    uint64_t refreshes;
};
static const CohPhysicsBudget query_budget={131071,COH_PHYSICS_MAX_TRIANGLES};
static int valid(const CohSupportPhysics *p){return p&&p->magic==SUPPORT_PHYSICS_MAGIC&&p->scene&&p->walker.ready==1;}
CohStatus coh_support_physics_create(CohSupportPhysics **out,const CohWalkTriangle *tri,
    uint32_t count,const float spawn[3],float yaw){
    CohSupportPhysics *p;CohPhysicsSegment segment[3];CohStatus status;unsigned i,j,k,parts;
    if(!out||*out||!tri||!count||!spawn||!isfinite(yaw))return COH_INVALID;
    if(count>COH_WALK_MAX_TRIANGLES)return COH_LIMIT;
    for(k=0;k<3;k++)if(!isfinite(spawn[k])||fabsf(spawn[k])>1000000.f)return COH_INVALID;
    p=calloc(1,sizeof(*p));if(!p)return COH_IO;p->magic=SUPPORT_PHYSICS_MAGIC;
    for(k=0;k<3;k++)p->extents[k]=32;
    for(i=0;i<count;i++)for(j=0;j<3;j++)for(k=0;k<3;k++){
        float v=tri[i].v[j][k];if(!isfinite(v)||fabsf(v)>1000000.f){status=COH_INVALID;goto fail;}
        p->extents[k]=fmaxf(p->extents[k],fabsf(v-spawn[k])+32);
        if(p->extents[k]>4096){status=COH_LIMIT;goto fail;}
    }
    parts=count<3?count:3;
    for(i=0;i<parts;i++){
        uint32_t first=(uint32_t)(((uint64_t)count*i)/parts),
            end=(uint32_t)(((uint64_t)count*(i+1))/parts);
        segment[i]=(CohPhysicsSegment){(uint64_t)i+1,1,tri+first,end-first};
    }
    status=coh_physics_scene_create(&p->scene,segment,parts,1,16*1024*1024,NULL);
    if(status!=COH_OK)goto fail;
    status=coh_physics_walker_prepare(&p->walker,p->scene,spawn,p->extents,spawn,yaw,query_budget,NULL);
    if(status!=COH_OK)goto fail;
    *out=p;return COH_OK;
fail:coh_support_physics_destroy(p);return status;
}
CohStatus coh_support_physics_step(CohSupportPhysics *p,uint32_t directions,float yaw){
    if(!valid(p))return COH_STATE;
    return coh_physics_walker_step(&p->walker,1,directions,yaw);
}
const CohWalkState *coh_support_physics_state(const CohSupportPhysics *p){
    return valid(p)?&p->walker.state:NULL;
}
CohStatus coh_support_physics_snapshot(const CohSupportPhysics *p,CohSupportPhysicsSnapshot *out){
    CohSupportPhysicsSnapshot result={0};float a[3],b[3];unsigned k;CohStatus status;
    if(!valid(p)||!out)return COH_INVALID;
    status=coh_physics_scene_info(p->scene,&result.scene);if(status!=COH_OK)return status;
    for(k=0;k<3;k++)a[k]=b[k]=p->walker.state.position[k];a[1]+=2.5f;b[1]-=.1f;
    status=coh_physics_query(p->scene,a,b,1,COH_PHYSICS_FROM_START,query_budget,
        &result.diagnostic_ground,&result.query);
    if(status!=COH_OK)return status;
    result.steps=p->walker.steps;result.refreshes=p->refreshes;
    result.refresh_requests=p->walker.refresh_requests;
    result.neighborhood_triangles=p->walker.world.triangle_count;
    *out=result;return COH_OK;
}
CohStatus coh_support_physics_refresh(CohSupportPhysics *p){
    CohStatus status;const CohWalkState *s;
    if(!valid(p))return COH_STATE;s=&p->walker.state;
    status=coh_physics_walker_prepare(&p->walker,p->scene,s->position,p->extents,
        s->position,s->controls.control_yaw,query_budget,NULL);
    if(status==COH_OK&&p->refreshes<UINT64_MAX)p->refreshes++;
    return status;
}
void coh_support_physics_clear(CohSupportPhysics *p){if(valid(p))coh_physics_walker_clear(&p->walker);}
void coh_support_physics_destroy(CohSupportPhysics *p){
    if(!p||p->magic!=SUPPORT_PHYSICS_MAGIC)return;p->magic=0;
    coh_physics_walker_destroy(&p->walker);coh_physics_scene_destroy(p->scene);free(p);
}
