#include "../coh_renderer.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
typedef struct {
  unsigned next, compile, destroy, bind, draw;
  CohStatus compile_fail, bind_fail, draw_fail;
  uint64_t sequences[32];
  CohMaterialFamily families[32];
} Mock;
static CohStatus compile(void *ctx, CohMaterialFamily f, const char *v,
                         const char *s, uint32_t *out) {
  Mock *m = ctx;
  assert(strstr(v, "#version 300 es"));
  assert(strstr(s, "#define MATERIAL"));
  (void)f;
  m->compile++;
  if (m->compile_fail)
    return m->compile_fail;
  *out = ++m->next;
  return COH_OK;
}
static void destroy(void *ctx, uint32_t p) {
  Mock *m = ctx;
  assert(p);
  m->destroy++;
}
static CohStatus bind(void *ctx, uint32_t p, const CohRenderMaterial *mat) {
  Mock *m = ctx;
  assert(p);
  assert(mat);
  m->bind++;
  return m->bind_fail;
}
static CohStatus draw(void *ctx, uint32_t p, const CohRenderDraw *d) {
  Mock *m = ctx;
  assert(p);
  if (m->draw < 32) {
    m->sequences[m->draw] = d->sequence;
    m->families[m->draw] = d->material.family;
  }
  m->draw++;
  return m->draw_fail;
}
static int cancel(void *ctx) { return *(int *)ctx; }
static void identity(float *m) {
  unsigned i;
  memset(m, 0, 16 * sizeof(float));
  for (i = 0; i < 4; ++i)
    m[i * 5] = 1;
}
static const CohRenderVertex vertices[] = {
    {{-1, -1, -1}, {0, 0, 1}, {0, 0}, {0, 0}, {.25f, .25f, .25f, 1}},
    {{1, -1, -1}, {0, 0, 1}, {1, 0}, {1, 0}, {.25f, .25f, .25f, 1}},
    {{0, 1, -1}, {0, 0, 1}, {.5f, 1}, {.5f, 1}, {.25f, .25f, .25f, 1}}};
static const uint32_t indices[] = {0, 1, 2};
static CohRenderDraw fixture(CohMaterialFamily f) {
  CohRenderDraw d;
  memset(&d, 0, sizeof d);
  d.geometry = (CohRenderGeometry){vertices, 3, indices, 3, 1, 1};
  d.material = coh_renderer_default_material(f);
  identity(d.model_view);
  identity(d.projection);
  return d;
}
int main(void) {
  CohRenderer *r = NULL;
  CohRendererConfig config = {8, 8, 12, 2};
  Mock mock = {0};
  CohRenderBackend b = {compile, destroy, bind, draw, &mock};
  CohRenderDraw d = fixture(COH_MAT_MULTIPLY), e = fixture(COH_MAT_DUAL);
  CohRendererStats stats;
  int stop = 1;
  float clip[4], normal[3], lit[4], fog, out[4] = {7, 7, 7, 7},
                                         base[4] = {.4f, .6f, .8f, .25f},
                                         dual[4] = {.3f, .5f, .7f, .5f};
  int discarded = -1;
  unsigned i;
  double sustained_cpu = 0;
  assert(coh_renderer_create(&config, &b, &r) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_STATE);
  assert(coh_renderer_begin(r, 0) == COH_OK);
  assert(coh_renderer_begin(r, 0) == COH_STATE);
  /* Reorder opaque within a run, but never across a translucent barrier. */
  assert(coh_renderer_submit(r, &e) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  e.material.blend = COH_BLEND_ALPHA;
  assert(coh_renderer_submit(r, &e) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  assert(coh_renderer_flush(r, (CohCancel){0}) == COH_OK);
  assert(mock.draw == 5 && mock.bind == 4 && mock.compile == 2);
  assert(mock.sequences[0] == 1 && mock.sequences[1] == 2 &&
         mock.sequences[2] == 0 && mock.sequences[3] == 3 &&
         mock.sequences[4] == 4);
  stats = coh_renderer_stats(r);
  assert(stats.queued == 0 && stats.owned_bytes > 0 &&
         stats.high_water_draws == 5 && stats.borrowed_vertex_bytes == 0);
  assert(coh_renderer_begin(r, 0) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  assert(coh_renderer_flush(r, (CohCancel){cancel, &stop}) == COH_CANCELLED);
  assert(mock.draw == 5);
  assert(coh_renderer_begin(r, 0) == COH_OK);
  d.geometry.index_count = 2;
  assert(coh_renderer_submit(r, &d) == COH_INVALID);
  d = fixture(COH_MAT_MULTIPLY);
  {
    uint32_t bad[] = {0, 1, 9};
    d.geometry.indices = bad;
    assert(coh_renderer_submit(r, &d) == COH_INVALID);
  }
  d = fixture(COH_MAT_MULTIPLY);
  d.material.alpha_ref = NAN;
  assert(coh_renderer_submit(r, &d) == COH_INVALID);
  d = fixture(COH_MAT_MULTIPLY);
  d.material.textures[0].mag_filter = COH_FILTER_MIP_LINEAR;
  assert(coh_renderer_submit(r, &d) == COH_INVALID);
  d = fixture(COH_MAT_MULTIPLY);
  d.model_view[0] = INFINITY;
  assert(coh_renderer_submit(r, &d) == COH_INVALID);
  d = fixture(COH_MAT_MULTIPLY);
  {
    CohRenderVertex bad[3];
    memcpy(bad, vertices, sizeof bad);
    bad[0].normal[2] = 0;
    d.geometry.vertices = bad;
    assert(coh_renderer_submit(r, &d) == COH_INVALID);
  }
  d = fixture(COH_MAT_MULTIPLY);
  for (i = 0; i < 8; ++i) {
    assert(coh_renderer_submit(r, &d) == COH_OK);
  }
  assert(coh_renderer_submit(r, &d) == COH_LIMIT);
  coh_renderer_surface_lost(r, 7, 0);
  assert(coh_renderer_stats(r).queued == 0 && mock.destroy == 0);
  assert(coh_renderer_begin(r, 0) == COH_STATE);
  assert(coh_renderer_begin(r, 7) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  mock.compile_fail = COH_UNSUPPORTED;
  assert(coh_renderer_flush(r, (CohCancel){0}) == COH_UNSUPPORTED);
  mock.compile_fail = COH_OK;
  assert(coh_renderer_begin(r, 7) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  mock.bind_fail = COH_STATE;
  assert(coh_renderer_flush(r, (CohCancel){0}) == COH_STATE);
  mock.bind_fail = COH_OK;
  assert(coh_renderer_begin(r, 7) == COH_OK);
  assert(coh_renderer_submit(r, &d) == COH_OK);
  mock.draw_fail = COH_IO;
  assert(coh_renderer_flush(r, (CohCancel){0}) == COH_IO);
  mock.draw_fail = COH_OK;
  coh_renderer_surface_lost(r, 8, 1);
  assert(mock.destroy == 1);
  coh_renderer_destroy(r);
  r = NULL;
  /* Single-slot cache can compile-before-evict safely and release every name.
   */
  memset(&mock, 0, sizeof mock);
  config.shader_capacity = 1;
  assert(coh_renderer_create(&config, &b, &r) == COH_OK);
  for (i = 0; i < 3; ++i) {
    d = fixture((CohMaterialFamily)i);
    assert(coh_renderer_begin(r, 0) == COH_OK);
    assert(coh_renderer_submit(r, &d) == COH_OK);
    assert(coh_renderer_flush(r, (CohCancel){0}) == COH_OK);
  }
  stats = coh_renderer_stats(r);
  assert(stats.compiles == 3 && stats.evictions == 2 && mock.destroy == 2);
  {
    size_t bytes = stats.owned_bytes;
    clock_t start = clock();
    for (i = 0; i < 20000; ++i) {
      assert(coh_renderer_begin(r, 0) == COH_OK);
      assert(coh_renderer_submit(r, &d) == COH_OK);
      assert(coh_renderer_flush(r, (CohCancel){0}) == COH_OK);
    }
    sustained_cpu = (double)(clock() - start) / CLOCKS_PER_SEC;
    stats = coh_renderer_stats(r);
    assert(stats.owned_bytes == bytes && stats.compiles == 3 &&
           stats.queued == 0 && stats.drawn == 20003);
  }
  coh_renderer_destroy(r);
  assert(mock.destroy == 3);
  config.max_draws = (size_t)-1;
  assert(coh_renderer_create(&config, &b, &r) == COH_LIMIT);
  /* Source math: alpha mask roles, strict GREATER, ADDGLOW mask < threshold,
     FF_LIT_GL specular is NOT disabled on a negative light dot product. */
  d = fixture(COH_MAT_DUAL);
  d.material.fog_params[2] = 100;
  d.material.const0[3] = .5f;
  assert(coh_renderer_fragment(&d.material, base, dual, 0, vertices[0].color, 1,
                               out, &discarded) == COH_OK);
  assert(out[3] == .25f && !discarded);
  d.material.alpha_ref = .25f;
  assert(coh_renderer_fragment(&d.material, base, dual, 0, vertices[0].color, 1,
                               out, &discarded) == COH_OK &&
         discarded);
  d.material.alpha_ref = NAN;
  out[0] = 7;
  assert(coh_renderer_fragment(&d.material, base, dual, 0, vertices[0].color, 1,
                               out, &discarded) == COH_INVALID &&
         out[0] == 7);
  d = fixture(COH_MAT_ADDGLOW);
  d.material.fog_params[2] = 100;
  d.material.glow_params[0] = .5f;
  assert(coh_renderer_fragment(&d.material, base, dual, .5f, vertices[0].color,
                               1, out, &discarded) == COH_OK);
  {
    float n = out[0];
    assert(coh_renderer_fragment(&d.material, base, dual, .499f,
                                 vertices[0].color, 1, out,
                                 &discarded) == COH_OK);
    assert(fabsf(out[0] - n - dual[0]) < 1e-6f);
  }
  d = fixture(COH_MAT_MULTIPLY);
  assert(coh_renderer_vertex(&d, &vertices[0], clip, normal, lit, &fog) ==
         COH_OK);
  assert(clip[0] == -1 && clip[3] == 1 && normal[2] == 1 &&
         fabsf(fog - sqrtf(3.f)) < 1e-6f);
  {
    float src[] = {1, 0, 0, .5f}, dst[] = {0, 1, 0, .5f};
    coh_renderer_blend(COH_BLEND_ALPHA, src, dst, out);
    assert(out[0] == .5f && out[1] == .5f && out[3] == .5f);
    coh_renderer_blend(COH_BLEND_ADDITIVE, src, dst, out);
    assert(out[3] == .75f);
  }
  printf(
      "{\"passed\":true,\"negative_cases\":12,\"queue_lifecycle_cache_checks\":"
      "true,\"owned_bytes\":%zu,\"sustained_frames\":20000,\"module_allocation_"
      "growth_bytes\":0,\"sustained_host_cpu_seconds\":%.6f}\n",
      stats.owned_bytes, sustained_cpu);
  return 0;
}
