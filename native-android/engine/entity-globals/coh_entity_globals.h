#ifndef COH_ENTITY_GLOBALS_H
#define COH_ENTITY_GLOBALS_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Local admission policy, not an assertion about the original earray limit.
 * IDs remain uninterpreted source int bit patterns, including duplicates and
 * order. They do not authorize powers, actor animation or appearance. */
#define COH_GLOBAL_POWER_MODE_MAX 1024u
typedef struct {
    uint32_t count;
    uint32_t modes[COH_GLOBAL_POWER_MODE_MAX];
} CohPowerModes;
typedef struct { uint32_t replacement_present; } CohPowerModeEvent;

/* Exact standalone entity_ReceivePowerModeUpdate body. Starts AFTER the
 * separate, unsupported PowerInfoUpdate grammar, before BadgeUpdate. This is
 * not an ALLENTS, character, entity, packet-order or acknowledgment parser.
 *
 * Absent update preserves state byte-for-byte; a present empty list clears it.
 * Present lists replace state, preserve IDs/order/duplicates, and zero unused
 * slots. On any error reader, state and event remain byte-for-byte unchanged.
 * No allocation, dictionary lookup, retained input, UI or renderer side effect.
 * Mutable reader/state/event and borrowed input must be disjoint; overlap is
 * rejected before writes. The caller owns input until this call returns and
 * must serialize access to reader/state/event. State count must be <= the cap.
 * One 4100-byte local candidate is used in addition to the caller's 4100-byte
 * state and input reader; no per-mode allocation. The enclosing transaction
 * must stage this state and enforce identity/order/budgets before publication.
 */
CohStatus coh_global_power_modes(CohRepReader *reader, CohPowerModes *state,
    CohPowerModeEvent *event);
#ifdef __cplusplus
}
#endif
#endif
