#include "coh_audio_session.h"
#include <stdlib.h>
#include <string.h>

struct CohAudioSession {
    CohMixer *mixer;
    CohMixerAAudio *sink;
    CohAudioSessionReport report;
    int closing;
};

/* No render consumer may be active here. Drain a saturated command queue
 * before publishing pause/resume; never call render concurrently with AAudio. */
static CohStatus quiescent_pause(CohAudioSession *s, int paused) {
    CohStatus result = coh_mixer_render(s->mixer, NULL, 0);
    if (result != COH_OK) return result;
    result = coh_mixer_pause(s->mixer, paused);
    if (result != COH_OK) return result;
    return coh_mixer_render(s->mixer, NULL, 0);
}

static void observe_error(CohAudioSession *s) {
    int32_t error = coh_mixer_aaudio_device_error(s->sink);
    if (error && !s->report.recovery_required) {
        s->report.last_device_error = error;
        s->report.device_failures++;
        s->report.recovery_required = 1;
    }
}

static CohStatus close_backend(CohAudioSession *s) {
    CohStatus result = COH_OK;
    if (s->sink) {
        /* A full producer queue cannot prevent closing. close joins callbacks,
         * drains controls, then quiescent_pause reliably applies the pause. */
        (void)coh_mixer_pause(s->mixer, 1);
        s->closing = 1;
        observe_error(s);
        CohMixerAAudioReport closed;
        memset(&closed, 0, sizeof closed);
        result = coh_mixer_aaudio_close(&s->sink, &closed);
        if (result != COH_OK) s->report.close_failures++;
        if (s->sink) return result;
        s->report.closes++;
        s->report.last_closed_backend = closed;
        /* An error can arrive between the pre-close poll and platform close.
         * The final joined snapshot is the authoritative last observation. */
        if (closed.device_error && !s->report.recovery_required) {
            s->report.last_device_error = closed.device_error;
            s->report.device_failures++;
            s->report.recovery_required = 1;
        }
    }
    s->closing = 0;
    CohStatus paused = quiescent_pause(s, 1);
    return result != COH_OK ? result : paused;
}

CohStatus coh_audio_session_create(CohMixer *mixer, CohAudioSession **out) {
    if (!out || !mixer) return COH_INVALID;
    *out = NULL;
    CohAudioSession *s = calloc(1, sizeof *s);
    if (!s) return COH_LIMIT;
    s->mixer = mixer;
    CohStatus result = quiescent_pause(s, 1);
    if (result != COH_OK) { free(s); return result; }
    *out = s;
    return COH_OK;
}

CohStatus coh_audio_session_pump(CohAudioSession *s) {
    if (!s) return COH_INVALID;
    observe_error(s);
    int desired = s->report.foreground && s->report.audio_focus;
    if (s->report.recovery_required || !desired) {
        CohStatus result = close_backend(s);
        return result != COH_OK ? result : (s->report.recovery_required ? COH_IO : COH_OK);
    }
    if (s->closing) {
        CohStatus result = close_backend(s);
        if (result != COH_OK) return result;
        if (s->report.recovery_required) return COH_IO;
    }
    if (s->sink) return COH_OK;
    CohStatus result = quiescent_pause(s, 0);
    if (result != COH_OK) return result;
    result = coh_mixer_aaudio_open(s->mixer, &s->sink);
    if (result != COH_OK) {
        s->report.open_failures++;
        if (s->sink) {
            /* open retained a failed-close handle. Its callback user data must
             * survive; pause now and retry close from a later owner pump. */
            s->closing = 1;
            (void)coh_mixer_pause(s->mixer, 1);
        } else {
            (void)quiescent_pause(s, 1);
        }
        return result;
    }
    s->report.opens++;
    return COH_OK;
}

CohStatus coh_audio_session_environment(CohAudioSession *s, int foreground, int focus) {
    if (!s || (foreground != 0 && foreground != 1) || (focus != 0 && focus != 1)) return COH_INVALID;
    s->report.foreground = foreground;
    s->report.audio_focus = focus;
    return coh_audio_session_pump(s);
}

CohStatus coh_audio_session_recover(CohAudioSession *s) {
    if (!s) return COH_INVALID;
    observe_error(s);
    if (!s->report.recovery_required) return COH_STATE;
    CohStatus result = close_backend(s);
    if (result != COH_OK) return result;
    s->report.recovery_required = 0;
    return coh_audio_session_pump(s);
}

CohStatus coh_audio_session_report(const CohAudioSession *s, CohAudioSessionReport *out) {
    if (!s || !out) return COH_INVALID;
    *out = s->report;
    out->has_backend = s->sink != NULL;
    out->state = s->closing ? COH_AUDIO_SESSION_CLOSING :
        s->report.recovery_required ? COH_AUDIO_SESSION_FAULTED :
        s->sink ? COH_AUDIO_SESSION_RUNNING : COH_AUDIO_SESSION_SUSPENDED;
    return COH_OK;
}

CohStatus coh_audio_session_destroy(CohAudioSession **handle) {
    if (!handle) return COH_INVALID;
    if (!*handle) return COH_OK;
    CohAudioSession *s = *handle;
    s->report.foreground = s->report.audio_focus = 0;
    CohStatus result = close_backend(s);
    if (s->sink) return result;
    free(s);
    *handle = NULL;
    return result;
}
