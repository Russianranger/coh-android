#ifndef COH_RESOURCE_JOIN_H
#define COH_RESOURCE_JOIN_H
#include "coh_catalog_snapshot.h"
#include "coh_resource_index.h"
#include "../scenegraph/runtime_graph.h"
typedef struct CohResourceJoin CohResourceJoin;
typedef struct {CohResourceBinding resource;uint8_t resources_sha256[32];} CohResourceJoinPins;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohResourceJoinBudget;
typedef struct {
    uint32_t rows,regular,external,models,graph_generation,catalog_generation;
    size_t owned_bytes,peak_record_bytes,aggregate_peak_bytes;
    uint32_t source_association_verified,assets_admitted,world_authority;
} CohResourceJoinReport;
/* SOURCE-ONLY association. Resource pins MUST be independently admitted from
 * the same capture's source/run/binding receipts. Neither supplied labels nor
 * this structural join authenticate their provenance. The whole stream hash is
 * checked over an owned copy. Graph binding AND exact borrowed source addresses
 * must match the retained catalog/snapshot owner. Every active original slot
 * and every future owner is matched once in source order; name/ID/model geometry
 * equality is byte-exact, without clone/public-name/path aliases.
 *
 * Catalog and snapshot references are retained. Graph remains caller-owned and
 * immutable through this join's lifetime; its source bytes are pinned by this
 * owner. Queries below use only copied mappings, not a borrowed graph pointer.
 * Old+new joins, unique catalog/snapshot owners, unique graphs, input resource
 * bytes, candidate descriptors, catalog walker and future decode scratch are
 * charged. Other original buffers, loader/material/index owners, callback/digest
 * scratch and GPU resources belong in retained_bytes. The graph allocation must
 * remain live and charged while a join exists even though queries do not touch
 * it. Caller serializes all preparation/ref/access and supplies disjoint controls.
 * *out must be NULL. Failure preserves old/out/report and frees all candidate
 * ownership. No assets, materials, client LOD, ACK, actor or live-world permit. */
CohStatus coh_resource_join_build(const CohResourceJoin *old,CohCatalogOwner *,
    CohCatalogSnapshot *,const CohRuntimeGraph *,CohBytes resources,const CohResourceJoinPins *,
    const CohResourceJoinBudget *,CohResourceDigest,void *,CohCancel,
    CohResourceJoin **out,CohResourceJoinReport *);
/* Serialized bounded references. Graph remains a BORROWED lease: it must stay
 * alive and immutable until the last join reference (including source-selection
 * owners) retires. Retaining a join does not retain a graph. */
CohStatus coh_resource_join_retain(CohResourceJoin *);
void coh_resource_join_free(CohResourceJoin *); /* release one reference */
typedef struct {
    CohResourceJoinPins pins;CohResourceJoinReport report;
    const void *catalog_identity,*snapshot_identity,*graph_identity;
    size_t catalog_owned_bytes,snapshot_owned_bytes,graph_owned_bytes;
    CohBytes catalog_bytes,snapshot_bytes,resource_bytes;
} CohResourceJoinIdentity;
/* Copied immutable binding/dependency identities and actual borrowed byte
 * spans. Used for exact cross-object pins and unique-owner budgeting. Output
 * disjoint from actual join/control/source storage; unchanged on refusal. */
CohStatus coh_resource_join_identity(const CohResourceJoin *,CohResourceJoinIdentity *);
/* Returned descriptors/raw bytes borrow join lifetime. Source order preserved. */
CohStatus coh_resource_join_sources(const CohResourceJoin *,const CohResourceSource **,
    size_t *count,CohResourceBinding *);
CohStatus coh_resource_join_node(const CohResourceJoin *,uint32_t ordinal,uint32_t *graph_node);
/* Prove a retained resource index copied every joined observation under exactly
 * the joined source/run/manifest/generation. Read-only, no authority transition. */
CohStatus coh_resource_join_match_index(const CohResourceJoin *,const CohResourceIndex *,CohCancel);
#endif
