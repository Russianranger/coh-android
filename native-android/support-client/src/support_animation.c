#include "support_animation.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
struct CohSupportAnimation {
    CohAnimationRig rigs[COH_SUPPORT_ANIMATION_CLIPS];
    CohSeqPoseBinding bindings[COH_SUPPORT_ANIMATION_CLIPS];
    CohSeqPlayback playback;
    uint32_t actor_id, kind, pending;
    uint64_t generation, triggers, cycles, trigger_tick;
    size_t borrowed_bytes;
};
CohStatus coh_support_animation_create(const CohBytes clips[COH_SUPPORT_ANIMATION_CLIPS],
    uint32_t actor_id,CohSupportAnimation **out) {
    CohSupportAnimation *state;CohStatus status;
    if(!clips || !out)return COH_INVALID;
    for(unsigned i=0;i<COH_SUPPORT_ANIMATION_CLIPS;++i)
        if(!clips[i].data || clips[i].size<128 || clips[i].size>8u*1024u*1024u)return COH_INVALID;
    state=calloc(1,sizeof *state);if(!state)return COH_LIMIT;
    for(unsigned i=0;i<COH_SUPPORT_ANIMATION_CLIPS;++i) {
        if(coh_animation_parse(clips[i].data,clips[i].size,&state->rigs[i])){free(state);return COH_INVALID;}
        if(i && (state->rigs[i].base.byte_count!=state->rigs[0].base.byte_count ||
            memcmp(state->rigs[i].base.bytes,state->rigs[0].base.bytes,state->rigs[0].base.byte_count))) {
            free(state);return COH_UNSUPPORTED;
        }
        state->bindings[i]=(CohSeqPoseBinding){i,4,&state->rigs[i]};
        state->borrowed_bytes+=clips[i].size;
    }
    status=coh_seq_playback_init(&state->playback,actor_id,4,state->bindings,
        COH_SUPPORT_ANIMATION_CLIPS,NULL,0);
    if(status!=COH_OK){free(state);return status;}
    state->actor_id=actor_id;state->pending=1;*out=state;return COH_OK;
}
void coh_support_animation_destroy(CohSupportAnimation *state){free(state);}
CohStatus coh_support_animation_trigger(CohSupportAnimation *state,uint32_t kind,uint64_t tick) {
    if(!state || kind>=COH_SUPPORT_ANIMATION_CLIPS ||
        (state->playback.initialized && tick<state->playback.tick) ||
        (state->pending && tick<state->trigger_tick) || state->generation==UINT64_MAX)return COH_INVALID;
    state->kind=kind;state->pending=1;state->trigger_tick=tick;++state->generation;++state->triggers;
    return COH_OK;
}
CohStatus coh_support_animation_sample(CohSupportAnimation *state,float dt,uint64_t tick,CohAnimationPose *out) {
    CohSeqSelection selection={0};const CohAnimationRig *rig;CohSeqPlaybackEvent event[1];size_t count=0;
    CohStatus status;float frame;unsigned cycle=0;
    if(!state || !out || !isfinite(dt) || dt<0 || dt>3 ||
        (state->pending && tick<state->trigger_tick))return COH_INVALID;
    rig=&state->rigs[state->kind];frame=state->pending?rig->first_frame:state->playback.frame+dt;
    if(frame>rig->last_frame) {
        frame-=rig->last_frame-rig->first_frame;
        if(frame>rig->last_frame)frame=rig->first_frame;
        cycle=COH_SEQ_CAUSE_CYCLE;
    }
    selection.actor_id=state->actor_id;selection.rig_id=4;selection.move=state->kind;
    selection.clip_id=state->kind;selection.frame=frame;selection.cause=cycle;
    selection.flags=COH_SEQ_CYCLE;selection.interpolate_frames=5;
    status=coh_seq_playback_sample(&state->playback,&selection,state->generation,dt,tick,
        (CohCancel){0},out,event,1,&count);
    if(status!=COH_OK)return status;
    state->pending=0;state->cycles+=(uint64_t)(cycle!=0);return COH_OK;
}
const CohAnimationRig *coh_support_animation_active_rig(const CohSupportAnimation *state) {
    return state?&state->rigs[state->kind]:NULL;
}
CohStatus coh_support_animation_snapshot(const CohSupportAnimation *state,CohSupportAnimationSnapshot *out) {
    CohSupportAnimationSnapshot result;
    if(!state || !out)return COH_INVALID;
    memset(&result,0,sizeof result);result.samples=state->playback.diagnostics.samples;
    result.triggers=state->triggers;result.transitions=state->playback.diagnostics.transitions;
    result.blended_bones=state->playback.diagnostics.blended_bones;result.cycles=state->cycles;
    result.last_tick=state->playback.tick;result.kind=state->kind;result.frame=state->playback.frame;
    result.retained_bytes=sizeof *state;result.borrowed_bytes=state->borrowed_bytes;*out=result;return COH_OK;
}
