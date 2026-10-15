#include "../../coh_hud.h"
#include "../coh_hud_android.h"
#include "../coh_hud_atlas.h"
#include "../coh_hud_gles.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
static CohHud hud;
static CohHudState state,saved;
static unsigned checks;
static size_t peak_draws;
static int missing_glyph;
static CohStatus glyph(void *context,uint32_t font,uint32_t cp,float size,CohUiGlyph *out){
    (void)context;(void)font;
    if(missing_glyph)return COH_NOT_FOUND;
    *out=(CohUiGlyph){7,{0,0,1,1},cp==' '?0:size*.5f,size,0,0,size*.55f};return COH_OK;
}
static void base(void){
    size_t i;CohHudIntent e;
    missing_glyph=0;assert(coh_hud_init(&hud,glyph,NULL)==COH_OK);memset(&state,0,sizeof(state));
    state.revision=42;state.actor_id=100;state.target_id=200;
    strcpy(state.actor_name,"Hero");strcpy(state.target_name,"Hellion");
    state.health=75;state.max_health=100;state.absorb=15;state.endurance=55;state.max_endurance=100;
    state.target_health=34;state.target_max_health=50;state.in_phase=1;
    state.power_count=10;for(i=0;i<state.power_count;i++){
        state.powers[i].id=(uint32_t)i+1000;state.powers[i].enabled=1;
        snprintf(state.powers[i].name,sizeof(state.powers[i].name),"Power %u",(unsigned)i+1);
    }
    state.character_count=3;for(i=0;i<3;i++){
        state.characters[i].id=(uint32_t)i+500;state.characters[i].enabled=1;
        snprintf(state.characters[i].name,sizeof(state.characters[i].name),"Hero %u",(unsigned)i+1);
    }
    state.chat_count=2;strcpy(state.chat[0],"[Local] Native HUD fixture");strcpy(state.chat[1],"[Team] Mock game state");
    assert(coh_hud_set_state(&hud,&state)==COH_OK);
    assert(coh_hud_surface(&hud,1,1280,720,(CohHudInsets){24,12,30,16})==COH_OK);
    assert(coh_hud_build(&hud)==COH_OK);
    while(coh_hud_poll(&hud,&e)){};
}
static const CohUiWidget *binding(uint32_t id){
    size_t i;for(i=0;i<hud.ui.widget_count;i++)if(hud.ui.widgets[i].desc.binding==id)return hud.ui.widgets+i;
    return NULL;
}
static void state_and_draws(void){
    size_t i,n;const CohUiDraw *d;const CohUiWidget *w;CohHudSkin skin={9,11,12,13,14};base();
    strcpy(state.actor_name,"caller changed");assert(!strcmp(hud.state.actor_name,"Hero"));
    w=binding(COH_HUD_BIND_HEALTH);assert(w);assert(fabsf(w->value-90.0f/115)<.00001f);
    w=binding(COH_HUD_BIND_ENDURANCE);assert(w&&fabsf(w->value-.55f)<.00001f);
    d=coh_hud_draws(&hud,1,&n);assert(d&&n>100&&n<COH_UI_DRAWS);peak_draws=n;
    for(i=0;i<n;i++){
        assert(d[i].surface_generation==1&&d[i].clip.x>=24&&d[i].clip.y>=12);
        assert(d[i].clip.x+d[i].clip.w<=1250.01f&&d[i].clip.y+d[i].clip.h<=704.01f);
    }
    assert(coh_hud_draws(&hud,2,&n)==NULL&&n==0);
    assert(coh_hud_set_skin(&hud,&skin)==COH_OK);assert(coh_hud_draws(&hud,1,&n)==NULL);
    assert(coh_hud_build(&hud)==COH_OK);d=coh_hud_draws(&hud,1,&n);
    {int image=0,font=0;for(i=0;i<n;i++){image|=d[i].kind==COH_UI_DRAW_IMAGE&&d[i].resource_id==11;
        if(d[i].kind==COH_UI_DRAW_GLYPH)font=1;}assert(image&&font);}
    assert(hud.ui.widgets[0].desc.font_id==9);checks++;
}
static void invalid_snapshot(void){
    base();saved=hud.state;
#define BAD(expr) do { state=saved;expr;assert(coh_hud_set_state(&hud,&state)==COH_INVALID);assert(!memcmp(&saved,&hud.state,sizeof(saved))); } while(0)
    BAD(state.health=NAN);BAD(state.endurance=INFINITY);BAD(state.health=-1);
    BAD(state.health=101);BAD(state.max_endurance=0);BAD(state.target_health=51);
    BAD(state.power_count=11);BAD(state.character_count=9);BAD(state.chat_count=9);
    BAD(state.powers[0].cooldown=-.01f);BAD(state.powers[0].cooldown=1.01f);BAD(state.powers[0].cooldown=NAN);
    BAD(state.powers[0].id=0);BAD(state.powers[1].id=state.powers[0].id);
    BAD(state.characters[1].id=state.characters[0].id);
    BAD(memset(state.actor_name,'x',sizeof(state.actor_name)));
    BAD(state.target_name[0]=(char)0xff);BAD(strcpy(state.chat[0],"bad\nnewline"));
    state=saved;state.max_health=state.health=state.absorb=state.endurance=state.max_endurance=0;
    assert(coh_hud_set_state(&hud,&state)==COH_OK);assert(coh_hud_build(&hud)==COH_OK);
    assert(binding(COH_HUD_BIND_HEALTH)->value==0&&binding(COH_HUD_BIND_ENDURANCE)->value==0);
    checks++;
#undef BAD
}
static void touch_and_controller(void){
    CohHudIntent e;const CohUiWidget *w;float x,y;CohHudNavigation nav;uint32_t focus;
    base();w=binding(COH_HUD_BIND_POWER_FIRST+2);assert(w);
    x=w->pixels.x+w->pixels.w*.5f+hud.insets.left;y=w->pixels.y+w->pixels.h*.5f+hud.insets.top;
    assert(coh_hud_android_touch(&hud,0,3,x,y)==COH_OK);
    assert(coh_hud_android_touch(&hud,1,3,x,y)==COH_OK);
    assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_USE_POWER&&e.id==1002&&e.slot==2&&e.actor_id==100&&e.revision==42);
    assert(!coh_hud_poll(&hud,&e));
    assert(coh_hud_android_key(&hud,96,0,0,0)==COH_OK);assert(coh_hud_poll(&hud,&e)&&e.id==1002);
    assert(coh_hud_android_key(&hud,96,0,1,0)==COH_OK);assert(!coh_hud_poll(&hud,&e));
    assert(coh_hud_android_key(&hud,96,1,0,0)==COH_OK);assert(!coh_hud_poll(&hud,&e));
    assert(coh_hud_android_key(&hud,22,0,0,0)==COH_OK);assert(hud.ui.focus==binding(COH_HUD_BIND_POWER_FIRST+3)->desc.id);
    assert(coh_hud_android_key(&hud,61,0,0,1)==COH_OK);assert(hud.ui.focus==binding(COH_HUD_BIND_POWER_FIRST+2)->desc.id);
    coh_hud_navigation_reset(&nav);assert(coh_hud_navigation_axis(&hud,&nav,1,0)==COH_OK);focus=hud.ui.focus;
    assert(coh_hud_navigation_axis(&hud,&nav,1,0)==COH_OK&&hud.ui.focus==focus);
    assert(coh_hud_navigation_axis(&hud,&nav,0,0)==COH_OK);
    assert(coh_hud_navigation_axis(&hud,&nav,1,0)==COH_OK&&hud.ui.focus!=focus);
    assert(coh_hud_navigation_axis(&hud,&nav,NAN,0)==COH_INVALID);
    assert(coh_hud_android_key(&hud,999,0,0,0)==COH_UNSUPPORTED);
    assert(coh_hud_android_key(&hud,96,2,0,0)==COH_INVALID);
    assert(coh_hud_android_touch(&hud,0,4,x,y)==COH_OK);
    assert(coh_hud_android_touch(&hud,3,0,x,y)==COH_OK);
    assert(coh_hud_android_touch(&hud,1,4,x,y)==COH_STATE&&!coh_hud_poll(&hud,&e));
    state.powers[2].cooldown=.5f;assert(coh_hud_set_state(&hud,&state)==COH_OK);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_POWER_FIRST+2)==COH_STATE);checks++;
}
static void text_ime(void){
    CohHudIme ime;CohHudIntent e;const CohUiWidget *w;base();coh_hud_ime_init(&ime);
    assert(coh_hud_ime_composing(&hud,&ime,"draft")==COH_STATE);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_CHAT_INPUT)==COH_OK&&coh_hud_keyboard_requested(&hud));
    assert(coh_hud_ime_composing(&hud,&ime,"unfinished")==COH_OK&&!coh_hud_poll(&hud,&e));
    w=binding(COH_HUD_BIND_CHAT_INPUT);assert(w&&!w->text[0]);
    assert(coh_hud_ime_commit(&hud,&ime,"Hello \xe7\x8c\xab")==COH_OK);
    assert(ime.commits==1&&!ime.composing[0]&&coh_hud_keyboard_requested(&hud));
    assert(coh_hud_ime_delete(&hud,1,0)==COH_OK);assert(!strcmp(w->text,"Hello "));
    assert(coh_hud_ime_delete(&hud,2,0)==COH_UNSUPPORTED);
    assert(coh_hud_ime_commit(&hud,&ime,"\xf0\x9f\x8e\xae")==COH_OK);
    assert(coh_hud_ime_commit(&hud,&ime,"\xed\xa0\x80")==COH_INVALID);
    assert(coh_hud_android_key(&hud,66,0,0,0)==COH_OK);
    assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_SEND_CHAT&&!strcmp(e.text,"Hello \xf0\x9f\x8e\xae"));
    assert(!w->text[0]);assert(coh_hud_android_key(&hud,66,0,0,0)==COH_OK&&!coh_hud_poll(&hud,&e));
    assert(coh_hud_ime_composing(&hud,&ime,"preview")==COH_OK);
    assert(coh_hud_ime_finish(&ime)==COH_OK&&!ime.composing[0]);
    assert(coh_hud_action(&hud,COH_UI_CANCEL)==COH_OK&&!coh_hud_keyboard_requested(&hud));checks++;
}
static void selection_and_bounds(void){
    size_t i;CohHudIntent e;base();state.show_character_select=1;
    assert(coh_hud_set_state(&hud,&state)==COH_OK);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_CHAT_INPUT)==COH_STATE);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_POWER_FIRST)==COH_STATE);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_CHARACTER_FIRST+1)==COH_OK);
    assert(coh_hud_action(&hud,COH_UI_ACTIVATE)==COH_OK);
    assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_SELECT_CHARACTER&&e.id==501&&e.slot==1);
    assert(coh_hud_action(&hud,COH_UI_CANCEL)==COH_OK);
    assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_CLOSE_CHARACTER_MENU);
    state.show_character_select=0;assert(coh_hud_set_state(&hud,&state)==COH_OK);
    assert(coh_hud_focus(&hud,COH_HUD_BIND_POWER_FIRST)==COH_OK);
    for(i=0;i<COH_HUD_INTENTS;i++)assert(coh_hud_action(&hud,COH_UI_ACTIVATE)==COH_OK);
    assert(hud.intent_count==32&&hud.stats.intent_high_water==32);
    assert(coh_hud_action(&hud,COH_UI_ACTIVATE)==COH_LIMIT&&hud.intent_count==32);
    assert(coh_hud_action(&hud,COH_UI_CANCEL)==COH_OK);
    for(i=0;i<COH_HUD_INTENTS;i++)assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_USE_POWER);
    assert(!coh_hud_poll(&hud,&e));checks++;
}
static void lifecycle(void){
    unsigned i;size_t n;const CohUiDraw *d;base();assert(coh_hud_focus(&hud,COH_HUD_BIND_CHAT_INPUT)==COH_OK);
    assert(coh_hud_text_commit(&hud,"survives")==COH_OK);
    for(i=0;i<32;i++){
        coh_hud_surface_lost(&hud);assert(!coh_hud_keyboard_requested(&hud));
        assert(coh_hud_build(&hud)==COH_STATE&&!coh_hud_draws(&hud,i+1,&n)&&n==0);
        assert(coh_hud_touch(&hud,COH_UI_TOUCH_DOWN,0,10,10)==COH_STATE);
        assert(coh_hud_surface(&hud,i+2,i%2?1280:720,i%2?720:1280,(CohHudInsets){32,24,32,24})==COH_OK);
        assert(coh_hud_build(&hud)==COH_OK);d=coh_hud_draws(&hud,i+2,&n);assert(d&&n);
        assert(!strcmp(binding(COH_HUD_BIND_CHAT_INPUT)->text,"survives"));
        assert(hud.state.revision==42&&coh_hud_keyboard_requested(&hud));
    }
    assert(coh_hud_surface(&hud,90,100,100,(CohHudInsets){60,0,60,0})==COH_INVALID);
    assert(coh_hud_surface(&hud,0,100,100,(CohHudInsets){0,0,0,0})==COH_INVALID);
    assert(coh_hud_surface(&hud,90,NAN,100,(CohHudInsets){0,0,0,0})==COH_INVALID);
    missing_glyph=1;assert(coh_hud_build(&hud)==COH_NOT_FOUND);assert(!coh_hud_draws(&hud,33,&n)&&n==0);missing_glyph=0;
    coh_hud_destroy(&hud);coh_hud_destroy(&hud);assert(coh_hud_build(&hud)==COH_STATE);checks++;
}
static void atlas(void){
    CohHudAtlasEntry entries[2]={{32,{7,{0,0,.1f,.1f},0,16,0,0,8}},
                                {65,{7,{.1f,.1f,.1f,.1f},8,16,0,0,9}}};
    CohHudAtlas a={1,16,entries,2,0};CohUiGlyph g;
    assert(coh_hud_atlas_validate(&a)==COH_OK);
    assert(coh_hud_atlas_glyph(&a,1,65,32,&g)==COH_OK&&g.width==16&&g.advance==18);
    assert(coh_hud_atlas_glyph(&a,1,66,16,&g)==COH_NOT_FOUND);
    a.fallback_codepoint=65;assert(coh_hud_atlas_validate(&a)==COH_OK);
    assert(coh_hud_atlas_glyph(&a,1,0x1f3ae,16,&g)==COH_OK&&g.advance==9);
    a.fallback_codepoint=66;assert(coh_hud_atlas_validate(&a)==COH_INVALID);a.fallback_codepoint=0;
    entries[1].codepoint=32;assert(coh_hud_atlas_validate(&a)==COH_INVALID);entries[1].codepoint=65;
    entries[1].glyph.uv.w=2;assert(coh_hud_atlas_validate(&a)==COH_INVALID);entries[1].glyph.uv.w=.1f;
    entries[1].glyph.advance=NAN;assert(coh_hud_atlas_validate(&a)==COH_INVALID);entries[1].glyph.advance=9;
    assert(coh_hud_atlas_glyph(&a,1,65,NAN,&g)==COH_INVALID);checks++;
}
static void quads(void){
    CohUiDraw d={COH_UI_DRAW_GLYPH,12,7,0x12345678u,{10,20,30,40},{.25f,.5f,.25f,.25f},{8,16,50,60},1};
    CohHudVertex v[6];int clip[4];
    assert(coh_hud_quad(&d,1,v)==COH_OK);
    assert(v[0].x==10&&v[0].y==20&&v[0].u==.25f&&v[0].v==.5f);
    assert(v[2].x==40&&v[2].y==60&&v[2].u==.5f&&v[2].v==.75f);
    assert(fabsf(v[0].r-18.0f/255)<.00001f&&fabsf(v[0].a-120.0f/255)<.00001f);
    assert(coh_hud_scissor(d.clip,1280,720,clip)==COH_OK);
    assert(clip[0]==8&&clip[1]==644&&clip[2]==50&&clip[3]==60);
    assert(coh_hud_scissor((CohUiRect){-20,-20,30,30},1280,720,clip)==COH_OK);
    assert(clip[0]==0&&clip[1]==710&&clip[2]==10&&clip[3]==10);
    assert(coh_hud_scissor((CohUiRect){2000,2000,10,10},1280,720,clip)==COH_OK&&clip[2]==0&&clip[3]==0);
    assert(coh_hud_quad(&d,2,v)==COH_INVALID);d.uv.w=2;
    assert(coh_hud_quad(&d,1,v)==COH_INVALID);d.uv.w=.25f;d.rect.w=NAN;
    assert(coh_hud_quad(&d,1,v)==COH_INVALID);
    assert(coh_hud_scissor((CohUiRect){0,0,1,1},0,720,clip)==COH_INVALID);checks++;
}
static void tray_decoration(void){
    uint32_t numbers[COH_HUD_POWERS];size_t i,n,images;const CohUiDraw *d;CohHudIntent e;
    const CohUiWidget *w;float x,y;base();
    for(i=0;i<COH_HUD_POWERS;i++)numbers[i]=101+(uint32_t)i;
    assert(coh_hud_set_tray_decoration(&hud,100,NULL)==COH_INVALID);
    assert(coh_hud_set_tray_decoration(&hud,100,numbers)==COH_OK);
    assert(!coh_hud_poll(&hud,&e)&&!coh_hud_draws(&hud,1,&n));
    numbers[0]=999;assert(hud.tray_numbers[0]==101); /* copied caller resources */
    assert(coh_hud_build(&hud)==COH_OK);d=coh_hud_draws(&hud,1,&n);images=0;
    for(i=0;i<n;i++)if(d[i].kind==COH_UI_DRAW_IMAGE){
        assert(d[i].resource_id>=100&&d[i].resource_id<=110);images++;
    }
    assert(images==20);
    /* Decoration neither captures touch nor adds a controller focus stop. */
    w=binding(COH_HUD_BIND_POWER_FIRST);x=w->pixels.x+3*hud.ui.scale_x+hud.insets.left;
    y=w->pixels.y+43*hud.ui.scale_y+hud.insets.top;
    assert(coh_hud_android_touch(&hud,0,7,x,y)==COH_OK);
    assert(coh_hud_android_touch(&hud,1,7,x,y)==COH_OK);
    assert(coh_hud_poll(&hud,&e)&&e.kind==COH_HUD_USE_POWER&&e.slot==0);
    state.power_count=2;state.show_character_select=1;
    assert(coh_hud_set_state(&hud,&state)==COH_OK);assert(coh_hud_build(&hud)==COH_OK);
    d=coh_hud_draws(&hud,1,&n);images=0;
    for(i=0;i<n;i++)if(d[i].kind==COH_UI_DRAW_IMAGE)images++;
    assert(images==4); /* only existing two powers, also while modal-disabled */
    coh_hud_surface_lost(&hud);assert(hud.tray_ring==100&&hud.tray_numbers[0]==101);
    assert(coh_hud_surface(&hud,2,720,1280,(CohHudInsets){12,18,12,18})==COH_OK);
    assert(coh_hud_build(&hud)==COH_OK);d=coh_hud_draws(&hud,2,&n);assert(d&&n);
    memset(numbers,0,sizeof(numbers));assert(coh_hud_set_tray_decoration(&hud,0,numbers)==COH_OK);
    assert(coh_hud_build(&hud)==COH_OK);d=coh_hud_draws(&hud,2,&n);
    for(i=0;i<n;i++)assert(d[i].kind!=COH_UI_DRAW_IMAGE);
    checks++;
}
int main(void){
    unsigned i;clock_t begin,end;double micros;size_t high;
    state_and_draws();invalid_snapshot();touch_and_controller();text_ime();selection_and_bounds();lifecycle();atlas();quads();tray_decoration();
    base();begin=clock();for(i=0;i<2000;i++){
        state.revision=i;state.health=(float)(i%101);assert(coh_hud_set_state(&hud,&state)==COH_OK);
        assert(coh_hud_build(&hud)==COH_OK);
    }end=clock();micros=(double)(end-begin)*1000000/CLOCKS_PER_SEC/2000;
    high=hud.ui.stats.draw_high_water;
    printf("{\"groups\":%u,\"state_negative_cases\":18,\"lifecycle_recreates\":32,\"benchmark_iterations\":2000,\"snapshot_build_mean_host_us\":%.3f,\"arena_bytes\":%zu,\"state_bytes\":%zu,\"widgets\":%zu,\"draw_high_water\":%zu,\"initial_draws\":%zu}\n",
           checks,micros,sizeof(CohHud),sizeof(CohHudState),hud.ui.widget_count,high,peak_draws);
    coh_hud_destroy(&hud);return 0;
}
