#define _POSIX_C_SOURCE 200809L
#include "coh_mixer_aaudio.h"
#include <aaudio/AAudio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
struct CohMixerAAudio {
    CohMixer *mixer;AAudioStream *stream;CohMixerAAudioReport report;
    atomic_int error;
};
static int64_t now_ns(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)) return 0;
    return (int64_t)t.tv_sec*1000000000LL+t.tv_nsec;
}
static aaudio_data_callback_result_t data(AAudioStream *stream,void *user,void *output,int32_t frames) {
    (void)stream;CohMixerAAudio *sink=user;int64_t start=now_ns();
    if(frames<0||frames>8192||coh_mixer_render(sink->mixer,output,(uint32_t)frames)!=COH_OK) {
        if(frames>0&&frames<=8192&&output) memset(output,0,(size_t)frames*2*sizeof(float));
        coh_mixer_device_error(sink->mixer);return AAUDIO_CALLBACK_RESULT_STOP;
    }
    int64_t end=now_ns();sink->report.callback_calls++;
    if(start<=0||end<start) sink->report.clock_errors++;
    else {
        uint64_t ns=(uint64_t)(end-start);
        if(ns>sink->report.maximum_callback_ns) sink->report.maximum_callback_ns=ns;
        if(frames>0&&ns>(uint64_t)frames*1000000000u/coh_mixer_sample_rate(sink->mixer)) sink->report.deadline_overruns++;
    }
    return AAUDIO_CALLBACK_RESULT_CONTINUE;
}
static void error(AAudioStream *stream,void *user,aaudio_result_t code) {
    (void)stream;CohMixerAAudio *sink=user;
    atomic_store_explicit(&sink->error,code,memory_order_release);coh_mixer_device_error(sink->mixer);
}
static CohStatus wait_for(AAudioStream *s,aaudio_stream_state_t wanted) {
    int64_t begun=now_ns();
    /* Ten bounded 50ms waits also terminate if the monotonic clock fails or
     * stops advancing. Never depend solely on a successful timer read. */
    for(unsigned attempt=0;attempt<10;attempt++) {
        aaudio_stream_state_t state=AAudioStream_getState(s),next=state;
        if(state==wanted) return COH_OK;
        if(state==AAUDIO_STREAM_STATE_DISCONNECTED||state==AAUDIO_STREAM_STATE_CLOSED) return COH_IO;
        int64_t now=now_ns();
        if(begun<=0||now<begun||now-begun>=500000000LL) return COH_IO;
        aaudio_result_t result=AAudioStream_waitForStateChange(s,state,&next,50000000LL);
        if(result!=AAUDIO_OK&&result!=AAUDIO_ERROR_TIMEOUT) return COH_IO;
    }
    return COH_IO;
}
CohStatus coh_mixer_aaudio_open(CohMixer *m,CohMixerAAudio **out) {
    if(!out||!m) return COH_INVALID;
    *out=NULL;CohMixerAAudio *sink=calloc(1,sizeof *sink);if(!sink) return COH_LIMIT;
    sink->mixer=m;atomic_init(&sink->error,0);
    if(!atomic_is_lock_free(&sink->error)) { free(sink);return COH_UNSUPPORTED; }
    AAudioStreamBuilder *builder=NULL;
    if(AAudio_createStreamBuilder(&builder)!=AAUDIO_OK||!builder) { free(sink);return COH_IO; }
    AAudioStreamBuilder_setDirection(builder,AAUDIO_DIRECTION_OUTPUT);
    AAudioStreamBuilder_setFormat(builder,AAUDIO_FORMAT_PCM_FLOAT);
    AAudioStreamBuilder_setSampleRate(builder,(int32_t)coh_mixer_sample_rate(m));
    AAudioStreamBuilder_setChannelCount(builder,2);
    AAudioStreamBuilder_setSharingMode(builder,AAUDIO_SHARING_MODE_SHARED);
    AAudioStreamBuilder_setPerformanceMode(builder,AAUDIO_PERFORMANCE_MODE_LOW_LATENCY);
    AAudioStreamBuilder_setDataCallback(builder,data,sink);AAudioStreamBuilder_setErrorCallback(builder,error,sink);
    aaudio_result_t result=AAudioStreamBuilder_openStream(builder,&sink->stream);
    AAudioStreamBuilder_delete(builder);
    if(result!=AAUDIO_OK||!sink->stream) { free(sink);return COH_IO; }
    sink->report.opened=1;sink->report.sample_rate=AAudioStream_getSampleRate(sink->stream);
    sink->report.channels=AAudioStream_getChannelCount(sink->stream);sink->report.format=AAudioStream_getFormat(sink->stream);
    sink->report.frames_per_burst=AAudioStream_getFramesPerBurst(sink->stream);sink->report.buffer_frames=AAudioStream_getBufferSizeInFrames(sink->stream);
    *out=sink;
    if(sink->report.sample_rate!=(int32_t)coh_mixer_sample_rate(m)||sink->report.channels!=2||sink->report.format!=AAUDIO_FORMAT_PCM_FLOAT) {
        coh_mixer_aaudio_close(out,NULL);return COH_UNSUPPORTED;
    }
    if(AAudioStream_requestStart(sink->stream)!=AAUDIO_OK||wait_for(sink->stream,AAUDIO_STREAM_STATE_STARTED)!=COH_OK) {
        coh_mixer_aaudio_close(out,NULL);return COH_IO;
    }
    sink->report.started=1;return COH_OK;
}
CohStatus coh_mixer_aaudio_close(CohMixerAAudio **handle,CohMixerAAudioReport *report) {
    if(!handle) return COH_INVALID;
    if(!*handle) { if(report) memset(report,0,sizeof *report);return COH_OK; }
    CohMixerAAudio *sink=*handle;CohStatus result=COH_OK;
    if(AAudioStream_getState(sink->stream)==AAUDIO_STREAM_STATE_STARTED||AAudioStream_getState(sink->stream)==AAUDIO_STREAM_STATE_STARTING) {
        if(AAudioStream_requestStop(sink->stream)!=AAUDIO_OK||wait_for(sink->stream,AAUDIO_STREAM_STATE_STOPPED)!=COH_OK) result=COH_IO;
        else sink->report.stopped=1;
    }
    sink->report.xrun_count=AAudioStream_getXRunCount(sink->stream);
    sink->report.frames_read=AAudioStream_getFramesRead(sink->stream);sink->report.frames_written=AAudioStream_getFramesWritten(sink->stream);
    sink->report.timestamp_available=AAudioStream_getTimestamp(sink->stream,CLOCK_MONOTONIC,&sink->report.timestamp_frame,&sink->report.timestamp_ns)==AAUDIO_OK;
    if(AAudioStream_close(sink->stream)!=AAUDIO_OK) return COH_IO;
    /* Platform close joins callbacks before their context can be reclaimed. */
    sink->report.closed=1;sink->report.device_error=atomic_load_explicit(&sink->error,memory_order_acquire);
    coh_mixer_render(sink->mixer,NULL,0);
    sink->report.result=(int32_t)result;if(report) *report=sink->report;
    free(sink);*handle=NULL;return result;
}
