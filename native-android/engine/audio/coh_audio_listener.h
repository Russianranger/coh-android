#ifndef COH_ENGINE_AUDIO_LISTENER_H
#define COH_ENGINE_AUDIO_LISTENER_H
#include "coh_mixer.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { CohVec3 position, right; } CohAudioListenerPose;
/* Pure camera adapter, no allocation/queue/clock/platform work. Source view is
 * the 4x3 column-major output of unchanged coh_world_camera(), INCLUDING its
 * source rdrFixMat X reflection. Generic GL row-zero extraction reverses pan.
 * Requires a finite orthonormal reflected basis (determinant -1); scaled,
 * sheared, perspective and ordinary unreflected GL matrices are rejected.
 * Projection flips are not audio orientation. Output unchanged on error. */
CohStatus coh_audio_listener_source_view(const float view[12], CohAudioListenerPose *out);
/* Camera world-space position and head-right, such as source head_mat[3]/[0].
 * Finite nonzero right is normalized with double intermediates. */
CohStatus coh_audio_listener_pose(CohVec3 position, CohVec3 right, CohAudioListenerPose *out);
/* Producer-owner convenience only; queue backpressure remains caller-owned.
 * Do not call this or mixer producer APIs from the realtime render callback. */
CohStatus coh_audio_listener_apply(CohMixer *, const CohAudioListenerPose *);
#ifdef __cplusplus
}
#endif
#endif
