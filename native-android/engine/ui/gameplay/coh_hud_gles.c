#include "coh_hud_gles.h"
#include <GLES3/gl3.h>
#include <stddef.h>
#include <string.h>
static const char *vertex_source=
    "#version 300 es\nprecision highp float;\n"
    "layout(location=0) in vec2 position;layout(location=1) in vec2 uv;layout(location=2) in vec4 color;"
    "uniform vec2 viewport;out vec2 texCoord;out vec4 tint;"
    "void main(){gl_Position=vec4(position.x/viewport.x*2.0-1.0,1.0-position.y/viewport.y*2.0,0.0,1.0);texCoord=uv;tint=color;}";
static const char *fragment_source=
    "#version 300 es\nprecision mediump float;\n"
    "in vec2 texCoord;in vec4 tint;uniform sampler2D image;uniform int mode;out vec4 result;"
    "void main(){if(mode==0){result=tint;}else{vec4 sampleColor=texture(image,texCoord);"
    "result=mode==2?vec4(tint.rgb,tint.a*sampleColor.r):tint*sampleColor;}}";
static GLuint shader(CohHudGles *r,GLenum type,const char *source){
    GLint compiled=0;GLuint s=glCreateShader(type);if(!s)return 0;
    glShaderSource(s,1,&source,NULL);glCompileShader(s);glGetShaderiv(s,GL_COMPILE_STATUS,&compiled);
    if(!compiled){glGetShaderInfoLog(s,sizeof(r->shader_log),NULL,r->shader_log);glDeleteShader(s);return 0;}
    return s;
}
void coh_hud_gles_forget(CohHudGles *r){if(r)memset(r,0,sizeof(*r));}
void coh_hud_gles_destroy(CohHudGles *r){
    if(!r)return;
    if(r->vao)glDeleteVertexArrays(1,&r->vao);
    if(r->buffer)glDeleteBuffers(1,&r->buffer);
    if(r->program)glDeleteProgram(r->program);
    coh_hud_gles_forget(r);
}
CohStatus coh_hud_gles_create(CohHudGles *r,uint32_t gen){
    GLuint vs,fs;GLint linked=0;
    if(!r||!gen)return COH_INVALID;
    /* A live renderer must be explicitly destroyed/forgotten before recreation. */
    if(r->program||r->buffer||r->vao)return COH_STATE;
    memset(r,0,sizeof(*r));r->stats.arena_bytes=sizeof(*r);
    if(!glGetString(GL_VERSION))return COH_STATE;
    if(glGetError()!=GL_NO_ERROR){r->stats.preexisting_errors++;return COH_STATE;}
    vs=shader(r,GL_VERTEX_SHADER,vertex_source);if(!vs)return COH_UNSUPPORTED;
    fs=shader(r,GL_FRAGMENT_SHADER,fragment_source);if(!fs){glDeleteShader(vs);return COH_UNSUPPORTED;}
    r->program=glCreateProgram();glAttachShader(r->program,vs);glAttachShader(r->program,fs);glLinkProgram(r->program);
    glDeleteShader(vs);glDeleteShader(fs);glGetProgramiv(r->program,GL_LINK_STATUS,&linked);
    if(!linked){glGetProgramInfoLog(r->program,sizeof(r->shader_log),NULL,r->shader_log);
        glDeleteProgram(r->program);r->program=0;return COH_UNSUPPORTED;}
    r->viewport_uniform=glGetUniformLocation(r->program,"viewport");r->mode_uniform=glGetUniformLocation(r->program,"mode");
    r->sampler_uniform=glGetUniformLocation(r->program,"image");
    glGenBuffers(1,&r->buffer);glGenVertexArrays(1,&r->vao);glBindVertexArray(r->vao);glBindBuffer(GL_ARRAY_BUFFER,r->buffer);
    glBufferData(GL_ARRAY_BUFFER,sizeof(r->vertices),NULL,GL_STREAM_DRAW);
    glEnableVertexAttribArray(0);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,sizeof(CohHudVertex),(const void *)offsetof(CohHudVertex,x));
    glEnableVertexAttribArray(1);glVertexAttribPointer(1,2,GL_FLOAT,GL_FALSE,sizeof(CohHudVertex),(const void *)offsetof(CohHudVertex,u));
    glEnableVertexAttribArray(2);glVertexAttribPointer(2,4,GL_FLOAT,GL_FALSE,sizeof(CohHudVertex),(const void *)offsetof(CohHudVertex,r));
    glBindVertexArray(0);glBindBuffer(GL_ARRAY_BUFFER,0);
    if(glGetError()!=GL_NO_ERROR){coh_hud_gles_destroy(r);return COH_IO;}
    r->generation=gen;return COH_OK;
}
static int same_clip(const int a[4],const int b[4]){return a[0]==b[0]&&a[1]==b[1]&&a[2]==b[2]&&a[3]==b[3];}
static void flush(CohHudGles *r,size_t quads,int mode,uint32_t texture,const int clip[4]){
    if(!quads)return;
    glScissor(clip[0],clip[1],clip[2],clip[3]);glBindTexture(GL_TEXTURE_2D,texture);glUniform1i(r->mode_uniform,mode);
    glBufferSubData(GL_ARRAY_BUFFER,0,(GLsizeiptr)(quads*6*sizeof(CohHudVertex)),r->vertices);
    glDrawArrays(GL_TRIANGLES,0,(GLsizei)(quads*6));r->stats.draw_calls++;r->stats.quads+=quads;
    r->stats.bytes_uploaded+=quads*6*sizeof(CohHudVertex);
    if(quads>r->stats.batch_high_water)r->stats.batch_high_water=quads;
}
CohStatus coh_hud_gles_draw(CohHudGles *r,int width,int height,uint32_t gen,const CohUiDraw *draws,size_t count,CohHudTextureFn resolve,void *context){
    size_t i,quads=0;int active_clip[4]={0,0,0,0},active_mode=0;uint32_t active_texture=0;
    CohHudVertex check[6];
    if(!r||!r->program||!gen||r->generation!=gen)return COH_STATE;
    if(width<1||height<1||width>32768||height>32768||count>COH_UI_DRAWS||(!draws&&count)){r->stats.rejected_frames++;return COH_INVALID;}
    for(i=0;i<count;i++){
        if(coh_hud_quad(draws+i,gen,check)!=COH_OK){r->stats.rejected_frames++;return COH_INVALID;}
        r->resolved[i]=(CohHudTexture){0,0};
        if(draws[i].kind!=COH_UI_DRAW_RECT){
            CohStatus s=resolve?resolve(context,draws[i].resource_id,r->resolved+i):COH_NOT_FOUND;
            if(s!=COH_OK||!r->resolved[i].handle||(r->resolved[i].red_coverage!=0&&r->resolved[i].red_coverage!=1)){
                r->stats.rejected_frames++;return s==COH_OK?COH_INVALID:s;
            }
        }
    }
    if(glGetError()!=GL_NO_ERROR){r->stats.preexisting_errors++;return COH_STATE;}
    glViewport(0,0,width,height);glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFuncSeparate(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_SCISSOR_TEST);glUseProgram(r->program);glUniform2f(r->viewport_uniform,(float)width,(float)height);
    glUniform1i(r->sampler_uniform,0);glActiveTexture(GL_TEXTURE0);glBindVertexArray(r->vao);glBindBuffer(GL_ARRAY_BUFFER,r->buffer);
    for(i=0;i<count;i++){
        int clip[4],mode=draws[i].kind==COH_UI_DRAW_RECT?0:r->resolved[i].red_coverage?2:1;
        uint32_t texture=r->resolved[i].handle;
        coh_hud_scissor(draws[i].clip,width,height,clip);
        if(!clip[2]||!clip[3]||draws[i].rect.w==0||draws[i].rect.h==0)continue;
        if(quads&&(quads==COH_HUD_GLES_BATCH_QUADS||mode!=active_mode||texture!=active_texture||!same_clip(clip,active_clip))){
            flush(r,quads,active_mode,active_texture,active_clip);quads=0;
        }
        if(!quads){active_mode=mode;active_texture=texture;memcpy(active_clip,clip,sizeof(clip));}
        coh_hud_quad(draws+i,gen,r->vertices+quads*6);quads++;
    }
    flush(r,quads,active_mode,active_texture,active_clip);
    glBindVertexArray(0);glBindBuffer(GL_ARRAY_BUFFER,0);glBindTexture(GL_TEXTURE_2D,0);glUseProgram(0);
    glDisable(GL_SCISSOR_TEST);glDepthMask(GL_TRUE);
    if(glGetError()!=GL_NO_ERROR){r->stats.gl_errors++;return COH_IO;}
    r->stats.frames++;return COH_OK;
}
