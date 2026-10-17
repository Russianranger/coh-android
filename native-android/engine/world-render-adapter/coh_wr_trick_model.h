#ifndef COH_WR_TRICK_MODEL_H
#define COH_WR_TRICK_MODEL_H
#include "coh_wr_trick_detached.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WR_TRICK_MODEL_QUERY_RESERVE 4096u
typedef struct {
 const char *model_name,*source_geo_path;
 uint32_t report_missing_suffix;
} CohWrTrickModelQuery;
typedef struct {size_t aggregate_limit,external_bytes;} CohWrTrickModelLimits;
enum {COH_WR_TRICK_MODEL_WHOLE_NAME=1,COH_WR_TRICK_MODEL_FIRST_SUFFIX=2};
enum {COH_WR_TRICK_MODEL_NO_DIAGNOSTIC=0,COH_WR_TRICK_MODEL_FILENAME_DIAGNOSTIC=1,COH_WR_TRICK_MODEL_GENERIC_DIAGNOSTIC=2};
typedef struct {
 uint8_t cache_sha256[32];char lookup_key[260];
 uint32_t historical_input_generation,branch,matched,source_ordinal,source_diagnostic;
 size_t aggregate_reserved_bytes;
} CohWrTrickModelSelection;
/* Original trickFromObjectName selection over an admitted historical dictionary:
 * first __ selects its COMPLETE suffix; otherwise the complete model name is the
 * key. A missing suffix never falls back to the model's base name. The dictionary
 * preserves original reverse-registration/first-owner precedence. Completed
 * misses return OK, matched=0 and source_ordinal=UINT32_MAX. source_diagnostic
 * classifies the original would-log branch; no logging/callback is performed.
 * source_geo_path affects only that diagnostic, never selection. Original global
 * existence reporting is an explicit 0/1 input. Both strings are printable ASCII
 * and NUL-terminated within 260 readable bytes (or provide all 260 readable bytes
 * for bounded refusal). Model name is nonempty; source path may be empty but not
 * NULL. A short unterminated span is not a valid const-char pointer input.
 * No heap, pin, retained pointers or new owner is created. Inputs stay immutable;
 * all refusals preserve output, which must be disjoint from inputs/owner/body.
 * external_bytes includes the existing owner and, for the whole-cache variant,
 * its configured whole loader reservation, plus all other live owners, source
 * statics/code/runtime/provider peaks. Adds 4 KiB bounded query/input/output/control
 * reserve before lookup. Detached lookup requires no retired loader/provider.
 * Results carry only the existing historical cache hash/import label. Use the
 * SAME still-live owner's existing view/numeric/child getters for the ordinal.
 * Numeric projections remain incomplete for animation. Neither a positive nor
 * a miss equates captured SERVER and CLIENT generations, proves an active table,
 * selects a TexBind/Basic texture or grants material/LOD/world/GPU permission. */
CohStatus coh_wr_trick_model_select(const CohWrTrickCache*,const CohWrTrickModelQuery*,const CohWrTrickModelLimits*,CohWrTrickModelSelection*);
CohStatus coh_wr_trick_detached_model_select(const CohWrTrickDetached*,const CohWrTrickModelQuery*,const CohWrTrickModelLimits*,CohWrTrickModelSelection*);
#ifdef __cplusplus
}
#endif
#endif
