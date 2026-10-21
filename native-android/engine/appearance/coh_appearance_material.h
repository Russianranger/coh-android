#ifndef COH_APPEARANCE_MATERIAL_H
#define COH_APPEARANCE_MATERIAL_H
#include "coh_appearance.h"
/* Explicit feature-limited character profile: original tex.c automatic
 * fallback with MULTITEX and BUMPMAPS unavailable. This does not implement the
 * original multi-layer chrome/bump shader, effective sampler cache or lighting
 * environment. Both sampled leaves must still resolve to authentic Basic
 * inputs. The original built-in white texture is named "none" here.
 * Requested logical identities stay in CohAppearanceMaterialBinding; these
 * are the actual source leaves selected by texResetTrickBasedParametersComposite
 * and getSwapX(require_replaceable=0). No missing input becomes white. */
typedef struct {
 char basic[2][256];
 uint32_t automatic_fallback,generic_swappable;
 float ambient_scale,diffuse_scale;
} CohAppearanceMaterialRecipe;
CohStatus coh_appearance_material_recipe(const char primary[256],
 const char secondary[256],CohAppearanceMaterialRecipe *);
#endif
