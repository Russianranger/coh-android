#ifndef COH_ATTRIB_MONITOR_H
#define COH_ATTRIB_MONITOR_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ATTRIB_MONITOR_SLOTS 11u
#define COH_ATTRIB_MONITOR_RAM_MAX (8u*1024u*1024u)
#define COH_ATTRIB_MONITOR_STACK_RESERVE 4096u
typedef struct{uint32_t present,key,value_word,buff;}CohAttribMonitorSlot;
typedef struct{uint32_t new_target,full;CohAttribMonitorSlot slots[COH_ATTRIB_MONITOR_SLOTS];size_t begin_bit,end_bit;}CohAttribMonitor;
typedef struct{CohAttribMonitor candidate;}CohAttribMonitorWorkspace;
/* Whole original monitor-only attribute-description body, AFTER caller's
 * attribute-present bit. full=1 unsupported atomically without dictionary.
 * Eleven source slots=MAX_COMBAT_STATS10+defense. Raw key/value/buff, no lookup,
 * previous-state/UI/target application, actor or ACK. Pairwise disjoint spans;
 * caller POD storage; input+bothPODs+4096stack+retained<=8MiB; no allocations.
 * Output and reader unchanged on failure. */
CohStatus coh_attrib_monitor_read(CohRepReader *,CohAttribMonitor *,CohAttribMonitorWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
