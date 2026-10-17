#ifndef COH_INITIAL_LIST_H
#define COH_INITIAL_LIST_H
#include "coh_initial_record.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INITIAL_LIST_STACK_RESERVE (COH_SELECTED_RECORD_STACK_RESERVE+32768u)
typedef struct{
 uint32_t index,entity_id,dbid,type,is_self,rare_flags,position_valid,orientation_valid;
 size_t begin_bit,end_bit;CohVec3 position;float quaternion[4];
}CohInitialListEntry;
typedef struct{
 CohBytes packet;size_t packet_bits,begin_bit,end_bit;uint64_t packet_lease_token;
 uint32_t packet_id,count,self_index,selected_dbid,raw_list_validated,unique_selected_self;
 CohSelectedRecord selected_record;
 uint32_t complete_initial_update,dictionary_authority,actor_publication,ack_permitted;
}CohInitialList;
typedef struct{CohStatus status;size_t bit;uint32_t ordinal,index;CohSelectedRecordFailure record;}CohInitialListFailure;
typedef struct{const void*pointer;size_t bytes;}CohInitialListSpan;
typedef struct{
 const CohSelectedRecordMemory*original;CohInitialListSpan spans[10];
}CohInitialListAllocator;
typedef struct{
 CohInitialList candidate;CohInitialListEntry entries[COH_ENT_LIST_MAX];
 CohRepReader reader;CohSelectedRecordContext context;CohEntSlot prior;
 CohSelectedRecord record;CohSelectedRecordWorkspace record_workspace;
 CohSelectedRecordMemory adapter;CohInitialListAllocator allocator;
}CohInitialListWorkspace;
/* Complete bounded INITIAL/create-only entity-list wire fragment, including
 * canonical sentinel, not the control/delete/character/global/command tails.
 * context.entity_index must be0: decoded list indices own that association.
 * Packet ID/DBID/dictionary/lease must come from the enclosing qualified owner;
 * this raw contract cannot authenticate supplied context integers or handles.
 * At most COH_ENT_LIST_MAX(256) records, preserving the existing local bound.
 * Signed-negative source delta encodings and slot-MAX+1 sentinel are supported.
 * No noncreate/interpolated records, missing selected self, duplicate slot/
 * server entity ID/player DBID, or other-player selected DBID alias is admitted.
 * Compact entries retain raw identity/pose and exact record spans; appearance,
 * powers/SG/buffs occupy one scratch loan at a time. No large POD per slot.
 * All required records must validate before output entries/reader/result commit;
 * on failure only workspace and diagnostic failure may change. Concurrent
 * publication needs the enclosing owner's synchronization after return.
 * Public input/output/entry/workspace/provider/context/dictionary spans must be
 * pairwise disjoint. Loan adapter additionally checks ALL enclosing spans.
 * Budget charges full supplied entry capacity, workspace, input, dictionary,
 * retained/context bytes, active pre-reserved loan and96KiB native stack.
 * Existing stricter4MiB SG/buff child caps remain. Output packet/dictionary lease
 * lifetimes and allocator rules inherit the selected-record contract. Entries
 * are caller-owned and immutable while the returned view is in use.
 * A whole raw list establishes only this fragment's unique selected self;
 * no authoritative actor, complete initial update or completion ACK is minted.
 */
CohStatus coh_initial_list_read(CohRepReader*,const CohSelectedRecordContext*,
 const CohSelectedRecordMemory*,CohInitialListEntry*,size_t capacity,CohInitialList*,
 CohInitialListWorkspace*,CohInitialListFailure*,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
