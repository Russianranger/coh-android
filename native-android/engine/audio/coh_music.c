#define OV_EXCLUDE_STATIC_CALLBACKS
#include <vorbis/vorbisfile.h>
#include "coh_music.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct CohMusic {
    CohMixer *mixer;CohAudioResource resource;CohMusicSource source;
    CohMusicConfig config;CohMusicReport report;CohResampler resample;
    OggVorbis_File decoder;uint64_t cursor, loop_frames;
    uint32_t opened, stream_opened, io_error, decoder_eof;
    uint32_t input_frames,input_at,output_frames;
    int16_t input[2048],output[2048];
};
static int cancelled(const CohMusic *m) { return m->config.cancel.poll&&m->config.cancel.poll(m->config.cancel.context); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint64_t get64(const uint8_t *p) { return get32(p)|(uint64_t)get32(p+4)<<32; }
static int exact(CohMusic *m,uint64_t offset,void *out,size_t size) {
    if (offset>m->source.bytes||size>m->source.bytes-offset) return 0;
    size_t got=m->source.read_at(m->source.context,offset,out,size);
    m->report.source_reads++;m->report.source_bytes+=got;
    if (got!=size) { m->io_error=1;return 0; }
    return 1;
}
static size_t read_source(void *out,size_t item,size_t count,void *opaque) {
    CohMusic *m=opaque;
    if (!item||!count||m->io_error||m->cursor>m->source.bytes) return 0;
    uint64_t available=(m->source.bytes-m->cursor)/item;
    if (count>available) count=(size_t)available;
    if (!count) return 0;
    size_t bytes=item*count;
    if (!exact(m,m->cursor,out,bytes)) return 0;
    m->cursor+=bytes;return count;
}
static int seek_source(void *opaque,ogg_int64_t offset,int whence) {
    CohMusic *m=opaque;uint64_t base;
    switch (whence) { case SEEK_SET:base=0;break;case SEEK_CUR:base=m->cursor;break;case SEEK_END:base=m->source.bytes;break;default:return -1; }
    if (offset<-(ogg_int64_t)base||offset>(ogg_int64_t)(m->source.bytes-base)) return -1;
    m->cursor=(uint64_t)((ogg_int64_t)base+offset);return 0;
}
static long tell_source(void *opaque) { CohMusic *m=opaque;return m->cursor<=LONG_MAX ? (long)m->cursor : -1; }
static int close_source(void *opaque) { (void)opaque;return 0; } /* Source stays borrowed. */

/* Same CRC polynomial, page/serial/sequence/EOS policy as accepted decoder;
 * streamed read_at source removes whole-compressed/whole-PCM storage limits.
 * At most one maximum-size Ogg page exists on the non-realtime stack. */
static CohStatus preflight(CohMusic *m,uint64_t *granule) {
    uint8_t page[65307];uint64_t offset=0;uint32_t serial=0,sequence=0;int ended=0;
    while (offset<m->source.bytes) {
        if (cancelled(m)) return COH_CANCELLED;
        if (ended||m->source.bytes-offset<27||!exact(m,offset,page,27)) return m->io_error?COH_IO:COH_INVALID;
        if (memcmp(page,"OggS",4)||page[4]||(page[5]&~7u)) return COH_INVALID;
        size_t n=page[26],bytes=27+n;
        if (m->source.bytes-offset<bytes||!exact(m,offset+27,page+27,n)) return m->io_error?COH_IO:COH_INVALID;
        for (size_t i=0;i<n;i++) bytes+=page[27+i];
        if (bytes>sizeof page||bytes>m->source.bytes-offset||!exact(m,offset+27+n,page+27+n,bytes-27-n)) return m->io_error?COH_IO:COH_INVALID;
        if (!sequence) {
            if (!(page[5]&2)||(page[5]&1)||get32(page+18)) return COH_INVALID;
            serial=get32(page+14);
        } else if ((page[5]&2)||get32(page+14)!=serial||get32(page+18)!=sequence) return COH_INVALID;
        if (sequence==UINT32_MAX) return COH_LIMIT;
        ++sequence;
        uint32_t crc=0;
        for (size_t i=0;i<bytes;i++) {
            crc^=(uint32_t)((i>=22&&i<26)?0:page[i])<<24;
            for (unsigned j=0;j<8;j++) crc=(crc<<1)^((crc&0x80000000u)?0x04c11db7u:0u);
        }
        if (crc!=get32(page+22)) { m->report.rejected_pages++;return COH_INVALID; }
        m->report.crc_pages++;
        if (page[5]&4) { ended=1;*granule=get64(page+6); }
        offset+=bytes;
    }
    return ended&&sequence>=3 ? COH_OK : COH_INVALID;
}
static CohStatus fault(CohMusic *m,CohStatus status) {
    m->report.cancelled=status==COH_CANCELLED;
    m->report.faulted=status!=COH_CANCELLED;
    (void)coh_mixer_stream_finish(m->mixer,m->resource);
    return status;
}
CohStatus coh_music_open(CohMixer *mix,CohMusicSource source,const CohMusicConfig *config,CohMusic **out) {
    if (!out) return COH_INVALID;
    *out=NULL;
    if (!mix||!source.read_at||!config||!source.bytes||!config->chunk_frames||config->chunk_frames>1024||config->loop>1||
        !config->max_source_bytes||config->max_source_bytes>UINT64_C(512)*1024*1024) return COH_INVALID;
    if (source.bytes>config->max_source_bytes) return COH_LIMIT;
    CohMusic *m=calloc(1,sizeof *m);if (!m) return COH_LIMIT;
    m->mixer=mix;m->source=source;m->config=*config;m->report.adapter_bytes=sizeof *m;
    uint64_t granule=0;CohStatus result=preflight(m,&granule);
    if (result) goto failed;
    ov_callbacks cb={read_source,seek_source,close_source,tell_source};
    m->report.codec_result=ov_open_callbacks(m,&m->decoder,NULL,0,cb);
    if (m->report.codec_result<0) { result=COH_IO;goto failed; }
    m->opened=1;
    if (m->io_error) { result=COH_IO;goto failed; }
    vorbis_info *info=ov_info(&m->decoder,-1);ogg_int64_t frames=ov_pcm_total(&m->decoder,-1);
    if (ov_streams(&m->decoder)!=1||!info||(info->channels!=1&&info->channels!=2)||info->rate<8000||info->rate>96000||
        frames<=0||(uint64_t)frames!=granule||(uint64_t)frames>(uint64_t)info->rate*86400) { result=COH_UNSUPPORTED;goto failed; }
    m->report.source_rate=(uint32_t)info->rate;m->report.output_rate=coh_mixer_sample_rate(mix);
    m->report.channels=(uint32_t)info->channels;m->report.source_frames=(uint64_t)frames;
    result=coh_resample_init(&m->resample,m->report.source_rate,m->report.output_rate,m->report.channels);
    if (result) goto failed;
    result=coh_mixer_stream_open(mix,m->report.channels,m->report.output_rate,&m->resource);
    if (result) goto failed;
    m->stream_opened=1;*out=m;return COH_OK;
failed:
    if (m->opened) ov_clear(&m->decoder);
    free(m);return result;
}
CohStatus coh_music_pump(CohMusic *m,uint32_t maximum) {
    if (!m||!maximum||maximum>32) return COH_INVALID;
    if (m->report.cancelled) return COH_CANCELLED;
    if (m->report.faulted) return COH_IO;
    if (m->report.eof) return COH_OK;
    m->report.pump_calls++;uint64_t before=m->report.decode_calls;
    /* Each iteration either submits a chunk, converts a bounded span, decodes
     * one bounded packet, or returns. Budget caps even pathological ratios. */
    for (uint32_t steps=0;steps<maximum*32+8;steps++) {
        if (cancelled(m)) return fault(m,COH_CANCELLED);
        if (m->output_frames) {
            CohStatus result=coh_mixer_stream_write(m->mixer,m->resource,m->output,m->output_frames);
            if (result==COH_LIMIT) { m->report.backpressure++;return COH_LIMIT; }
            if (result) return fault(m,result);
            m->report.submitted_frames+=m->output_frames;m->output_frames=0;
        }
        if (m->input_at<m->input_frames||m->decoder_eof) {
            uint32_t used=0,made=0;
            CohStatus result=coh_resample_process(&m->resample,m->input+(size_t)m->input_at*m->report.channels,m->input_frames-m->input_at,
                m->output,m->config.chunk_frames,&used,&made,(int)m->decoder_eof);
            if (result) return fault(m,result);
            m->input_at+=used;m->output_frames=made;
            if (made) continue;
            if (m->resample.finished) {
                result=coh_mixer_stream_finish(m->mixer,m->resource);
                if (result) return fault(m,result);
                m->report.eof=1;return COH_OK;
            }
        }
        if (m->report.decode_calls-before>=maximum) return COH_OK;
        int section=0;
        long bytes=ov_read(&m->decoder,(char *)m->input,sizeof m->input,0,2,1,&section);
        m->report.decode_calls++;
        uint64_t count=m->report.decode_calls-before;
        if (count>m->report.maximum_pump_decode_calls) m->report.maximum_pump_decode_calls=count;
        m->report.codec_result=(int)bytes;
        if (bytes<0||section||m->io_error||bytes%(2*m->report.channels)) return fault(m,COH_IO);
        if (!bytes) {
            if (m->loop_frames!=m->report.source_frames||ov_pcm_tell(&m->decoder)!=(ogg_int64_t)m->report.source_frames) return fault(m,COH_IO);
            if (m->config.loop) {
                m->report.codec_result=ov_pcm_seek(&m->decoder,0);
                if (m->report.codec_result||m->io_error) return fault(m,COH_IO);
                m->report.loops++;m->loop_frames=0;
            } else m->decoder_eof=1;
            m->input_at=m->input_frames=0;
            continue;
        }
        m->input_frames=(uint32_t)bytes/(2*m->report.channels);m->input_at=0;
        m->loop_frames+=m->input_frames;m->report.decoded_frames+=m->input_frames;
        if (m->loop_frames>m->report.source_frames) return fault(m,COH_IO);
    }
    return COH_OK;
}
CohStatus coh_music_event(const CohMusic *m,uint64_t frame,uint32_t emitter,CohAudioBus bus,float gain,CohAudioEvent *out) {
    if (!m||!out||bus<0||bus>=COH_BUS_COUNT||!isfinite(gain)||gain<0||gain>1) return COH_INVALID;
    CohAudioEvent event={0};event.at_frame=frame;event.emitter=emitter;event.resource=m->resource;
    event.kind=COH_AUDIO_STREAM;event.bus=bus;event.gain=gain;event.priority=1;
    *out=event;return COH_OK;
}
CohStatus coh_music_report(const CohMusic *m,CohMusicReport *out) {
    if (!m||!out) return COH_INVALID;
    *out=m->report;return COH_OK;
}
CohStatus coh_music_close(CohMusic **handle) {
    if (!handle) return COH_INVALID;
    CohMusic *m=*handle;if (!m) return COH_OK;
    if (m->stream_opened) {
        CohStatus result=coh_mixer_stream_close(m->mixer,m->resource);
        if (result) return result;
    }
    if (m->opened) ov_clear(&m->decoder);
    free(m);*handle=NULL;return COH_OK;
}
