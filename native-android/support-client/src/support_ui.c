#include "support_ui.h"
#include "../../engine/ui/gameplay/coh_hud_android.h"
#include "../../engine/ui/gameplay/coh_hud_atlas.h"
/* Generated at packaging time by engine/ui/gameplay/make_atlas.py, default
 * prefix coh_hud_font, font1/resource7. No TTF decode on the GL/audio thread. */
#include "support_font.h"
#include "support_tray.h"
#include "../../engine/ui/gameplay/coh_hud_axis_navigation.h"
#include <stdatomic.h>
#include <GLES3/gl3.h>
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct SupportUi {
    _Atomic uint64_t axes;_Atomic uint32_t axis_reset;uint32_t axis_seen;
    CohHudAxisNavigation axis;uint64_t prior_axis_actions,prior_axis_repeats;
    pthread_mutex_t mutex;CohHud hud;CohHudIme ime;CohHudState state;
    CohPresentation presentation;CohHudAxisNavigation presentation_axis;uint64_t presentation_sequence;
    CohPresentationCue presentation_cues[COH_PRESENTATION_QUEUE];size_t presentation_cue_count;
    CohHudGles gpu;CohHudGlesStats prior_gpu;uint32_t texture,tray[11];
    CohHudIntent history[COH_HUD_INTENTS];size_t history_count;
    uint64_t mock_ms,recharge_until[COH_HUD_POWERS];SupportUiStats stats;
};
static void utf8_copy(char *out,size_t capacity,const char *text){
    size_t n=strlen(text);if(n>=capacity)n=capacity-1;
    while(n&&((unsigned char)text[n]&0xc0u)==0x80u)n--;
    memcpy(out,text,n);out[n]=0;
}
static void message(SupportUi *u,const char *text){
    size_t slot;if(u->state.chat_count==COH_HUD_CHAT_LINES){
        memmove(u->state.chat,u->state.chat+1,(COH_HUD_CHAT_LINES-1)*sizeof(u->state.chat[0]));slot=COH_HUD_CHAT_LINES-1;
    }else slot=u->state.chat_count++;
    utf8_copy(u->state.chat[slot],sizeof(u->state.chat[slot]),text);
}
static void gpu_add(CohHudGlesStats *sum,const CohHudGlesStats *part){
    sum->frames+=part->frames;sum->quads+=part->quads;sum->draw_calls+=part->draw_calls;sum->bytes_uploaded+=part->bytes_uploaded;
    sum->rejected_frames+=part->rejected_frames;sum->gl_errors+=part->gl_errors;sum->preexisting_errors+=part->preexisting_errors;
    if(part->arena_bytes>sum->arena_bytes)sum->arena_bytes=part->arena_bytes;
    if(part->batch_high_water>sum->batch_high_water)sum->batch_high_water=part->batch_high_water;
}
static CohStatus record(SupportUi *u,CohStatus s){u->stats.last_status=(int)s;return s;}
static CohStatus update(SupportUi *u){u->state.revision++;return coh_hud_set_state(&u->hud,&u->state);}
static void presentation_state(SupportUi *u){
    CohPresentationState state;coh_presentation_mock_state(&state,&u->state);
    (void)coh_presentation_set_state(&u->presentation,&state);
}
static void presentation_drain(SupportUi *u){
    CohPresentationIntent intent;CohPresentationCue cue;char text[COH_UI_TEXT];
    while(coh_presentation_poll(&u->presentation,&intent)){
        u->stats.presentation_intents++;
        snprintf(text,sizeof text,"OFFLINE panel intent: kind %u, item %u",(unsigned)intent.kind,intent.id);message(u,text);
    }
    while(coh_presentation_poll_cue(&u->presentation,&cue)){
        u->stats.presentation_cues++;
        if(u->presentation_cue_count<COH_PRESENTATION_QUEUE)u->presentation_cues[u->presentation_cue_count++]=cue;
        else u->stats.presentation_cue_drops++;
    }
}
static CohStatus presentation_hit(SupportUi *u,uint32_t power){
    CohPresentationEvent event={0};event.sequence=++u->presentation_sequence;
    event.revision=u->presentation.state.revision;event.now_ms=u->mock_ms;
    event.actor_id=u->state.actor_id;event.target_id=u->state.target_id;event.power_id=power;
    event.kind=COH_PRESENTATION_IMPACT;event.amount=-12;event.damager_is_owned=1;
    event.animation_asset=1; /* Explicit offline binding to authenticated Huge/1_2punch; no impact audio asset available. */
    event.x=320;event.y=315;
    CohStatus s=coh_presentation_event(&u->presentation,&event);
    if(s==COH_OK){u->state.target_health=u->state.target_health>12?u->state.target_health-12:100;presentation_drain(u);}
    return s;
}
static void drain_intents(SupportUi *u){
    CohHudIntent e;char line[COH_UI_TEXT];
    while(coh_hud_poll(&u->hud,&e)){
        u->stats.intents_processed++;
        if(u->history_count==COH_HUD_INTENTS){
            memmove(u->history,u->history+1,(COH_HUD_INTENTS-1)*sizeof(u->history[0]));u->history_count--;u->stats.intent_history_drops++;
        }
        u->history[u->history_count++]=e;
        switch(e.kind){
        case COH_HUD_USE_POWER:
            if(e.slot<u->state.power_count){
                u->stats.power_uses++;u->stats.last_power=e.id;u->state.powers[e.slot].cooldown=1;
                u->recharge_until[e.slot]=u->mock_ms>UINT64_MAX-2500?UINT64_MAX:u->mock_ms+2500;
                snprintf(line,sizeof(line),"OFFLINE power intent: %u (local mock hit)",e.id);message(u,line);
                (void)presentation_hit(u,e.id);
            }break;
        case COH_HUD_SEND_CHAT:
            u->stats.chat_submits++;message(u,"OFFLINE chat submitted locally:");message(u,e.text);break;
        case COH_HUD_SELECT_CHARACTER:
            u->stats.character_selections++;u->stats.last_character=e.id;
            if(e.slot<u->state.character_count)utf8_copy(u->state.actor_name,sizeof(u->state.actor_name),u->state.characters[e.slot].name);
            u->state.show_character_select=0;presentation_state(u);
            message(u,"OFFLINE selection only; scene remains Huge/Wretch.");break;
        case COH_HUD_OPEN_CHARACTER_MENU:
            u->stats.menu_opens++;u->state.show_character_select=1;break;
        case COH_HUD_CLOSE_CHARACTER_MENU:
            u->stats.menu_closes++;u->state.show_character_select=0;break;
        case COH_HUD_TARGET:
            u->stats.target_clicks++;message(u,"OFFLINE target intent; no targeting protocol.");break;
        }
        snprintf(u->stats.last_intent,sizeof(u->stats.last_intent),"offline kind=%u id=%u slot=%u revision=%llu",(unsigned)e.kind,e.id,e.slot,(unsigned long long)e.revision);
        update(u);
    }
}
SupportUi *support_ui_create(void){
    static const char *powers[COH_HUD_POWERS]={"Brawl","Punch","Kick","Sprint","Jump","Rest","Power 7","Power 8","Power 9","Power 10"};
    static const char *characters[3]={"Offline Huge / Wretch","Offline Male choice","Offline Female choice"};
    SupportUi *u=calloc(1,sizeof(*u));size_t i;
    if(!u)return NULL;
    atomic_init(&u->axes,UINT64_MAX);atomic_init(&u->axis_reset,0);
    if(pthread_mutex_init(&u->mutex,NULL)!=0){free(u);return NULL;}
    if(coh_hud_atlas_validate(&coh_hud_font)!=COH_OK||coh_hud_init(&u->hud,coh_hud_atlas_glyph,&coh_hud_font)!=COH_OK){
        pthread_mutex_destroy(&u->mutex);free(u);return NULL;
    }
    if(coh_hud_set_tray_decoration(&u->hud,100,coh_hud_tray_numbers)!=COH_OK){
        pthread_mutex_destroy(&u->mutex);coh_hud_destroy(&u->hud);free(u);return NULL;
    }
    coh_hud_ime_init(&u->ime);u->state.actor_id=100;u->state.target_id=200;u->state.in_phase=1;
    strcpy(u->state.actor_name,"Offline Huge / Wretch");strcpy(u->state.target_name,"Mock target (offline)");
    u->state.health=85;u->state.max_health=100;u->state.absorb=15;u->state.endurance=75;u->state.max_endurance=100;
    u->state.target_health=60;u->state.target_max_health=100;u->state.power_count=COH_HUD_POWERS;
    for(i=0;i<COH_HUD_POWERS;i++){u->state.powers[i].id=1000+(uint32_t)i;u->state.powers[i].enabled=1;
        strcpy(u->state.powers[i].name,powers[i]);}
    u->state.character_count=3;for(i=0;i<3;i++){
        u->state.characters[i].id=500+(uint32_t)i;u->state.characters[i].enabled=1;strcpy(u->state.characters[i].name,characters[i]);
    }
    message(u,"OFFLINE HUD: native original-font rendering.");
    message(u,"D-pad/A, touch, chat/IME: local intents only.");
    message(u,"Character choices are data; scene stays Wretch.");
    if(coh_presentation_init(&u->presentation,coh_hud_atlas_glyph,&coh_hud_font)!=COH_OK){pthread_mutex_destroy(&u->mutex);coh_hud_destroy(&u->hud);free(u);return NULL;}
    u->stats.arena_bytes=sizeof(*u);record(u,update(u));presentation_state(u);return u;
}
void support_ui_destroy(SupportUi *u){
    if(!u)return;
    /* External owner has stopped/joined callbacks before this CPU destruction. */
    pthread_mutex_destroy(&u->mutex);coh_presentation_destroy(&u->presentation);coh_hud_destroy(&u->hud);free(u);
}
/* Lifecycle/input updates never wait for the HUD lock or a GL driver call. */
void support_ui_navigation(SupportUi *u,int active,float x,float y){
    if(!u||!isfinite(x)||!isfinite(y)||x< -1||x>1||y< -1||y>1)return;
    uint64_t value=UINT64_MAX;
    if(active){uint32_t a,b;memcpy(&a,&x,sizeof a);memcpy(&b,&y,sizeof b);value=((uint64_t)a<<32)|b;}
    atomic_store_explicit(&u->axes,value,memory_order_release);
    if(!active)atomic_fetch_add_explicit(&u->axis_reset,1,memory_order_release);
}
CohStatus support_ui_surface(SupportUi *u,uint32_t gen,int width,int height,CohHudInsets safe){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    s=coh_hud_surface(&u->hud,gen,(float)width,(float)height,safe);
    if(s==COH_OK)s=coh_presentation_surface(&u->presentation,gen,(float)width,(float)height,safe);
    record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
static CohStatus texture_resolve(void *context,uint32_t id,CohHudTexture *out){
    SupportUi *u=context;
    if(id==7&&u->texture){*out=(CohHudTexture){u->texture,1};return COH_OK;}
    for(unsigned i=0;i<11;i++)if(id==coh_hud_tray_images[i].resource&&u->tray[i]){*out=(CohHudTexture){u->tray[i],0};return COH_OK;}
    return COH_NOT_FOUND;
}
CohStatus support_ui_context_create(SupportUi *u,uint32_t gen){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    s=coh_hud_gles_create(&u->gpu,gen);
    if(s==COH_OK){
        glGenTextures(1,&u->texture);glBindTexture(GL_TEXTURE_2D,u->texture);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
        glTexImage2D(GL_TEXTURE_2D,0,GL_R8,COH_HUD_FONT_WIDTH,COH_HUD_FONT_HEIGHT,0,GL_RED,GL_UNSIGNED_BYTE,coh_hud_font_alpha);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        glGenTextures(11,u->tray);
        for(unsigned i=0;i<11;i++){
            const CohHudTrayImage *image=&coh_hud_tray_images[i];
            glBindTexture(GL_TEXTURE_2D,u->tray[i]);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,(GLsizei)image->width,(GLsizei)image->height,0,GL_RGBA,GL_UNSIGNED_BYTE,image->rgba);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        }
        glBindTexture(GL_TEXTURE_2D,0);
        if(!u->texture||glGetError()!=GL_NO_ERROR){if(u->texture)glDeleteTextures(1,&u->texture);
            glDeleteTextures(11,u->tray);memset(u->tray,0,sizeof u->tray);u->texture=0;coh_hud_gles_destroy(&u->gpu);s=COH_IO;}
    }
    record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
void support_ui_context_destroy(SupportUi *u){
    if(!u)return;
    pthread_mutex_lock(&u->mutex);gpu_add(&u->prior_gpu,&u->gpu.stats);coh_hud_gles_destroy(&u->gpu);
    if(u->texture)glDeleteTextures(1,&u->texture);
    glDeleteTextures(11,u->tray);memset(u->tray,0,sizeof u->tray);u->texture=0;
    coh_hud_surface_lost(&u->hud);coh_presentation_surface_lost(&u->presentation);u->stats.surface_losses++;pthread_mutex_unlock(&u->mutex);
}
void support_ui_context_lost(SupportUi *u){
    if(!u)return;
    pthread_mutex_lock(&u->mutex);gpu_add(&u->prior_gpu,&u->gpu.stats);coh_hud_gles_forget(&u->gpu);u->texture=0;memset(u->tray,0,sizeof u->tray);
    coh_hud_surface_lost(&u->hud);coh_presentation_surface_lost(&u->presentation);u->stats.surface_losses++;pthread_mutex_unlock(&u->mutex);
}
CohStatus support_ui_draw(SupportUi *u,int width,int height,uint32_t gen){
    CohStatus s;const CohUiDraw *draws;size_t count;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    s=coh_hud_build(&u->hud);
    if(s==COH_OK){draws=coh_hud_draws(&u->hud,gen,&count);s=draws?coh_hud_gles_draw(&u->gpu,width,height,gen,draws,count,texture_resolve,u):COH_STATE;}
    if(s==COH_OK)s=coh_presentation_build(&u->presentation);
    if(s==COH_OK){draws=coh_presentation_draws(&u->presentation,gen,&count);s=draws?coh_hud_gles_draw(&u->gpu,width,height,gen,draws,count,texture_resolve,u):COH_STATE;}
    record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_pointer(SupportUi *u,int action,uint32_t pointer,float x,float y,int *consumed){
    CohStatus s;int captured;
    if(consumed)*consumed=0;
    if(!u||!consumed)return COH_INVALID;
    pthread_mutex_lock(&u->mutex);
    if(u->presentation.visible){
        *consumed=1;
        switch(action){
        case 0:case 5:s=coh_presentation_touch(&u->presentation,COH_UI_TOUCH_DOWN,pointer,x,y);break;
        case 1:case 6:s=coh_presentation_touch(&u->presentation,COH_UI_TOUCH_UP,pointer,x,y);break;
        case 3:s=coh_presentation_touch(&u->presentation,COH_UI_TOUCH_CANCEL,pointer,x,y);break;
        case 2:s=COH_OK;break;default:s=COH_UNSUPPORTED;break;
        }
        presentation_drain(u);record(u,s);pthread_mutex_unlock(&u->mutex);return s;
    }
    captured=u->hud.ui.capture!=0;
    s=coh_hud_android_touch(&u->hud,action,pointer,x,y);
    /* Read before draining intents: activation may disable the clicked power
     * or change modal visibility, but that release still belongs to the HUD. */
    *consumed=captured||u->hud.ui.capture!=0;
    if(s==COH_OK)drain_intents(u);
    record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_touch(SupportUi *u,int action,uint32_t pointer,float x,float y){
    int consumed;return support_ui_pointer(u,action,pointer,x,y,&consumed);
}
CohStatus support_ui_key(SupportUi *u,int key,int action,int repeat,int shift){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    if(u->presentation.visible){
        CohUiAction mapped;int navigation=0;
        switch(key){case 19:mapped=COH_UI_UP;navigation=1;break;case 20:mapped=COH_UI_DOWN;navigation=1;break;
        case 21:mapped=COH_UI_LEFT;navigation=1;break;case 22:mapped=COH_UI_RIGHT;navigation=1;break;
        case 61:mapped=shift?COH_UI_PREVIOUS:COH_UI_NEXT;navigation=1;break;
        case 102:mapped=COH_UI_PREVIOUS;navigation=1;break;case 103:mapped=COH_UI_NEXT;navigation=1;break;
        case 23:case 96:case 66:mapped=COH_UI_ACTIVATE;break;case 4:case 97:case 111:mapped=COH_UI_CANCEL;break;
        default:pthread_mutex_unlock(&u->mutex);return COH_UNSUPPORTED;}
        s=(action==1||(!navigation&&repeat))?COH_OK:coh_presentation_action(&u->presentation,mapped);
        if(s==COH_NOT_FOUND)s=COH_OK;
        presentation_drain(u);record(u,s);pthread_mutex_unlock(&u->mutex);return s;
    }
    s=coh_hud_android_key(&u->hud,key,action,repeat,shift);if(s==COH_OK)drain_intents(u);record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_text(SupportUi *u,const char *text){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    s=coh_hud_ime_commit(&u->hud,&u->ime,text);record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_composing(SupportUi *u,const char *text){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    coh_ui_layout(&u->hud.ui);s=coh_hud_ime_composing(&u->hud,&u->ime,text);record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_submit(SupportUi *u){return support_ui_key(u,66,0,0,0);}
CohStatus support_ui_focus_chat(SupportUi *u){
    CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    s=record(u,coh_hud_focus(&u->hud,COH_HUD_BIND_CHAT_INPUT));pthread_mutex_unlock(&u->mutex);return s;
}
int support_ui_keyboard_requested(SupportUi *u){
    int result;if(!u)return 0;pthread_mutex_lock(&u->mutex);coh_ui_layout(&u->hud.ui);
    result=coh_hud_keyboard_requested(&u->hud);pthread_mutex_unlock(&u->mutex);return result;
}
CohStatus support_ui_tick_mock(SupportUi *u,uint64_t elapsed){
    size_t i;CohStatus s;if(!u)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    if(elapsed<u->mock_ms){record(u,COH_INVALID);pthread_mutex_unlock(&u->mutex);return COH_INVALID;}
    uint32_t reset=atomic_load_explicit(&u->axis_reset,memory_order_acquire);
    if(reset!=u->axis_seen){u->prior_axis_actions+=u->axis.actions;u->prior_axis_repeats+=u->axis.repeats;coh_hud_axis_reset(&u->axis);coh_hud_axis_reset(&u->presentation_axis);u->axis_seen=reset;}
    uint64_t axes=atomic_load_explicit(&u->axes,memory_order_acquire);
    if(axes!=UINT64_MAX){uint32_t a=(uint32_t)(axes>>32),b=(uint32_t)axes;float x,y;memcpy(&x,&a,sizeof x);memcpy(&y,&b,sizeof y);
        s=u->presentation.visible?coh_presentation_axis(&u->presentation,&u->presentation_axis,x,y,elapsed):coh_hud_axis_step(&u->hud,&u->axis,x,y,elapsed);
        if(s!=COH_OK){record(u,s);pthread_mutex_unlock(&u->mutex);return s;}drain_intents(u);presentation_drain(u);
    }
    u->mock_ms=elapsed;(void)coh_presentation_tick(&u->presentation,elapsed);u->state.health=80+(float)(elapsed%20000)/1000;
    u->state.endurance=55+(float)(elapsed%30000)/1000;
    for(i=0;i<u->state.power_count;i++)u->state.powers[i].cooldown=u->recharge_until[i]>elapsed?(float)(u->recharge_until[i]-elapsed)/2500.0f:0;
    s=record(u,update(u));pthread_mutex_unlock(&u->mutex);return s;
}
CohStatus support_ui_snapshot(SupportUi *u,SupportUiStats *out){
    const CohUiWidget *input;size_t i;if(!u||!out)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    *out=u->stats;out->axis_actions=u->prior_axis_actions+u->axis.actions;out->axis_repeats=u->prior_axis_repeats+u->axis.repeats;out->hud=u->hud.stats;out->widgets=u->hud.ui.stats;out->gpu=u->prior_gpu;gpu_add(&out->gpu,&u->gpu.stats);
    out->presentation=u->presentation.stats;out->presentation_visible=u->presentation.visible;out->presentation_tab=(uint32_t)u->presentation.tab;out->target_health=u->state.target_health;
    out->generation=u->gpu.generation;coh_ui_layout(&u->hud.ui);out->keyboard_requested=coh_hud_keyboard_requested(&u->hud);
    for(i=0;i<u->hud.ui.widget_count;i++)if(u->hud.ui.widgets[i].desc.binding==COH_HUD_BIND_CHAT_INPUT){
        input=u->hud.ui.widgets+i;memcpy(out->chat_input,input->text,sizeof(out->chat_input));break;
    }
    pthread_mutex_unlock(&u->mutex);return COH_OK;
}
int support_ui_poll_intent(SupportUi *u,CohHudIntent *out){
    if(!u||!out)return 0;
    pthread_mutex_lock(&u->mutex);if(!u->history_count){pthread_mutex_unlock(&u->mutex);return 0;}
    *out=u->history[0];memmove(u->history,u->history+1,(--u->history_count)*sizeof(u->history[0]));pthread_mutex_unlock(&u->mutex);return 1;
}

CohStatus support_ui_presentation(SupportUi *u,int action){
    CohStatus s;if(!u||action<0||action>1)return COH_INVALID;pthread_mutex_lock(&u->mutex);
    if(action==0){
        CohPresentationTab tab=u->presentation.visible?(CohPresentationTab)((u->presentation.tab+1)%COH_PRESENTATION_TABS):COH_PRESENTATION_DETAILS;
        presentation_state(u);coh_hud_axis_reset(&u->presentation_axis);(void)coh_hud_touch(&u->hud,COH_UI_TOUCH_CANCEL,u->hud.ui.capture_pointer,0,0);
        s=coh_presentation_show(&u->presentation,1,tab);
    }else{s=presentation_hit(u,1000);if(s==COH_OK)(void)update(u);}
    record(u,s);pthread_mutex_unlock(&u->mutex);return s;
}

int support_ui_poll_presentation_cue(SupportUi *u,CohPresentationCue *out){
    if(!u||!out)return 0;
    pthread_mutex_lock(&u->mutex);
    if(!u->presentation_cue_count){pthread_mutex_unlock(&u->mutex);return 0;}
    *out=u->presentation_cues[0];memmove(u->presentation_cues,u->presentation_cues+1,(--u->presentation_cue_count)*sizeof *out);
    pthread_mutex_unlock(&u->mutex);return 1;
}

void support_ui_preview_label(SupportUi *u,int male){
    if(!u)return;
    pthread_mutex_lock(&u->mutex);
    strcpy(u->state.actor_name,male?"Neutral Male costume (offline)":"Offline Huge / Wretch");
    (void)update(u);presentation_state(u);pthread_mutex_unlock(&u->mutex);
}
