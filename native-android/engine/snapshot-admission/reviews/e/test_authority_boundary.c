#include "../../../world-render-adapter/coh_world_render.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "%d: %s\n", __LINE__, #x); exit(1); } } while (0)

/* Independent mechanics experiment. Every receipt/triangle below is invented.
 * Acceptance here MUST NOT be read as real-world, source, or actor authority. */
int main(void) {
    CohWrBudget *budget = NULL;
    CohWrMailbox *mailbox = NULL;
    CohWrSnapshot *first = NULL, *candidate = NULL, *lease = NULL;
    CohWrSnapshot *sentinel = (CohWrSnapshot *)(uintptr_t)1;
    CohRenderVertex vertices[3] = {0};
    uint32_t indices[3] = {0,1,2};
    CohWrDrawInput draws[2] = {0};
    CohWrInput input = {0};
    CohCancel never = {0};
    size_t i;
    input.receipt = (CohWrReceipt){.abi=COH_WR_ABI, .source=COH_WR_LOCAL_DEVELOPMENT_AUTH,
        .session=1, .snapshot=1, .transaction=1, .scene_generation=1, .asset_generation=1,
        .entity_generation=1, .selected_dbid=42, .player_entity=71,
        .prerequisites=COH_WR_ALL_PREREQUISITES};
    memset(input.receipt.catalog_sha256,1,32);
    memset(input.receipt.asset_manifest_sha256,2,32);
    memset(input.receipt.transaction_sha256,3,32);
    input.player=(CohWrActor){.dbid=42,.entity_id=71,.slot=9,.generation=1,.is_self=1,
        .appearance_generation=1,.pose_generation=1,.quaternion={0,0,0,1},
        .position={1000,2000,3000}};
    for (i=0;i<2;++i) {
        draws[i].geometry=(CohRenderGeometry){vertices,3,indices,3,123,1};
        draws[i].material=coh_renderer_default_material(COH_MAT_DUAL);
        draws[i].world[0]=draws[i].world[5]=draws[i].world[10]=draws[i].world[15]=1;
        draws[i].kind=i?COH_WR_PLAYER_DRAW:COH_WR_WORLD_DRAW;
        draws[i].actor_entity=i?71:0;
    }
    input.draws=draws; input.draw_count=2;
    CHECK(coh_wr_budget_create(1024*1024,0,&budget)==COH_OK);
    CHECK(coh_wr_mailbox_create(budget,&mailbox)==COH_OK);
    /* Actor position and player draw matrix disagree: attestation validation
     * deliberately cannot verify this upstream semantic relationship. */
    CHECK(coh_wr_prepare(&input,budget,never,&first)==COH_OK);
    CHECK(coh_wr_actor(first)->position[0]==1000);
    CHECK(coh_wr_publish(mailbox,first)==COH_OK);
    CHECK(coh_wr_acquire(mailbox,&lease)==COH_OK && lease==first);
    input.receipt.snapshot=2; input.receipt.transaction=2;
    for (i=0;i<9;++i) {
        size_t owned=coh_wr_budget_memory(budget).owned_bytes;
        input.receipt.prerequisites=COH_WR_ALL_PREREQUISITES & ~(1u<<i);
        candidate=sentinel;
        CHECK(coh_wr_prepare(&input,budget,never,&candidate)==COH_STATE);
        CHECK(candidate==sentinel && coh_wr_budget_memory(budget).owned_bytes==owned);
    }
    input.receipt.prerequisites=COH_WR_ALL_PREREQUISITES;
    input.receipt.catalog_sha256[0]=9;
    CHECK(coh_wr_prepare(&input,budget,never,&candidate)==COH_OK);
    CHECK(coh_wr_publish(mailbox,candidate)==COH_STATE);
    CHECK(coh_wr_actor(lease)->position[0]==1000);
    coh_wr_release(candidate); candidate=NULL;
    CHECK(coh_wr_acquire(mailbox,&candidate)==COH_OK && candidate==first);
    coh_wr_release(candidate); coh_wr_release(lease); coh_wr_release(first);
    coh_wr_mailbox_clear(mailbox); coh_wr_mailbox_destroy(mailbox); coh_wr_collect(budget);
    CHECK(coh_wr_budget_destroy(budget)==COH_OK);
    printf("{\"checks\":%u,\"invented_receipts_only\":true,\"pose_relation_verified_by_adapter\":false,\"world_authority\":false}\n",checks);
    return 0;
}
