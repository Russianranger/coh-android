#ifndef COH_ENGINE_AUDIO_MIXER_H
#define COH_ENGINE_AUDIO_MIXER_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_MIXER_MAX_VOICES 32u
#define COH_MIXER_MAX_EVENTS 128u
#define COH_MIXER_MAX_CACHE 32u
#define COH_MIXER_MAX_STREAMS 4u
typedef struct CohMixer CohMixer;
typedef struct { uint32_t slot, generation; } CohAudioResource;
typedef enum { COH_BUS_FX, COH_BUS_MUSIC, COH_BUS_VOICE, COH_BUS_AMBIENT, COH_BUS_COUNT } CohAudioBus;
typedef enum { COH_AUDIO_CACHED, COH_AUDIO_STREAM } CohAudioSourceKind;
typedef struct {
    uint32_t sample_rate, voices, event_capacity, cache_entries; /* event_capacity is a power of two. */
    size_t cache_bytes;
    uint32_t stream_frames; /* Per stream, stereo float ring; power of two, zero disables. */
} CohMixerConfig;
typedef struct {
    uint64_t at_frame;
    uint32_t source, emitter;
    CohAudioResource resource;
    CohAudioSourceKind kind;
    CohAudioBus bus;
    uint32_t priority; /* Higher values win; equal priority uses source loudness. */
    float gain, inner_radius, outer_radius;
    CohVec3 position;
    uint8_t spatial, ignore_ramp, loop, interrupt;
} CohAudioEvent;
typedef struct {
    uint64_t rendered_frames, play_started, play_completed, play_rejected, voices_stolen;
    uint64_t queue_rejected, pending_rejected, late_events, clipped_samples;
    uint64_t stream_underrun_frames, stream_underrun_callbacks, cancelled;
    uint64_t pause_callbacks, device_errors, callback_calls;
    uint64_t maximum_callback_frames, cache_hits, cache_misses, cache_evictions;
    size_t allocated_bytes, cache_used_bytes, cache_peak_bytes;
    uint32_t active_voices, pending_events, retained_resources, device_generation;
} CohMixerDiagnostics;

/* One control/decoder producer and one render consumer. All allocation occurs
 * in create; render never allocates, locks, decodes, frees or calls user code.
 * create/cache/stream/producers are not real-time APIs. Destroy and diagnostics
 * require the producer and render callback stopped. Destroy accepts NULL.
 * Cache IDs preserve original virtual path and content generation (191 bytes).
 * Cache data is copied, normalized and owned; callers may release decoded PCM.
 * PCM rate must match the engine rate; resampling is explicitly unsupported. */
CohStatus coh_mixer_create(const CohMixerConfig *, CohMixer **out);
uint32_t coh_mixer_sample_rate(const CohMixer *);
void coh_mixer_destroy(CohMixer *);
CohStatus coh_mixer_cache_pcm16(CohMixer *, CohAssetId, const int16_t *, uint32_t frames,
                              uint32_t channels, uint32_t rate, CohAudioResource *out);
/* Reuses accepted COHAUD11 parser/decoder result. Decode remains off callback. */
CohStatus coh_mixer_cache_decoded(CohMixer *, CohAssetId, CohBytes, CohAudioResource *out);
CohStatus coh_mixer_stream_open(CohMixer *, uint32_t channels, uint32_t rate, CohAudioResource *out);
/* SPSC stream, one decoder producer. Writes are all-or-nothing and bounded.
 * A stream has one playback consumer. EOF drains queued data then completes.
 * Its resource may be reopened only after playback/pending references retire. */
CohStatus coh_mixer_stream_write(CohMixer *, CohAudioResource, const int16_t *, uint32_t frames);
CohStatus coh_mixer_stream_finish(CohMixer *, CohAudioResource);
CohStatus coh_mixer_stream_close(CohMixer *, CohAudioResource);
CohStatus coh_mixer_play(CohMixer *, const CohAudioEvent *);
CohStatus coh_mixer_stop_emitter(CohMixer *, uint32_t emitter);
CohStatus coh_mixer_cancel_all(CohMixer *);
CohStatus coh_mixer_update_emitter(CohMixer *, uint32_t emitter, CohVec3, float gain);
CohStatus coh_mixer_listener(CohMixer *, CohVec3 position, CohVec3 right);
CohStatus coh_mixer_bus_gain(CohMixer *, CohAudioBus, float gain);
CohStatus coh_mixer_pause(CohMixer *, int paused);
/* Error callback-safe: atomic request only. Render pauses and flushes queued/
 * active sounds. The control owner must stop/close/reopen the backend, then
 * explicitly resume. No backend object is closed by an audio callback. */
void coh_mixer_device_error(CohMixer *);
/* Stereo float output, interleaved. Frames may be zero; maximum 8192 per call.
 * Pause freezes the simulation audio clock. Starved streams emit silence and
 * retain playback position; cache voices still progress. Clipping is bounded. */
CohStatus coh_mixer_render(CohMixer *, float *stereo, uint32_t frames);
CohStatus coh_mixer_diagnostics(const CohMixer *, CohMixerDiagnostics *);
/* Source-derived scalar attenuation; invalid inputs return 0. Panning uses
 * source head-right dot product + original +/-2000 dB100 DirectSound range;
 * software stereo approximates the sink, not HRTF/DirectSound sample output. */
float coh_mixer_attenuation(float inner, float outer, float distance, int ignore_ramp);
void coh_mixer_spatial_gains(const CohAudioEvent *, CohVec3 listener, CohVec3 right,
                             float bus_gain, float *left, float *right_gain);
#ifdef __cplusplus
}
#endif
#endif
