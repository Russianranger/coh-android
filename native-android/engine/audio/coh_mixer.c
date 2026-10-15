#include "coh_mixer.h"
#include "../../audio/coh_audio.h"
#include <math.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char path[192]; uint32_t asset_generation, generation, frames, channels;
    uint64_t used; float *pcm; atomic_uint refs;
} Cache;
typedef struct {
    uint32_t generation, channels, open; float *pcm;
    atomic_uint refs, write, read, eof;
} Stream;
typedef struct { CohAudioEvent event; uint32_t position; int active; } Voice;
typedef enum { PLAY, STOP, CANCEL, UPDATE, LISTENER, BUS, PAUSE } Kind;
typedef struct {
    Kind kind; CohAudioEvent event; CohVec3 position, right;
    uint32_t emitter, bus; float gain; int paused;
} Command;
struct CohMixer {
    CohMixerConfig config;
    Cache cache[COH_MIXER_MAX_CACHE]; Stream streams[COH_MIXER_MAX_STREAMS];
    Voice voices[COH_MIXER_MAX_VOICES];
    Command queue[COH_MIXER_MAX_EVENTS]; CohAudioEvent pending[COH_MIXER_MAX_EVENTS];
    atomic_uint write, read, error;
    uint32_t pending_count; int paused;
    uint64_t frame, lru; CohVec3 listener, right; float bus[COH_BUS_COUNT];
    float *cache_storage, *stream_storage;
    CohMixerDiagnostics diagnostic;
};

static int finite3(CohVec3 p) { return isfinite(p.x)&&isfinite(p.y)&&isfinite(p.z); }
static float clamp(float x,float lo,float hi) { return fminf(hi,fmaxf(lo,x)); }
float coh_mixer_attenuation(float inner,float outer,float distance,int ignore) {
    if (!isfinite(inner)||!isfinite(outer)||!isfinite(distance)||inner<0||outer<inner||outer<=0||distance<0) return 0;
    if (ignore) inner=0;
    if (distance>=outer) return 0;
    if (distance<=inner) return 1;
    return 1.f-((distance-inner)/(outer-inner));
}
void coh_mixer_spatial_gains(const CohAudioEvent *e,CohVec3 listener,CohVec3 right,float bus,float *left,float *rg) {
    if (!left||!rg) return;
    *left=*rg=0;
    if (!e||!finite3(e->position)||!finite3(listener)||!finite3(right)||!isfinite(e->gain)||!isfinite(bus)) return;
    float attenuation=1,pan=0;
    if (e->spatial) {
        float x=e->position.x-listener.x,y=e->position.y-listener.y,z=e->position.z-listener.z;
        float distance=sqrtf(x*x+y*y+z*z);
        attenuation=coh_mixer_attenuation(e->inner_radius,e->outer_radius,distance,e->ignore_ramp);
        /* sphereGroupGetVolume divides the weighted pan by total volume.
         * For one sphere that leaves the normalized head-right dot product. */
        if (distance>0 && isfinite(distance)&&attenuation*e->gain>0) pan=clamp((x*right.x+y*right.y+z*right.z)/distance,-1,1);
    }
    int db=0;
    if (coh_audio_ratio_to_db(clamp(attenuation*e->gain*bus,0,1),&db)) return;
    float g=coh_audio_db_to_ratio(db);
    int pan_db=(int)clamp(pan*2000.f,-10000,10000);
    *left=g*coh_audio_db_to_ratio(pan_db>0 ? -pan_db : 0);
    *rg=g*coh_audio_db_to_ratio(pan_db<0 ? pan_db : 0);
}

CohStatus coh_mixer_create(const CohMixerConfig *c,CohMixer **out) {
    if (!out) return COH_INVALID;
    *out=NULL;
    if (!c||c->sample_rate<8000||c->sample_rate>192000||!c->voices||c->voices>COH_MIXER_MAX_VOICES||
        !c->event_capacity||(c->event_capacity&(c->event_capacity-1))||c->event_capacity>COH_MIXER_MAX_EVENTS||!c->cache_entries||c->cache_entries>COH_MIXER_MAX_CACHE||
        c->cache_bytes<8*c->cache_entries||c->cache_bytes>64u*1024u*1024u||c->stream_frames>65536||
        (c->stream_frames&&(c->stream_frames&(c->stream_frames-1)))) return COH_INVALID;
    CohMixer *m=calloc(1,sizeof *m);
    if (!m) return COH_LIMIT;
    m->config=*c;
    size_t per=c->cache_bytes/c->cache_entries/sizeof(float);
    m->cache_storage=calloc(per*c->cache_entries,sizeof(float));
    size_t stream_samples=(size_t)c->stream_frames*2*COH_MIXER_MAX_STREAMS;
    if (stream_samples) m->stream_storage=calloc(stream_samples,sizeof(float));
    if (!m->cache_storage||(stream_samples&&!m->stream_storage)) { coh_mixer_destroy(m);return COH_LIMIT; }
    atomic_init(&m->write,0);atomic_init(&m->read,0);atomic_init(&m->error,0);
    /* Atomics must be lock-free on this target to satisfy the callback contract. */
    if (!atomic_is_lock_free(&m->write)||!atomic_is_lock_free(&m->error)) { coh_mixer_destroy(m);return COH_UNSUPPORTED; }
    for (uint32_t i=0;i<c->cache_entries;i++) { m->cache[i].pcm=m->cache_storage+i*per;atomic_init(&m->cache[i].refs,0); }
    for (uint32_t i=0;i<COH_MIXER_MAX_STREAMS;i++) {
        Stream *s=&m->streams[i];s->pcm=m->stream_storage ? m->stream_storage+(size_t)i*c->stream_frames*2 : NULL;
        atomic_init(&s->refs,0);atomic_init(&s->write,0);atomic_init(&s->read,0);atomic_init(&s->eof,0);
    }
    m->right.x=1;
    for (unsigned i=0;i<COH_BUS_COUNT;i++) m->bus[i]=1;
    m->diagnostic.allocated_bytes=sizeof *m+per*c->cache_entries*sizeof(float)+stream_samples*sizeof(float);
    *out=m;return COH_OK;
}
void coh_mixer_destroy(CohMixer *m) { if (m) { free(m->cache_storage);free(m->stream_storage);free(m); } }
uint32_t coh_mixer_sample_rate(const CohMixer *m) { return m ? m->config.sample_rate : 0; }

static CohStatus cache_prepare(CohMixer *m,CohAssetId id,uint32_t frames,uint32_t channels,uint32_t rate,Cache **out,CohAudioResource *handle) {
    if (!m||!id.path||!id.path[0]||!handle||!frames||(channels!=1&&channels!=2)) return COH_INVALID;
    size_t length=0;while(length<192&&id.path[length]) length++;
    if (length==192) return COH_LIMIT;
    if (rate!=m->config.sample_rate) return COH_UNSUPPORTED;
    size_t capacity=m->config.cache_bytes/m->config.cache_entries/sizeof(float);
    if ((uint64_t)frames*channels>capacity) return COH_LIMIT;
    for (uint32_t i=0;i<m->config.cache_entries;i++) {
        Cache *s=&m->cache[i];
        if (s->generation&&s->asset_generation==id.generation&&!strcmp(s->path,id.path)) {
            s->used=++m->lru;*handle=(CohAudioResource){i,s->generation};*out=NULL;m->diagnostic.cache_hits++;return COH_OK;
        }
    }
    m->diagnostic.cache_misses++;
    Cache *victim=NULL;uint32_t index=0;
    for (uint32_t i=0;i<m->config.cache_entries;i++) {
        Cache *s=&m->cache[i];
        if (!atomic_load_explicit(&s->refs,memory_order_acquire)&&(!victim||s->used<victim->used)) { victim=s;index=i; }
    }
    if (!victim) return COH_LIMIT;
    if (victim->generation) { m->diagnostic.cache_evictions++;m->diagnostic.cache_used_bytes-=(size_t)victim->frames*victim->channels*sizeof(float); }
    uint32_t generation=victim->generation+1;if (!generation) generation=1;
    victim->generation=generation;victim->asset_generation=id.generation;victim->frames=frames;victim->channels=channels;
    memcpy(victim->path,id.path,length+1);victim->used=++m->lru;
    m->diagnostic.cache_used_bytes+=(size_t)frames*channels*sizeof(float);
    if (m->diagnostic.cache_used_bytes>m->diagnostic.cache_peak_bytes) m->diagnostic.cache_peak_bytes=m->diagnostic.cache_used_bytes;
    *out=victim;*handle=(CohAudioResource){index,generation};return COH_OK;
}
CohStatus coh_mixer_cache_pcm16(CohMixer *m,CohAssetId id,const int16_t *pcm,uint32_t frames,uint32_t channels,uint32_t rate,CohAudioResource *out) {
    if (!pcm) return COH_INVALID;
    Cache *s=NULL;CohStatus status=cache_prepare(m,id,frames,channels,rate,&s,out);
    if (status||!s) return status;
    for (size_t i=0;i<(size_t)frames*channels;i++) s->pcm[i]=(float)pcm[i]/32768.f;
    return COH_OK;
}
CohStatus coh_mixer_cache_decoded(CohMixer *m,CohAssetId id,CohBytes b,CohAudioResource *out) {
    CohAudioFixture f;
    if (coh_audio_parse(b.data,b.size,&f)) return COH_INVALID;
    Cache *s=NULL;CohStatus status=cache_prepare(m,id,f.frames,f.channels,f.sample_rate,&s,out);
    if (status||!s) return status;
    for (size_t i=0;i<(size_t)f.frames*f.channels;i++) {
        unsigned v=(unsigned)f.pcm[i*2]|((unsigned)f.pcm[i*2+1]<<8);
        s->pcm[i]=(float)(v>=32768 ? (int)v-65536 : (int)v)/32768.f;
    }
    return COH_OK;
}
static Stream *stream_find(CohMixer *m,CohAudioResource h) {
    return m&&h.slot<COH_MIXER_MAX_STREAMS&&h.generation&&m->streams[h.slot].open&&m->streams[h.slot].generation==h.generation ? &m->streams[h.slot] : NULL;
}
CohStatus coh_mixer_stream_open(CohMixer *m,uint32_t channels,uint32_t rate,CohAudioResource *out) {
    if (!m||!out||(channels!=1&&channels!=2)) return COH_INVALID;
    if (rate!=m->config.sample_rate||!m->config.stream_frames) return COH_UNSUPPORTED;
    for (uint32_t i=0;i<COH_MIXER_MAX_STREAMS;i++) {
        Stream *s=&m->streams[i];
        if (s->open||atomic_load_explicit(&s->refs,memory_order_acquire)) continue;
        s->generation++;if (!s->generation) s->generation=1;s->channels=channels;s->open=1;
        atomic_store(&s->write,0);atomic_store(&s->read,0);atomic_store(&s->eof,0);
        *out=(CohAudioResource){i,s->generation};return COH_OK;
    }
    return COH_LIMIT;
}
CohStatus coh_mixer_stream_write(CohMixer *m,CohAudioResource h,const int16_t *pcm,uint32_t frames) {
    Stream *s=stream_find(m,h);if (!s||(!pcm&&frames)) return COH_INVALID;
    if (atomic_load_explicit(&s->eof,memory_order_acquire)) return COH_STATE;
    unsigned w=atomic_load_explicit(&s->write,memory_order_relaxed),r=atomic_load_explicit(&s->read,memory_order_acquire);
    if (frames>m->config.stream_frames-(w-r)) return COH_LIMIT;
    for (uint32_t i=0;i<frames;i++) {
        size_t target=(size_t)((w+i)%m->config.stream_frames)*2;
        s->pcm[target]=(float)pcm[(size_t)i*s->channels]/32768.f;
        s->pcm[target+1]=(float)pcm[(size_t)i*s->channels+s->channels-1]/32768.f;
    }
    atomic_store_explicit(&s->write,w+frames,memory_order_release);return COH_OK;
}
CohStatus coh_mixer_stream_finish(CohMixer *m,CohAudioResource h) {
    Stream *s=stream_find(m,h);if (!s) return COH_INVALID;
    atomic_store_explicit(&s->eof,1,memory_order_release);return COH_OK;
}
CohStatus coh_mixer_stream_close(CohMixer *m,CohAudioResource h) {
    Stream *s=stream_find(m,h);if (!s) return COH_INVALID;
    if (atomic_load_explicit(&s->refs,memory_order_acquire)) return COH_STATE;
    s->open=0;return COH_OK;
}
static atomic_uint *resource_refs(CohMixer *m,const CohAudioEvent *e) {
    CohAudioResource h=e->resource;
    if (e->kind==COH_AUDIO_CACHED) return h.slot<m->config.cache_entries&&h.generation&&m->cache[h.slot].generation==h.generation ? &m->cache[h.slot].refs : NULL;
    if (e->kind==COH_AUDIO_STREAM) { Stream *s=stream_find(m,h);return s ? &s->refs : NULL; }
    return NULL;
}
static void release(CohMixer *m,const CohAudioEvent *e) {
    /* Ownership prevents resource generation reuse until this release. */
    atomic_uint *refs=e->kind==COH_AUDIO_CACHED ? &m->cache[e->resource.slot].refs : &m->streams[e->resource.slot].refs;
    atomic_fetch_sub_explicit(refs,1,memory_order_release);
}
static CohStatus enqueue(CohMixer *m,const Command *command) {
    if (!m) return COH_INVALID;
    unsigned w=atomic_load_explicit(&m->write,memory_order_relaxed),r=atomic_load_explicit(&m->read,memory_order_acquire);
    if (w-r>=m->config.event_capacity) { m->diagnostic.queue_rejected++;return COH_LIMIT; }
    m->queue[w%m->config.event_capacity]=*command;
    atomic_store_explicit(&m->write,w+1,memory_order_release);return COH_OK;
}
CohStatus coh_mixer_play(CohMixer *m,const CohAudioEvent *e) {
    if (!m||!e||e->bus>=COH_BUS_COUNT||e->bus<0||!isfinite(e->gain)||e->gain<0||e->gain>1||!finite3(e->position)||
        (e->spatial&&(!isfinite(e->inner_radius)||!isfinite(e->outer_radius)||e->inner_radius<0||e->outer_radius<e->inner_radius||e->outer_radius<=0))||
        (e->kind==COH_AUDIO_STREAM&&e->loop)) return COH_INVALID;
    atomic_uint *refs=resource_refs(m,e);if (!refs) return COH_NOT_FOUND;
    if (e->kind==COH_AUDIO_STREAM&&atomic_load_explicit(refs,memory_order_acquire)) return COH_STATE;
    atomic_fetch_add_explicit(refs,1,memory_order_relaxed);
    Command c={0};c.kind=PLAY;c.event=*e;CohStatus status=enqueue(m,&c);
    if (status) release(m,e);
    return status;
}
CohStatus coh_mixer_stop_emitter(CohMixer *m,uint32_t emitter) { Command c={0};c.kind=STOP;c.emitter=emitter;return enqueue(m,&c); }
CohStatus coh_mixer_cancel_all(CohMixer *m) { Command c={0};c.kind=CANCEL;return enqueue(m,&c); }
CohStatus coh_mixer_update_emitter(CohMixer *m,uint32_t emitter,CohVec3 pos,float gain) {
    if (!finite3(pos)||!isfinite(gain)||gain<0||gain>1) return COH_INVALID;
    Command c={0};c.kind=UPDATE;c.emitter=emitter;c.position=pos;c.gain=gain;return enqueue(m,&c);
}
CohStatus coh_mixer_listener(CohMixer *m,CohVec3 pos,CohVec3 right) {
    if (!finite3(pos)||!finite3(right)) return COH_INVALID;
    float n=sqrtf(right.x*right.x+right.y*right.y+right.z*right.z);
    if (!isfinite(n)||n<.999f||n>1.001f) return COH_INVALID;
    Command c={0};c.kind=LISTENER;c.position=pos;c.right=right;return enqueue(m,&c);
}
CohStatus coh_mixer_bus_gain(CohMixer *m,CohAudioBus bus,float gain) {
    if (bus<0||bus>=COH_BUS_COUNT||!isfinite(gain)||gain<0||gain>1) return COH_INVALID;
    Command c={0};c.kind=BUS;c.bus=(uint32_t)bus;c.gain=gain;return enqueue(m,&c);
}
CohStatus coh_mixer_pause(CohMixer *m,int paused) { Command c={0};c.kind=PAUSE;c.paused=paused!=0;return enqueue(m,&c); }
void coh_mixer_device_error(CohMixer *m) { if (m) atomic_fetch_add_explicit(&m->error,1,memory_order_relaxed); }
static void stop(CohMixer *m,uint32_t emitter,int all) {
    for (uint32_t i=0;i<m->config.voices;i++) if (m->voices[i].active&&(all||m->voices[i].event.emitter==emitter)) {
        release(m,&m->voices[i].event);m->voices[i].active=0;m->diagnostic.cancelled++;
    }
    for (uint32_t i=0;i<m->pending_count;) {
        if (all||m->pending[i].emitter==emitter) {
            release(m,&m->pending[i]);m->pending_count--;memmove(m->pending+i,m->pending+i+1,(m->pending_count-i)*sizeof *m->pending);m->diagnostic.cancelled++;
        } else i++;
    }
}
static void drain(CohMixer *m) {
    unsigned r=atomic_load_explicit(&m->read,memory_order_relaxed),w=atomic_load_explicit(&m->write,memory_order_acquire);
    while(r!=w) {
        Command *c=&m->queue[r%m->config.event_capacity];
        if (c->kind==PLAY) {
            if (m->pending_count==m->config.event_capacity) { release(m,&c->event);m->diagnostic.pending_rejected++; }
            else {
                uint32_t i=m->pending_count++;
                while(i&&m->pending[i-1].at_frame>c->event.at_frame) { m->pending[i]=m->pending[i-1];i--; }
                m->pending[i]=c->event;
            }
        } else if(c->kind==STOP) stop(m,c->emitter,0);
        else if(c->kind==CANCEL) stop(m,0,1);
        else if(c->kind==LISTENER) { m->listener=c->position;m->right=c->right; }
        else if(c->kind==BUS) m->bus[c->bus]=c->gain;
        else if(c->kind==PAUSE) m->paused=c->paused;
        else if(c->kind==UPDATE) {
            for (uint32_t i=0;i<m->config.voices;i++) if (m->voices[i].active&&m->voices[i].event.emitter==c->emitter) { m->voices[i].event.position=c->position;m->voices[i].event.gain=c->gain; }
            for (uint32_t i=0;i<m->pending_count;i++) if (m->pending[i].emitter==c->emitter) { m->pending[i].position=c->position;m->pending[i].gain=c->gain; }
        }
        r++;
    }
    atomic_store_explicit(&m->read,r,memory_order_release);
}
static float loudness(CohMixer *m,const CohAudioEvent *e) {
    float l,r;coh_mixer_spatial_gains(e,m->listener,m->right,m->bus[e->bus],&l,&r);return fmaxf(l,r);
}
static void start(CohMixer *m,CohAudioEvent *e) {
    if (e->at_frame<m->frame) m->diagnostic.late_events++;
    Voice *slot=NULL;
    for (uint32_t i=0;i<m->config.voices;i++) {
        Voice *v=&m->voices[i];
        if (v->active&&v->event.emitter==e->emitter) {
            if (!e->interrupt) { release(m,e);m->diagnostic.play_rejected++;return; }
            slot=v;break;
        }
        if (!v->active&&!slot) slot=v;
    }
    if (!slot) {
        float quiet=loudness(m,e);uint32_t priority=e->priority;
        for (uint32_t i=0;i<m->config.voices;i++) {
            Voice *v=&m->voices[i];float gain=loudness(m,&v->event);
            if (v->event.priority<priority||(v->event.priority==priority&&gain<quiet)) { slot=v;priority=v->event.priority;quiet=gain; }
        }
    }
    if (!slot) { release(m,e);m->diagnostic.play_rejected++;return; }
    if (slot->active) { release(m,&slot->event);m->diagnostic.voices_stolen++; }
    slot->event=*e;slot->position=0;slot->active=1;m->diagnostic.play_started++;
}
static void due(CohMixer *m) {
    while(m->pending_count&&m->pending[0].at_frame<=m->frame) {
        CohAudioEvent e=m->pending[0];m->pending_count--;
        memmove(m->pending,m->pending+1,m->pending_count*sizeof *m->pending);start(m,&e);
    }
}
static void mix(CohMixer *m,float *out,uint32_t count) {
    for(uint32_t i=0;i<m->config.voices;i++) {
        Voice *v=&m->voices[i];if (!v->active) continue;
        float left,right;coh_mixer_spatial_gains(&v->event,m->listener,m->right,m->bus[v->event.bus],&left,&right);
        uint32_t starved=0;
        for(uint32_t f=0;f<count;f++) {
            float l=0,r=0;int ended=0;
            if (v->event.kind==COH_AUDIO_CACHED) {
                Cache *s=&m->cache[v->event.resource.slot];
                l=s->pcm[(size_t)v->position*s->channels];r=s->pcm[(size_t)v->position*s->channels+s->channels-1];
                v->position++;
                if (v->position==s->frames) { if(v->event.loop) v->position=0;else ended=1; }
            } else {
                Stream *s=&m->streams[v->event.resource.slot];
                /* Observe EOF before write: EOF's release publishes the final
                 * producer write, preventing stale-empty early completion. */
                unsigned eof=atomic_load_explicit(&s->eof,memory_order_acquire);
                unsigned rd=atomic_load_explicit(&s->read,memory_order_relaxed),wr=atomic_load_explicit(&s->write,memory_order_acquire);
                if (rd==wr) {
                    if (eof) ended=1;
                    else starved++;
                } else {
                    size_t j=(size_t)(rd%m->config.stream_frames)*2;l=s->pcm[j];r=s->pcm[j+1];
                    atomic_store_explicit(&s->read,rd+1,memory_order_release);
                    if (rd+1==wr&&eof) ended=1;
                }
            }
            out[(size_t)f*2]+=l*left;out[(size_t)f*2+1]+=r*right;
            if (ended) { release(m,&v->event);v->active=0;m->diagnostic.play_completed++;break; }
        }
        if(starved) { m->diagnostic.stream_underrun_frames+=starved;m->diagnostic.stream_underrun_callbacks++; }
    }
}
CohStatus coh_mixer_render(CohMixer *m,float *out,uint32_t frames) {
    if (!m||(!out&&frames)||frames>8192) return COH_INVALID;
    if(frames) memset(out,0,(size_t)frames*2*sizeof(float));
    m->diagnostic.callback_calls++;
    if(frames>m->diagnostic.maximum_callback_frames) m->diagnostic.maximum_callback_frames=frames;
    drain(m);
    unsigned errors=atomic_exchange_explicit(&m->error,0,memory_order_acquire);
    if(errors) { stop(m,0,1);m->paused=1;m->diagnostic.device_errors+=errors;m->diagnostic.device_generation++; }
    if(m->paused) { m->diagnostic.pause_callbacks++;return COH_OK; }
    uint32_t offset=0;
    while(offset<frames) {
        due(m);uint32_t n=frames-offset;
        if(m->pending_count&&m->pending[0].at_frame-m->frame<n) n=(uint32_t)(m->pending[0].at_frame-m->frame);
        mix(m,out+(size_t)offset*2,n);m->frame+=n;offset+=n;
    }
    for(size_t i=0;i<(size_t)frames*2;i++) {
        if(out[i]<-1||out[i]>1) m->diagnostic.clipped_samples++;
        out[i]=clamp(out[i],-1,1);
    }
    m->diagnostic.rendered_frames=m->frame;return COH_OK;
}
CohStatus coh_mixer_diagnostics(const CohMixer *m,CohMixerDiagnostics *out) {
    if(!m||!out) return COH_INVALID;
    *out=m->diagnostic;out->pending_events=m->pending_count;out->active_voices=0;out->retained_resources=0;
    for(uint32_t i=0;i<m->config.voices;i++) out->active_voices+=(m->voices[i].active!=0);
    for(uint32_t i=0;i<m->config.cache_entries;i++) out->retained_resources+=atomic_load(&m->cache[i].refs);
    for(uint32_t i=0;i<COH_MIXER_MAX_STREAMS;i++) out->retained_resources+=atomic_load(&m->streams[i].refs);
    return COH_OK;
}
