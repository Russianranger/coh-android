#define _POSIX_C_SOURCE 200809L
#include "support_bridge.h"
#include "support_physics.h"
#include "support_animation.h"
#include "support_audio.h"
#include "support_ui.h"
#include "coh_skin_cache.h"
#include "coh_perf.h"
#include "coh_perf_bridge.h"
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <inttypes.h>
struct SupportBridge {
 pthread_mutex_t mutex;
 CohSupportPhysics *physics; CohSupportAnimation *animation;
 SupportAudio *audio; SupportUi *ui; CohSkinCache *cache; CohPerf perf; CohPerfBridge observed; float spawn[3];
 uint64_t route_generation,active_ns,active_since,presentation_animations; int audio_allowed;
 const CohWalkTriangle *tri;unsigned triangle_count;CohBytes clips[3]; uint64_t tick,frames,trigger_count,failures,started;
 uint32_t generation,kind,hud_generation;int hud_width,hud_height; int mock_active,foreground,configured,context;
};
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;}
SupportBridge *support_bridge_create(const CohWalkTriangle *tri,unsigned count,const float spawn[3],float yaw,unsigned max_vertices){
 SupportBridge *b=calloc(1,sizeof *b);if(!b)return NULL;pthread_mutex_init(&b->mutex,NULL);
 memcpy(b->spawn,spawn,sizeof b->spawn);coh_perf_bridge_init(&b->observed);b->tri=tri;b->triangle_count=count;b->started=ns();b->ui=support_ui_create();CohPerfConfig p=coh_perf_default_config();
 CohSkinCacheConfig cache={11,max_vertices,COH_ANIMATION_PALETTE,16u<<20};
 if(!b->ui||coh_perf_init(&b->perf,&p)||coh_skin_cache_create(&cache,&b->cache)||coh_support_physics_create(&b->physics,tri,count,spawn,yaw)) {(void)support_bridge_destroy(&b);return NULL;}
 coh_perf_set_paused(&b->perf,1);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_COPIED_BYTES,1,0);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_SKINNED_VERTICES,1,0);return b;
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
 support_audio_emitter(b->audio,b->spawn[0]+8,b->spawn[1],b->spawn[2]+4);
 if(b->route_generation)support_audio_route(b->audio,b->route_generation);
 if(b->foreground&&b->audio_allowed)support_audio_resume(b->audio);ok=1;
 done:coh_support_animation_destroy(animation);for(unsigned i=0;i<3;i++)free((void*)staged[i].data);
 if(!ok)b->failures++;pthread_mutex_unlock(&b->mutex);return ok;
}
void support_bridge_foreground(SupportBridge*b,int active){if(!b)return;pthread_mutex_lock(&b->mutex);uint64_t now=ns();if(b->foreground&&!active)b->active_ns+=now-b->active_since;else if(!b->foreground&&active)b->active_since=now;b->foreground=active;coh_perf_set_paused(&b->perf,!active);if(b->audio){if(active&&b->audio_allowed)support_audio_resume(b->audio);else support_audio_pause(b->audio);}pthread_mutex_unlock(&b->mutex);}
void support_bridge_audio_environment(SupportBridge*b,int allowed,uint64_t route){
 if(!b)return;pthread_mutex_lock(&b->mutex);b->audio_allowed=!!allowed;b->route_generation=route;
 if(b->audio){support_audio_route(b->audio,route);if(b->foreground&&allowed)support_audio_resume(b->audio);else support_audio_pause(b->audio);}
 pthread_mutex_unlock(&b->mutex);
}
void support_bridge_listener(SupportBridge*b,const float view[12]){
 if(!b)return;CohAudioListenerPose pose;if(coh_audio_listener_source_view(view,&pose))return;
 pthread_mutex_lock(&b->mutex);if(b->audio)support_audio_listener(b->audio,&pose);pthread_mutex_unlock(&b->mutex);
}
void support_bridge_render_metrics(SupportBridge*b,uint64_t draws,uint64_t uploads,uint64_t hits,uint64_t misses,uint64_t evictions){
 if(!b)return;pthread_mutex_lock(&b->mutex);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_DRAW_CALLS,draws);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_UPLOAD_BYTES,uploads);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_ASSET_HITS,hits);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_ASSET_MISSES,misses);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_ASSET_EVICTIONS,evictions);
 pthread_mutex_unlock(&b->mutex);
}
void support_bridge_stage(SupportBridge*b,CohPerfStage stage,int begin){
 if(!b)return;pthread_mutex_lock(&b->mutex);
 if(b->perf.active_frame&&!b->perf.snapshot.paused){if(begin)coh_perf_stage_begin(&b->perf,stage,ns());else coh_perf_stage_end(&b->perf,stage,ns());}
 pthread_mutex_unlock(&b->mutex);
}
int support_bridge_walk(SupportBridge*b,unsigned dirs,float yaw,CohWalkState*out){
 if(!b||!out)return 0;pthread_mutex_lock(&b->mutex);
 uint32_t previous=coh_support_physics_state(b->physics)->triangle_tests;
 int measure=b->perf.active_frame&&!b->perf.snapshot.paused;if(measure)coh_perf_stage_begin(&b->perf,COH_PERF_COLLISION,ns());
 CohStatus status=coh_support_physics_step(b->physics,dirs,yaw);
 if(status==COH_OK){*out=*coh_support_physics_state(b->physics);coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_COLLISION_TESTS,out->triangle_tests-previous);}
 else b->failures++;
 if(measure)coh_perf_stage_end(&b->perf,COH_PERF_COLLISION,ns());pthread_mutex_unlock(&b->mutex);return status==COH_OK;
}
void support_bridge_reset(SupportBridge*b,const float spawn[3],float yaw,CohWalkState*out){if(!b)return;pthread_mutex_lock(&b->mutex);CohSupportPhysics *fresh=NULL;if(!coh_support_physics_create(&fresh,b->tri,b->triangle_count,spawn,yaw)){coh_support_physics_destroy(b->physics);b->physics=fresh;}else b->failures++;if(out)*out=*coh_support_physics_state(b->physics);b->mock_active=0;coh_skin_cache_invalidate(b->cache);pthread_mutex_unlock(&b->mutex);}
void support_bridge_clear(SupportBridge*b){if(!b)return;support_ui_navigation(b->ui,0,0,0);pthread_mutex_lock(&b->mutex);coh_support_physics_clear(b->physics);pthread_mutex_unlock(&b->mutex);}
int support_bridge_pose(SupportBridge*b,float dt,CohAnimationPose*out,const CohAnimationRig**rig){if(!b)return 0;pthread_mutex_lock(&b->mutex);int result=0;if(b->animation&&b->mock_active){int measure=b->perf.active_frame&&!b->perf.snapshot.paused;if(measure)coh_perf_stage_begin(&b->perf,COH_PERF_ANIMATION,ns());if(!coh_support_animation_sample(b->animation,dt,++b->tick,out)){*rig=coh_support_animation_active_rig(b->animation);result=1;}else b->failures++;if(measure)coh_perf_stage_end(&b->perf,COH_PERF_ANIMATION,ns());}pthread_mutex_unlock(&b->mutex);return result;}
const CohSkinnedVertex*support_bridge_skin(SupportBridge*b,unsigned part,const CohMeshVertex*v,unsigned count,const float*rows,unsigned bones){if(!b)return NULL;pthread_mutex_lock(&b->mutex);const CohSkinnedVertex*out=NULL;CohSkinKey key={part+1,1,1,1,1,1};int measure=b->perf.active_frame&&!b->perf.snapshot.paused;if(measure)coh_perf_stage_begin(&b->perf,COH_PERF_SKINNING,ns());if(coh_skin_cache_sample(b->cache,key,v,count,rows,bones,&out,NULL))b->failures++;if(measure)coh_perf_stage_end(&b->perf,COH_PERF_SKINNING,ns());pthread_mutex_unlock(&b->mutex);return out;}
void support_bridge_surface_begin(SupportBridge*b,unsigned gen){if(!b)return;int context=support_ui_context_create(b->ui,gen)==COH_OK;pthread_mutex_lock(&b->mutex);b->generation=gen;
 int paused=b->perf.snapshot.paused;coh_perf_set_paused(&b->perf,1);
 CohSkinCacheStats c=coh_skin_cache_stats(b->cache);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_COPIED_BYTES,1,c.copied_bytes);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_SKINNED_VERTICES,1,c.kernel_vertices);
 coh_perf_set_paused(&b->perf,paused);coh_perf_surface(&b->perf,gen);coh_perf_gpu_unavailable(&b->perf);b->context=context;if(!context)b->failures++;pthread_mutex_unlock(&b->mutex);}
/* Render owner only. Never hold the lifecycle/performance mutex across GL.
 * The UI adapter has its own bounded draw/input serialization. */
int support_bridge_draw(SupportBridge*b,int w,int h,unsigned gen){if(!b)return 0;
 int ok=b->context;
 if(ok&&(b->hud_generation!=gen||b->hud_width!=w||b->hud_height!=h)){
  ok=support_ui_surface(b->ui,gen,w,h,(CohHudInsets){0,0,0,0})==COH_OK;
  if(ok){b->hud_generation=gen;b->hud_width=w;b->hud_height=h;}
 }
 SupportUiStats before={0},after={0};support_ui_snapshot(b->ui,&before);
 if(ok)ok=support_ui_tick_mock(b->ui,(ns()-b->started)/1000000)==COH_OK&&support_ui_draw(b->ui,w,h,gen)==COH_OK;
 support_ui_snapshot(b->ui,&after);
 pthread_mutex_lock(&b->mutex);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_DRAW_CALLS,after.gpu.draw_calls-before.gpu.draw_calls);
 coh_perf_bridge_delta(&b->observed,&b->perf,COH_PERF_UPLOAD_BYTES,after.gpu.bytes_uploaded-before.gpu.bytes_uploaded);
 if(!ok)b->failures++;pthread_mutex_unlock(&b->mutex);return ok;
}
void support_bridge_surface_end(SupportBridge*b){if(!b)return;support_ui_context_destroy(b->ui);b->context=0;b->hud_generation=0;}
void support_bridge_frame_begin(SupportBridge*b){if(!b)return;
 CohPresentationCue cues[COH_PRESENTATION_QUEUE];unsigned count=0;
 while(count<COH_PRESENTATION_QUEUE&&support_ui_poll_presentation_cue(b->ui,&cues[count]))count++;
 pthread_mutex_lock(&b->mutex);
 for(unsigned i=0;i<count;i++)if(cues[i].animation_asset==1&&b->animation){
  b->kind=0;b->mock_active=1;
  if(coh_support_animation_trigger(b->animation,0,b->tick+1))b->failures++;else b->presentation_animations++;
 }
 if(!b->perf.snapshot.paused)coh_perf_frame_begin(&b->perf,ns(),b->generation);pthread_mutex_unlock(&b->mutex);
}
void support_bridge_frame_end(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);CohSkinCacheStats c=coh_skin_cache_stats(b->cache);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_COPIED_BYTES,1,c.copied_bytes);
 coh_perf_bridge_total(&b->observed,&b->perf,COH_PERF_SKINNED_VERTICES,1,c.kernel_vertices);
 if(b->perf.active_frame&&!b->perf.snapshot.paused)coh_perf_frame_end(&b->perf,ns());b->frames++;pthread_mutex_unlock(&b->mutex);}
void support_bridge_trigger(SupportBridge*b){if(!b)return;pthread_mutex_lock(&b->mutex);if(b->animation){b->kind=(uint32_t)(b->trigger_count%4);b->mock_active=b->kind<3;if(b->mock_active&&coh_support_animation_trigger(b->animation,b->kind,b->tick+1))b->failures++;b->trigger_count++;if(b->audio)support_audio_emitter(b->audio,b->spawn[0]+(b->kind==0?-8.f:8.f),b->spawn[1],b->spawn[2]+4);}pthread_mutex_unlock(&b->mutex);}
void support_bridge_preview_label(SupportBridge*b,int male){if(b)support_ui_preview_label(b->ui,male);}
void support_bridge_presentation(SupportBridge*b,int action){if(b)(void)support_ui_presentation(b->ui,action);}
int support_bridge_touch(SupportBridge*b,int action,unsigned pointer,float x,float y){if(!b)return 0;int consumed=0;(void)support_ui_pointer(b->ui,action,pointer,x,y,&consumed);return consumed;}
void support_bridge_navigation(SupportBridge*b,int active,float x,float y){if(b)support_ui_navigation(b->ui,active,x,y);}
int support_bridge_key(SupportBridge*b,int key,int action,int repeat,int shift){if(!b)return 0;return support_ui_key(b->ui,key,action,repeat,shift)==COH_OK;}
void support_bridge_text(SupportBridge*b,const char*text){if(!b)return;support_ui_focus_chat(b->ui);support_ui_text(b->ui,text);support_ui_submit(b->ui);}
void support_bridge_snapshot(SupportBridge*b,char*out,size_t cap){if(!out||!cap)return;if(!b){snprintf(out,cap,"{\"configured\":false}");return;}SupportUiStats u={0};support_ui_snapshot(b->ui,&u);pthread_mutex_lock(&b->mutex);
 char perf[8192];size_t needed=0;if(coh_perf_json(&b->perf,perf,sizeof perf,&needed))strcpy(perf,"{}");
 CohSupportPhysicsSnapshot p={0};coh_support_physics_snapshot(b->physics,&p);CohSupportAnimationSnapshot a={0};if(b->animation)coh_support_animation_snapshot(b->animation,&a);
 SupportAudioReport r={0};if(b->audio)support_audio_snapshot(b->audio,&r);CohSkinCacheStats c=coh_skin_cache_stats(b->cache);
 int written=snprintf(out,cap,"{\"schema\":1,\"offline_mock\":true,\"configured\":%s,\"failures\":%"PRIu64",\"frames\":%"PRIu64",\"character\":{\"scene_actor\":\"Wretch\",\"appearance_preview_report\":\"native.appearance_preview\",\"new_body_gpu_qualified\":false},\"physics\":{\"steps\":%"PRIu64",\"segments\":%u,\"triangles\":%u,\"owned_bytes\":%zu,\"nodes_visited\":%u,\"triangle_tests\":%u,\"jump_supported\":false},\"animation\":{\"samples\":%"PRIu64",\"triggers\":%"PRIu64",\"kind\":%u,\"neutral_pose\":true},\"hud\":{\"frames\":%"PRIu64",\"gl_errors\":%"PRIu64",\"power_uses\":%"PRIu64",\"chat_submits\":%"PRIu64",\"character_selections\":%"PRIu64",\"intents\":%"PRIu64",\"surface_recreates\":%"PRIu64",\"generation\":%u},\"audio\":{\"initialized\":%d,\"running\":%d,\"last_status\":%d,\"device_error\":%d,\"opens\":%"PRIu64",\"closes\":%"PRIu64",\"decode_calls\":%"PRIu64",\"diagnostics_valid\":%d,\"rendered_frames\":%"PRIu64",\"underrun_frames\":%"PRIu64",\"callback_calls\":%"PRIu64",\"maximum_callback_ns\":%"PRIu64"},\"skin_cache\":{\"hits\":%"PRIu64",\"misses\":%"PRIu64",\"bytes\":%zu},\"performance\":%s}",b->configured?"true":"false",b->failures,b->frames,p.steps,p.scene.segment_count,p.scene.triangle_count,p.scene.owned_bytes,p.query.nodes,p.query.triangles,a.samples,b->trigger_count,b->kind,u.gpu.frames,u.gpu.gl_errors,u.power_uses,u.chat_submits,u.character_selections,u.intents_processed,u.hud.surface_recreates,u.generation,r.initialized,r.running,r.last_status,r.device_error,r.opens,r.closes,r.decode_calls,r.diagnostics_valid,r.rendered_frames,r.underrun_frames,r.callback_calls,r.maximum_callback_ns,c.hits,c.misses,c.allocated_bytes,perf);
 if(written<0||(size_t)written>=cap){snprintf(out,cap,"{\"configured\":true,\"failures\":1,\"diagnostic_truncated\":true}");pthread_mutex_unlock(&b->mutex);return;}
 /* Coverage is separate from zero-valued generic observer counters. */
 char observed[6144];size_t observed_needed=0;
 uint64_t accounted=sizeof *b+c.allocated_bytes+p.scene.owned_bytes+u.arena_bytes+r.mixer_allocated_bytes+r.adapter_bytes;
 coh_perf_bridge_memory(&b->observed,COH_PERF_MEMORY_ACCOUNTED,accounted);
 if(coh_perf_bridge_json(&b->observed,observed,sizeof observed,&observed_needed))strcpy(observed,"{}");
 size_t used=strlen(out);
 if(used&&out[used-1]=='}'&&used<cap){
  int appended=snprintf(out+used-1,cap-used+1,",\"presentation\":{\"visible\":%s,\"tab\":%u,\"events\":%"PRIu64",\"intents\":%"PRIu64",\"cues\":%"PRIu64",\"missing_audio\":%"PRIu64",\"missing_animation\":%"PRIu64",\"animation_bindings\":%"PRIu64",\"cue_drops\":%"PRIu64",\"audio_binding_available\":false,\"queue_limits\":%"PRIu64",\"builds\":%"PRIu64",\"target_health\":%.9g,\"offline_only\":true},\"ui_extensions\":{\"authentic_tray_images\":11,\"power_specific_icons\":false,\"axis_actions\":%"PRIu64",\"axis_repeats\":%"PRIu64"},\"active_foreground_ms\":%"PRIu64",\"observations\":%s,\"observation_scope\":\"Frame actor+world+HUD+appearance-preview draw calls; Wretch+HUD dynamic uploads (preview upload bytes unmeasured); asset-cache operations; exact skin-cache copies/kernel vertices; source WALK triangle tests. Partial module-accounted bytes exclude renderer-scene, codec, allocator and OS memory. Startup diagnostic GPU readbacks are outside profiling; waits/allocations/RSS/PSS/thermal unknown.\",\"audio_environment\":{\"focus_allowed\":%s,\"route_generation\":%"PRIu64",\"route_reopens\":%"PRIu64",\"listener_updates\":%"PRIu64",\"recovered_device_errors\":%"PRIu64",\"last_device_error\":%d,\"listener_position\":[%.9g,%.9g,%.9g],\"listener_right\":[%.9g,%.9g,%.9g]}}",u.presentation_visible?"true":"false",u.presentation_tab,u.presentation.events,u.presentation_intents,u.presentation_cues,u.presentation.missing_audio,u.presentation.missing_animation,b->presentation_animations,u.presentation_cue_drops,u.presentation.queue_limits,u.presentation.builds,u.target_health,u.axis_actions,u.axis_repeats,(b->active_ns+(b->foreground?ns()-b->active_since:0))/1000000,observed,b->audio_allowed?"true":"false",b->route_generation,r.route_reopens,r.listener_updates,r.recovered_device_errors,r.last_device_error,r.listener.position.x,r.listener.position.y,r.listener.position.z,r.listener.right.x,r.listener.right.y,r.listener.right.z);
  if(appended<0||(size_t)appended>=cap-used+1)snprintf(out,cap,"{\"configured\":true,\"failures\":1,\"diagnostic_truncated\":true}");
 }
 pthread_mutex_unlock(&b->mutex);
}
