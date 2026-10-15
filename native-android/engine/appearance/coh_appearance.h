#ifndef COH_APPEARANCE_H
#define COH_APPEARANCE_H
#include "../coh_contracts.h"
#include "../assets/coh_asset_geo.h"
#include "../../character/coh_character.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_APPEARANCE_PARTS 60u
#define COH_APPEARANCE_DRAWS 120u
#define COH_APPEARANCE_NAME 256u
#define COH_APPEARANCE_CHEST_LINKS 16u
/* Source BodyType numeric values and names remain unchanged. String values are
 * copied, not interned. Caller chooses a rig by this ent_type; no global actor. */
typedef struct {uint32_t body_type;char ent_type[256],geometry_prefix[256],texture_prefix[256];} CohAppearanceBody;
/* BodyPart records are data (Defs/UI/bodyparts.bp), never per-character code.
 * Socket IDs are source bones.h values, R before L for paired parts.
 * UINT32_MAX for first socket preserves source unknown-bodypart no-op behavior. */
typedef struct {
 const char *name,*geometry_name,*texture_name,*base_name;
 uint32_t socket[2],socket_count,dont_clear;
} CohAppearancePartDef;
typedef struct {
 uint32_t definition;const char *geometry,*texture[2];uint8_t color[4][4];
} CohAppearancePart;
enum {COH_APPEARANCE_GEOMETRY=1,COH_APPEARANCE_TEXTURE=2};
/* Source texture-prefix and chest-link existence lookup. Synchronous and
 * side-effect-free. Texture probes include .tga; geometry probes use the source
 * file.model key. NULL deliberately means no prefixed/linked override exists. */
typedef int (*CohAppearanceProbe)(void *,uint32_t kind,const char *key);
typedef struct {
 CohAppearanceBody body;const CohAppearancePartDef *definitions;uint32_t definition_count;
 const CohAppearancePart *parts;uint32_t part_count,generation;uint8_t skin[4];
 const char *const *chest_links;uint32_t chest_link_count;
 CohAppearanceProbe probe;void *probe_context;CohCancel cancel;
} CohAppearanceRequest;
enum {COH_APPEARANCE_CLEAR=1u,COH_APPEARANCE_SKIN_COLOR=2u};
/* All names and colors copied into caller-owned output. Texture "none" is the
 * original unbound marker; downstream renderer may map it to its white texture.
 * generation and source paths supply the existing immutable asset-ID contract. */
typedef struct {
 uint32_t definition,socket,generation,flags;
 char geometry_key[256],geometry_path[256],model_name[256],texture[2][256];
 uint8_t color[4][4];
} CohAppearanceDraw;
typedef struct {uint32_t draws,cleared,skin_routed,geometry_probes,texture_probes;size_t scratch_bytes;} CohAppearanceDiagnostics;
/* Fixed caller-owned transaction arena; no heap, decode, GL or global state.
 * Prefer actor/control thread. Borrowed inputs/callbacks only live during call. */
typedef struct {CohAppearanceDraw draws[COH_APPEARANCE_DRAWS];} CohAppearanceWorkspace;
CohStatus coh_appearance_body(uint32_t body_type,const char *ent_type_override,
 const char *geometry_prefix_override,CohAppearanceBody *out);
CohStatus coh_appearance_assemble(const CohAppearanceRequest *,CohAppearanceWorkspace *,
 CohAppearanceDraw *out,size_t capacity,size_t *count,CohAppearanceDiagnostics *);
/* Optional read-only adapters. Caller pins parsed GEO, rig, morph and pose for
 * synchronous calls. Matching uses source case-insensitive no-trick identity;
 * returns NOT_FOUND (not synthesized geometry) for absent resources. */
CohStatus coh_appearance_geo_model(const CohAssetGeo *,const CohAppearanceDraw *,
 uint32_t maximum_models,uint32_t *index,CohAssetGeoModel *);
/* Preserves existing exact socket/inverse-bind/nonpropagating bone-scale math.
 * morph=NULL supports an already qualified neutral rig. A non-NULL morph is
 * admitted only for the existing qualified Huge body type; no new body morph
 * arithmetic is claimed. Palette output remains untouched on any error. */
CohStatus coh_appearance_palette(const CohAppearanceDraw *,uint32_t body_type,
 const CohAnimationRig *,const CohCharacterMorph *,const CohAnimationPose *,
 const uint32_t *bone_ids,uint32_t count,float *rows,size_t scalar_capacity);
#ifdef __cplusplus
}
#endif
#endif
