#ifndef COH_ENTITY_FRAME_H
#define COH_ENTITY_FRAME_H
#include "../entities/coh_entities.h"
#include "../entity-control/coh_entity_control.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ENTITY_FRAME_RAM_MAX (8u*1024u*1024u)
#define COH_ENTITY_FRAME_STACK_RESERVE 65536u
typedef struct{
 uint32_t selected_dbid,packet_id,session_generation,schema_generation,legacy_commands;
 uint64_t packet_lease_token;
}CohEntityFrameContext;
typedef struct{
 CohBytes packet;size_t packet_bits,begin_bit,header_end_bit,list_end_bit,control_end_bit,end_bit;
 uint64_t packet_lease_token;uint32_t packet_id,session_generation;
 CohRepUpdatePrefix header;CohEntList list;CohEntSlot selected;
 CohControlUpdate control;CohEntDeletes deletes;
 uint32_t selected_wire_identity_matched,character_suffix_validated,dictionary_authority;
 uint32_t transport_end_verified,complete_initial_update,actor_publication,ack_permitted;
}CohEntityFrame;
typedef struct{
 CohEntityFrame candidate;CohEntSlot slots[COH_ENT_LIST_MAX];CohEntListWorkspace list;
}CohEntityFrameWorkspace;
typedef enum{COH_FRAME_COMMAND=1,COH_FRAME_HEADER,COH_FRAME_LIST,COH_FRAME_CONTROL,COH_FRAME_DELETES,COH_FRAME_SELECTED}CohEntityFrameStage;
typedef struct{CohStatus status;CohEntityFrameStage stage;size_t bit;CohEntFailure entity;CohControlFailure control;}CohEntityFrameFailure;
/* Diagnostic full-update prelude: reads command/header→entity list→non-debug
 * control→deletes, stops exactly BEFORE receiveCharacterFromServer. Uses existing
 * qualified parsers; never skips unsupported record/control/debug grammar.
 * Full update resets every admitted index to original empty/tombstone defaults;
 * indices are caller's bounded slot admission set, not fabricated entity records.
 * Unknown indices refuse. At least one source self must match selected_dbid;
 * duplicate self and deletion/identity conflicts refuse atomically.
 * Caller binds selected_dbid to its real DB selection and schema to same session;
 * raw context integers do not authenticate a server. legacy selects the existing
 * normalized/old+5 command profile. Full odd_send must1 per original producer.
 * All explicit spans pairwise disjoint; output/workspace heap/arena-owned.
 * Budget charges full input+schema+indices+context+reader+output+workspace+failure+
 *64KiB native reserve+retained<=8MiB. Reader/output atomic on refusal, workspace
 * scratch. Caller retains immutable packet while views/spans are used; lease
 * token labels lifetime only. No suffix/dictionary/transport-end/actor/ACK permit. */
CohStatus coh_entity_frame_read(CohRepReader *,const CohEntityFrameContext *,
 const CohRepSchema *,const uint32_t*admitted_indices,size_t count,
 CohEntityFrame *,CohEntityFrameWorkspace *,CohEntityFrameFailure *,
 size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
