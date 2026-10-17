#ifndef COH_WR_MODEL_MATERIAL_H
#define COH_WR_MODEL_MATERIAL_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WR_MODEL_MATERIAL_PARTS_MAX 256u
#define COH_WR_MODEL_MATERIAL_LAYERS 11u
/* Original shader numeric domain, not CohMaterialFamily. Input MODULATE=0 may
 * become MULTIPLY=1 at model level. No source shader may be cast to renderer enum. */
enum {COH_WR_MODEL_MODULATE=0,COH_WR_MODEL_MULTIPLY=1,COH_WR_MODEL_DUAL=2,COH_WR_MODEL_ADDGLOW=3,COH_WR_MODEL_ALPHADETAIL=4,COH_WR_MODEL_BUMP_MULTIPLY=5,COH_WR_MODEL_BUMP_DUAL=6,COH_WR_MODEL_WATER=7,COH_WR_MODEL_MULTI=8,COH_WR_MODEL_SUNFLARE=9};
typedef struct {int32_t shader;uint32_t bits;} CohWrModelBlend;
typedef struct {
 const char*name;
 CohWrModelBlend blend;
 uint32_t layer_present_mask,layer_alpha_mask,mask_is_exact_white;
 uint32_t texopt_present,texopt_flags,texopt_model_flags,multiply1_reflect,is_fallback;
} CohWrModelMaterialPart;
typedef struct {
 const char*model_name;const CohWrModelMaterialPart*parts;uint32_t part_count;
 uint32_t selected_trick_present,trick_flags1,trick_flags2,trick_model_flags;
 uint32_t bone_info_present,normals_present,bumpmaps_enabled,water_mode;
} CohWrModelMaterialInput;
typedef struct {
 uint32_t model_flags,trick_present,trick_info_present,trick_flags1,trick_flags2;
 uint32_t part_count,unrepresented_shader_mask,nonzero_blend_bits;
 CohWrModelBlend common_blend,parts[COH_WR_MODEL_MATERIAL_PARTS_MAX];
} CohWrModelMaterialProjection;
/* Complete numerical fresh-initial modelResetFlags/alpha/blend projection from
 * separately resolved original CLIENT TexBind/Basic/Trick inputs. No model
 * history/reload/custom texture/draw-time override is emulated. No pointers or
 * resources are retained, no heap allocation/callbacks and no render material,
 * pin, generation or namespace permission is produced. All failure outputs are
 * unchanged. Inputs/names must be immutable and disjoint from writable output.
 * Basic layer bits follow original TexLayerIndex0..10 (BASE0,GENERIC1,MASK4).
 * A live exact white identity is REQUIRED to set mask_is_exact_white; historical
 * labels/white names cannot establish it. Alpha bits are effective Basic flags,
 * not cached header TexOpt flags. Selected Trick is already postprocessed and
 * source-selected; these scalar inputs do not authenticate that selection.
 * Every name must contain NUL within256 readable bytes, or provide all256
 * readable bytes for bounded refusal. A short unterminated span is not a valid
 * const-char pointer input. part_count1..256; source shader0..9/bits<=65535;
 * accepted names are nonempty printable ASCII shorter than256 bytes.
 * water_mode is original OptionWater0..4; bump flag is actual GFXF_BUMPMAPS.
 * Unknown model/Trick/TexOpt bits are preserved by source operations, never
 * treated as supported renderer semantics. unrepresented_shader_mask explicitly
 * marks final shaders outside MULTIPLY/DUAL/ADDGLOW; nonzero blend bits and all
 * remaining flags also require separate producer interpretation. Existing
 * CohWrRigidMaterial admission must remain the final material/pin validator.
 * Borrowed input/name storage, caller output and4KiB own control stack must be
 * included in the parent aggregate reservation, plus compiler/runtime overhead.
 * This policy result never admits even a supported shader to drawing. */
CohStatus coh_wr_model_material_project(const CohWrModelMaterialInput*,CohWrModelMaterialProjection*);
#ifdef __cplusplus
}
#endif
#endif
