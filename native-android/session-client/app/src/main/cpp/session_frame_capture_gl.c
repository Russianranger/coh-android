#include "session_frame_capture_gl.h"
#include "session_frame_capture.h"
#include <GLES3/gl3.h>
/* Entire default framebuffer only. No window/UI capture; no shared Session
 * mutex. Targets and pack state are restored before presentation. */
int coh_frame_capture_readback(uint32_t vw,uint32_t vh,uint32_t w,uint32_t h,uint8_t *rgba){
    if(!rgba||!vw||!vh||vw>16384||vh>16384||!w||!h||w>COH_CAPTURE_WIDTH||h>COH_CAPTURE_HEIGHT)return 0;
    GLint read=0,draw=0,texture=0,pack=0,buffer=0,row=0,skipx=0,skipy=0;GLuint fbo=0,color=0;
    GLboolean scissor=glIsEnabled(GL_SCISSOR_TEST);int ok=0;
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw);
    glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);glGetIntegerv(GL_PACK_ALIGNMENT,&pack);
    glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&buffer);glGetIntegerv(GL_PACK_ROW_LENGTH,&row);
    glGetIntegerv(GL_PACK_SKIP_PIXELS,&skipx);glGetIntegerv(GL_PACK_SKIP_ROWS,&skipy);
    glGenTextures(1,&color);glBindTexture(GL_TEXTURE_2D,color);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,(GLsizei)w,(GLsizei)h);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,color,0);
    if(glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE){
        glDisable(GL_SCISSOR_TEST);glBindFramebuffer(GL_READ_FRAMEBUFFER,0);
        glBlitFramebuffer(0,0,(GLint)vw,(GLint)vh,0,0,(GLint)w,(GLint)h,GL_COLOR_BUFFER_BIT,GL_NEAREST);
        glBindFramebuffer(GL_READ_FRAMEBUFFER,fbo);glBindBuffer(GL_PIXEL_PACK_BUFFER,0);
        glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_PACK_ROW_LENGTH,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);
        glReadPixels(0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,rgba);ok=glGetError()==GL_NO_ERROR;
    }
    glBindFramebuffer(GL_READ_FRAMEBUFFER,(GLuint)read);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,(GLuint)draw);
    glBindTexture(GL_TEXTURE_2D,(GLuint)texture);glBindBuffer(GL_PIXEL_PACK_BUFFER,(GLuint)buffer);
    glPixelStorei(GL_PACK_ALIGNMENT,pack);glPixelStorei(GL_PACK_ROW_LENGTH,row);glPixelStorei(GL_PACK_SKIP_PIXELS,skipx);glPixelStorei(GL_PACK_SKIP_ROWS,skipy);
    if(scissor)glEnable(GL_SCISSOR_TEST);else glDisable(GL_SCISSOR_TEST);
    if(fbo)glDeleteFramebuffers(1,&fbo);
    if(color)glDeleteTextures(1,&color);
    if(glGetError()!=GL_NO_ERROR)ok=0;
    return ok;
}
