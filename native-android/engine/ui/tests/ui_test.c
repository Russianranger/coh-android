#include "../coh_ui.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static CohUi u;
static unsigned groups;
static int glyph_mode;
static CohStatus glyph(void *ctx,uint32_t font,uint32_t cp,float size,CohUiGlyph *g){
    (void)ctx;(void)font;
    if(glyph_mode==1)return COH_NOT_FOUND;
    *g=(CohUiGlyph){17,{0,0,.125f,.25f},size*.5f,size,0,0,size*.6f};
    if(cp==' ')g->width=0;
    if(glyph_mode==2)g->advance=NAN;
    if(glyph_mode==3)g->uv.w=2;
    return COH_OK;
}
static CohUiDesc desc(uint32_t id,CohUiKind kind,uint32_t parent,float x,float y,float w,float h){
    CohUiDesc d={0};d.id=id;d.kind=kind;d.parent=parent;
    d.rect=(CohUiRect){x,y,w,h};d.flags=COH_UI_VISIBLE|COH_UI_ENABLED;
    if(kind==COH_UI_BUTTON||kind==COH_UI_INPUT)d.flags|=COH_UI_FOCUSABLE;
    d.color=0x245985ff;d.text_color=0xffffffff;d.font_size=16;return d;
}
static void fresh(CohUiScale scale){coh_ui_init(&u,scale,glyph,NULL);glyph_mode=0;assert(coh_ui_surface(&u,1,1280,720)==COH_OK);}
static void add(CohUiDesc d,const char *s){assert(coh_ui_add(&u,&d,s)==COH_OK);}
static void drain(void){CohUiEvent e;while(coh_ui_poll(&u,&e)){};}
static void near(float a,float b){assert(fabsf(a-b)<.001f);}
static void bounds(void){
    CohUiDesc d=desc(1,COH_UI_BUTTON,0,0,0,20,20);unsigned i;
    coh_ui_init(&u,COH_UI_SCALE_XY,glyph,NULL);
    assert(coh_ui_build(&u)==COH_STATE);assert(!coh_ui_drawlist_valid(&u,1));
    assert(coh_ui_surface(&u,0,1280,720)==COH_INVALID);
    assert(coh_ui_surface(&u,1,NAN,720)==COH_INVALID);
    assert(coh_ui_surface(&u,1,1280,720)==COH_OK);
    assert(coh_ui_add(&u,&d,"x")==COH_OK);assert(coh_ui_add(&u,&d,"x")==COH_INVALID);
    d.id=2;d.parent=999;assert(coh_ui_add(&u,&d,"")==COH_NOT_FOUND);d.parent=0;
    d.rect.w=-1;assert(coh_ui_add(&u,&d,"")==COH_INVALID);d.rect.w=20;
    d.anchor_y=NAN;assert(coh_ui_add(&u,&d,"")==COH_INVALID);d.anchor_y=0;
    for(i=2;i<=COH_UI_WIDGETS;i++){d.id=i;assert(coh_ui_add(&u,&d,"")==COH_OK);}
    d.id=999;assert(coh_ui_add(&u,&d,"")==COH_LIMIT);
    assert(u.stats.widget_high_water==COH_UI_WIDGETS);assert(u.stats.arena_bytes==sizeof(CohUi));groups++;
}
static void layout(void){
    CohUiDesc d;const CohUiWidget *w;
    fresh(COH_UI_SCALE_FIT);add(desc(1,COH_UI_PANEL,0,100,200,400,200),"");
    d=desc(2,COH_UI_BUTTON,1,-10,-20,100,50);d.anchor_x=d.anchor_y=1;add(d,"x");
    assert(coh_ui_layout(&u)==COH_OK);w=coh_ui_widget(&u,2);
    near(w->logical.x,390);near(w->logical.y,330);near(w->pixels.x,525.625f);near(w->pixels.y,309.375f);
    near(u.offset_x,160);near(u.scale_x,.9375f);near(u.scale_y,.9375f);
    assert(coh_ui_set_rect(&u,2,(CohUiRect){300,0,100,50})==COH_OK);assert(coh_ui_layout(&u)==COH_OK);
    assert(coh_ui_widget(&u,2)->clip.w==0);
    assert(coh_ui_set_rect(&u,2,(CohUiRect){-10,-20,100,50})==COH_OK);
    assert(coh_ui_focus(&u,2)==COH_OK);
    assert(coh_ui_set_flags(&u,1,COH_UI_ENABLED)==COH_OK);assert(!coh_ui_keyboard_requested(&u));
    assert(coh_ui_layout(&u)==COH_OK);assert(u.focus==0);assert(!coh_ui_widget(&u,2)->effective_visible);
    assert(coh_ui_remove(&u,1)==COH_OK);assert(u.widget_count==0);assert(coh_ui_remove(&u,1)==COH_NOT_FOUND);groups++;
}
static void bindings(void){
    CohUiDesc d;fresh(COH_UI_SCALE_XY);
    d=desc(1,COH_UI_LABEL,0,0,0,100,20);d.binding=91;add(d,"one");
    d=desc(2,COH_UI_INPUT,0,0,30,100,20);d.binding=91;add(d,"two");
    d=desc(3,COH_UI_PROGRESS,0,0,60,100,20);d.binding=92;add(d,"");
    assert(coh_ui_bind_text(&u,91,"hello")==COH_OK);assert(!strcmp(coh_ui_widget(&u,1)->text,"hello"));
    assert(!strcmp(coh_ui_widget(&u,2)->text,"hello"));
    assert(coh_ui_bind_text(&u,91,"bad\n")==COH_INVALID);assert(!strcmp(coh_ui_widget(&u,1)->text,"hello"));
    assert(coh_ui_bind_value(&u,92,NAN)==COH_INVALID);assert(coh_ui_bind_value(&u,92,2)==COH_OK);
    assert(coh_ui_widget(&u,3)->value==1);assert(coh_ui_bind_value(&u,92,-1)==COH_OK);assert(coh_ui_widget(&u,3)->value==0);
    assert(coh_ui_focus(&u,2)==COH_OK);assert(coh_ui_bind_enabled(&u,91,0)==COH_OK);assert(coh_ui_layout(&u)==COH_OK);assert(u.focus==0);
    assert(coh_ui_bind_text(&u,0,"x")==COH_INVALID);assert(coh_ui_bind_value(&u,99,0)==COH_NOT_FOUND);groups++;
}
static void touch(void){
    CohUiEvent e;fresh(COH_UI_SCALE_NONE);add(desc(1,COH_UI_BUTTON,0,0,0,100,40),"go");
    assert(coh_ui_touch(&u,COH_UI_TOUCH_DOWN,44,0,0)==COH_OK);assert(u.focus==1);assert(u.capture==1);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_DOWN,45,1,1)==COH_STATE);assert(u.capture_pointer==44);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_UP,45,1,1)==COH_STATE);assert(u.capture==1);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_UP,44,100,40)==COH_OK);assert(!u.capture);
    assert(coh_ui_poll(&u,&e)&&e.kind==COH_UI_EVENT_FOCUS&&e.widget==1);
    assert(coh_ui_poll(&u,&e)&&e.kind==COH_UI_EVENT_ACTIVATE&&e.widget==1);assert(!coh_ui_poll(&u,&e));
    assert(coh_ui_touch(&u,COH_UI_TOUCH_DOWN,44,1,1)==COH_OK);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_UP,44,1000,1000)==COH_OK);assert(u.event_count==0);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_DOWN,44,1,1)==COH_OK);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_CANCEL,44,0,0)==COH_OK);assert(!u.capture);
    assert(coh_ui_touch(&u,COH_UI_TOUCH_DOWN,44,NAN,1)==COH_INVALID);groups++;
}
static void controller(void){
    fresh(COH_UI_SCALE_NONE);add(desc(1,COH_UI_BUTTON,0,10,10,50,40),"1");add(desc(2,COH_UI_BUTTON,0,100,10,50,40),"2");
    add(desc(3,COH_UI_INPUT,0,10,100,50,40),"");add(desc(4,COH_UI_BUTTON,0,100,100,50,40),"4");
    assert(coh_ui_action(&u,COH_UI_NEXT)==COH_OK&&u.focus==1);
    assert(coh_ui_action(&u,COH_UI_RIGHT)==COH_OK&&u.focus==2);
    assert(coh_ui_action(&u,COH_UI_DOWN)==COH_OK&&u.focus==4);
    assert(coh_ui_action(&u,COH_UI_LEFT)==COH_OK&&u.focus==3);assert(coh_ui_keyboard_requested(&u));
    assert(coh_ui_action(&u,COH_UI_PREVIOUS)==COH_OK&&u.focus==2);
    assert(coh_ui_action(&u,COH_UI_UP)==COH_NOT_FOUND&&u.focus==2);
    assert(coh_ui_action(&u,COH_UI_CANCEL)==COH_OK&&!u.focus);groups++;
}
static void text(void){
    size_t n=99;char long_text[COH_UI_TEXT+1];unsigned i;CohUiEvent e;
    const char *invalid[]={"\xc0\x80","\xed\xa0\x80","\xf4\x90\x80\x80","\xe2\x82","\x80","\xf8\x80\x80\x80\x80","\x7f","\x01"};
    fresh(COH_UI_SCALE_XY);add(desc(1,COH_UI_INPUT,0,10,10,400,40),"");assert(coh_ui_focus(&u,1)==COH_OK);drain();
    assert(coh_ui_text_commit(&u,"A\xe2\x82\xac\xf0\x9f\x98\x80")==COH_OK);
    assert(coh_ui_utf8(coh_ui_widget(&u,1)->text,1,&n)==COH_OK&&n==8);
    assert(coh_ui_action(&u,COH_UI_BACKSPACE)==COH_OK);assert(!strcmp(coh_ui_widget(&u,1)->text,"A\xe2\x82\xac"));
    assert(coh_ui_action(&u,COH_UI_BACKSPACE)==COH_OK);assert(!strcmp(coh_ui_widget(&u,1)->text,"A"));
    for(i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++){
        n=99;assert(coh_ui_utf8(invalid[i],1,&n)==COH_INVALID&&n==99);
        assert(coh_ui_text_commit(&u,invalid[i])==COH_INVALID);assert(!strcmp(coh_ui_widget(&u,1)->text,"A"));
    }
    memset(long_text,'x',sizeof(long_text));long_text[sizeof(long_text)-1]=0;
    assert(coh_ui_text_commit(&u,long_text)==COH_LIMIT);assert(coh_ui_text_commit(&u,"\n")==COH_INVALID);
    drain();assert(coh_ui_action(&u,COH_UI_SUBMIT)==COH_OK);assert(coh_ui_poll(&u,&e)&&e.kind==COH_UI_EVENT_SUBMIT);groups++;
}
static void event_limit(void){
    unsigned i;fresh(COH_UI_SCALE_NONE);add(desc(1,COH_UI_INPUT,0,1,1,100,40),"");assert(coh_ui_focus(&u,1)==COH_OK);drain();
    for(i=0;i<COH_UI_EVENTS;i++)assert(coh_ui_action(&u,COH_UI_SUBMIT)==COH_OK);
    assert(coh_ui_text_commit(&u,"rejected")==COH_LIMIT);assert(coh_ui_widget(&u,1)->text[0]==0);
    assert(coh_ui_focus(&u,0)==COH_LIMIT&&u.focus==1);assert(u.stats.event_limit_hits==2);drain();groups++;
}
static void drawlist(void){
    unsigned i;char text[101];fresh(COH_UI_SCALE_XY);
    add(desc(1,COH_UI_WINDOW,0,0,0,200,100),"HUD");
    assert(coh_ui_build(&u)==COH_OK);assert(u.draw_count==4);assert(coh_ui_drawlist_valid(&u,1));
    assert(u.draws[1].kind==COH_UI_DRAW_GLYPH&&u.draws[1].resource_id==17);assert(u.draws[1].surface_generation==1);
    glyph_mode=1;assert(coh_ui_build(&u)==COH_NOT_FOUND);assert(u.draw_count==0&&!coh_ui_drawlist_valid(&u,1));
    glyph_mode=2;assert(coh_ui_build(&u)==COH_INVALID);glyph_mode=3;assert(coh_ui_build(&u)==COH_INVALID);
    glyph_mode=0;u.glyph=NULL;assert(coh_ui_build(&u)==COH_UNSUPPORTED);assert(!u.draw_count);
    fresh(COH_UI_SCALE_NONE);memset(text,'a',100);text[100]=0;
    for(i=1;i<=50;i++)add(desc(i,COH_UI_LABEL,0,0,0,1000,700),text);
    assert(coh_ui_build(&u)==COH_LIMIT);assert(!u.draw_count);assert(u.stats.draw_limit_hits==1);groups++;
}
static void lifecycle(void){
    fresh(COH_UI_SCALE_XY);add(desc(1,COH_UI_INPUT,0,1,1,100,40),"stay");assert(coh_ui_focus(&u,1)==COH_OK);
    assert(coh_ui_build(&u)==COH_OK);coh_ui_surface_lost(&u);assert(!coh_ui_drawlist_valid(&u,1));
    assert(coh_ui_build(&u)==COH_STATE);assert(coh_ui_text_commit(&u,"x")==COH_STATE);
    assert(coh_ui_surface(&u,2,1920,1080)==COH_OK);assert(!coh_ui_drawlist_valid(&u,2));assert(u.focus==1);
    assert(coh_ui_build(&u)==COH_OK);assert(coh_ui_drawlist_valid(&u,2));assert(!coh_ui_drawlist_valid(&u,1));
    assert(!strcmp(coh_ui_widget(&u,1)->text,"stay"));
    coh_ui_destroy(&u);coh_ui_destroy(&u);assert(u.widget_count==0);groups++;
}
static void gameplay_bindings(void){
    CohUiDesc d;CohUiEvent e;unsigned i;size_t count;
    fresh(COH_UI_SCALE_FIT);add(desc(1,COH_UI_WINDOW,0,20,20,400,200),"");
    d=desc(2,COH_UI_LABEL,1,10,10,300,24);d.binding=1001;add(d,"Character");
    d=desc(3,COH_UI_PROGRESS,1,10,40,300,20);d.binding=1002;add(d,"");
    d=desc(4,COH_UI_PROGRESS,1,10,65,300,20);d.binding=1003;add(d,"");
    d=desc(5,COH_UI_BUTTON,1,10,100,80,40);d.binding=2001;add(d,"Power 1");
    d=desc(6,COH_UI_INPUT,0,20,-20,600,32);d.anchor_y=1;d.binding=3001;add(d,"");
    d=desc(7,COH_UI_ICON,1,330,10,40,40);d.resource_id=45;add(d,"");
    count=u.widget_count;
    for(i=0;i<500;i++){
        assert(coh_ui_bind_text(&u,1001,i&1?"Huge hero":"Scrapper")==COH_OK);
        assert(coh_ui_bind_value(&u,1002,(float)i/500)==COH_OK);
        assert(coh_ui_bind_value(&u,1003,1-(float)i/500)==COH_OK);
        assert(coh_ui_bind_enabled(&u,2001,i&1)==COH_OK);assert(coh_ui_build(&u)==COH_OK);
        assert(u.widget_count==count);assert(coh_ui_drawlist_valid(&u,1));
    }
    assert(coh_ui_focus(&u,5)==COH_OK);drain();assert(coh_ui_action(&u,COH_UI_ACTIVATE)==COH_OK);
    assert(coh_ui_poll(&u,&e)&&e.widget==5&&e.binding==2001&&e.kind==COH_UI_EVENT_ACTIVATE);
    assert(coh_ui_focus(&u,6)==COH_OK);assert(coh_ui_text_commit(&u,"hello Atlas")==COH_OK);
    assert(coh_ui_action(&u,COH_UI_SUBMIT)==COH_OK);assert(coh_ui_keyboard_requested(&u));
    /* Surface recreation preserves data bindings and event-to-game IDs. */
    coh_ui_surface_lost(&u);assert(!coh_ui_keyboard_requested(&u));
    assert(coh_ui_surface(&u,2,1920,1080)==COH_OK);assert(coh_ui_build(&u)==COH_OK);
    assert(!strcmp(coh_ui_widget(&u,6)->text,"hello Atlas"));
    assert(coh_ui_remove(&u,6)==COH_OK);assert(u.focus==0);assert(u.event_count==0);groups++;
}
static void stress(void){
    unsigned i;clock_t start;double elapsed;
    fresh(COH_UI_SCALE_FIT);add(desc(1,COH_UI_INPUT,0,20,20,300,40),"");assert(coh_ui_focus(&u,1)==COH_OK);drain();
    start=clock();
    for(i=0;i<20000;i++){
        assert(coh_ui_text_commit(&u,"\xe2\x82\xac")==COH_OK);assert(coh_ui_action(&u,COH_UI_BACKSPACE)==COH_OK);
        assert(coh_ui_build(&u)==COH_OK);drain();
        if(i%100==0){coh_ui_surface_lost(&u);assert(coh_ui_surface(&u,i+2,1280,720)==COH_OK);}
        assert(u.widget_count==1&&u.event_count==0&&u.draw_count<=5);
    }
    elapsed=(double)(clock()-start)/CLOCKS_PER_SEC;groups++;
    printf("{\"test_groups\":%u,\"stress_iterations\":20000,\"stress_cpu_seconds\":%.6f,\"arena_bytes\":%zu,\"widget_high_water\":%zu,\"draw_high_water\":%zu,\"event_high_water\":%zu,\"frames\":%llu,\"ui_heap_calls_by_design\":0}\n",
        groups,elapsed,sizeof(CohUi),u.stats.widget_high_water,u.stats.draw_high_water,u.stats.event_high_water,(unsigned long long)u.stats.frames);
}
int main(void){bounds();layout();bindings();touch();controller();text();event_limit();drawlist();lifecycle();gameplay_bindings();stress();return 0;}
