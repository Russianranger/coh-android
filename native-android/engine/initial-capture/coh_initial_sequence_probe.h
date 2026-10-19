#ifndef COH_INITIAL_SEQUENCE_PROBE_H
#define COH_INITIAL_SEQUENCE_PROBE_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_SEQUENCE_INPUT=1,COH_INITIAL_SEQUENCE_UPDATE,COH_INITIAL_SEQUENCE_INDEX,
 COH_INITIAL_SEQUENCE_TICKS,COH_INITIAL_SEQUENCE_MOVE_BITS,COH_INITIAL_SEQUENCE_TRIGGERS
} CohInitialSequenceStage;
typedef struct {
 CohStatus status;CohInitialSequenceStage stage;
 size_t begin_bit,index_end_bit,ticks_end_bit,sequence_end_bit,failure_bit;
 uint32_t update_seen,index_present,ticks_present,movement_bits_present,sequence_validated;
} CohInitialSequenceProbe;
/* Diagnostic INITIAL full-create sequence leaf, starting at the exact end of
 * the validated mode/pose prefix in the same immutable ALLENTS loan. The owner
 * supplies that boundary, never scans for it. Raw syntax only; no ordering or
 * dictionary generation is invented and no sequence/actor state is applied.
 *
 * Source update1 -> optional Pack8 index -> optional Pack4 ticks -> optional
 * scalar11 movement bits. Index/ticks retain the established consumer bounds
 * INT32_MAX/U16_MAX. Original server timing storage is U8; wider fixture values
 * qualify consumer-range syntax only, not representable server object state.
 * All rounded booleans/scalars are width checked in compressed profile too.
 * Absent optional fields are legitimate zero values. Absent update refuses
 * this initial profile. Stop BEFORE triggered-move count; successful syntax
 * returns UNSUPPORTED/TRIGGERS, or INVALID there when no following bits exist.
 *
 * Report retains only offsets/presence and no movement index/ticks/bit values,
 * packet pointer or resource identity. Inputs are unchanged on every return.
 * Invalid API inputs/aliases leave output unchanged; syntax refusals initialize
 * it with the first bounded failure. No allocations; existing4MiB cap applies.
 */
CohStatus coh_initial_sequence_probe(const CohRepReader *sequence_start,
 CohInitialSequenceProbe *);
#define COH_INITIAL_SEQUENCE_REPORT_MAX 1024u
int coh_initial_sequence_probe_json(const CohInitialSequenceProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
