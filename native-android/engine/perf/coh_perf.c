#include "coh_perf.h"
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static uint64_t add(uint64_t a, uint64_t b) {
  return UINT64_MAX - a < b ? UINT64_MAX : a + b;
}
static int config_valid(const CohPerfConfig *c) {
  return c && c->enabled <= 1 && !(c->stage_mask >> COH_PERF_STAGE_COUNT) &&
         c->target_frame_ns && c->stall_ns >= c->target_frame_ns;
}
static void histogram(CohPerfHistogram *h, uint64_t ns) {
  uint64_t bucket = ns / COH_PERF_BUCKET_NS;
  if (bucket >= COH_PERF_HISTOGRAM_BINS) bucket = COH_PERF_HISTOGRAM_BINS - 1;
  h->samples = add(h->samples, 1);
  h->sum_ns = add(h->sum_ns, ns);
  if (ns > h->max_ns) h->max_ns = ns;
  h->bins[bucket] = add(h->bins[bucket], 1);
}
static void abandon(CohPerf *p) {
  if (p->active_frame)
    p->snapshot.dropped_frames = add(p->snapshot.dropped_frames, 1);
  p->active_frame = p->active_stages = 0;
}
static CohStatus invalid(CohPerf *p, CohStatus status) {
  if (p && p->config.enabled)
    p->snapshot.invalid_samples = add(p->snapshot.invalid_samples, 1);
  return status;
}
CohPerfConfig coh_perf_default_config(void) {
  CohPerfConfig c = {1, (1u << COH_PERF_STAGE_COUNT) - 1, 33333333, 100000000};
  return c;
}
CohStatus coh_perf_init(CohPerf *p, const CohPerfConfig *c) {
  if (!p || !config_valid(c)) return COH_INVALID;
  memset(p, 0, sizeof *p);
  p->config = *c;
  p->snapshot.schema = COH_PERF_SCHEMA;
  p->snapshot.enabled = c->enabled;
  p->snapshot.epoch = 1;
  return COH_OK;
}
CohStatus coh_perf_configure(CohPerf *p, const CohPerfConfig *c) {
  if (!p || !config_valid(c)) return COH_INVALID;
  abandon(p);
  p->config = *c;
  p->snapshot.enabled = c->enabled;
  return COH_OK;
}
void coh_perf_set_paused(CohPerf *p, int paused) {
  if (!p) return;
  if (!!paused != !!p->snapshot.paused) {
    abandon(p);
    p->snapshot.epoch = add(p->snapshot.epoch, 1);
  }
  p->snapshot.paused = !!paused;
}
void coh_perf_surface(CohPerf *p, uint32_t generation) {
  if (!p || generation == p->snapshot.surface_generation) return;
  abandon(p);
  p->snapshot.surface_generation = generation;
  p->snapshot.epoch = add(p->snapshot.epoch, 1);
}
CohStatus coh_perf_frame_begin(CohPerf *p, uint64_t now, uint32_t generation) {
  if (!p) return COH_INVALID;
  if (!p->config.enabled) return COH_OK;
  if (p->snapshot.paused || p->active_frame ||
      generation != p->snapshot.surface_generation)
    return invalid(p, COH_STATE);
  p->frame_start_ns = now;
  p->active_frame = 1;
  return COH_OK;
}
CohStatus coh_perf_frame_end(CohPerf *p, uint64_t now) {
  if (!p) return COH_INVALID;
  if (!p->config.enabled) return COH_OK;
  if (!p->active_frame || p->snapshot.paused) return invalid(p, COH_STATE);
  if (now < p->frame_start_ns) {
    abandon(p);
    return invalid(p, COH_INVALID);
  }
  if (p->active_stages) invalid(p, COH_STATE);
  uint64_t elapsed = now - p->frame_start_ns;
  histogram(&p->snapshot.frame, elapsed);
  if (elapsed > p->config.target_frame_ns)
    p->snapshot.over_budget = add(p->snapshot.over_budget, 1);
  if (elapsed >= p->config.stall_ns)
    p->snapshot.stalls = add(p->snapshot.stalls, 1);
  p->active_frame = p->active_stages = 0;
  return COH_OK;
}
CohStatus coh_perf_stage_begin(CohPerf *p, CohPerfStage stage, uint64_t now) {
  if (!p || (unsigned)stage >= COH_PERF_STAGE_COUNT) return COH_INVALID;
  if (!p->config.enabled || !(p->config.stage_mask & (1u << stage))) return COH_OK;
  if (!p->active_frame || (p->active_stages & (1u << stage)))
    return invalid(p, COH_STATE);
  if (now < p->frame_start_ns) return invalid(p, COH_INVALID);
  p->stage_start_ns[stage] = now;
  p->active_stages |= 1u << stage;
  return COH_OK;
}
CohStatus coh_perf_stage_end(CohPerf *p, CohPerfStage stage, uint64_t now) {
  if (!p || (unsigned)stage >= COH_PERF_STAGE_COUNT) return COH_INVALID;
  if (!p->config.enabled || !(p->config.stage_mask & (1u << stage))) return COH_OK;
  if (!(p->active_stages & (1u << stage))) return invalid(p, COH_STATE);
  p->active_stages &= ~(1u << stage);
  if (now < p->stage_start_ns[stage]) return invalid(p, COH_INVALID);
  histogram(&p->snapshot.stages[stage], now - p->stage_start_ns[stage]);
  return COH_OK;
}
CohStatus coh_perf_count(CohPerf *p, CohPerfCounter counter, uint64_t value) {
  if (!p || (unsigned)counter >= COH_PERF_COUNTER_COUNT) return COH_INVALID;
  if (p->config.enabled && !p->snapshot.paused)
    p->snapshot.counters[counter] = add(p->snapshot.counters[counter], value);
  return COH_OK;
}
void coh_perf_resident(CohPerf *p, uint64_t bytes) {
  if (!p || !p->config.enabled) return;
  p->snapshot.resident_bytes = bytes;
  if (bytes > p->snapshot.peak_resident_bytes) p->snapshot.peak_resident_bytes = bytes;
}
CohStatus coh_perf_gpu_sample_epoch(CohPerf *p, uint32_t generation, uint64_t epoch,
                                   uint64_t ns, int ready, int disjoint) {
  if (!p) return COH_INVALID;
  if (!p->config.enabled) return COH_OK;
  if (generation != p->snapshot.surface_generation || epoch != p->snapshot.epoch || p->snapshot.paused) {
    p->snapshot.gpu_stale = add(p->snapshot.gpu_stale, 1);
    return COH_STATE;
  }
  if (!ready) {
    p->snapshot.gpu_not_ready = add(p->snapshot.gpu_not_ready, 1);
    return COH_OK;
  }
  if (disjoint) {
    p->snapshot.gpu_disjoint = add(p->snapshot.gpu_disjoint, 1);
    return COH_OK;
  }
  histogram(&p->snapshot.gpu, ns);
  return COH_OK;
}
CohStatus coh_perf_gpu_sample(CohPerf *p, uint32_t generation, uint64_t ns,
                             int ready, int disjoint) {
  return coh_perf_gpu_sample_epoch(p, generation, p ? p->snapshot.epoch : 0,
                                   ns, ready, disjoint);
}
void coh_perf_gpu_unavailable(CohPerf *p) {
  if (p && p->config.enabled)
    p->snapshot.gpu_unavailable = add(p->snapshot.gpu_unavailable, 1);
}
void coh_perf_snapshot(const CohPerf *p, CohPerfSnapshot *out) {
  if (p && out) *out = p->snapshot;
}
uint64_t coh_perf_percentile_upper_ns(const CohPerfHistogram *h, uint32_t q) {
  if (!h || !h->samples || !q || q > 100) return 0;
  /* ceil(samples*q/100) without overflowing. */
  uint64_t rank = (h->samples / 100) * q + ((h->samples % 100) * q + 99) / 100;
  uint64_t seen = 0;
  for (unsigned i = 0; i < COH_PERF_HISTOGRAM_BINS; i++) {
    seen = add(seen, h->bins[i]);
    if (seen >= rank) {
      uint64_t upper = ((uint64_t)i + 1) * COH_PERF_BUCKET_NS - 1;
      return i == COH_PERF_HISTOGRAM_BINS - 1 || upper > h->max_ns ? h->max_ns : upper;
    }
  }
  return h->max_ns;
}
typedef struct { char *out; size_t cap, used; int failed; } Json;
static void append(Json *j, const char *format, ...) {
  va_list args;
  va_start(args, format);
  size_t left = j->used < j->cap ? j->cap - j->used : 0;
  int n = vsnprintf(left ? j->out + j->used : NULL, left, format, args);
  va_end(args);
  if (n < 0 || (size_t)n > SIZE_MAX - j->used) j->failed = 1;
  else j->used += (size_t)n;
}
static void json_histogram(Json *j, const CohPerfHistogram *h) {
  append(j, "{\"samples\":%" PRIu64 ",\"sum_ns\":%" PRIu64 ",\"max_ns\":%" PRIu64
         ",\"p50_upper_ns\":%" PRIu64 ",\"p95_upper_ns\":%" PRIu64 ",\"p99_upper_ns\":%" PRIu64 "}",
         h->samples, h->sum_ns, h->max_ns,
         coh_perf_percentile_upper_ns(h, 50), coh_perf_percentile_upper_ns(h, 95),
         coh_perf_percentile_upper_ns(h, 99));
}
CohStatus coh_perf_json(const CohPerf *p, char *output, size_t cap, size_t *needed) {
  static const char *const stages[COH_PERF_STAGE_COUNT] = {
    "animation", "skinning", "collision", "asset_loading", "render_submit", "present", "audio_control"};
  static const char *const counters[COH_PERF_COUNTER_COUNT] = {
    "copied_bytes", "upload_bytes", "draw_calls", "state_binds", "skinned_vertices",
    "collision_tests", "asset_hits", "asset_misses", "asset_evictions", "readbacks", "explicit_waits", "allocations"};
  if (!p || (!output && cap) || !needed) return COH_INVALID;
  const CohPerfSnapshot *s = &p->snapshot;
  Json j = {output, cap, 0, 0};
  append(&j, "{\"schema\":%u,\"module\":\"coh-native-perf\",\"time_unit\":\"ns\","
         "\"clock\":\"caller_monotonic\",\"percentile_bucket_ns\":%u,\"enabled\":%s,\"paused\":%s,"
         "\"surface_generation\":%u,\"epoch\":%" PRIu64 ",\"target_frame_ns\":%" PRIu64
         ",\"stall_ns\":%" PRIu64 ",\"dropped_frames\":%" PRIu64 ",\"invalid_samples\":%" PRIu64
         ",\"over_budget\":%" PRIu64 ",\"stalls\":%" PRIu64 ",\"resident_bytes\":%" PRIu64
         ",\"peak_resident_bytes\":%" PRIu64 ",\"gpu_unavailable\":%" PRIu64
         ",\"gpu_disjoint\":%" PRIu64 ",\"gpu_stale\":%" PRIu64 ",\"gpu_not_ready\":%" PRIu64 ",\"frame\":",
         s->schema, COH_PERF_BUCKET_NS, s->enabled ? "true" : "false", s->paused ? "true" : "false",
         s->surface_generation, s->epoch, p->config.target_frame_ns, p->config.stall_ns,
         s->dropped_frames, s->invalid_samples, s->over_budget, s->stalls,
         s->resident_bytes, s->peak_resident_bytes, s->gpu_unavailable, s->gpu_disjoint,
         s->gpu_stale, s->gpu_not_ready);
  json_histogram(&j, &s->frame);
  append(&j, ",\"gpu\":"); json_histogram(&j, &s->gpu);
  append(&j, ",\"stages\":{");
  for (unsigned i = 0; i < COH_PERF_STAGE_COUNT; i++) {
    append(&j, "%s\"%s\":", i ? "," : "", stages[i]);
    json_histogram(&j, &s->stages[i]);
  }
  append(&j, "},\"counters\":{");
  for (unsigned i = 0; i < COH_PERF_COUNTER_COUNT; i++)
    append(&j, "%s\"%s\":%" PRIu64, i ? "," : "", counters[i], s->counters[i]);
  append(&j, "}}");
  if (j.failed || j.used == SIZE_MAX) { if (cap) output[0] = 0; return COH_LIMIT; }
  *needed = j.used + 1;
  if (*needed > cap) { if (cap) output[0] = 0; return COH_LIMIT; }
  return COH_OK;
}
