#define _POSIX_C_SOURCE 200809L
#include "support_bridge.h"
#include "support_physics.h"
#include "support_animation.h"
#include "support_audio.h"
#include "support_ui.h"
#include "coh_skin_cache.h"
#include "coh_perf.h"
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <inttypes.h>
struct SupportBridge {
 pthread_mutex_t mutex;
 CohSupportPhysics *physics; CohSupportAnimation *animation;
 SupportAudio *audio; SupportUi *ui; CohSkinCache *cache; CohPerf perf;
 const CohWalkTriangle *tri;unsigned triangle_count;CohBytes clips[3]; uint64_t tick,frames,trigger_count,failures,started;
 uint32_t generation,kind,hud_generation;int hud_width,hud_height; int mock_active,foreground,configured,context;
};
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;}
SupportBridge *support_bridge_create(const CohWalkTriangle *tri,unsigned count,const float spawn[3],float yaw,unsigned max_vertices){
 SupportBridge *b=calloc(1,sizeof *b);if(!b)return NULL;pthread_mutex_init(&b->mutex,NULL);
 b->tri=tri;b->triangle_count=count;b->started=ns();b->ui=support_ui_create();CohPerfConfig p=coh_perf_default_config();
 CohSkinCacheConfig cache={11,max_vertices,COH_ANIMATION_PALETTE,16u<<20};
 if(!b->ui||coh_perf_init(&b->perf,&p)||coh_skin_cache_create(&cache,&b->cache)||coh_support_physics_create(&b->physics,tri,count,spawn,yaw)) {(void)support_bridge_destroy(&b);return NULL;}
 coh_perf_set_paused(&b->perf,1);return b;
}
int support_bridge_destroy(SupportBridge **owner){if(!owner)return 0;SupportBridge *b=*owner;if(!b)return 1;
 /* Caller has stopped render/input users and serializes destruction. No other
  * dependency is released until the backend has joined every callback. */
 if(b->audio&&support_audio_destroy(&b->audio)){b->failures++;return 0;}
 coh_support_animation_destroy(b->animation);for(unsigned i=0;i<3;i++)free((void*)b->clips[i].data);
 coh_support_physics_destroy(b->physics);support_ui_destroy(b->ui);coh_skin_cache_destroy(&b->cache);pthread_mutex_destroy(&b->mutex);free(b);*owner=NULL;return 1;
}
int support_bridge_configure(SupportBridge *b,AAssetManager *manager,const void *clips[3],const size_t sizes[3]){
 if(!b||!manager||!clips||!sizes)return 0;pthread_mutex_lock(&b->mutex);
 int ok=0;CohBytes staged[3]={{0}};CohSupportAnimation *animation=NULL;SupportAudio *audio=NULL;
 if(b->configured){ok=1;goto done;}
 /* Stage owned clips/animation before starting the asynchronous audio worker.
  * No failure path overwrites an existing owner or leaves partial state. */
 for(unsigned i=0;i<3;i++){if(!clips[i]||!sizes[i]||sizes[i]>(1u<<20))goto done;uint8_t *p=malloc(sizes[i]);if(!p)goto done;memcpy(p,clips[i],sizes[i]);staged[i]=(CohBytes){p,sizes[i]};}
 if(coh_support_animation_create(staged,1,&animation))goto done;
 audio=support_audio_create(manager);if(!audio)goto done;
 memcpy(b->clips,staged,sizeof staged);memset(staged,0,sizeof staged);
 b->animation=animation;animation=NULL;b->audio=audio;b->configured=1;
 if(b->foreground)support_audio_resume(b->audio);ok=1;
 done:coh_support_animation_destroy(animation);for(unsigned i=0;i<3;i++)free((void*)staged[i].data);
 if(!ok)b->failures++;pthread_mutex_unlock(&b->mutex);return ok;
}
void support_bridge_foreground(SupportBridge*b,int active){if(!b)return;pthread_mutex_lock(&b->mutex);b->foreground=active;coh_perf_set_paused(&b->perf,!active);if(b->audio){if(active)support_audio_resume(b->audio);else support_audio_pause(b->audio);}pthread_mutex_unlock(&b->mutex);}
int support_bridge_walk(SupportBridge*b,unsigned dirs,float yaw,CohWalkState*out){if(!b||!out)return 0;pthread_mutex_lock(&b->mutex);coh_perf_stage_begin(&b->perf,COH_PERF_COLLISION,ns());CohStatus status=coh_support_physics_step(b->physics,dirs,yaw);if(status==COH_OK)*out=*coh_support_physics_state(b->physics);else b->failures++;coh_perf_stage_end(&b->perf,COH_PERF_COLLISION,ns());pthread_mutex_unlock(&b->mutex);return status==COH_OK;}
void support_bridge_reset(SupportBridge*b,const float spawn[3],float yaw,CohWalkState*out){if(!b)return;pthread_mutex_lock(&b->mutex);CohSupportPhysics *fresh=NULL;if(!coh_support_physics_create(&fresh,b->tri,b->triangle_count,spawn,yaw)){coh_support_physics_destroy(b->physics);b->physics=fresh;}else b->failures++;if(out)*out=*coh_support_physics_state(b->physics);b->mock_active=0;coh_skin_cache_invalidate(b->cache);pthread_mutex_unlock(&b->mutex);}
void support_bridge_clear(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);coh_support_physics_clear(b->physics);pthread_mutex_unlock(&b->mutex);}
int support_bridge_pose(SupportBridge*b,float dt,CohAnimationPose*out,const CohAnimationRig**rig){if(!b)return 0;pthread_mutex_lock(&b->mutex);int result=0;if(b->animation&&b->mock_active){coh_perf_stage_begin(&b->perf,COH_PERF_ANIMATION,ns());if(!coh_support_animation_sample(b->animation,dt,++b->tick,out)){*rig=coh_support_animation_active_rig(b->animation);result=1;}else b->failures++;coh_perf_stage_end(&b->perf,COH_PERF_ANIMATION,ns());}pthread_mutex_unlock(&b->mutex);return result;}
const CohSkinnedVertex*support_bridge_skin(SupportBridge*b,unsigned part,const CohMeshVertex*v,unsigned count,const float*rows,unsigned bones){if(!b)return NULL;pthread_mutex_lock(&b->mutex);const CohSkinnedVertex*out=NULL;CohSkinKey key={part+1,1,1,1,1,1};int measure=b->perf.active_frame&&!b->perf.snapshot.paused;if(measure)coh_perf_stage_begin(&b->perf,COH_PERF_SKINNING,ns());if(coh_skin_cache_sample(b->cache,key,v,count,rows,bones,&out,NULL))b->failures++;if(measure)coh_perf_stage_end(&b->perf,COH_PERF_SKINNING,ns());pthread_mutex_unlock(&b->mutex);return out;}
void support_bridge_surface_begin(SupportBridge*b,unsigned gen){if(!b)return;int context=support_ui_context_create(b->ui,gen)==COH_OK;pthread_mutex_lock(&b->mutex);b->generation=gen;coh_perf_surface(&b->perf,gen);coh_perf_gpu_unavailable(&b->perf);b->context=context;if(!context)b->failures++;pthread_mutex_unlock(&b->mutex);}
/* Render owner only. Never hold the lifecycle/performance mutex across GL.
 * The UI adapter has its own bounded draw/input serialization. */
int support_bridge_draw(SupportBridge*b,int w,int h,unsigned gen){if(!b)return 0;
 int ok=b->context;
 if(ok&&(b->hud_generation!=gen||b->hud_width!=w||b->hud_height!=h)){
  ok=support_ui_surface(b->ui,gen,w,h,(CohHudInsets){0,0,0,0})==COH_OK;
  if(ok){b->hud_generation=gen;b->hud_width=w;b->hud_height=h;}
 }
 if(ok)ok=support_ui_tick_mock(b->ui,(ns()-b->started)/1000000)==COH_OK&&support_ui_draw(b->ui,w,h,gen)==COH_OK;
 if(!ok){pthread_mutex_lock(&b->mutex);b->failures++;pthread_mutex_unlock(&b->mutex);}return ok;
}
void support_bridge_surface_end(SupportBridge*b){if(!b)return;support_ui_context_destroy(b->ui);b->context=0;b->hud_generation=0;}
void support_bridge_frame_begin(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);coh_perf_frame_begin(&b->perf,ns(),b->generation);pthread_mutex_unlock(&b->mutex);}
void support_bridge_frame_end(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);if(b->perf.active_frame&&!b->perf.snapshot.paused)coh_perf_frame_end(&b->perf,ns());b->frames++;pthread_mutex_unlock(&b->mutex);}
void support_bridge_trigger(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);if(b->animation){b->kind=(uint32_t)(b->trigger_count%4);b->mock_active=b->kind<3;if(b->mock_active&&coh_support_animation_trigger(b->animation,b->kind,b->tick+1))b->failures++;b->trigger_count++;if(b->audio)support_audio_emitter(b->audio,(b->kind==0?-8.f:8.f),0,4);}pthread_mutex_unlock(&b->mutex);}
int support_bridge_touch(SupportBridge*b,int action,unsigned pointer,float x,float y){if(!b)return 0;return support_ui_touch(b->ui,action,pointer,x,y)==COH_OK;}
int support_bridge_key(SupportBridge*b,int key,int action,int repeat,int shift){if(!b)return 0;return support_ui_key(b->ui,key,action,repeat,shift)==COH_OK;}
void support_bridge_text(SupportBridge*b,const char*text){if(!b)return;support_ui_focus_chat(b->ui);support_ui_text(b->ui,text);support_ui_submit(b->ui);}
void support_bridge_snapshot(SupportBridge*b,char*out,size_t cap){if(!b){snprintf(out,cap,"{\"configured\":false}");return;}SupportUiStats u={0};support_ui_snapshot(b->ui,&u);pthread_mutex_lock(&b->mutex);
 char perf[8192];size_t needed=0;if(coh_perf_json(&b->perf,perf,sizeof perf,&needed))strcpy(perf,"{}");
 CohSupportPhysicsSnapshot p={0};coh_support_physics_snapshot(b->physics,&p);CohSupportAnimationSnapshot a={0};if(b->animation)coh_support_animation_snapshot(b->animation,&a);
 SupportAudioReport r={0};if(b->audio)support_audio_snapshot(b->audio,&r);CohSkinCacheStats c=coh_skin_cache_stats(b->cache);
 snprintf(out,cap,"{\"schema\":1,\"offline_mock\":true,\"configured\":%s,\"failures\":%"PRIu64",\"frames\":%"PRIu64",\"character\":{\"scene_actor\":\"Wretch\",\"new_body_gpu_qualified\":false},\"physics\":{\"steps\":%"PRIu64",\"segments\":%u,\"triangles\":%u,\"owned_bytes\":%zu,\"nodes_visited\":%u,\"triangle_tests\":%u,\"jump_supported\":false},\"animation\":{\"samples\":%"PRIu64",\"triggers\":%"PRIu64",\"kind\":%u,\"neutral_pose\":true},\"hud\":{\"frames\":%"PRIu64",\"gl_errors\":%"PRIu64",\"power_uses\":%"PRIu64",\"chat_submits\":%"PRIu64",\"character_selections\":%"PRIu64",\"intents\":%"PRIu64",\"surface_recreates\":%"PRIu64",\"generation\":%u},\"audio\":{\"initialized\":%d,\"running\":%d,\"last_status\":%d,\"device_error\":%d,\"opens\":%"PRIu64",\"closes\":%"PRIu64",\"decode_calls\":%"PRIu64",\"diagnostics_valid\":%d,\"rendered_frames\":%"PRIu64",\"underrun_frames\":%"PRIu64",\"callback_calls\":%"PRIu64",\"maximum_callback_ns\":%"PRIu64"},\"skin_cache\":{\"hits\":%"PRIu64",\"misses\":%"PRIu64",\"bytes\":%zu},\"performance\":%s}",b->configured?"true":"false",b->failures,b->frames,p.steps,p.scene.segment_count,p.scene.triangle_count,p.scene.owned_bytes,p.query.nodes,p.query.triangles,a.samples,b->trigger_count,b->kind,u.gpu.frames,u.gpu.gl_errors,u.power_uses,u.chat_submits,u.character_selections,u.intents_processed,u.hud.surface_recreates,u.generation,r.initialized,r.running,r.last_status,r.device_error,r.opens,r.closes,r.decode_calls,r.diagnostics_valid,r.rendered_frames,r.underrun_frames,r.callback_calls,r.maximum_callback_ns,c.hits,c.misses,c.allocated_bytes,perf);
 pthread_mutex_unlock(&b->mutex);
}
