#ifndef COH_WORLD_RENDER_H
#define COH_WORLD_RENDER_H
#include "../renderer/coh_renderer.h"
#ifdef __cplusplus
extern "C" {
#endif

#define COH_WR_ABI 1u
#define COH_WR_MAX_DRAWS 4096u
#define COH_WR_MAX_VERTICES 65536u
#define COH_WR_MAX_INDICES 196608u
#define COH_WR_MAX_MEMORY (96u * 1024u * 1024u)

/* These are caller attestations, NOT verification performed by this adapter.
 * The current catalog/graph/entity modules cannot yet produce ALL of them.
 * No networking, ACK, READY or LIVE transition exists in this module. */
enum {
    COH_WR_SCENE_CATALOG = 1u << 0,
    COH_WR_SCENE_TOPOLOGY = 1u << 1,
    COH_WR_SCENE_CHECKSUMS = 1u << 2,
    COH_WR_ASSET_IDENTITIES = 1u << 3,
    COH_WR_RENDER_SEMANTICS = 1u << 4,
    COH_WR_SELECTED_PLAYER = 1u << 5,
    COH_WR_FULL_CHARACTER = 1u << 6,
    COH_WR_FULL_GLOBAL_TAILS = 1u << 7,
    COH_WR_ACTOR_APPEARANCE = 1u << 8,
    COH_WR_ALL_PREREQUISITES = (1u << 9) - 1u
};
typedef enum {
    COH_WR_FIXTURE = 0, COH_WR_LOCAL_DEVELOPMENT_AUTH = 1,
    COH_WR_ENCRYPTED_AUTH = 2
} CohWrSource;
typedef struct {
    uint32_t abi, prerequisites;
    CohWrSource source;
    uint64_t session, snapshot, transaction;
    uint32_t scene_generation, asset_generation, entity_generation;
    uint32_t selected_dbid, player_entity;
    /* Hash identities are supplied by independently qualified upstream owners.
     * Not CRC authentication; this module only preserves/nonzero-checks them. */
    uint8_t catalog_sha256[32], asset_manifest_sha256[32], transaction_sha256[32];
} CohWrReceipt;
typedef struct {
    uint32_t dbid, entity_id, slot, generation, is_self;
    uint32_t appearance_generation, pose_generation, sequencer_state;
    float position[3], quaternion[4];
} CohWrActor;
typedef enum { COH_WR_WORLD_DRAW = 1, COH_WR_PLAYER_DRAW = 2 } CohWrDrawKind;
typedef struct {
    CohRenderGeometry geometry;
    CohRenderMaterial material; /* handles MUST be zero; logical IDs below */
    float world[16]; /* original source-layout affine column-major transform */
    uint64_t texture_id[3]; /* 0 = explicitly unbound, never an unresolved name */
    CohWrDrawKind kind;
    uint32_t actor_entity; /* zero for world; selected entity for player */
} CohWrDrawInput;
typedef struct {
    CohWrReceipt receipt;
    CohWrActor player;
    const CohWrDrawInput *draws;
    size_t draw_count;
} CohWrInput;
typedef struct CohWrBudget CohWrBudget;
typedef struct CohWrSnapshot CohWrSnapshot;
typedef struct CohWrMailbox CohWrMailbox;
typedef struct CohWrBindings CohWrBindings;
typedef struct { size_t limit, external_bytes, owned_bytes, peak_bytes, retired; } CohWrMemory;

/* Shared aggregate cap includes reserved catalog/old+candidate graph/scratch/
 * source-asset storage AND all adapter-owned snapshots, bindings and mailboxes.
 * Upstream must reserve its actual retained/peak bytes before preparation. The
 * allocator overhead and GPU/driver/server memory are outside this accounting.
 * Creation/preparation/collection/destruction are control-thread operations. */
CohStatus coh_wr_budget_create(size_t limit, size_t external_bytes, CohWrBudget **);
CohStatus coh_wr_budget_external(CohWrBudget *, size_t external_bytes);
CohWrMemory coh_wr_budget_memory(CohWrBudget *);
void coh_wr_collect(CohWrBudget *);
CohStatus coh_wr_budget_destroy(CohWrBudget *); /* STATE while any objects remain */

/* Full validation, bounded copy and allocation happen OFF the render thread.
 * Borrowed inputs must remain immutable through return. Output is unchanged on
 * failure. A fixture can never be relabeled as production after preparation.
 * No current production upstream is authorized to set missing prerequisites. */
CohStatus coh_wr_prepare(const CohWrInput *, CohWrBudget *, CohCancel, CohWrSnapshot **);
CohStatus coh_wr_prepare_fixture(const CohWrInput *, CohWrBudget *, CohCancel, CohWrSnapshot **);
const CohWrReceipt *coh_wr_receipt(const CohWrSnapshot *);
const CohWrActor *coh_wr_actor(const CohWrSnapshot *);
size_t coh_wr_draw_count(const CohWrSnapshot *);
CohStatus coh_wr_retain(CohWrSnapshot *);
/* Final release queues CPU retirement; it does NOT free/GL-delete on renderer.
 * The budget must outlive every object and the control thread must collect. */
void coh_wr_release(CohWrSnapshot *);

/* Short mutex section protects a single immutable scene+player generation.
 * Acquire/release perform no allocation, IO, asset decoding, or name scans.
 * Publish retains candidate. Older leased snapshots remain valid; old snapshots
 * are reclaimed only after their final lease AND control-thread collect.
 * Scene/asset/entity generations cannot decrease. Same scene retains catalog
 * and asset generation; same asset generation retains manifest digest; same
 * entity generation retains player entity/slot and nondecreasing pose/appearance.
 * Snapshot and transaction IDs must increase within the same session/source.
 * Clear explicitly ends session before another DBID/source/session is admitted.
 * Mailbox destruction requires callers to have stopped concurrent operations. */
CohStatus coh_wr_mailbox_create(CohWrBudget *, CohWrMailbox **);
CohStatus coh_wr_publish(CohWrMailbox *, CohWrSnapshot *);
CohStatus coh_wr_acquire(CohWrMailbox *, CohWrSnapshot **);
void coh_wr_mailbox_clear(CohWrMailbox *);
void coh_wr_mailbox_destroy(CohWrMailbox *);

/* Allocate both active/scratch numeric texture tables off-thread. Holds its own
 * snapshot lease. Bind/lost/draw are serialized on the GL owner thread. Resolver
 * returns an already prepared borrowed GPU name for EXACT logical ID + asset +
 * Surface generation, never decodes assets or silently substitutes identities.
 * All nonzero names must remain alive until last flush/Surface abandonment.
 * Bindings retain the CPU snapshot; do not destroy them until every submitted
 * borrowed CohRenderDraw span has flushed or been explicitly abandoned.
 * On bind failure the previous complete binding remains unchanged. */
typedef CohStatus (*CohWrTextureFn)(void *, uint64_t texture_id,
    uint32_t asset_generation, uint32_t surface_generation, uint32_t *handle);
CohStatus coh_wr_bindings_create(CohWrSnapshot *, CohWrBindings **);
CohStatus coh_wr_bind(CohWrBindings *, uint32_t surface_generation,
    CohWrTextureFn, void *, CohCancel);
void coh_wr_surface_lost(CohWrBindings *);
CohStatus coh_wr_draw(const CohWrBindings *, uint32_t surface_generation,
    size_t index, const float view[16], const float projection[16], CohRenderDraw *);
void coh_wr_bindings_destroy(CohWrBindings *); /* control thread after flush */

#ifdef __cplusplus
}
#endif
#endif
