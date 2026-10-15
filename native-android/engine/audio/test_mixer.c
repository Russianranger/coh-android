#define _POSIX_C_SOURCE 200809L
#include "coh_mixer.h"
#include "../../audio/coh_audio.h"
#ifdef WITH_DECODE
#include "../../decode/coh_decode.h"
#endif
#include <assert.h>
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Link-time allocation guard makes allocation/free in render a test failure. */
static _Thread_local int realtime;
static atomic_long allocations;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void *,size_t);void __real_free(void *);
void *__wrap_malloc(size_t n) { assert(!realtime);void *p=__real_malloc(n);if(p)atomic_fetch_add(&allocations,1);return p; }
void *__wrap_calloc(size_t a,size_t b) { assert(!realtime);void *p=__real_calloc(a,b);if(p)atomic_fetch_add(&allocations,1);return p; }
void *__wrap_realloc(void *p,size_t n) {
    assert(!realtime);void *q=__real_realloc(p,n);
    if(!p&&q) atomic_fetch_add(&allocations,1);
    if(p&&!n) atomic_fetch_sub(&allocations,1);
    return q;
}
void __wrap_free(void *p) { assert(!realtime);if(p)atomic_fetch_sub(&allocations,1);__real_free(p); }
extern float oracle_attenuation(float,float,float,int);
extern int oracle_db(float);
extern float oracle_gain(int);
extern float oracle_spatial(float,float,float,float,float,float,int,float *);
static unsigned checks,source_checks;
#define CHECK(c) do { checks++;if(!(c)) { fprintf(stderr,"check failed at %s:%d: %s\n",__FILE__,__LINE__,#c);abort(); } } while(0)
static void near(float a,float b,float tolerance) { CHECK(isfinite(a)&&fabsf(a-b)<=tolerance); }
static CohMixer *make(uint32_t voices,uint32_t events,uint32_t cache,uint32_t stream) {
    CohMixer *m=NULL;CohMixerConfig c={44100,voices,events,cache,(size_t)cache*200000,stream};
    CHECK(coh_mixer_create(&c,&m)==COH_OK);CHECK(m!=NULL);return m;
}
static void render(CohMixer *m,float *out,uint32_t n) { realtime=1;CohStatus s=coh_mixer_render(m,out,n);realtime=0;CHECK(s==COH_OK); }
static CohMixerDiagnostics diagnostics(CohMixer *m) { CohMixerDiagnostics d;CHECK(coh_mixer_diagnostics(m,&d)==COH_OK);return d; }
static CohAudioResource cached(CohMixer *m,const char *name,const int16_t *pcm,uint32_t frames,uint32_t channels) {
    CohAudioResource h;CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){name,1},pcm,frames,channels,44100,&h)==COH_OK);return h;
}
static CohAudioEvent event(CohAudioResource h,uint32_t emitter,float gain) {
    CohAudioEvent e={0};e.resource=h;e.emitter=emitter;e.source=emitter;e.gain=gain;e.bus=COH_BUS_FX;e.kind=COH_AUDIO_CACHED;return e;
}
static void oracle_test(void) {
    for(unsigned i=0;i<1000;i++) {
        float inner=(float)(i%21),outer=inner+(float)(1+i%19),distance=(float)(i%53)*.73f;
        float a=coh_mixer_attenuation(inner,outer,distance,i&1),b=oracle_attenuation(inner,outer,distance,i&1);
        near(a,b,1e-7f);source_checks++;
        CohAudioEvent e={0};e.gain=(float)(i%11)*.1f;e.spatial=1;e.inner_radius=inner;e.outer_radius=outer;e.ignore_ramp=i&1;
        e.position=(CohVec3){distance,0,0};float l,r;
        coh_mixer_spatial_gains(&e,(CohVec3){0,0,0},(CohVec3){1,0,0},.6f,&l,&r);
        float g=oracle_gain(oracle_db(fminf(1.f,b*e.gain*.6f)));
        float pan=distance>0&&b*e.gain>0 ? 1 : 0;
        near(l,g*oracle_gain((int)(-pan*2000)),1e-6f);near(r,g,1e-6f);source_checks+=2;
    }
    CHECK(coh_mixer_attenuation(5,4,0,0)==0);CHECK(coh_mixer_attenuation(0,4,NAN,0)==0);
    near(coh_mixer_attenuation(5,5,4,0),1,0);near(coh_mixer_attenuation(5,5,5,0),0,0);
    for(unsigned i=0;i<1000;i++) {
        CohAudioEvent e={0};e.gain=(i%9+1)*.1f;e.spatial=1;e.inner_radius=2;e.outer_radius=40;e.ignore_ramp=i&1;
        e.position=(CohVec3){(float)((int)(i%25)-12),(float)(i%19),(float)(i%13)};
        float pan=0,volume=oracle_spatial(e.inner_radius,e.outer_radius,e.position.x,e.position.y,e.position.z,e.gain,e.ignore_ramp,&pan);
        float gain=oracle_gain(oracle_db(volume*.6f));int db=(int)(pan*2000);float l,r;
        coh_mixer_spatial_gains(&e,(CohVec3){0,0,0},(CohVec3){1,0,0},.6f,&l,&r);
        /* Source sums volume-weighted directions before dividing; reduction
         * rounding may move quantized pan by one hundredth of a decibel. */
        near(l,gain*oracle_gain(db>0?-db:0),2e-4f);near(r,gain*oracle_gain(db<0?db:0),2e-4f);source_checks+=2;
    }
}
static void scheduling(void) {
    CohMixer *m=make(4,16,2,0);int16_t pcm[]={8192,16384,-8192,-16384,4096,8192,0,0};
    CohAudioResource h=cached(m,"data/sound/ogg/test/schedule.ogg",pcm,4,2);
    CohAudioEvent a=event(h,1,.25f),b=event(h,2,.5f);a.at_frame=3;b.at_frame=5;b.bus=COH_BUS_MUSIC;
    CHECK(coh_mixer_play(m,&a)==COH_OK);CHECK(coh_mixer_play(m,&b)==COH_OK);
    float out[24];render(m,out,12);
    float ga=oracle_gain(oracle_db(.25f)),gb=oracle_gain(oracle_db(.5f));
    for(unsigned f=0;f<12;f++) for(unsigned ch=0;ch<2;ch++) {
        float expected=0;
        if(f>=3&&f<7) expected+=(float)pcm[(f-3)*2+ch]/32768.f*ga;
        if(f>=5&&f<9) expected+=(float)pcm[(f-5)*2+ch]/32768.f*gb;
        near(out[f*2+ch],expected,1e-7f);
    }
    CohMixerDiagnostics d=diagnostics(m);CHECK(d.play_started==2&&d.play_completed==2&&d.rendered_frames==12&&d.retained_resources==0);
    a.at_frame=1;CHECK(coh_mixer_play(m,&a)==COH_OK);render(m,out,4);CHECK(diagnostics(m).late_events==1);
    CHECK(coh_mixer_listener(m,(CohVec3){0,0,0},(CohVec3){0,0,0})==COH_INVALID);
    CHECK(coh_mixer_listener(m,(CohVec3){0,0,0},(CohVec3){1,0,0})==COH_OK);
    a.at_frame=16;a.loop=1;a.spatial=1;a.inner_radius=0;a.outer_radius=10;a.position=(CohVec3){5,0,0};a.gain=1;
    CHECK(coh_mixer_bus_gain(m,COH_BUS_FX,.5f)==COH_OK);CHECK(coh_mixer_play(m,&a)==COH_OK);render(m,out,4);
    float l,r;coh_mixer_spatial_gains(&a,(CohVec3){0,0,0},(CohVec3){1,0,0},.5f,&l,&r);
    near(out[0],.25f*l,1e-7f);near(out[1],.5f*r,1e-7f);
    CHECK(coh_mixer_update_emitter(m,1,(CohVec3){-5,0,0},.3f)==COH_OK);render(m,out,4);
    CHECK(out[0]>out[1]*.4f); /* left hemisphere is less attenuated by pan */
    uint64_t frame=diagnostics(m).rendered_frames;
    CHECK(coh_mixer_pause(m,1)==COH_OK);render(m,out,4);CHECK(diagnostics(m).rendered_frames==frame);
    for(unsigned i=0;i<8;i++) CHECK(out[i]==0);
    CHECK(coh_mixer_pause(m,0)==COH_OK);render(m,out,4);CHECK(diagnostics(m).rendered_frames==frame+4);
    coh_mixer_device_error(m);render(m,out,4);d=diagnostics(m);CHECK(d.device_errors==1&&d.device_generation==1&&!d.retained_resources&&!d.active_voices);
    for(unsigned i=0;i<8;i++) CHECK(out[i]==0);
    CHECK(coh_mixer_pause(m,0)==COH_OK);a.at_frame=0;a.loop=0;CHECK(coh_mixer_play(m,&a)==COH_OK);render(m,out,4);CHECK(diagnostics(m).play_completed==4);
    coh_mixer_destroy(m);
}
static void bounds_priority(void) {
    CohMixer *m=make(1,4,1,0);int16_t pcm[4]={32767,32767,32767,32767};
    CohAudioResource h=cached(m,"data/sound/test.ogg",pcm,4,1),hit;
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){"data/sound/test.ogg",1},pcm,4,1,44100,&hit)==COH_OK);
    CHECK(hit.slot==h.slot&&hit.generation==h.generation);
    CohAudioEvent a=event(h,1,.5f);a.loop=1;
    CHECK(coh_mixer_play(m,&a)==COH_OK);
    CohAudioResource newer;
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){"data/sound/next.ogg",1},pcm,4,1,44100,&newer)==COH_LIMIT);
    float out[16];render(m,out,4);
    CohAudioEvent b=event(h,2,.25f);b.loop=1;
    CHECK(coh_mixer_play(m,&b)==COH_OK);render(m,out,4);CHECK(diagnostics(m).play_rejected==1);
    b.priority=1;CHECK(coh_mixer_play(m,&b)==COH_OK);render(m,out,4);CHECK(diagnostics(m).voices_stolen==1);
    CHECK(coh_mixer_play(m,&b)==COH_OK);render(m,out,4);CHECK(diagnostics(m).play_rejected==2);
    b.interrupt=1;CHECK(coh_mixer_play(m,&b)==COH_OK);render(m,out,4);CHECK(diagnostics(m).voices_stolen==2);
    CHECK(coh_mixer_stop_emitter(m,2)==COH_OK);render(m,out,1);CHECK(!diagnostics(m).retained_resources);
    for(unsigned i=0;i<4;i++) { b.at_frame=100+i;CHECK(coh_mixer_play(m,&b)==COH_OK); }
    CHECK(coh_mixer_play(m,&b)==COH_LIMIT);render(m,out,1);CHECK(diagnostics(m).pending_events==4);
    CHECK(coh_mixer_play(m,&b)==COH_OK);render(m,out,1);CHECK(diagnostics(m).pending_rejected==1);
    CHECK(coh_mixer_cancel_all(m)==COH_OK);render(m,out,1);CHECK(!diagnostics(m).retained_resources);
    newer=cached(m,"data/sound/next.ogg",pcm,4,1);CHECK(newer.generation!=h.generation);
    CHECK(coh_mixer_play(m,&a)==COH_NOT_FOUND);
    CHECK(coh_mixer_bus_gain(m,COH_BUS_COUNT,1)==COH_INVALID);CHECK(coh_mixer_bus_gain(m,COH_BUS_FX,NAN)==COH_INVALID);
    a=event(newer,2,INFINITY);CHECK(coh_mixer_play(m,&a)==COH_INVALID);
    CHECK(coh_mixer_render(m,NULL,1)==COH_INVALID);CHECK(coh_mixer_render(m,out,8193)==COH_INVALID);
    CHECK(coh_mixer_cache_decoded(m,(CohAssetId){"bad",0},(CohBytes){(uint8_t*)pcm,sizeof pcm},&h)==COH_INVALID);
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){"bad",0},pcm,UINT32_MAX,2,44100,&h)==COH_LIMIT);
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){"bad",0},pcm,4,1,48000,&h)==COH_UNSUPPORTED);
    char long_path[194];memset(long_path,'x',193);long_path[193]=0;
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){long_path,0},pcm,4,1,44100,&h)==COH_LIMIT);
    CohMixerDiagnostics d=diagnostics(m);CHECK(d.cache_evictions==1&&d.cache_peak_bytes<=200000&&d.queue_rejected==1);
    coh_mixer_destroy(m);
    CohMixerConfig bad={44100,0,0,0,0,0};m=(CohMixer*)1;CHECK(coh_mixer_create(&bad,&m)==COH_INVALID&&m==NULL);
    coh_mixer_destroy(NULL);
}
static void streaming(void) {
    CohMixer *m=make(4,16,1,4);CohAudioResource h[4],extra;
    for(unsigned i=0;i<4;i++) CHECK(coh_mixer_stream_open(m,i&1 ? 2 : 1,44100,&h[i])==COH_OK);
    CHECK(coh_mixer_stream_open(m,1,44100,&extra)==COH_LIMIT);
    int16_t pcm[]={8192,16384,24576,-8192};
    CHECK(coh_mixer_stream_write(m,h[0],pcm,5)==COH_LIMIT);CHECK(coh_mixer_stream_write(m,h[0],pcm,3)==COH_OK);
    CohAudioEvent e=event(h[0],5,1);e.kind=COH_AUDIO_STREAM;
    CHECK(coh_mixer_play(m,&e)==COH_OK);CHECK(coh_mixer_play(m,&e)==COH_STATE);CHECK(coh_mixer_stream_close(m,h[0])==COH_STATE);
    float out[16];render(m,out,5);
    for(unsigned i=0;i<3;i++) { near(out[i*2],(float)pcm[i]/32768.f,0);near(out[i*2+1],out[i*2],0); }
    CHECK(out[6]==0&&out[8]==0);CHECK(diagnostics(m).stream_underrun_frames==2);
    CHECK(coh_mixer_stream_write(m,h[0],pcm+1,3)==COH_OK);CHECK(coh_mixer_stream_finish(m,h[0])==COH_OK);
    CHECK(coh_mixer_stream_write(m,h[0],pcm,1)==COH_STATE);render(m,out,4);
    for(unsigned i=0;i<3;i++) near(out[i*2],(float)pcm[i+1]/32768.f,0);
    CHECK(out[6]==0);CHECK(diagnostics(m).play_completed==1);CHECK(coh_mixer_stream_close(m,h[0])==COH_OK);
    CHECK(coh_mixer_stream_open(m,2,44100,&extra)==COH_OK);CHECK(extra.generation!=h[0].generation);
    CHECK(coh_mixer_stream_write(m,h[0],pcm,1)==COH_INVALID);
    CHECK(coh_mixer_stream_write(m,h[1],pcm,2)==COH_OK);CHECK(coh_mixer_stream_finish(m,h[1])==COH_OK);
    e=event(h[1],6,1);e.kind=COH_AUDIO_STREAM;CHECK(coh_mixer_play(m,&e)==COH_OK);render(m,out,3);
    for(unsigned i=0;i<4;i++) near(out[i],(float)pcm[i]/32768.f,0);
    for(unsigned i=0;i<4;i++) CHECK(coh_mixer_stream_close(m,i==0?extra:h[i])==COH_OK);
    coh_mixer_destroy(m);
}
static void clip_and_lifetime(void) {
    CohMixer *m=make(32,128,2,64);int16_t pcm[]={32767,-32768};CohAudioResource h=cached(m,"data/sound/loop.ogg",pcm,2,1);
    CohAudioEvent e=event(h,0,1);e.loop=1;
    for(unsigned i=0;i<32;i++) { e.emitter=i;CHECK(coh_mixer_play(m,&e)==COH_OK); }
    float out[1024];size_t bytes=diagnostics(m).allocated_bytes;
    struct timespec start,end;clock_gettime(CLOCK_MONOTONIC,&start);
    /* 120 seconds of source-rate audio, no wall-clock sleep. */
    for(unsigned f=0;f<10336;f++) render(m,out,512);
    clock_gettime(CLOCK_MONOTONIC,&end);
    CHECK(out[0]==1&&out[2]==-1);CohMixerDiagnostics d=diagnostics(m);
    CHECK(d.active_voices==32&&d.retained_resources==32&&d.cache_used_bytes==8&&d.allocated_bytes==bytes);
    CHECK(d.clipped_samples==d.rendered_frames*2);
    CHECK(coh_mixer_cancel_all(m)==COH_OK);render(m,out,1);CHECK(!diagnostics(m).retained_resources);
    printf("{\"kind\":\"extended\",\"simulated_seconds\":%.3f,\"host_seconds\":%.6f,\"voices\":32,\"allocated_bytes\":%zu,\"callback_allocations\":0}\n",
           (double)d.rendered_frames/44100.,(double)(end.tv_sec-start.tv_sec)+(double)(end.tv_nsec-start.tv_nsec)/1e9,bytes);
    coh_mixer_destroy(m);
}
typedef struct { CohMixer *m;atomic_int done;uint64_t samples;double sum; } Concurrent;
static void *consumer(void *opaque) {
    Concurrent *x=opaque;float out[128];
    for(;;) {
        realtime=1;assert(coh_mixer_render(x->m,out,64)==COH_OK);realtime=0;
        for(unsigned i=0;i<128;i++) { if(out[i]) x->samples++;x->sum+=out[i]; }
        if(atomic_load_explicit(&x->done,memory_order_acquire)) break;
    }
    return NULL;
}
static void concurrent_stream(void) {
    CohMixer *m=make(1,8,1,256);CohAudioResource h;CHECK(coh_mixer_stream_open(m,1,44100,&h)==COH_OK);
    CohAudioEvent e=event(h,1,1);e.kind=COH_AUDIO_STREAM;CHECK(coh_mixer_play(m,&e)==COH_OK);
    Concurrent x={0};x.m=m;atomic_init(&x.done,0);pthread_t thread;CHECK(!pthread_create(&thread,NULL,consumer,&x));
    int16_t pcm[64];for(unsigned i=0;i<64;i++) pcm[i]=8192;
    for(unsigned n=0;n<2000;n++) { CohStatus s;do { s=coh_mixer_stream_write(m,h,pcm,64); } while(s==COH_LIMIT);CHECK(s==COH_OK); }
    CHECK(coh_mixer_stream_finish(m,h)==COH_OK);
    /* Producer completion must not truncate pending ring samples: wait on the
     * stream close ownership result; diagnostics are read only after join. */
    while(coh_mixer_stream_close(m,h)==COH_STATE) { }
    atomic_store_explicit(&x.done,1,memory_order_release);CHECK(!pthread_join(thread,NULL));
    CHECK(x.samples==2000u*64u*2u);CHECK(x.sum==2000.*64.*2.*.25);CHECK(diagnostics(m).play_completed==1);
    coh_mixer_destroy(m);
}
#ifdef WITH_DECODE
static unsigned char *read_file(const char *p,size_t *size) {
    FILE *f=fopen(p,"rb");CHECK(f!=NULL);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<2000000);rewind(f);
    unsigned char *bytes=malloc((size_t)n);CHECK(bytes!=NULL);CHECK(fread(bytes,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));*size=(size_t)n;return bytes;
}
static void authentic(const char *ogg_path,const char *reference_path) {
    size_t n,rn;unsigned char *ogg=read_file(ogg_path,&n),*reference=read_file(reference_path,&rn);
    CohDecodedAudio decoded={0};CohDecodeProof proof;
    CHECK(coh_decode_ogg(ogg,n,&decoded,&proof)==COH_DECODE_OK);
    CHECK(coh_decode_compare_reference(&decoded,reference,rn,&proof)==COH_DECODE_OK);
    CHECK(proof.maximum_sample_error<=1&&proof.compared_samples==36336);
    CohMixer *m=make(8,32,2,1024);CohAudioResource h;
    CHECK(coh_mixer_cache_decoded(m,(CohAssetId){"data/sound/ogg/player/headset_incoming_02.ogg",1},(CohBytes){decoded.data,decoded.length},&h)==COH_OK);
    CohAudioFixture f;CHECK(coh_audio_parse(decoded.data,decoded.length,&f)==COH_AUDIO_OK);
    for(unsigned i=0;i<3;i++) { CohAudioEvent e=event(h,10+i,.25f);e.bus=(CohAudioBus)i;CHECK(coh_mixer_play(m,&e)==COH_OK); }
    float out[1024];uint32_t position=0;double error=0;
    while(position<f.frames) {
        uint32_t frames=f.frames-position;if(frames>512) frames=512;render(m,out,frames);
        for(unsigned i=0;i<frames*2;i++) {
            size_t p=((size_t)position*2+i)*2;unsigned bits=f.pcm[p]|((unsigned)f.pcm[p+1]<<8);
            int sample=bits>=32768 ? (int)bits-65536 : (int)bits;
            float expected=(float)sample/32768.f*oracle_gain(oracle_db(.25f))*3.f;
            float difference=fabsf(out[i]-expected);if(difference>error) error=difference;near(out[i],expected,1e-7f);
        }
        position+=frames;
    }
    CHECK(diagnostics(m).play_completed==3&&diagnostics(m).retained_resources==0);
    printf("{\"kind\":\"authentic\",\"simultaneous_voices\":3,\"frames\":%u,\"decoder_maximum_sample_error\":%u,\"mixer_oracle_maximum_error\":%.9g}\n",f.frames,proof.maximum_sample_error,error);
    coh_mixer_destroy(m);coh_decode_release(&decoded);free(ogg);free(reference);
}
#endif
int main(int argc,char **argv) {
    oracle_test();scheduling();bounds_priority();streaming();clip_and_lifetime();concurrent_stream();
#ifdef WITH_DECODE
    CHECK(argc==3);authentic(argv[1],argv[2]);
#else
    (void)argc;(void)argv;
#endif
    CHECK(atomic_load(&allocations)==0);
    printf("{\"kind\":\"summary\",\"passed\":true,\"checks\":%u,\"source_comparisons\":%u,\"live_wrapped_allocations_after_teardown\":0}\n",checks,source_checks);return 0;
}
