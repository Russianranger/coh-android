#ifndef COH_WR_TEXNAME_H
#define COH_WR_TEXNAME_H
#include "../coh_contracts.h"
#define COH_WR_TEXNAME_INPUT_MAX 255u
#define COH_WR_TEXNAME_KEY_MAX 127u
#define COH_WR_TEXNAME_SWAPS_MAX 256u
typedef struct {const char *source,*destination;} CohWrMaterialNameSwap;
typedef struct {
 const char *name;uint32_t texture_count;
 const CohWrMaterialNameSwap *scene_material_swaps;uint32_t swap_count;
} CohWrTexNameInput;
enum {COH_WR_TEXNAME_COMPOSITE_LOOKUP=1,COH_WR_TEXNAME_PORTAL_BRANCH=2,COH_WR_TEXNAME_EMPTY_TABLE_BRANCH=3};
typedef struct {
 uint32_t branch,scene_swap_index;
 char stripped[256],composite_key[128];
} CohWrTexNameProjection;
/* Pure bounded ASCII original CLIENT name projection. No table lookup, TexBind,
 * BasicTexture, fallback asset, shader, generation or material permit is produced.
 * The portal/empty-table values identify original producer branches only.
 * Removes last extension before portal detection; ordinary lookup skips one!,
 * applies original texFixName suffix rules, then FIRST case-insensitive scene
 * material swap (destination is NOT renormalized). Case/path are preserved.
 * Source-unsafe texFixName 4..7-byte bare names and oversized keys refuse;
 * this does not reproduce original out-of-bounds reads/writes. Refusal leaves
 * output unchanged. Input strings/arrays must remain immutable during call.
 * Inherited definition swaps, texture/locale actualTexture swaps and capability-
 * dependent composite construction remain separate CLIENT prerequisites. */
CohStatus coh_wr_texname_project(const CohWrTexNameInput*,CohWrTexNameProjection*);
#endif
