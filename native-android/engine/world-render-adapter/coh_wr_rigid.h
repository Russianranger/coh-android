#ifndef COH_WR_RIGID_H
#define COH_WR_RIGID_H
#include "coh_world_render.h"
#include "../assets/coh_asset_geo.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Additive source-resource conversion, NOT world/actor/live admission. All calls
 * and callbacks use one off-thread owner. The protected asset loader outlives
 * every resource. The loader MUST be configured with
 * total_bytes<=loader_reservation; its opaque
 * public API cannot attest that configuration. The whole explicit reservation
 * is charged before acquisition and actual peaks checked against it, separate
 * from external_bytes.
 * external_bytes includes ALL other retained/peak material/digest/source/GPU
 * storage. The cap covers old resources if charged there; it is not an RSS cap. */
typedef struct {
    size_t aggregate_limit,external_bytes,loader_reservation,max_workspace_bytes,max_stream_bytes;
    uint32_t max_models,max_vertices,max_triangles,max_parts;
} CohWrRigidLimits;
typedef struct {
    CohRenderMaterial material; /* supported renderer semantics, zero GPU names */
    float uv_scale[2][2]; /* source V=1-V exactly once, then qualified bind scale */
    uint64_t texture_id[3],geometry_id; /* exact immutable producer identities */
    uint32_t generation,unsupported_semantics; /* nonzero unsupported refuses */
    uint8_t source_sha256[32]; /* independently authenticated material binding */
    void *pin; /* required lifetime pin, released once on rollback/retirement */
} CohWrRigidMaterial;
/* Successful callback transfers exactly one pin. On error callback retains
 * responsibility for its scratch/pins; no output ownership transfers. */
typedef CohStatus (*CohWrRigidMaterialAcquire)(void *,CohAssetId,const char *model,
    uint32_t partition,const CohAssetGeoMaterial *,CohWrRigidMaterial *);
typedef void (*CohWrRigidMaterialRelease)(void *,void *pin);
typedef CohStatus (*CohWrRigidDigest)(void *,CohBytes,uint8_t sha256[32]);
typedef struct {
    CohAssetId geo; const char *model; /* exact generation/name; no aliases */
    uint8_t geo_sha256[32];
    uint32_t material_generation;
    CohWrRigidDigest digest; void *digest_context;
    CohWrRigidMaterialAcquire acquire; CohWrRigidMaterialRelease release;
    void *material_context;
} CohWrRigidRequest;
typedef struct CohWrRigidResource CohWrRigidResource;
typedef struct {
    uint32_t geo_version,asset_generation,material_generation,parts,vertices,triangles;
    size_t owned_bytes,temporary_bytes,loader_bytes,loader_reservation,external_bytes,aggregate_peak_bytes;
    uint8_t geo_sha256[32];
} CohWrRigidReport;
/* Exact source digest checked before decode. Rigid GEOv8 base channels only;
 * rejects bone info, skin weights/indices, lightmap UV, reflection channels,
 * nonunit source scale, alternate pivots, missing/unsupported materials. Grid/reduction storage
 * is not consumed and grants no collision/LOD interpretation. Caller semantic
 * producer must refuse tricks/LOD/material states it has not qualified.
 * Full model/partition identity and both CPU/material pins survive loader trim.
 * *out MUST be NULL; COH_STATE otherwise. Failure leaves output unchanged; every acquired pin rolls back. */
CohStatus coh_wr_rigid_acquire(CohAssetLoader *,const CohWrRigidRequest *,
    const CohWrRigidLimits *,CohCancel,CohWrRigidResource **);
CohStatus coh_wr_rigid_identity(const CohWrRigidResource *,CohAssetId *,const char **model);
CohStatus coh_wr_rigid_report(const CohWrRigidResource *,CohWrRigidReport *);
/* Views borrow immutable owned geometry and pinned material. World transform is
 * supplied separately. Keep resource through coh_wr_prepare geometry copying. Material/texture pins
 * must additionally survive binding/all renderer flushes or transfer to an
 * independently retained owner; preparation copies IDs and acquires no GPU pin. */
CohStatus coh_wr_rigid_part(const CohWrRigidResource *,uint32_t,
    CohRenderGeometry *,CohWrRigidMaterial *);
/* Retire off-thread only after all borrowers finish; NULLs caller pointer. */
void coh_wr_rigid_release(CohWrRigidResource **);
#ifdef __cplusplus
}
#endif
#endif
