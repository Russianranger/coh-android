#include "coh_presentation.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

enum { ROOT=1,PANEL=2,TITLE=3,CLOSE=4,FOOTER=5,TAB=10,DETAIL=20,
       ROW=40,ROW_DETAIL=50,ROW_PROGRESS=60,ROW_ICON=70,EFFECT=80,ROW_NAME=90 };
#define SHOWN (COH_UI_VISIBLE|COH_UI_ENABLED)
#define BUTTON (SHOWN|COH_UI_FOCUSABLE)
static const char *tabs[COH_PRESENTATION_TABS]={"Details","Inventory","Enhance","Missions","Contacts"};
static CohUiWidget *widget(CohPresentation *p,uint32_t id){
    size_t i;for(i=0;i<p->ui.widget_count;i++)if(p->ui.widgets[i].desc.id==id)return p->ui.widgets+i;
    return NULL;
}
static CohStatus add(CohPresentation *p,uint32_t id,uint32_t parent,CohUiKind kind,
                     uint32_t flags,CohUiRect rect,uint32_t color,const char *text){
    CohUiDesc d;memset(&d,0,sizeof(d));d.id=id;d.parent=parent;d.binding=id;d.kind=kind;
    d.flags=flags;d.rect=rect;d.color=color;d.text_color=0xffffffffu;d.font_id=1;d.font_size=15;
    return coh_ui_add(&p->ui,&d,text);
}
#define ADD(id,parent,kind,flags,x,y,w,h,color,text) do { \
    CohStatus s_=add(p,id,parent,kind,flags,(CohUiRect){x,y,w,h},color,text); \
    if(s_!=COH_OK){coh_presentation_destroy(p);return s_;} } while(0)
CohStatus coh_presentation_init(CohPresentation *p,CohUiGlyphFn glyph,void *ctx){
    size_t i;if(!p)return COH_INVALID;memset(p,0,sizeof(*p));
    coh_ui_init(&p->ui,COH_UI_SCALE_FIT,glyph,ctx);
    ADD(ROOT,0,COH_UI_PANEL,SHOWN,0,0,1024,768,0,"");
    ADD(PANEL,ROOT,COH_UI_WINDOW,0,504,124,508,536,0x102c40f5u,"");
    ADD(TITLE,PANEL,COH_UI_LABEL,SHOWN,12,8,420,24,0,"OFFLINE PRESENTATION");
    ADD(CLOSE,PANEL,COH_UI_BUTTON,BUTTON,454,6,42,30,0x31536bffu,"Close");
    for(i=0;i<COH_PRESENTATION_TABS;i++){
        ADD(TAB+(uint32_t)i,PANEL,COH_UI_BUTTON,BUTTON,12+(float)i*98,40,94,30,0x31536bffu,tabs[i]);
    }
    for(i=0;i<6;i++){
        ADD(DETAIL+(uint32_t)i,PANEL,COH_UI_LABEL,SHOWN,14,92+(float)i*42,480,36,0,"");
    }
    for(i=0;i<COH_PRESENTATION_ROWS;i++){
        ADD(ROW+(uint32_t)i,PANEL,COH_UI_BUTTON,0,12,84+(float)i*49,484,45,0x203e54ffu,"");
        ADD(ROW_ICON+(uint32_t)i,ROW+(uint32_t)i,COH_UI_ICON,0,3,3,32,32,0xffffffffu,"");
        ADD(ROW_NAME+(uint32_t)i,ROW+(uint32_t)i,COH_UI_LABEL,SHOWN,5,0,472,23,0,"");
        ADD(ROW_DETAIL+(uint32_t)i,ROW+(uint32_t)i,COH_UI_LABEL,SHOWN,5,23,472,19,0,"");
        ADD(ROW_PROGRESS+(uint32_t)i,ROW+(uint32_t)i,COH_UI_PROGRESS,SHOWN,0,43,484,2,0x00deffffu,"");
    }
    ADD(FOOTER,PANEL,COH_UI_LABEL,SHOWN,12,494,484,30,0,"A/Touch: inspect  |  B: close  |  Mock only");
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++){
        ADD(EFFECT+(uint32_t)i,ROOT,COH_UI_LABEL,0,0,0,160,32,0,"");
        widget(p,EFFECT+(uint32_t)i)->desc.font_size=24;
    }
    p->initialized=1;p->stats.arena_bytes=sizeof(*p);return COH_OK;
}
void coh_presentation_destroy(CohPresentation *p){if(p)memset(p,0,sizeof(*p));}
static int valid_text(const char *s,size_t cap){
    size_t i;for(i=0;i<cap;i++)if(!s[i])return coh_ui_utf8(s,1,NULL)==COH_OK;return 0;
}
static int valid_state(const CohPresentationState *s){
    size_t i,j,k;if(!s||!s->actor_id||s->level>1000||!valid_text(s->name,sizeof(s->name))||
       !valid_text(s->archetype,sizeof(s->archetype))||!valid_text(s->origin,sizeof(s->origin))||
       !valid_text(s->description,sizeof(s->description)))return 0;
    for(i=0;i<4;i++){
        if(s->counts[i]>COH_PRESENTATION_ROWS)return 0;
        for(j=0;j<s->counts[i];j++){
            const CohPresentationRow *r=&s->rows[i][j];
            if(!r->id||!valid_text(r->name,sizeof(r->name))||!valid_text(r->detail,sizeof(r->detail))||
               !isfinite(r->progress)||r->progress<0||r->progress>1||
               (r->enabled!=0&&r->enabled!=1)||(r->completed!=0&&r->completed!=1))return 0;
            for(k=0;k<j;k++)if(s->rows[i][k].id==r->id)return 0;
        }
    }
    return 1;
}
static void refresh(CohPresentation *p){
    size_t i;char text[COH_UI_TEXT];
    coh_ui_set_flags(&p->ui,PANEL,p->visible?SHOWN:0);
    for(i=0;i<COH_PRESENTATION_TABS;i++)widget(p,TAB+(uint32_t)i)->desc.color=
        i==(size_t)p->tab?0x276f93ffu:0x31536bffu;
    for(i=0;i<6;i++)coh_ui_set_flags(&p->ui,DETAIL+(uint32_t)i,p->tab==COH_PRESENTATION_DETAILS?SHOWN:0);
    snprintf(text,sizeof(text),"Name: %s",p->state.name);coh_ui_set_text(&p->ui,DETAIL,text);
    snprintf(text,sizeof(text),"Archetype: %s",p->state.archetype);coh_ui_set_text(&p->ui,DETAIL+1,text);
    snprintf(text,sizeof(text),"Origin: %s",p->state.origin);coh_ui_set_text(&p->ui,DETAIL+2,text);
    snprintf(text,sizeof(text),"Level: %u   Influence: %llu",p->state.level,(unsigned long long)p->state.influence);
    coh_ui_set_text(&p->ui,DETAIL+3,text);coh_ui_set_text(&p->ui,DETAIL+4,p->state.description);
    coh_ui_set_text(&p->ui,DETAIL+5,"Local copied demo state; inspect actions only.");
    for(i=0;i<COH_PRESENTATION_ROWS;i++){
        const CohPresentationRow *r=NULL;
        if(p->tab>COH_PRESENTATION_DETAILS&&i<p->state.counts[p->tab-1])r=&p->state.rows[p->tab-1][i];
        coh_ui_set_flags(&p->ui,ROW+(uint32_t)i,r?(COH_UI_VISIBLE|COH_UI_FOCUSABLE|(r->enabled?COH_UI_ENABLED:0)):0);
        coh_ui_set_text(&p->ui,ROW_NAME+(uint32_t)i,r?r->name:"");
        coh_ui_set_rect(&p->ui,ROW_NAME+(uint32_t)i,(CohUiRect){r&&r->icon?40:5,0,r&&r->icon?437:472,23});
        coh_ui_set_rect(&p->ui,ROW_DETAIL+(uint32_t)i,(CohUiRect){r&&r->icon?40:5,23,r&&r->icon?437:472,19});
        coh_ui_set_text(&p->ui,ROW_DETAIL+(uint32_t)i,r?r->detail:"");
        widget(p,ROW_DETAIL+(uint32_t)i)->desc.text_color=r&&r->completed?
            (p->tab==COH_PRESENTATION_CONTACTS?0x00ff33ffu:0x00ff44ffu):
            (p->tab==COH_PRESENTATION_MISSIONS?0x00deffffu:0xffffffffu);
        widget(p,ROW_PROGRESS+(uint32_t)i)->value=r?r->progress:0;
        widget(p,ROW_ICON+(uint32_t)i)->desc.resource_id=r?r->icon:0;
        coh_ui_set_flags(&p->ui,ROW_ICON+(uint32_t)i,r&&r->icon?SHOWN:0);
        /* Original icon identities remain explicit and optional. With one present,
         * indent text so no label is painted on top of authenticated art. */
        widget(p,ROW+(uint32_t)i)->desc.text_color=0xffffffffu;
    }
}
CohStatus coh_presentation_set_state(CohPresentation *p,const CohPresentationState *s){
    if(!p||!p->initialized)return COH_STATE;
    if(!valid_state(s)||(p->has_state&&s->actor_id==p->state.actor_id&&s->revision<p->state.revision)){
        p->stats.rejected_states++;return COH_INVALID;
    }
    if(p->has_state&&(s->actor_id!=p->state.actor_id||s->revision!=p->state.revision))
        coh_ui_touch(&p->ui,COH_UI_TOUCH_CANCEL,p->ui.capture_pointer,0,0);
    if(p->has_state&&s->actor_id!=p->state.actor_id){
        p->intent_count=p->cue_count=0;memset(p->effects,0,sizeof(p->effects));p->last_sequence=0;
        for(size_t i=0;i<COH_PRESENTATION_EFFECTS;i++)coh_ui_set_flags(&p->ui,EFFECT+(uint32_t)i,0);
        coh_ui_action(&p->ui,COH_UI_CANCEL); /* release old touch capture */
    }
    p->state=*s;p->has_state=1;refresh(p);p->stats.snapshots++;return COH_OK;
}
CohStatus coh_presentation_show(CohPresentation *p,int visible,CohPresentationTab tab){
    if(!p||!p->initialized)return COH_STATE;
    if((visible!=0&&visible!=1)||tab<0||tab>=COH_PRESENTATION_TABS)return COH_INVALID;
    p->visible=visible;p->tab=tab;refresh(p);
    if(!visible){coh_ui_action(&p->ui,COH_UI_CANCEL);coh_ui_focus(&p->ui,0);}
    if(p->ui.surface_ready){coh_ui_layout(&p->ui);if(visible)coh_ui_focus(&p->ui,TAB+(uint32_t)tab);}
    {CohUiEvent ignored;while(coh_ui_poll(&p->ui,&ignored)){}}
    return COH_OK;
}
CohStatus coh_presentation_surface(CohPresentation *p,uint32_t gen,float w,float h,CohHudInsets safe){
    CohStatus s;if(!p||!p->initialized)return COH_STATE;
    if(!isfinite(w)||!isfinite(h)||w>32768||h>32768||!isfinite(safe.left)||!isfinite(safe.top)||
       !isfinite(safe.right)||!isfinite(safe.bottom)||safe.left<0||safe.right<0||safe.top<0||safe.bottom<0||
       w-safe.left-safe.right<1||h-safe.top-safe.bottom<1)return COH_INVALID;
    s=coh_ui_surface(&p->ui,gen,w-safe.left-safe.right,h-safe.top-safe.bottom);
    if(s==COH_OK)p->insets=safe;
    return s;
}
void coh_presentation_surface_lost(CohPresentation *p){
    if(p&&p->initialized){coh_ui_surface_lost(&p->ui);p->stats.surface_losses++;}
}
CohStatus coh_presentation_build(CohPresentation *p){
    size_t i;CohStatus s;if(!p||!p->initialized)return COH_STATE;
    s=coh_ui_build(&p->ui);if(s!=COH_OK)return s;
    for(i=0;i<p->ui.draw_count;i++){
        p->ui.draws[i].rect.x+=p->insets.left;p->ui.draws[i].rect.y+=p->insets.top;
        p->ui.draws[i].clip.x+=p->insets.left;p->ui.draws[i].clip.y+=p->insets.top;
    }
    p->stats.builds++;if(p->ui.draw_count>p->stats.draw_high_water)p->stats.draw_high_water=p->ui.draw_count;
    return COH_OK;
}
const CohUiDraw *coh_presentation_draws(const CohPresentation *p,uint32_t gen,size_t *count){
    if(count)*count=0;
    if(!p||!p->initialized||!coh_ui_drawlist_valid(&p->ui,gen))return NULL;
    if(count)*count=p->ui.draw_count;
    return p->ui.draws;
}
static void emit(CohPresentation *p,CohPresentationIntentKind kind,uint32_t id,uint32_t slot){
    CohPresentationIntent *e=&p->intents[p->intent_count++];memset(e,0,sizeof(*e));
    e->kind=kind;e->revision=p->state.revision;e->actor_id=p->state.actor_id;e->id=id;e->slot=slot;e->tab=p->tab;
}
static CohStatus drain(CohPresentation *p,CohStatus status){
    CohUiEvent e;if(status!=COH_OK)return status;
    while(coh_ui_poll(&p->ui,&e))if(e.kind==COH_UI_EVENT_ACTIVATE){
        if(e.binding>=TAB&&e.binding<TAB+COH_PRESENTATION_TABS){
            p->tab=(CohPresentationTab)(e.binding-TAB);refresh(p);emit(p,COH_PRESENTATION_OPEN_TAB,0,0);
        }else if(e.binding==CLOSE){coh_presentation_show(p,0,p->tab);emit(p,COH_PRESENTATION_CLOSE,0,0);
        }else if(e.binding>=ROW&&e.binding<ROW+COH_PRESENTATION_ROWS&&p->tab>COH_PRESENTATION_DETAILS){
            uint32_t slot=e.binding-ROW;
            if(slot<p->state.counts[p->tab-1])emit(p,(CohPresentationIntentKind)(COH_PRESENTATION_INSPECT_ITEM+p->tab-1),p->state.rows[p->tab-1][slot].id,slot);
        }
    }
    return coh_ui_layout(&p->ui);
}
static CohStatus input_ready(CohPresentation *p){
    if(!p||!p->initialized||!p->visible||!p->has_state)return COH_STATE;
    if(p->intent_count>=COH_PRESENTATION_QUEUE){p->stats.queue_limits++;return COH_LIMIT;}return COH_OK;
}
CohStatus coh_presentation_action(CohPresentation *p,CohUiAction action){
    CohStatus s=input_ready(p);if(s!=COH_OK)return s;
    if(action==COH_UI_CANCEL){coh_presentation_show(p,0,p->tab);emit(p,COH_PRESENTATION_CLOSE,0,0);return COH_OK;}
    return drain(p,coh_ui_action(&p->ui,action));
}
CohStatus coh_presentation_touch(CohPresentation *p,CohUiTouch a,uint32_t pointer,float x,float y){
    CohStatus s=input_ready(p);if(s!=COH_OK){
        if(a==COH_UI_TOUCH_CANCEL&&p&&p->initialized)return coh_ui_touch(&p->ui,a,pointer,0,0);
        return s;
    }
    return drain(p,coh_ui_touch(&p->ui,a,pointer,x-p->insets.left,y-p->insets.top));
}
static CohStatus panel_action(void *context,CohUiAction action){return coh_presentation_action((CohPresentation *)context,action);}
CohStatus coh_presentation_axis(CohPresentation *p,CohHudAxisNavigation *nav,float x,float y,uint64_t ms){
    if(!p||!p->initialized||!p->visible)return COH_STATE;
    return coh_ui_axis_step(nav,x,y,ms,panel_action,p);
}
CohStatus coh_presentation_focus_row(CohPresentation *p,size_t row){
    CohStatus s=input_ready(p);if(s!=COH_OK)return s;
    if(p->tab==COH_PRESENTATION_DETAILS||row>=p->state.counts[p->tab-1])return COH_NOT_FOUND;
    return drain(p,coh_ui_focus(&p->ui,ROW+(uint32_t)row));
}
int coh_presentation_poll(CohPresentation *p,CohPresentationIntent *out){
    if(!p||!out||!p->intent_count)return 0;
    *out=p->intents[0];
    memmove(p->intents,p->intents+1,(--p->intent_count)*sizeof(*out));return 1;
}
uint32_t coh_presentation_damage_color(int32_t n,int self,int owned,int absorb){
    if(n>0)return absorb?0xffffffffu:0x00ff0000u;
    if(self)return 0xff000000u;
    if(owned)return 0xff800000u;
    return 0xa0a0a000u;
}
CohStatus coh_presentation_tick(CohPresentation *p,uint64_t now){
    size_t i;if(!p||!p->initialized)return COH_STATE;
    if(p->has_clock&&now<p->now_ms)return COH_INVALID;
    p->now_ms=now;p->has_clock=1;
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++)if(p->effects[i].active){
        CohPresentationEvent *e=&p->effects[i].event;uint64_t age=now-e->now_ms;
        uint64_t duration=e->kind==COH_PRESENTATION_ACTIVATE?400:1500;
        if(age>=duration){p->effects[i].active=0;coh_ui_set_flags(&p->ui,EFFECT+(uint32_t)i,0);p->stats.expired_effects++;}
        else{
            float progress=(float)age/(float)duration;
            uint32_t color=e->kind==COH_PRESENTATION_ACTIVATE?0x00deff00u:
                coh_presentation_damage_color(e->amount,e->victim_is_self,e->damager_is_owned,e->absorb);
            widget(p,EFFECT+(uint32_t)i)->desc.text_color=(color&0xffffff00u)|(uint32_t)(255*(1-progress));
            coh_ui_set_rect(&p->ui,EFFECT+(uint32_t)i,(CohUiRect){e->x,e->y-40*progress,160,32});
        }
    }
    return COH_OK;
}
CohStatus coh_presentation_event(CohPresentation *p,const CohPresentationEvent *e){
    size_t i,slot=COH_PRESENTATION_EFFECTS,active=0;char text[64];CohPresentationCue *c;
    if(!p||!p->initialized||!p->has_state)return COH_STATE;
    if(!e||!e->sequence||e->sequence<=p->last_sequence||e->revision!=p->state.revision||
       e->actor_id!=p->state.actor_id||!e->target_id||e->target_id!=p->state.target_id||
       !e->power_id||(e->kind!=COH_PRESENTATION_ACTIVATE&&e->kind!=COH_PRESENTATION_IMPACT)||
       (p->has_clock&&e->now_ms<p->now_ms)||e->amount < -1000000000||e->amount > 1000000000||
       !isfinite(e->x)||!isfinite(e->y)||e->x<0||e->x>864||e->y<40||e->y>736||
       !isfinite(e->emitter.x)||!isfinite(e->emitter.y)||!isfinite(e->emitter.z)||
       (e->victim_is_self!=0&&e->victim_is_self!=1)||(e->damager_is_owned!=0&&e->damager_is_owned!=1)||
       (e->absorb!=0&&e->absorb!=1)||
       (e->kind==COH_PRESENTATION_IMPACT&&!e->amount)){
        p->stats.rejected_events++;return COH_INVALID;
    }
    if(p->cue_count==COH_PRESENTATION_QUEUE){p->stats.queue_limits++;return COH_LIMIT;}
    /* Expired effects can be reused without changing live state on rejection. */
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++){
        uint64_t duration=p->effects[i].event.kind==COH_PRESENTATION_ACTIVATE?400:1500;
        if(!p->effects[i].active||e->now_ms-p->effects[i].event.now_ms>=duration){if(slot==COH_PRESENTATION_EFFECTS)slot=i;}
        else active++;
    }
    if(slot==COH_PRESENTATION_EFFECTS){p->stats.queue_limits++;return COH_LIMIT;}
    coh_presentation_tick(p,e->now_ms);p->effects[slot].event=*e;p->effects[slot].active=1;p->last_sequence=e->sequence;
    if(e->kind==COH_PRESENTATION_ACTIVATE)snprintf(text,sizeof(text),"[ TARGET ]");
    else snprintf(text,sizeof(text),"%+d",(int)e->amount);
    coh_ui_set_text(&p->ui,EFFECT+(uint32_t)slot,text);coh_ui_set_flags(&p->ui,EFFECT+(uint32_t)slot,SHOWN);
    c=&p->cues[p->cue_count++];memset(c,0,sizeof(*c));
    c->sequence=e->sequence;c->revision=e->revision;c->kind=e->kind;c->actor_id=e->actor_id;c->target_id=e->target_id;
    c->power_id=e->power_id;c->audio_asset=e->audio_asset;c->animation_asset=e->animation_asset;c->emitter=e->emitter;
    p->stats.events++;if(!e->audio_asset)p->stats.missing_audio++;if(!e->animation_asset)p->stats.missing_animation++;
    if(active+1>p->stats.effect_high_water)p->stats.effect_high_water=active+1;
    return coh_presentation_tick(p,e->now_ms);
}
int coh_presentation_poll_cue(CohPresentation *p,CohPresentationCue *out){
    if(!p||!out||!p->cue_count)return 0;
    *out=p->cues[0];
    memmove(p->cues,p->cues+1,(--p->cue_count)*sizeof(*out));return 1;
}
void coh_presentation_mock_state(CohPresentationState *s,const CohHudState *h){
    size_t i;static const char *names[4][3]={
        {"Mock inspiration","Mock salvage","Mock recipe"},
        {"Mock damage enhancement","Mock accuracy enhancement","Mock endurance enhancement"},
        {"Explore Atlas Park (mock)","Visit station (mock)","Enter Kings Row (mock)"},
        {"Atlas contact (mock)","Training contact (mock)","Kings Row contact (mock)"}};
    if(!s||!h)return;
    memset(s,0,sizeof(*s));s->revision=h->revision;s->actor_id=h->actor_id;s->target_id=h->target_id;
    snprintf(s->name,sizeof(s->name),"%s",h->actor_name);snprintf(s->archetype,sizeof(s->archetype),"Offline preview");
    snprintf(s->origin,sizeof(s->origin),"Mock only");snprintf(s->description,sizeof(s->description),"No real character, inventory or task changes.");
    s->level=1;
    for(i=0;i<4;i++){
        size_t j;s->counts[i]=3;
        for(j=0;j<3;j++){
            CohPresentationRow *r=&s->rows[i][j];r->id=1000+(uint32_t)(i*10+j);r->enabled=1;
            snprintf(r->name,sizeof(r->name),"%s",names[i][j]);
            snprintf(r->detail,sizeof(r->detail),"Inspect only; original icon not loaded");
        }
    }
    s->rows[2][0].progress=.5f;s->rows[2][1].progress=1;s->rows[2][1].completed=1;
    s->rows[3][1].completed=1;
}
