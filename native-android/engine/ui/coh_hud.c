#include "coh_hud.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

enum { ROOT=1,STATUS=2,NAME=3,HEALTH_BG=4,HEALTH=5,ABSORB=6,HEALTH_TEXT=7,
       END_BG=8,ENDURANCE=9,END_TEXT=10,TARGET=11,TARGET_BAR=12,TARGET_TEXT=13,
       CHAT=14,CHAT_INPUT=15,TRAY=16,CHAR_MENU=17,SELECT=18,
       POWER_FIRST=32,POWER_ICON_FIRST=48,POWER_RECHARGE_FIRST=64,
       CHARACTER_FIRST=80,CHAT_FIRST=96,POWER_NUMBER_FIRST=112 };
#define SHOWN (COH_UI_VISIBLE|COH_UI_ENABLED)
#define BUTTON (SHOWN|COH_UI_FOCUSABLE)
static uint32_t blend(float t,uint32_t a,uint32_t b) {
    uint32_t r=0;unsigned shift;
    for(shift=0;shift<32;shift+=8){uint32_t x=(a>>shift)&255u,y=(b>>shift)&255u;
        uint32_t d=(uint32_t)((float)(x>y?x-y:y-x)*t);
        r|=((x>y?x-d:x+d)&255u)<<shift;
    }
    return r;
}
uint32_t coh_hud_health_color(int phase,float p) {
    if(!phase)return 0x888888ffu;
    if(p>.60f)return 0x50eb34ffu;
    if(p>.40f)return blend((p-.40f)/(.60f-.40f),0xebff20ffu,0x50eb34ffu);
    if(p>.20f)return blend((p-.20f)/(.40f-.20f),0xf72200ffu,0xebff20ffu);
    return 0xf72200ffu;
}
uint32_t coh_hud_endurance_color(float p) {
    if(p>.70f)return 0x0005ffffu;
    if(p>.30f)return blend((p-.30f)/(.70f-.30f),0x000588ffu,0x0005ffffu);
    return 0x000588ffu;
}
static CohStatus add(CohHud *h,uint32_t id,uint32_t parent,uint32_t binding,CohUiKind kind,
                     uint32_t flags,CohUiRect rect,uint32_t color,const char *text) {
    CohUiDesc d;memset(&d,0,sizeof(d));d.id=id;d.parent=parent;d.binding=binding;d.kind=kind;
    d.flags=flags;d.rect=rect;d.color=color;d.text_color=0xffffffffu;d.font_id=1;d.font_size=16;
    return coh_ui_add(&h->ui,&d,text);
}
#define ADD(id,parent,binding,kind,flags,x,y,w,z,color,text) do { \
    CohStatus a_=add(h,id,parent,binding,kind,flags,(CohUiRect){x,y,w,z},color,text); \
    if(a_!=COH_OK){coh_hud_destroy(h);return a_;} } while(0)
CohStatus coh_hud_init(CohHud *h,CohUiGlyphFn glyph,void *context) {
    size_t i;if(!h)return COH_INVALID;memset(h,0,sizeof(*h));
    coh_ui_init(&h->ui,COH_UI_SCALE_FIT,glyph,context);
    ADD(ROOT,0,0,COH_UI_PANEL,SHOWN,0,0,1024,768,0x00000000u,"");
    ADD(STATUS,ROOT,0,COH_UI_WINDOW,SHOWN,12,12,310,102,0x102c40e8u,"");
    ADD(NAME,STATUS,0,COH_UI_LABEL,SHOWN,10,4,292,20,0,"Native character");
    ADD(HEALTH_BG,STATUS,0,COH_UI_PANEL,SHOWN,10,30,290,24,0x080e16ffu,"");
    ADD(HEALTH,STATUS,COH_HUD_BIND_HEALTH,COH_UI_PROGRESS,SHOWN,10,30,290,24,0x50eb34ffu,"");
    ADD(ABSORB,STATUS,0,COH_UI_PROGRESS,SHOWN,10,30,290,24,0x888888ffu,"");
    ADD(HEALTH_TEXT,STATUS,0,COH_UI_LABEL,SHOWN,14,32,282,20,0,"HP 0 / 0");
    ADD(END_BG,STATUS,0,COH_UI_PANEL,SHOWN,10,62,290,24,0x080e16ffu,"");
    ADD(ENDURANCE,STATUS,COH_HUD_BIND_ENDURANCE,COH_UI_PROGRESS,SHOWN,10,62,290,24,0x0005ffffu,"");
    ADD(END_TEXT,STATUS,0,COH_UI_LABEL,SHOWN,14,64,282,20,0,"END 0 / 0");
    ADD(TARGET,ROOT,COH_HUD_BIND_TARGET,COH_UI_BUTTON,0,656,12,356,90,0x301d2ce8u,"");
    ADD(TARGET_BAR,TARGET,0,COH_UI_PROGRESS,SHOWN,10,36,336,24,0xf72200ffu,"");
    ADD(TARGET_TEXT,TARGET,0,COH_UI_LABEL,SHOWN,14,38,328,20,0,"");
    ADD(CHAT,ROOT,0,COH_UI_WINDOW,SHOWN,12,450,480,222,0x10202cc8u,"");
    for(i=0;i<COH_HUD_CHAT_LINES;i++){
        ADD(CHAT_FIRST+(uint32_t)i,CHAT,COH_HUD_BIND_CHAT_FIRST+(uint32_t)i,COH_UI_LABEL,SHOWN,8,8+(float)i*20,464,20,0,"");
    }
    ADD(CHAT_INPUT,CHAT,COH_HUD_BIND_CHAT_INPUT,COH_UI_INPUT,BUTTON,8,180,464,30,0x0b121eeeu,"");
    ADD(TRAY,ROOT,0,COH_UI_WINDOW,SHOWN,222,682,790,74,0x102c40e8u,"");
    for(i=0;i<COH_HUD_POWERS;i++){
        ADD(POWER_FIRST+(uint32_t)i,TRAY,COH_HUD_BIND_POWER_FIRST+(uint32_t)i,COH_UI_BUTTON,0,8+(float)i*78,8,72,58,0x31536bffu,"");
        ADD(POWER_ICON_FIRST+(uint32_t)i,POWER_FIRST+(uint32_t)i,0,COH_UI_ICON,0,9,0,54,54,0xffffffffu,"");
        ADD(POWER_RECHARGE_FIRST+(uint32_t)i,POWER_FIRST+(uint32_t)i,0,COH_UI_PROGRESS,SHOWN,0,52,72,6,0x66cceeffu,"");
        ADD(POWER_NUMBER_FIRST+(uint32_t)i,POWER_FIRST+(uint32_t)i,0,COH_UI_ICON,0,2,40,(i==1||i==5)?6:7,9,0xffffffffu,"");
    }
    ADD(CHAR_MENU,ROOT,COH_HUD_BIND_CHARACTER_MENU,COH_UI_BUTTON,BUTTON,12,682,196,36,0x31536bffu,"Characters");
    ADD(SELECT,ROOT,0,COH_UI_WINDOW,0,336,142,352,294,0x102c40f8u,"Select character");
    for(i=0;i<COH_HUD_CHARACTERS;i++){
        ADD(CHARACTER_FIRST+(uint32_t)i,SELECT,COH_HUD_BIND_CHARACTER_FIRST+(uint32_t)i,COH_UI_BUTTON,0,12,32+(float)i*32,328,28,0x31536bffu,"");
    }
    h->initialized=1;h->stats.arena_bytes=sizeof(*h);return COH_OK;
}
void coh_hud_destroy(CohHud *h){if(h)memset(h,0,sizeof(*h));}
static int text_valid(const char *s,size_t cap) {
    size_t i;for(i=0;i<cap;i++)if(!s[i])return coh_ui_utf8(s,1,NULL)==COH_OK;
    return 0;
}
static int number(float x){return isfinite(x)&&x>=0&&x<=1000000000.0f;}
static int state_valid(const CohHudState *s){
    size_t i,j;if(!s||s->power_count>COH_HUD_POWERS||s->character_count>COH_HUD_CHARACTERS||s->chat_count>COH_HUD_CHAT_LINES||
       !text_valid(s->actor_name,sizeof(s->actor_name))||!text_valid(s->target_name,sizeof(s->target_name))||
       !number(s->health)||!number(s->max_health)||!number(s->absorb)||!number(s->endurance)||!number(s->max_endurance)||
       !number(s->target_health)||!number(s->target_max_health)||s->health>s->max_health||s->endurance>s->max_endurance||
       s->target_health>s->target_max_health)return 0;
    for(i=0;i<s->power_count;i++){
        const CohHudPower *p=&s->powers[i];
        if(!p->id||!text_valid(p->name,sizeof(p->name))||!isfinite(p->cooldown)||p->cooldown<0||p->cooldown>1)return 0;
        for(j=0;j<i;j++)if(s->powers[j].id==p->id)return 0;
    }
    for(i=0;i<s->character_count;i++){
        if(!s->characters[i].id||!text_valid(s->characters[i].name,sizeof(s->characters[i].name)))return 0;
        for(j=0;j<i;j++)if(s->characters[j].id==s->characters[i].id)return 0;
    }
    for(i=0;i<s->chat_count;i++)if(!text_valid(s->chat[i],sizeof(s->chat[i])))return 0;
    return 1;
}
static CohUiWidget *widget(CohHud *h,uint32_t id){
    size_t i;for(i=0;i<h->ui.widget_count;i++)if(h->ui.widgets[i].desc.id==id)return h->ui.widgets+i;
    return NULL;
}
static float ratio(float current,float max){return max>0?current/max:0;}
CohStatus coh_hud_set_state(CohHud *h,const CohHudState *s){
    size_t i;char text[COH_UI_TEXT];float total;
    if(!h||!h->initialized)return COH_STATE;
    if(!state_valid(s)){h->stats.rejected_states++;return COH_INVALID;}
    /* All following operations are fixed-bound nonfailing updates to initialized widgets. */
    h->state=*s;
    coh_ui_set_text(&h->ui,NAME,s->actor_name);
    total=s->max_health+s->absorb;
    coh_ui_bind_value(&h->ui,COH_HUD_BIND_HEALTH,ratio(s->health+s->absorb,total));
    widget(h,HEALTH)->desc.color=coh_hud_health_color(s->in_phase,ratio(s->health,s->max_health));
    widget(h,ABSORB)->value=ratio(s->absorb,total);
    snprintf(text,sizeof(text),"HP %.0f / %.0f (+%.0f)",(double)s->health,(double)s->max_health,(double)s->absorb);
    coh_ui_set_text(&h->ui,HEALTH_TEXT,text);
    coh_ui_bind_value(&h->ui,COH_HUD_BIND_ENDURANCE,ratio(s->endurance,s->max_endurance));
    widget(h,ENDURANCE)->desc.color=coh_hud_endurance_color(ratio(s->endurance,s->max_endurance));
    snprintf(text,sizeof(text),"END %.0f / %.0f",(double)s->endurance,(double)s->max_endurance);
    coh_ui_set_text(&h->ui,END_TEXT,text);
    coh_ui_set_flags(&h->ui,TARGET,s->target_id?(s->show_character_select?COH_UI_VISIBLE:BUTTON):0);
    coh_ui_set_text(&h->ui,TARGET,s->target_name);
    widget(h,TARGET_BAR)->value=ratio(s->target_health,s->target_max_health);
    snprintf(text,sizeof(text),"HP %.0f / %.0f",(double)s->target_health,(double)s->target_max_health);
    coh_ui_set_text(&h->ui,TARGET_TEXT,text);
    for(i=0;i<COH_HUD_POWERS;i++){
        int present=i<s->power_count;
        const CohHudPower *p=&s->powers[i];
        uint32_t flags=present?(COH_UI_VISIBLE|COH_UI_FOCUSABLE):0;
        if(present&&p->enabled&&p->cooldown==0&&!s->show_character_select)flags|=COH_UI_ENABLED;
        coh_ui_set_flags(&h->ui,POWER_FIRST+(uint32_t)i,flags);
        coh_ui_set_text(&h->ui,POWER_FIRST+(uint32_t)i,present?p->name:"");
        /* An image widget paints text after its image, keeping labels readable. */
        widget(h,POWER_FIRST+(uint32_t)i)->desc.kind=present&&p->icon?COH_UI_ICON:COH_UI_BUTTON;
        widget(h,POWER_FIRST+(uint32_t)i)->desc.resource_id=present?p->icon:0;
        widget(h,POWER_RECHARGE_FIRST+(uint32_t)i)->value=present?p->cooldown:0;
        widget(h,POWER_ICON_FIRST+(uint32_t)i)->desc.resource_id=h->tray_ring;
        coh_ui_set_flags(&h->ui,POWER_ICON_FIRST+(uint32_t)i,present&&h->tray_ring?SHOWN:0);
        widget(h,POWER_NUMBER_FIRST+(uint32_t)i)->desc.resource_id=h->tray_numbers[i];
        coh_ui_set_flags(&h->ui,POWER_NUMBER_FIRST+(uint32_t)i,present&&h->tray_numbers[i]?SHOWN:0);
    }
    coh_ui_set_flags(&h->ui,SELECT,s->show_character_select?SHOWN:0);
    coh_ui_set_flags(&h->ui,CHAT_INPUT,s->show_character_select?COH_UI_VISIBLE:BUTTON);
    coh_ui_set_flags(&h->ui,CHAR_MENU,s->show_character_select?COH_UI_VISIBLE:BUTTON);
    for(i=0;i<COH_HUD_CHARACTERS;i++){
        int present=i<s->character_count;
        coh_ui_set_flags(&h->ui,CHARACTER_FIRST+(uint32_t)i,present?(COH_UI_VISIBLE|COH_UI_FOCUSABLE|(s->characters[i].enabled?COH_UI_ENABLED:0)):0);
        coh_ui_set_text(&h->ui,CHARACTER_FIRST+(uint32_t)i,present?s->characters[i].name:"");
    }
    for(i=0;i<COH_HUD_CHAT_LINES;i++)coh_ui_set_text(&h->ui,CHAT_FIRST+(uint32_t)i,i<s->chat_count?s->chat[i]:"");
    h->stats.state_updates++;return COH_OK;
}
CohStatus coh_hud_set_skin(CohHud *h,const CohHudSkin *skin){
    size_t i;uint32_t ids[4]={STATUS,TRAY,CHAT,SELECT},resources[4];
    if(!h||!h->initialized)return COH_STATE;
    if(!skin||!skin->font)return COH_INVALID;
    resources[0]=skin->status_frame;resources[1]=skin->tray_frame;
    resources[2]=skin->chat_frame;resources[3]=skin->character_frame;
    for(i=0;i<h->ui.widget_count;i++)h->ui.widgets[i].desc.font_id=skin->font;
    for(i=0;i<4;i++){
        CohUiWidget *w=widget(h,ids[i]);w->desc.resource_id=resources[i];
        w->desc.kind=resources[i]?COH_UI_ICON:COH_UI_WINDOW;
    }
    /* Public setter invalidates the retained drawlist after direct descriptor edits. */
    return coh_ui_set_text(&h->ui,NAME,h->state.actor_name);
}
CohStatus coh_hud_set_tray_decoration(CohHud *h,uint32_t ring,const uint32_t numbers[COH_HUD_POWERS]){
    uint32_t copy[COH_HUD_POWERS];
    if(!h||!h->initialized)return COH_STATE;
    if(!numbers)return COH_INVALID;
    memcpy(copy,numbers,sizeof(copy));h->tray_ring=ring;memcpy(h->tray_numbers,copy,sizeof(copy));
    return coh_hud_set_state(h,&h->state);
}
CohStatus coh_hud_surface(CohHud *h,uint32_t gen,float width,float height,CohHudInsets safe){
    CohStatus s;
    if(!h||!h->initialized)return COH_STATE;
    if(!isfinite(width)||!isfinite(height)||!isfinite(safe.left)||!isfinite(safe.top)||!isfinite(safe.right)||!isfinite(safe.bottom)||
       width>32768||height>32768||safe.left<0||safe.top<0||safe.right<0||safe.bottom<0||
       width-safe.left-safe.right<1||height-safe.top-safe.bottom<1)return COH_INVALID;
    s=coh_ui_surface(&h->ui,gen,width-safe.left-safe.right,height-safe.top-safe.bottom);
    if(s!=COH_OK)return s;
    h->surface_width=width;h->surface_height=height;h->insets=safe;h->stats.surface_recreates++;return COH_OK;
}
void coh_hud_surface_lost(CohHud *h){if(h&&h->initialized){coh_ui_surface_lost(&h->ui);h->stats.surface_losses++;}}
CohStatus coh_hud_build(CohHud *h){
    size_t i;CohStatus s;if(!h||!h->initialized)return COH_STATE;s=coh_ui_build(&h->ui);if(s!=COH_OK)return s;
    for(i=0;i<h->ui.draw_count;i++){
        CohUiDraw *d=h->ui.draws+i;d->rect.x+=h->insets.left;d->rect.y+=h->insets.top;
        d->clip.x+=h->insets.left;d->clip.y+=h->insets.top;
    }
    h->stats.builds++;return COH_OK;
}
const CohUiDraw *coh_hud_draws(const CohHud *h,uint32_t generation,size_t *count){
    if(count)*count=0;
    if(!h||!h->initialized||!coh_ui_drawlist_valid(&h->ui,generation))return NULL;
    if(count)*count=h->ui.draw_count;
    return h->ui.draws;
}
static CohStatus room(CohHud *h){
    if(h->intent_count==COH_HUD_INTENTS){h->stats.intent_limit_hits++;return COH_LIMIT;}return COH_OK;
}
static void emit(CohHud *h,CohHudIntentKind kind,uint32_t id,uint32_t slot,const char *text){
    CohHudIntent *e=&h->intents[h->intent_count++];memset(e,0,sizeof(*e));e->kind=kind;
    e->revision=h->state.revision;e->actor_id=h->state.actor_id;e->id=id;e->slot=slot;
    if(text)memcpy(e->text,text,strlen(text)+1);
    h->stats.intents_emitted++;if(h->intent_count>h->stats.intent_high_water)h->stats.intent_high_water=h->intent_count;
}
static CohStatus drain(CohHud *h){
    CohUiEvent e;while(coh_ui_poll(&h->ui,&e)){
        if(e.kind==COH_UI_EVENT_SUBMIT&&e.binding==COH_HUD_BIND_CHAT_INPUT){
            const CohUiWidget *w=coh_ui_widget(&h->ui,CHAT_INPUT);
            if(w&&w->text[0]){if(room(h)!=COH_OK)return COH_LIMIT;
                emit(h,COH_HUD_SEND_CHAT,0,0,w->text);coh_ui_set_text(&h->ui,CHAT_INPUT,"");}
        }else if(e.kind==COH_UI_EVENT_ACTIVATE){
            if(room(h)!=COH_OK)return COH_LIMIT;
            if(e.binding>=COH_HUD_BIND_POWER_FIRST&&e.binding<COH_HUD_BIND_POWER_FIRST+COH_HUD_POWERS){
                uint32_t slot=e.binding-COH_HUD_BIND_POWER_FIRST;
                if(slot<h->state.power_count)emit(h,COH_HUD_USE_POWER,h->state.powers[slot].id,slot,NULL);
            }else if(e.binding>=COH_HUD_BIND_CHARACTER_FIRST&&e.binding<COH_HUD_BIND_CHARACTER_FIRST+COH_HUD_CHARACTERS){
                uint32_t slot=e.binding-COH_HUD_BIND_CHARACTER_FIRST;
                if(slot<h->state.character_count)emit(h,COH_HUD_SELECT_CHARACTER,h->state.characters[slot].id,slot,NULL);
            }else if(e.binding==COH_HUD_BIND_CHARACTER_MENU)emit(h,COH_HUD_OPEN_CHARACTER_MENU,0,0,NULL);
            else if(e.binding==COH_HUD_BIND_TARGET)emit(h,COH_HUD_TARGET,h->state.target_id,0,NULL);
        }
    }return COH_OK;
}
static CohStatus finish(CohHud *h,CohStatus s){
    if(s!=COH_OK)return s;
    s=drain(h);if(s!=COH_OK)return s;
    return coh_ui_layout(&h->ui);
}
CohStatus coh_hud_touch(CohHud *h,CohUiTouch action,uint32_t pointer,float x,float y){
    if(!h||!h->initialized)return COH_STATE;
    if(room(h)!=COH_OK&&action!=COH_UI_TOUCH_CANCEL)return COH_LIMIT;
    return finish(h,coh_ui_touch(&h->ui,action,pointer,x-h->insets.left,y-h->insets.top));
}
CohStatus coh_hud_action(CohHud *h,CohUiAction action){
    if(!h||!h->initialized)return COH_STATE;
    if(room(h)!=COH_OK&&action!=COH_UI_CANCEL)return COH_LIMIT;
    if(action==COH_UI_CANCEL&&h->state.show_character_select){
        if(room(h)!=COH_OK)return COH_LIMIT;
        emit(h,COH_HUD_CLOSE_CHARACTER_MENU,0,0,NULL);
    }
    return finish(h,coh_ui_action(&h->ui,action));
}
CohStatus coh_hud_text_commit(CohHud *h,const char *text){
    if(!h||!h->initialized)return COH_STATE;
    return finish(h,coh_ui_text_commit(&h->ui,text));
}
CohStatus coh_hud_focus(CohHud *h,uint32_t binding){
    size_t i;if(!h||!h->initialized)return COH_STATE;
    if(!binding)return finish(h,coh_ui_focus(&h->ui,0));
    for(i=0;i<h->ui.widget_count;i++)if(h->ui.widgets[i].desc.binding==binding)
        return finish(h,coh_ui_focus(&h->ui,h->ui.widgets[i].desc.id));
    return COH_NOT_FOUND;
}
int coh_hud_keyboard_requested(const CohHud *h){return h&&h->initialized&&coh_ui_keyboard_requested(&h->ui);}
int coh_hud_poll(CohHud *h,CohHudIntent *e){
    if(!h||!e||!h->intent_count)return 0;
    *e=h->intents[0];
    memmove(h->intents,h->intents+1,(--h->intent_count)*sizeof(h->intents[0]));return 1;
}
