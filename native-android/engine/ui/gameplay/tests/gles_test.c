/* Executed by gles_check.py inside an actual surfaceless Mesa GLES3 context.
 * Readback belongs to qualification only, never the shipping draw path. */
#include "../coh_hud_gles.h"
#include <GLES3/gl3.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifdef COH_HUD_REAL_FONT
#include "atlas.h"
#endif
static CohHudGles renderer;
static GLuint atlas;
static CohUiDraw draws[COH_HUD_GLES_BATCH_QUADS+1];
static CohStatus resolve(void *ctx,uint32_t resource,CohHudTexture *out){
    (void)ctx;if(resource!=7)return COH_NOT_FOUND;*out=(CohHudTexture){atlas,1};return COH_OK;
}
static CohUiDraw rectangle(uint32_t color,CohUiRect rect,CohUiRect clip){
    CohUiDraw d;memset(&d,0,sizeof(d));d.kind=COH_UI_DRAW_RECT;d.color=color;d.rect=rect;
    d.clip=clip;d.uv=(CohUiRect){0,0,1,1};d.surface_generation=1;return d;
}
static void pixel(int x,int y,int r,int g,int b){
    unsigned char value[4];glReadPixels(x,y,1,1,GL_RGBA,GL_UNSIGNED_BYTE,value);
    assert(value[0]>=r-1&&value[0]<=r+1&&value[1]>=g-1&&value[1]<=g+1&&value[2]>=b-1&&value[2]<=b+1);
}
int run_hud_gles_tests(void){
    unsigned char coverage=128;size_t i;uint64_t prior;CohUiRect full={0,0,64,64};
    assert(coh_hud_gles_create(&renderer,1)==COH_OK);
    assert(coh_hud_gles_create(&renderer,1)==COH_STATE);
    glGenTextures(1,&atlas);glBindTexture(GL_TEXTURE_2D,atlas);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    glTexImage2D(GL_TEXTURE_2D,0,GL_R8,1,1,0,GL_RED,GL_UNSIGNED_BYTE,&coverage);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);
    draws[0]=rectangle(0xff0000ffu,full,full);
    draws[1]=rectangle(0x0000ffffu,(CohUiRect){0,0,32,64},full);draws[1].kind=COH_UI_DRAW_GLYPH;draws[1].resource_id=7;
    draws[2]=rectangle(0x00ff00ffu,(CohUiRect){32,0,32,64},(CohUiRect){48,16,16,16});
    assert(coh_hud_gles_draw(&renderer,64,64,1,draws,3,resolve,NULL)==COH_OK);
    pixel(8,56,127,0,128);pixel(40,40,255,0,0);pixel(56,40,0,255,0);pixel(56,8,255,0,0);
    assert(!glIsEnabled(GL_SCISSOR_TEST)&&glGetError()==GL_NO_ERROR);
    prior=renderer.stats.frames;draws[1].resource_id=8;
    assert(coh_hud_gles_draw(&renderer,64,64,1,draws,3,resolve,NULL)==COH_NOT_FOUND&&renderer.stats.frames==prior);
    draws[1].resource_id=7;assert(coh_hud_gles_draw(&renderer,64,64,2,draws,3,resolve,NULL)==COH_STATE);
    draws[1].surface_generation=2;assert(coh_hud_gles_draw(&renderer,64,64,1,draws,3,resolve,NULL)==COH_INVALID);
    draws[1].surface_generation=1;
    assert(coh_hud_gles_draw(&renderer,64,64,1,draws,COH_UI_DRAWS+1,resolve,NULL)==COH_INVALID);
    for(i=0;i<COH_HUD_GLES_BATCH_QUADS+1;i++)draws[i]=rectangle(0xffffffffu,full,full);
    prior=renderer.stats.draw_calls;
    assert(coh_hud_gles_draw(&renderer,64,64,1,draws,COH_HUD_GLES_BATCH_QUADS+1,resolve,NULL)==COH_OK);
    assert(renderer.stats.draw_calls-prior==2&&renderer.stats.batch_high_water==COH_HUD_GLES_BATCH_QUADS);
    assert(renderer.stats.gl_errors==0&&renderer.stats.preexisting_errors==0);
    assert(!glIsEnabled(GL_SCISSOR_TEST));
    printf("{\"pixel_comparisons\":4,\"channel_tolerance\":1,\"negative_cases\":5,\"batch_quads\":%u,\"batch_draw_calls\":2,\"arena_bytes\":%zu,\"GL_errors\":0}\n",COH_HUD_GLES_BATCH_QUADS,sizeof(renderer));
    coh_hud_gles_destroy(&renderer);coh_hud_gles_destroy(&renderer);
    assert(coh_hud_gles_create(&renderer,2)==COH_OK);coh_hud_gles_destroy(&renderer);
    coh_hud_gles_forget(&renderer);glDeleteTextures(1,&atlas);return 0;
}
#ifdef COH_HUD_REAL_FONT
int run_hud_original_font_tests(void){
    size_t i;int comparisons=0;unsigned char pixels[256*256*4];CohUiRect full={0,0,64,64};
    assert(coh_hud_atlas_validate(&coh_hud_font)==COH_OK);
    assert(coh_hud_gles_create(&renderer,1)==COH_OK);
    glGenTextures(1,&atlas);glBindTexture(GL_TEXTURE_2D,atlas);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    glTexImage2D(GL_TEXTURE_2D,0,GL_R8,COH_HUD_FONT_WIDTH,COH_HUD_FONT_HEIGHT,0,GL_RED,GL_UNSIGNED_BYTE,coh_hud_font_alpha);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    for(i=0;i<coh_hud_font.count;i++){
        CohUiGlyph g;int x,y,w,h,atlas_x,atlas_y;CohUiDraw d;
        assert(coh_hud_atlas_glyph(&coh_hud_font,1,coh_hud_font.entries[i].codepoint,16,&g)==COH_OK);
        w=(int)g.width;h=(int)g.height;if(!w||!h)continue;
        assert(w<60&&h<60);atlas_x=(int)(g.uv.x*COH_HUD_FONT_WIDTH);atlas_y=(int)(g.uv.y*COH_HUD_FONT_HEIGHT);
        d=rectangle(0xffffffffu,(CohUiRect){2,2,g.width,g.height},full);d.kind=COH_UI_DRAW_GLYPH;d.resource_id=7;d.uv=g.uv;
        glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);
        assert(coh_hud_gles_draw(&renderer,64,64,1,&d,1,resolve,NULL)==COH_OK);
        glReadPixels(2,64-2-h,w,h,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
        for(y=0;y<h;y++)for(x=0;x<w;x++){
            unsigned expected=coh_hud_font_alpha[(atlas_y+y)*COH_HUD_FONT_WIDTH+atlas_x+x];
            unsigned char *p=pixels+((h-1-y)*w+x)*4;
            assert(p[0]+1u>=expected&&p[0]<=expected+1u&&p[1]+1u>=expected&&p[1]<=expected+1u&&p[2]+1u>=expected&&p[2]<=expected+1u);
            comparisons++;
        }
    }
    assert(renderer.stats.gl_errors==0&&glGetError()==GL_NO_ERROR);
    coh_hud_gles_destroy(&renderer);glDeleteTextures(1,&atlas);return comparisons;
}
#endif
