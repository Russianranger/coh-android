#include "../coh_wr_presentation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while (0)
static const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static CohCancel never={0};
typedef struct { unsigned compile,destroy,bind,draw,hold,drop,resolve; } Calls;
static CohStatus compile(void *v,CohMaterialFamily family,const char *vs,const char *fs,uint32_t *out) {
    Calls *c=v; (void)family; CHECK(vs && fs); *out=++c->compile; return COH_OK;
}
static void destroy(void *v,uint32_t program) { (void)program; ++((Calls *)v)->destroy; }
static CohStatus bind(void *v,uint32_t program,const CohRenderMaterial *m) {
    (void)program; (void)m; ++((Calls *)v)->bind; return COH_OK;
}
static CohStatus draw(void *v,uint32_t program,const CohRenderDraw *d) {
    (void)program; CHECK(d->geometry.vertex_count==3); ++((Calls *)v)->draw; return COH_OK;
}
static CohStatus hold(void *v) { ++((Calls *)v)->hold; return COH_OK; }
static void drop(void *v) { ++((Calls *)v)->drop; }
static CohStatus resolve(void *v,uint64_t id,uint32_t asset,uint32_t surface,uint32_t *out) {
    CHECK(id==23 && asset==2 && surface); ++((Calls *)v)->resolve; *out=123; return COH_OK;
}
static void same_renderers(CohRenderer *a,CohRenderer *b,uint32_t surface) {
    CohRendererStats x=coh_renderer_stats(a),y=coh_renderer_stats(b);
    CHECK(x.surface_generation==surface && y.surface_generation==1);
    CHECK(!x.queued && !y.queued && !y.submitted && !y.drawn && !y.compiles);
}
int main(void) {
    Calls calls={0},other={0},saved;
    CohWrBudget *budget=NULL;
    CohWrSnapshot *snapshot=NULL;
    CohWrPreparedFrame *frame=NULL;
    CohWrPresentation *owner=NULL,*fresh=NULL;
    CohRenderer *a=NULL,*b=NULL;
    CohRendererConfig config=coh_renderer_default_config();
    CohRenderBackend backend={compile,destroy,bind,draw,&calls},alternate={compile,destroy,bind,draw,&other};
    CohWrPresentationResources resources={&calls,hold,drop,resolve};
    CohWrPresentationResult result={0},sentinel;
    CohRenderVertex vertices[3]={0}; uint32_t indices[3]={0,1,2};
    CohWrDrawInput draws[2]={0};
    CohWrInput input={0};
    for (unsigned i=0;i<3;++i) { vertices[i].position[i]=1; vertices[i].normal[2]=1; }
    input.receipt=(CohWrReceipt){.abi=COH_WR_ABI,.source=COH_WR_FIXTURE,.session=55,
        .snapshot=1,.transaction=1,.scene_generation=1,.asset_generation=2,
        .entity_generation=3,.selected_dbid=42,.player_entity=71};
    input.player=(CohWrActor){.dbid=42,.entity_id=71,.slot=17,.generation=3,.is_self=1,
        .appearance_generation=4,.pose_generation=5,.quaternion={0,0,0,1}};
    input.draws=draws; input.draw_count=2;
    for (unsigned i=0;i<2;++i) {
        draws[i].geometry=(CohRenderGeometry){vertices,3,indices,3,100+i,2};
        draws[i].material=coh_renderer_default_material(COH_MAT_MULTIPLY);
        memcpy(draws[i].world,identity,sizeof(identity)); draws[i].texture_id[0]=23;
        draws[i].kind=i?COH_WR_PLAYER_DRAW:COH_WR_WORLD_DRAW; draws[i].actor_entity=i?71:0;
    }
    CHECK(coh_wr_budget_create(1024*1024,4096,&budget)==COH_OK);
    CHECK(coh_wr_prepare_fixture(&input,budget,never,&snapshot)==COH_OK);
    CHECK(coh_renderer_create(&config,&backend,&a)==COH_OK);
    CHECK(coh_renderer_create(&config,&alternate,&b)==COH_OK);
    coh_renderer_surface_lost(a,1,0); coh_renderer_surface_lost(b,1,0);
    CHECK(coh_wr_presentation_create_fixture(budget,&config,&owner)==COH_OK);
    CHECK(coh_wr_presentation_prepare(owner,snapshot,1,NULL,2,identity,identity,&resources,never,&frame)==COH_OK);
    CHECK(coh_wr_presentation_publish(owner,frame)==COH_OK);
    coh_wr_presentation_release(frame); frame=NULL;
    CHECK(coh_wr_presentation_resume(owner,a,1)==COH_OK);
    CHECK(coh_wr_presentation_render(owner,a,never,&result)==COH_OK && result.adopted && result.draws==2);
    CHECK(calls.hold==1 && !calls.drop);
    saved=calls;
    size_t bytes=coh_wr_budget_memory(budget).owned_bytes;
    memset(&result,0x57,sizeof(result)); sentinel=result;
    CHECK(coh_wr_presentation_resume(owner,b,1)==COH_STATE);
    CHECK(coh_wr_presentation_pause(owner,b)==COH_STATE);
    CHECK(coh_wr_presentation_render(owner,b,never,&result)==COH_STATE);
    CHECK(!memcmp(&result,&sentinel,sizeof(result)));
    CHECK(coh_wr_presentation_surface_lost(owner,b,2,1)==COH_STATE);
    CHECK(coh_wr_presentation_stop(owner,b,1)==COH_STATE);
    coh_wr_presentation_collect(owner);
    CHECK(!memcmp(&calls,&saved,sizeof(calls)) && !memcmp(&other,&(Calls){0},sizeof(other)));
    CHECK(coh_wr_budget_memory(budget).owned_bytes==bytes);
    same_renderers(a,b,1);
    /* Wrong-owner refusals preserve the active frame and correct lifecycle. */
    CHECK(coh_wr_presentation_render(owner,a,never,&result)==COH_OK && result.publication==1 && result.draws==2);
    CHECK(coh_wr_presentation_pause(owner,a)==COH_OK);
    CHECK(coh_wr_presentation_resume(owner,a,1)==COH_OK);
    CHECK(coh_wr_presentation_surface_lost(owner,a,2,1)==COH_OK);
    CHECK(coh_wr_presentation_resume(owner,a,2)==COH_OK);
    CHECK(coh_wr_presentation_render(owner,a,never,&result)==COH_OK && result.surface_generation==2 && result.draws==2);
    same_renderers(a,b,2);
    CHECK(coh_wr_presentation_stop(owner,a,1)==COH_OK);
    coh_wr_presentation_collect(owner);
    CHECK(calls.hold==1 && calls.drop==1);
    CHECK(coh_wr_presentation_destroy(&owner)==COH_OK && !owner);
    /* Failed initial admission does not latch A; first successful loss binds B. */
    CHECK(coh_wr_presentation_create_fixture(budget,&config,&fresh)==COH_OK);
    CHECK(coh_wr_presentation_resume(fresh,a,1)==COH_STATE);
    CHECK(coh_wr_presentation_surface_lost(fresh,b,2,0)==COH_OK);
    CHECK(coh_wr_presentation_resume(fresh,a,2)==COH_STATE);
    CHECK(coh_wr_presentation_resume(fresh,b,2)==COH_OK);
    CHECK(coh_wr_presentation_stop(fresh,b,0)==COH_OK);
    CHECK(coh_wr_presentation_destroy(&fresh)==COH_OK);
    /* Pause can be the first successful lifecycle call too. */
    CHECK(coh_wr_presentation_create_fixture(budget,&config,&fresh)==COH_OK);
    CHECK(coh_wr_presentation_pause(fresh,a)==COH_OK);
    CHECK(coh_wr_presentation_stop(fresh,b,0)==COH_STATE);
    CHECK(coh_wr_presentation_stop(fresh,a,0)==COH_OK);
    CHECK(coh_wr_presentation_destroy(&fresh)==COH_OK);
    coh_wr_release(snapshot); coh_wr_collect(budget);
    coh_renderer_destroy(a); coh_renderer_destroy(b);
    CHECK(coh_wr_budget_destroy(budget)==COH_OK);
    printf("{\"checks\":%u,\"renderer_identity\":true,\"draws\":%u,\"resource_holds\":%u,\"resource_drops\":%u,\"fixture_only\":true,\"gles_executed\":false}\n",
        checks,calls.draw,calls.hold,calls.drop);
    return 0;
}
