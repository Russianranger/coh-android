#ifndef COH_NATIVE_SUPPORT_AUDIO_H
#define COH_NATIVE_SUPPORT_AUDIO_H
#include <android/asset_manager.h>
#include <stdint.h>
#include "../../engine/audio/coh_audio_listener.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct SupportAudio SupportAudio;
typedef struct {
    int initialized, running, requested_running, shutdown_requested;
    int diagnostics_valid, last_status, close_pending;
    int32_t xrun_count, device_error;
    uint32_t active_voices, retained_resources;
    uint64_t worker_ticks, opens, closes, state_changes;
    uint64_t music_loops, ambient_loops, decode_calls, backpressure;
    uint64_t source_bytes, rendered_frames, underrun_frames, underrun_callbacks;
    uint64_t callback_calls, maximum_callback_ns, deadline_overruns;
    uint64_t mixer_allocated_bytes, adapter_bytes;
    uint64_t snapshot_generation;
    uint64_t listener_updates,route_reopens,recovered_device_errors;
    int32_t last_device_error;
    CohAudioListenerPose listener;
} SupportAudioReport;
/* Starts one non-realtime control/decoder/backend-owner worker. Manager must
 * outlive successful destroy. Assets are music.ogg and ambient.ogg.
 * Returns NULL on allocation/thread initialization failure; codec/backend
 * initialization is asynchronous and reported by snapshot. Initially paused. */
SupportAudio *support_audio_create(AAssetManager *);
/* Latest-state bounded mailbox, never calls codec/AAudio on caller thread. */
void support_audio_resume(SupportAudio *);
void support_audio_pause(SupportAudio *);
void support_audio_emitter(SupportAudio *,float x,float y,float z);
void support_audio_listener(SupportAudio *,const CohAudioListenerPose *);
void support_audio_route(SupportAudio *,uint64_t generation);
/* Thread-safe copy; returns 0 on success. Mixer/backend counters are captured
 * only after sink close joins callbacks. While running they describe the last
 * quiescent checkpoint; diagnostics_valid=0 makes that explicit. Pause, wait
 * until running=0, then snapshot to export current underrun/timing counters. */
int support_audio_snapshot(SupportAudio *,SupportAudioReport *);
/* Requests shutdown and joins worker. Returns 0 and nulls pointer on success.
 * A failed platform close returns nonzero and RETAINS handle+mixer+assets for
 * retry: do not discard it. Retry transfers ownership to a new cleanup worker
 * only after joining its predecessor. Never free callback state before close.
 * Concurrent destroy/control calls are forbidden; caller serializes destroy.
 * The platform AAudio close call itself has no application cancellation API. */
int support_audio_destroy(SupportAudio **);
#ifdef __cplusplus
}
#endif
#endif
