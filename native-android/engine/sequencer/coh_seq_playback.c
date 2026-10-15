#include "coh_seq_playback.h"
#include <math.h>
#include <string.h>

static int topology(const CohAnimationRig *r) {
    uint8_t seen[COH_ANIMATION_BONES]={0}; uint32_t i;
    if (!r || !r->node_count || r->node_count>COH_ANIMATION_BONES ||
        !isfinite(r->first_frame) || !isfinite(r->last_frame) ||
        r->first_frame<0 || r->last_frame<r->first_frame) return 0;
    for (i=0;i<r->node_count;++i) {
        unsigned id=r->order[i]; int p;
        if (id>=COH_ANIMATION_BONES || seen[id]) return 0;
        p=r->parent[id];
        if (p!=-1 && (p<0 || p>=(int)COH_ANIMATION_BONES || !seen[p])) return 0;
        seen[id]=1;
    }
    return 1;
}
static int same_topology(const CohAnimationRig *a,const CohAnimationRig *b) {
    uint32_t i;
    if (!a || !b || a->node_count!=b->node_count) return 0;
    for (i=0;i<a->node_count;++i) {
        unsigned id=a->order[i];
        if (id!=b->order[i] || a->parent[id]!=b->parent[id]) return 0;
    }
    return 1;
}
static CohStatus bindings_valid(const CohSeqPoseBinding *b,size_t n,uint32_t rig) {
    size_t i;
    if (!b || !n) return COH_INVALID;
    if (n>COH_SEQ_MAX_MOVES) return COH_LIMIT;
    for (i=0;i<n;++i)
        if (b[i].rig_id!=rig || (b[i].rig && !topology(b[i].rig))) return COH_INVALID;
    return COH_OK;
}
CohStatus coh_seq_playback_init(CohSeqPlayback *p,uint32_t actor,uint32_t rig,
    const CohSeqPoseBinding *bindings,size_t n,const CohSeqMarker *markers,size_t count) {
    CohSeqPlayback result; size_t i; CohStatus status;
    if (!p || (count && !markers)) return COH_INVALID;
    if (count>COH_SEQ_PLAYBACK_MARKERS) return COH_LIMIT;
    status=bindings_valid(bindings,n,rig); if (status!=COH_OK) return status;
    for (i=0;i<count;++i) {
        const CohSeqMarker *m=&markers[i];
        if (m->move>=n || !isfinite(m->frame) || m->frame<0 || m->frame>1000000)
            return COH_INVALID;
        if (i && (m->move<markers[i-1].move ||
            (m->move==markers[i-1].move && m->frame<markers[i-1].frame))) return COH_INVALID;
        if (bindings[m->move].rig && (m->frame<bindings[m->move].rig->first_frame ||
            m->frame>bindings[m->move].rig->last_frame)) return COH_INVALID;
    }
    memset(&result,0,sizeof result); result.actor_id=actor; result.rig_id=rig;
    result.bindings=bindings; result.binding_count=n; result.markers=markers;
    result.marker_count=count; result.move=COH_SEQ_NONE;
    result.diagnostics.retained_bytes=sizeof result; *p=result; return COH_OK;
}
CohStatus coh_seq_playback_rebind(CohSeqPlayback *p,const CohSeqPoseBinding *bindings,size_t n) {
    CohStatus status; size_t i;
    if (!p || n!=p->binding_count) return COH_INVALID;
    status=bindings_valid(bindings,n,p->rig_id); if (status!=COH_OK) return status;
    if (p->initialized && (!bindings[p->move].rig ||
        bindings[p->move].clip_id!=p->bindings[p->move].clip_id ||
        !same_topology(p->last_rig,bindings[p->move].rig) ||
        p->frame<bindings[p->move].rig->first_frame ||
        p->frame>bindings[p->move].rig->last_frame)) return COH_STATE;
    for(i=0;i<p->marker_count;++i) {
        const CohSeqMarker *m=&p->markers[i]; const CohAnimationRig *r=bindings[m->move].rig;
        if(r && (m->frame<r->first_frame || m->frame>r->last_frame)) return COH_INVALID;
    }
    p->bindings=bindings;
    if(p->initialized)p->last_rig=bindings[p->move].rig;
    return COH_OK;
}
static float quaternion(float alpha,const float *a,float *q) {
    float dot=a[0]*q[0]+a[1]*q[1]+a[2]*q[2]+a[3]*q[3];
    float beta=1.f-alpha,mag=0; unsigned j;
    if (dot<0) alpha=-alpha;
    for(j=0;j<4;++j) { q[j]=beta*a[j]+alpha*q[j]; mag+=q[j]*q[j]; }
    if(mag<=0)q[0]=1;
    else { float inv=1.f/(float)sqrt(mag); for(j=0;j<4;++j)q[j]*=inv; }
    return dot;
}
static void world_rows(const CohAnimationRig *r,CohAnimationPose *pose) {
    uint32_t i; unsigned j,k;
    for(i=0;i<r->node_count;++i) {
        unsigned id=r->order[i]; const float *q=pose->rotation[id],*p=pose->position[id];
        float tx=2.f*q[0],ty=2.f*q[1],tz=2.f*q[2],wx=tx*q[3],wy=ty*q[3],wz=tz*q[3];
        float xx=tx*q[0],xy=ty*q[0],xz=tz*q[0],yy=ty*q[1],yz=tz*q[1],zz=tz*q[2];
        float local[12]={1.f-(yy+zz),xy+wz,xz-wy,p[0],xy-wz,1.f-(xx+zz),yz+wx,p[1],xz+wy,yz-wx,1.f-(xx+yy),p[2]};
        float *out=pose->world_rows[id]; int parent=r->parent[id];
        if(parent==-1)memcpy(out,local,sizeof local);
        else { const float *a=pose->world_rows[parent];
            for(j=0;j<3;++j) {
                for(k=0;k<3;++k)out[j*4+k]=local[k]*a[j*4]+local[4+k]*a[j*4+1]+local[8+k]*a[j*4+2];
                out[j*4+3]=local[3]*a[j*4]+local[7]*a[j*4+1]+local[11]*a[j*4+2]+a[j*4+3];
            }
        }
    }
}
static int crosses(const CohSeqPlayback *p,const CohSeqSelection *s,const CohSeqMarker *m,int entry) {
    if(m->move!=s->move)return 0;
    if(entry)return m->frame<=s->frame;
    if(s->cause&COH_SEQ_CAUSE_CYCLE)return m->frame>p->frame || m->frame<=s->frame;
    return m->frame>p->frame && m->frame<=s->frame;
}
static void event(CohSeqPlaybackEvent *e,const CohSeqSelection *s,uint64_t tick,
    uint32_t type,uint32_t kind,uint32_t token,float frame) {
    e->tick=tick; e->actor_id=s->actor_id; e->rig_id=s->rig_id; e->move=s->move;
    e->clip_id=s->clip_id; e->type=type; e->kind=kind; e->token=token; e->frame=frame;
}
CohStatus coh_seq_playback_sample(CohSeqPlayback *p,const CohSeqSelection *s,
    uint64_t generation,float dt,uint64_t tick,CohCancel cancel,CohAnimationPose *out,
    CohSeqPlaybackEvent *events,size_t capacity,size_t *event_count) {
    CohSeqPlayback next; CohAnimationPose pose; const CohAnimationRig *r;
    size_t i,n=0,write=0; uint32_t entry; float percent; unsigned j;
    if(!p || !s || !out || !event_count || (capacity && !events) ||
        s->actor_id!=p->actor_id || s->rig_id!=p->rig_id || s->move>=p->binding_count ||
        !isfinite(dt) || dt<0 || dt>3 || !isfinite(s->frame) ||
        !isfinite(s->interpolate_frames) || s->interpolate_frames<0 || s->interpolate_frames>1000 ||
        (p->initialized && (tick<=p->tick || generation<p->transition_generation))) return COH_INVALID;
    if(cancel.poll && cancel.poll(cancel.context))return COH_CANCELLED;
    r=p->bindings[s->move].rig;
    if(!r)return COH_NOT_FOUND;
    if(s->clip_id!=p->bindings[s->move].clip_id || s->frame<r->first_frame || s->frame>r->last_frame)return COH_INVALID;
    entry=!p->initialized || generation!=p->transition_generation;
    if(p->initialized && ((!entry && s->move!=p->move) ||
        !same_topology(p->last_rig,r)))return COH_STATE;
    if(!entry && !(s->cause&COH_SEQ_CAUSE_CYCLE) && s->frame<p->frame)return COH_STATE;
    n=entry?1u:((s->cause&COH_SEQ_CAUSE_CYCLE)?1u:0u);
    for(i=0;i<p->marker_count;++i)if(crosses(p,s,&p->markers[i],entry))++n;
    if(n>capacity)return COH_LIMIT;
    if(coh_animation_sample(r,s->frame,&pose))return COH_INVALID;
    next=*p;
    if(entry) {
        next.interpolation_frame=0;
        for(i=0;i<COH_ANIMATION_BONES;++i)next.rotation_blend[i]=next.translation_blend[i]=p->stored_valid[i];
        if(p->initialized)++next.diagnostics.transitions;
    }
    next.interpolation_frame+=dt;
    /* Source duration is <=1000; all larger clocks select percent_new=1.
     * Saturation prevents an unbounded lifecycle counter without changing it. */
    if(next.interpolation_frame>1004)next.interpolation_frame=1004;
    percent=next.interpolation_frame<s->interpolate_frames ? 1.f/(1.f+s->interpolate_frames-next.interpolation_frame) : 1.f;
    if(p->initialized && !(s->flags&COH_SEQ_PLAYBACK_NOINTERP)) {
        for(i=0;i<r->node_count;++i) {
            unsigned id=r->order[i]; int changed=0;
            /* animateGfxNodeBone does not invoke its blend helper at >=1. */
            if(percent>=1)continue;
            if(next.rotation_blend[id]) {
                float dot=quaternion(percent,p->last_pose.rotation[id],pose.rotation[id]);
                if(dot>1-(.0003*dt))next.rotation_blend[id]=0;
                changed=1;
            }
            if(next.translation_blend[id]) {
                float distance=0;
                for(j=0;j<3;++j) {
                    float old=p->last_pose.position[id][j];
                    pose.position[id][j]=old+(pose.position[id][j]-old)*percent;
                    distance+=(pose.position[id][j]-old)*(pose.position[id][j]-old);
                }
                {float tolerance=(float)(.001*dt);
                    if(distance<=tolerance*tolerance)next.translation_blend[id]=0;}
                changed=1;
            }
            next.diagnostics.blended_bones+=(uint64_t)changed;
        }
        world_rows(r,&pose);
    }
    /* No writes to external output until every validation/sampling step passed. */
    if(entry)event(&events[write++],s,tick,COH_SEQ_EVENT_ENTER,0,0,s->frame);
    else if(s->cause&COH_SEQ_CAUSE_CYCLE)event(&events[write++],s,tick,COH_SEQ_EVENT_CYCLE,0,0,s->frame);
    /* A wrap dispatches end-of-old-cycle before beginning-of-new-cycle. */
    if(!entry && (s->cause&COH_SEQ_CAUSE_CYCLE)) {
        for(i=0;i<p->marker_count;++i) {const CohSeqMarker *m=&p->markers[i];
            if(m->move==s->move && m->frame>p->frame)event(&events[write++],s,tick,COH_SEQ_EVENT_MARKER,m->kind,m->token,m->frame);
        }
        for(i=0;i<p->marker_count;++i) {const CohSeqMarker *m=&p->markers[i];
            if(m->move==s->move && m->frame<=s->frame && m->frame<=p->frame)event(&events[write++],s,tick,COH_SEQ_EVENT_MARKER,m->kind,m->token,m->frame);
        }
    } else for(i=0;i<p->marker_count;++i) {const CohSeqMarker *m=&p->markers[i];
        if(crosses(p,s,m,(int)entry))event(&events[write++],s,tick,COH_SEQ_EVENT_MARKER,m->kind,m->token,m->frame);
    }
    if(!(s->flags&COH_SEQ_PLAYBACK_NOINTERP)) {
        next.last_pose=pose;
        for(i=0;i<r->node_count;++i)next.stored_valid[r->order[i]]=1;
    }
    next.last_rig=r; next.move=s->move; next.frame=s->frame;
    next.tick=tick; next.transition_generation=generation; next.initialized=1;
    ++next.diagnostics.samples; next.diagnostics.events+=write;
    next.diagnostics.borrowed_rig_bytes=r->byte_count;
    *out=pose; *event_count=write; *p=next; return COH_OK;
}
CohStatus coh_seq_playback_state(const CohSeqBits *base,const CohSeqStateUpdate *updates,size_t n,CohSeqBits *out) {
    CohSeqBits result; size_t i;
    if(!base || !out || (n && !updates) || (base->words[COH_SEQ_WORDS-1]&0xfffff000u))return COH_INVALID;
    if(n>COH_SEQ_STATES)return COH_LIMIT;
    result=*base;
    for(i=0;i<n;++i) {
        if(updates[i].on>1 || updates[i].bit>=COH_SEQ_STATES)return COH_INVALID;
        if(coh_seq_set_bit(&result,updates[i].bit,updates[i].on)!=COH_OK)return COH_INVALID;
    }
    *out=result; return COH_OK;
}
