#include "coh_presentation.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
static CohPresentation p;
static CohPresentationState state,saved;
static CohStatus glyph(void *context,uint32_t font,uint32_t cp,float size,CohUiGlyph *out){
    (void)context;(void)font;*out=(CohUiGlyph){7,{0,0,1,1},cp==' '?0:size*.5f,size,0,0,size*.55f};return COH_OK;
}
static void base(void){
    CohHudState hud;memset(&hud,0,sizeof(hud));hud.revision=42;hud.actor_id=100;hud.target_id=200;strcpy(hud.actor_name,"Offline Wretch");
    assert(coh_presentation_init(&p,glyph,NULL)==COH_OK);coh_presentation_mock_state(&state,&hud);
    assert(coh_presentation_set_state(&p,&state)==COH_OK);
    assert(coh_presentation_surface(&p,1,1280,720,(CohHudInsets){24,12,30,16})==COH_OK);
    assert(coh_presentation_show(&p,1,COH_PRESENTATION_DETAILS)==COH_OK);
}
static void snapshots(void){
    unsigned i;size_t n;base();saved=state;
#define BAD(expr) do {state=saved;expr;assert(coh_presentation_set_state(&p,&state)==COH_INVALID);assert(!memcmp(&p.state,&saved,sizeof(saved)));} while(0)
    BAD(state.actor_id=0);BAD(state.revision=41);BAD(state.level=1001);BAD(state.counts[0]=9);
    BAD(state.rows[0][0].progress=NAN);BAD(state.rows[0][0].progress=INFINITY);BAD(state.rows[0][0].progress=-.1f);
    BAD(state.rows[0][0].progress=1.1f);BAD(state.rows[0][0].id=0);BAD(state.rows[0][1].id=state.rows[0][0].id);
    BAD(state.rows[0][0].enabled=2);BAD(state.rows[0][0].completed=-1);
    BAD(memset(state.name,'x',sizeof(state.name)));BAD(strcpy(state.origin,"bad\ntext"));
    BAD(state.archetype[0]=(char)0xff);BAD(memset(state.rows[0][0].detail,'x',sizeof(state.rows[0][0].detail)));
    state=saved;strcpy(state.name,"Caller changed");assert(!strcmp(p.state.name,"Offline Wretch"));
    for(i=0;i<5;i++){
        const CohUiDraw *d;size_t k;assert(coh_presentation_show(&p,1,(CohPresentationTab)i)==COH_OK);
        assert(coh_presentation_build(&p)==COH_OK);d=coh_presentation_draws(&p,1,&n);assert(d&&n>40);
        for(k=0;k<n;k++)assert(d[k].surface_generation==1&&d[k].clip.x>=24&&d[k].clip.y>=12&&
            d[k].clip.x+d[k].clip.w<=1250.01f&&d[k].clip.y+d[k].clip.h<=704.01f);
    }
    assert(!coh_presentation_draws(&p,2,&n)&&!n);
    assert(coh_presentation_show(&p,1,(CohPresentationTab)5)==COH_INVALID);
    assert(coh_presentation_surface(&p,2,100,100,(CohHudInsets){60,0,60,0})==COH_INVALID);
    assert(coh_presentation_surface(&p,2,NAN,720,(CohHudInsets){0,0,0,0})==COH_INVALID);
#undef BAD
}
static void controls(void){
    size_t i;CohPresentationIntent e;const CohUiWidget *w;float x,y;base();
    for(i=1;i<5;i++){
        assert(coh_presentation_show(&p,1,(CohPresentationTab)i)==COH_OK);
        assert(coh_presentation_focus_row(&p,1)==COH_OK);assert(coh_presentation_action(&p,COH_UI_ACTIVATE)==COH_OK);
        assert(coh_presentation_poll(&p,&e)&&e.kind==(CohPresentationIntentKind)(COH_PRESENTATION_INSPECT_ITEM+i-1)&&
               e.id==1001+(i-1)*10&&e.actor_id==100&&e.revision==42&&e.slot==1);
        assert(!coh_presentation_poll(&p,&e));
    }
    w=coh_ui_widget(&p.ui,40);assert(w);x=w->pixels.x+20+p.insets.left;y=w->pixels.y+10+p.insets.top;
    assert(coh_presentation_touch(&p,COH_UI_TOUCH_DOWN,9,x,y)==COH_OK);
    assert(coh_presentation_touch(&p,COH_UI_TOUCH_UP,9,x,y)==COH_OK);
    assert(coh_presentation_poll(&p,&e)&&e.id==1030&&e.kind==COH_PRESENTATION_INSPECT_CONTACT);
    assert(coh_presentation_touch(&p,COH_UI_TOUCH_DOWN,9,x,y)==COH_OK);
    state.revision++;assert(coh_presentation_set_state(&p,&state)==COH_OK);
    assert(coh_presentation_touch(&p,COH_UI_TOUCH_UP,9,x,y)==COH_STATE&&!coh_presentation_poll(&p,&e));
    assert(coh_presentation_focus_row(&p,1)==COH_OK);
    for(i=0;i<COH_PRESENTATION_QUEUE;i++)assert(coh_presentation_action(&p,COH_UI_ACTIVATE)==COH_OK);
    assert(coh_presentation_action(&p,COH_UI_ACTIVATE)==COH_LIMIT&&p.intent_count==COH_PRESENTATION_QUEUE);
    while(coh_presentation_poll(&p,&e))assert(e.revision==43);
    state.rows[3][1].enabled=0;assert(coh_presentation_set_state(&p,&state)==COH_OK);
    assert(coh_presentation_focus_row(&p,1)==COH_STATE);assert(coh_presentation_focus_row(&p,8)==COH_NOT_FOUND);
    assert(coh_presentation_action(&p,COH_UI_CANCEL)==COH_OK&&!p.visible);
    assert(coh_presentation_poll(&p,&e)&&e.kind==COH_PRESENTATION_CLOSE);
    assert(coh_presentation_action(&p,COH_UI_ACTIVATE)==COH_STATE);
    for(i=0;i<256;i++)assert(coh_presentation_show(&p,1,(CohPresentationTab)(i%5))==COH_OK);
    assert(p.ui.event_count==0); /* external tab cycling must not fill hidden event queue */
}
static void analog(void){
    CohHudAxisNavigation nav;uint32_t first;base();coh_hud_axis_reset(&nav);
    assert(coh_presentation_show(&p,1,COH_PRESENTATION_INVENTORY)==COH_OK);
    first=p.ui.focus;assert(coh_presentation_axis(&p,&nav,1,0,100)==COH_OK);
    assert(p.ui.focus!=first&&nav.actions==1&&nav.repeats==0);
    first=p.ui.focus;assert(coh_presentation_axis(&p,&nav,1,0,449)==COH_OK&&p.ui.focus==first);
    assert(coh_presentation_axis(&p,&nav,1,0,450)==COH_OK&&p.ui.focus!=first&&nav.repeats==1);
    assert(coh_presentation_axis(&p,&nav,NAN,0,451)==COH_INVALID);
    assert(coh_presentation_axis(&p,&nav,0,0,451)==COH_OK&&nav.direction==0);
    assert(coh_presentation_show(&p,0,COH_PRESENTATION_INVENTORY)==COH_OK);
    assert(coh_presentation_axis(&p,&nav,1,0,452)==COH_STATE);
}
static CohPresentationEvent event(void){
    CohPresentationEvent e;memset(&e,0,sizeof(e));e.sequence=1;e.revision=42;e.now_ms=100;e.kind=COH_PRESENTATION_IMPACT;
    e.actor_id=100;e.target_id=200;e.power_id=1001;e.amount=-12;e.damager_is_owned=1;e.x=400;e.y=300;return e;
}
static void effects(void){
    CohPresentationEvent e,bad;CohPresentationCue cue;size_t i;uint64_t last;base();e=event();
#define BAD(expr) do {bad=e;expr;assert(coh_presentation_event(&p,&bad)==COH_INVALID);assert(p.stats.events==0&&p.cue_count==0);} while(0)
    BAD(bad.sequence=0);BAD(bad.actor_id=2);BAD(bad.target_id=2);BAD(bad.revision=41);BAD(bad.power_id=0);
    BAD(bad.x=NAN);BAD(bad.y=1);BAD(bad.x=900);BAD(bad.emitter.x=INFINITY);BAD(bad.amount=0);BAD(bad.absorb=2);
    BAD(bad.kind=(CohPresentationEventKind)9);
#undef BAD
    assert(coh_presentation_event(&p,&e)==COH_OK);assert(p.cue_count==1&&p.stats.missing_audio==1&&p.stats.missing_animation==1);
    assert(coh_presentation_poll_cue(&p,&cue)&&cue.sequence==1&&cue.actor_id==100&&cue.power_id==1001&&!cue.audio_asset);
    assert(coh_presentation_event(&p,&e)==COH_INVALID);assert(coh_presentation_tick(&p,99)==COH_INVALID);
    assert(coh_presentation_tick(&p,850)==COH_OK);assert(p.effects[0].active);
    assert(coh_ui_widget(&p.ui,80)->desc.rect.y==280&&coh_ui_widget(&p.ui,80)->desc.text_color==0xff80007fu);
    assert(coh_presentation_tick(&p,1600)==COH_OK&&!p.effects[0].active);
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++){e.sequence++;e.now_ms=1600;assert(coh_presentation_event(&p,&e)==COH_OK);}
    last=p.last_sequence;e.sequence++;assert(coh_presentation_event(&p,&e)==COH_LIMIT&&p.last_sequence==last);
    assert(p.stats.effect_high_water==8);assert(coh_presentation_tick(&p,3100)==COH_OK);
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++){e.sequence++;e.now_ms=3100;assert(coh_presentation_event(&p,&e)==COH_OK);}
    assert(p.cue_count==16);e.sequence++;e.now_ms=4600;
    assert(coh_presentation_event(&p,&e)==COH_LIMIT&&p.now_ms==3100);
    while(coh_presentation_poll_cue(&p,&cue)){};
    assert(coh_presentation_event(&p,&e)==COH_OK);
    state.actor_id=101;state.revision=1;assert(coh_presentation_set_state(&p,&state)==COH_OK&&p.cue_count==0&&p.last_sequence==0);
    for(i=0;i<COH_PRESENTATION_EFFECTS;i++)assert(!p.effects[i].active);
}
static void lifecycle(void){
    unsigned i;size_t n;base();assert(coh_presentation_show(&p,1,COH_PRESENTATION_MISSIONS)==COH_OK);
    for(i=0;i<64;i++){
        coh_presentation_surface_lost(&p);assert(coh_presentation_build(&p)==COH_STATE);
        assert(!coh_presentation_draws(&p,i+1,&n)&&!n);
        assert(coh_presentation_surface(&p,i+2,i%2?1280:720,i%2?720:1280,(CohHudInsets){24,24,24,24})==COH_OK);
        assert(coh_presentation_build(&p)==COH_OK&&coh_presentation_draws(&p,i+2,&n));
        assert(p.tab==COH_PRESENTATION_MISSIONS&&p.visible&&!strcmp(p.state.name,"Offline Wretch"));
    }
}
int main(void){
    clock_t start;unsigned i;snapshots();controls();analog();effects();lifecycle();base();
    start=clock();for(i=0;i<1000;i++){state.revision++;assert(coh_presentation_set_state(&p,&state)==COH_OK);assert(coh_presentation_build(&p)==COH_OK);}
    printf("{\"passed\":true,\"snapshot_negative_cases\":16,\"event_negative_cases\":12,\"panel_tabs\":5,\"inspect_intent_types\":4,\"lifecycle_recreations\":64,\"arena_bytes\":%zu,\"draw_high_water\":%zu,\"host_snapshot_build_1000_cpu_ms\":%.3f}\n",sizeof(p),p.stats.draw_high_water,1000.0*(clock()-start)/CLOCKS_PER_SEC);
    coh_presentation_destroy(&p);coh_presentation_destroy(&p);return 0;
}
