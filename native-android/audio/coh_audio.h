#ifndef COH_NATIVE_AUDIO_H
#define COH_NATIVE_AUDIO_H
#include <stddef.h>
#include <stdint.h>

enum { COH_AUDIO_OK=0, COH_AUDIO_INVALID=-1, COH_AUDIO_BUSY=-2,
       COH_AUDIO_BACKEND=-3, COH_AUDIO_CANCELLED=1 };
typedef struct {
    uint32_t sample_rate, channels, frames, pcm_bytes;
    const uint8_t *pcm;
} CohAudioFixture;
typedef struct {
    int result, requested_rate, actual_rate, actual_channels, actual_format;
    int opened, started, stopped, closed, cancelled, backend_errors;
    int completed_clips, requested_clips, partial_writes, write_calls;
    int xrun_count, timestamp_available;
    int64_t submitted_frames, read_frames, timestamp_frame, timestamp_ns;
    int source_volume_db;
    float source_effective_gain;
    int quiet_volume_db;
    float quiet_effective_gain;
    int64_t duration_ns;
} CohAudioPlayback;
typedef struct {
    unsigned checks, failed, source_cases;
    double maximum_source_error;
} CohAudioProof;

/* Source volume semantics: DirectSound hundredths of dB, clamped [-10000,0]. */
int coh_audio_ratio_to_db(float ratio, int *db);
float coh_audio_db_to_ratio(int db);
int coh_audio_parse(const uint8_t *data, size_t length, CohAudioFixture *out);
int coh_audio_scale(const CohAudioFixture *fixture, uint32_t frame_offset,
                    uint32_t frames, int db, int16_t *out);
/* One caller at a time; the calling worker exclusively owns AAudio close.
 * cancel may be called from the UI thread; never directly closes a stream. */
int coh_audio_play(const uint8_t *data, size_t length, CohAudioPlayback *out);
void coh_audio_cancel(void);
int coh_audio_is_active(void);
void coh_audio_set_foreground(int foreground);
int coh_audio_selftest(CohAudioProof *out);
#endif
