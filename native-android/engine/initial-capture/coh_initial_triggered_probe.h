#ifndef COH_INITIAL_TRIGGERED_PROBE_H
#define COH_INITIAL_TRIGGERED_PROBE_H
#include "../entities/coh_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_TRIGGERED_INPUT=1,COH_INITIAL_TRIGGERED_COUNT,COH_INITIAL_TRIGGERED_INDEX,
 COH_INITIAL_TRIGGERED_TICKS,COH_INITIAL_TRIGGERED_FX,COH_INITIAL_TRIGGERED_AI_ANIMATION
} CohInitialTriggeredStage;
typedef struct {
 CohStatus status;CohInitialTriggeredStage stage;
 size_t begin_bit,count_end_bit,triggered_end_bit,failure_bit;
 uint32_t count,count_validated,entries_validated,current_entry,fx_entries,triggered_moves_validated;
} CohInitialTriggeredProbe;
/* Diagnostic full-create leaf after the validated sequence in the SAME loan.
 * The enclosing owner supplies sequence_end_bit; never scan for a count.
 * Pack1 count -> count repetitions of Pack10 index, Pack6 delayed ticks and
 * Boolean/optional Pack16 FX. Preserve local COH_ENT_TRIGGER_MAX=16, although
 * the original source supports20. Larger counts are LIMIT at this explicit
 * native profile boundary, not proof of a malformed original packet.
 * Index/ticks retain existing signed32 consumer bounds; FX remains fullU32.
 * Compressed Pack widths are minima, not scalar maxima; Boolean still<=1.
 *
 * Zero count is valid, including the original set_triggered_moves branch.
 * Complete list returns UNSUPPORTED before AI animation; no following bits
 * returns INVALID there while triggered_moves_validated stays true. Partial
 * entry progress is numeric diagnostic evidence only. No entries, values,
 * packet pointers, FX/resource identities or actor state are retained/applied.
 * No animation-string parsing, ordering/dictionary generation or ACK permit.
 * Inputs are immutable; invalid API inputs/aliases preserve output. Syntax
 * refusals initialize the first failure stage/cursor and complete-entry count.
 * No allocation; existing4MiB reader and fixed report limits remain in force.
 */
CohStatus coh_initial_triggered_probe(const CohRepReader *trigger_start,
 CohInitialTriggeredProbe *);
#define COH_INITIAL_TRIGGERED_REPORT_MAX 1024u
int coh_initial_triggered_probe_json(const CohInitialTriggeredProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
