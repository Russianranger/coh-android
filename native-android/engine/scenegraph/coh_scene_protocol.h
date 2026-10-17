#ifndef COH_SCENE_PROTOCOL_H
#define COH_SCENE_PROTOCOL_H
#include "coh_catalog_seed.h"
#include "coh_runtime_graph_owner.h"
#include "../scenecatalog/coh_catalog_snapshot.h"
#define COH_SCENE_PROTOCOL_LOCAL_SCRATCH_BYTES (64u*1024u)
typedef struct CohSceneProtocol CohSceneProtocol;
typedef struct {
 CohRuntimeGroupsWitness *witness;
 const CohRuntimeGroupsWitnessBinding *binding;
 const CohRepReader *reader;
} CohSceneProtocolGroups;
typedef struct {
 uint32_t generation,graph_generation,catalog_generation,asset_generation,snapshot_generation;
 uint32_t groups_compatibility_checked;
 uint8_t catalog_sha256[32],snapshot_sha256[32],source_sha256[32],run_sha256[32],inventory_sha256[32];
 CohRuntimeGroupsWitnessBinding groups;
} CohSceneProtocolBinding;
typedef struct {CohCatalogSeedRecord source;uint32_t update_presence_known;} CohSceneProtocolRecord;
typedef struct {
 CohSceneProtocolBinding binding;
 uint32_t records,ordinary_records,active_records,tombstones,external_records;
 uint32_t equal_wire_updates,verified_omissions;
 size_t owned_bytes,dependencies_bytes,prior_owned_bytes,prior_dependencies_bytes,aggregate_reserved_bytes;
 uint32_t protocol_wire_inputs_complete,client_derived_state_complete,bounds_cache_checksums_recomputed;
 uint32_t source_generation_admitted,world_authority,owned_graph_lease;
} CohSceneProtocolReport;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohSceneProtocolBudget;
/* Immutable transactional PROTOCOL-WIRE INPUT state, never a live world permit.
 * Actual catalog +snapshot owners are retained. Graph is borrowed and must stay
 * alive/immutable through all state refs, lookup calls and candidate publication.
 * No graph retain is implied. Source raw wire spans live through state retirement.
 * NULL groups builds a detached complete source seed: update_presence_known=0.
 * A nonNULL groups requires all three fields and validates exact immutable
 * witness/packet before constructing a compatibility-marked state. No packet,
 * CLIENT derived state, source-generation certificate, ACK or renderer permit is
 * manufactured. Optional GROUPS binding is external provenance, not authority.
 *
 * Next local preparation generation is exactly old+1 (or1). Catalog, asset,
 * graph and snapshot generations cannot regress. Same catalog generation must
 * preserve catalog/snapshot/source/run; same asset generation preserves inventory.
 * Within that same source generation a checked GROUPS association cannot silently
 * downgrade to source-only. Old remains caller-retained unchanged; no old retain.
 * old must remain alive until candidate publication/discard. Reference operations
 * and publication are caller-serialized (not atomic across threads).
 *
 * Candidate descriptorarray is bounded; full source-wire fields are borrowed
 * unchanged, not eagerly re-materialized. Named budget automatically charges
 * old+new state/dependencies even when aliased: graph payload, actual catalog
 * owner, complete SnapshotOwner, optional witness payload, input reader bytes,
 * provisional emittedmask,64KiB local frame and128KiB nested core. Caps32/96MiB
 * unchanged. retained_bytes adds all other owners/slack/provider contexts/stacks.
 * Controls/known source/input spans disjoint; opaque owners/graph/cancel contexts
 * additionally caller-disjoint. Cancel callback may mutate only its own context.
 * *out must be NULL; all failures leave out/report/old/reader unchanged.
 */
CohStatus coh_scene_protocol_create(const CohSceneProtocol *old,const CohRuntimeGraph *,
 CohCatalogOwner *,CohCatalogSnapshot *,const CohSceneProtocolGroups *,uint32_t generation,
 const CohSceneProtocolBudget *,const CohCancel *,CohSceneProtocol **out,CohSceneProtocolReport *);
/* Owning variant: derives graph+sources from the actual immutable GraphOwner,
 * retains that owner through all state references, and charges its metadata in
 * addition to the dependencies already charged above. Existing borrowed entry
 * is unchanged. The source-only/compatibility-only authority limits still apply. */
CohStatus coh_scene_protocol_create_owned(const CohSceneProtocol *,CohRuntimeGraphOwner *,
 const CohSceneProtocolGroups *,uint32_t,const CohSceneProtocolBudget *,const CohCancel *,
 CohSceneProtocol **,CohSceneProtocolReport *);
CohStatus coh_scene_protocol_retain(CohSceneProtocol *);
void coh_scene_protocol_release(CohSceneProtocol *);
/* Serialized guarded transfer. Candidate must have been built for EXACT current
 * pointer and next generation; retired must beNULL. On refusal all unchanged.
 * Caller retires old only after every borrower finishes. This publishes protocol
 * input state only, never world/actor/resources or source/live generation. */
CohStatus coh_scene_protocol_publish(CohSceneProtocol **current,CohSceneProtocol **candidate,CohSceneProtocol **retired);
CohStatus coh_scene_protocol_report(const CohSceneProtocol *,CohSceneProtocolReport *);
CohStatus coh_scene_protocol_record(const CohSceneProtocol *,uint32_t ordinal,CohSceneProtocolRecord *);
CohStatus coh_scene_protocol_slot(const CohSceneProtocol *,uint32_t file,uint32_t slot,CohSceneProtocolRecord *);
/* Existing compact graph adapter, exact borrowed identity only. */
CohStatus coh_scene_protocol_graph(const CohSceneProtocol *,const CohRuntimeGraph **);
#endif
