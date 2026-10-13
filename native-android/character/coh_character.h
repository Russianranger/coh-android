#ifndef COH_CHARACTER_H
#define COH_CHARACTER_H
#include "../animation/coh_animation.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Morph records preserve source GEO model.scale triples, not sampled palettes.
 * Runtime computes the original appearance exceptions and float32 arithmetic. */
typedef struct {
    const uint8_t *bytes; size_t byte_count;
    uint32_t body_type;
    float geom_scale[3],bone_scale,shoulder_scale,chest_scale,waist_scale;
    float hip_scale,leg_scale,arm_scale,head_scales[3],leg_scale_ratio;
    float shoulder_skinny[3],shoulder_fat[3],hip[3],neck[3];
    float head_min[3],head_max[3],face_scales[7][3];
    float fat_model_scale[COH_ANIMATION_BONES][3];
    float skinny_model_scale[COH_ANIMATION_BONES][3];
    float bone_scales[COH_ANIMATION_BONES][3];
    float effective_head_scales[3],neck_scale,actor_root_rows[12];
} CohCharacterMorph;
/* Outputs remain untouched on failure. COHMOR01 is a bounded 256-byte header
 * plus 99 ordered (ID,fat3,skinny3) 28-byte records. Body type is source Huge=4.
 * A missing source scale model is represented by unit model.scale. */
int coh_character_parse_morph(const uint8_t *,size_t,CohCharacterMorph *);
/* Native raw-key sampling, source morph translations before animDelta,
 * limb scale/unscale and scaled entity root, single clip/no transition. */
int coh_character_sample(const CohAnimationRig *,const CohCharacterMorph *,
                         float frame,CohAnimationPose *);
/* Skin bone scales do not propagate down hierarchy. Palette preserves source
 * parentWorld * (localNode * boneScale) order, then inverse-bind and attachment as two
 * point transforms. Rigid GEO parts use the proven one-bone fallback adapter. */
int coh_character_palette(const CohAnimationRig *,const CohCharacterMorph *,
                          const CohAnimationPose *,uint32_t socket_id,
                          const uint32_t *bone_ids,uint32_t count,float *rows);
#ifdef __cplusplus
}
#endif
#endif
