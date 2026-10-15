#ifndef COH_ENGINE_AUDIO_AAUDIO_H
#define COH_ENGINE_AUDIO_AAUDIO_H
#include "coh_mixer.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohMixerAAudio CohMixerAAudio;
typedef struct {
    int32_t result, sample_rate, channels, format, frames_per_burst, buffer_frames;
    int32_t xrun_count, device_error;
    uint64_t callback_calls, maximum_callback_ns, deadline_overruns, clock_errors;
    int64_t frames_written, frames_read, timestamp_frame, timestamp_ns;
    int timestamp_available, opened, started, stopped, closed;
} CohMixerAAudioReport;
/* Optional Android API26+ sink. Borrowed mixer must outlive close. This sink
 * uses the new mixer exclusively; never run two render consumers. All APIs
 * except AAudio's internal callbacks are called on one backend owner thread.
 * Open does not silently change sample rate/channel count or mutate the old
 * accepted native audio gate. Source PCM must match the actual opened rate.
 * No stream handle escapes to UI/lifecycle/error threads. */
CohStatus coh_mixer_aaudio_open(CohMixer *, CohMixerAAudio **out);
/* Stop/wait/close is bounded except the platform close operation itself.
 * Null handle is an idempotent success. Close records final consumption/xrun/
 * timestamp diagnostics, then processes outstanding mixer controls at zero
 * frames with the callback stopped. For pause, enqueue mixer_pause(1) before
 * close; recreate, enqueue mixer_pause(0), open to resume. For device failure,
 * close consumes the error request and flushes sounds; then explicitly resume.
 * A failed close must be retried; handle stays alive while backend may use it. */
CohStatus coh_mixer_aaudio_close(CohMixerAAudio **, CohMixerAAudioReport *);
#ifdef __cplusplus
}
#endif
#endif
