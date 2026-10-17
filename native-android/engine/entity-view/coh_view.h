#ifndef COH_VIEW_H
#define COH_VIEW_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_VIEW_RAM_MAX (8u*1024u*1024u)
#define COH_VIEW_STACK_RESERVE 4096u
typedef struct{
 uint32_t sky_interesting,sky1,sky2,sky_weight_word,slave_present,slave_pyr_words[3];
 size_t begin_bit,sky_end_bit,end_bit;
}CohWorldView;
typedef struct{CohWorldView candidate;}CohWorldViewWorkspace;
/* Original final sky/slave PYR subtransaction. Sky IDs raw; defaults0,1,0 are
 * source receiver defaults only. Camera PYR is not character orientation/identity.
 * No sky resource, camera application, packet-end, fullupdate or ACK authority.
 * Pairwise disjoint input/reader/output/workspace, caller-owned POD; aggregate
 * input+bothPODs+4096stack+retained<=8MiB. Failure preserves reader and output. */
CohStatus coh_world_view_read(CohRepReader *,CohWorldView *,CohWorldViewWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
