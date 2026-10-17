#ifndef COH_SOURCE_SEALED_H
#define COH_SOURCE_SEALED_H
#include "coh_source_mesh_batch.h"
typedef struct CohSourceSealed CohSourceSealed;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;}CohSourceSealedBudget;
typedef struct {
 uint32_t source_ordinal,graph_node,graph_generation,catalog_generation,first_part,vertices,triangles,parts;
 CohResourceBinding binding;CohResourceGeoPin geo;CohResourceView model;
 CohBytes resource_record,original_header;uint8_t resource_record_sha256[32],resources_sha256[32];
 uint32_t unscaled_base_uv,material_binding_required;
}CohSourceSealedEntry;
typedef struct {
 uint32_t meshes,parts,evidence_kind,profile_id;
 size_t owned_bytes,shared_source_bytes,preparation_reserve,retirement_peak_bytes;
 size_t inherited_loader_reservations; /* charged during transfer, NOT owned */
 uint32_t body_dependencies,index_dependencies,loader_dependencies,payload_streams_retained;
 uint32_t direct_open_observed,live_generation_admitted;
 uint32_t renderer_ready,client_materials_available,actor_available,world_authority;
}CohSourceSealedReport;
typedef struct {const CohSourceSelection*selection_identity;const CohResourceJoin*join_identity;CohResourceJoinIdentity join;}CohSourceSealedIdentity;
/* Separate SOURCE-only seal. Copies canonical arrays/indices, exact COHRES and
 * complete decompressed GEO header; rebases EVERY name/material pointer into
 * owned storage. Retains actual Selection (and its actual join/catalog/snapshot),
 * NEVER a Body/index/loader reference. External graph lease still MUST outlive
 * owner. Old batch+all its loader reservations+new copy+16KiB own frames+caller
 * peaks charged BEFORE callback/allocation. <=32MiB owned /96MiB aggregate.
 * Only final complete success consumes/frees *batch and clears it. Otherwise
 * batch/out/report unchanged. *outNULL, serialized access, opaque/control/source
 * allocations caller-disjoint; known source/control aliases/endpoints guarded.
 * Caller MUST actually trim/destroy its external loaders/provider and retire any
 * OTHER pins before their reservation can leave the application budget. This
 * owner cannot destroy unrelated caller loaders. A zero dependency count alone
 * is not proof those external allocations have been retired.
 * Header pack offsets remain metadata. Full GEO payload streams (GRID/reduction
 * payloads included) are NOT retained/exposed; exact body SHA/path permit only
 * a separately validated future reacquire. No false BodyLease is returned.
 * All geometry/material/readiness restrictions of canonical SOURCE mesh remain. */
CohStatus coh_source_sealed_create(CohSourceMeshBatch**,const CohSourceSealedBudget*,CohCancel,CohSourceSealed**,CohSourceSealedReport*);
void coh_source_sealed_free(CohSourceSealed*);
CohStatus coh_source_sealed_report(const CohSourceSealed*,CohSourceSealedReport*);
CohStatus coh_source_sealed_identity(const CohSourceSealed*,CohSourceSealedIdentity*);
CohStatus coh_source_sealed_find(const CohSourceSealed*,uint32_t ordinal,uint32_t*slot);
CohStatus coh_source_sealed_entry(const CohSourceSealed*,uint32_t slot,CohSourceSealedEntry*);
CohStatus coh_source_sealed_part(const CohSourceSealed*,uint32_t slot,uint32_t part,CohSourceMeshPart*);
#endif
