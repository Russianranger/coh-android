#ifndef COH_SOURCE_RIGID_H
#define COH_SOURCE_RIGID_H
#include "coh_source_selection.h"
#include "../world-render-adapter/coh_wr_rigid_source.h"
typedef struct CohSourceRigid CohSourceRigid;
typedef struct {
 uint32_t source_ordinal,material_generation;
 CohWrRigidDigest digest;void *digest_context;
 CohWrRigidMaterialAcquire acquire;CohWrRigidMaterialRelease release;void *material_context;
} CohSourceRigidRequest;
typedef struct {
 size_t aggregate_limit,retained_bytes,max_workspace_bytes,max_stream_bytes;
 uint32_t max_models,max_vertices,max_triangles,max_parts;
} CohSourceRigidLimits;
typedef struct {
 uint32_t source_ordinal,graph_node,owner_kind,file,slot,original_id;
 uint32_t evidence_kind,profile_id,asset_generation,resource_owner_generation,graph_generation,catalog_generation,material_generation;
 uint32_t derived_file_origin_verified,direct_open_observed,unresolved_client_semantics;
 CohWrRigidReport rigid;size_t retained_source_bytes,aggregate_reserved_bytes;
 uint8_t source_sha256[32],run_sha256[32],resource_record_sha256[32],resources_sha256[32];
 uint32_t assets_admitted,client_materials_available,live_generation_admitted,world_authority;
} CohSourceRigidReport;
/* Transfer *body into one immutable CPU-rigid owner ONLY on complete success.
 * Body, *out and report unchanged on ANY refusal; no partial transfer. Exact
 * loader/path/model/bodyhash/assetgeneration and graph owner come from actual
 * SourceBody lease+wholejoin ordinal, never request labels. Zero-draw models
 * refuse before material callback. Material callbacks/generation remain an
 * EXTERNAL independently qualified CLIENT prerequisite; fixture callbacks
 * remain fixtures. This bridge never grants material/draw/live/world authority.
 * Trusted exact SHA256 callback; no caller expected geometry hash accepted.
 * Limits.retained_bytes reserves ALL other old/resources/material/digest/GPU
 * owners and callback peaks. Actual current source-owner bytes + bridge/scratch
 * are added; actual bodyloader reservation derived and charged once separately.
 * Caller serializes access and supplies disjoint controls/opaque source storage.
 * Actual loader and borrowed graph outlive bridge. Retire off render thread. */
CohStatus coh_source_rigid_create(CohSourceBody **body,const CohSourceRigidRequest *,
 const CohSourceRigidLimits *,CohCancel,CohSourceRigid **out,CohSourceRigidReport *);
/* Outputs/geometry/material names borrow bridge lifetime; caller outputs are
 * disjoint from bridge/body/index/source storage. No publication or GPU pins
 * are minted. Material pins remain held until bridge retirement. */
CohStatus coh_source_rigid_report(const CohSourceRigid *,CohSourceRigidReport *);
CohStatus coh_source_rigid_part(const CohSourceRigid *,uint32_t,CohRenderGeometry *,CohWrRigidMaterial *);
void coh_source_rigid_free(CohSourceRigid *);
#endif
