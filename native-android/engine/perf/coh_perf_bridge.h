#ifndef COH_PERF_BRIDGE_H
#define COH_PERF_BRIDGE_H
#include "coh_perf.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
    COH_PERF_MEMORY_ACCOUNTED, /* Explicit caller-owned module bytes, not RSS. */
    COH_PERF_MEMORY_RSS, COH_PERF_MEMORY_PSS, COH_PERF_MEMORY_COUNT
} CohPerfMemoryKind;
typedef struct {
    uint64_t generation, total, observations, rebases, rejected;
    uint32_t known, baseline;
} CohPerfCounterBinding;
typedef struct { uint64_t current_bytes, peak_bytes, observations; } CohPerfMemoryGauge;
typedef struct {
    CohPerfCounterBinding counters[COH_PERF_COUNTER_COUNT];
    CohPerfMemoryGauge memory[COH_PERF_MEMORY_COUNT];
} CohPerfBridge;
/* One owner serializes bridge and CohPerf sampling. Fixed caller-owned storage;
 * no allocation, locks, GL, file I/O, platform calls or clock reads. Initialize
 * together with a NEW perf observer. No cross-observer reuse without reinit. */
void coh_perf_bridge_init(CohPerfBridge *);
/* Feed monotonically increasing OWNER totals, not frame deltas. First total
 * establishes a baseline without counting unknown earlier work. Change nonzero
 * owner_generation when that source resets/recreates; this rebases, preserving
 * perf history. A decrease within one generation is rejected without mutation
 * of its baseline (COH_STATE), NEVER inferred as uint64 rollover. Bind each
 * counter exclusively to one source; combine totals at caller if necessary.
 * Baselines advance during disabled/paused periods so those deltas stay excluded.
 * Do not mix total and delta mode for one counter before reinitializing. */
CohStatus coh_perf_bridge_total(CohPerfBridge *,CohPerf *,CohPerfCounter,
                                uint64_t owner_generation,uint64_t total);
/* Explicit operation deltas, including zero. Marks that counter measured, so a
 * measured zero is distinguishable from unknown/unconnected. Mutually exclusive
 * with total mode per counter. Both modes use saturating existing perf sums. */
CohStatus coh_perf_bridge_delta(CohPerfBridge *,CohPerf *,CohPerfCounter,uint64_t delta);
/* Measurement kind and presence are explicit. Never label module-accounted
 * bytes as RSS/PSS; unknown gauges remain unknown. Sampling belongs off hot
 * paths if obtaining the supplied bytes involves OS/file work. */
CohStatus coh_perf_bridge_memory(CohPerfBridge *,CohPerfMemoryKind,uint64_t bytes);
/* Bounded owner/export-thread JSON. Includes known flags, total source baseline,
 * generation, observations, rebase/rejection counts, distinct memory gauges.
 * Values are uint64 (beware JavaScript precision >2^53). COH_LIMIT reports
 * needed including NUL, empties output if cap>0. No live callback stats read. */
CohStatus coh_perf_bridge_json(const CohPerfBridge *,char *,size_t cap,size_t *needed);
#ifdef __cplusplus
}
#endif
#endif
