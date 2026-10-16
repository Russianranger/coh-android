#include "coh_presentation.h"
#include "../coh_hud_atlas.h"
#include "../coh_hud_gles.h"
#include "support_font.h"
#include <GLES3/gl3.h>
#include <assert.h>
#include <string.h>
static CohHud h;
static CohPresentation p;
static CohHudGles gpu;
static GLuint font;
static CohStatus texture(void *ctx,uint32_t resource,CohHudTexture *out){
    (void)ctx;if(resource==7){*out=(CohHudTexture){font,1};return COH_OK;}
    return COH_NOT_FOUND;
}
int presentation_demo(unsigned tab,unsigned char *pixels){
    CohHudState hs;CohPresentationState ps;CohPresentationEvent e;size_t n,i;const CohUiDraw *d;
    memset(&hs,0,sizeof(hs));hs.revision=42;hs.actor_id=100;hs.target_id=200;hs.in_phase=1;
    strcpy(hs.actor_name,"Offline Huge / Wretch");strcpy(hs.target_name,"Mock target (offline)");
    hs.health=85;hs.max_health=100;hs.endurance=75;hs.max_endurance=100;hs.target_health=60;hs.target_max_health=100;
    hs.power_count=10;for(i=0;i<10;i++){hs.powers[i].id=1000+(uint32_t)i;hs.powers[i].enabled=1;strcpy(hs.powers[i].name,i==0?"Brawl":"Mock power");}
    hs.chat_count=3;strcpy(hs.chat[0],"OFFLINE: original Montreal Heavy font.");strcpy(hs.chat[1],"New panel is copied mock state.");strcpy(hs.chat[2],"No server commands or real combat.");
    assert(coh_hud_init(&h,coh_hud_atlas_glyph,&coh_hud_font)==COH_OK);
    assert(coh_hud_set_state(&h,&hs)==COH_OK);
    assert(coh_hud_surface(&h,1,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(coh_presentation_init(&p,coh_hud_atlas_glyph,&coh_hud_font)==COH_OK);
    coh_presentation_mock_state(&ps,&hs);assert(coh_presentation_set_state(&p,&ps)==COH_OK);
    assert(coh_presentation_surface(&p,1,1280,720,(CohHudInsets){0,0,0,0})==COH_OK);
    assert(coh_presentation_show(&p,1,(CohPresentationTab)tab)==COH_OK);
    memset(&e,0,sizeof(e));e.sequence=1;e.revision=42;e.now_ms=100;e.actor_id=100;e.target_id=200;e.power_id=1000;e.x=320;e.y=270;e.damager_is_owned=1;
    e.kind=COH_PRESENTATION_ACTIVATE;assert(coh_presentation_event(&p,&e)==COH_OK);
    e.sequence=2;e.kind=COH_PRESENTATION_IMPACT;e.amount=-12;e.y=315;assert(coh_presentation_event(&p,&e)==COH_OK);
    assert(coh_presentation_tick(&p,180)==COH_OK);
    assert(coh_hud_gles_create(&gpu,1)==COH_OK);
    glGenTextures(1,&font);glBindTexture(GL_TEXTURE_2D,font);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    glTexImage2D(GL_TEXTURE_2D,0,GL_R8,COH_HUD_FONT_WIDTH,COH_HUD_FONT_HEIGHT,0,GL_RED,GL_UNSIGNED_BYTE,coh_hud_font_alpha);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glViewport(0,0,1280,720);glClearColor(.025f,.04f,.065f,1);glClear(GL_COLOR_BUFFER_BIT);
    assert(coh_hud_build(&h)==COH_OK);d=coh_hud_draws(&h,1,&n);assert(d);
    assert(coh_hud_gles_draw(&gpu,1280,720,1,d,n,texture,NULL)==COH_OK);
    assert(coh_presentation_build(&p)==COH_OK);d=coh_presentation_draws(&p,1,&n);assert(d);
    assert(coh_hud_gles_draw(&gpu,1280,720,1,d,n,texture,NULL)==COH_OK);
    assert(gpu.stats.gl_errors==0);glReadPixels(0,0,1280,720,GL_RGBA,GL_UNSIGNED_BYTE,pixels);assert(glGetError()==GL_NO_ERROR);
    glDeleteTextures(1,&font);coh_hud_gles_destroy(&gpu);coh_presentation_destroy(&p);coh_hud_destroy(&h);return (int)n;
}
