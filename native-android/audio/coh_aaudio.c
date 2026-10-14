#define _POSIX_C_SOURCE 200809L
#include "coh_audio.h"
#include <aaudio/AAudio.h>
#include <stdatomic.h>
#include <string.h>
#include <time.h>

static atomic_uint cancel_epoch=0;
static atomic_int active=0;
static atomic_int playing=0;
static atomic_int foreground=1;
static int64_t monotonic_ns(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC,&now)) return 0;
    return (int64_t)now.tv_sec*1000000000LL+now.tv_nsec;
}
void coh_audio_cancel(void) { atomic_fetch_add(&cancel_epoch,1); }
void coh_audio_set_foreground(int value) {
    atomic_store(&foreground,value!=0);
    if (!value) coh_audio_cancel();
}
int coh_audio_is_active(void) { return atomic_load(&playing); }
static int cancelled(unsigned epoch) { return !atomic_load(&foreground) || atomic_load(&cancel_epoch)!=epoch; }
static int await_state(AAudioStream *s,aaudio_stream_state_t wanted,unsigned epoch,int check_cancel) {
    int64_t deadline=monotonic_ns()+500000000LL;
    while (monotonic_ns()<deadline) {
        if (check_cancel && cancelled(epoch)) return COH_AUDIO_CANCELLED;
        aaudio_stream_state_t state=AAudioStream_getState(s),next=state;
        if (state==wanted) return COH_AUDIO_OK;
        if (state==AAUDIO_STREAM_STATE_DISCONNECTED || state==AAUDIO_STREAM_STATE_CLOSED) return COH_AUDIO_BACKEND;
        aaudio_result_t result=AAudioStream_waitForStateChange(s,state,&next,50000000LL);
        if (result!=AAUDIO_OK && result!=AAUDIO_ERROR_TIMEOUT) return COH_AUDIO_BACKEND;
    }
    return COH_AUDIO_BACKEND;
}
int coh_audio_play(const uint8_t *data,size_t length,CohAudioPlayback *out) {
    if (!out) return COH_AUDIO_INVALID;
    memset(out,0,sizeof *out);out->requested_clips=3;
    CohAudioFixture f;
    if (coh_audio_parse(data,length,&f)) return out->result=COH_AUDIO_INVALID;
    int expected=0;
    if (!atomic_compare_exchange_strong(&active,&expected,1)) return out->result=COH_AUDIO_BUSY;
    unsigned epoch=atomic_load(&cancel_epoch);
    int64_t begun=monotonic_ns();
    AAudioStreamBuilder *builder=0;AAudioStream *stream=0;
    int status=COH_AUDIO_BACKEND;
    out->requested_rate=(int)f.sample_rate;
    if (coh_audio_ratio_to_db(.6f,&out->source_volume_db)) goto cleanup;
    out->source_effective_gain=coh_audio_db_to_ratio(out->source_volume_db);
    if (coh_audio_ratio_to_db(.3f,&out->quiet_volume_db)) goto cleanup;
    out->quiet_effective_gain=coh_audio_db_to_ratio(out->quiet_volume_db);
    if (cancelled(epoch)) { status=COH_AUDIO_CANCELLED;goto cleanup; }
    if (AAudio_createStreamBuilder(&builder)!=AAUDIO_OK || !builder) { out->backend_errors++;goto cleanup; }
    AAudioStreamBuilder_setDirection(builder,AAUDIO_DIRECTION_OUTPUT);
    AAudioStreamBuilder_setFormat(builder,AAUDIO_FORMAT_PCM_I16);
    AAudioStreamBuilder_setSampleRate(builder,(int32_t)f.sample_rate);
    AAudioStreamBuilder_setChannelCount(builder,(int32_t)f.channels);
    AAudioStreamBuilder_setSharingMode(builder,AAUDIO_SHARING_MODE_SHARED);
    AAudioStreamBuilder_setPerformanceMode(builder,AAUDIO_PERFORMANCE_MODE_NONE);
    /* API 26 supports the sink contract. The optional usage/content setters
     * begin at API 28; retain AAudio's default MEDIA/MUSIC routing here. */
    if (AAudioStreamBuilder_openStream(builder,&stream)!=AAUDIO_OK || !stream) { out->backend_errors++;goto cleanup; }
    out->opened=1;
    out->actual_rate=AAudioStream_getSampleRate(stream);
    out->actual_channels=AAudioStream_getChannelCount(stream);
    out->actual_format=AAudioStream_getFormat(stream);
    if (out->actual_rate!=(int)f.sample_rate || out->actual_channels!=(int)f.channels || out->actual_format!=AAUDIO_FORMAT_PCM_I16) { out->backend_errors++;goto cleanup; }
    if (cancelled(epoch)) { status=COH_AUDIO_CANCELLED;goto cleanup; }
    if (AAudioStream_requestStart(stream)!=AAUDIO_OK) { out->backend_errors++;goto cleanup; }
    status=await_state(stream,AAUDIO_STREAM_STATE_STARTED,epoch,1);
    if (status!=COH_AUDIO_OK) { if (status<0) out->backend_errors++;goto cleanup; }
    out->started=1;
    atomic_store(&playing,1);
    int16_t buffer[512*2];
    /* 3 exact clips, with 150 ms silent separation, bounded below 7 seconds.
     * Partial writes retain their remaining samples rather than dropping them. */
    for (unsigned clip=0;clip<3;clip++) {
        uint32_t position=0;
        const uint32_t end=f.frames+(clip<2 ? f.sample_rate*15/100 : 0);
        while (position<end) {
            if (cancelled(epoch)) { status=COH_AUDIO_CANCELLED;goto cleanup; }
            if (monotonic_ns()-begun>7000000000LL) { out->backend_errors++;status=COH_AUDIO_BACKEND;goto cleanup; }
            uint32_t count=end-position;
            if (count>512) count=512;
            if (position<f.frames) {
                if (count>f.frames-position) count=f.frames-position;
                if (coh_audio_scale(&f,position,count,clip==1 ? out->quiet_volume_db : out->source_volume_db,buffer)) { status=COH_AUDIO_INVALID;goto cleanup; }
            } else memset(buffer,0,(size_t)count*f.channels*sizeof *buffer);
            uint32_t written=0;
            while (written<count) {
                if (cancelled(epoch)) { status=COH_AUDIO_CANCELLED;goto cleanup; }
                if (monotonic_ns()-begun>7000000000LL) { out->backend_errors++;status=COH_AUDIO_BACKEND;goto cleanup; }
                aaudio_result_t n=AAudioStream_write(stream,buffer+(size_t)written*f.channels,(int32_t)(count-written),100000000LL);
                out->write_calls++;
                if (n<0 || n>(int32_t)(count-written)) { out->backend_errors++;status=COH_AUDIO_BACKEND;goto cleanup; }
                if (n<(int32_t)(count-written)) out->partial_writes++;
                written+=(uint32_t)n;out->submitted_frames+=n;
            }
            position+=count;
        }
        out->completed_clips++;
    }
    /* Submitted buffers are not proof that the backend consumed them. Wait for
     * the monotonic consumption counter, with an independent bounded deadline. */
    {
        int64_t drain_deadline=monotonic_ns()+1500000000LL;
        do {
            if (cancelled(epoch)) { status=COH_AUDIO_CANCELLED;goto cleanup; }
            out->read_frames=AAudioStream_getFramesRead(stream);
            if (out->read_frames>=out->submitted_frames) break;
            struct timespec delay={0,10000000};nanosleep(&delay,0);
        } while (monotonic_ns()<drain_deadline);
        if (out->read_frames<out->submitted_frames) { out->backend_errors++;status=COH_AUDIO_BACKEND;goto cleanup; }
    }
    status=COH_AUDIO_OK;
cleanup:
    if (stream) {
        out->xrun_count=AAudioStream_getXRunCount(stream);
        out->read_frames=AAudioStream_getFramesRead(stream);
        if (AAudioStream_getTimestamp(stream,CLOCK_MONOTONIC,&out->timestamp_frame,&out->timestamp_ns)==AAUDIO_OK) out->timestamp_available=1;
        if (out->started) {
            if (AAudioStream_requestStop(stream)==AAUDIO_OK && await_state(stream,AAUDIO_STREAM_STATE_STOPPED,epoch,0)==COH_AUDIO_OK) out->stopped=1;
            else { out->backend_errors++;status=COH_AUDIO_BACKEND; }
        }
        if (AAudioStream_close(stream)==AAUDIO_OK) out->closed=1;
        else { out->backend_errors++;status=COH_AUDIO_BACKEND; }
    }
    if (builder && AAudioStreamBuilder_delete(builder)!=AAUDIO_OK) { out->backend_errors++;status=COH_AUDIO_BACKEND; }
    out->cancelled=cancelled(epoch);
    out->duration_ns=monotonic_ns()-begun;
    out->result=status;
    atomic_store(&playing,0);
    atomic_store(&active,0);
    return status;
}
