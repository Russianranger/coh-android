#ifndef COH_DB_ACCOUNT_INVENTORY_H
#define COH_DB_ACCOUNT_INVENTORY_H
#include "coh_db_account_controls.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { COH_DB_ACCOUNT_INVENTORY=13 };
#define COH_DB_ACCOUNT_ITEMS_MAX 1024u /* Native refusal domain, not source max. */
typedef struct {
    uint32_t items;
    /* Decoded one-bit wire value only, never authenticated inventory authority. */
    uint32_t wire_authoritative;
} CohDbAccountInventory;
/* Complete DBGAMESERVER_ACCOUNTSERVER_INVENTORY logical envelope, including
 * command, both flags, transfer tokens, NUL shard name, all SKU/count/expiration
 * fields, aligned 128 loyalty bits and all seven Auto tail scalars. Only the
 * count and wire flag survive: no SKU, text, entitlement, loyalty, account flags,
 * currency or bonus-slot values escape. No catalog/character/costume state is
 * created. This does not apply the original UI's authoritative-cache policy.
 * Even a UI-ignored cached envelope must pass this whole-body validator.
 * Legacy/profile, limits, immutable input and disjoint/aligned output contracts
 * match coh_db_account_control_parse. Errors preserve output. No heap/callbacks.
 */
CohStatus coh_db_account_inventory_parse(CohBytes, size_t bit_length,
    int byte_aligned, int legacy_commands, CohDbAccountInventory *);
#ifdef __cplusplus
}
#endif
#endif
