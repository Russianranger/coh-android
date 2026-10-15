#ifndef COH_HUD_ATLAS_H
#define COH_HUD_ATLAS_H
#include "../coh_hud.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_HUD_ATLAS_GLYPHS 512u
typedef struct { uint32_t codepoint; CohUiGlyph glyph; } CohHudAtlasEntry;
/* Immutable atlas supplied by original TTF/atlas rasterizer, or explicitly
 * labelled diagnostic fallback. Metrics describe design_size logical pixels.
 * Resource identity must be invalidated by caller on Surface generation loss. */
typedef struct {
    uint32_t font_id; float design_size; const CohHudAtlasEntry *entries;size_t count;
    uint32_t fallback_codepoint; /* 0=strict; otherwise an explicitly present replacement */
} CohHudAtlas;
CohStatus coh_hud_atlas_validate(const CohHudAtlas *atlas);
CohStatus coh_hud_atlas_glyph(void *context,uint32_t font,uint32_t codepoint,float size,CohUiGlyph *out);
#ifdef __cplusplus
}
#endif
#endif
