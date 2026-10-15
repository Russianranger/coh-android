#ifndef COH_PERF_H
#define COH_PERF_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Opt-in, single-owner observer. Callers provide MONOTONIC nanoseconds; no clock,
 * GL, allocation, locking or platform calls occur in sampling methods.
 * No sample from this module is proof of full-game or physical performance. */
#define COH_PERF_SCHEMA 1u
#define COH_PERF_HISTOGRAM_BINS 257u
#define COH_PERF_BUCKET_NS 500000u
typedef enum {
  COH_PERF_ANIMATION, COH_PERF_SKINNING, COH_PERF_COLLISION,
  COH_PERF_ASSET_LOADING, COH_PERF_RENDER_SUBMIT, COH_PERF_PRESENT,
  COH_PERF_AUDIO_CONTROL, COH_PERF_STAGE_COUNT
} CohPerfStage;
typedef enum {
  COH_PERF_COPIED_BYTES, COH_PERF_UPLOAD_BYTES, COH_PERF_DRAW_CALLS,
  COH_PERF_STATE_BINDS, COH_PERF_SKINNED_VERTICES, COH_PERF_COLLISION_TESTS,
  COH_PERF_ASSET_HITS, COH_PERF_ASSET_MISSES, COH_PERF_ASSET_EVICTIONS,
  COH_PERF_READBACKS, COH_PERF_EXPLICIT_WAITS, COH_PERF_ALLOCATIONS,
  COH_PERF_COUNTER_COUNT
} CohPerfCounter;
typedef struct {
  uint64_t samples, sum_ns, max_ns;
  uint64_t bins[COH_PERF_HISTOGRAM_BINS];
} CohPerfHistogram;
typedef struct {
  uint32_t enabled; /* 0 disables all sample/counter collection. */
  uint32_t stage_mask; /* Bit per CohPerfStage. */
  uint64_t target_frame_ns, stall_ns;
} CohPerfConfig;
typedef struct {
  uint32_t schema, enabled, paused, surface_generation;
  uint64_t epoch, dropped_frames, invalid_samples, over_budget, stalls;
  uint64_t gpu_unavailable, gpu_disjoint, gpu_stale, gpu_not_ready;
  uint64_t counters[COH_PERF_COUNTER_COUNT];
  uint64_t resident_bytes, peak_resident_bytes;
  CohPerfHistogram frame, gpu, stages[COH_PERF_STAGE_COUNT];
} CohPerfSnapshot;
typedef struct {
  CohPerfConfig config;
  CohPerfSnapshot snapshot;
  uint64_t frame_start_ns, stage_start_ns[COH_PERF_STAGE_COUNT];
  uint32_t active_frame, active_stages;
} CohPerf;
CohPerfConfig coh_perf_default_config(void);
CohStatus coh_perf_init(CohPerf *, const CohPerfConfig *);
/* Reconfigure preserves collected data; discards unfinished measurements. */
CohStatus coh_perf_configure(CohPerf *, const CohPerfConfig *);
/* Pauses/surface changes cancel unfinished scopes, never include background
 * time. CPU statistics persist. A new Surface increments the logical epoch. */
void coh_perf_set_paused(CohPerf *, int paused);
void coh_perf_surface(CohPerf *, uint32_t generation);
CohStatus coh_perf_frame_begin(CohPerf *, uint64_t now_ns, uint32_t generation);
CohStatus coh_perf_frame_end(CohPerf *, uint64_t now_ns);
CohStatus coh_perf_stage_begin(CohPerf *, CohPerfStage, uint64_t now_ns);
CohStatus coh_perf_stage_end(CohPerf *, CohPerfStage, uint64_t now_ns);
CohStatus coh_perf_count(CohPerf *, CohPerfCounter, uint64_t count);
void coh_perf_resident(CohPerf *, uint64_t bytes);
/* Adapter supplies an already-ready asynchronous timer-query result. This
 * function NEVER polls GL, blocks, creates a fence or infers GPU time from CPU.
 * ready=0/disjoint/stale generation are diagnostics only, not timing samples. */
CohStatus coh_perf_gpu_sample(CohPerf *, uint32_t generation, uint64_t elapsed_ns,
                             int ready, int disjoint);
/* Preferred queued-query API. Capture snapshot.epoch when submitting the query;
 * pause/resume invalidates its epoch even if the GL Surface is unchanged.
 * The shorter gpu_sample is for an already-ready current-epoch result only. */
CohStatus coh_perf_gpu_sample_epoch(CohPerf *, uint32_t generation, uint64_t epoch,
                                   uint64_t elapsed_ns, int ready, int disjoint);
void coh_perf_gpu_unavailable(CohPerf *);
void coh_perf_snapshot(const CohPerf *, CohPerfSnapshot *);
/* Conservative bucket upper bound, overflow bucket uses observed max. q=1..100.
 * Returns 0 for invalid/empty input. This is NOT an exact percentile. */
uint64_t coh_perf_percentile_upper_ns(const CohPerfHistogram *, uint32_t q);
/* Control-thread bounded JSON, including counters and stage summaries. libc
 * formatting is used only here, never in a sampling or audio callback. On COH_LIMIT the
 * required byte count INCLUDING NUL is returned and output is empty if cap>0. */
CohStatus coh_perf_json(const CohPerf *, char *output, size_t cap, size_t *needed);
#ifdef __cplusplus
}
#endif
#endif
