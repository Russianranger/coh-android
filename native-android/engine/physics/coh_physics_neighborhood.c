#include "coh_physics_neighborhood.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define NEIGHBORHOOD_MAGIC 0x504e4231u
struct CohPhysicsPreparedNeighborhood {
    uint32_t magic,committed;
    CohPhysicsNeighborhoodRequest request;
    CohPhysicsWalker candidate;
    CohPhysicsNeighborhoodInfo info;
};
CohStatus coh_physics_neighborhood_capture(const CohPhysicsWalker *w,
    uint64_t owner,CohPhysicsNeighborhoodRequest *out){
    CohPhysicsNeighborhoodRequest next={0};
    if(!w||!out||!owner)return COH_INVALID;
    if(w->ready!=1||!w->generation||!w->world.prepared)return COH_STATE;
    next.owner_generation=owner;next.scene_generation=w->generation;next.ready=1;
    next.state=w->state;next.steps=w->steps;*out=next;return COH_OK;
}
CohStatus coh_physics_neighborhood_build(CohPhysicsPreparedNeighborhood **out,
    const CohPhysicsNeighborhoodRequest *r,const CohPhysicsSnapshot *snapshot,
    const float center[3],const float extents[3],CohPhysicsBudget budget,
    const CohCancel *cancel,CohPhysicsAdmission *admission){
    CohPhysicsPreparedNeighborhood *p;CohStatus status;
    if(admission)*admission=(CohPhysicsAdmission){0};
    if(!out||*out||!r||!r->owner_generation||!r->scene_generation||r->ready!=1)return COH_INVALID;
    if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
    p=calloc(1,sizeof *p);if(!p)return COH_IO;
    p->request=*r;p->candidate.ready=1;p->candidate.generation=r->scene_generation;
    p->candidate.state=r->state;p->candidate.steps=r->steps;
    status=coh_physics_snapshot_walker_prepare(&p->candidate,snapshot,center,extents,
        r->state.position,r->state.controls.control_yaw,budget,cancel,admission);
    if(status!=COH_OK){coh_physics_walker_destroy(&p->candidate);free(p);return status;}
    p->magic=NEIGHBORHOOD_MAGIC;p->info.owner_generation=r->owner_generation;
    p->info.source_generation=r->scene_generation;p->info.target_generation=p->candidate.generation;
    p->info.owned_triangle_bytes=p->candidate.owned_triangle_bytes;*out=p;return COH_OK;
}
CohStatus coh_physics_neighborhood_commit(CohPhysicsWalker *w,uint64_t owner,
    CohPhysicsPreparedNeighborhood *p){
    CohPhysicsWalker old;unsigned k;
    if(!w||!owner||!p||p->magic!=NEIGHBORHOOD_MAGIC)return COH_INVALID;
    if(p->committed||w->ready!=1||!w->world.prepared||owner!=p->request.owner_generation||
       w->generation!=p->request.scene_generation||w->steps<p->request.steps)return COH_STATE;
    if(p->candidate.generation!=p->request.scene_generation&&
       (w->steps!=p->request.steps||memcmp(&w->state,&p->request.state,sizeof w->state)))return COH_STATE;
    for(k=0;k<3;k++)if(!isfinite(w->state.position[k])||
        w->state.position[k]<p->candidate.query_min[k]+16||
        w->state.position[k]>p->candidate.query_max[k]-16)return COH_NOT_FOUND;
    old=*w;*w=p->candidate;
    w->state=old.state;w->steps=old.steps;w->refresh_requests=old.refresh_requests;
    p->candidate=old;p->committed=1;p->info.committed=1;return COH_OK;
}
CohStatus coh_physics_neighborhood_info(const CohPhysicsPreparedNeighborhood *p,
    CohPhysicsNeighborhoodInfo *out){
    if(!p||p->magic!=NEIGHBORHOOD_MAGIC||!out)return COH_INVALID;
    *out=p->info;return COH_OK;
}
void coh_physics_neighborhood_destroy(CohPhysicsPreparedNeighborhood *p){
    if(!p||p->magic!=NEIGHBORHOOD_MAGIC)return;
    p->magic=0;coh_physics_walker_destroy(&p->candidate);free(p);
}
