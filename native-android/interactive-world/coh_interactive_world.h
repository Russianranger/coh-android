#ifndef COH_INTERACTIVE_WORLD_H
#define COH_INTERACTIVE_WORLD_H
#include <stddef.h>
#include <stdint.h>
#include "coh_input.h"
#include "coh_world.h"

/* The caller supplies a fresh consumed native input frame at each render tick.
 * sample returns 1 on success, 0 on orderly cancellation, -1 on failure.
 * revision counts external Android input events, never generated selftests.
 * Both callbacks must be thread-safe. The caller serializes all graphics runs
 * and owns the retained ANativeWindow for the whole call. */
typedef struct {
    void *opaque;
    int (*sample)(void *, float seconds, CohInputFrame *, uint64_t *revision);
    int (*cancelled)(void *);
} CohInteractiveWorldControl;

/* Adapter policy: source editor look's pitch-negation is retained, and its
 * fixed yaw+180 convention is removed relative to the original fixture view.
 * Native input orientation differences are converted from radians to degrees,
 * then accumulated/clamped to +/-12 degrees about authentic camera zero.
 * Saturation has no motion backlog: reversing immediately leaves the bound.
 * Camera position, roll, FOV and all authored nodes remain the fixture values.
 * This is controlled camera look, not character movement or collision. */
typedef struct {
    int initialized;
    float previous_pyr[3], offset_degrees[2];
} CohInteractiveCamera;
int coh_interactive_camera_apply(CohInteractiveCamera *, const CohInputFrame *,
    const CohWorldInputs *, CohWorldInputs *, float *pitch_change, float *yaw_change);

typedef struct {
    int passed, engine_passed, interaction_passed, cancelled, obsolete, expected_cancel, session_failure;
    int fixtures_valid, baseline_cpu_passed, baseline_gpu_passed;
    int context_created, objects_released, swapped, width, height;
    unsigned frames, source_frames_consumed, direction_mask, settled_frames;
    unsigned cpu_direction_mask, gpu_direction_mask, image_direction_mask;
    unsigned external_revision_changes, input_motion_frames, stationary_mismatches;
    unsigned camera_determinism_checks, camera_determinism_mismatches;
    unsigned image_samples, changed_image_samples, same_camera_image_mismatches;
    unsigned gl_errors, egl_error, shader_language_version, shader_precise_enabled;
    uint64_t baseline_transform_components, baseline_transform_mismatches;
    uint64_t interactive_transform_components, interactive_transform_mismatches;
    uint64_t baseline_cpu_components, baseline_cpu_mismatches;
    uint64_t input_linked_changed_pixels, duration_ms, first_revision, last_revision;
    float first_camera_degrees[3], last_camera_degrees[3];
    char stage[512], failure[512], gl_vendor[512], gl_renderer[512];
    char shader_precision_mechanism[512];
} CohInteractiveWorldReport;

#ifdef __ANDROID__
#include <android/native_window.h>
int coh_interactive_world_run(ANativeWindow *,
    const uint8_t *world, size_t world_bytes,
    const uint8_t *reference, size_t reference_bytes,
    const uint8_t *materials, size_t material_bytes,
    const CohInteractiveWorldControl *, CohInteractiveWorldReport *);
/* The caller frees this independently owned immutable UTF8 snapshot. */
char *coh_interactive_world_json(const CohInteractiveWorldReport *);
#endif
#endif
