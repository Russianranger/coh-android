#ifndef COH_GROUPS_H
#define COH_GROUPS_H
#include "coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Admission policies for structural traversal, not original-engine maxima.
 * No graph, pointer, string or transform is retained, and no allocation occurs. */
#define COH_GROUPS_FILE_MAX 1024u
#define COH_GROUPS_DEF_ID_MAX 65535u
#define COH_GROUPS_DEF_MAX 65536u
#define COH_GROUPS_CHILD_MAX 262144u
#define COH_GROUPS_ROOT_ID_MAX 1048575u
#define COH_GROUPS_ROOT_MAX 65536u
#define COH_GROUPS_PROPERTY_MAX 65536u
#define COH_GROUPS_SWAP_MAX 65536u
#define COH_GROUPS_VALUE_MAX 4096u
#define COH_GROUPS_STRING_BYTES_MAX (3u*1024u*1024u)
#define COH_GROUPS_WORK_MAX (1024u*1024u)
typedef enum {
    COH_GROUPS_STAGE_NONE=0, COH_GROUPS_STAGE_PREFIX=1,
    COH_GROUPS_STAGE_FILES=2, COH_GROUPS_STAGE_FILE=3,
    COH_GROUPS_STAGE_DEF=4, COH_GROUPS_STAGE_CHILD=5,
    COH_GROUPS_STAGE_MATRIX=6, COH_GROUPS_STAGE_TRICKS=7,
    COH_GROUPS_STAGE_PROPERTY=8, COH_GROUPS_STAGE_SWAP=9,
    COH_GROUPS_STAGE_ROOT=10, COH_GROUPS_STAGE_FOOTER=11,
    COH_GROUPS_STAGE_END=12
} CohGroupsStage;
typedef struct {
    uint32_t new_world, files, present_files, defs, removed_defs, children,
        roots, removed_roots, properties, swaps, raw_matrices, packed_matrices,
        strings, string_bytes, work_units, max_def_id, max_root_id,
        footer_file_count, footer_active_roots, footer_defs_crc, footer_refs_crc;
    size_t prefix_bits, consumed_bits;
} CohGroupsInspection;
typedef struct { CohGroupsStage stage; size_t bit_offset; CohStatus status; } CohGroupsFailure;
/* Begin immediately after the normalized GROUPS command. The caller selects
 * the existing reader representation and byte budget. Inspect the complete
 * normal-world body synchronously, including the prefix and four-field footer.
 * Exact logical end is required. Source-produced definition IDs and sparse
 * root IDs must increase within their file/list, rejecting duplicate/decreasing
 * records without a retained identity set. Base/raid and unknown texture masks
 * are unsupported. Floats must be finite; packed transforms are traversed, not
 * reconstructed or claimed equivalent. Counts/string/work ceilings apply.
 *
 * On error reader and inspection are unchanged. Optional failure receives only
 * numeric stage/status/bit offset; no server text or body is retained. Offset
 * is the last completed read boundary (after an invalid scalar when read).
 * PREFIX uses the accepted transactional prefix parser, so its failure offset
 * is the prefix start boundary, not an individual malformed prefix field. On
 * success failure is cleared. String/work counters cover the tail after the
 * already bounded prefix. Footer checksums are observed, never verified here.
 * This grants no asset resolution, live scene, selected identity, ACK or READY.
 */
CohStatus coh_rep_groups(CohRepReader *, CohGroupsInspection *, CohGroupsFailure *);
#ifdef __cplusplus
}
#endif
#endif
