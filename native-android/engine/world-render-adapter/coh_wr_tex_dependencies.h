#ifndef COH_WR_TEX_DEPENDENCIES_H
#define COH_WR_TEX_DEPENDENCIES_H
#include "coh_wr_tex_inputs.h"
#include "coh_wr_texopt_lookup.h"
typedef struct CohWrTexDependencies CohWrTexDependencies;
typedef struct{size_t owned_limit,aggregate_limit,external_bytes;}CohWrTexDependencyLimits;
enum{COH_WR_TEX_DEP_ACTIVE_NAMESPACE=1u,COH_WR_TEX_DEP_ENUMERATION_OVERLAY=2u,COH_WR_TEX_DEP_LWC_AVAILABILITY=4u,COH_WR_TEX_DEP_LOCALE_SCENE_SWAP=8u,COH_WR_TEX_DEP_CAPABILITY_FALLBACK=16u,COH_WR_TEX_DEP_TEXWORD=32u,COH_WR_TEX_DEP_ACTIVE_GENERATION=64u,COH_WR_TEX_DEP_COMPOSITE_BINDING=128u,COH_WR_TEX_DEP_GPU_LAYERS=256u,COH_WR_TEX_DEP_TRICK_AUTOLOD=512u};
typedef struct{uint32_t count,historical_input_generation,missing_requirements;size_t owned_bytes,aggregate_reserved_bytes;}CohWrTexDependencyReport;
typedef struct{
 CohWrTexHeaderInput header;CohWrTexOptLookup lookup;
 uint32_t initial_basic_flags,effective_basic_flags,effective_texopt_flags,texopt_surface,target,load_state[2],has_been_composited,reload_required;
 float gloss;const char*initial_composite_name,*initial_composite_directory;
 uint32_t missing_requirements,unresolved_client_semantics;
}CohWrTexBasicInput;
enum{COH_WR_TEX_DEP_NOT_REQUESTED=0,COH_WR_TEX_DEP_PRESENT_IMPORTED_HEADER=1,COH_WR_TEX_DEP_NOT_OBSERVED=2,COH_WR_TEX_DEP_UNQUALIFIED_KEY=3};
typedef struct{const char*name;char basic_key[128];uint32_t source_slot,valid_source_request,local_observation,local_header_ordinal;}CohWrTexDependency;
/* Takes ownership of *inputs ONLY on success; no active namespace/composite is
 * created. Loader outlives result; cache/Surface needed only during preparation.
 * Immutable imported headers form a SUBSET, not original CLIENT scan/overlay
 * order. Initial DDS flags and original Basic reset/target source projections
 * remain separate from cached TexOpt flags. Missing prerequisites stay explicit.
 * external covers whole inputs owner/loader, cache owner/whole loader, Surface
 * owner/static, other old owners and provider/runtime/code peaks (same loader
 * reservations may be conservatively charged twice). Adds64KiB own/nested stack
 * control reserve and all record owners. Caller outputs disjoint/writable outside
 * borrowed blobs; failures preserve inputs and output. No material/world permit. */
CohStatus coh_wr_tex_dependencies_stage(CohWrTexInputs**,const CohWrTexOptCache*,const CohWrSurfaceStates*,const CohWrTexDependencyLimits*,CohCancel,CohWrTexDependencies**);
void coh_wr_tex_dependencies_release(CohWrTexDependencies**);
CohStatus coh_wr_tex_dependencies_report(const CohWrTexDependencies*,CohWrTexDependencyReport*);
CohStatus coh_wr_tex_dependencies_basic(const CohWrTexDependencies*,uint32_t,CohWrTexBasicInput*);
/* Slots0..12 original blend names;13..15 enabled fallback base/blend/bump. Each
 * lookup observes ONLY the imported header subset. NOT_OBSERVED never means an
 * active CLIENT missing texture and does not select a default/fallback resource.
 * Original unsafe texFixName short domain remains explicitly UNQUALIFIED_KEY. */
CohStatus coh_wr_tex_dependencies_dependency(const CohWrTexDependencies*,uint32_t,uint32_t,CohWrTexDependency*);
CohStatus coh_wr_tex_dependencies_texopt(const CohWrTexDependencies*,uint32_t,CohWrTexOptView*);
#endif
