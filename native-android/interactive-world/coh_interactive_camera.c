/* Controlled source-camera adapter. Original accepted kernels are unchanged. */
#include "coh_interactive_world.h"
#include <math.h>
#include <string.h>
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
static float source_difference(float current, float previous) {
    float difference = current - previous;
    /* Same one-wrap domain and operation order as original subAngle/fixAngle. */
    if (difference > RAD(180.0)) difference -= RAD(360.0);
    if (difference <= RAD(-180.0)) difference += RAD(360.0);
    return difference;
}
static float clamp_degrees(float value) {
    return value < -12.0f ? -12.0f : (value > 12.0f ? 12.0f : value);
}
int coh_interactive_camera_apply(CohInteractiveCamera *state,
    const CohInputFrame *frame, const CohWorldInputs *baseline,
    CohWorldInputs *out, float *pitch_change, float *yaw_change) {
    if (!state || !frame || !baseline || !out || !pitch_change || !yaw_change)
        return 0;
    for (unsigned i = 0; i < 3; i++)
        if (!isfinite(frame->pyr[i]) || fabsf(frame->pyr[i]) > (float)RAD(180.0) + .00001f)
            return 0;
    CohInteractiveCamera candidate = *state;
    if (!candidate.initialized) {
        memset(&candidate, 0, sizeof candidate);
        memcpy(candidate.previous_pyr, frame->pyr, sizeof candidate.previous_pyr);
        candidate.initialized = 1;
    }
    for (unsigned i = 0; i < 3; i++)
        if (!isfinite(candidate.previous_pyr[i]) || fabsf(candidate.previous_pyr[i]) > (float)RAD(180.0) + .00001f) return 0;
    for (unsigned i = 0; i < 2; i++)
        if (!isfinite(candidate.offset_degrees[i]) || fabsf(candidate.offset_degrees[i]) > 12.0f)
            return 0;
    const float old_pitch = candidate.offset_degrees[0];
    const float old_yaw = candidate.offset_degrees[1];
    /* Original targetPYR pitch is -pyr.pitch. Its yaw is addAngle(pyr.yaw,PI).
     * Removing the constant PI relative to the initial view gives the same
     * wrapped yaw increment. source_difference preserves that increment. */
    const float pitch_radians = -source_difference(frame->pyr[0], candidate.previous_pyr[0]);
    const float yaw_radians = source_difference(frame->pyr[1], candidate.previous_pyr[1]);
    candidate.offset_degrees[0] = clamp_degrees(old_pitch + (float)((double)pitch_radians * (180.0 / PI)));
    candidate.offset_degrees[1] = clamp_degrees(old_yaw + (float)((double)yaw_radians * (180.0 / PI)));
    memcpy(candidate.previous_pyr, frame->pyr, sizeof candidate.previous_pyr);
    CohWorldInputs camera = *baseline;
    camera.cameras[0].pyr_degrees[0] += candidate.offset_degrees[0];
    camera.cameras[0].pyr_degrees[1] += candidate.offset_degrees[1];
    float view[12], projection[16];
    if (coh_world_camera(&camera, 0, 0, view, projection)) return 0;
    *pitch_change = candidate.offset_degrees[0] - old_pitch;
    *yaw_change = candidate.offset_degrees[1] - old_yaw;
    *state = candidate;
    *out = camera;
    return 1;
}
