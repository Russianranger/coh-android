#include "coh_renderer.h"
#include "coh_renderer_shaders.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
typedef struct {
  uint32_t program;
  CohMaterialFamily family;
  uint64_t use;
  int valid;
} Shader;
struct CohRenderer {
  CohRendererConfig config;
  CohRenderBackend backend;
  CohRenderDraw *draws;
  Shader *shaders;
  CohRendererStats stats;
  uint64_t clock;
  int active;
};
static float clamp01(float x) { return fminf(1.f, fmaxf(0.f, x)); }
static float lerp(float a, float b, float t) { return a + (b - a) * t; }
static int finite_n(const float *v, size_t n) {
  size_t i;
  for (i = 0; i < n; ++i)
    if (!isfinite(v[i]))
      return 0;
  return 1;
}
static int mul_size(size_t a, size_t b, size_t *out) {
  if (b && a > SIZE_MAX / b)
    return 0;
  *out = a * b;
  return 1;
}
static void transform(const float *m, const float *v, float w, float *out,
                      int n) {
  int i;
  for (i = 0; i < n; ++i)
    out[i] =
        ((m[i] * v[0] + m[4 + i] * v[1]) + m[8 + i] * v[2]) + m[12 + i] * w;
}
static int normalize(float *v) {
  float d = (v[0] * v[0] + v[1] * v[1]) + v[2] * v[2];
  float k;
  if (!isfinite(d) || d <= 0)
    return 0;
  k = 1.f / sqrtf(d);
  v[0] *= k;
  v[1] *= k;
  v[2] *= k;
  return finite_n(v, 3);
}
static int valid_material(const CohRenderMaterial *m) {
  size_t i;
  if (m->family < COH_MAT_MULTIPLY || m->family > COH_MAT_ADDGLOW ||
      m->lighting < COH_LIGHT_VERTEX || m->lighting > COH_LIGHT_FIXED ||
      m->blend < COH_BLEND_OPAQUE || m->blend > COH_BLEND_ADDITIVE ||
      m->depth_test > 1 || m->depth_write > 1 || m->cull_back > 1 ||
      m->front_cw > 1)
    return 0;
  if (!finite_n(m->const0, 4) || !finite_n(m->const1, 4) ||
      !finite_n(m->fog_params, 4) || !finite_n(m->fog_color, 4) ||
      !finite_n(m->glow_params, 4) || !finite_n(m->light, 3) ||
      !finite_n(m->diffuse, 4) || !finite_n(m->ambient, 4) ||
      !finite_n(m->specular, 3) || !isfinite(m->alpha_ref) ||
      m->alpha_ref < 0 || m->alpha_ref > 1 || !isfinite(m->shininess) ||
      m->shininess < 0 || m->shininess > 128)
    return 0;
  for (i = 0; i < 3; ++i) {
    const CohRenderTexture *t = &m->textures[i];
    if (t->wrap_s < COH_WRAP_REPEAT || t->wrap_s > COH_WRAP_MIRROR ||
        t->wrap_t < COH_WRAP_REPEAT || t->wrap_t > COH_WRAP_MIRROR ||
        t->min_filter < COH_FILTER_NEAREST ||
        t->min_filter > COH_FILTER_MIP_LINEAR ||
        t->mag_filter < COH_FILTER_NEAREST || t->mag_filter > COH_FILTER_LINEAR)
      return 0;
  }
  return 1;
}
CohRendererConfig coh_renderer_default_config(void) {
  CohRendererConfig c = {512, 65536, 196608, 3};
  return c;
}
CohRenderMaterial coh_renderer_default_material(CohMaterialFamily f) {
  CohRenderMaterial m;
  size_t i;
  memset(&m, 0, sizeof m);
  m.family = f;
  m.light[2] = 1;
  m.fog_params[2] = 1;
  m.fog_params[3] = 1;
  m.shininess = 1;
  m.depth_test = m.depth_write = m.cull_back = m.front_cw = 1;
  for (i = 0; i < 4; ++i)
    m.const0[i] = m.const1[i] = m.ambient[i] = 1;
  return m;
}
CohStatus coh_renderer_create(const CohRendererConfig *c,
                              const CohRenderBackend *b, CohRenderer **out) {
  CohRenderer *r;
  size_t d, s;
  if (!c || !b || !out || !b->compile || !b->destroy_program || !b->bind ||
      !b->draw || !c->max_draws || !c->max_vertices_per_draw ||
      !c->max_indices_per_draw || !c->shader_capacity || c->shader_capacity > 3)
    return COH_INVALID;
  if (!mul_size(c->max_draws, sizeof(CohRenderDraw), &d) ||
      !mul_size(c->shader_capacity, sizeof(Shader), &s) ||
      d > SIZE_MAX - s - sizeof(*r))
    return COH_LIMIT;
  if (*out)
    return COH_STATE;
  r = calloc(1, sizeof(*r));
  if (!r)
    return COH_LIMIT;
  r->draws = calloc(c->max_draws, sizeof(*r->draws));
  r->shaders = calloc(c->shader_capacity, sizeof(*r->shaders));
  if (!r->draws || !r->shaders) {
    free(r->draws);
    free(r->shaders);
    free(r);
    return COH_LIMIT;
  }
  r->config = *c;
  r->backend = *b;
  r->stats.owned_bytes = sizeof(*r) + d + s;
  *out = r;
  return COH_OK;
}
void coh_renderer_destroy(CohRenderer *r) {
  if (!r)
    return;
  coh_renderer_surface_lost(r, 0, 1);
  free(r->draws);
  free(r->shaders);
  free(r);
}
CohStatus coh_renderer_begin(CohRenderer *r, uint32_t gen) {
  if (!r)
    return COH_INVALID;
  if (r->active || r->stats.queued)
    return COH_STATE;
  if (gen != r->stats.surface_generation)
    return COH_STATE;
  r->active = 1;
  return COH_OK;
}
CohStatus coh_renderer_submit(CohRenderer *r, const CohRenderDraw *d) {
  size_t i, vb, ib;
  if (!r || !d)
    return COH_INVALID;
  if (!r->active)
    return COH_STATE;
  if (!valid_material(&d->material) || !finite_n(d->model_view, 16) ||
      !finite_n(d->projection, 16) || !d->geometry.vertices ||
      !d->geometry.indices || !d->geometry.vertex_count ||
      !d->geometry.index_count || d->geometry.index_count % 3) {
    r->stats.rejected++;
    return COH_INVALID;
  }
  if (r->stats.queued == r->config.max_draws ||
      d->geometry.vertex_count > r->config.max_vertices_per_draw ||
      d->geometry.index_count > r->config.max_indices_per_draw ||
      !mul_size(d->geometry.vertex_count, sizeof(CohRenderVertex), &vb) ||
      !mul_size(d->geometry.index_count, sizeof(uint32_t), &ib) ||
      r->stats.borrowed_vertex_bytes > SIZE_MAX - vb ||
      r->stats.borrowed_index_bytes > SIZE_MAX - ib) {
    r->stats.rejected++;
    return COH_LIMIT;
  }
  for (i = 0; i < d->geometry.vertex_count; ++i) {
    float clip[4], normal[3], lit[4], fog;
    const CohRenderVertex *v = &d->geometry.vertices[i];
    if (!finite_n(v->position, 3) || !finite_n(v->normal, 3) ||
        !finite_n(v->uv0, 2) || !finite_n(v->uv1, 2) ||
        !finite_n(v->color, 4) ||
        coh_renderer_vertex(d, v, clip, normal, lit, &fog) != COH_OK) {
      r->stats.rejected++;
      return COH_INVALID;
    }
  }
  for (i = 0; i < d->geometry.index_count; ++i)
    if (d->geometry.indices[i] >= d->geometry.vertex_count) {
      r->stats.rejected++;
      return COH_INVALID;
    }
  r->draws[r->stats.queued] = *d;
  r->draws[r->stats.queued].sequence = r->stats.submitted++;
  r->stats.queued++;
  r->stats.borrowed_vertex_bytes += vb;
  r->stats.borrowed_index_bytes += ib;
  if (r->stats.queued > r->stats.high_water_draws)
    r->stats.high_water_draws = r->stats.queued;
  return COH_OK;
}
static int compare_pipeline(const CohRenderMaterial *a,
                            const CohRenderMaterial *b) {
  size_t i;
#define CMP(field)                                                             \
  if (a->field != b->field)                                                    \
  return a->field < b->field ? -1 : 1
  CMP(family);
  CMP(blend);
  CMP(depth_test);
  CMP(depth_write);
  CMP(cull_back);
  CMP(front_cw);
  for (i = 0; i < 3; ++i) {
    CMP(textures[i].handle);
    CMP(textures[i].wrap_s);
    CMP(textures[i].wrap_t);
    CMP(textures[i].min_filter);
    CMP(textures[i].mag_filter);
  }
#undef CMP
  return 0;
}
static int compare_draw(const void *aa, const void *bb) {
  const CohRenderDraw *a = aa, *b = bb;
  int c = compare_pipeline(&a->material, &b->material);
  return c ? c : (a->sequence > b->sequence) - (a->sequence < b->sequence);
}
/* Constant-storage heapsort, sequence is a unique tie-breaker. libc qsort
 * implementations may allocate a merge buffer; frame submission must not. */
static void sift_draws(CohRenderDraw *d, size_t root, size_t n) {
  while (root < n / 2) {
    size_t child = root * 2 + 1;
    CohRenderDraw swap;
    if (child + 1 < n && compare_draw(d + child, d + child + 1) < 0)
      ++child;
    if (compare_draw(d + root, d + child) >= 0)
      return;
    swap = d[root];
    d[root] = d[child];
    d[child] = swap;
    root = child;
  }
}
static void sort_draws(CohRenderDraw *d, size_t n) {
  size_t i;
  CohRenderDraw swap;
  if (n < 2)
    return;
  for (i = n / 2; i > 0; --i)
    sift_draws(d, i - 1, n);
  for (i = n - 1; i > 0; --i) {
    swap = d[0];
    d[0] = d[i];
    d[i] = swap;
    sift_draws(d, 0, i);
  }
}
static CohStatus program_for(CohRenderer *r, CohMaterialFamily f, uint32_t *p) {
  size_t i, slot = 0;
  uint32_t made = 0;
  CohStatus s;
  for (i = 0; i < r->config.shader_capacity; ++i)
    if (r->shaders[i].valid && r->shaders[i].family == f) {
      r->shaders[i].use = ++r->clock;
      *p = r->shaders[i].program;
      r->stats.cache_hits++;
      return COH_OK;
    }
  for (i = 0; i < r->config.shader_capacity; ++i) {
    if (!r->shaders[i].valid) {
      slot = i;
      break;
    }
    if (r->shaders[i].use < r->shaders[slot].use)
      slot = i;
  }
  s = r->backend.compile(r->backend.context, f, coh_renderer_vertex_shader(),
                         coh_renderer_fragment_shader(f), &made);
  if (s != COH_OK || !made) {
    if (made)
      r->backend.destroy_program(r->backend.context, made);
    return s == COH_OK ? COH_STATE : s;
  }
  if (r->shaders[slot].valid) {
    r->backend.destroy_program(r->backend.context, r->shaders[slot].program);
    r->stats.evictions++;
  }
  r->shaders[slot] = (Shader){made, f, ++r->clock, 1};
  r->stats.compiles++;
  *p = made;
  return COH_OK;
}
CohStatus coh_renderer_flush(CohRenderer *r, CohCancel cancel) {
  size_t i, first;
  uint32_t program = 0, previous = 0;
  CohStatus status = COH_OK;
  const CohRenderMaterial *bound = NULL;
  if (!r)
    return COH_INVALID;
  if (!r->active)
    return COH_STATE;
  /* Never move opaque geometry across a translucent submission. */
  for (first = 0; first < r->stats.queued;) {
    size_t end = first;
    if (r->draws[first].material.blend != COH_BLEND_OPAQUE) {
      ++first;
      continue;
    }
    while (end < r->stats.queued &&
           r->draws[end].material.blend == COH_BLEND_OPAQUE)
      ++end;
    sort_draws(r->draws + first, end - first);
    first = end;
  }
  for (i = 0; i < r->stats.queued; ++i) {
    const CohRenderDraw *d = &r->draws[i];
    if (cancel.poll && cancel.poll(cancel.context)) {
      r->stats.cancelled++;
      status = COH_CANCELLED;
      break;
    }
    status = program_for(r, d->material.family, &program);
    if (status != COH_OK)
      break;
    if (!bound || program != previous ||
        compare_pipeline(bound, &d->material)) {
      status = r->backend.bind(r->backend.context, program, &d->material);
      if (status != COH_OK)
        break;
      r->stats.state_binds++;
      bound = &d->material;
      previous = program;
    }
    status = r->backend.draw(r->backend.context, program, d);
    if (status != COH_OK)
      break;
    r->stats.drawn++;
  }
  r->stats.queued = r->stats.borrowed_vertex_bytes =
      r->stats.borrowed_index_bytes = 0;
  r->active = 0;
  return status;
}
void coh_renderer_surface_lost(CohRenderer *r, uint32_t gen, int alive) {
  size_t i;
  if (!r)
    return;
  for (i = 0; i < r->config.shader_capacity; ++i) {
    if (alive && r->shaders[i].valid)
      r->backend.destroy_program(r->backend.context, r->shaders[i].program);
    memset(&r->shaders[i], 0, sizeof(Shader));
  }
  r->stats.surface_generation = gen;
  r->stats.queued = r->stats.borrowed_vertex_bytes =
      r->stats.borrowed_index_bytes = 0;
  r->active = 0;
}
CohRendererStats coh_renderer_stats(const CohRenderer *r) {
  CohRendererStats empty = {0};
  return r ? r->stats : empty;
}
CohStatus coh_renderer_vertex(const CohRenderDraw *d, const CohRenderVertex *v,
                              float clip[4], float normal[3], float lit[4],
                              float *fog) {
  float p[3], n[3], c[4], l[4], f, ndl;
  size_t i;
  if (!d || !v || !clip || !normal || !lit || !fog ||
      !valid_material(&d->material) || !finite_n(d->model_view, 16) ||
      !finite_n(d->projection, 16) || !finite_n(v->position, 3) ||
      !finite_n(v->normal, 3) || !finite_n(v->color, 4))
    return COH_INVALID;
  transform(d->model_view, v->position, 1, p, 3);
  transform(d->model_view, v->normal, 0, n, 3);
  if (!normalize(n))
    return COH_INVALID;
  transform(d->projection, p, 1, c, 4);
  f = sqrtf((p[0] * p[0] + p[1] * p[1]) + p[2] * p[2] + 1e-16f);
  ndl = (n[0] * d->material.light[0] + n[1] * d->material.light[1]) +
        n[2] * d->material.light[2];
  if (d->material.lighting == COH_LIGHT_VERTEX)
    memcpy(l, v->color, sizeof l);
  else if (d->material.lighting == COH_LIGHT_DIFFUSE)
    for (i = 0; i < 4; ++i)
      l[i] = clamp01(ndl) * d->material.diffuse[i] + d->material.ambient[i];
  else {
    float view[3] = {-p[0], -p[1], -p[2]}, half[3], spec;
    if (!normalize(view))
      return COH_INVALID;
    for (i = 0; i < 3; ++i)
      half[i] = d->material.light[i] + view[i];
    if (!normalize(half))
      return COH_INVALID;
    spec = powf(clamp01((n[0] * half[0] + n[1] * half[1]) + n[2] * half[2]),
                d->material.shininess);
    for (i = 0; i < 3; ++i)
      l[i] = (clamp01(ndl * d->material.diffuse[i]) + d->material.ambient[i]) *
                 v->color[i] +
             spec * d->material.specular[i];
    l[3] = v->color[3];
  }
  if (!finite_n(c, 4) || !finite_n(l, 4) || !isfinite(f))
    return COH_INVALID;
  memcpy(clip, c, sizeof c);
  memcpy(normal, n, sizeof n);
  memcpy(lit, l, sizeof l);
  *fog = f;
  return COH_OK;
}
CohStatus coh_renderer_fragment(const CohRenderMaterial *m, const float base[4],
                                const float dual[4], float mask,
                                const float lit[4], float fog, float rgba[4],
                                int *discard) {
  float result[4], fog_amount;
  size_t i;
  if (!m || !base || !dual || !lit || !rgba || !discard || !valid_material(m) ||
      !finite_n(base, 4) || !finite_n(dual, 4) || !finite_n(lit, 4) ||
      !isfinite(mask) || !isfinite(fog))
    return COH_INVALID;
  for (i = 0; i < 3; ++i) {
    if (m->family == COH_MAT_MULTIPLY)
      result[i] = base[i] * dual[i] * (8.f * lit[i]);
    else if (m->family == COH_MAT_DUAL)
      result[i] =
          lerp(lerp(m->const1[i], m->const0[i], dual[i]), 1.f, base[3]) *
          base[i] * 4.f * lit[i];
    else {
      result[i] = lerp(m->const0[i], base[i], base[3]) * 4.f * lit[i];
      if (mask < m->glow_params[0])
        result[i] += dual[i];
    }
  }
  result[3] =
      m->family == COH_MAT_MULTIPLY
          ? base[3] * dual[3] * m->const0[3]
          : (m->family == COH_MAT_DUAL ? dual[3] * m->const0[3] : m->const0[3]);
  fog_amount = clamp01(m->fog_params[3] * (m->fog_params[2] - fog));
  for (i = 0; i < 3; ++i)
    result[i] = lerp(m->fog_color[i], result[i], fog_amount);
  if (!finite_n(result, 4))
    return COH_INVALID;
  *discard = !(result[3] > m->alpha_ref);
  memcpy(rgba, result, sizeof result);
  return COH_OK;
}
void coh_renderer_blend(CohBlend mode, const float src[4], const float dst[4],
                        float out[4]) {
  float s[4], d[4];
  size_t i;
  for (i = 0; i < 4; ++i) {
    s[i] = clamp01(src[i]);
    d[i] = clamp01(dst[i]);
  }
  for (i = 0; i < 4; ++i)
    out[i] = mode == COH_BLEND_OPAQUE
                 ? s[i]
                 : clamp01(s[i] * s[3] +
                           d[i] * (mode == COH_BLEND_ALPHA ? 1.f - s[3] : 1.f));
}
const char *coh_renderer_vertex_shader(void) { return vertex_shader; }
const char *coh_renderer_fragment_shader(CohMaterialFamily f) {
  switch (f) {
  case COH_MAT_MULTIPLY:
    return fragment_shader_0;
  case COH_MAT_DUAL:
    return fragment_shader_1;
  case COH_MAT_ADDGLOW:
    return fragment_shader_2;
  default:
    return NULL;
  }
}

const char *coh_renderer_vertex_shader_precise(void) {
  return vertex_shader_320;
}
const char *coh_renderer_fragment_shader_precise(CohMaterialFamily f) {
  switch (f) {
  case COH_MAT_MULTIPLY:
    return fragment_shader_320_0;
  case COH_MAT_DUAL:
    return fragment_shader_320_1;
  case COH_MAT_ADDGLOW:
    return fragment_shader_320_2;
  default:
    return NULL;
  }
}

size_t coh_renderer_allocation_bytes(size_t draws,size_t shaders){
  size_t d,s;if(!draws||!shaders||shaders>3||!mul_size(draws,sizeof(CohRenderDraw),&d)||!mul_size(shaders,sizeof(Shader),&s)||d>SIZE_MAX-s-sizeof(CohRenderer))return 0;
  return sizeof(CohRenderer)+d+s;
}
