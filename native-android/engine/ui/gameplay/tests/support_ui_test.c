#define _POSIX_C_SOURCE 200809L
#include "../../../../support-client/src/support_ui.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static SupportUi *ui;
static void tap(float x,float y){CohStatus s;assert(support_ui_touch(ui,0,0,x,y)==COH_OK);s=support_ui_touch(ui,1,0,x,y);assert(s==COH_OK||s==COH_STATE);}
static void *snapshots(void *ctx){
    SupportUiStats stats;unsigned i;(void)ctx;
    for(i=0;i<2000;i++){assert(support_ui_snapshot(ui,&stats)==COH_OK);assert(stats.arena_bytes>sizeof(CohHud));}
    return NULL;
}
static void *navigation(void *ctx){
    unsigned i;(void)ctx;for(i=0;i<2000;i++){
        CohStatus s=support_ui_key(ui,61,0,0,(int)(i&1u));assert(s==COH_OK||s==COH_NOT_FOUND);
    }return NULL;
}
int run_support_ui_tests(void){
    SupportUiStats stats;CohHudIntent intent;unsigned count=0,i;pthread_t one,two;
    ui=support_ui_create();assert(ui);
    assert(support_ui_draw(ui,1280,720,1)==COH_STATE);
    assert(support_ui_surface(ui,1,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(support_ui_context_create(ui,1)==COH_OK);
    assert(support_ui_tick_mock(ui,0)==COH_OK);assert(support_ui_draw(ui,1280,720,1)==COH_OK);
    tap(396,604);assert(support_ui_keyboard_requested(ui));
    assert(support_ui_text(ui,"Hello \xe7\x8c\xab")==COH_OK);
    assert(support_ui_draw(ui,1280,720,1)==COH_OK);assert(support_ui_submit(ui)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.chat_submits==1&&!stats.chat_input[0]);
    tap(409,674);assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.power_uses==1&&stats.last_power==1000);
    tap(409,674);assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.power_uses==1);
    assert(support_ui_tick_mock(ui,3000)==COH_OK);tap(409,674);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.power_uses==2);
    tap(263,656);assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.menu_opens==1);
    tap(640,206);assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.character_selections==1&&stats.last_character==501);
    tap(396,604);assert(support_ui_text(ui,"survives")==COH_OK);
    assert(support_ui_draw(ui,1280,720,1)==COH_OK);
    support_ui_context_destroy(ui);assert(support_ui_draw(ui,1280,720,1)==COH_STATE);
    assert(support_ui_context_create(ui,2)==COH_OK);
    assert(support_ui_surface(ui,2,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(support_ui_draw(ui,1280,720,2)==COH_OK);
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&!strcmp(stats.chat_input,"survives")&&stats.gpu.gl_errors==0&&stats.gpu.frames==4);
    while(support_ui_poll_intent(ui,&intent))count++;
    assert(count==5);
    assert(!pthread_create(&one,NULL,snapshots,NULL));assert(!pthread_create(&two,NULL,navigation,NULL));
    for(i=0;i<100;i++){
        assert(support_ui_tick_mock(ui,4000+i)==COH_OK);assert(support_ui_draw(ui,1280,720,2)==COH_OK);
    }
    assert(!pthread_join(one,NULL)&&!pthread_join(two,NULL));
    assert(support_ui_snapshot(ui,&stats)==COH_OK&&stats.gpu.gl_errors==0&&stats.gpu.frames==104);
    printf("{\"offline_intents\":%u,\"gpu_frames\":%llu,\"thread_snapshot_calls\":2000,\"thread_navigation_calls\":2000,\"arena_bytes\":%zu,\"GL_errors\":0}\n",count,(unsigned long long)stats.gpu.frames,stats.arena_bytes);
    support_ui_context_destroy(ui);support_ui_destroy(ui);support_ui_destroy(NULL);ui=NULL;return 0;
}
#ifdef SUPPORT_UI_TEST_MAIN
/* Minimal stable EGL ABI declarations keep this host-only bootstrap independent
 * of X11/platform headers. The actual implementation is libEGL.so.1. */
extern void *eglGetDisplay(void *display);
extern int eglInitialize(void *display,int *major,int *minor);
extern int eglBindAPI(unsigned api);
extern int eglChooseConfig(void *display,const int *attrs,void **config,int size,int *count);
extern void *eglCreatePbufferSurface(void *display,void *config,const int *attrs);
extern void *eglCreateContext(void *display,void *config,void *share,const int *attrs);
extern int eglMakeCurrent(void *display,void *read,void *draw,void *context);
extern int eglDestroyContext(void *display,void *context);
extern int eglDestroySurface(void *display,void *surface);
extern int eglTerminate(void *display);
int main(void){
    const int attrs[]={0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038};
    const int surface_attrs[]={0x3057,1280,0x3056,720,0x3038},context_attrs[]={0x3098,3,0x3038};
    void *display,*config,*surface,*context;int major,minor,count,result;
    assert(!setenv("EGL_PLATFORM","surfaceless",1));display=eglGetDisplay(NULL);
    assert(eglInitialize(display,&major,&minor)&&eglBindAPI(0x30a0));
    assert(eglChooseConfig(display,attrs,&config,1,&count)&&count);
    surface=eglCreatePbufferSurface(display,config,surface_attrs);context=eglCreateContext(display,config,NULL,context_attrs);
    assert(surface&&context&&eglMakeCurrent(display,surface,surface,context));result=run_support_ui_tests();
    eglMakeCurrent(display,NULL,NULL,NULL);eglDestroyContext(display,context);eglDestroySurface(display,surface);eglTerminate(display);return result;
}
#endif
