/* Kept in the adapter translation unit to share its exact aggregate allocator.
 * No allocation/destruction occurs from the GL consumption path. */
struct CohWrPreparedFrame {
    atomic_uint references;
    CohWrPresentation *owner;
    CohWrPreparedFrame *next;
    CohWrFrame *frame;
    CohWrBindings *bindings;
    CohWrPresentationResources resources;
    uint64_t publication;
};
struct CohWrPresentation {
    pthread_mutex_t mutex;
    CohWrBudget *budget;
    CohWrMailbox *source;
    CohRendererConfig config;
    CohWrPreparedFrame *pending, *active, *retired;
    uint64_t publication;
    size_t objects;
    uint32_t fixture, paused, stopped, surface;
};
static CohStatus presentation_create(CohWrBudget *b,const CohRendererConfig *c,
    CohWrPresentation **out,int fixture) {
    CohWrPresentation *p;
    CohStatus status;
    if (!b || !c || !out) return COH_INVALID;
    if (*out) return COH_STATE;
    if (!c->max_draws || c->max_draws>COH_WR_MAX_BATCH_DRAWS ||
        !c->max_vertices_per_draw || !c->max_indices_per_draw ||
        !c->shader_capacity || c->shader_capacity>3) return COH_LIMIT;
    if (!reserve(b,sizeof(*p))) return COH_LIMIT;
    p=calloc(1,sizeof(*p));
    if (!p) { unreserve(b,sizeof(*p)); return COH_LIMIT; }
    if (pthread_mutex_init(&p->mutex,NULL)) {
        free(p); unreserve(b,sizeof(*p)); return COH_STATE;
    }
    status=coh_wr_mailbox_create(b,&p->source);
    if (status!=COH_OK) {
        pthread_mutex_destroy(&p->mutex); free(p); unreserve(b,sizeof(*p)); return status;
    }
    p->budget=b; p->config=*c; p->fixture=(uint32_t)fixture; p->paused=1;
    *out=p; return COH_OK;
}
CohStatus coh_wr_presentation_create(CohWrBudget *b,const CohRendererConfig *c,CohWrPresentation **out) {
    return presentation_create(b,c,out,0);
}
CohStatus coh_wr_presentation_create_fixture(CohWrBudget *b,const CohRendererConfig *c,CohWrPresentation **out) {
    return presentation_create(b,c,out,1);
}
static CohStatus presentation_retain(CohWrPreparedFrame *f) {
    unsigned refs=atomic_load_explicit(&f->references,memory_order_relaxed);
    do { if (!refs || refs==UINT32_MAX) return COH_LIMIT; }
    while (!atomic_compare_exchange_weak_explicit(&f->references,&refs,refs+1,
        memory_order_relaxed,memory_order_relaxed));
    return COH_OK;
}
void coh_wr_presentation_release(CohWrPreparedFrame *f) {
    CohWrPresentation *p;
    if (!f || atomic_fetch_sub_explicit(&f->references,1,memory_order_acq_rel)!=1) return;
    p=f->owner;
    pthread_mutex_lock(&p->mutex);
    f->next=p->retired; p->retired=f;
    pthread_mutex_unlock(&p->mutex);
}
CohStatus coh_wr_presentation_prepare(CohWrPresentation *p,CohWrSnapshot *s,
    uint64_t publication,const size_t *indices,size_t count,const float view[16],
    const float projection[16],const CohWrPresentationResources *resources,
    CohCancel cancel,CohWrPreparedFrame **out) {
    CohWrPreparedFrame *f;
    CohStatus status;
    int stopped;
    if (!p || !s || !publication || !resources || !resources->hold ||
        !resources->drop || !resources->resolve || !out || s->budget!=p->budget) return COH_INVALID;
    if (*out) return COH_STATE;
    if ((s->receipt.source==COH_WR_FIXTURE)!=!!p->fixture) return COH_STATE;
    pthread_mutex_lock(&p->mutex); stopped=p->stopped; pthread_mutex_unlock(&p->mutex);
    if (stopped) return COH_STATE;
    if (cancelled(cancel)) return COH_CANCELLED;
    if (!reserve(p->budget,sizeof(*f))) return COH_LIMIT;
    f=calloc(1,sizeof(*f));
    if (!f) { unreserve(p->budget,sizeof(*f)); return COH_LIMIT; }
    status=coh_wr_frame_create(s,indices,count,view,projection,&p->config,cancel,&f->frame);
    if (status!=COH_OK) goto failed;
    status=coh_wr_bindings_create(s,&f->bindings);
    if (status!=COH_OK) goto failed;
    status=resources->hold(resources->context);
    if (status!=COH_OK) goto failed;
    if (cancelled(cancel)) { resources->drop(resources->context); status=COH_CANCELLED; goto failed; }
    f->owner=p; f->publication=publication; f->resources=*resources;
    atomic_init(&f->references,1);
    pthread_mutex_lock(&p->mutex); ++p->objects; pthread_mutex_unlock(&p->mutex);
    *out=f; return COH_OK;
failed:
    coh_wr_bindings_destroy(f->bindings); coh_wr_frame_destroy(f->frame);
    free(f); unreserve(p->budget,sizeof(*f)); return status;
}
CohStatus coh_wr_presentation_publish(CohWrPresentation *p,CohWrPreparedFrame *f) {
    CohWrPreparedFrame *old=NULL;
    CohStatus status;
    if (!p || !f || f->owner!=p) return COH_INVALID;
    pthread_mutex_lock(&p->mutex);
    if (p->stopped || f->publication<=p->publication) { status=COH_STATE; goto done; }
    status=presentation_retain(f);
    if (status!=COH_OK) goto done;
    /* Camera frames may share an identical immutable source pointer. Any new
     * snapshot still passes the original complete monotonic publication rule. */
    pthread_mutex_lock(&p->source->mutex);
    status=p->source->current==f->frame->snapshot?COH_OK:COH_NOT_FOUND;
    pthread_mutex_unlock(&p->source->mutex);
    if (status!=COH_OK) status=coh_wr_publish(p->source,f->frame->snapshot);
    if (status!=COH_OK) {
        /* Extra reference cannot become final: publisher retains its lease. */
        atomic_fetch_sub_explicit(&f->references,1,memory_order_relaxed); goto done;
    }
    old=p->pending; p->pending=f; p->publication=f->publication;
done:
    pthread_mutex_unlock(&p->mutex);
    coh_wr_presentation_release(old); return status;
}
CohStatus coh_wr_presentation_resume(CohWrPresentation *p,CohRenderer *r,uint32_t surface) {
    CohRendererStats stats;
    if (!p || !r || !surface) return COH_INVALID;
    stats=coh_renderer_stats(r);
    if (p->stopped || stats.queued || stats.surface_generation!=surface ||
        (p->surface && p->surface!=surface)) return COH_STATE;
    p->surface=surface; p->paused=0; return COH_OK;
}
CohStatus coh_wr_presentation_pause(CohWrPresentation *p,CohRenderer *r) {
    if (!p || !r) return COH_INVALID;
    if (p->stopped || coh_renderer_stats(r).queued) return COH_STATE;
    p->paused=1; return COH_OK;
}
CohStatus coh_wr_presentation_surface_lost(CohWrPresentation *p,CohRenderer *r,
    uint32_t surface,int alive) {
    if (!p || !r || !surface || (alive!=0 && alive!=1)) return COH_INVALID;
    if (p->stopped || surface<=p->surface ||
        surface<=coh_renderer_stats(r).surface_generation) return COH_STATE;
    /* Abandon borrowed spans BEFORE invalidating their binding/owner lifetimes. */
    coh_renderer_surface_lost(r,surface,alive);
    if (p->active) coh_wr_surface_lost(p->active->bindings);
    p->surface=surface; p->paused=1; return COH_OK;
}
static int presentation_cancel(void *v) { (void)v; return 1; }
static CohStatus presentation_draw(CohWrPreparedFrame *f,CohRenderer *r,
    uint32_t surface,CohCancel cancel,CohWrPresentationResult *result) {
    CohStatus status;
    size_t batch;
    for (batch=0;batch<coh_wr_frame_batch_count(f->frame);++batch) {
        CohWrBatch span;
        size_t i;
        if (cancelled(cancel)) return COH_CANCELLED;
        status=coh_wr_frame_batch(f->frame,batch,&span);
        if (status!=COH_OK) return status;
        status=coh_renderer_begin(r,surface);
        if (status!=COH_OK) return status;
        for (i=0;i<span.count;++i) {
            CohRenderDraw draw;
            if (cancelled(cancel)) { status=COH_CANCELLED; break; }
            status=coh_wr_frame_draw(f->frame,f->bindings,surface,span.first+i,&draw);
            if (status==COH_OK) status=coh_renderer_submit(r,&draw);
            if (status!=COH_OK) break;
        }
        if (status==COH_OK) status=coh_renderer_flush(r,cancel);
        else {
            CohCancel abandon={presentation_cancel,NULL};
            /* Source renderer clears active/queued even for an empty cancelled
             * flush, without executing a backend draw or destroying programs. */
            (void)coh_renderer_flush(r,abandon);
        }
        if (status!=COH_OK) return status;
        result->draws+=span.count; ++result->batches;
    }
    return COH_OK;
}
CohStatus coh_wr_presentation_render(CohWrPresentation *p,CohRenderer *r,
    CohCancel cancel,CohWrPresentationResult *out) {
    CohWrPreparedFrame *candidate=NULL,*selected,*old=NULL,*pending=NULL;
    CohWrPresentationResult result={0};
    CohStatus status;
    if (!p || !r || !out) return COH_INVALID;
    if (p->paused || p->stopped || !p->surface || coh_renderer_stats(r).queued ||
        coh_renderer_stats(r).surface_generation!=p->surface) return COH_STATE;
    pthread_mutex_lock(&p->mutex);
    if (p->pending && p->pending!=p->active) {
        status=presentation_retain(p->pending);
        if (status==COH_OK) candidate=p->pending;
    } else status=COH_OK;
    pthread_mutex_unlock(&p->mutex);
    if (status!=COH_OK) return status;
    selected=candidate?candidate:p->active;
    result.candidate_status=COH_OK; result.surface_generation=p->surface;
    if (candidate) {
        result.candidate_status=coh_wr_frame_bind(candidate->frame,candidate->bindings,
            p->surface,candidate->resources.resolve,candidate->resources.context,cancel);
        if (result.candidate_status!=COH_OK) {
            selected=p->active; result.fallback=selected!=NULL;
        }
    }
    if (!selected) {
        status=candidate?result.candidate_status:COH_NOT_FOUND;
        *out=result; coh_wr_presentation_release(candidate); return status;
    }
    if (selected!=candidate) {
        status=coh_wr_frame_bind(selected->frame,selected->bindings,p->surface,
            selected->resources.resolve,selected->resources.context,cancel);
    } else status=COH_OK;
    result.publication=selected->publication;
    result.snapshot=selected->frame->snapshot->receipt.snapshot;
    result.transaction=selected->frame->snapshot->receipt.transaction;
    result.source=selected->frame->snapshot->receipt.source;
    if (status==COH_OK) status=presentation_draw(selected,r,p->surface,cancel,&result);
    if (selected==candidate && status!=COH_OK) result.candidate_status=status;
    if (selected==candidate && status==COH_OK) {
        old=p->active; p->active=candidate; candidate=NULL;
        pthread_mutex_lock(&p->mutex);
        if (p->pending==p->active) { pending=p->pending; p->pending=NULL; }
        pthread_mutex_unlock(&p->mutex);
        result.adopted=1;
    }
    coh_wr_presentation_release(old); coh_wr_presentation_release(pending);
    coh_wr_presentation_release(candidate); *out=result; return status;
}
CohStatus coh_wr_presentation_stop(CohWrPresentation *p,CohRenderer *r,int alive) {
    CohWrPreparedFrame *pending,*active;
    if (!p || !r || (alive!=0 && alive!=1)) return COH_INVALID;
    if (p->stopped) return COH_STATE;
    coh_renderer_surface_lost(r,p->surface,alive);
    pthread_mutex_lock(&p->mutex);
    p->stopped=1; p->paused=1; pending=p->pending; p->pending=NULL;
    active=p->active; p->active=NULL;
    pthread_mutex_unlock(&p->mutex);
    coh_wr_mailbox_clear(p->source);
    coh_wr_presentation_release(pending); coh_wr_presentation_release(active);
    return COH_OK;
}
void coh_wr_presentation_collect(CohWrPresentation *p) {
    CohWrPreparedFrame *f,*next;
    if (!p) return;
    pthread_mutex_lock(&p->mutex); f=p->retired; p->retired=NULL; pthread_mutex_unlock(&p->mutex);
    while (f) {
        next=f->next;
        f->resources.drop(f->resources.context);
        coh_wr_bindings_destroy(f->bindings); coh_wr_frame_destroy(f->frame);
        free(f); unreserve(p->budget,sizeof(*f));
        pthread_mutex_lock(&p->mutex); --p->objects; pthread_mutex_unlock(&p->mutex);
        f=next;
    }
    coh_wr_collect(p->budget);
}
CohStatus coh_wr_presentation_destroy(CohWrPresentation **owner) {
    CohWrPresentation *p;
    CohWrBudget *b;
    if (!owner || !(p=*owner)) return COH_INVALID;
    if (!p->stopped || p->objects || p->retired || p->pending || p->active) return COH_STATE;
    b=p->budget; coh_wr_mailbox_destroy(p->source);
    pthread_mutex_destroy(&p->mutex); free(p); unreserve(b,sizeof(*p));
    *owner=NULL; return COH_OK;
}
