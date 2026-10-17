typedef struct {
    Resolver resolver;
    unsigned holds,drops,held,fail_hold;
    CohWrPresentation *publish_owner;
    CohWrPreparedFrame *publish_during_bind;
} PresentationResources;
static CohStatus presentation_hold(void *v) {
    PresentationResources *r=v;
    ++r->holds;
    if (r->fail_hold) return COH_STATE;
    ++r->held; return COH_OK;
}
static void presentation_drop(void *v) {
    PresentationResources *r=v;
    CHECK(r->held>0); --r->held; ++r->drops;
}
static CohStatus presentation_resolve(void *v,uint64_t id,uint32_t asset,uint32_t surface,uint32_t *out) {
    PresentationResources *r=v;
    if (!r->held) return COH_STATE;
    if (r->publish_during_bind) {
        CohWrPreparedFrame *f=r->publish_during_bind;
        r->publish_during_bind=NULL;
        CHECK(coh_wr_presentation_publish(r->publish_owner,f)==COH_OK);
        coh_wr_presentation_release(f);
    }
    return resolve(&r->resolver,id,asset,surface,out);
}
typedef struct { Backend backend; unsigned fail_draw; } PresentationBackend;
static CohStatus presentation_backend_draw(void *v,uint32_t n,const CohRenderDraw *d) {
    PresentationBackend *b=v;
    CohStatus status=draw_geometry(&b->backend,n,d);
    return b->fail_draw && b->backend.draw==b->fail_draw?COH_STATE:status;
}
static void presentation_lifecycle(void) {
    Fixture f;
    CohWrBudget *b=NULL;
    CohWrSnapshot *s=NULL,*next=NULL;
    CohWrPresentation *p=NULL,*production=NULL;
    CohWrPreparedFrame *one=NULL,*two=NULL,*three=NULL,*sentinel=NULL;
    PresentationResources old={0},candidate={0},latest={0};
    CohWrPresentationResources old_ops={&old,presentation_hold,presentation_drop,presentation_resolve};
    CohWrPresentationResources candidate_ops={&candidate,presentation_hold,presentation_drop,presentation_resolve};
    CohWrPresentationResources latest_ops={&latest,presentation_hold,presentation_drop,presentation_resolve};
    PresentationBackend backend={0};
    CohRenderBackend ops={compile_shader,destroy_shader,bind_shader,presentation_backend_draw,&backend};
    CohRendererConfig config=coh_renderer_default_config();
    CohRenderer *renderer=NULL;
    CohWrPresentationResult result,before_result;
    CohWrMemory baseline;
    unsigned aa,ff,drawn,drops;
    config.max_draws=1; /* Exercise actual multi-batch renderer consumption. */
    fixture(&f,1);
    CHECK(coh_wr_budget_create(1024*1024,16384,&b)==COH_OK);
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
    CHECK(coh_renderer_create(&config,&ops,&renderer)==COH_OK);
    CHECK(coh_wr_presentation_create(b,&config,&production)==COH_OK);
    CHECK(coh_wr_presentation_prepare(production,s,1,NULL,2,ident,ident,&old_ops,never,&one)==COH_STATE && !one);
    CHECK(coh_wr_presentation_destroy(&production)==COH_STATE && production);
    CHECK(coh_wr_presentation_stop(production,renderer,0)==COH_OK);
    CHECK(coh_wr_presentation_destroy(&production)==COH_OK && !production);
    CHECK(coh_wr_presentation_create_fixture(b,&config,&p)==COH_OK);
    { CohWrPresentation *saved=p;
      CHECK(coh_wr_presentation_create_fixture(b,&config,&p)==COH_STATE && p==saved);
    }
    baseline=coh_wr_budget_memory(b);
    for (long i=0;i<3;++i) {
        atomic_store(&fail_after,i);
        CHECK(coh_wr_presentation_prepare(p,s,1,NULL,2,ident,ident,&old_ops,never,&one)==COH_LIMIT && !one);
        atomic_store(&fail_after,-1);
        CHECK(coh_wr_budget_memory(b).owned_bytes==baseline.owned_bytes);
    }
    candidate.fail_hold=1;
    CHECK(coh_wr_presentation_prepare(p,s,1,NULL,2,ident,ident,&candidate_ops,never,&one)==COH_STATE && !one);
    CHECK(!candidate.held && !candidate.drops);
    candidate.fail_hold=0;
    CHECK(coh_wr_budget_memory(b).owned_bytes==baseline.owned_bytes);
    {
        int n=0; CohCancel cancel={cancel_at,&n};
        CHECK(coh_wr_presentation_prepare(p,s,1,NULL,2,ident,ident,&old_ops,cancel,&one)==COH_CANCELLED && !one);
    }
    CHECK(coh_wr_presentation_prepare(p,s,1,NULL,2,ident,ident,&old_ops,never,&one)==COH_OK);
    { CohWrPreparedFrame *saved=one;
      CHECK(coh_wr_presentation_prepare(p,s,2,NULL,2,ident,ident,&old_ops,never,&one)==COH_STATE && one==saved);
    }
    CHECK(old.held==1);
    CHECK(coh_wr_presentation_publish(p,one)==COH_OK);
    CHECK(coh_wr_presentation_publish(p,one)==COH_STATE);
    coh_wr_presentation_release(one); one=NULL;
    memset(&result,0x57,sizeof(result)); before_result=result;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_STATE && !memcmp(&result,&before_result,sizeof(result)));
    coh_renderer_surface_lost(renderer,1,0);
    CHECK(coh_wr_presentation_resume(p,renderer,2)==COH_STATE);
    CHECK(coh_wr_presentation_resume(p,renderer,1)==COH_OK);
    aa=atomic_load(&allocations); ff=atomic_load(&frees);
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK);
    CHECK(result.adopted && result.publication==1 && result.snapshot==1 && result.draws==2 && result.batches==2);
    CHECK(result.source==COH_WR_FIXTURE && !result.fallback && old.held==1);
    CHECK(atomic_load(&allocations)==aa && atomic_load(&frees)==ff);
    /* Same authoritative snapshot, new camera/visibility frame is a different
     * publication; source packet counters are never fabricated to move camera. */
    CHECK(coh_wr_presentation_prepare(p,s,2,NULL,2,ident,ident,&candidate_ops,never,&two)==COH_OK);
    candidate.resolver.fail_id=24;
    CHECK(coh_wr_presentation_publish(p,two)==COH_OK);
    coh_wr_presentation_release(two); two=NULL;
    aa=atomic_load(&allocations); ff=atomic_load(&frees);
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK);
    CHECK(result.candidate_status==COH_NOT_FOUND && result.fallback && !result.adopted && result.publication==1);
    CHECK(result.draws==2 && old.held==1 && candidate.held==1);
    CHECK(atomic_load(&allocations)==aa && atomic_load(&frees)==ff);
    /* Failed second batch leaves first batch's pixels irrecoverable, but keeps
     * old CPU generation and clears every borrowed renderer span. */
    candidate.resolver.fail_id=0;
    backend.fail_draw=backend.backend.draw+2;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_STATE);
    CHECK(!result.adopted && result.candidate_status==COH_STATE && result.batches==1 && !coh_renderer_stats(renderer).queued);
    backend.fail_draw=0; candidate.resolver.fail_id=24;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK && result.publication==1 && result.fallback);
    candidate.resolver.fail_id=0;
    CHECK(coh_wr_presentation_pause(p,renderer)==COH_OK);
    drawn=backend.backend.draw;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_STATE && backend.backend.draw==drawn);
    CHECK(coh_wr_presentation_resume(p,renderer,1)==COH_OK);
    /* A newly published generation replaces pending ownership while an older
     * candidate is leased inside its resolver; no callback/free can retire it. */
    fixture(&f,2);
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&next)==COH_OK);
    CHECK(coh_wr_presentation_prepare(p,next,3,NULL,2,ident,ident,&latest_ops,never,&three)==COH_OK);
    candidate.publish_owner=p; candidate.publish_during_bind=three; three=NULL;
    aa=atomic_load(&allocations); ff=atomic_load(&frees); drops=old.drops;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK && result.publication==2 && result.adopted);
    CHECK(old.drops==drops && old.held==1 && candidate.held==1 && latest.held==1);
    CHECK(atomic_load(&allocations)==aa && atomic_load(&frees)==ff);
    coh_wr_presentation_collect(p);
    CHECK(old.held==0 && old.drops==1);
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK && result.publication==3 && result.snapshot==2);
    coh_wr_presentation_collect(p); CHECK(candidate.held==0 && candidate.drops==1);
    /* Regressing immutable source state is refused even with a larger camera
     * publication counter; the last valid active bundle remains rendered. */
    CHECK(coh_wr_presentation_prepare(p,s,4,NULL,2,ident,ident,&old_ops,never,&one)==COH_OK);
    CHECK(coh_wr_presentation_publish(p,one)==COH_STATE);
    coh_wr_presentation_release(one); one=NULL;
    CHECK(coh_wr_presentation_surface_lost(p,renderer,1,0)==COH_STATE);
    aa=atomic_load(&allocations); ff=atomic_load(&frees);
    CHECK(coh_wr_presentation_surface_lost(p,renderer,2,0)==COH_OK);
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_STATE);
    CHECK(coh_wr_presentation_resume(p,renderer,1)==COH_STATE);
    CHECK(coh_wr_presentation_resume(p,renderer,2)==COH_OK);
    latest.resolver.fail_id=23;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_NOT_FOUND && !result.draws);
    latest.resolver.fail_id=0;
    CHECK(coh_wr_presentation_render(p,renderer,never,&result)==COH_OK && result.publication==3 && result.surface_generation==2);
    CHECK(atomic_load(&allocations)==aa && atomic_load(&frees)==ff);
    CHECK(coh_wr_presentation_prepare(p,next,5,NULL,2,ident,ident,&latest_ops,never,&sentinel)==COH_OK);
    CHECK(coh_wr_presentation_stop(p,renderer,1)==COH_OK);
    CHECK(coh_wr_presentation_resume(p,renderer,2)==COH_STATE);
    CHECK(coh_wr_presentation_publish(p,sentinel)==COH_STATE);
    CHECK(coh_wr_presentation_prepare(p,next,6,NULL,2,ident,ident,&latest_ops,never,&one)==COH_STATE && !one);
    coh_wr_release(s); coh_wr_release(next);
    coh_wr_presentation_collect(p);
    CHECK(latest.held==1); /* caller-owned prepared lease keeps owner alive */
    CHECK(coh_wr_presentation_destroy(&p)==COH_STATE && p);
    coh_wr_presentation_release(sentinel); coh_wr_presentation_collect(p);
    CHECK(!latest.held && old.holds==old.drops && latest.holds==latest.drops);
    CHECK(coh_wr_presentation_destroy(&p)==COH_OK && !p);
    coh_renderer_destroy(renderer);
    CHECK(coh_wr_budget_destroy(b)==COH_OK);
}
typedef struct {
    CohWrPresentation *owner;
    CohRenderer *renderer;
    atomic_uint failed,observed;
    atomic_int stop;
    pthread_mutex_t mutex;
    pthread_cond_t condition;
} PresentationRace;
static void *presentation_consumer(void *v) {
    PresentationRace *race=v;
    uint64_t previous=0;
    while (!atomic_load(&race->stop)) {
        CohWrPresentationResult result={0};
        CohStatus status=coh_wr_presentation_render(race->owner,race->renderer,never,&result);
        if (status==COH_NOT_FOUND && !previous) continue;
        if (status!=COH_OK || result.publication<previous || result.source!=COH_WR_FIXTURE ||
            result.snapshot!=1 || result.draws!=2 || result.batches!=2) atomic_store(&race->failed,1);
        previous=result.publication;
        atomic_store(&race->observed,(unsigned)previous);
        pthread_mutex_lock(&race->mutex);
        pthread_cond_broadcast(&race->condition);
        pthread_mutex_unlock(&race->mutex);
    }
    return NULL;
}
static int presentation_wait(PresentationRace *race,unsigned target) {
    struct timespec deadline={time(NULL)+10,0};
    int status=0;
    pthread_mutex_lock(&race->mutex);
    while (atomic_load(&race->observed)<target && !status)
        status=pthread_cond_timedwait(&race->condition,&race->mutex,&deadline);
    pthread_mutex_unlock(&race->mutex);
    return status==0 && !atomic_load(&race->failed);
}
static void presentation_concurrent_consumer(void) {
    Fixture f;
    CohWrBudget *budget=NULL;
    CohWrSnapshot *snapshot=NULL;
    CohWrPresentation *owner=NULL;
    PresentationResources resources[512]={0};
    Backend backend={0};
    CohRenderBackend operations={compile_shader,destroy_shader,bind_shader,draw_geometry,&backend};
    CohRendererConfig config=coh_renderer_default_config();
    CohRenderer *renderer=NULL;
    pthread_t thread;
    PresentationRace race={0};
    config.max_draws=1;
    fixture(&f,1);
    CHECK(coh_wr_budget_create(4*1024*1024,sizeof(resources),&budget)==COH_OK);
    CHECK(coh_wr_prepare_fixture(&f.input,budget,never,&snapshot)==COH_OK);
    CHECK(coh_wr_presentation_create_fixture(budget,&config,&owner)==COH_OK);
    CHECK(coh_renderer_create(&config,&operations,&renderer)==COH_OK);
    coh_renderer_surface_lost(renderer,1,0);
    CHECK(coh_wr_presentation_resume(owner,renderer,1)==COH_OK);
    race.owner=owner; race.renderer=renderer;
    CHECK(!pthread_mutex_init(&race.mutex,NULL));
    CHECK(!pthread_cond_init(&race.condition,NULL));
    CHECK(!pthread_create(&thread,NULL,presentation_consumer,&race));
    for (unsigned i=0;i<512;++i) {
        CohWrPreparedFrame *prepared=NULL;
        CohWrPresentationResources source={resources+i,presentation_hold,presentation_drop,presentation_resolve};
        CHECK(coh_wr_presentation_prepare(owner,snapshot,i+1,NULL,2,ident,ident,&source,never,&prepared)==COH_OK);
        CHECK(coh_wr_presentation_publish(owner,prepared)==COH_OK);
        coh_wr_presentation_release(prepared);
        if (i%16==15) coh_wr_presentation_collect(owner);
        if (i%128==127) CHECK(presentation_wait(&race,i+1));
    }
    atomic_store(&race.stop,1);
    CHECK(!pthread_join(thread,NULL));
    CHECK(!atomic_load(&race.failed) && atomic_load(&race.observed)==512);
    CHECK(coh_wr_presentation_stop(owner,renderer,1)==COH_OK);
    coh_wr_release(snapshot); coh_wr_presentation_collect(owner);
    for (unsigned i=0;i<512;++i) CHECK(!resources[i].held && resources[i].holds==1 && resources[i].drops==1);
    CHECK(coh_wr_presentation_destroy(&owner)==COH_OK);
    CHECK(!pthread_cond_destroy(&race.condition)); CHECK(!pthread_mutex_destroy(&race.mutex));
    coh_renderer_destroy(renderer);
    CHECK(coh_wr_budget_destroy(budget)==COH_OK);
}
