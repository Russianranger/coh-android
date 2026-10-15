#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "native-android/support-client/src/support_audio.c"

/* Controlled dependencies: this exercises the real mailbox/owner implementation,
 * never pretends to run Android or an actual realtime callback. */
struct AAssetManager { int present; };
struct AAsset { int live; size_t cursor; };
struct CohMixer { int live; };
struct CohMixerAAudio { int live; };
struct CohMusic { int live; uint64_t calls; };
static _Atomic unsigned assets, mixers, streams, sinks, opens, closes;
static _Atomic int block_close, device_error, fail_ambient;
static pthread_t backend_owner;
static unsigned checks;
#define CHECK(x) do { assert(x); checks++; } while(0)
static void owner_check(void) { assert(pthread_equal(pthread_self(),backend_owner)); }
AAsset *AAssetManager_open(AAssetManager *m,const char *path,int mode) {
 (void)mode;assert(m);if(atomic_load(&fail_ambient)&&!strcmp(path,"ambient.ogg"))return NULL;
 AAsset *a=calloc(1,sizeof *a);assert(a);a->live=1;atomic_fetch_add(&assets,1);return a;
}
off64_t AAsset_getLength64(AAsset *a) { assert(a&&a->live);return 32; }
off64_t AAsset_seek64(AAsset *a,off64_t at,int whence) { assert(a&&a->live&&whence==SEEK_SET);a->cursor=(size_t)at;return at; }
int AAsset_read(AAsset *a,void *out,size_t count) { assert(a&&a->live);memset(out,1,count);a->cursor+=count;return (int)count; }
void AAsset_close(AAsset *a) { assert(a&&a->live);a->live=0;atomic_fetch_sub(&assets,1);free(a); }
CohStatus coh_mixer_create(const CohMixerConfig *c,CohMixer **out) { assert(c&&out);backend_owner=pthread_self();*out=calloc(1,sizeof **out);assert(*out);(*out)->live=1;atomic_fetch_add(&mixers,1);return COH_OK; }
void coh_mixer_destroy(CohMixer *m) { owner_check();assert(m&&m->live&&!atomic_load(&sinks)&&!atomic_load(&streams));m->live=0;atomic_fetch_sub(&mixers,1);free(m); }
CohStatus coh_mixer_render(CohMixer *m,float *out,uint32_t frames) { owner_check();assert(m&&m->live&&!out&&!frames&&!atomic_load(&sinks));return COH_OK; }
CohStatus coh_mixer_pause(CohMixer *m,int pause) { owner_check();assert(m&&m->live&&(pause==0||pause==1));return COH_OK; }
CohStatus coh_mixer_cancel_all(CohMixer *m) { owner_check();assert(m&&m->live&&!atomic_load(&sinks));return COH_OK; }
CohStatus coh_mixer_diagnostics(const CohMixer *m,CohMixerDiagnostics *d) { owner_check();assert(m&&m->live&&!atomic_load(&sinks));memset(d,0,sizeof *d);d->rendered_frames=64;d->allocated_bytes=sizeof *m;return COH_OK; }
CohStatus coh_mixer_play(CohMixer *m,const CohAudioEvent *event) { owner_check();assert(m&&m->live&&event);return COH_OK; }
CohStatus coh_mixer_update_emitter(CohMixer *m,uint32_t id,CohVec3 position,float gain) { owner_check();assert(m&&m->live&&id==1002&&gain>0&&isfinite(position.x));return COH_OK; }
CohStatus coh_audio_listener_apply(CohMixer *m,const CohAudioListenerPose *p) { owner_check();assert(m&&m->live&&p);return COH_OK; }
CohStatus coh_music_open(CohMixer *m,CohMusicSource source,const CohMusicConfig *config,CohMusic **out) { owner_check();assert(m&&m->live&&config&&out&&source.bytes==32);unsigned char b=0;assert(source.read_at(source.context,0,&b,1)==1&&b==1);*out=calloc(1,sizeof **out);assert(*out);(*out)->live=1;atomic_fetch_add(&streams,1);return COH_OK; }
CohStatus coh_music_pump(CohMusic *music,uint32_t calls) { owner_check();assert(music&&music->live&&calls);music->calls++;return COH_LIMIT; }
CohStatus coh_music_event(const CohMusic *music,uint64_t at,uint32_t id,CohAudioBus bus,float gain,CohAudioEvent *event) { owner_check();assert(music&&music->live);memset(event,0,sizeof *event);event->at_frame=at;event->emitter=id;event->bus=bus;event->gain=gain;return COH_OK; }
CohStatus coh_music_report(const CohMusic *music,CohMusicReport *out) { owner_check();assert(music&&music->live);memset(out,0,sizeof *out);out->decode_calls=music->calls;return COH_OK; }
CohStatus coh_music_close(CohMusic **music) { owner_check();if(!*music)return COH_OK;assert(!atomic_load(&sinks)&&(*music)->live);(*music)->live=0;atomic_fetch_sub(&streams,1);free(*music);*music=NULL;return COH_OK; }
CohStatus coh_mixer_aaudio_open(CohMixer *m,CohMixerAAudio **out) { owner_check();assert(m&&m->live&&!atomic_load(&sinks)&&!*out);*out=calloc(1,sizeof **out);assert(*out);(*out)->live=1;atomic_fetch_add(&sinks,1);atomic_fetch_add(&opens,1);return COH_OK; }
int32_t coh_mixer_aaudio_device_error(const CohMixerAAudio *sink) { owner_check();return sink?atomic_load(&device_error):0; }
CohStatus coh_mixer_aaudio_close(CohMixerAAudio **sink,CohMixerAAudioReport *out) { backend_owner=pthread_self();if(!*sink)return COH_OK;assert((*sink)->live&&atomic_load(&sinks)==1);if(atomic_load(&block_close))return COH_IO;memset(out,0,sizeof *out);out->device_error=atomic_exchange(&device_error,0);out->callback_calls=100;out->maximum_callback_ns=1000;(*sink)->live=0;free(*sink);*sink=NULL;atomic_fetch_sub(&sinks,1);atomic_fetch_add(&closes,1);return COH_OK; }
static SupportAudioReport wait_for(SupportAudio *audio,int kind,uint64_t minimum) {
 struct timespec delay={0,1000000};SupportAudioReport report={0};
 for(unsigned i=0;i<2500;i++) { CHECK(support_audio_snapshot(audio,&report)==COH_OK);
  int ready=kind==0?report.initialized:kind==1?report.running&&report.opens>=minimum:
   kind==2?report.close_pending:kind==3?!report.running&&!report.close_pending&&report.closes>=minimum:
   kind==4?report.listener_updates>=minimum:kind==5?report.route_reopens>=minimum:
   kind==6?report.recovered_device_errors>=minimum:report.last_status==COH_NOT_FOUND;
  if(ready)return report;(void)nanosleep(&delay,NULL);
 }
 fprintf(stderr,"timeout kind=%d running=%d pending=%d status=%d opens=%llu closes=%llu\n",kind,report.running,report.close_pending,report.last_status,(unsigned long long)report.opens,(unsigned long long)report.closes);abort();
}
int main(void) {
 struct AAssetManager manager={1};SupportAudio *audio=support_audio_create(&manager);CHECK(audio);
 SupportAudioReport report=wait_for(audio,0,0);CHECK(!report.running&&atomic_load(&assets)==2&&atomic_load(&streams)==2&&!atomic_load(&sinks));
 support_audio_resume(audio);report=wait_for(audio,1,1);CHECK(report.diagnostics_valid==0&&atomic_load(&sinks)==1);
 CohAudioListenerPose pose={{3,4,5},{1,0,0}};support_audio_listener(audio,&pose);report=wait_for(audio,4,1);CHECK(report.listener.position.x==3);
 support_audio_route(audio,1);report=wait_for(audio,5,1);report=wait_for(audio,1,2);CHECK(atomic_load(&sinks)==1);
 atomic_store(&device_error,-899);report=wait_for(audio,6,1);CHECK(report.last_device_error==-899&&report.device_error==0);CHECK(atomic_load(&streams)==2);
 atomic_store(&block_close,1);support_audio_route(audio,2);report=wait_for(audio,2,0);uint64_t route_opens=report.opens;
 CHECK(report.requested_running&&atomic_load(&sinks)==1&&atomic_load(&assets)==2);
 atomic_store(&block_close,0);report=wait_for(audio,1,route_opens+1);CHECK(atomic_load(&sinks)==1);
 atomic_store(&block_close,1);support_audio_pause(audio);report=wait_for(audio,2,0);CHECK(atomic_load(&assets)==2&&atomic_load(&streams)==2&&atomic_load(&mixers)==1&&atomic_load(&sinks)==1);
 uint64_t previous_closes=report.closes;atomic_store(&block_close,0);report=wait_for(audio,3,previous_closes+1);CHECK(report.diagnostics_valid==1&&!atomic_load(&sinks));
 support_audio_resume(audio);report=wait_for(audio,1,report.opens+1);CHECK(atomic_load(&sinks)==1);
 atomic_store(&block_close,1);SupportAudio *saved=audio;CHECK(support_audio_destroy(&audio)==COH_IO);CHECK(audio==saved&&atomic_load(&assets)==2&&atomic_load(&streams)==2&&atomic_load(&mixers)==1&&atomic_load(&sinks)==1);
 atomic_store(&block_close,0);CHECK(support_audio_destroy(&audio)==COH_OK&&!audio);CHECK(!atomic_load(&assets)&&!atomic_load(&streams)&&!atomic_load(&mixers)&&!atomic_load(&sinks));
 atomic_store(&fail_ambient,1);audio=support_audio_create(&manager);CHECK(audio);(void)wait_for(audio,7,0);CHECK(support_audio_destroy(&audio)==COH_OK&&!audio);CHECK(!atomic_load(&assets)&&!atomic_load(&streams)&&!atomic_load(&mixers)&&!atomic_load(&sinks));
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":9,\"backend_opens\":%u,\"backend_closes\":%u,\"outstanding_assets\":%u,\"outstanding_mixers\":%u,\"outstanding_streams\":%u,\"outstanding_sinks\":%u,\"android_execution\":false}\n",checks,atomic_load(&opens),atomic_load(&closes),atomic_load(&assets),atomic_load(&mixers),atomic_load(&streams),atomic_load(&sinks));return 0;
}
