#ifndef COH_BADGES_H
#define COH_BADGES_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Source array extents. The record-count bounds also bound malicious duplicate
 * IDs; valid repeated IDs are preserved in wire order, not silently deduped. */
#define COH_BADGE_PLAYER_MAX 4096u
#define COH_BADGE_SUPERGROUP_MAX 1050u
#define COH_BADGE_RECENT_MAX 50u
#define COH_BADGE_MONITOR_MAX 10u
#define COH_BADGE_RECORD_MAX (COH_BADGE_PLAYER_MAX+COH_BADGE_SUPERGROUP_MAX)
/* Explicit local filename admission, not a limit asserted of the source. */
#define COH_BADGE_FILENAME_MAX 1024u
#define COH_BADGE_FILENAMES_MAX (64u*1024u)
#define COH_BADGE_AGGREGATE_MAX (4u*1024u*1024u)

enum { COH_BADGE_OWNED=1u, COH_BADGE_VISIBLE=2u, COH_BADGE_KNOWN=4u,
       COH_BADGE_FILENAME=8u };
typedef struct {
    uint32_t index,flags,completion,filename_offset,filename_bytes;
} CohBadgeRecord;
typedef struct { uint32_t index,time_awarded; } CohBadgeRecent;
typedef struct {
    uint32_t debug_mode,player_count,supergroup_present,supergroup_count;
    uint32_t history_present,history_count,filenames_bytes;
    /* Player records first, then supergroup records. A zero filename length
     * with COH_BADGE_FILENAME set means an explicit empty filename. Without
     * that flag the source clears the previous filename to NULL. */
    CohBadgeRecord records[COH_BADGE_RECORD_MAX];
    CohBadgeRecent recent[COH_BADGE_RECENT_MAX];
    char filenames[COH_BADGE_FILENAMES_MAX];
} CohBadgeUpdate;
typedef struct { CohBadgeUpdate candidate; } CohBadgeWorkspace;
typedef struct { uint32_t indices[COH_BADGE_MONITOR_MAX]; } CohBadgeMonitor;

/* Entire original entity_ReceiveBadgeUpdate wire body, AFTER power modes and
 * BEFORE the full-update-only monitor body. This emits ordered raw events,
 * not dictionary-bound badge/UI state and never an actor/ACK certificate.
 *
 * Reader/output remain byte-identical on every failure. Workspace is caller
 * scratch, is unspecified after failure and must never be published. All
 * reader/output/workspace/input memory must be disjoint and caller-serialized.
 * No allocation, I/O, retained input or dictionary/UI mutation. Workspace and
 * output belong on a heap/arena, not an Android stack. Budget charges both PODs,
 * input bytes, an 8KiB stack reserve and caller_retained_bytes, including any old
 * output retained by an enclosing transaction. Limit <=4MiB, no hidden owner.
 * Counts/indices outside pinned source capacities, strings exceeding the local
 * bounds and noncanonical boolean bytes are refused rather than truncated.
 */
CohStatus coh_global_badges(CohRepReader *,CohBadgeUpdate *,CohBadgeWorkspace *,
    size_t caller_retained_bytes,size_t aggregate_limit);

/* Exactly ten original optional pack8 indices. All 32-bit source bit patterns,
 * duplicate IDs and order survive unchanged. Original CheckAndSortInfo needs
 * admitted badge dictionaries/state; it is deliberately not invoked here.
 * Atomic reader/output, no allocation, <=40-byte local candidate. */
CohStatus coh_global_badge_monitor(CohRepReader *,CohBadgeMonitor *);
#ifdef __cplusplus
}
#endif
#endif
