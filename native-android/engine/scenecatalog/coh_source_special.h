#ifndef COH_SOURCE_SPECIAL_H
#define COH_SOURCE_SPECIAL_H
#include "coh_source_selection.h"
/* Source-only supplemental channels; NEVER an ordinary CPU/draw permit. */
#define COH_SOURCE_SPECIAL_REFLECTION 1u
#define COH_SOURCE_SPECIAL_MISSING_UV 2u
#define COH_SOURCE_SPECIAL_ALT_PIVOT 4u
#define COH_SOURCE_SPECIAL_PREPARATION_RESERVE (16u*1024u)
#define COH_SOURCE_SPECIAL_MAX_QUADS 256u
#define COH_SOURCE_SPECIAL_MAX_STREAM (256u*1024u)
typedef struct {size_t aggregate_limit,retained_bytes;} CohSourceSpecialBudget;
typedef struct {
 CohSourceBodyLease source;
 uint32_t kinds,reflection_quads,alternate_pivots,observed_cast_shadow;
 CohBytes reflection_delta,alternate_pivot_wire;
 const float *reflection_vertices; /*quad_count*12 binary32 scalars in workspace*/
 float alternate_pivot[15][12];
 size_t workspace_bytes,aggregate_reserved_bytes;
 uint32_t ordinary_cpu_ready,client_semantics_admitted,world_authority;
} CohSourceSpecial;
/* Actual opaque Body and wholejoin ordinal only; no supplied path/hash/version.
 * No allocation, mutation of Body or transfer. Body+graph+loader and caller
 * workspace must remain live+immutable while borrowed output views are used.
 * Workspace may change on failure; *out unchanged. All known source/control
 * spans must be disjoint; opaque Body private allocation disjoint by caller.
 * Workspace must have float alignment; capacity<=1MiB bounds work/storage.
 * Charges actual Body dependencies+one actual loader reservation+whole workspace
 * and known native preparation frames (16KiB) plus caller retained bytes.
 * Not RSS/whole-process accounting. Other live owners
 * and external zlib/callback stack peaks belong in retained_bytes. Ordinary models
 * return NOT_FOUND; special channels stay explicit pending CLIENT consumers. */
CohStatus coh_source_special_prepare(const CohSourceBody *,uint32_t source_ordinal,
 void *workspace,size_t capacity,const CohSourceSpecialBudget *,CohCancel,
 CohSourceSpecial *out);
#endif
