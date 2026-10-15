#include "coh_hud_android.h"
#include <math.h>
#include <string.h>
CohStatus coh_hud_android_key(CohHud *h,int code,int action,int repeat,int shift){
    CohUiAction mapped;int navigation=0;
    if(!h||!h->initialized)return COH_STATE;
    if(action<0||action>1||repeat<0)return COH_INVALID;
    switch(code){
    case 19:mapped=COH_UI_UP;navigation=1;break;
    case 20:mapped=COH_UI_DOWN;navigation=1;break;
    case 21:mapped=COH_UI_LEFT;navigation=1;break;
    case 22:mapped=COH_UI_RIGHT;navigation=1;break;
    case 61:mapped=shift?COH_UI_PREVIOUS:COH_UI_NEXT;navigation=1;break;
    case 102:mapped=COH_UI_PREVIOUS;navigation=1;break;
    case 103:mapped=COH_UI_NEXT;navigation=1;break;
    case 23:case 96:mapped=COH_UI_ACTIVATE;break;
    case 66:mapped=COH_UI_SUBMIT;break;
    case 67:mapped=COH_UI_BACKSPACE;navigation=1;break;
    case 4:case 97:case 111:mapped=COH_UI_CANCEL;break;
    default:return COH_UNSUPPORTED;
    }
    if(action==1||(!navigation&&repeat))return COH_OK;
    return coh_hud_action(h,mapped);
}
CohStatus coh_hud_android_touch(CohHud *h,int action,uint32_t pointer,float x,float y){
    if(!h||!h->initialized)return COH_STATE;
    if(!isfinite(x)||!isfinite(y))return COH_INVALID;
    switch(action){
    case 0:case 5:return coh_hud_touch(h,COH_UI_TOUCH_DOWN,pointer,x,y);
    case 1:case 6:return coh_hud_touch(h,COH_UI_TOUCH_UP,pointer,x,y);
    case 3:return coh_hud_touch(h,COH_UI_TOUCH_CANCEL,h->ui.capture_pointer,x,y);
    case 2:return COH_OK; /* Button capture resolves inside/outside on release. */
    default:return COH_UNSUPPORTED;
    }
}
void coh_hud_ime_init(CohHudIme *ime){if(ime)memset(ime,0,sizeof(*ime));}
CohStatus coh_hud_ime_composing(CohHud *h,CohHudIme *ime,const char *text){
    CohStatus s;size_t n;
    if(!ime)return COH_INVALID;
    if(!coh_hud_keyboard_requested(h))return COH_STATE;
    s=coh_ui_utf8(text,1,&n);if(s!=COH_OK){ime->rejected++;return s;}
    memcpy(ime->composing,text,n+1);return COH_OK;
}
CohStatus coh_hud_ime_commit(CohHud *h,CohHudIme *ime,const char *text){
    CohStatus s;if(!ime)return COH_INVALID;
    s=coh_hud_text_commit(h,text);
    if(s!=COH_OK){ime->rejected++;return s;}
    ime->composing[0]=0;ime->commits++;return COH_OK;
}
CohStatus coh_hud_ime_finish(CohHudIme *ime){if(!ime)return COH_INVALID;ime->composing[0]=0;return COH_OK;}
CohStatus coh_hud_ime_delete(CohHud *h,int before,int after){
    if(before!=1||after!=0)return COH_UNSUPPORTED;
    return coh_hud_action(h,COH_UI_BACKSPACE);
}
void coh_hud_navigation_reset(CohHudNavigation *n){if(n)memset(n,0,sizeof(*n));}
CohStatus coh_hud_navigation_axis(CohHud *h,CohHudNavigation *n,float x,float y){
    int dx,dy;CohStatus s=COH_OK;
    if(!h||!h->initialized)return COH_STATE;
    if(!n||!isfinite(x)||!isfinite(y)||x< -1||x>1||y< -1||y>1)return COH_INVALID;
    dx=x>.55f?1:x< -.55f?-1:0;dy=y>.55f?1:y< -.55f?-1:0;
    /* One direction per sample; stronger axis wins, ties choose horizontal. */
    if(fabsf(x)>=fabsf(y))dy=0;else dx=0;
    if(dx&&dx!=n->horizontal)s=coh_hud_action(h,dx>0?COH_UI_RIGHT:COH_UI_LEFT);
    else if(dy&&dy!=n->vertical)s=coh_hud_action(h,dy>0?COH_UI_DOWN:COH_UI_UP);
    n->horizontal=dx;n->vertical=dy;return s;
}
