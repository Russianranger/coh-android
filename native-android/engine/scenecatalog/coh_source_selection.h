#ifndef COH_SOURCE_SELECTION_H
#define COH_SOURCE_SELECTION_H
#include "coh_resource_join.h"
#define COH_SOURCE_SELECTION_FILES 391u
#define COH_SOURCE_SELECTION_EVIDENCE 7u
/* Only the independently reviewed exact disposable cold capture38994607354.
 * No public proof constructor, expected-hash input or JSON-success flags. */
typedef struct CohSourceSelection CohSourceSelection;
typedef struct CohSourceBody CohSourceBody;
typedef enum {COH_SOURCE_PROCEDURAL_EXACT_COLD_CAPTURE=1} CohSourceEvidenceKind;
/* Ordered actual raw bytes: source/run/control-fixture/resource-binding/capture
 * receipt/sealed391body-header witness/finalsource-route witness. Expected raw
 * lengths and digests are built in, never caller-selected. */
typedef struct {CohBytes bytes[COH_SOURCE_SELECTION_EVIDENCE];} CohSourceSelectionEvidence;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohSourceSelectionBudget;
typedef struct {
 uint32_t evidence_kind,profile_id,profile_association_verified,direct_open_observed;
 uint32_t files,covered_model_rows,root_model_references;
 size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t assets_admitted,client_materials_available,live_generation_admitted,world_authority;
} CohSourceSelectionReport;
/* Retains exactjoin; its actual graph remains BORROWED. Caller MUST keep that
 * graph live+immutable until the last selection/body/join reference retires.
 * The owner checks actualcatalog/snapshot/resource bytes and copied opaquejoin
 * bindings against a compiled exact profile. WitnessJSON alone cannot mint it.
 * Old/new/unique owner dependencies, inputevidence, profiletable and scratch are
 * charged; other digest/callback/context owners belong in retained_bytes.
 * Digest callback is a trusted, independently qualified whole-byte SHA256
 * implementation, as in existing owner/index APIs; a fake callback cannot
 * qualify evidence. Serialized access; known controls/source spans disjoint; opaqueallocations
 * also disjoint by caller. *outNULL. On refusal old/out/report unchanged. */
CohStatus coh_source_selection_create(const CohSourceSelection *old,CohResourceJoin *,
 const CohSourceSelectionEvidence *,const CohSourceSelectionBudget *,
 CohResourceDigest,void *,CohCancel,CohSourceSelection **out,CohSourceSelectionReport *);
CohStatus coh_source_selection_retain(CohSourceSelection *);
void coh_source_selection_free(CohSourceSelection *);
CohStatus coh_source_selection_report(const CohSourceSelection *,CohSourceSelectionReport *);
/* Ordinal is from the retained wholejoin. Exact profile source-name association;
 * unmodeled/uncovered returnsNOT_FOUND; borrowedpin names live through owner.
 * No blob at-use check or derived-origin permit is implied by this lookup. */
CohStatus coh_source_selection_pin(const CohSourceSelection *,uint32_t source_ordinal,
 uint32_t *file_index,CohResourceGeoPin *);
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes,loader_reservation;} CohSourceBodyBudget;
typedef struct {
 uint32_t evidence_kind,profile_id,file_index,source_rows,derived_origin_verified,direct_open_observed;
 size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t assets_admitted,client_materials_available,live_generation_admitted,world_authority;
} CohSourceBodyReport;
/* FILE-SCOPED procedural derivation, never a wholeworld/material/livepermit.
 * Uses the fixed profile path/hash and ALL matching actualjoined Model owners,
 * not merely rootowners. Protectedloader blob identity/generation/wholeSHA and
 * header/model/partition checks run before success. Retainsselection+immutable
 * index and protected blob. Loader stays caller-owned and outlivesbody. Its
 * configured limit MUST be <=loader_reservation. Other loader owners/contexts
 * and digest scratch charged by caller; old/new loader reservations are unique
 * by identity. No eager391file residency. *outNULL; rollback preservesold/out.
 * Zero-drawsource rows stay explicit, grant no geometry/material permit. */
CohStatus coh_source_body_create(const CohSourceBody *old,CohSourceSelection *,
 uint32_t file_index,CohAssetLoader *,const CohSourceBodyBudget *,CohResourceDigest,
 void *,CohCancel,CohSourceBody **out,CohSourceBodyReport *);
void coh_source_body_free(CohSourceBody *);
/* Borrowed immutable index; caller may not free it or outlivebody. */
CohStatus coh_source_body_view(const CohSourceBody *,const CohResourceIndex **,CohSourceBodyReport *);
typedef struct {
 uint32_t source_ordinal,graph_node,graph_generation,catalog_generation;CohResourceBinding binding;
 CohResourceGeoPin geo;CohResourceView model;CohResourceOwnerSources actual_sources;
 uint8_t resource_record_sha256[32],resources_sha256[32];
 CohAssetLoader *loader;size_t loader_reservation,retained_owner_bytes;
} CohSourceBodyLease;
/* Exact wholejoin ordinal→actual retained index owner. Names/header/model views
 * borrow body; source identities and generation are never caller labels.
 * retained_owner_bytes counts actual current body/index/selection/join/catalog/
 * snapshot/borrowedgraph/profile owners, EXCLUDING the separately returned
 * loaderreservation. Does not subtract historical preparation peaks. Caller
 * accounts all other live owners/scratch and keeps actual graph+loader alive.
 * No allocations/digests. Output disjoint from body/index and all borrowed
 * source/owner storage; known source spans checked; unchanged on refusal. */
CohStatus coh_source_body_lease(const CohSourceBody *,uint32_t source_ordinal,CohSourceBodyLease *);
/* Actual immutable dependency identities, never caller labels. Bytes exclude
 * loader reservation. body_owned_bytes includes its private index. Shared
 * selection/join/catalog/snapshot/graph/profile may be charged once ONLY by
 * actual pointer identity; equal hashes do not establish shared ownership.
 * Borrowed through Body lifetime. Graph+loader still need caller-held leases.
 * Controls/output disjoint from opaque owners and known source storage. */
typedef struct {
 const void *body_identity,*index_identity,*selection_identity,*profile_identity;
 const CohResourceJoin *join_identity;
 size_t body_owned_bytes,selection_owned_bytes,profile_bytes;
 CohResourceJoinIdentity join;
 CohAssetLoader *loader;size_t loader_reservation;
} CohSourceBodyDependencies;
CohStatus coh_source_body_dependencies(const CohSourceBody *,CohSourceBodyDependencies *);

#endif
