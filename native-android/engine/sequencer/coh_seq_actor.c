#include "coh_seq_actor.h"
#include <string.h>

static int contains_bone(const CohAnimationRig *rig,uint32_t bone) {
    uint32_t i;
    if(bone==COH_SEQ_SOCKET_ROOT)return 1;
    if(!rig || !rig->node_count || rig->node_count>COH_ANIMATION_BONES || bone>=COH_ANIMATION_BONES)return 0;
    for(i=0;i<rig->node_count;++i)if(rig->order[i]==bone)return 1;
    return 0;
}
static CohStatus resources_valid(const CohSeqActorResources *r) {
    size_t i,j; CohStatus status;
    if(!r || !r->graph || !r->clips || !r->poses || !r->move_count ||
        !r->appearance_generation || !r->rig_generation || !r->resource_generation ||
        (r->marker_count && !r->markers) || (r->route_count && !r->routes))return COH_INVALID;
    if(r->marker_count>COH_SEQ_PLAYBACK_MARKERS || r->route_count>COH_SEQ_ACTOR_ROUTES)return COH_LIMIT;
    status=coh_seq_validate(r->graph,r->clips,r->move_count);if(status!=COH_OK)return status;
    for(i=0;i<r->move_count;++i) {
        if(r->poses[i].clip_id!=r->clips[i].clip_id || r->poses[i].rig_id!=r->rig_id)return COH_INVALID;
        if(r->clips[i].ready && (!r->poses[i].rig ||
            r->clips[i].first_frame<r->poses[i].rig->first_frame ||
            r->clips[i].last_frame>r->poses[i].rig->last_frame))return COH_INVALID;
    }
    for(i=0;i<r->route_count;++i) {
        const CohSeqCueRoute *route=&r->routes[i];
        if(route->kind<COH_SEQ_CUE_AUDIO || route->kind>COH_SEQ_CUE_ATTACHMENT ||
            (route->socket_bone!=COH_SEQ_SOCKET_ROOT && route->socket_bone>=COH_ANIMATION_BONES))return COH_INVALID;
        for(j=0;j<i;++j)if(route->marker_kind==r->routes[j].marker_kind &&
            route->marker_token==r->routes[j].marker_token)return COH_INVALID;
        /* A route may only refer to a reachable socket in every loaded move
         * that can emit it. Missing clips are admitted later by rebind. */
        for(j=0;j<r->marker_count;++j) {
            const CohSeqMarker *marker=&r->markers[j];
            if(marker->move>=r->move_count)return COH_INVALID;
            if(marker->kind==route->marker_kind && marker->token==route->marker_token &&
                r->poses[marker->move].rig && !contains_bone(r->poses[marker->move].rig,route->socket_bone))return COH_UNSUPPORTED;
        }
    }
    return COH_OK;
}
CohStatus coh_seq_actor_init(CohSeqActor *actor,const CohSeqActorResources *r,
    uint32_t initial,uint32_t seed) {
    CohSeqActor next;CohStatus status;
    if(!actor)return COH_INVALID;
    status=resources_valid(r);if(status!=COH_OK)return status;
    memset(&next,0,sizeof next);next.resources=*r;
    status=coh_seq_init(&next.sequencer,r->graph,r->clips,r->move_count,r->actor_id,r->rig_id,initial,seed);
    if(status!=COH_OK)return status;
    status=coh_seq_playback_init(&next.playback,r->actor_id,r->rig_id,r->poses,r->move_count,r->markers,r->marker_count);
    if(status!=COH_OK)return status;
    next.selection.move=COH_SEQ_NONE;*actor=next;return COH_OK;
}
static void route_cue(CohSeqActorCue *out,const CohSeqPlaybackEvent *event,
    const CohSeqActorResources *r,const CohAnimationPose *pose) {
    static const float identity[12]={1,0,0,0,0,1,0,0,0,0,1,0};size_t i;
    memset(out,0,sizeof *out);out->animation=*event;
    out->appearance_generation=r->appearance_generation;out->rig_generation=r->rig_generation;
    out->resource_generation=r->resource_generation;out->socket_bone=COH_SEQ_SOCKET_ROOT;
    memcpy(out->socket_rows,identity,sizeof identity);
    if(event->type!=COH_SEQ_EVENT_MARKER)return;
    for(i=0;i<r->route_count;++i) {
        const CohSeqCueRoute *route=&r->routes[i];
        if(route->marker_kind==event->kind && route->marker_token==event->token) {
            out->kind=route->kind;out->resource_id=route->resource_id;out->socket_bone=route->socket_bone;
            if(route->socket_bone!=COH_SEQ_SOCKET_ROOT)
                memcpy(out->socket_rows,pose->world_rows[route->socket_bone],sizeof out->socket_rows);
            return;
        }
    }
}
CohStatus coh_seq_actor_step(CohSeqActor *actor,const CohSeqInput *input,uint64_t tick,
    CohAnimationPose *out,CohSeqActorCue *cues,size_t capacity,size_t *count) {
    CohSeqActor next;CohAnimationPose pose;
    CohSeqPlaybackEvent events[COH_SEQ_PLAYBACK_EVENTS];size_t n=0,i;CohStatus status;
    if(!actor || !input || !out || !count || (capacity && !cues))return COH_INVALID;
    if(actor->playback.initialized && tick<=actor->playback.tick)return COH_INVALID;
    /* coh_seq_step performs the single cancellation poll before mutation. The
     * downstream sample is synchronous bounded work and must not poll again. */
    next=*actor;status=coh_seq_step(&next.sequencer,input,&next.selection);
    if(status!=COH_OK)return status;
    status=coh_seq_playback_sample(&next.playback,&next.selection,
        next.sequencer.diagnostics.transitions,input->timestep_frames,tick,
        (CohCancel){0},&pose,events,capacity<COH_SEQ_PLAYBACK_EVENTS?capacity:COH_SEQ_PLAYBACK_EVENTS,&n);
    if(status!=COH_OK)return status;
    /* All routes and sockets were admitted; staging has no fallible operation. */
    for(i=0;i<n;++i)route_cue(&cues[i],&events[i],&next.resources,&pose);
    ++next.successful_ticks;next.cue_count+=n;
    *out=pose;*count=n;*actor=next;return COH_OK;
}
CohStatus coh_seq_actor_rebind(CohSeqActor *actor,const CohSeqActorResources *r) {
    CohSeqActor next;CohStatus status;
    if(!actor || !r || r->actor_id!=actor->resources.actor_id || r->rig_id!=actor->resources.rig_id ||
        r->appearance_generation!=actor->resources.appearance_generation ||
        r->rig_generation!=actor->resources.rig_generation || r->graph!=actor->resources.graph ||
        r->move_count!=actor->resources.move_count || r->resource_generation<=actor->resources.resource_generation ||
        r->markers!=actor->resources.markers || r->marker_count!=actor->resources.marker_count ||
        r->routes!=actor->resources.routes || r->route_count!=actor->resources.route_count)return COH_INVALID;
    status=resources_valid(r);if(status!=COH_OK)return status;
    {const CohSeqClip *old=&actor->resources.clips[actor->sequencer.move];
     const CohSeqClip *current=&r->clips[actor->sequencer.move];
     if(!current->ready || current->clip_id!=old->clip_id ||
        current->first_frame!=old->first_frame || current->last_frame!=old->last_frame ||
        current->type_scale!=old->type_scale || !current->asset.path ||
        strcmp(current->asset.path,old->asset.path))return COH_STATE;}
    next=*actor;status=coh_seq_rebind_clips(&next.sequencer,r->clips,r->move_count);
    if(status!=COH_OK)return status;
    status=coh_seq_playback_rebind(&next.playback,r->poses,r->move_count);
    if(status!=COH_OK)return status;
    next.resources=*r;*actor=next;return COH_OK;
}
const CohAnimationRig *coh_seq_actor_active_rig(const CohSeqActor *actor) {
    if(!actor || !actor->playback.initialized || actor->selection.move>=actor->resources.move_count)return NULL;
    return actor->resources.poses[actor->selection.move].rig;
}
CohStatus coh_seq_actor_snapshot(const CohSeqActor *actor,CohSeqActorSnapshot *out) {
    CohSeqActorSnapshot next;
    if(!actor || !out)return COH_INVALID;
    memset(&next,0,sizeof next);next.actor_id=actor->resources.actor_id;next.rig_id=actor->resources.rig_id;
    next.move=actor->selection.move;next.clip_id=actor->selection.clip_id;next.appearance_generation=actor->resources.appearance_generation;
    next.rig_generation=actor->resources.rig_generation;next.resource_generation=actor->resources.resource_generation;
    next.tick=actor->playback.tick;next.successful_ticks=actor->successful_ticks;
    next.transitions=actor->playback.diagnostics.transitions;next.blended_bones=actor->playback.diagnostics.blended_bones;
    next.cue_count=actor->cue_count;next.frame=actor->playback.frame;next.retained_bytes=sizeof *actor;
    next.borrowed_active_rig_bytes=actor->playback.diagnostics.borrowed_rig_bytes;*out=next;return COH_OK;
}
