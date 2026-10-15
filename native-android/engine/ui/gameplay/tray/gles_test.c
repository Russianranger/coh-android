/* Qualification-only readback. Production HUD never reads back or waits. */
#include "../coh_hud_gles.h"
#include "support_tray.h"
#include <GLES3/gl3.h>
#include <assert.h>
#include <string.h>
static CohHudGles renderer;
static GLuint textures[11];
static CohStatus resolve(void *context,uint32_t resource,CohHudTexture *texture){
    unsigned i;(void)context;
    for(i=0;i<11;i++)if(resource==coh_hud_tray_images[i].resource){
        *texture=(CohHudTexture){textures[i],0};return COH_OK;
    }
    return COH_NOT_FOUND;
}
int run_tray_gles_tests(void){
    unsigned round,i,x,y;int comparisons=0;unsigned char pixels[64*64*4];
    for(round=0;round<3;round++){
        assert(coh_hud_gles_create(&renderer,round+1)==COH_OK);glGenTextures(11,textures);
        for(i=0;i<11;i++){
            const CohHudTrayImage *image=coh_hud_tray_images+i;CohUiDraw draw;
            glBindTexture(GL_TEXTURE_2D,textures[i]);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,(GLsizei)image->width,(GLsizei)image->height,0,GL_RGBA,GL_UNSIGNED_BYTE,image->rgba);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
            memset(&draw,0,sizeof(draw));draw.kind=COH_UI_DRAW_IMAGE;draw.resource_id=image->resource;
            draw.rect=(CohUiRect){0,0,(float)image->width,(float)image->height};draw.uv=(CohUiRect){0,0,1,1};
            draw.clip=(CohUiRect){0,0,64,64};draw.color=0xffffffffu;draw.surface_generation=round+1;
            glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);
            assert(coh_hud_gles_draw(&renderer,64,64,round+1,&draw,1,resolve,NULL)==COH_OK);
            glReadPixels(0,64-(GLint)image->height,(GLsizei)image->width,(GLsizei)image->height,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
            for(y=0;y<image->height;y++)for(x=0;x<image->width;x++){
                const unsigned char *source=image->rgba+(y*image->width+x)*4;
                const unsigned char *actual=pixels+((image->height-y-1)*image->width+x)*4;unsigned channel;
                for(channel=0;channel<3;channel++){
                    unsigned expected=(source[channel]*source[3]+127u)/255u;
                    assert(actual[channel]+1u>=expected&&actual[channel]<=expected+1u);comparisons++;
                }
            }
            assert(glGetError()==GL_NO_ERROR);
        }
        assert(renderer.stats.gl_errors==0);coh_hud_gles_destroy(&renderer);glDeleteTextures(11,textures);
    }
    return comparisons;
}
