#ifndef COH_CHARACTER_PREFIX_H
#define COH_CHARACTER_PREFIX_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_AUTH_BYTES 128u
typedef struct {
    uint32_t boost_diminishing,power_diminishing,no_base_edit,beta_base,base_raid;
    uint8_t auth_user_data[COH_CHARACTER_AUTH_BYTES];
    uint32_t player_type,player_subtype,praetorian_progress,player_type_by_location;
    size_t begin_bit,end_bit;
} CohCharacterPrefix;
/* Exact sendCharacterToClient/receiveCharacterFromServer pre-character boundary.
 * Packed server settings are raw words, not assumed booleans. Auth data uses
 * original byte-array alignment even on non-byte-aligned packets. Data may
 * contain account entitlements: do not log/export auth_user_data by default.
 * No dictionary lookup, entitlement application, character identity, complete
 * transaction, actor publication or ACK. Subsequent character_Receive must pass
 * within the same enclosing transaction. Input/output/reader must be disjoint.
 * Allocation-free. Reader/output unchanged on refusal. */
CohStatus coh_character_prefix(CohRepReader *,CohCharacterPrefix *);
#ifdef __cplusplus
}
#endif
#endif
