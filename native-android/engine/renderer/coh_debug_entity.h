#ifndef COH_DEBUG_ENTITY_H
#define COH_DEBUG_ENTITY_H
#include "coh_renderer.h"
#include "../initial-capture/coh_initial_pose_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Crude ORANGE DIAGNOSTIC BOX, not a costume or complete authoritative actor.
 * Uses only the supplied decoded absolute server sample and real entity index.
 * No default/spawn, smoothing, input movement or coordinate conversion occurs.
 * Caller selects the actual selected-self prefix/raw-DBID match, clears on
 * disconnect/reconnect and labels this marker as an observed server entity.
 *
 * view/projection are column-major. white is the caller's actual live backend
 * white resource for this Surface; all returned geometry is immutable static
 * storage, valid for module lifetime. No heap, GL call, resource hold or ACK.
 * Output copies model-view/projection and material; no sample pointer survives.
 * Draw can use the existing renderer backend or its explicit debug draw path.
 * Invalid/overlapping/nonfinite inputs preserve output. The marker's fixed
 * 2x6x2 dimensions and orange color are diagnostic styling, never game data.
 */
CohStatus coh_debug_entity_draw(const CohInitialPoseSample*,uint32_t entity_index,
 const float view[16],const float projection[16],CohRenderTexture white,
 CohRenderDraw*);
#ifdef __cplusplus
}
#endif
#endif
