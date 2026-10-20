#ifndef COH_ORIGINAL_ENT_COSTUME_H
#define COH_ORIGINAL_ENT_COSTUME_H
#include "coh_original_costume_receive.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_ENT_COSTUME_STACK_RESERVE 8192u
enum {COH_ENT_COSTUME_SELECTOR=1,COH_ENT_COSTUME_REWARDS=2,
 COH_ENT_COSTUME_BODY=3,COH_ENT_COSTUME_SG_FLAG=4,COH_ENT_COSTUME_SG_BODY=5,
 COH_ENT_COSTUME_SG_MODE=6,COH_ENT_COSTUME_SG_HIDE=7,
 COH_ENT_COSTUME_FX_FLAG=8,COH_ENT_COSTUME_FX_STRING=9,
 COH_ENT_COSTUME_NPC_FLAG=10,COH_ENT_COSTUME_NPC_FIELDS=11,
 COH_ENT_COSTUME_NPC_CUSTOM=12,COH_ENT_COSTUME_APPEARANCE_END=13,
 COH_ENT_COSTUME_XLUCENCY=14,COH_ENT_COSTUME_SUFFIX=15,
 COH_ENT_COSTUME_NPC_DEFINITIONS=16,COH_ENT_COSTUME_POWER_SELECTOR=17,
 COH_ENT_COSTUME_POWER_LIST=18,COH_ENT_COSTUME_POWER_CRC=19,
 COH_ENT_COSTUME_TITLES=20,COH_ENT_COSTUME_RAGDOLL=21,
 COH_ENT_COSTUME_BASIC_STATS=22,COH_ENT_COSTUME_VISION=23};
typedef struct {
 CohStatus status;size_t begin_bit,end_bit,failure_bit,packet_bits,appearance_end_bit,main_body_end_bit,selected_body_end_bit,power_begin_bit,power_end_bit;
 uint32_t field,selector,bodies_expected,bodies_read,selected_body,
  selected_complete,supergroup_present,supergroup_complete,supergroup_mode,
  hide_emblem,fx_present,fx_bytes,npc_fallthrough,npc_index,npc_costume_index,
  appearance_complete,xlucency_complete,entity_complete,message_complete,
  power_selector,power_complete,power_lists_read,power_entry_count,power_crc,required_table,
  titles_complete,ragdoll_complete,basic_stats_complete;
 CohOriginalCostumeReport body;
} CohOriginalEntCostumeReport;
/* Entry is the actual original appearance-selector cursor in the same decoded
 * ALLENTS reader. Run the whole unchanged entReceiveCostume, original
 * entReceiveXlucency and entReceivePowerCust. Native scalar/storage wrappers discard cosmetic/UI side
 * effects and never claim a loaded actor. Existing CLIENT tables and body
 * workspace remain immutable/exclusive as in the body decoder. Capture, when
 * supplied, publishes only the selected complete main body (not an SG costume).
 * NPC appearance identifiers/custom colors are decoded without publishing a
 * model or consulting a cosmetic NPC definition while in the discard profile.
 * Nonempty power customization needs the original BasePower CRC lookup, absent
 * from this caller; stop at that actual callback and retain its requested CRC.
 * COH_OK means this bounded appearance component completed, never end-of-entity
 * or end-of-message; unknown suffix bits stay unread.
 * The caller charges all owner/source/index/message resources, capture and this
 * stack reserve under the unchanged 8 MiB initial aggregate. No heap allocation.
 */
CohStatus coh_original_ent_costume_receive(const CohRepReader *,uint32_t body_parts,
 uint32_t selected_body,const CohClientCostumeSlots *,CohOriginalCostumeWorkspace *,
 CohOriginalCostumeSnapshot *,CohOriginalEntCostumeReport *);
/* Initial profile requires the already source-validated initial create/self and
 * all rare flags; pchar_things is the actual original earlier wire flag. */
CohStatus coh_original_ent_costume_receive_initial(const CohRepReader *,uint32_t,
 uint32_t,uint32_t pchar_things,const CohClientCostumeSlots *,
 CohOriginalCostumeWorkspace *,CohOriginalCostumeSnapshot *,CohOriginalEntCostumeReport *);
const char *coh_original_ent_costume_field_name(uint32_t);
#ifdef __cplusplus
}
#endif
#endif
