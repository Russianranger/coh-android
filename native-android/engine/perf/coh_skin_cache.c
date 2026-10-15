#include "coh_skin_cache.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
  CohSkinKey key;
  uint64_t age;
  uint32_t valid, vertices, bones;
  CohMeshVertex *source;
  float *palette;
  CohSkinnedVertex *output;
} Slot;
struct CohSkinCache {
  CohSkinCacheConfig config;
  CohSkinCacheStats stats;
  uint64_t serial;
  Slot slots[];
};
static uint64_t add(uint64_t a, uint64_t b) {
  return UINT64_MAX - a < b ? UINT64_MAX : a + b;
}
static int same_key(CohSkinKey a, CohSkinKey b) {
  return a.mesh == b.mesh && a.rig == b.rig && a.pose == b.pose &&
         a.mesh_generation == b.mesh_generation &&
         a.rig_generation == b.rig_generation && a.pose_generation == b.pose_generation;
}
static int valid_key(CohSkinKey k) {
  return k.mesh && k.rig && k.pose && k.mesh_generation && k.rig_generation && k.pose_generation;
}
CohStatus coh_skin_cache_create(const CohSkinCacheConfig *cfg, CohSkinCache **out) {
  if (!cfg || !out || !cfg->entries || cfg->entries > 64 || !cfg->max_vertices ||
      cfg->max_vertices > COH_MESH_MAX_VERTICES || !cfg->max_bones ||
      cfg->max_bones > COH_MESH_MAX_BONES) return COH_INVALID;
  /* All limits are small constants above; arithmetic is valid also on 32-bit. */
  size_t stride = (size_t)cfg->max_vertices * (sizeof(CohMeshVertex) + sizeof(CohSkinnedVertex)) +
                  (size_t)cfg->max_bones * 12 * sizeof(float);
  size_t metadata = sizeof(CohSkinCache) + (size_t)cfg->entries * sizeof(Slot);
  if (stride > (SIZE_MAX - metadata) / cfg->entries) return COH_LIMIT;
  size_t bytes = metadata + stride * cfg->entries;
  if (bytes > cfg->byte_budget) return COH_LIMIT;
  CohSkinCache *c = calloc(1, bytes);
  if (!c) return COH_IO;
  c->config = *cfg; c->stats.allocated_bytes = bytes;
  uint8_t *at = (uint8_t *)c + metadata;
  for (uint32_t i = 0; i < cfg->entries; i++) {
    c->slots[i].source = (CohMeshVertex *)at;
    at += (size_t)cfg->max_vertices * sizeof(CohMeshVertex);
    c->slots[i].palette = (float *)at;
    at += (size_t)cfg->max_bones * 12 * sizeof(float);
    c->slots[i].output = (CohSkinnedVertex *)at;
    at += (size_t)cfg->max_vertices * sizeof(CohSkinnedVertex);
  }
  *out = c;
  return COH_OK;
}
void coh_skin_cache_destroy(CohSkinCache **c) {
  if (c) { free(*c); *c = NULL; }
}
void coh_skin_cache_invalidate(CohSkinCache *c) {
  if (!c) return;
  for (uint32_t i = 0; i < c->config.entries; i++) c->slots[i].valid = 0;
  c->stats.resident_entries = 0;
  c->stats.invalidations = add(c->stats.invalidations, 1);
}
CohSkinCacheStats coh_skin_cache_stats(const CohSkinCache *c) {
  CohSkinCacheStats s = {0};
  return c ? c->stats : s;
}
static uint64_t next_age(CohSkinCache *c) {
  if (c->serial == UINT64_MAX) {
    for (uint32_t i = 0; i < c->config.entries; i++) c->slots[i].age = 0;
    c->serial = 0;
  }
  return ++c->serial;
}
CohStatus coh_skin_cache_sample(CohSkinCache *c, CohSkinKey key,
                               const CohMeshVertex *vertices, uint32_t count,
                               const float *palette, uint32_t bones,
                               const CohSkinnedVertex **out, int *hit) {
  if (!c) return COH_INVALID;
  if (!vertices || !palette || !out || !count || count > c->config.max_vertices ||
      !bones || bones > c->config.max_bones || !valid_key(key)) {
    c->stats.rejections = add(c->stats.rejections, 1);
    return COH_INVALID;
  }
  Slot *victim = NULL;
  size_t vb = (size_t)count * sizeof(CohMeshVertex), pb = (size_t)bones * 12 * sizeof(float);
  for (uint32_t i = 0; i < c->config.entries; i++) {
    Slot *s = &c->slots[i];
    if (s->valid && same_key(s->key, key)) {
      /* Do not trust caller generations to imply identical bytes. No hashes or
       * float epsilon comparisons can accidentally reuse the wrong output. */
      if (s->vertices == count && s->bones == bones) {
        c->stats.compared_bytes = add(c->stats.compared_bytes, vb + pb);
        if (!memcmp(s->source, vertices, vb) && !memcmp(s->palette, palette, pb)) {
          s->age = next_age(c);
          c->stats.hits = add(c->stats.hits, 1);
          *out = s->output; if (hit) *hit = 1;
          return COH_OK;
        }
      }
      victim = s;
      break;
    }
    if (!victim || (!s->valid && victim->valid) ||
        (s->valid == victim->valid && s->age < victim->age)) victim = s;
  }
  c->stats.misses = add(c->stats.misses, 1);
  if (victim->valid) {
    c->stats.evictions = add(c->stats.evictions, 1);
    c->stats.resident_entries--;
    victim->valid = 0;
  }
  /* accepted kernel validates every vertex + palette and preserves source float
   * operation order. New wrapper changes no deformation math. */
  for (uint32_t i = 0; i < count; i++) {
    c->stats.kernel_vertices = add(c->stats.kernel_vertices, 1);
    if (coh_mesh_skin_vertex(&vertices[i], palette, bones, &victim->output[i])) {
      c->stats.rejections = add(c->stats.rejections, 1);
      return COH_INVALID;
    }
  }
  memcpy(victim->source, vertices, vb); memcpy(victim->palette, palette, pb);
  c->stats.copied_bytes = add(c->stats.copied_bytes, vb + pb);
  victim->key = key; victim->vertices = count; victim->bones = bones;
  victim->age = next_age(c); victim->valid = 1; c->stats.resident_entries++;
  *out = victim->output; if (hit) *hit = 0;
  return COH_OK;
}
