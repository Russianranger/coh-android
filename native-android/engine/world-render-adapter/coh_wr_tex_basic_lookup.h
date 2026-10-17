#ifndef COH_WR_TEX_BASIC_LOOKUP_H
#define COH_WR_TEX_BASIC_LOOKUP_H
#include "coh_wr_tex_inputs.h"
typedef struct{size_t aggregate_limit,external_bytes;}CohWrTexBasicLookupLimits;
enum{COH_WR_BASIC_NULL_REQUEST=0,COH_WR_BASIC_OBSERVED_HEADER=1,COH_WR_BASIC_NAMESPACE_UNKNOWN=2};
typedef struct{char key[128];uint32_t format_flags,branch,input_generation,header_ordinal,guarded_short_key_policy,unresolved_client_semantics;uint8_t header_sha256[32];size_t aggregate_reserved_bytes;}CohWrTexBasicLookup;
/* Original BasicTexture texFind semantics, distinct from model/composite lookup:
 * one leading!, positional suffix checks; no PORTAL branch, last-dot stripping,
 * directory stripping or material swaps. Searches ONLY immutable imported header
 * subset; namespace-unknown never permits white/default fallback or skipping a
 * higher-priority locale candidate. NULL request preserves original NULL branch.
 * Strict rejects original unsafe bare4..7 domain. Guarded is the explicitly
 * qualified two-location original correction, never unchanged-source for repair.
 * Read-only/no allocation; input owner/loader outlive borrowed query. external
 * includes input owner's owned bytes+whole loader reservation+16KiBold control,
 * other live owners/provider/runtime/code peaks. Adds16KiB own nested stack/
 * input/output/control reserve before query; no processRSS/active namespace proof.
 * All failures preserve output and reject output aliases with owner/blob/query.
 * Returned scalar/key/hash values are caller owned; no borrowed resource handle. */
CohStatus coh_wr_tex_basic_lookup(const CohWrTexInputs*,const char*,const CohWrTexBasicLookupLimits*,CohWrTexBasicLookup*);
CohStatus coh_wr_tex_basic_lookup_guarded(const CohWrTexInputs*,const char*,const CohWrTexBasicLookupLimits*,CohWrTexBasicLookup*);
#endif
