#include "../coh_world_render.h"
#include "original_matrix.h"
#include <float.h>
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static atomic_long fail_after = ATOMIC_VAR_INIT(-1);
static atomic_uint allocations, frees;
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void *__real_realloc(void *,size_t);
void __real_free(void *);
static int fail_allocation(void) {
    long n=atomic_load(&fail_after);
    atomic_fetch_add(&allocations,1);
    if (n<0) return 0;
    if (n==0) return 1;
    atomic_fetch_sub(&fail_after,1); return 0;
}
void *__wrap_malloc(size_t n) { return fail_allocation()?NULL:__real_malloc(n); }
void *__wrap_calloc(size_t n,size_t z) { return fail_allocation()?NULL:__real_calloc(n,z); }
void *__wrap_realloc(void *p,size_t n) { return fail_allocation()?NULL:__real_realloc(p,n); }
void __wrap_free(void *p) { if (p) atomic_fetch_add(&frees,1); __real_free(p); }

static float ident[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static CohCancel never={0};
typedef struct {
    CohWrInput input;
    CohWrDrawInput draws[2];
    CohRenderVertex vertices[3];
    uint32_t indices[3];
} Fixture;
static void fixture(Fixture *f,uint64_t sequence) {
    unsigned i,j;
    memset(f,0,sizeof(*f));
    f->input.receipt=(CohWrReceipt){.abi=COH_WR_ABI,.source=COH_WR_FIXTURE,.session=55,
        .snapshot=sequence,.transaction=sequence,.scene_generation=1,.asset_generation=2,
        .entity_generation=3,.selected_dbid=42,.player_entity=71};
    f->input.player=(CohWrActor){.dbid=42,.entity_id=71,.slot=17,.generation=3,.is_self=1,
        .appearance_generation=4,.pose_generation=5,.sequencer_state=6,.quaternion={0,0,0,1}};
    f->input.draws=f->draws; f->input.draw_count=2;
    for(i=0;i<3;++i) {
        f->indices[i]=i; f->vertices[i].position[i]=1; f->vertices[i].normal[2]=1;
        for(j=0;j<4;++j) f->vertices[i].color[j]=1;
    }
    for(i=0;i<2;++i) {
        f->draws[i].geometry=(CohRenderGeometry){f->vertices,3,f->indices,3,100+i,2};
        f->draws[i].material=coh_renderer_default_material(COH_MAT_DUAL);
        memcpy(f->draws[i].world,ident,sizeof(ident));
        f->draws[i].texture_id[0]=23; f->draws[i].texture_id[1]=24;
        f->draws[i].kind=i?COH_WR_PLAYER_DRAW:COH_WR_WORLD_DRAW;
        f->draws[i].actor_entity=i?71:0;
    }
}
typedef struct { unsigned calls; uint64_t fail_id; } Resolver;
static CohStatus resolve(void *v,uint64_t id,uint32_t asset,uint32_t surface,uint32_t *out) {
    Resolver *r=v; ++r->calls;
    if (asset!=2 || id==r->fail_id) return COH_NOT_FOUND;
    *out=(uint32_t)id+100*surface; return COH_OK;
}
static int cancel_at(void *context) { int *n=context; return (*n)--==0; }
static uint32_t random_value=0xface1234u;
static uint32_t random_u32(void) { random_value=random_value*1664525u+1013904223u; return random_value; }

static void rejection_and_lifetime(void) {
    Fixture f; CohWrInput bad;
    CohWrBudget *b=NULL;
    CohWrSnapshot *s=NULL,*out=NULL,*lease=NULL;
    CohWrBindings *binding=NULL;
    CohWrMailbox *m=NULL;
    CohWrMemory initial,held;
    CohRenderDraw draw,before;
    Resolver r={0};
    unsigned i;
    CHECK(coh_wr_budget_create(1024*1024,4096,&b)==COH_OK);
    initial=coh_wr_budget_memory(b);
    fixture(&f,1);
    CHECK(coh_wr_prepare(&f.input,b,never,&out)==COH_STATE && out==NULL);
    bad=f.input; bad.receipt.source=COH_WR_LOCAL_DEVELOPMENT_AUTH;
    CHECK(coh_wr_prepare_fixture(&bad,b,never,&out)==COH_STATE);
    bad.receipt.prerequisites=COH_WR_ALL_PREREQUISITES;
    CHECK(coh_wr_prepare(&bad,b,never,&out)==COH_STATE);
    memset(bad.receipt.catalog_sha256,1,32); memset(bad.receipt.asset_manifest_sha256,2,32);
    memset(bad.receipt.transaction_sha256,3,32);
    for(i=0;i<9;++i) {
        bad.receipt.prerequisites=COH_WR_ALL_PREREQUISITES&~(1u<<i);
        CHECK(coh_wr_prepare(&bad,b,never,&out)==COH_STATE && out==NULL);
    }
    bad.receipt.prerequisites=COH_WR_ALL_PREREQUISITES;
    /* Deliberately fabricated receipt tests API admission ONLY. It does not
     * execute/authenticate a source server and is never a live-world result. */
    CHECK(coh_wr_prepare(&bad,b,never,&out)==COH_OK);
    CHECK(coh_wr_receipt(out)->source==COH_WR_LOCAL_DEVELOPMENT_AUTH);
    coh_wr_release(out); coh_wr_collect(b); out=NULL;
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
    CHECK(coh_wr_receipt(s)->source==COH_WR_FIXTURE && coh_wr_receipt(s)->prerequisites==0);
    CHECK(coh_wr_draw_count(s)==2 && coh_wr_actor(s)->dbid==42);
    CHECK(coh_wr_mailbox_create(b,&m)==COH_OK);
    CHECK(coh_wr_publish(m,s)==COH_OK);
    CHECK(coh_wr_publish(m,s)==COH_STATE);
    CHECK(coh_wr_acquire(m,&lease)==COH_OK && lease==s);
    held=coh_wr_budget_memory(b);
    atomic_store(&fail_after,0);
    CHECK(coh_wr_bindings_create(s,&binding)==COH_LIMIT && binding==NULL);
    atomic_store(&fail_after,-1);
    CHECK(coh_wr_budget_memory(b).owned_bytes==held.owned_bytes);
    CHECK(coh_wr_bindings_create(s,&binding)==COH_OK);
    memset(&draw,0x55,sizeof(draw)); before=draw;
    CHECK(coh_wr_draw(binding,1,0,ident,ident,&draw)==COH_STATE && !memcmp(&draw,&before,sizeof(draw)));
    CHECK(coh_wr_bind(binding,1,resolve,&r,never)==COH_OK);
    CHECK(coh_wr_draw(binding,1,0,ident,ident,&draw)==COH_OK);
    CHECK(draw.geometry.vertices!=f.vertices && draw.geometry.indices!=f.indices);
    CHECK(draw.material.textures[0].handle==123 && draw.geometry.vertices[0].position[0]==1);
    f.vertices[0].position[0]=99; f.indices[0]=99; f.input.player.dbid=999;
    CHECK(coh_wr_actor(s)->dbid==42 && draw.geometry.vertices[0].position[0]==1 && draw.geometry.indices[0]==0);
    { int n=2; CohCancel cancel={cancel_at,&n};
      CHECK(coh_wr_bind(binding,2,resolve,&r,cancel)==COH_CANCELLED);
      CHECK(coh_wr_draw(binding,1,0,ident,ident,&draw)==COH_OK && draw.material.textures[0].handle==123);
    }
    r.fail_id=24;
    CHECK(coh_wr_bind(binding,2,resolve,&r,never)==COH_NOT_FOUND);
    CHECK(coh_wr_draw(binding,1,0,ident,ident,&draw)==COH_OK && draw.material.textures[0].handle==123);
    CHECK(coh_wr_draw(binding,2,0,ident,ident,&draw)==COH_STATE);
    coh_wr_surface_lost(binding);
    CHECK(coh_wr_draw(binding,1,0,ident,ident,&draw)==COH_STATE);
    r.fail_id=0;
    CHECK(coh_wr_bind(binding,2,resolve,&r,never)==COH_OK);
    CHECK(coh_wr_draw(binding,2,0,ident,ident,&draw)==COH_OK && draw.material.textures[0].handle==223);
    CHECK(coh_wr_budget_destroy(b)==COH_STATE);
    held=coh_wr_budget_memory(b);
    CHECK(coh_wr_budget_external(b,held.limit-held.owned_bytes+1)==COH_LIMIT);
    CHECK(coh_wr_budget_memory(b).external_bytes==initial.external_bytes);
    coh_wr_release(s); coh_wr_mailbox_clear(m); coh_wr_release(lease);
    CHECK(coh_wr_budget_memory(b).retired==0); /* binding is the last lease */
    coh_wr_bindings_destroy(binding);
    CHECK(coh_wr_budget_memory(b).retired==1);
    coh_wr_mailbox_destroy(m); coh_wr_collect(b);
    CHECK(coh_wr_budget_memory(b).owned_bytes==initial.owned_bytes);
    CHECK(coh_wr_budget_destroy(b)==COH_OK);
}

static void rollback_tests(void) {
    Fixture f;
    CohWrBudget *b=NULL;
    CohWrSnapshot *s=NULL,*sentinel=(CohWrSnapshot *)(uintptr_t)1;
    CohWrMemory initial;
    unsigned i,successes=0;
    CHECK(coh_wr_budget_create(1024*1024,0,&b)==COH_OK);
    initial=coh_wr_budget_memory(b);
    for(i=0;i<30;++i) {
        CohStatus status;
        int n=(int)i;
        CohCancel cancel={cancel_at,&n}; fixture(&f,1); s=sentinel;
        status=coh_wr_prepare_fixture(&f.input,b,cancel,&s);
        if(status==COH_OK) { ++successes; coh_wr_release(s); coh_wr_collect(b); }
        else CHECK(status==COH_CANCELLED && s==sentinel);
        CHECK(coh_wr_budget_memory(b).owned_bytes==initial.owned_bytes);
    }
    CHECK(successes>0 && successes<30);
    fixture(&f,1); s=sentinel;
    atomic_store(&fail_after,0);
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_LIMIT && s==sentinel);
    atomic_store(&fail_after,-1);
    CHECK(coh_wr_budget_memory(b).owned_bytes==initial.owned_bytes);
    for(i=0;i<5000;++i) {
        CohStatus status; fixture(&f,1); s=sentinel;
        switch(random_u32()%10) {
        case 0: f.indices[0]=3+random_u32()%100; break;
        case 1: f.vertices[0].normal[0]=NAN; break;
        case 2: f.draws[0].geometry.generation=77; break;
        case 3: f.draws[0].material.alpha_ref=2; break;
        case 4: f.input.player.quaternion[0]=INFINITY; break;
        case 5: f.draws[1].actor_entity=100; break;
        case 6: f.input.player.is_self=0; break;
        case 7: f.draws[0].material.textures[0].handle=55; break;
        case 8: f.input.draw_count=COH_WR_MAX_DRAWS+1; break;
        case 9: f.draws[0].world[15]=0; break;
        }
        status=coh_wr_prepare_fixture(&f.input,b,never,&s);
        CHECK((status==COH_INVALID || status==COH_LIMIT) && s==sentinel);
        CHECK(coh_wr_budget_memory(b).owned_bytes==initial.owned_bytes);
    }
    fixture(&f,1); s=sentinel;
    CHECK(coh_wr_budget_external(b,initial.limit-initial.owned_bytes)==COH_OK);
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_LIMIT && s==sentinel);
    CHECK(coh_wr_budget_destroy(b)==COH_OK);
}

static void generation_and_capacity(void) {
    Fixture f;
    CohWrBudget *b=NULL;
    CohWrSnapshot *s=NULL,*newer=NULL,*old=NULL;
    CohWrMailbox *m=NULL;
    CohWrDrawInput *draws;
    unsigned i;
    CHECK(coh_wr_budget_create(COH_WR_MAX_MEMORY,32u*1024u*1024u,&b)==COH_OK);
    CHECK(coh_wr_mailbox_create(b,&m)==COH_OK);
    fixture(&f,1); CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
    CHECK(coh_wr_publish(m,s)==COH_OK); CHECK(coh_wr_acquire(m,&old)==COH_OK);
    fixture(&f,2); f.input.player.position[0]=10;
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&newer)==COH_OK);
    CHECK(coh_wr_publish(m,newer)==COH_OK);
    CHECK(coh_wr_actor(old)->position[0]==0 && coh_wr_actor(newer)->position[0]==10);
    coh_wr_release(s); coh_wr_release(newer);
    for(i=0;i<13;++i) {
        fixture(&f,3);
        switch(i) {
        case 0: f.input.receipt.session=100; break;
        case 1: f.input.receipt.transaction=2; break;
        case 2: f.input.receipt.asset_generation=1; f.draws[0].geometry.generation=f.draws[1].geometry.generation=1; break;
        case 3: f.input.receipt.entity_generation=2; f.input.player.generation=2; break;
        case 4: f.input.receipt.selected_dbid=55; f.input.player.dbid=55; break;
        case 5: f.input.receipt.snapshot=1; break;
        case 6: f.input.receipt.scene_generation=2; f.input.receipt.asset_generation=1;
            f.draws[0].geometry.generation=f.draws[1].geometry.generation=1; break;
        case 7: f.input.receipt.catalog_sha256[0]=1; break;
        case 8: f.input.receipt.asset_manifest_sha256[0]=1; break;
        case 9: f.input.receipt.player_entity=72; f.input.player.entity_id=72; f.draws[1].actor_entity=72; break;
        case 10: f.input.player.slot=18; break;
        case 11: f.input.player.appearance_generation=3; break;
        case 12: f.input.player.pose_generation=4; break;
        }
        CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
        CHECK(coh_wr_publish(m,s)==COH_STATE); coh_wr_release(s);
    }
    coh_wr_mailbox_clear(m); coh_wr_release(old); coh_wr_collect(b);
    fixture(&f,10); f.input.receipt.session=100;
    draws=calloc(COH_WR_MAX_DRAWS,sizeof(*draws)); CHECK(draws!=NULL);
    for(i=0;i<COH_WR_MAX_DRAWS;++i) draws[i]=f.draws[i&1];
    f.input.draws=draws; f.input.draw_count=COH_WR_MAX_DRAWS;
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
    CHECK(coh_wr_draw_count(s)==COH_WR_MAX_DRAWS);
    CHECK(coh_wr_publish(m,s)==COH_OK);
    CHECK(coh_wr_budget_memory(b).peak_bytes<=COH_WR_MAX_MEMORY);
    free(draws); coh_wr_release(s); coh_wr_mailbox_destroy(m); coh_wr_collect(b);
    CHECK(coh_wr_budget_destroy(b)==COH_OK);
}

typedef struct { unsigned compile,draw,destroy; } Backend;
static CohStatus compile_shader(void *p,CohMaterialFamily f,const char *v,const char *q,uint32_t *o) {
    Backend *b=p; (void)f; if(!v||!q) return COH_INVALID; *o=++b->compile; return COH_OK;
}
static void destroy_shader(void *p,uint32_t n) { Backend *b=p; if(n) ++b->destroy; }
static CohStatus bind_shader(void *p,uint32_t n,const CohRenderMaterial *m) { (void)p; return n&&m?COH_OK:COH_INVALID; }
static CohStatus draw_geometry(void *p,uint32_t n,const CohRenderDraw *d) {
    Backend *b=p; if(!n||!d) return COH_INVALID; ++b->draw; return COH_OK;
}
static void renderer_and_original_matrix(void) {
    Fixture f;
    CohWrBudget *b=NULL;
    CohWrSnapshot *s=NULL;
    CohWrBindings *bindings=NULL;
    CohRenderDraw draw,sentinel;
    Resolver r={0};
    Backend backend={0};
    CohRenderBackend functions={compile_shader,destroy_shader,bind_shader,draw_geometry,&backend};
    CohRenderer *renderer=NULL;
    CohRendererConfig config=coh_renderer_default_config();
    unsigned i,j,aa,ff;
    CHECK(coh_wr_budget_create(1024*1024,0,&b)==COH_OK);
    CHECK(coh_renderer_create(&config,&functions,&renderer)==COH_OK);
    for(i=0;i<512;++i) {
        float view[16], original[16];
        fixture(&f,1);
        for(j=0;j<16;++j) view[j]=((int)(random_u32()%256)-128)/16.f;
        for(j=0;j<12;++j) if(j%4!=3) f.draws[0].world[j]=((int)(random_u32()%256)-128)/16.f;
        f.draws[0].world[12]=2; f.draws[0].world[13]=3; f.draws[0].world[14]=4;
        CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
        CHECK(coh_wr_bindings_create(s,&bindings)==COH_OK);
        CHECK(coh_wr_bind(bindings,1,resolve,&r,never)==COH_OK);
        mulMat44Inline((const float (*)[4])view,(const float (*)[4])f.draws[0].world,(float (*)[4])original);
        CHECK(coh_wr_draw(bindings,1,0,view,ident,&draw)==COH_OK);
        CHECK(!memcmp(original,draw.model_view,sizeof(original)));
        coh_wr_bindings_destroy(bindings); coh_wr_release(s); coh_wr_collect(b);
    }
    fixture(&f,1);
    f.draws[0].world[0]=2;
    CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
    CHECK(coh_wr_bindings_create(s,&bindings)==COH_OK);
    CHECK(coh_wr_bind(bindings,1,resolve,&r,never)==COH_OK);
    coh_renderer_surface_lost(renderer,1,0);
    aa=atomic_load(&allocations); ff=atomic_load(&frees);
    CHECK(coh_renderer_begin(renderer,1)==COH_OK);
    for(i=0;i<2;++i) {
        CHECK(coh_wr_draw(bindings,1,i,ident,ident,&draw)==COH_OK);
        CHECK(coh_renderer_submit(renderer,&draw)==COH_OK);
    }
    CHECK(coh_renderer_flush(renderer,never)==COH_OK && backend.draw==2);
    CHECK(atomic_load(&allocations)==aa && atomic_load(&frees)==ff);
    sentinel=draw;
    { float overflow[16]; for(i=0;i<16;++i) overflow[i]=FLT_MAX;
      CHECK(coh_wr_draw(bindings,1,0,overflow,ident,&draw)==COH_INVALID && !memcmp(&draw,&sentinel,sizeof(draw)));
      overflow[0]=INFINITY;
      CHECK(coh_wr_draw(bindings,1,0,overflow,ident,&draw)==COH_INVALID);
    }
    draw=sentinel;
    coh_wr_surface_lost(bindings); coh_renderer_surface_lost(renderer,2,0);
    CHECK(coh_wr_draw(bindings,2,0,ident,ident,&draw)==COH_STATE && !memcmp(&draw,&sentinel,sizeof(draw)));
    CHECK(coh_wr_bind(bindings,2,resolve,&r,never)==COH_OK);
    CHECK(coh_wr_draw(bindings,2,0,ident,ident,&draw)==COH_OK);
    coh_wr_bindings_destroy(bindings); coh_wr_release(s); coh_wr_collect(b);
    coh_renderer_destroy(renderer); CHECK(coh_wr_budget_destroy(b)==COH_OK);
}

typedef struct { CohWrMailbox *mailbox; atomic_uint failed,reads; atomic_int stop; } Concurrent;
static void *read_thread(void *p) {
    Concurrent *c=p;
    uint64_t last=0;
    while(!atomic_load(&c->stop)) {
        CohWrSnapshot *s=NULL;
        CohStatus status=coh_wr_acquire(c->mailbox,&s);
        if(status==COH_OK) {
            const CohWrReceipt *r=coh_wr_receipt(s);
            const CohWrActor *a=coh_wr_actor(s);
            if(r->snapshot<last || (uint64_t)a->position[0]!=r->snapshot || a->dbid!=r->selected_dbid)
                atomic_store(&c->failed,1);
            last=r->snapshot; atomic_fetch_add(&c->reads,1); coh_wr_release(s);
        } else if(status!=COH_NOT_FOUND) atomic_store(&c->failed,1);
    }
    return NULL;
}
static void concurrent_publication(void) {
    CohWrBudget *b=NULL;
    CohWrMailbox *m=NULL;
    CohWrSnapshot *s=NULL;
    Fixture f;
    Concurrent c;
    pthread_t threads[3];
    unsigned i;
    CHECK(coh_wr_budget_create(8*1024*1024,0,&b)==COH_OK);
    CHECK(coh_wr_mailbox_create(b,&m)==COH_OK);
    c.mailbox=m; atomic_init(&c.failed,0); atomic_init(&c.reads,0); atomic_init(&c.stop,0);
    for(i=0;i<3;++i) CHECK(pthread_create(threads+i,NULL,read_thread,&c)==0);
    for(i=1;i<=2000;++i) {
        fixture(&f,i); f.input.player.position[0]=(float)i;
        CHECK(coh_wr_prepare_fixture(&f.input,b,never,&s)==COH_OK);
        CHECK(coh_wr_publish(m,s)==COH_OK); coh_wr_release(s);
        if(i%10==0) coh_wr_collect(b);
    }
    atomic_store(&c.stop,1);
    for(i=0;i<3;++i) CHECK(pthread_join(threads[i],NULL)==0);
    CHECK(!atomic_load(&c.failed) && atomic_load(&c.reads)>0);
    coh_wr_mailbox_destroy(m); coh_wr_collect(b); CHECK(coh_wr_budget_destroy(b)==COH_OK);
}

int main(void) {
    rejection_and_lifetime(); rollback_tests(); generation_and_capacity();
    renderer_and_original_matrix(); concurrent_publication();
    printf("{\"passed\":true,\"checks\":%u,\"original_matrix_cases\":512,\"bounded_mutations\":5000,"
        "\"published_generations\":2000,\"concurrent_readers\":3,\"max_draws_tested\":4096,"
        "\"render_allocations\":0,\"render_frees\":0,\"fixture_only\":true,\"authentic_world_entry\":false}\n",checks);
    return 0;
}
