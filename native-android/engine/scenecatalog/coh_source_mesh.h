#ifndef COH_SOURCE_MESH_H
#define COH_SOURCE_MESH_H
#include "coh_source_selection.h"
#include "../renderer/coh_renderer.h"
typedef struct CohSourceMesh CohSourceMesh;
typedef struct {uint32_t source_ordinal;CohResourceDigest digest;void*digest_context;}CohSourceMeshRequest;
typedef struct {size_t aggregate_limit,retained_bytes,max_stream_bytes;}CohSourceMeshBudget;
typedef struct {
 CohSourceBodyLease source;
 uint32_t vertices,triangles,parts,unscaled_base_uv,material_binding_required;
 size_t owned_bytes,temporary_bytes,preparation_reserve,aggregate_reserved_bytes;
 uint32_t render_ready,client_materials_available,world_authority;
}CohSourceMeshReport;
typedef struct {
 const CohRenderVertex*vertices;uint32_t vertex_count;
 const uint32_t*indices;uint32_t index_count;
 CohAssetGeoMaterial source_material;
}CohSourceMeshPart;
/* Separate SOURCE-only exactv8 opt-in, not a rigid/material entry. One canonical
 * unscaled vertex array is shared by all partitions; UV=sourceU,1-sourceV in both
 * base channels, neutral carrier color1. No per-material scale, lighting or draw
 * state is invented. Consumers MUST separately qualify/apply effective CLIENT
 * UV/material semantics; output never grants renderer readiness.
 * ActualBody supplies all path/model/hash/row/identity/generation fields. Whole
 * body SHA is checked again before decode. Refuses all existing special cases,
 * skin/lightmap channels and nonunit scale; GRID/reductions stay Body metadata.
 * RetainsBody by TRANSFER only on complete success. Failure leaves Body/out/report
 * unchanged and rolls back allocations. Caller supplies disjoint controls and
 * opaque source allocations; known source/control aliases/endpoints refuse.
 * Graph+loader remain borrowed and must outlive this owner. Provider, all other
 * old/actor/dictionary/GPU owners and peaks belong in retained_bytes. Actual
 * source dependencies+one exact loader reservation+owned+temporary+16KiB known
 * native preparation frames are added. Aggregate<=96MiB, stream<=2MiB; source
 * model/vertex/triangle/part ceilings unchanged. No processRSS guarantee. */
CohStatus coh_source_mesh_v8_create(CohSourceBody**,const CohSourceMeshRequest*,
 const CohSourceMeshBudget*,CohCancel,CohSourceMesh**,CohSourceMeshReport*);
CohStatus coh_source_mesh_report(const CohSourceMesh*,CohSourceMeshReport*);
/* Views require mesh lifetime; controls disjoint from all owned/source storage. */
CohStatus coh_source_mesh_part(const CohSourceMesh*,uint32_t,CohSourceMeshPart*);
typedef struct {CohBytes mesh_storage;CohSourceBodyDependencies body;}CohSourceMeshDependencies;
/* Borrowed through mesh lifetime, no allocation/reference/authority change.
 * Actual storage and dependency identities support exact unique-owner charges. */
CohStatus coh_source_mesh_dependencies(const CohSourceMesh*,CohSourceMeshDependencies*);
void coh_source_mesh_free(CohSourceMesh*);
#endif
