#include "coh_hud_axis_navigation.h"
#include <math.h>
#include <string.h>
enum { NEUTRAL,LEFT,RIGHT,UP,DOWN };
void coh_hud_axis_reset(CohHudAxisNavigation *n){if(n)memset(n,0,sizeof(*n));}
static int selected(int held,float x,float y){
    float ax=fabsf(x),ay=fabsf(y),projected=0,competing=0;int candidate;
    if(fmaxf(ax,ay)<.55f)candidate=NEUTRAL;
    else if(ax>=ay)candidate=x<0?LEFT:RIGHT;
    else candidate=y<0?UP:DOWN;
    switch(held){
    case LEFT:projected=-x;competing=ay;break;
    case RIGHT:projected=x;competing=ay;break;
    case UP:projected=-y;competing=ax;break;
    case DOWN:projected=y;competing=ax;break;
    default:break;
    }
    /* Keep an engaged direction through the deadband and diagonal jitter. */
    if(held&&projected>=.35f&&(candidate==NEUTRAL||competing<=projected+.15f))return held;
    return candidate;
}
CohStatus coh_hud_axis_step(CohHud *h,CohHudAxisNavigation *n,float x,float y,uint64_t ms){
    int direction,edge,repeat;CohStatus status=COH_OK;CohUiAction action=COH_UI_LEFT;
    if(!h||!h->initialized)return COH_STATE;
    if(!n)return COH_INVALID;
    if(!isfinite(x)||!isfinite(y)||x< -1||x>1||y< -1||y>1||
       (n->clock_seen&&ms<n->last_sample_ms)){n->rejected++;return COH_INVALID;}
    direction=selected(n->direction,x,y);edge=direction!=n->direction;
    repeat=direction&&!edge&&ms-n->last_action_ms>=(n->repeating?110u:350u);
    if(direction&&(edge||repeat)){
        switch(direction){case LEFT:action=COH_UI_LEFT;break;case RIGHT:action=COH_UI_RIGHT;break;
        case UP:action=COH_UI_UP;break;case DOWN:action=COH_UI_DOWN;break;default:break;}
        status=coh_hud_action(h,action);
        if(status!=COH_OK&&status!=COH_NOT_FOUND){n->rejected++;return status;}
        n->actions++;if(repeat)n->repeats++;if(status==COH_NOT_FOUND)n->blocked++;
        n->last_action_ms=ms;n->repeating=repeat;
    }else if(!direction)n->repeating=0;
    n->direction=direction;n->clock_seen=1;n->last_sample_ms=ms;n->samples++;
    return COH_OK;
}
