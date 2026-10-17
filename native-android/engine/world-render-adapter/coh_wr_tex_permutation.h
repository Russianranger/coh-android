#ifndef COH_WR_TEX_PERMUTATION_H
#define COH_WR_TEX_PERMUTATION_H
#include "coh_wr_tex_basic_lookup.h"
#define COH_WR_TEX_PERMUTATION_SWAPS_MAX 256u
#define COH_WR_TEX_PERMUTATION_LOCALES_MAX 16u
typedef struct{const char*source,*destination;}CohWrTexSceneSwap;
typedef struct{uint32_t base_header_ordinal,configuration_label,initial_load_state,guarded_short_key_policy;const CohWrTexSceneSwap*swaps;uint32_t swap_count;const char*search_path;}CohWrTexPermutationInput;
typedef struct{size_t aggregate_limit,external_bytes;}CohWrTexPermutationLimits;
enum{COH_WR_TEX_PERMUTATION_COMPLETE_SOURCE_PLAN=0,COH_WR_TEX_PERMUTATION_SCENE_NAMESPACE_UNKNOWN=1,COH_WR_TEX_PERMUTATION_LOCALE_NAMESPACE_UNKNOWN=2,COH_WR_TEX_PERMUTATION_WHITE_IDENTITY_UNKNOWN=3};
typedef struct{uint32_t input_generation,configuration_label,base_header_ordinal,scene_swap_index,after_scene_header_ordinal,candidate_header_ordinal,frontier,locale_count,frontier_locale_index,query_count,guarded_short_key_policy,unresolved_client_semantics;char scene_destination[128],locale_keys[COH_WR_TEX_PERMUTATION_LOCALES_MAX][128];CohWrTexBasicLookup queries[2];size_t input_bytes,aggregate_reserved_bytes;}CohWrTexPermutationPlan;
/* Read-only initial-not-loaded SOURCE plan, no BasicTexture mutations/loads.
 * All scene names are normalized with texFixName WITHOUT texFind's leading!
 * removal. Highest matching scene ordinal wins. Locale strtok delimiters and
 * leading# removal preserve exact source order/empty-after# tokens. Lookup stops
 * at the first unknown namespace candidate; never assumes missing or white.
 * An observed locale candidate stops at missing actual white identity. Nothing
 * beyond that frontier is selected or skipped. Supplied config label is merely
 * caller source-input identity, never authenticated/current SERVER generation.
 * Strict/guarded policies explicitly select qualified Basic lookup semantics.
 * Requires immutable owner/query/config spans for whole call; loader alive.
 * external covers old owner+wholeloader+old16KiBcontrol+other provider/runtime/
 * old resources; adds all input bytes+32KiBown control+16KiBnestedBasic reserve.
 * Scalar fixed-size output owns all strings/ordinals; no resource/renderer handle.
 * Every failure preserves output; all borrowed owner/blob/input aliases refuse.
 * Other load states, overlong/nonASCII names or unbounded locale lists refuse.
 * Completed SOURCE plan still grants no active namespace/TexWord/capability/
 * material/world permission. Current scene/locale/white identity remain external. */
CohStatus coh_wr_tex_permutation_plan(const CohWrTexInputs*,const CohWrTexPermutationInput*,const CohWrTexPermutationLimits*,CohCancel,CohWrTexPermutationPlan*);
#endif
