#include "coh_world_render.h"
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

struct CohWrBudget {
    pthread_mutex_t mutex;
    size_t limit, external, owned, peak, retired_count;
    CohWrSnapshot *retired;
};
struct CohWrSnapshot {
    atomic_uint references;
    CohWrBudget *budget;
    CohWrSnapshot *next;
    size_t bytes, count;
    CohWrReceipt receipt;
    CohWrActor player;
    CohWrDrawInput *draws;
};
struct CohWrMailbox { pthread_mutex_t mutex; CohWrBudget *budget; CohWrSnapshot *current; };
struct CohWrBindings {
    CohWrSnapshot *snapshot;
    size_t bytes;
    uint32_t generation, valid;
    uint32_t *active, *scratch;
};

static int finite_n(const float *p, size_t n) {
    size_t i;
    for (i = 0; i < n; ++i) if (!isfinite(p[i])) return 0;
    return 1;
}
static int cancelled(CohCancel c) { return c.poll && c.poll(c.context); }
static int nonzero(const uint8_t p[32]) {
    size_t i; uint8_t n = 0;
    for (i = 0; i < 32; ++i) n |= p[i];
    return n != 0;
}
static int add(size_t *v, size_t count, size_t element) {
    if (count && element > (SIZE_MAX - *v) / count) return 0;
    *v += count * element;
    return 1;
}
static int reserve(CohWrBudget *b, size_t bytes) {
    int ok;
    pthread_mutex_lock(&b->mutex);
    ok = bytes <= b->limit - b->external - b->owned;
    if (ok) {
        b->owned += bytes;
        if (b->owned + b->external > b->peak) b->peak = b->owned + b->external;
    }
    pthread_mutex_unlock(&b->mutex);
    return ok;
}
static void unreserve(CohWrBudget *b, size_t bytes) {
    pthread_mutex_lock(&b->mutex);
    b->owned -= bytes;
    pthread_mutex_unlock(&b->mutex);
}
CohStatus coh_wr_budget_create(size_t limit, size_t external, CohWrBudget **out) {
    CohWrBudget *b;
    if (!out || limit > COH_WR_MAX_MEMORY || external > limit || sizeof(*b) > limit-external) return COH_LIMIT;
    b = calloc(1, sizeof(*b));
    if (!b) return COH_LIMIT;
    if (pthread_mutex_init(&b->mutex, NULL)) { free(b); return COH_STATE; }
    b->limit = limit; b->external = external; b->owned = sizeof(*b);
    b->peak = external + b->owned; *out = b;
    return COH_OK;
}
CohStatus coh_wr_budget_external(CohWrBudget *b, size_t bytes) {
    CohStatus status = COH_OK;
    if (!b) return COH_INVALID;
    pthread_mutex_lock(&b->mutex);
    if (bytes > b->limit - b->owned) status = COH_LIMIT;
    else { b->external = bytes; if (bytes + b->owned > b->peak) b->peak = bytes + b->owned; }
    pthread_mutex_unlock(&b->mutex);
    return status;
}
CohWrMemory coh_wr_budget_memory(CohWrBudget *b) {
    CohWrMemory m = {0,0,0,0,0};
    if (!b) return m;
    pthread_mutex_lock(&b->mutex);
    m.limit = b->limit; m.external_bytes = b->external; m.owned_bytes = b->owned;
    m.peak_bytes = b->peak; m.retired = b->retired_count;
    pthread_mutex_unlock(&b->mutex);
    return m;
}
void coh_wr_collect(CohWrBudget *b) {
    CohWrSnapshot *s, *next;
    if (!b) return;
    pthread_mutex_lock(&b->mutex);
    s = b->retired; b->retired = NULL; b->retired_count = 0;
    pthread_mutex_unlock(&b->mutex);
    while (s) { size_t bytes = s->bytes; next = s->next; free(s); unreserve(b, bytes); s = next; }
}
CohStatus coh_wr_budget_destroy(CohWrBudget *b) {
    if (!b) return COH_INVALID;
    if (coh_wr_budget_memory(b).owned_bytes != sizeof(*b)) return COH_STATE;
    pthread_mutex_destroy(&b->mutex); free(b); return COH_OK;
}
static int valid_material(const CohRenderMaterial *m) {
    size_t i;
    if (m->family < COH_MAT_MULTIPLY || m->family > COH_MAT_ADDGLOW ||
        m->lighting < COH_LIGHT_VERTEX || m->lighting > COH_LIGHT_FIXED ||
        m->blend < COH_BLEND_OPAQUE || m->blend > COH_BLEND_ADDITIVE ||
        m->depth_test > 1 || m->depth_write > 1 || m->cull_back > 1 || m->front_cw > 1 ||
        !finite_n(m->const0,4) || !finite_n(m->const1,4) || !finite_n(m->fog_params,4) ||
        !finite_n(m->fog_color,4) || !finite_n(m->glow_params,4) || !finite_n(m->light,3) ||
        !finite_n(m->diffuse,4) || !finite_n(m->ambient,4) || !finite_n(m->specular,3) ||
        !isfinite(m->alpha_ref) || m->alpha_ref < 0 || m->alpha_ref > 1 ||
        !isfinite(m->shininess) || m->shininess < 0 || m->shininess > 128) return 0;
    for (i=0;i<3;++i) {
        const CohRenderTexture *t = m->textures+i;
        if (t->handle || t->wrap_s < COH_WRAP_REPEAT || t->wrap_s > COH_WRAP_MIRROR ||
            t->wrap_t < COH_WRAP_REPEAT || t->wrap_t > COH_WRAP_MIRROR ||
            t->min_filter < COH_FILTER_NEAREST || t->min_filter > COH_FILTER_MIP_LINEAR ||
            t->mag_filter < COH_FILTER_NEAREST || t->mag_filter > COH_FILTER_LINEAR) return 0;
    }
    return 1;
}
static CohStatus prepare(const CohWrInput *in, CohWrBudget *b, CohCancel cancel,
                         CohWrSnapshot **out, int fixture) {
    const CohWrReceipt *r;
    const CohWrActor *a;
    CohWrSnapshot *s;
    size_t bytes = sizeof(*s), i, j, world = 0, player = 0;
    unsigned char *cursor;
    float qnorm;
    if (!in || !b || !out) return COH_INVALID;
    r = &in->receipt; a = &in->player;
    if (r->abi != COH_WR_ABI || !r->session || !r->snapshot || !r->transaction ||
        !r->scene_generation || !r->asset_generation || !r->entity_generation ||
        !r->selected_dbid || !r->player_entity || !a->appearance_generation || !a->pose_generation ||
        a->is_self != 1 || a->dbid != r->selected_dbid || a->entity_id != r->player_entity ||
        a->generation != r->entity_generation || !finite_n(a->position,3) || !finite_n(a->quaternion,4)) return COH_INVALID;
    qnorm = ((a->quaternion[0]*a->quaternion[0]+a->quaternion[1]*a->quaternion[1])+
             a->quaternion[2]*a->quaternion[2])+a->quaternion[3]*a->quaternion[3];
    if (!isfinite(qnorm) || qnorm < 0.99f || qnorm > 1.01f) return COH_INVALID;
    if (!fixture && (r->source < COH_WR_LOCAL_DEVELOPMENT_AUTH || r->source > COH_WR_ENCRYPTED_AUTH ||
        r->prerequisites != COH_WR_ALL_PREREQUISITES || !nonzero(r->catalog_sha256) ||
        !nonzero(r->asset_manifest_sha256) || !nonzero(r->transaction_sha256))) return COH_STATE;
    if (fixture && r->source != COH_WR_FIXTURE) return COH_STATE;
    if (!in->draws || !in->draw_count) return COH_INVALID;
    if (in->draw_count > COH_WR_MAX_DRAWS || !add(&bytes,in->draw_count,sizeof(*in->draws))) return COH_LIMIT;
    for (i=0;i<in->draw_count;++i) {
        const CohWrDrawInput *d=in->draws+i;
        if (cancelled(cancel)) return COH_CANCELLED;
        if (!d->geometry.vertices || !d->geometry.indices || !d->geometry.vertex_count || !d->geometry.index_count ||
            !d->geometry.identity || d->geometry.generation != r->asset_generation || d->geometry.index_count%3 ||
            !valid_material(&d->material) || !finite_n(d->world,16) ||
            d->world[3] != 0 || d->world[7] != 0 || d->world[11] != 0 || d->world[15] != 1) return COH_INVALID;
        if (d->kind == COH_WR_WORLD_DRAW && !d->actor_entity) ++world;
        else if (d->kind == COH_WR_PLAYER_DRAW && d->actor_entity == a->entity_id) ++player;
        else return COH_INVALID;
        if (d->geometry.vertex_count > COH_WR_MAX_VERTICES || d->geometry.index_count > COH_WR_MAX_INDICES ||
            !add(&bytes,d->geometry.vertex_count,sizeof(CohRenderVertex)) ||
            !add(&bytes,d->geometry.index_count,sizeof(uint32_t)) || bytes>b->limit) return COH_LIMIT;
        for (j=0;j<d->geometry.vertex_count;++j) {
            const CohRenderVertex *v=d->geometry.vertices+j;
            if ((j&255u)==0 && cancelled(cancel)) return COH_CANCELLED;
            if (!finite_n(v->position,3) || !finite_n(v->normal,3) || !finite_n(v->uv0,2) ||
                !finite_n(v->uv1,2) || !finite_n(v->color,4)) return COH_INVALID;
        }
        for (j=0;j<d->geometry.index_count;++j) {
            if ((j&255u)==0 && cancelled(cancel)) return COH_CANCELLED;
            if (d->geometry.indices[j] >= d->geometry.vertex_count) return COH_INVALID;
        }
    }
    if (!world || !player) return COH_STATE;
    if (!reserve(b,bytes)) return COH_LIMIT;
    s=calloc(1,bytes);
    if (!s) { unreserve(b,bytes); return COH_LIMIT; }
    atomic_init(&s->references,1); s->budget=b; s->bytes=bytes;
    s->receipt=*r; s->player=*a; s->count=in->draw_count;
    if (fixture) s->receipt.prerequisites=0;
    s->draws=(CohWrDrawInput *)(s+1);
    cursor=(unsigned char *)(s->draws+in->draw_count);
    for (i=0;i<in->draw_count;++i) {
        CohWrDrawInput *d=s->draws+i;
        size_t vbytes, ibytes;
        if (cancelled(cancel)) { free(s); unreserve(b,bytes); return COH_CANCELLED; }
        *d=in->draws[i];
        vbytes=d->geometry.vertex_count*sizeof(CohRenderVertex);
        ibytes=d->geometry.index_count*sizeof(uint32_t);
        memcpy(cursor,d->geometry.vertices,vbytes); d->geometry.vertices=(const CohRenderVertex *)cursor; cursor+=vbytes;
        memcpy(cursor,d->geometry.indices,ibytes); d->geometry.indices=(const uint32_t *)cursor; cursor+=ibytes;
    }
    if (cancelled(cancel)) { free(s); unreserve(b,bytes); return COH_CANCELLED; }
    *out=s; return COH_OK;
}
CohStatus coh_wr_prepare(const CohWrInput *i,CohWrBudget *b,CohCancel c,CohWrSnapshot **o) { return prepare(i,b,c,o,0); }
CohStatus coh_wr_prepare_fixture(const CohWrInput *i,CohWrBudget *b,CohCancel c,CohWrSnapshot **o) { return prepare(i,b,c,o,1); }
const CohWrReceipt *coh_wr_receipt(const CohWrSnapshot *s) { return s?&s->receipt:NULL; }
const CohWrActor *coh_wr_actor(const CohWrSnapshot *s) { return s?&s->player:NULL; }
size_t coh_wr_draw_count(const CohWrSnapshot *s) { return s?s->count:0; }
CohStatus coh_wr_retain(CohWrSnapshot *s) {
    unsigned old;
    if (!s) return COH_INVALID;
    old=atomic_load_explicit(&s->references,memory_order_relaxed);
    do { if (!old || old==UINT32_MAX) return COH_LIMIT; }
    while (!atomic_compare_exchange_weak_explicit(&s->references,&old,old+1,memory_order_relaxed,memory_order_relaxed));
    return COH_OK;
}
void coh_wr_release(CohWrSnapshot *s) {
    CohWrBudget *b;
    if (!s || atomic_fetch_sub_explicit(&s->references,1,memory_order_acq_rel)!=1) return;
    b=s->budget;
    pthread_mutex_lock(&b->mutex);
    s->next=b->retired; b->retired=s; ++b->retired_count;
    pthread_mutex_unlock(&b->mutex);
}
CohStatus coh_wr_mailbox_create(CohWrBudget *b,CohWrMailbox **out) {
    CohWrMailbox *m;
    if (!b || !out) return COH_INVALID;
    if (!reserve(b,sizeof(*m))) return COH_LIMIT;
    m=calloc(1,sizeof(*m));
    if (!m) { unreserve(b,sizeof(*m)); return COH_LIMIT; }
    if (pthread_mutex_init(&m->mutex,NULL)) { free(m); unreserve(b,sizeof(*m)); return COH_STATE; }
    m->budget=b; *out=m; return COH_OK;
}
CohStatus coh_wr_publish(CohWrMailbox *m,CohWrSnapshot *s) {
    CohWrSnapshot *old;
    CohStatus status;
    if (!m || !s || s->budget!=m->budget) return COH_INVALID;
    pthread_mutex_lock(&m->mutex);
    old=m->current;
    if (old && (s->receipt.session!=old->receipt.session || s->receipt.source!=old->receipt.source ||
        s->receipt.selected_dbid!=old->receipt.selected_dbid || s->receipt.snapshot<=old->receipt.snapshot ||
        s->receipt.transaction<=old->receipt.transaction || s->receipt.scene_generation<old->receipt.scene_generation ||
        s->receipt.asset_generation<old->receipt.asset_generation ||
        s->receipt.entity_generation<old->receipt.entity_generation ||
        (s->receipt.scene_generation==old->receipt.scene_generation &&
            (s->receipt.asset_generation!=old->receipt.asset_generation ||
             memcmp(s->receipt.catalog_sha256,old->receipt.catalog_sha256,32))) ||
        (s->receipt.asset_generation==old->receipt.asset_generation &&
             memcmp(s->receipt.asset_manifest_sha256,old->receipt.asset_manifest_sha256,32)) ||
        (s->receipt.entity_generation==old->receipt.entity_generation &&
            (s->receipt.player_entity!=old->receipt.player_entity || s->player.slot!=old->player.slot ||
             s->player.appearance_generation<old->player.appearance_generation ||
             s->player.pose_generation<old->player.pose_generation)))) {
        pthread_mutex_unlock(&m->mutex); return COH_STATE;
    }
    status=coh_wr_retain(s);
    if (status==COH_OK) m->current=s;
    pthread_mutex_unlock(&m->mutex);
    if (status==COH_OK) coh_wr_release(old);
    return status;
}
CohStatus coh_wr_acquire(CohWrMailbox *m,CohWrSnapshot **out) {
    CohStatus status;
    if (!m || !out) return COH_INVALID;
    pthread_mutex_lock(&m->mutex);
    status=m->current?coh_wr_retain(m->current):COH_NOT_FOUND;
    if (status==COH_OK) *out=m->current;
    pthread_mutex_unlock(&m->mutex);
    return status;
}
void coh_wr_mailbox_clear(CohWrMailbox *m) {
    CohWrSnapshot *old;
    if (!m) return;
    pthread_mutex_lock(&m->mutex); old=m->current; m->current=NULL; pthread_mutex_unlock(&m->mutex);
    coh_wr_release(old);
}
void coh_wr_mailbox_destroy(CohWrMailbox *m) {
    CohWrBudget *b;
    if (!m) return;
    b=m->budget; coh_wr_mailbox_clear(m); pthread_mutex_destroy(&m->mutex); free(m); unreserve(b,sizeof(*m));
}
CohStatus coh_wr_bindings_create(CohWrSnapshot *s,CohWrBindings **out) {
    CohWrBindings *b;
    size_t bytes=sizeof(*b);
    if (!s || !out) return COH_INVALID;
    if (!add(&bytes,s->count,6*sizeof(uint32_t)) || !reserve(s->budget,bytes)) return COH_LIMIT;
    b=calloc(1,bytes);
    if (!b) { unreserve(s->budget,bytes); return COH_LIMIT; }
    if (coh_wr_retain(s)!=COH_OK) { free(b); unreserve(s->budget,bytes); return COH_LIMIT; }
    b->snapshot=s; b->bytes=bytes; b->active=(uint32_t *)(b+1); b->scratch=b->active+3*s->count;
    *out=b; return COH_OK;
}
CohStatus coh_wr_bind(CohWrBindings *b,uint32_t generation,CohWrTextureFn resolve,void *context,CohCancel c) {
    size_t i,j;
    uint32_t *swap;
    if (!b || !generation) return COH_INVALID;
    for (i=0;i<b->snapshot->count;++i) for (j=0;j<3;++j) {
        uint64_t id=b->snapshot->draws[i].texture_id[j];
        uint32_t handle=0;
        CohStatus status;
        if (cancelled(c)) return COH_CANCELLED;
        if (id) {
            if (!resolve) return COH_NOT_FOUND;
            status=resolve(context,id,b->snapshot->receipt.asset_generation,generation,&handle);
            if (status!=COH_OK) return status;
            if (!handle) return COH_NOT_FOUND;
        }
        b->scratch[3*i+j]=handle;
    }
    if (cancelled(c)) return COH_CANCELLED;
    swap=b->active; b->active=b->scratch; b->scratch=swap;
    b->generation=generation; b->valid=1; return COH_OK;
}
void coh_wr_surface_lost(CohWrBindings *b) { if (b) { b->valid=0; b->generation=0; } }
CohStatus coh_wr_draw(const CohWrBindings *b,uint32_t generation,size_t index,
    const float view[16],const float projection[16],CohRenderDraw *out) {
    CohRenderDraw d;
    const CohWrDrawInput *in;
    size_t row,col,j;
    if (!b || !view || !projection || !out || index>=b->snapshot->count || !finite_n(view,16) || !finite_n(projection,16)) return COH_INVALID;
    if (!b->valid || !generation || b->generation!=generation) return COH_STATE;
    in=b->snapshot->draws+index;
    memset(&d,0,sizeof(d)); d.geometry=in->geometry; d.material=in->material;
    memcpy(d.projection,projection,sizeof(d.projection));
    for (col=0;col<4;++col) for (row=0;row<4;++row)
        d.model_view[4*col+row]=((view[row]*in->world[4*col]+view[4+row]*in->world[4*col+1])+
            view[8+row]*in->world[4*col+2])+view[12+row]*in->world[4*col+3];
    if (!finite_n(d.model_view,16)) return COH_INVALID;
    for (j=0;j<3;++j) d.material.textures[j].handle=b->active[3*index+j];
    *out=d; return COH_OK;
}
void coh_wr_bindings_destroy(CohWrBindings *b) {
    CohWrBudget *budget;
    size_t bytes;
    if (!b) return;
    budget=b->snapshot->budget; bytes=b->bytes;
    coh_wr_release(b->snapshot); free(b); unreserve(budget,bytes);
}
