#include "../coh_music.h"
#include <assert.h>
#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static _Thread_local int realtime;
static atomic_long allocations;
static atomic_long peak_allocations;
typedef struct {void *pointer;size_t bytes;} Allocation;
static Allocation allocation_slots[2048];
static size_t live_bytes,peak_bytes;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void *,size_t);void __real_free(void *);
static void allocated(void *p,size_t bytes) {
    long n=atomic_fetch_add(&allocations,1)+1;long old=atomic_load(&peak_allocations);while(n>old&&!atomic_compare_exchange_weak(&peak_allocations,&old,n)){}
    for(unsigned i=0;i<2048;i++)if(!allocation_slots[i].pointer){allocation_slots[i]=(Allocation){p,bytes};live_bytes+=bytes;if(live_bytes>peak_bytes)peak_bytes=live_bytes;return;}
    assert(!"allocation accounting table full");
}
static void released(void *p) {
    atomic_fetch_sub(&allocations,1);
    for(unsigned i=0;i<2048;i++)if(allocation_slots[i].pointer==p){live_bytes-=allocation_slots[i].bytes;allocation_slots[i]=(Allocation){0};return;}
    assert(!"untracked allocation");
}
void *__wrap_malloc(size_t n) { assert(!realtime);void *p=__real_malloc(n);if(p)allocated(p,n);return p; }
void *__wrap_calloc(size_t a,size_t b) { assert(!realtime);void *p=__real_calloc(a,b);if(p)allocated(p,a*b);return p; }
void *__wrap_realloc(void *p,size_t n) {
    assert(!realtime);void *q=__real_realloc(p,n);
    if(q){if(p)released(p);allocated(q,n);}else if(p&&!n)released(p);
    return q;
}
void __wrap_free(void *p) { assert(!realtime);if(p)released(p);__real_free(p); }
static unsigned checks,oracle_samples,negative_cases;
extern float oracle_attenuation(float,float,float,int);
extern float oracle_gain(int);
extern int oracle_db(float);
#define CHECK(c) do { ++checks;if(!(c)){fprintf(stderr,"failed %s:%d %s\n",__FILE__,__LINE__,#c);abort();} }while(0)
static void render(CohMixer *m,float *p,uint32_t n) { realtime=1;CohStatus r=coh_mixer_render(m,p,n);realtime=0;CHECK(r==COH_OK); }
static CohMixer *mixer(uint32_t rate) { CohMixer *m=NULL;CohMixerConfig c={rate,32,128,4,4*8192,4096};CHECK(coh_mixer_create(&c,&m)==COH_OK);return m; }
static uint32_t random_value=0x12345678;
static uint32_t random_next(void) { random_value=random_value*1664525+1013904223;return random_value; }
static int16_t reference_sample(const int16_t *pcm,uint32_t frames,uint32_t ch,uint32_t c,uint64_t i,uint32_t in,uint32_t out) {
    double position=(double)i*in/out;uint64_t a=(uint64_t)position,b=a+1;
    if(a>=frames)a=frames-1;
    if(b>=frames)b=frames-1;
    double v=pcm[a*ch+c]*(1-(position-floor(position)))+pcm[b*ch+c]*(position-floor(position));
    return (int16_t)(v>=0 ? floor(v+.5) : ceil(v-.5));
}
static uint64_t convert(CohResampler *s,const int16_t *input,uint32_t frames,int16_t *output,uint32_t capacity,int fragmented) {
    uint32_t at=0;uint64_t made=0;
    for(unsigned step=0;!s->finished;step++) {
        CHECK(step<100000);
        uint32_t n=frames-at;if(fragmented&&n>1+random_next()%31)n=1+random_next()%31;
        if(n>frames-at)n=frames-at;
        uint32_t outcap=capacity-(uint32_t)made;if(fragmented&&outcap>1+random_next()%23)outcap=1+random_next()%23;
        uint32_t used=0,produced=0;
        CHECK(coh_resample_process(s,input+(size_t)at*s->channels,n,output+(size_t)made*s->channels,outcap,&used,&produced,at+n==frames)==COH_OK);
        at+=used;made+=produced;CHECK(made<capacity);CHECK(used||produced||s->finished);
    }
    CHECK(at==frames);return made;
}
static void resample_tests(void) {
    int16_t pcm[514],out[14000],chunked[14000];
    const uint32_t rates[]={8000,11025,22050,44100,48000,96000,192000};
    for(unsigned k=0;k<514;k++)pcm[k]=(int16_t)(random_next()>>16);
    for(unsigned a=0;a<7;a++)for(unsigned b=0;b<7;b++)for(uint32_t ch=1;ch<=2;ch++) {
        CohResampler s,t;CHECK(coh_resample_init(&s,rates[a],rates[b],ch)==COH_OK);t=s;
        uint64_t n=convert(&s,pcm,257,out,7000,0),m=convert(&t,pcm,257,chunked,7000,1);
        CHECK(n==m&&n==((uint64_t)257*rates[b]+rates[a]-1)/rates[a]);CHECK(!memcmp(out,chunked,(size_t)n*ch*2));
        for(uint64_t i=0;i<n;i++)for(uint32_t c=0;c<ch;c++) {
            int d=(int)out[i*ch+c]-reference_sample(pcm,257,ch,c,i,rates[a],rates[b]);CHECK(abs(d)<=1);oracle_samples++;
        }
    }
    CohResampler s={0};uint32_t used=99,made=99;
    CHECK(coh_resample_init(NULL,44100,48000,2)==COH_INVALID);
    CHECK(coh_resample_init(&s,0,48000,2)==COH_INVALID);
    CHECK(coh_resample_init(&s,44100,48000,3)==COH_INVALID);
    CHECK(coh_resample_init(&s,44100,48000,2)==COH_OK);
    CohResampler old=s;CHECK(coh_resample_process(&s,pcm,257,NULL,0,&used,&made,1)==COH_OK&&used==0&&made==0&&!memcmp(&s,&old,sizeof s));
    CHECK(coh_resample_process(&s,NULL,1,out,1,&used,&made,1)==COH_INVALID&&used==0&&made==0);
    CHECK(coh_resample_process(&s,NULL,0,out,1,&used,&made,1)==COH_OK&&s.finished);
    CHECK(coh_resample_process(&s,pcm,1,out,1,&used,&made,1)==COH_STATE);
    negative_cases+=7;
}
typedef struct { uint8_t *data;size_t size;int broken,cancel; } Memory;
static size_t read_memory(void *context,uint64_t at,void *out,size_t n) {
    Memory *m=context;CHECK(!realtime);
    if(m->broken||at>m->size||n>m->size-at)return 0;
    memcpy(out,m->data+(size_t)at,n);return n;
}
static int cancelled(void *context) { return ((Memory *)context)->cancel; }
static CohMusicConfig config(Memory *m,int loop) { CohMusicConfig c={127,(uint32_t)loop,1024*1024,{cancelled,m}};return c; }
static Memory read_file(const char *path) {
    FILE *f=fopen(path,"rb");CHECK(f!=NULL);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);
    Memory m={0};m.size=(size_t)n;m.data=malloc(m.size);CHECK(m.data&&fread(m.data,1,m.size,f)==m.size);fclose(f);return m;
}
static CohMusicReport report(CohMusic *music) { CohMusicReport r;CHECK(coh_music_report(music,&r)==COH_OK);return r; }
static void stop_close(CohMixer *m,CohMusic **music) {
    CHECK(coh_mixer_cancel_all(m)==COH_OK);render(m,NULL,0);CHECK(coh_music_close(music)==COH_OK&&!*music);CHECK(coh_music_close(music)==COH_OK);coh_mixer_destroy(m);
}
static void streaming_compare(Memory *ogg,Memory *reference,uint32_t rate) {
    CohMixer *mix=mixer(rate);CohMusic *music=NULL;CohMusicConfig c=config(ogg,0);
    CHECK(coh_music_open(mix,(CohMusicSource){read_memory,ogg,ogg->size},&c,&music)==COH_OK);
    CohMusicReport r=report(music);CHECK(r.source_rate==44100&&r.channels==2&&r.source_frames==18168);
    CHECK(coh_music_pump(music,32)==COH_LIMIT);CohAudioEvent event;
    CHECK(coh_music_event(music,0,41,COH_BUS_MUSIC,1,&event)==COH_OK);CHECK(coh_mixer_play(mix,&event)==COH_OK);
    CHECK(coh_music_close(&music)==COH_STATE&&music);
    uint64_t frames=((uint64_t)18168*rate+44100-1)/44100,at=0;float out[512];
    int16_t *pcm=(int16_t *)(reference->data+64);CHECK(reference->size==64+18168*4);
    while(at<frames) {
        CohStatus result=coh_music_pump(music,8);CHECK(result==COH_OK||result==COH_LIMIT);
        uint32_t n=(uint32_t)(frames-at>256?256:frames-at);render(mix,out,n);
        for(uint32_t i=0;i<n;i++)for(uint32_t ch=0;ch<2;ch++) {
            float expected=(float)reference_sample(pcm,18168,2,ch,at+i,44100,rate)/32768.f;
            CHECK(fabsf(out[(size_t)i*2+ch]-expected)<=2.f/32768.f);oracle_samples++;
        }
        at+=n;
    }
    for(unsigned i=0;i<3&&!report(music).eof;i++)CHECK(coh_music_pump(music,8)==COH_OK);
    r=report(music);CHECK(r.eof&&r.decoded_frames==18168&&r.submitted_frames==frames&&r.backpressure>0&&r.maximum_pump_decode_calls<=32);
    render(mix,out,1);CohMixerDiagnostics d;CHECK(coh_mixer_diagnostics(mix,&d)==COH_OK&&d.stream_underrun_frames==0&&d.active_voices==0);
    printf("{\"case\":\"authentic_stream_reference\",\"output_rate\":%u,\"frames\":%llu,\"adapter_bytes\":%zu,\"source_reads\":%llu,\"backpressure\":%llu}\n",rate,(unsigned long long)frames,r.adapter_bytes,(unsigned long long)r.source_reads,(unsigned long long)r.backpressure);
    stop_close(mix,&music);
}
static void streaming_stress(Memory *ogg) {
    CohMixer *mix=mixer(48000);CohMusic *music=NULL;CohMusicConfig c=config(ogg,1);CohAudioEvent event;
    CHECK(coh_music_open(mix,(CohMusicSource){read_memory,ogg,ogg->size},&c,&music)==COH_OK);
    CHECK(coh_music_pump(music,32)==COH_LIMIT);
    CHECK(coh_music_event(music,0,17,COH_BUS_AMBIENT,.5f,&event)==COH_OK);event.spatial=1;event.inner_radius=1;event.outer_radius=20;event.position.x=5;
    CHECK(coh_mixer_play(mix,&event)==COH_OK);float out[512];uint64_t frames=0;long baseline=atomic_load(&allocations),maximum=baseline;size_t initial_bytes=live_bytes,maximum_bytes=initial_bytes;
    for(unsigned i=0;i<22500;i++) {
        CohStatus result=coh_music_pump(music,8);CHECK(result==COH_OK||result==COH_LIMIT);
        if(i%701==0) CHECK(coh_mixer_update_emitter(mix,17,(CohVec3){i&1?5.f:-5.f,0,0},.5f)==COH_OK);
        if(i%503==0) { CHECK(coh_mixer_pause(mix,1)==COH_OK);render(mix,out,128);for(unsigned j=0;j<256;j++)CHECK(out[j]==0);CHECK(coh_mixer_pause(mix,0)==COH_OK); }
        render(mix,out,256);frames+=256;long n=atomic_load(&allocations);if(n>maximum)maximum=n;
        if(live_bytes>maximum_bytes)maximum_bytes=live_bytes;
    }
    CohMusicReport r=report(music);CohMixerDiagnostics d;CHECK(coh_mixer_diagnostics(mix,&d)==COH_OK);
    CHECK(frames==48000*120&&r.loops>290&&d.stream_underrun_frames==0&&maximum<=baseline+16&&maximum_bytes==initial_bytes);
    printf("{\"case\":\"continuous_loop_stress\",\"simulated_seconds\":120,\"frames\":%llu,\"loops\":%llu,\"adapter_bytes\":%zu,\"mixer_bytes\":%zu,\"initial_live_allocations\":%ld,\"maximum_live_allocations\":%ld,\"initial_tracked_bytes\":%zu,\"maximum_tracked_bytes\":%zu,\"underrun_frames\":%llu,\"pause_cycles\":45}\n",(unsigned long long)frames,(unsigned long long)r.loops,r.adapter_bytes,d.allocated_bytes,baseline,maximum,initial_bytes,maximum_bytes,(unsigned long long)d.stream_underrun_frames);
    ogg->cancel=1;CHECK(coh_music_pump(music,8)==COH_CANCELLED&&report(music).cancelled);ogg->cancel=0;stop_close(mix,&music);
}
static void negative(Memory *original) {
    CohMixer *mix=mixer(44100);CohMusic *music=NULL;Memory bad=*original;CohMusicConfig c=config(&bad,0);
    const size_t cuts[]={0,1,26,27,128,4096};
    for(unsigned i=0;i<sizeof cuts/sizeof cuts[0]+2;i++) {
        bad.size=i<sizeof cuts/sizeof cuts[0]?cuts[i]:(i==6?original->size/2:original->size-1);
        CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)!=COH_OK&&!music);negative_cases++;
    }
    bad.size=original->size;bad.data=malloc(bad.size);CHECK(bad.data);memcpy(bad.data,original->data,bad.size);bad.data[bad.size/2]^=64;
    CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_INVALID&&!music);negative_cases++;
    memcpy(bad.data,original->data,bad.size);bad.broken=1;
    CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_IO&&!music);negative_cases++;
    bad.broken=0;bad.cancel=1;CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_CANCELLED&&!music);negative_cases++;
    bad.cancel=0;c.max_source_bytes=1;CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_LIMIT&&!music);negative_cases++;
    c=config(&bad,0);c.chunk_frames=1025;CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_INVALID&&!music);negative_cases++;
    c=config(&bad,0);CHECK(coh_music_open(mix,(CohMusicSource){read_memory,&bad,bad.size},&c,&music)==COH_OK);
    CHECK(coh_music_pump(music,0)==COH_INVALID&&coh_music_pump(music,33)==COH_INVALID);negative_cases+=2;
    bad.broken=1;
    CohStatus result=COH_OK;float out[512];CohAudioEvent e;CHECK(coh_music_event(music,0,1,COH_BUS_MUSIC,1,&e)==COH_OK);CHECK(coh_mixer_play(mix,&e)==COH_OK);
    for(unsigned i=0;i<300&&result!=COH_IO;i++) { result=coh_music_pump(music,32);render(mix,out,256); }
    CHECK(result==COH_IO&&report(music).faulted);negative_cases++;
    stop_close(mix,&music);free(bad.data);
}
static void long_asset_compare(Memory *ogg,Memory *reference,uint32_t rate,const char *label) {
    CohMixer *mix=mixer(rate);CohMusic *music=NULL;CohMusicConfig c=config(ogg,0);
    CHECK(coh_music_open(mix,(CohMusicSource){read_memory,ogg,ogg->size},&c,&music)==COH_OK);
    CohMusicReport r=report(music);CHECK(r.source_frames>(uint64_t)r.source_rate*2);
    CHECK(reference->size==r.source_frames*r.channels*2);
    CHECK(coh_music_pump(music,32)==COH_LIMIT);CohAudioEvent event;
    CHECK(coh_music_event(music,0,201,COH_BUS_MUSIC,1,&event)==COH_OK);CHECK(coh_mixer_play(mix,&event)==COH_OK);
    uint64_t frames=(r.source_frames*rate+r.source_rate-1)/r.source_rate,at=0;float out[512];
    int16_t *pcm=(int16_t *)reference->data;unsigned maximum_error=0;
    while(at<frames) {
        CohStatus result=coh_music_pump(music,8);CHECK(result==COH_OK||result==COH_LIMIT);
        uint32_t n=(uint32_t)(frames-at>256?256:frames-at);render(mix,out,n);
        for(uint32_t i=0;i<n;i++)for(uint32_t ch=0;ch<2;ch++) {
            int expected=reference_sample(pcm,(uint32_t)r.source_frames,r.channels,ch%r.channels,at+i,r.source_rate,rate);
            int error=(int)lroundf(out[(size_t)i*2+ch]*32768)-expected;
            unsigned absolute=(unsigned)abs(error);if(absolute>maximum_error)maximum_error=absolute;
            CHECK(absolute<=3);oracle_samples++;
        }
        at+=n;
    }
    for(unsigned i=0;i<3&&!report(music).eof;i++)CHECK(coh_music_pump(music,8)==COH_OK);
    CohMusicReport final=report(music);CHECK(final.eof&&final.decoded_frames==r.source_frames&&final.submitted_frames==frames);
    render(mix,out,1);CohMixerDiagnostics d;CHECK(coh_mixer_diagnostics(mix,&d)==COH_OK&&d.stream_underrun_frames==0);
    printf("{\"case\":\"authentic_long_stream\",\"asset\":\"%s\",\"source_rate\":%u,\"channels\":%u,\"source_frames\":%llu,\"output_rate\":%u,\"frames\":%llu,\"seconds\":%.6f,\"independent_ffmpeg_max_error_lsb\":%u,\"adapter_bytes\":%zu,\"compressed_bytes\":%zu,\"decoded_pcm_bytes\":%zu}\n",label,r.source_rate,r.channels,(unsigned long long)r.source_frames,rate,(unsigned long long)frames,(double)r.source_frames/r.source_rate,maximum_error,r.adapter_bytes,ogg->size,reference->size);
    stop_close(mix,&music);
}
static void concurrent_authentic(Memory *head,Memory *head_ref,Memory *music_asset,Memory *music_ref,Memory *ambient_asset,Memory *ambient_ref) {
    CohMixer *mix=mixer(48000);Memory *assets[]={head,music_asset,ambient_asset};
    CohMusic *streams[3]={0};CohMusicReport reports[3];CohAudioEvent events[3];
    const float gains[]={.4f,.2f,.3f};const CohAudioBus buses[]={COH_BUS_FX,COH_BUS_MUSIC,COH_BUS_AMBIENT};
    for(unsigned k=0;k<3;k++) {
        CohMusicConfig c=config(assets[k],0);
        CHECK(coh_music_open(mix,(CohMusicSource){read_memory,assets[k],assets[k]->size},&c,&streams[k])==COH_OK);
        reports[k]=report(streams[k]);CHECK(coh_music_pump(streams[k],32)==COH_LIMIT);
        CHECK(coh_music_event(streams[k],0,300+k,buses[k],gains[k],&events[k])==COH_OK);
        if(k==2){events[k].spatial=1;events[k].inner_radius=1;events[k].outer_radius=20;events[k].position.x=5;}
        CHECK(coh_mixer_play(mix,&events[k])==COH_OK);
    }
    render(mix,NULL,0);CohMixerDiagnostics d;
    float out[512];unsigned maximum=0;
    for(uint32_t at=0;at<6144;at+=256) {
        for(unsigned k=0;k<3;k++){CohStatus r=coh_music_pump(streams[k],8);CHECK(r==COH_OK||r==COH_LIMIT);}
        if(at==3072)CHECK(coh_mixer_update_emitter(mix,302,(CohVec3){-5,0,0},.3f)==COH_OK);
        render(mix,out,256);
        for(uint32_t i=0;i<256;i++)for(uint32_t ch=0;ch<2;ch++) {
            float h=reference_sample((int16_t *)(head_ref->data+64),18168,2,ch,at+i,44100,48000)/32768.f;
            float music=reference_sample((int16_t *)music_ref->data,(uint32_t)reports[1].source_frames,reports[1].channels,ch%reports[1].channels,at+i,reports[1].source_rate,48000)/32768.f;
            float ambient=reference_sample((int16_t *)ambient_ref->data,(uint32_t)reports[2].source_frames,reports[2].channels,ch%reports[2].channels,at+i,reports[2].source_rate,48000)/32768.f;
            float spatial=oracle_gain(oracle_db(.3f*oracle_attenuation(1,20,5,0)));
            if((at<3072&&ch==0)||(at>=3072&&ch==1))spatial*=oracle_gain(-2000);
            float expected=h*oracle_gain(oracle_db(.4f))+music*oracle_gain(oracle_db(.2f))+ambient*spatial;
            unsigned error=(unsigned)lroundf(fabsf(out[(size_t)i*2+ch]-expected)*32768.f);
            if(error>maximum)maximum=error;
            CHECK(error<=3);oracle_samples++;
        }
    }
    CHECK(coh_mixer_diagnostics(mix,&d)==COH_OK&&d.active_voices==3&&d.stream_underrun_frames==0);
    CHECK(coh_mixer_cancel_all(mix)==COH_OK);render(mix,NULL,0);
    for(unsigned k=0;k<3;k++)CHECK(coh_music_close(&streams[k])==COH_OK);
    coh_mixer_destroy(mix);
    printf("{\"case\":\"three_authentic_concurrent_sources\",\"voices\":3,\"frames\":6144,\"source_gain_oracle\":true,\"positional_emitter_reversal\":true,\"max_error_lsb\":%u,\"underrun_frames\":0}\n",maximum);
}
int main(int argc,char **argv) {
    CHECK(argc==3||argc==7);resample_tests();Memory ogg=read_file(argv[1]),reference=read_file(argv[2]);
    streaming_compare(&ogg,&reference,44100);streaming_compare(&ogg,&reference,48000);streaming_stress(&ogg);negative(&ogg);
    if(argc==7) {
        Memory music=read_file(argv[3]),music_ref=read_file(argv[4]);
        Memory ambient=read_file(argv[5]),ambient_ref=read_file(argv[6]);
        long_asset_compare(&music,&music_ref,48000,"Atlas Plaza music");
        long_asset_compare(&ambient,&ambient_ref,48000,"City steam ambient");
        concurrent_authentic(&ogg,&reference,&music,&music_ref,&ambient,&ambient_ref);
        free(music.data);free(music_ref.data);free(ambient.data);free(ambient_ref.data);
    }
    free(ogg.data);free(reference.data);CHECK(atomic_load(&allocations)==0&&live_bytes==0);
    printf("{\"case\":\"summary\",\"checks\":%u,\"oracle_samples\":%u,\"negative_cases\":%u,\"live_allocations_after_teardown\":%ld,\"tracked_bytes_after_teardown\":%zu,\"peak_tracked_bytes\":%zu,\"peak_live_allocations\":%ld,\"callback_allocations\":0}\n",checks,oracle_samples,negative_cases,atomic_load(&allocations),live_bytes,peak_bytes,atomic_load(&peak_allocations));return 0;
}
