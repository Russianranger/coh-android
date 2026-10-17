#ifndef COH_WR_SURFACE_STATES_H
#define COH_WR_SURFACE_STATES_H
#include "../coh_contracts.h"
#define COH_WR_SURFACE_MAX 876u
typedef struct CohWrSurfaceStates CohWrSurfaceStates;
typedef CohStatus(*CohWrSurfaceDigest)(void*,CohBytes,uint8_t[32]);
typedef struct{size_t owned_limit,aggregate_limit,external_bytes;}CohWrSurfaceLimits;
typedef struct{uint32_t historical_input_generation,count;size_t owned_bytes,aggregate_reserved_bytes;}CohWrSurfaceReport;
/* Historical original CLIENT input dictionary ONLY. Exact retained seqstatebits
 * full SHA+schema and source-pinned code-defined core are required. This is not
 * current entity/animation/material authority. Loader-independent immutable owner.
 * Digest/context/input remain immutable throughout prepare. Digest/provider/runtime
 * stack peaks and all other live resources must be reserved in external_bytes.
 * Fixed16KiB own stack/control+16KiB source-static reservation are charged first.
 * *out must be NULL; refusal preserves output. Caller does not retain input bytes. */
CohStatus coh_wr_surface_prepare(CohBytes,uint32_t,CohWrSurfaceDigest,void*,const CohWrSurfaceLimits*,CohCancel,CohWrSurfaceStates**);
void coh_wr_surface_release(CohWrSurfaceStates**);
CohStatus coh_wr_surface_report(const CohWrSurfaceStates*,CohWrSurfaceReport*);
/* Exact original upper-case ASCII safe subset. Missing preserves output and must
 * remain distinguishable from original setupTexOpt's explicit default-to-zero. */
CohStatus coh_wr_surface_lookup(const CohWrSurfaceStates*,const char*,uint32_t*);
#endif
