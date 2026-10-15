#ifndef COH_ENGINE_AUDIO_MUSIC_H
#define COH_ENGINE_AUDIO_MUSIC_H
#include "coh_mixer.h"
#include "coh_resample.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohMusic CohMusic;
/* Immutable random-access compressed source. read_at may perform disk I/O;
 * it is called only by open/pump on the non-realtime owner. Return bytes read,
 * zero on error/EOF. Source and context outlive successful close. A failed
 * short read is an I/O error, never interpreted as clean codec EOF. */
typedef size_t (*CohMusicReadAt)(void *,uint64_t offset,void *,size_t bytes);
typedef struct { CohMusicReadAt read_at; void *context; uint64_t bytes; } CohMusicSource;
typedef struct {
    uint32_t chunk_frames; /* 1..1024, must fit the mixer's configured ring. */
    uint32_t loop;         /* 0 or 1; rewind decoder on owner, not mixer loop. */
    uint64_t max_source_bytes; /* 1..512MiB; checked before source access. */
    CohCancel cancel;     /* Polled only on owner, before bounded work. */
} CohMusicConfig;
typedef struct {
    uint32_t source_rate, output_rate, channels, eof, cancelled, faulted;
    uint64_t source_frames, decoded_frames, submitted_frames, loops;
    uint64_t decode_calls, pump_calls, backpressure, source_reads, source_bytes;
    uint64_t maximum_pump_decode_calls, rejected_pages, crc_pages;
    size_t adapter_bytes; /* Fixed adapter allocation; codec allocations separate. */
    int codec_result;
} CohMusicReport;
/* Uses qualified pinned libogg/libvorbis and original ov_read signed16 LE
 * convention, but decodes bounded chunks instead of whole-file PCM. Single
 * logical Ogg Vorbis stream, 1/2ch, 8..96kHz, CRC-validated complete pages.
 * A full compressed integrity scan/seek index happens off callback at open;
 * compressed bytes are NOT copied/retained by this adapter. */
CohStatus coh_music_open(CohMixer *,CohMusicSource,const CohMusicConfig *,CohMusic **out);
/* Bounded work; max_decode_calls 1..32 per pump. COH_LIMIT is normal ring
 * backpressure: output remains retained, no further decode occurs until written.
 * Call frequently from the serialized mixer control/decoder owner. No internal
 * worker thread. Open/pump/close must NEVER run from mixer or AAudio callback. */
CohStatus coh_music_pump(CohMusic *,uint32_t max_decode_calls);
/* Builds a nonspatial event on MUSIC/AMBIENT/FX/VOICE bus. Caller may add source
 * radii/position/spatial fields, using unchanged source-authentic mixer gains. */
CohStatus coh_music_event(const CohMusic *,uint64_t at_frame,uint32_t emitter,
                          CohAudioBus,float gain,CohAudioEvent *out);
CohStatus coh_music_report(const CohMusic *,CohMusicReport *out);
/* Enqueues no controls. Stop emitter/cancel externally and let render retire
 * its reference before close. COH_STATE retains *music for retry; successful
 * close clears codec+resource and nulls caller handle. NULL is idempotent. */
CohStatus coh_music_close(CohMusic **music);
#ifdef __cplusplus
}
#endif
#endif
