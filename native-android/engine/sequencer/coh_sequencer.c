#include "coh_sequencer.h"
#include <math.h>
#include <string.h>

static int valid_clip(const CohSeqClip *c) {
    return c->ready <= 1u && (!c->ready || (c->asset.path &&
        isfinite(c->first_frame) && isfinite(c->last_frame) &&
        c->first_frame >= 0 && c->last_frame >= c->first_frame &&
        c->last_frame <= 1000000 && isfinite(c->type_scale) &&
        c->type_scale >= 0 && c->type_scale <= 4));
}
CohStatus coh_seq_validate(const CohSeqGraph *g, const CohSeqClip *clips, size_t n) {
    uint32_t i, j;
    if (!g || !g->moves || !g->move_count || !clips || n != g->move_count)
        return COH_INVALID;
    if (g->move_count > COH_SEQ_MAX_MOVES) return COH_LIMIT;
    for (i=0; i<g->move_count; ++i) {
        const CohSeqMove *m=&g->moves[i];
        if (!m->name || m->required_count>COH_SEQ_REQUIRES ||
            m->cycle_count>COH_SEQ_CYCLES || m->priority<0 ||
            !isfinite(m->scale) || m->scale<0 || m->scale>4 ||
            !isfinite(m->interpolate) || m->interpolate<0 ||
            m->interpolate>1000 || !valid_clip(&clips[i])) return COH_INVALID;
        if (m->next_move!=COH_SEQ_NONE && m->next_move>=g->move_count)
            return COH_INVALID;
        if ((m->flags&COH_SEQ_COMPLEX_CYCLE) &&
            (!(m->flags&COH_SEQ_CYCLE) || !m->cycle_count)) return COH_INVALID;
        for (j=0; j<m->required_count; ++j) {
            uint32_t k;
            if (m->required[j]>=COH_SEQ_STATES) return COH_INVALID;
            for (k=0; k<j; ++k)
                if (m->required[k]==m->required[j]) return COH_INVALID;
        }
        for (j=0; j<m->cycle_count; ++j)
            if (m->cycle_moves[j]>=g->move_count) return COH_INVALID;
    }
    return COH_OK;
}
CohStatus coh_seq_set_bit(CohSeqBits *b, uint32_t bit, int on) {
    uint32_t mask;
    if (!b || bit>=COH_SEQ_STATES) return COH_INVALID;
    mask=1u<<(bit&31u);
    if (on) b->words[bit/32u]|=mask; else b->words[bit/32u]&=~mask;
    return COH_OK;
}
int coh_seq_requires(const CohSeqMove *m, const CohSeqBits *s) {
    uint32_t i;
    if (!m || !s || m->required_count>COH_SEQ_REQUIRES) return 0;
    for (i=0; i<m->required_count; ++i) {
        uint32_t b=m->required[i];
        if (b>=COH_SEQ_STATES || !(s->words[b/32u]&(1u<<(b&31u)))) return 0;
    }
    return 1;
}
int coh_seq_interrupts(const CohSeqMove *a, const CohSeqMove *b) {
    uint32_t i;
    if (!a || !b) return 0;
    for (i=0; i<COH_SEQ_IRQ_WORDS; ++i)
        if (a->interrupts[i]&b->members[i]) return 1;
    return 0;
}
CohStatus coh_seq_init(CohSequencer *s, const CohSeqGraph *g,
                       const CohSeqClip *clips, size_t n, uint32_t actor,
                       uint32_t rig, uint32_t move, uint32_t seed) {
    CohSequencer t;
    CohStatus status;
    if (!s) return COH_INVALID;
    status=coh_seq_validate(g,clips,n);
    if (status!=COH_OK) return status;
    if (move>=g->move_count) return COH_INVALID;
    if (!clips[move].ready) return COH_NOT_FOUND;
    memset(&t,0,sizeof t);
    t.graph=g; t.clips=clips; t.actor_id=actor; t.rig_id=rig;
    t.move=move; t.previous_move=t.searched_move=COH_SEQ_NONE;
    t.frame=clips[move].first_frame; t.previous_frame=-1;
    t.predict_seed=seed; t.diagnostics.retained_bytes=sizeof t;
    *s=t;
    return COH_OK;
}
CohStatus coh_seq_rebind_clips(CohSequencer *s, const CohSeqClip *clips, size_t n) {
    CohStatus status;
    if (!s || !s->graph || s->move>=n) return COH_INVALID;
    status=coh_seq_validate(s->graph,clips,n);
    if (status!=COH_OK) return status;
    if (!clips[s->move].ready) return COH_NOT_FOUND;
    if (!isfinite(s->frame) || s->frame<clips[s->move].first_frame ||
        s->frame>clips[s->move].last_frame) return COH_INVALID;
    s->clips=clips;
    return COH_OK;
}
/* The source indexes each interrupting move under its first declared required
 * bit, then visits set bits ascending and moves in declaration order. */
static CohStatus search(CohSequencer *s, const CohSeqInput *in, uint32_t *chosen) {
    uint32_t i, count=0;
    uint32_t candidates[COH_SEQ_MAX_TIES];
    int32_t highest=0;
    int overflow=0;
    const CohSeqGraph *g=s->graph;
    ++s->diagnostics.searches;
    for (i=0; i<g->move_count; ++i) {
            const CohSeqMove *m=&g->moves[i];
            uint32_t j, irq=0;
            if (!m->required_count) continue;
            for (j=0; j<COH_SEQ_IRQ_WORDS; ++j) irq|=m->interrupts[j];
            if (!irq) continue;
            ++s->diagnostics.candidate_checks;
            if (!in->force_interrupt && !coh_seq_interrupts(m,&g->moves[s->move]))
                continue;
            if (m->priority<highest || !coh_seq_requires(m,&in->state)) continue;
            if (m->priority>highest) { count=0; highest=m->priority; overflow=0; }
            if (count==COH_SEQ_MAX_TIES) { overflow=1; continue; }
            /* Stable insertion of equal-priority results in source anchor-bit
             * order. One graph scan plus at most 100 bounded insertions. */
            j=count;
            while (j && g->moves[candidates[j-1]].required[0]>m->required[0]) {
                candidates[j]=candidates[j-1]; --j;
            }
            candidates[j]=i; ++count;
    }
    if (overflow) return COH_LIMIT;
    *chosen=COH_SEQ_NONE;
    if (count) {
        uint32_t first=candidates[0]; *chosen=first;
        if (count>1) {
            uint32_t pick=(g->moves[first].flags&COH_SEQ_PICK_RANDOMLY) ?
                in->random_choice : s->incrementor++;
            *chosen=candidates[pick%count];
        }
    }
    return COH_OK;
}
static uint32_t random_source(uint32_t *seed) {
    /* Explicit modulo-2^32 arithmetic preserves Windows source results without
     * signed-overflow UB in the legacy randUIntGivenSeed implementation. */
    *seed=*seed*214013u+2531011u;
    return (*seed>>16u)&0x7fffu;
}
static CohStatus enter(CohSequencer *s, uint32_t move) {
    const CohSeqClip *c;
    const CohSeqMove *a=&s->graph->moves[s->move], *b;
    if (move==COH_SEQ_NONE) return COH_UNSUPPORTED;
    if (move>=s->graph->move_count) return COH_STATE;
    c=&s->clips[move]; b=&s->graph->moves[move];
    if (!c->ready) return COH_NOT_FOUND;
    if (!((a->flags&COH_SEQ_CYCLE) && (b->flags&COH_SEQ_CYCLE) &&
          s->frame<c->last_frame && s->frame>c->first_frame &&
          !(a->flags&COH_SEQ_COMPLEX_CYCLE))) {
        s->frame=c->first_frame; s->previous_frame=-1;
    }
    s->previous_move=s->move; s->move=move;
    ++s->diagnostics.transitions;
    return COH_OK;
}
CohStatus coh_seq_step(CohSequencer *s, const CohSeqInput *in, CohSeqSelection *out) {
    CohSequencer t;
    CohSeqSelection result;
    const CohSeqMove *m;
    const CohSeqClip *c;
    uint32_t next=COH_SEQ_NONE, cause=0;
    float dt;
    CohStatus status;
    if (!s || !in || !out || !s->graph || !s->clips ||
        s->move>=s->graph->move_count || !isfinite(s->frame) ||
        !isfinite(s->previous_frame) || !isfinite(in->timestep_frames) ||
        in->timestep_frames<0 || in->timestep_frames>3 ||
        !isfinite(in->animation_scale) || in->animation_scale<0 ||
        in->animation_scale>4 || in->force_interrupt>1 ||
        (in->state.words[COH_SEQ_WORDS-1]&0xfffff000u)) return COH_INVALID;
    if (in->cancel.poll && in->cancel.poll(in->cancel.context)) return COH_CANCELLED;
    t=*s; m=&t.graph->moves[t.move]; c=&t.clips[t.move];
    if (!c->ready) return COH_NOT_FOUND;
    ++t.diagnostics.steps;
    dt=in->timestep_frames*in->animation_scale;
    if (in->force_interrupt || t.searched_move!=t.move ||
        memcmp(&t.last_state,&in->state,sizeof t.last_state)) {
        t.last_state=in->state; t.searched_move=t.move;
        status=search(&t,in,&next);
        if (status!=COH_OK) return status;
        if (next!=COH_SEQ_NONE) cause|=COH_SEQ_CAUSE_INTERRUPT;
    }
    if (!in->force_interrupt && (next==COH_SEQ_NONE || next==t.move) &&
        (m->flags&(COH_SEQ_CYCLE|COH_SEQ_REQ_INPUTS)) &&
        !(m->flags&COH_SEQ_FINISH_CYCLE) && !coh_seq_requires(m,&in->state)) {
        next=m->next_move; cause|=COH_SEQ_CAUSE_RELEASE;
        if (next==COH_SEQ_NONE) return COH_UNSUPPORTED;
    }
    if (!in->force_interrupt && (next==COH_SEQ_NONE || next==t.move)) {
        float scale=(c->type_scale!=1) ? c->type_scale : m->scale;
        t.previous_frame=t.frame; t.frame+=scale*dt;
        next=COH_SEQ_NONE;
        if (t.frame>c->last_frame) {
            if ((m->flags&COH_SEQ_CYCLE) && coh_seq_requires(m,&in->state)) {
                if (m->flags&COH_SEQ_COMPLEX_CYCLE) {
                    uint32_t choice=random_source(&t.predict_seed)%m->cycle_count;
                    next=m->cycle_moves[choice];
                    if (next!=t.move) cause|=COH_SEQ_CAUSE_COMPLEX;
                }
                if (next==COH_SEQ_NONE || next==t.move) {
                    t.frame-=c->last_frame-c->first_frame;
                    if (t.frame>c->last_frame) t.frame=c->first_frame;
                    t.previous_frame=-1; ++t.diagnostics.cycles;
                    cause|=COH_SEQ_CAUSE_CYCLE;
                }
            } else {
                next=m->next_move; cause|=(m->flags&COH_SEQ_CYCLE) ?
                    COH_SEQ_CAUSE_RELEASE : COH_SEQ_CAUSE_ENDED;
                if (next==COH_SEQ_NONE) return COH_UNSUPPORTED;
            }
        }
    }
    if (next!=COH_SEQ_NONE && (in->force_interrupt || next!=t.move)) {
        status=enter(&t,next);
        if (status!=COH_OK) return status;
    }
    memset(&result,0,sizeof result);
    result.actor_id=t.actor_id; result.rig_id=t.rig_id;
    result.move=t.move; result.previous_move=t.previous_move;
    result.clip_id=t.clips[t.move].clip_id;
    result.flags=t.graph->moves[t.move].flags; result.cause=cause;
    result.frame=t.frame; result.previous_frame=t.previous_frame;
    result.interpolate_frames=t.graph->moves[t.move].interpolate;
    *s=t; *out=result;
    return COH_OK;
}
CohStatus coh_seq_sample(const CohSequencer *s, const CohAnimationRig *const *rigs,
                         size_t count, CohAnimationPose *pose) {
    const CohAnimationRig *rig;
    if (!s || !s->graph || !pose || !rigs || s->move>=count ||
        s->move>=s->graph->move_count) return COH_INVALID;
    rig=rigs[s->move];
    if (!rig) return COH_NOT_FOUND;
    if (!isfinite(s->frame) || s->frame<rig->first_frame ||
        s->frame>rig->last_frame) return COH_INVALID;
    return coh_animation_sample(rig,s->frame,pose)==0 ? COH_OK : COH_INVALID;
}
