#ifndef COH_APPEARANCE_SCALES_H
#define COH_APPEARANCE_SCALES_H
#include "coh_appearance_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_APPEARANCE_HUGE_MORPH_BYTES 3028u
#define COH_APPEARANCE_HUGE_SCALE_STACK 12288u
/* Original Huge type scale models, in original BoneId order. A unit entry is
 * permitted only where the actual original model header lacks that bone. The
 * source GEO adapter preserves the first model for each source bone ID. */
typedef struct {float fat[99][3],skinny[99][3];uint32_t fat_models,skinny_models;} CohAppearanceHugeScales;
typedef struct {uint32_t bodytype,converted_scale,fat_models,skinny_models;float height_scale;} CohAppearanceHugeScaleDiagnostics;
CohStatus coh_appearance_huge_scale_models(const CohAssetGeo *fat,
 const CohAssetGeo *skinny,CohAppearanceHugeScales *);
/* Caller-owned private candidate storage, immutable while out is borrowed.
 * No allocation or source IO. Uses source Huge type parameters and the received
 * Appearance union directly; convertedScale is informational at costume_Apply.
 * The legacy scalar fHeadScale is not the later Vec3 fHeadScales. No UI range
 * remapping or NPC defaults are applied. Existing character sampler composes
 * the original bone/limb/translation/height operations at draw time.
 * All spans must be disjoint. out/diagnostics are unchanged on every failure;
 * candidate bytes may change. Charge old/candidate storage and stack to caller. */
CohStatus coh_appearance_huge_morph(const CohOriginalCostumeSnapshot *,
 const CohAppearanceHugeScales *,uint8_t candidate[COH_APPEARANCE_HUGE_MORPH_BYTES],
 CohCharacterMorph *out,CohAppearanceHugeScaleDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
