#ifndef COH_DB_ACCOUNT_CONTROLS_H
#define COH_DB_ACCOUNT_CONTROLS_H
#include "coh_dbclient.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { COH_DB_ACCOUNT_CHARCOUNT=8, COH_DB_ACCOUNT_UNAVAILABLE=14 };
/* Explicit native refusal domains, not original server wire limits. */
#define COH_DB_ACCOUNT_SHARDS_MAX 256u
#define COH_DB_ACCOUNT_STRING_MAX 16384u /* Includes the terminating NUL. */
typedef struct {
    uint32_t command, shards, error_branch;
} CohDbAccountControl;
/* Complete logical packet including its command. No text/row values escape.
 * UNAVAILABLE admits only the original command-only sender/Queue relay form;
 * the distinct direct relay with an ignored string is deliberately refused.
 * CHARCOUNT retains only its branch and row count: it grants no account,
 * catalog, transfer, character-list, authentication or world authority.
 * All row scalars preserve source U32 decoding; no count relationships or
 * Boolean constraint on vip-only status are invented. Positive shard counts
 * must fit the explicit bounded domain (therefore the original signed loop).
 * Input remains immutable/live for the call. Output must be aligned and
 * disjoint from the complete declared input span; failures leave it unchanged.
 * No heap, callbacks, string copies, UI effects, sends, or retained leases. */
CohStatus coh_db_account_control_parse(CohBytes, size_t bit_length,
    int byte_aligned, int legacy_commands, CohDbAccountControl *);
#ifdef __cplusplus
}
#endif
#endif
