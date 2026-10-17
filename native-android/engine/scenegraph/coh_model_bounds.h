#ifndef COH_MODEL_BOUNDS_H
#define COH_MODEL_BOUNDS_H
#include "../coh_contracts.h"
#define COH_MODEL_BOUNDS_MODELS_MAX 65536u
#define COH_MODEL_BOUNDS_HEADER_MAX (32u*1024u*1024u)
typedef struct {float min[3],max[3],scale[3],radius;} CohModelBoundsNumbers;
typedef struct {CohBytes header,names;size_t records_offset;uint32_t version,models;} CohModelBoundsTable;
typedef struct {CohModelBoundsTable table;size_t offset;uint32_t row;} CohModelBoundsCursor;
typedef struct {CohModelBoundsNumbers numbers;const char *name;CohBytes record;uint32_t disk_row;} CohModelBoundsView;
/* Extracts only original readModel fields from already independently admitted
 * immutable decompressed GEO headers. This is NOT complete GEO admission.
 * Accepts original0,2,3,4,5,7,8; original loader refuses6. Names/records/fields
 * are bounded; table/cursor must come from these APIs and remain unmodified
 * except through next. Finite ordered boxes and nonnegative radius are required.
 * No heap/callback. Table/cursor/view names/spans borrow header lifetime.
 * Workspaces/outputs must be disjoint from header; known overlap is rejected.
 * Outputs unchanged on refusal; source row order is preserved. */
CohStatus coh_model_bounds_open(CohBytes,uint32_t version,CohModelBoundsTable *);
CohStatus coh_model_bounds_begin(const CohModelBoundsTable *,CohModelBoundsCursor *);
CohStatus coh_model_bounds_next(CohModelBoundsCursor *,CohModelBoundsView *);
/* Exact source-copy comparison, no normalization/tolerance. Bits0..2 min,
 *3..5 max,6..8 scale,9 radius; signed-zero differences remain observable.
 * Inputs are observations, never proof of source-channel/file generation.
 * Returns OK with mask0 for equality, nonzero mask for valid unequal fields.
 * Known output/input alias and malformed/nonfinite boxes refuse atomically. */
CohStatus coh_model_bounds_compare(const CohModelBoundsNumbers *source,
    const CohModelBoundsNumbers *disk,uint32_t *mismatch_fields);
#endif
