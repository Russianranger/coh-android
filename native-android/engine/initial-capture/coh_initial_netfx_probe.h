#ifndef COH_INITIAL_NETFX_PROBE_H
#define COH_INITIAL_NETFX_PROBE_H
#include "../entities/coh_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_NETFX_INPUT=1,COH_INITIAL_NETFX_FLAGS,COH_INITIAL_NETFX_BODY,
 COH_INITIAL_NETFX_COSTUME
} CohInitialNetFxStage;
typedef struct {
 CohStatus status;CohInitialNetFxStage stage;
 size_t begin_bit,flags_end_bit,netfx_end_bit,failure_bit;
 uint32_t pchar_things,in_phase,body_present,effect_count,netfx_validated;
 CohEntFailure entity_failure;
} CohInitialNetFxProbe;
/* Diagnostic initial full-create leaf after AI animation in the SAME immutable
 * ALLENTS loan. The enclosing owner supplies that exact boundary; never scan.
 * Read both pchar_things and inPhase booleans. Only their conjunction carries
 * a complete NetFX list, decoded by the existing transactional public parser.
 * Every Boolean combination is supported; the first entity need not be self.
 * Cross-prefix equality with the earlier create inPhase has NOT been proved.
 *
 * Preserve the existing native32-effect and all child scalar/reference/finite
 * float bounds. Original effects use a dynamic array;32 is a native diagnostic
 * limit. No dictionary/resource lookup, effect execution or actor ordering.
 * Scratch entries are discarded; only effect count after complete child success
 * and bounded numeric diagnostics survive. Conditional-off is a validated empty
 * stage, not an omitted count. Stop BEFORE costume, never parse its selector.
 * Complete stage returns UNSUPPORTED/COSTUME, or INVALID there if no next bits.
 * Inputs stay immutable; invalid API inputs/aliases leave output unchanged.
 * No allocation; existing4MiB input ceiling and fixed report limit remain.
 */
CohStatus coh_initial_netfx_probe(const CohRepReader *,CohInitialNetFxProbe *);
#define COH_INITIAL_NETFX_REPORT_MAX 1024u
int coh_initial_netfx_probe_json(const CohInitialNetFxProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
