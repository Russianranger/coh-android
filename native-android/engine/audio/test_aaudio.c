#define _POSIX_C_SOURCE 200809L
/* Backend-owner failure paths tested with an explicit host-only AAudio shim.
 * This is not evidence of Android audio playback or device lifecycle behavior. */
#include "coh_audio_session.h"
#include <aaudio/AAudio.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef struct { int rate,channels,format;AAudioDataCallback data;AAudioErrorCallback error;void *user; } Settings;
struct AAudioStreamBuilder { Settings s; };
struct AAudioStream { Settings s;int state;int64_t frames; };
static int fail_create,fail_open,fail_start,fail_stop,fail_close,wrong_format,fail_clock,never_start;
int __real_clock_gettime(clockid_t,struct timespec *);
int __wrap_clock_gettime(clockid_t id,struct timespec *t) { return fail_clock ? -1 : __real_clock_gettime(id,t); }
static unsigned opened,closed,builders;
static int late_close_error;
static AAudioStream *active;
aaudio_result_t AAudio_createStreamBuilder(AAudioStreamBuilder **b) { if(fail_create) return -2;*b=calloc(1,sizeof **b);builders++;return 0; }
aaudio_result_t AAudioStreamBuilder_delete(AAudioStreamBuilder *b) { free(b);builders--;return 0; }
void AAudioStreamBuilder_setDirection(AAudioStreamBuilder *b,int32_t n) { (void)b;assert(n==AAUDIO_DIRECTION_OUTPUT); }
void AAudioStreamBuilder_setFormat(AAudioStreamBuilder *b,int32_t n) { b->s.format=n; }
void AAudioStreamBuilder_setSampleRate(AAudioStreamBuilder *b,int32_t n) { b->s.rate=n; }
void AAudioStreamBuilder_setChannelCount(AAudioStreamBuilder *b,int32_t n) { b->s.channels=n; }
void AAudioStreamBuilder_setSharingMode(AAudioStreamBuilder *b,int32_t n) { (void)b;assert(n==AAUDIO_SHARING_MODE_SHARED); }
void AAudioStreamBuilder_setPerformanceMode(AAudioStreamBuilder *b,int32_t n) { (void)b;assert(n==AAUDIO_PERFORMANCE_MODE_LOW_LATENCY); }
void AAudioStreamBuilder_setDataCallback(AAudioStreamBuilder *b,AAudioDataCallback f,void *p) { b->s.data=f;b->s.user=p; }
void AAudioStreamBuilder_setErrorCallback(AAudioStreamBuilder *b,AAudioErrorCallback f,void *p) { b->s.error=f;b->s.user=p; }
aaudio_result_t AAudioStreamBuilder_openStream(AAudioStreamBuilder *b,AAudioStream **s) {
    if(fail_open) return -2;
    *s=calloc(1,sizeof **s);(*s)->s=b->s;if(wrong_format)(*s)->s.format=1;active=*s;opened++;return 0;
}
int32_t AAudioStream_getSampleRate(AAudioStream *s) { return s->s.rate; }
int32_t AAudioStream_getChannelCount(AAudioStream *s) { return s->s.channels; }
int32_t AAudioStream_getFormat(AAudioStream *s) { return s->s.format; }
int32_t AAudioStream_getFramesPerBurst(AAudioStream *s) { (void)s;return 192; }
int32_t AAudioStream_getBufferSizeInFrames(AAudioStream *s) { (void)s;return 384; }
aaudio_stream_state_t AAudioStream_getState(AAudioStream *s) { return s->state; }
aaudio_result_t AAudioStream_waitForStateChange(AAudioStream *s,aaudio_stream_state_t previous,aaudio_stream_state_t *next,int64_t timeout) {
    (void)previous;(void)timeout;*next=s->state;return 0;
}
aaudio_result_t AAudioStream_requestStart(AAudioStream *s) { if(fail_start)return -2;s->state=never_start?AAUDIO_STREAM_STATE_STARTING:AAUDIO_STREAM_STATE_STARTED;return 0; }
aaudio_result_t AAudioStream_requestStop(AAudioStream *s) { if(fail_stop)return -2;s->state=AAUDIO_STREAM_STATE_STOPPED;return 0; }
aaudio_result_t AAudioStream_close(AAudioStream *s) {
    if(fail_close)return -2;
    if(late_close_error) { s->s.error(s,s->s.user,late_close_error);late_close_error=0; }
    free(s);active=NULL;closed++;return 0;
}
int32_t AAudioStream_getXRunCount(AAudioStream *s) { (void)s;return 3; }
int64_t AAudioStream_getFramesRead(AAudioStream *s) { return s->frames; }
int64_t AAudioStream_getFramesWritten(AAudioStream *s) { return s->frames; }
aaudio_result_t AAudioStream_getTimestamp(AAudioStream *s,int32_t clock,int64_t *frame,int64_t *ns) { (void)clock;*frame=s->frames;*ns=100;return 0; }
static void fire(float *out,int frames) { assert(active&&active->state==AAUDIO_STREAM_STATE_STARTED);assert(active->s.data(active,active->s.user,out,frames)==AAUDIO_CALLBACK_RESULT_CONTINUE);active->frames+=frames; }

static CohAudioSessionReport session_report(CohAudioSession *s, CohAudioSessionState state) {
    CohAudioSessionReport r;
    assert(coh_audio_session_report(s,&r)==COH_OK && r.state==state);
    return r;
}
static void test_session(void) {
    CohMixerConfig config={44100,4,16,2,400000,0};CohMixer *m=NULL;
    assert(coh_mixer_create(&config,&m)==COH_OK);
    CohAudioSession *s=NULL;CohAudioSessionReport r;CohMixerDiagnostics d;
    assert(coh_audio_session_create(NULL,&s)==COH_INVALID);
    assert(coh_audio_session_create(m,NULL)==COH_INVALID);
    assert(coh_audio_session_pump(NULL)==COH_INVALID);
    assert(coh_audio_session_recover(NULL)==COH_INVALID);
    assert(coh_audio_session_report(NULL,&r)==COH_INVALID);
    assert(coh_audio_session_destroy(NULL)==COH_INVALID);
    assert(coh_audio_session_destroy(&s)==COH_OK);
    assert(coh_mixer_aaudio_device_error(NULL)==0);
    assert(coh_audio_session_create(m,&s)==COH_OK);
    session_report(s,COH_AUDIO_SESSION_SUSPENDED);
    assert(coh_audio_session_report(s,NULL)==COH_INVALID);
    assert(coh_audio_session_environment(s,-1,1)==COH_INVALID);
    assert(coh_audio_session_environment(s,1,2)==COH_INVALID);
    assert(coh_audio_session_recover(s)==COH_STATE);
    assert(coh_audio_session_environment(s,1,0)==COH_OK && !active);
    int16_t pcm[2]={8192,8192};CohAudioResource resource;
    assert(coh_mixer_cache_pcm16(m,(CohAssetId){"data/sound/lifecycle.ogg",1},pcm,2,1,44100,&resource)==COH_OK);
    CohAudioEvent e={0};e.resource=resource;e.gain=1;e.loop=1;e.emitter=9;
    assert(coh_mixer_play(m,&e)==COH_OK);
    assert(coh_audio_session_environment(s,1,1)==COH_OK);
    r=session_report(s,COH_AUDIO_SESSION_RUNNING);assert(r.opens==1 && r.has_backend);
    assert(coh_audio_session_environment(s,1,1)==COH_OK);
    assert(session_report(s,COH_AUDIO_SESSION_RUNNING).opens==1);
    float out[128];fire(out,64);assert(out[0]==.25f);
    assert(coh_audio_session_environment(s,1,0)==COH_OK);
    r=session_report(s,COH_AUDIO_SESSION_SUSPENDED);assert(!r.has_backend && r.closes==1);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.rendered_frames==64 && d.retained_resources==1);
    assert(coh_audio_session_pump(s)==COH_OK);
    assert(coh_audio_session_environment(s,1,1)==COH_OK);fire(out,64);assert(out[0]==.25f);
    assert(coh_audio_session_environment(s,0,1)==COH_OK);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.rendered_frames==128);
    /* Surface loss is intentionally absent from this API: activity+focus remain
     * active, so an unrelated graphics notification cannot restart audio. */
    assert(coh_audio_session_environment(s,1,1)==COH_OK);
    for(unsigned i=0;i<16;i++) assert(coh_mixer_bus_gain(m,COH_BUS_FX,1)==COH_OK);
    assert(coh_audio_session_environment(s,0,1)==COH_OK);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.rendered_frames==128 && d.retained_resources==1);
    assert(coh_audio_session_environment(s,1,1)==COH_OK);fire(out,64);assert(out[0]==.25f);
    /* Failed close retains both sink and session; a rapid foreground transition
     * must complete that close before allocating a replacement. */
    fail_close=1;assert(coh_audio_session_environment(s,0,1)==COH_IO);
    r=session_report(s,COH_AUDIO_SESSION_CLOSING);assert(r.has_backend && r.close_failures==1);
    assert(coh_audio_session_pump(s)==COH_IO);
    fail_close=0;assert(coh_audio_session_environment(s,1,1)==COH_OK);
    r=session_report(s,COH_AUDIO_SESSION_RUNNING);assert(r.close_failures==2);
    fire(out,64);assert(out[0]==.25f);
    /* Device loss flushes source refs and latches until explicit recovery. */
    active->s.error(active,active->s.user,-899);
    assert(coh_audio_session_pump(s)==COH_IO);
    r=session_report(s,COH_AUDIO_SESSION_FAULTED);
    assert(r.device_failures==1 && r.last_device_error==-899 && !r.has_backend);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.device_errors==1 && d.retained_resources==0);
    uint64_t before=r.opens;
    assert(coh_audio_session_pump(s)==COH_IO);
    assert(coh_audio_session_environment(s,1,1)==COH_IO);
    assert(session_report(s,COH_AUDIO_SESSION_FAULTED).opens==before);
    assert(coh_audio_session_recover(s)==COH_OK);
    fire(out,64);for(unsigned i=0;i<128;i++)assert(out[i]==0);
    assert(coh_mixer_play(m,&e)==COH_OK);fire(out,64);assert(out[0]==.25f);
    /* The close snapshot must catch errors racing the pre-close atomic poll. */
    late_close_error=-898;
    assert(coh_audio_session_environment(s,0,1)==COH_IO);
    r=session_report(s,COH_AUDIO_SESSION_FAULTED);assert(r.device_failures==2 && r.last_device_error==-898);
    assert(coh_audio_session_recover(s)==COH_OK && !active);
    session_report(s,COH_AUDIO_SESSION_SUSPENDED);
    /* An open failure can itself retain a failed-close context. */
    fail_start=1;fail_close=1;
    assert(coh_audio_session_environment(s,1,1)==COH_IO);
    r=session_report(s,COH_AUDIO_SESSION_CLOSING);assert(r.open_failures==1 && r.has_backend);
    fail_start=0;fail_close=0;assert(coh_audio_session_pump(s)==COH_OK);
    session_report(s,COH_AUDIO_SESSION_RUNNING);
    /* Callback validation errors use the same observable recovery path. */
    assert(active->s.data(active,active->s.user,out,8193)==AAUDIO_CALLBACK_RESULT_STOP);
    assert(coh_audio_session_pump(s)==COH_IO);
    r=session_report(s,COH_AUDIO_SESSION_FAULTED);
    assert(r.last_device_error==COH_MIXER_AAUDIO_RENDER_ERROR && r.device_failures==3);
    assert(coh_audio_session_recover(s)==COH_OK);
    /* Retried destruction cannot reclaim a callback context after failed close. */
    fail_close=1;assert(coh_audio_session_destroy(&s)==COH_IO && s);
    session_report(s,COH_AUDIO_SESSION_CLOSING);
    fail_close=0;assert(coh_audio_session_destroy(&s)==COH_OK && !s);
    assert(coh_audio_session_destroy(&s)==COH_OK);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.device_errors==3 && d.retained_resources==0);
    /* Cached PCM remains owned by the borrowed mixer after session teardown. */
    assert(coh_mixer_play(m,&e)==COH_OK);
    assert(coh_audio_session_create(m,&s)==COH_OK);
    assert(coh_audio_session_environment(s,1,1)==COH_OK);fire(out,64);assert(out[0]==.25f);
    fail_stop=1;assert(coh_audio_session_destroy(&s)==COH_IO && !s);fail_stop=0;
    assert(coh_mixer_cancel_all(m)==COH_OK);assert(coh_mixer_render(m,NULL,0)==COH_OK);
    assert(coh_mixer_diagnostics(m,&d)==COH_OK && d.retained_resources==0);
    coh_mixer_destroy(m);
    printf("{\"kind\":\"audio_session_host_owner\",\"passed\":true,\"device_faults\":3,\"scope\":\"host shim lifecycle only; no Android focus or audible playback qualification\"}\n");
}

int main(void) {
    CohMixerConfig config={44100,4,16,2,400000,0};CohMixer *m=NULL;assert(coh_mixer_create(&config,&m)==COH_OK);
    CohMixerAAudio *sink=NULL;CohMixerAAudioReport report;
    assert(coh_mixer_aaudio_open(NULL,&sink)==COH_INVALID);assert(coh_mixer_aaudio_close(&sink,&report)==COH_OK);
    fail_create=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_IO&&!sink);fail_create=0;
    fail_open=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_IO&&!sink);fail_open=0;
    wrong_format=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_UNSUPPORTED&&!sink);wrong_format=0;
    fail_start=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_IO&&!sink);fail_start=0;
    fail_clock=1;never_start=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_IO&&!sink);fail_clock=0;never_start=0;
    /* The clock can remain valid while a backend never transitions: the
     * attempt cap must still terminate, independent of elapsed wall time. */
    never_start=1;assert(coh_mixer_aaudio_open(m,&sink)==COH_IO&&!sink);never_start=0;
    int16_t pcm[2]={8192,8192};CohAudioResource resource;
    assert(coh_mixer_cache_pcm16(m,(CohAssetId){"data/sound/test.ogg",1},pcm,2,1,44100,&resource)==COH_OK);
    CohAudioEvent e={0};e.resource=resource;e.gain=1;e.loop=1;e.emitter=1;
    assert(coh_mixer_play(m,&e)==COH_OK);assert(coh_mixer_aaudio_open(m,&sink)==COH_OK);
    float out[128];fire(out,64);for(unsigned i=0;i<128;i++)assert(out[i]==.25f);
    fail_clock=1;fire(out,64);fail_clock=0;
    assert(coh_mixer_pause(m,1)==COH_OK);fire(out,64);for(unsigned i=0;i<128;i++)assert(out[i]==0);
    assert(coh_mixer_aaudio_close(&sink,&report)==COH_OK&&!sink&&report.closed&&report.stopped);
    assert(report.callback_calls==3&&report.frames_read==192&&report.xrun_count==3&&report.timestamp_available&&report.clock_errors==1);
    assert(coh_mixer_pause(m,0)==COH_OK);assert(coh_mixer_aaudio_open(m,&sink)==COH_OK);fire(out,64);assert(out[0]==.25f);
    active->state=AAUDIO_STREAM_STATE_DISCONNECTED;active->s.error(active,active->s.user,-899);
    assert(coh_mixer_aaudio_close(&sink,&report)==COH_OK&&!sink&&report.device_error==-899);
    CohMixerDiagnostics d;assert(coh_mixer_diagnostics(m,&d)==COH_OK&&d.device_errors==1&&d.retained_resources==0);
    assert(coh_mixer_pause(m,0)==COH_OK);assert(coh_mixer_play(m,&e)==COH_OK);assert(coh_mixer_aaudio_open(m,&sink)==COH_OK);fire(out,64);assert(out[0]==.25f);
    fail_close=1;assert(coh_mixer_aaudio_close(&sink,&report)==COH_IO&&sink);fail_close=0;
    assert(coh_mixer_aaudio_close(&sink,&report)==COH_OK&&!sink);
    assert(coh_mixer_aaudio_open(m,&sink)==COH_OK);fail_stop=1;
    assert(coh_mixer_aaudio_close(&sink,&report)==COH_IO&&!sink&&report.closed);fail_stop=0;
    assert(coh_mixer_aaudio_open(m,&sink)==COH_OK);
    assert(active->s.data(active,active->s.user,out,8193)==AAUDIO_CALLBACK_RESULT_STOP);
    assert(coh_mixer_aaudio_close(&sink,&report)==COH_OK&&!sink);
    assert(opened==closed&&builders==0&&!active);coh_mixer_destroy(m);
    test_session();assert(opened==closed&&builders==0&&!active);
    printf("{\"kind\":\"aaudio_host_owner\",\"passed\":true,\"opened\":%u,\"closed\":%u,\"scope\":\"host shim lifecycle only\"}\n",opened,closed);return 0;
}
