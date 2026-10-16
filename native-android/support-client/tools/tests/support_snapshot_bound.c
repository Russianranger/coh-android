#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <float.h>
#include <string.h>
#include "native-android/support-client/src/support_bridge.c"
CohStatus support_ui_snapshot(SupportUi *ui,SupportUiStats *out){(void)ui;memset(out,255,sizeof *out);out->target_health=-FLT_MAX;return COH_OK;}
CohStatus coh_support_physics_snapshot(const CohSupportPhysics *physics,CohSupportPhysicsSnapshot *out){(void)physics;memset(out,255,sizeof *out);return COH_OK;}
CohStatus coh_support_animation_snapshot(const CohSupportAnimation *animation,CohSupportAnimationSnapshot *out){(void)animation;memset(out,255,sizeof *out);return COH_OK;}
int support_audio_snapshot(SupportAudio *audio,SupportAudioReport *out){(void)audio;memset(out,255,sizeof *out);out->listener=(CohAudioListenerPose){{-FLT_MAX,FLT_MAX,-FLT_MAX},{FLT_MAX,-FLT_MAX,FLT_MAX}};return COH_OK;}
CohSkinCacheStats coh_skin_cache_stats(const CohSkinCache *cache){(void)cache;CohSkinCacheStats out;memset(&out,255,sizeof out);return out;}
int main(void){
 SupportBridge b;memset(&b,255,sizeof b);assert(!pthread_mutex_init(&b.mutex,NULL));
 char json[16384];memset(json,0x55,sizeof json);support_bridge_snapshot(&b,json,sizeof json);
 assert(strlen(json)<sizeof json-1);assert(json[0]=='{'&&json[strlen(json)-1]=='}');puts(json);
 pthread_mutex_destroy(&b.mutex);return 0;
}
