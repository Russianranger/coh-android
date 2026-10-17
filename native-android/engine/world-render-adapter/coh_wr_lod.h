#ifndef COH_WR_LOD_H
#define COH_WR_LOD_H
#include "../coh_contracts.h"
/* Pure CLIENT modelCalcAlpha projection, NOT semantic admission. These bits
 * describe independently resolved CLIENT state; they are not raw SERVER flags.
 * No geometry/material/resource/world capability or ownership is produced. */
enum {
 COH_WR_LOD_SELECTED=1u,COH_WR_LOD_DEBUG_FADE=2u,COH_WR_LOD_PARENT_FADE=4u,
 COH_WR_LOD_WINDOW=8u,COH_WR_LOD_MODEL_TRICK=16u,COH_WR_LOD_NOFOG=32u,
 COH_WR_LOD_NIGHTLIGHT=64u,COH_WR_LOD_ADDGLOW=128u,COH_WR_LOD_DRAW_TRICK=256u,
 COH_WR_LOD_STIPPLE1=512u,COH_WR_LOD_STIPPLE2=1024u,COH_WR_LOD_NO_FOG_CLIP=2048u,
 COH_WR_LOD_FOG_CLIP=4096u,COH_WR_LOD_DRAW_ALL=8192u
};
typedef struct {
 float distance,scale,client_lod_scale,client_fade_range;
 float definition_lod[4],selected_lod[4]; /* near,nearfade,far,farfade */
 float definition_radius,node_radius,fog_far,draw_alpha;
 uint32_t flags,lod_fadenode,lamp_alpha;
} CohWrLodInput;
typedef struct {uint32_t alpha,beyond_fog,stipple_alpha;} CohWrLodProjection;
/* Finite bounded valid subset; outputs unchanged on refusal and aliases refuse.
 * draw_alpha==0 preserves original inherited-alpha sentinel (not opacity zero).
 * stipple_alpha remains zero on original early returns. Selected AutoLOD,
 * inherited model/draw tricks, radius, fog and sun state must already be resolved.
 * This is neither LOD-model selection nor a draw/visibility permit. */
CohStatus coh_wr_lod_project(const CohWrLodInput *,CohWrLodProjection *);
#endif
