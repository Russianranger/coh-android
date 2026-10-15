#ifndef COH_HUD_ANDROID_H
#define COH_HUD_ANDROID_H
#include "../coh_hud.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Android KeyEvent/MotionEvent numeric constants are pinned against NDK r28c
 * android/{keycodes,input}.h. JNI/Java caller owns conversion and UI-thread
 * dispatch. No AInputEvent or Activity pointer is retained. */
CohStatus coh_hud_android_key(CohHud *hud,int keycode,int action,int repeat_count,int shift);
CohStatus coh_hud_android_touch(CohHud *hud,int masked_action,uint32_t pointer,float x,float y);
/* IME composition is deliberately separate from committed chat text. Temporary
 * composing text is copied, never sent as a chat intent or rendered as final. */
typedef struct { char composing[COH_UI_TEXT]; uint64_t commits,rejected; } CohHudIme;
void coh_hud_ime_init(CohHudIme *ime);
CohStatus coh_hud_ime_composing(CohHud *hud,CohHudIme *ime,const char *utf8);
CohStatus coh_hud_ime_commit(CohHud *hud,CohHudIme *ime,const char *utf8);
CohStatus coh_hud_ime_finish(CohHudIme *ime);
CohStatus coh_hud_ime_delete(CohHud *hud,int before_scalars,int after_scalars);
/* Neutral-to-direction edges avoid repeated motion with held joystick hats.
 * Caller selects a UI navigation stick and continues passing neutral samples. */
typedef struct { int horizontal,vertical; } CohHudNavigation;
void coh_hud_navigation_reset(CohHudNavigation *navigation);
CohStatus coh_hud_navigation_axis(CohHud *hud,CohHudNavigation *navigation,float x,float y);
#ifdef __cplusplus
}
#endif
#endif
