#ifndef COH_ENGINE_AUDIO_SESSION_H
#define COH_ENGINE_AUDIO_SESSION_H
#include "coh_mixer_aaudio.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohAudioSession CohAudioSession;
typedef enum {
    COH_AUDIO_SESSION_SUSPENDED,
    COH_AUDIO_SESSION_RUNNING,
    COH_AUDIO_SESSION_CLOSING,
    COH_AUDIO_SESSION_FAULTED
} CohAudioSessionState;
typedef struct {
    CohAudioSessionState state;
    int foreground, audio_focus, has_backend, recovery_required;
    int32_t last_device_error;
    uint64_t opens, closes, open_failures, close_failures, device_failures;
    CohMixerAAudioReport last_closed_backend;
} CohAudioSessionReport;

/* Opt-in Android API26+ backend owner. One application owner serializes this
 * API with every other mixer producer API. Creation requires no render consumer;
 * the borrowed mixer and its cached/stream PCM must outlive successful destroy.
 * Initial state is suspended with neither foreground nor audio focus. The app
 * obtains focus itself; this adapter neither calls Java nor claims OS focus.
 * Only this session may create/render an AAudio sink for the borrowed mixer.
 * Surface loss alone is not an audio lifecycle event. */
CohStatus coh_audio_session_create(CohMixer *, CohAudioSession **out);
/* Boolean inputs must be exactly 0 or 1. Audio runs only while both are true.
 * Pause retains mixer voices/cache and freezes its audio clock. Duplicate
 * notifications are idempotent. Failed closes retain their callback context;
 * pump retries closing before reopening, even if foreground changes again. */
CohStatus coh_audio_session_environment(CohAudioSession *, int foreground, int audio_focus);
/* Call on the owner after notifications and periodically while running. This
 * only reads the backend's atomic error flag while callbacks are active. A
 * device/callback error closes the backend, flushes mixer voices through its
 * accepted device-error path and latches a fault; it never silently replays.
 * COH_IO means an observed fault or backend operation failure. A successful
 * close can still report COH_IO after a stop failure; its handle is released. */
CohStatus coh_audio_session_pump(CohAudioSession *);
/* Explicit recovery after an error; caller requeues appropriate game sounds
 * after successful recovery. Pending failed closes must finish first. Ordinary
 * open/close failures can be retried through pump without this acknowledgement. */
CohStatus coh_audio_session_recover(CohAudioSession *);
/* Owner-thread metadata only: safe with the render callback active. It never
 * reads mixer/live callback counters. last_closed_backend is copied only after
 * close has joined callbacks. Use mixer diagnostics only with session suspended
 * and all producers quiescent, as required by the existing mixer contract. */
CohStatus coh_audio_session_report(const CohAudioSession *, CohAudioSessionReport *);
/* Null handle is idempotent. On failed platform close, the session is retained
 * for retry and the borrowed mixer MUST remain alive. If close releases its
 * backend after a stop error, the session is consumed while COH_IO is returned.
 * Does not destroy the borrowed mixer or evict cached/stream resources. */
CohStatus coh_audio_session_destroy(CohAudioSession **);
#ifdef __cplusplus
}
#endif
#endif
