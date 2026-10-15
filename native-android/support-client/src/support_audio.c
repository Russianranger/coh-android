#define _POSIX_C_SOURCE 200809L
#include "support_audio.h"
#include "../../engine/audio/coh_music.h"
#include "../../engine/audio/coh_mixer_aaudio.h"
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct {AAsset *asset;uint64_t bytes;} AssetSource;
struct SupportAudio {
    AAssetManager *manager;pthread_t worker;pthread_mutex_t mutex;pthread_cond_t wake;
    int joined,cleanup_only,desired,shutdown,position_pending,retry_requested,listener_pending;
    uint64_t route_generation,route_applied;
    CohAudioListenerPose listener;
    CohVec3 position;SupportAudioReport published,owner;
    CohMixer *mixer;CohMixerAAudio *backend;CohMusic *music,*ambient;
    AssetSource music_source,ambient_source;
    int voices_queued,ready,fatal;
};
/* Both sources belong exclusively to the decoder worker. This is a serialized
 * AAsset read/seek pair, so no asset mutex is needed; the mailbox lock is never
 * held over I/O/decode/backend work. The audio callback never accesses assets. */
static size_t asset_read(void *context,uint64_t offset,void *out,size_t bytes) {
    AssetSource *source=context;
    if (!source->asset||offset>source->bytes||bytes>source->bytes-offset||bytes>65536) return 0;
    if (AAsset_seek64(source->asset,(off64_t)offset,SEEK_SET)!=(off64_t)offset) return 0;
    size_t received=0;
    while(received<bytes) {
        int n=AAsset_read(source->asset,(char *)out+received,bytes-received);
        if(n<=0) return 0;
        received+=(size_t)n;
    }
    return received;
}
static CohStatus asset_open(SupportAudio *s,const char *path,AssetSource *source) {
    source->asset=AAssetManager_open(s->manager,path,AASSET_MODE_RANDOM);
    if(!source->asset)return COH_NOT_FOUND;
    off64_t bytes=AAsset_getLength64(source->asset);
    if(bytes<=0||bytes>8*1024*1024){AAsset_close(source->asset);source->asset=NULL;return COH_LIMIT;}
    source->bytes=(uint64_t)bytes;return COH_OK;
}
static int owner_cancel(void *context) {
    SupportAudio *s=context;pthread_mutex_lock(&s->mutex);int stop=s->shutdown;pthread_mutex_unlock(&s->mutex);return stop;
}
static void publish(SupportAudio *s) {
    CohMusicReport music={0},ambient={0};
    if(s->music)(void)coh_music_report(s->music,&music);
    if(s->ambient)(void)coh_music_report(s->ambient,&ambient);
    s->owner.music_loops=music.loops;s->owner.ambient_loops=ambient.loops;
    s->owner.decode_calls=music.decode_calls+ambient.decode_calls;
    s->owner.backpressure=music.backpressure+ambient.backpressure;
    s->owner.source_bytes=music.source_bytes+ambient.source_bytes;
    s->owner.adapter_bytes=music.adapter_bytes+ambient.adapter_bytes;
    pthread_mutex_lock(&s->mutex);
    s->owner.requested_running=s->desired;s->owner.shutdown_requested=s->shutdown;
    s->owner.snapshot_generation++;s->published=s->owner;
    pthread_mutex_unlock(&s->mutex);
}
static CohStatus quiescent_pause(SupportAudio *s,int paused) {
    CohStatus r=coh_mixer_render(s->mixer,NULL,0);if(r)return r;
    r=coh_mixer_pause(s->mixer,paused);if(r)return r;
    return coh_mixer_render(s->mixer,NULL,0);
}
static void checkpoint(SupportAudio *s) {
    if(s->backend||!s->mixer)return;
    CohMixerDiagnostics d={0};
    if(coh_mixer_diagnostics(s->mixer,&d)!=COH_OK)return;
    s->owner.rendered_frames=d.rendered_frames;s->owner.underrun_frames=d.stream_underrun_frames;
    s->owner.underrun_callbacks=d.stream_underrun_callbacks;s->owner.active_voices=d.active_voices;
    s->owner.retained_resources=d.retained_resources;s->owner.mixer_allocated_bytes=d.allocated_bytes;
    s->owner.diagnostics_valid=1;
}
static CohStatus suspend_backend(SupportAudio *s) {
    CohStatus result=COH_OK;
    if(s->backend) {
        (void)coh_mixer_pause(s->mixer,1);
        CohMixerAAudioReport report={0};
        result=coh_mixer_aaudio_close(&s->backend,&report);
        if(s->backend){s->owner.close_pending=1;return result;}
        s->owner.closes++;s->owner.close_pending=0;
        s->owner.xrun_count=report.xrun_count;s->owner.device_error=report.device_error;
        s->owner.callback_calls+=report.callback_calls;
        if(report.maximum_callback_ns>s->owner.maximum_callback_ns)s->owner.maximum_callback_ns=report.maximum_callback_ns;
        s->owner.deadline_overruns+=report.deadline_overruns;
        if(report.device_error)s->voices_queued=0;
    }
    s->owner.running=0;
    if(s->mixer){CohStatus p=quiescent_pause(s,1);if(!result)result=p;checkpoint(s);}
    return result;
}
static CohStatus pump_sources(SupportAudio *s,uint32_t calls) {
    CohStatus a=coh_music_pump(s->music,calls),b=coh_music_pump(s->ambient,calls);
    if(a!=COH_OK&&a!=COH_LIMIT)return a;
    if(b!=COH_OK&&b!=COH_LIMIT)return b;
    return COH_OK;
}
static CohStatus open_sources(SupportAudio *s) {
    CohMusicConfig config={256,1,8*1024*1024,{owner_cancel,s}};
    CohStatus r=coh_music_open(s->mixer,(CohMusicSource){asset_read,&s->music_source,s->music_source.bytes},&config,&s->music);
    if(r)return r;
    r=coh_music_open(s->mixer,(CohMusicSource){asset_read,&s->ambient_source,s->ambient_source.bytes},&config,&s->ambient);
    return r;
}
static CohStatus start_backend(SupportAudio *s,CohVec3 position) {
    if(s->backend)return COH_STATE;
    CohStatus r;
    if(!s->voices_queued) {
        /* Device errors may have flushed voices. Retire and replace stream
         * resources on the joined owner before explicitly restarting music. */
        r=coh_mixer_cancel_all(s->mixer);if(r)return r;
        r=coh_mixer_render(s->mixer,NULL,0);if(r)return r;
        if(s->owner.device_error) {
            r=coh_music_close(&s->music);if(r)return r;
            r=coh_music_close(&s->ambient);if(r)return r;
            r=open_sources(s);if(r)return r;
        }
        int music_full=0,ambient_full=0;
        for(unsigned i=0;i<64&&(!music_full||!ambient_full);i++) {
            if(!music_full){r=coh_music_pump(s->music,32);if(r==COH_LIMIT)music_full=1;else if(r)return r;}
            if(!ambient_full){r=coh_music_pump(s->ambient,32);if(r==COH_LIMIT)ambient_full=1;else if(r)return r;}
        }
        if(!music_full||!ambient_full)return COH_LIMIT;
        checkpoint(s);uint64_t at=s->owner.rendered_frames;
        CohAudioEvent music,ambient;
        r=coh_music_event(s->music,at,1001,COH_BUS_MUSIC,.18f,&music);if(r)return r;
        r=coh_music_event(s->ambient,at,1002,COH_BUS_AMBIENT,.6f,&ambient);if(r)return r;
        ambient.spatial=1;ambient.inner_radius=1;ambient.outer_radius=30;ambient.position=position;
        r=coh_mixer_play(s->mixer,&music);if(r)return r;
        r=coh_mixer_play(s->mixer,&ambient);if(r)return r;
        s->voices_queued=1;
    }
    r=quiescent_pause(s,0);if(r)return r;
    r=coh_mixer_update_emitter(s->mixer,1002,position,.6f);if(r)return r;
    r=coh_mixer_aaudio_open(s->mixer,&s->backend);
    if(!r){s->owner.opens++;s->owner.running=1;s->owner.diagnostics_valid=0;
        if(s->owner.device_error){s->owner.last_device_error=s->owner.device_error;s->owner.recovered_device_errors++;s->owner.device_error=0;}}
    else if(!s->backend)(void)quiescent_pause(s,1);
    return r;
}
static CohStatus initialize(SupportAudio *s) {
    CohMixerConfig config={48000,32,128,4,32768,16384};
    CohStatus r=coh_mixer_create(&config,&s->mixer);if(r)return r;
    r=asset_open(s,"music.ogg",&s->music_source);if(r)return r;
    r=asset_open(s,"ambient.ogg",&s->ambient_source);if(r)return r;
    r=open_sources(s);if(r)return r;
    r=quiescent_pause(s,1);if(r)return r;
    checkpoint(s);s->ready=1;s->owner.initialized=1;return COH_OK;
}
static CohStatus cleanup(SupportAudio *s) {
    CohStatus result=suspend_backend(s);
    if(s->backend)return result?result:COH_STATE;
    if(s->mixer) {
        (void)coh_mixer_cancel_all(s->mixer);(void)coh_mixer_render(s->mixer,NULL,0);
        CohStatus a=coh_music_close(&s->music),b=coh_music_close(&s->ambient);
        if(a||b)return a?a:b;
        checkpoint(s);coh_mixer_destroy(s->mixer);s->mixer=NULL;
    }
    if(s->music_source.asset){AAsset_close(s->music_source.asset);s->music_source.asset=NULL;}
    if(s->ambient_source.asset){AAsset_close(s->ambient_source.asset);s->ambient_source.asset=NULL;}
    s->owner.running=0;return result;
}
static void *owner_worker(void *opaque) {
    SupportAudio *s=opaque;
    if(!s->cleanup_only){s->owner.last_status=initialize(s);s->fatal=s->owner.last_status!=COH_OK;publish(s);}
    for(;;) {
        pthread_mutex_lock(&s->mutex);
        int shutdown=s->shutdown,desired=s->desired,position_pending=s->position_pending,retry=s->retry_requested,listener_pending=s->listener_pending;
        int listener_sent=0;
        CohAudioListenerPose listener=s->listener;s->listener_pending=0;
        uint64_t route=s->route_generation;
        CohVec3 position=s->position;s->position_pending=0;
        s->retry_requested=0;
        pthread_mutex_unlock(&s->mutex);
        if(shutdown)break;
        s->owner.worker_ticks++;
        if(s->ready&&s->owner.close_pending){
            s->owner.last_status=suspend_backend(s);
            if(s->backend)goto owner_cycle_done;
        }
        if(retry&&s->fatal&&s->ready) {
            CohStatus result=suspend_backend(s);
            if(!s->backend) {
                (void)coh_mixer_cancel_all(s->mixer);(void)coh_mixer_render(s->mixer,NULL,0);
                CohStatus a=coh_music_close(&s->music),b=coh_music_close(&s->ambient);
                if(!a&&!b){result=open_sources(s);if(!result){s->voices_queued=0;s->fatal=0;}}
            }
            s->owner.last_status=result;
        }
        if(s->ready&&!s->fatal) {
            CohStatus result=COH_OK;
            int32_t device_error=coh_mixer_aaudio_device_error(s->backend);
            if(s->backend&&(device_error||route!=s->route_applied||!desired)) {
                result=suspend_backend(s);
                if(s->backend){s->owner.last_status=result;goto owner_cycle_done;}
                if(device_error||route!=s->route_applied)s->owner.route_reopens++;
                s->route_applied=route;s->owner.state_changes++;result=COH_OK;
            }
            if(!s->backend)s->route_applied=route;
            if(desired&&!s->backend){result=start_backend(s,position);s->owner.state_changes++;}
            if(result==COH_OK&&desired&&s->backend) {
                if(position_pending)result=coh_mixer_update_emitter(s->mixer,1002,position,.6f);
                if(result==COH_LIMIT){pthread_mutex_lock(&s->mutex);s->position_pending=1;pthread_mutex_unlock(&s->mutex);result=COH_OK;}
                if(!result&&listener_pending){result=coh_audio_listener_apply(s->mixer,&listener);
                    if(!result){s->owner.listener=listener;s->owner.listener_updates++;listener_sent=1;}
                    if(result==COH_LIMIT){pthread_mutex_lock(&s->mutex);s->listener_pending=1;pthread_mutex_unlock(&s->mutex);result=COH_OK;}}
                if(!result)result=pump_sources(s,8);
            }
            s->owner.last_status=result;
            if(result!=COH_OK&&result!=COH_CANCELLED){(void)suspend_backend(s);s->fatal=1;}
        }
owner_cycle_done:
        /* Failed close/initialization/pause must not drop the latest mailbox pose. */
        if(listener_pending&&!listener_sent){pthread_mutex_lock(&s->mutex);s->listener_pending=1;pthread_mutex_unlock(&s->mutex);}
        publish(s);
        struct timespec deadline;
        if(clock_gettime(CLOCK_MONOTONIC,&deadline)==0) {
            deadline.tv_nsec+=16000000;if(deadline.tv_nsec>=1000000000){deadline.tv_nsec-=1000000000;deadline.tv_sec++;}
            pthread_mutex_lock(&s->mutex);
            if(!s->shutdown)(void)pthread_cond_timedwait(&s->wake,&s->mutex,&deadline);
            pthread_mutex_unlock(&s->mutex);
        } else {struct timespec delay={0,16000000};(void)nanosleep(&delay,NULL);}
    }
    s->owner.last_status=cleanup(s);publish(s);return NULL;
}
SupportAudio *support_audio_create(AAssetManager *manager) {
    if(!manager)return NULL;
    SupportAudio *s=calloc(1,sizeof *s);if(!s)return NULL;s->manager=manager;s->position=(CohVec3){8,0,0};
    if(pthread_mutex_init(&s->mutex,NULL)){free(s);return NULL;}
    pthread_condattr_t attr;
    if(pthread_condattr_init(&attr)){pthread_mutex_destroy(&s->mutex);free(s);return NULL;}
    int result=pthread_condattr_setclock(&attr,CLOCK_MONOTONIC);
    if(!result)result=pthread_cond_init(&s->wake,&attr);
    pthread_condattr_destroy(&attr);
    if(result){pthread_mutex_destroy(&s->mutex);free(s);return NULL;}
    if(pthread_create(&s->worker,NULL,owner_worker,s)){pthread_cond_destroy(&s->wake);pthread_mutex_destroy(&s->mutex);free(s);return NULL;}
    return s;
}
static void environment(SupportAudio *s,int running) {
    if(!s)return;
    pthread_mutex_lock(&s->mutex);if(!s->shutdown){s->desired=running;if(running)s->retry_requested=1;}pthread_cond_signal(&s->wake);pthread_mutex_unlock(&s->mutex);
}
void support_audio_resume(SupportAudio *s){environment(s,1);}
void support_audio_pause(SupportAudio *s){environment(s,0);}
void support_audio_emitter(SupportAudio *s,float x,float y,float z) {
    if(!s||!isfinite(x)||!isfinite(y)||!isfinite(z))return;
    pthread_mutex_lock(&s->mutex);s->position=(CohVec3){x,y,z};s->position_pending=1;pthread_cond_signal(&s->wake);pthread_mutex_unlock(&s->mutex);
}
void support_audio_listener(SupportAudio *s,const CohAudioListenerPose *pose) {
    if(!s||!pose)return;
    pthread_mutex_lock(&s->mutex);
    if(memcmp(&s->listener,pose,sizeof *pose)){s->listener=*pose;s->listener_pending=1;pthread_cond_signal(&s->wake);}
    pthread_mutex_unlock(&s->mutex);
}
void support_audio_route(SupportAudio *s,uint64_t generation) {
    if(!s||!generation)return;
    pthread_mutex_lock(&s->mutex);s->route_generation=generation;pthread_cond_signal(&s->wake);pthread_mutex_unlock(&s->mutex);
}
int support_audio_snapshot(SupportAudio *s,SupportAudioReport *out) {
    if(!s||!out)return COH_INVALID;
    pthread_mutex_lock(&s->mutex);*out=s->published;pthread_mutex_unlock(&s->mutex);return COH_OK;
}
int support_audio_destroy(SupportAudio **handle) {
    if(!handle)return COH_INVALID;
    SupportAudio *s=*handle;if(!s)return COH_OK;
    if(s->joined) {
        s->cleanup_only=1;s->joined=0;
        if(pthread_create(&s->worker,NULL,owner_worker,s)){s->joined=1;return COH_IO;}
    } else {
        pthread_mutex_lock(&s->mutex);s->shutdown=1;s->desired=0;pthread_cond_signal(&s->wake);pthread_mutex_unlock(&s->mutex);
    }
    if(pthread_join(s->worker,NULL))return COH_IO;
    s->joined=1;
    if(s->backend||s->mixer||s->music||s->ambient)return COH_IO;
    pthread_cond_destroy(&s->wake);pthread_mutex_destroy(&s->mutex);free(s);*handle=NULL;return COH_OK;
}
