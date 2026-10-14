/* Source static world/camera qualification; no map streaming/game integration.
 * Bytes and every EGL/GL object are owned by one bounded, serialized JNI call. */
#define _POSIX_C_SOURCE 200809L
#include <jni.h>
#include <android/native_window.h>
#include <android/native_window_jni.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include "coh_mesh.h"
#include "coh_world.h"
#include "coh_world_scene.h"
#include "shader_sources.h"
#include "world_shader_sources.h"

#define CYCLES 2
#define WORLD_SIZE 512
#define BYTE_TOLERANCE 2
#define FLOAT_TOLERANCE 0.0001f
#define MAX_ASSET (16u * 1024u * 1024u)
#define TEXT_CAP 512
#define JSON_CAP 65536
#define TF_FLOATS 13u
#define CHECKPOINTS 6u
#define PREVIEW_FRAMES 45u

typedef struct { uint8_t*p;size_t n; } Bytes;
typedef struct { float position[3],normal[3],uv0[2],uv1[2],clip[4],eye[3]; } Vertex;
typedef struct { uint32_t count;size_t stride;const uint8_t*data; } Materials;
typedef struct {
    const uint8_t*locals,*worlds,*cases;uint32_t case_stride,vertices,geometry_offset;
} WorldReference;
typedef struct {
    GLuint id;GLint mode,model,modelview,view,projection,light,diffuse,ambient,base,dual,const0,const1;
    GLint fog_params,fog_color,alpha_ref,reference_color,reference_fog;
} Program;
typedef struct { GLuint fbo,color,depth;int width,height; } Target;
typedef struct {
    int completed,passed,released,swap_passed,context_created;
    int group_transform_match,camera_match,world_transform_match,world_render_match,scene_assembly_match,camera_preview_passed,material_pixel_match,window_pixel_match;
    int width,height,viewport_x,viewport_y,viewport_w,viewport_h;
    unsigned gl_errors,first_gl_error,egl_error;
    uint64_t group_local_components,group_local_mismatches,group_world_components,group_world_mismatches,camera_view_components,camera_view_mismatches,projection_components,projection_mismatches,modelview_components,modelview_mismatches;
    float group_local_max_error,group_world_max_error,camera_view_max_error,projection_max_error,modelview_max_error;
    uint64_t transform_vertices,transform_components,transform_mismatches,world_position_mismatches,eye_position_mismatches,normal_mismatches,clip_mismatches;float max_transform_error;
    uint32_t first_transform_camera,first_transform_part,first_transform_vertex,first_transform_component;float first_transform_expected,first_transform_actual;int first_transform_actual_finite;
    uint64_t world_compared_pixels,world_interior_pixels,world_edge_excluded_pixels,world_mismatches;
    uint64_t world_pose_interiors[6],world_pose_compared[6],world_pose_excluded[6];
    uint64_t part_interior_pixels[COH_WORLD_PARTS],part_transform_vertices[COH_WORLD_PARTS],part_image_compared_pixels[COH_WORLD_PARTS],part_image_mismatches[COH_WORLD_PARTS];
    unsigned world_max_byte_error,world_poses,first_image_camera,first_image_part,first_image_x,first_image_y;uint8_t first_image_actual[4],first_image_expected[4];
    uint64_t material_pixels,material_mismatches,material_discard_clear_pixels;unsigned material_max_byte_error,material_cases,blend_cases,real_material_cases,synthetic_semantic_cases;
    unsigned window_samples,window_mismatches;
    unsigned preview_frames,distinct_camera_views,preview_image_samples,preview_changed_image_samples;uint64_t preview_pixels_changed_from_first,preview_elapsed_ms;
    unsigned diagnostic_cases,diagnostic_pixels,diagnostic_mismatches;
    char stage[TEXT_CAP],failure[TEXT_CAP],gl_vendor[TEXT_CAP],gl_renderer[TEXT_CAP],gl_version[TEXT_CAP],glsl_version[TEXT_CAP],egl_vendor[TEXT_CAP],egl_version[TEXT_CAP];
} Cycle;
typedef struct { Vertex*vertices,*reference;uint32_t*indices;uint32_t first_vertex; } Geometry;
typedef struct {
    int passed,world_valid,attempted;CohWorldScene scene;WorldReference reference;Materials materials;
    float local[6][12],world[6][12];char failure[TEXT_CAP];Cycle cycles[CYCLES];
} Report;
typedef struct { char*s;size_t n;int ok; } Json;
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const uint8_t *p){uint32_t b=u32(p);float f;memcpy(&f,&b,4);return f;}
static void textcopy(char *d,const char *s){(void)snprintf(d,TEXT_CAP,"%s",s?s:"");}
static const char *boolstr(int b){return b?"true":"false";}
static int fail(Cycle *c,const char *stage,const char *why){textcopy(c->stage,stage);textcopy(c->failure,why);return 0;}
static int egfail(Cycle *c,const char *stage){c->egl_error=(unsigned)eglGetError();return fail(c,stage,"EGL operation failed; Surface may have been destroyed");}
static int glcheck(Cycle *c,const char *stage){int ok=1;GLenum e;for(unsigned i=0;i<32&&(e=glGetError())!=GL_NO_ERROR;i++){c->gl_errors++;if(!c->first_gl_error)c->first_gl_error=e;ok=0;}return ok?1:fail(c,stage,"GL error");}
static void append(Json *j,const char *fmt,...) __attribute__((format(printf,2,3)));
static void append(Json *j,const char *fmt,...){if(!j->ok)return;va_list a;va_start(a,fmt);int n=vsnprintf(j->s+j->n,JSON_CAP-j->n,fmt,a);va_end(a);if(n<0||(size_t)n>=JSON_CAP-j->n){j->ok=0;return;}j->n+=(size_t)n;}
static void string(Json *j,const char *s){append(j,"\"");for(const unsigned char *p=(const unsigned char*)s;*p&&j->ok;p++){if(*p=='"'||*p=='\\')append(j,"\\%c",*p);else if(*p<32||*p>=127)append(j,"\\u%04x",*p);else append(j,"%c",*p);}append(j,"\"");}

static int copy_java(JNIEnv*env,jbyteArray a,Bytes*out){if(!a)return 0;jsize n=(*env)->GetArrayLength(env,a);if(n<=0||(size_t)n>MAX_ASSET)return 0;out->p=malloc((size_t)n);if(!out->p)return 0;out->n=(size_t)n;(*env)->GetByteArrayRegion(env,a,0,n,(jbyte*)out->p);if((*env)->ExceptionCheck(env)){(*env)->ExceptionClear(env);return 0;}return 1;}
static void floats(const uint8_t*p,float*f,unsigned n){for(unsigned i=0;i<n;i++)f[i]=f32(p+i*4);}
static int reserved_zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
static GLuint shader(Cycle*c,GLenum type,const char*source){GLuint s=glCreateShader(type);if(!s){fail(c,"shader-create","Shader allocation failed");return 0;}glShaderSource(s,1,&source,NULL);glCompileShader(s);GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char log[TEXT_CAP]={0};glGetShaderInfoLog(s,TEXT_CAP,NULL,log);fail(c,"shader-compile",log[0]?log:"Shader compilation failed");glDeleteShader(s);return 0;}return s;}
static int program_create(Cycle*c,Program*p,const char*v,const char*f,int transform){
    GLuint vs=shader(c,GL_VERTEX_SHADER,v);if(!vs)return 0;GLuint fs=shader(c,GL_FRAGMENT_SHADER,f);if(!fs){glDeleteShader(vs);return 0;}
    p->id=glCreateProgram();if(!p->id){glDeleteShader(vs);glDeleteShader(fs);return fail(c,"program-create","Program allocation failed");}
    glAttachShader(p->id,vs);glAttachShader(p->id,fs);if(transform){const char*varyings[]={"vWorldPosition","vEyeNormal","vEyePosition","vClipPosition"};glTransformFeedbackVaryings(p->id,4,varyings,GL_INTERLEAVED_ATTRIBS);}glLinkProgram(p->id);glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;glGetProgramiv(p->id,GL_LINK_STATUS,&ok);if(!ok){char log[TEXT_CAP]={0};glGetProgramInfoLog(p->id,TEXT_CAP,NULL,log);return fail(c,"program-link",log[0]?log:"Program linking failed");}
#define U(field,name) p->field=glGetUniformLocation(p->id,name)
    U(mode,"uMaterialMode");U(projection,"uProjection");U(model,"uModel");U(view,"uView");U(modelview,"uModelView");U(light,"uLightDir");U(diffuse,"uDiffuse");U(ambient,"uAmbient");U(base,"uBase");U(dual,"uDual");U(const0,"uConst0");U(const1,"uConst1");U(fog_params,"uFogParams");U(fog_color,"uFogColor");U(alpha_ref,"uAlphaRef");U(reference_color,"uReferenceColor");U(reference_fog,"uReferenceFogCoord");
#undef U
    return glcheck(c,"program-build");
}
static int texture_create(Cycle*c,GLuint*out,unsigned w,unsigned h,const uint8_t*rgba){glGenTextures(1,out);glBindTexture(GL_TEXTURE_2D,*out);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,(GLsizei)w,(GLsizei)h);if(rgba)glTexSubImage2D(GL_TEXTURE_2D,0,0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,rgba);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return glcheck(c,"texture-create");}
static int scene_texture_filter(Cycle*c,const GLuint*textures,unsigned count,GLenum filter){
    glActiveTexture(GL_TEXTURE0);
    for(unsigned i=0;i<count;i++){glBindTexture(GL_TEXTURE_2D,textures[i]);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,(GLint)filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,(GLint)filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_BASE_LEVEL,0);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,0);}
    return glcheck(c,filter==GL_LINEAR?"character-linear-mip0-sampler":"analytic-material-nearest-mip0-sampler");
}
static int target_create(Cycle*c,Target*t,int size,int depth){t->width=t->height=size;if(!texture_create(c,&t->color,(unsigned)size,(unsigned)size,NULL))return 0;glGenFramebuffers(1,&t->fbo);glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t->color,0);if(depth){glGenRenderbuffers(1,&t->depth);glBindRenderbuffer(GL_RENDERBUFFER,t->depth);glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT24,size,size);glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,t->depth);}if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail(c,"fbo-status","RGBA8 framebuffer incomplete");return glcheck(c,"fbo-create");}
static void target_delete(Target*t){if(t->fbo)glDeleteFramebuffers(1,&t->fbo);if(t->color)glDeleteTextures(1,&t->color);if(t->depth)glDeleteRenderbuffers(1,&t->depth);}
static void bind_textures(Program*p,GLuint base,GLuint dual){glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,base);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,dual);glUniform1i(p->base,0);glUniform1i(p->dual,1);}
static void material_uniforms(Program*p,const uint8_t*record){float v[24];floats(record,v,24);glUniform4fv(p->const0,1,v);glUniform4fv(p->const1,1,v+4);glUniform4fv(p->reference_color,1,v+8);glUniform4fv(p->fog_params,1,v+12);glUniform4fv(p->fog_color,1,v+16);glUniform1f(p->reference_fog,f32(record+96));glUniform1f(p->alpha_ref,f32(record+100));}
static void vertex_layout(GLuint vao,GLuint vbo,GLuint indices){glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,indices);
#define A(loc,count,field) glVertexAttribPointer(loc,count,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)offsetof(Vertex,field));glEnableVertexAttribArray(loc)
A(0,3,position);A(1,3,normal);A(2,2,uv0);A(3,2,uv1);A(4,4,clip);A(5,3,eye);
#undef A
}
static unsigned pixel_error(const uint8_t*a,const uint8_t*b,unsigned channels){unsigned max=0;for(unsigned k=0;k<channels;k++){unsigned d=a[k]>b[k]?a[k]-b[k]:b[k]-a[k];if(d>max)max=d;}return max;}
static void edge_mark(uint8_t*mask,float ax,float ay,float bx,float by){
    int minx=(int)floorf(fminf(ax,bx)-2.0f),maxx=(int)ceilf(fmaxf(ax,bx)+2.0f),miny=(int)floorf(fminf(ay,by)-2.0f),maxy=(int)ceilf(fmaxf(ay,by)+2.0f);
    if(minx<0)minx=0;if(miny<0)miny=0;if(maxx>=WORLD_SIZE)maxx=WORLD_SIZE-1;if(maxy>=WORLD_SIZE)maxy=WORLD_SIZE-1;
    float dx=bx-ax,dy=by-ay,len=dx*dx+dy*dy;
    for(int y=miny;y<=maxy;y++)for(int x=minx;x<=maxx;x++){float px=x+.5f-ax,py=y+.5f-ay,t=len>0?(px*dx+py*dy)/len:0;if(t<0)t=0;if(t>1)t=1;float ex=px-t*dx,ey=py-t*dy;if(ex*ex+ey*ey<=4.0f)mask[y*WORLD_SIZE+x]=1;}
}
static int display_window(Cycle*c,EGLDisplay d,EGLSurface surface,Target*t,GLuint program,
                          GLuint vao,GLuint vbo,const uint8_t*image,int validate){
    EGLint w=0,h=0;if(!eglQuerySurface(d,surface,EGL_WIDTH,&w)||!eglQuerySurface(d,surface,EGL_HEIGHT,&h))return egfail(c,"surface-query");
    if(w<=0||h<=0||w>16384||h>16384)return fail(c,"surface-size","Surface dimensions outside bounded positive range");c->width=w;c->height=h;
    int size=w<h?w:h;c->viewport_w=c->viewport_h=size;c->viewport_x=(w-size)/2;c->viewport_y=(h-size)/2;
    const float quad[]={-1,-1,1,-1,1,1,-1,-1,1,1,-1,1};glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,2*sizeof(float),(void*)0);glEnableVertexAttribArray(0);glDisableVertexAttribArray(2);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,w,h);glClearColor(.04f,.04f,.06f,1);glClear(GL_COLOR_BUFFER_BIT);glViewport(c->viewport_x,c->viewport_y,size,size);glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,t->color);glUniform1i(glGetUniformLocation(program,"uImage"),0);glUniform4i(glGetUniformLocation(program,"uViewport"),c->viewport_x,c->viewport_y,size,size);glDrawArrays(GL_TRIANGLES,0,6);if(!glcheck(c,"window-draw"))return 0;
    if(validate){
        for(int gy=1;gy<=7;gy++)for(int gx=1;gx<=7;gx++){int lx=gx*size/8,ly=gy*size/8;if(lx>=size)lx=size-1;if(ly>=size)ly=size-1;unsigned tx=(unsigned)(((uint64_t)(2*lx+1)*WORLD_SIZE)/(2u*(unsigned)size)),ty=(unsigned)(((uint64_t)(2*ly+1)*WORLD_SIZE)/(2u*(unsigned)size));uint8_t got[4]={0};glReadPixels(c->viewport_x+lx,c->viewport_y+ly,1,1,GL_RGBA,GL_UNSIGNED_BYTE,got);if(!glcheck(c,"window-readback"))return 0;c->window_samples++;if(pixel_error(got,image+((size_t)ty*WORLD_SIZE+tx)*4,3))c->window_mismatches++;}
        if(c->window_mismatches)return fail(c,"window-parity","Opaque RGB window samples differ from final qualified mesh FBO");c->window_pixel_match=1;
    }
    if(!eglSwapBuffers(d,surface))return egfail(c,"swap-buffers");c->swap_passed=1;return glcheck(c,"post-swap");
}


static int material_check(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,const GLuint*textures,GLuint controlled,const Report*r,uint8_t*readback){
    static const float quad[]={-1,-1,0,0,1,-1,1,0,1,1,1,1,-1,-1,0,0,1,1,1,1,-1,1,0,1};glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)0);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)(2*sizeof(float)));glEnableVertexAttribArray(0);glEnableVertexAttribArray(2);
    glUseProgram(p->id);glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,64,64);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    for(uint32_t i=0;i<r->materials.count;i++){const uint8_t*record=r->materials.data+i*r->materials.stride;const CohWorldPart*part=&r->scene.parts[u32(record+108)];uint32_t flags=u32(record+104);glUniform1i(p->mode,(int)part->mode);bind_textures(p,textures[part->base_texture],flags&2u?controlled:textures[part->dual_texture]);if(flags&2u)c->synthetic_semantic_cases++;else c->real_material_cases++;float clear[4];floats(record+80,clear,4);glClearColor(clear[0],clear[1],clear[2],clear[3]);glClear(GL_COLOR_BUFFER_BIT);if(flags&1u){glEnable(GL_BLEND);c->blend_cases++;}else glDisable(GL_BLEND);material_uniforms(p,record);glDrawArrays(GL_TRIANGLES,0,6);glReadPixels(0,0,64,64,GL_RGBA,GL_UNSIGNED_BYTE,readback);if(!glcheck(c,"world-material-readback"))return 0;
        uint8_t clear_bytes[4];for(unsigned k=0;k<4;k++){float x=fminf(1,fmaxf(0,clear[k]));clear_bytes[k]=(uint8_t)floorf(x*255+.5f);}const uint8_t*golden=record+128;for(unsigned k=0;k<64*64;k++){unsigned error=pixel_error(readback+k*4,golden+k*4,4);c->material_pixels++;if(error>c->material_max_byte_error)c->material_max_byte_error=error;if(error>BYTE_TOLERANCE)c->material_mismatches++;if(!memcmp(golden+k*4,clear_bytes,4))c->material_discard_clear_pixels++;}c->material_cases++;
    }
    glDisable(GL_BLEND);return c->material_mismatches?fail(c,"world-material-parity","Actual per-part texture/color CPU references differ from native dual shader"):1;
}
static uint64_t monotonic_ms(const struct timespec*t){return (uint64_t)t->tv_sec*1000+(uint64_t)t->tv_nsec/1000000;}
static int world_reference_parse(Bytes b,const CohWorldScene*s,WorldReference*out){
    if(b.n<640||memcmp(b.p,"COHWRF09",8)||u32(b.p+8)!=1||u32(b.p+12)!=64||u32(b.p+16)!=6||u32(b.p+20)!=6||u32(b.p+24)!=s->vertices||u32(b.p+28)!=s->part_count||u32(b.p+32)!=64||u32(b.p+36)!=352||u32(b.p+40)!=640||u32(b.p+44)!=160+s->vertices*52||u32(b.p+48)!=b.n||u32(b.p+52)!=160||!reserved_zero(b.p+56,8)||b.n!=640+(size_t)6*u32(b.p+44))return 0;
    for(size_t i=64;i<b.n;i+=4)if(!isfinite(f32(b.p+i))||fabsf(f32(b.p+i))>1000000)return 0;
    *out=(WorldReference){b.p+64,b.p+352,b.p+640,u32(b.p+44),s->vertices,160};return 1;
}
static int material_parse(Bytes b,const CohWorldScene*s,Materials*out){
    if(b.n<64||memcmp(b.p,"COHWMAT9",8)||u32(b.p+8)!=1||u32(b.p+12)!=64||u32(b.p+16)!=64||u32(b.p+20)!=64||u32(b.p+24)!=s->part_count*6||u32(b.p+28)!=128||u32(b.p+32)!=s->part_count||u32(b.p+36)!=16384||u32(b.p+40)!=16512||u32(b.p+44)!=64||u32(b.p+48)!=b.n||!reserved_zero(b.p+52,12)||b.n!=64+s->part_count*6*16512)return 0;
    for(unsigned i=0;i<s->part_count*6;i++){const uint8_t*p=b.p+64+i*16512;
        for(unsigned o=0;o<104;o+=4)if(!isfinite(f32(p+o))||fabsf(f32(p+o))>1000000)return 0;
        if(f32(p+100)<0||f32(p+100)>1||(u32(p+104)&~3u)||u32(p+108)!=i/6||u32(p+112)!=i%6||u32(p+116)!=s->parts[i/6].mode||!reserved_zero(p+120,8))return 0;
        for(unsigned k=0;k<8;k++){float expected=k==3&&i%6==1?.5f:k<4?s->parts[i/6].const0[k]:s->parts[i/6].const1[k-4];if(f32(p+k*4)!=expected)return 0;}
        const uint32_t flags[6]={0,1,0,1,2,3};const float refs[6]={0,0,0,1,0,.6f};
        if(u32(p+104)!=flags[i%6]||f32(p+100)!=refs[i%6]||f32(p+96)!=(i%6==2?15.f:0.f))return 0;
    }
    *out=(Materials){s->part_count*6,16512,b.p+64};return 1;
}
static void compare_scalar(float actual,float expected,uint64_t*count,uint64_t*mismatches,float*max){(*count)++;float error=fabsf(actual-expected);if(isfinite(error)&&error>*max)*max=error;if(!isfinite(actual)||error>FLOAT_TOLERANCE)(*mismatches)++;}
static const uint8_t*camera_gold(const Report*r,unsigned camera){return r->reference.cases+(size_t)camera*r->reference.case_stride;}
static const uint8_t*vertex_gold(const Report*r,const Geometry*g,unsigned camera){return camera_gold(r,camera)+160+(size_t)g->first_vertex*52;}
static int math_check(Cycle*c,const Report*r){
    for(unsigned i=0;i<6;i++)for(unsigned k=0;k<12;k++){
        compare_scalar(r->local[i][k],f32(r->reference.locals+i*48+k*4),&c->group_local_components,&c->group_local_mismatches,&c->group_local_max_error);
        compare_scalar(r->world[i][k],f32(r->reference.worlds+i*48+k*4),&c->group_world_components,&c->group_world_mismatches,&c->group_world_max_error);
    }
    c->group_transform_match=!c->group_local_mismatches&&!c->group_world_mismatches;
    for(unsigned i=0;i<6;i++){float view[12],proj[16],eye[6][12];if(coh_world_camera(&r->scene.inputs,i,0,view,proj)||coh_world_group_eye_matrices(&r->scene.inputs,view,eye))return fail(c,"native-camera","Source Pos/PYR/view/perspective evaluation failed");const uint8_t*p=camera_gold(r,i);
        for(unsigned k=0;k<12;k++)compare_scalar(view[k],f32(p+k*4),&c->camera_view_components,&c->camera_view_mismatches,&c->camera_view_max_error);
        for(unsigned k=0;k<16;k++)compare_scalar(proj[k],f32(p+48+k*4),&c->projection_components,&c->projection_mismatches,&c->projection_max_error);
        for(unsigned k=0;k<12;k++)compare_scalar(eye[5][k],f32(p+112+k*4),&c->modelview_components,&c->modelview_mismatches,&c->modelview_max_error);
    }
    c->camera_match=!c->camera_view_mismatches&&!c->projection_mismatches&&!c->modelview_mismatches;
    return c->group_transform_match&&c->camera_match?1:fail(c,"source-matrix-parity","Native hierarchy/view/projection differs from independently compiled source kernels");
}
static void world_uniforms(Program*p,const CohWorldPart*part,const GLuint*textures,const float*model,const float*view,const float*proj){
    float m[16],v[16];coh_world_gl_matrix(model,m);coh_world_gl_matrix(view,v);glUseProgram(p->id);glUniform1i(p->mode,(int)part->mode);glUniformMatrix4fv(p->model,1,GL_FALSE,m);glUniformMatrix4fv(p->modelview,1,GL_FALSE,v);glUniformMatrix4fv(p->projection,1,GL_FALSE,proj);
    glUniform3f(p->light,.188144f,.282216f,.940721f);glUniform4f(p->diffuse,0,0,0,0);glUniform4f(p->ambient,.25f*part->ambient_scale,.25f*part->ambient_scale,.25f*part->ambient_scale,1);
    glUniform4fv(p->const0,1,part->const0);glUniform4fv(p->const1,1,part->const1);glUniform4f(p->fog_params,0,0,1000000,1);glUniform4f(p->fog_color,0,0,0,1);glUniform1f(p->alpha_ref,part->alpha_ref);bind_textures(p,textures[part->base_texture],textures[part->dual_texture]);
}
static int transform_check(Cycle*c,Program*p,GLuint vao,GLuint vbo,GLuint ibo,GLuint tf,const Report*r,const Geometry*g,const GLuint*textures,unsigned part,unsigned camera,const float*view,const float*proj){
    const CohWorldPart*draw=&r->scene.parts[part];world_uniforms(p,draw,textures,r->world[draw->node],view,proj);vertex_layout(vao,vbo,ibo);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)draw->mesh.vertex_count*sizeof(Vertex)),g->vertices,GL_DYNAMIC_DRAW);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(GLsizeiptr)((size_t)draw->mesh.vertex_count*TF_FLOATS*4),NULL,GL_DYNAMIC_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,tf);glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,(GLsizei)draw->mesh.vertex_count);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);if(!glcheck(c,"world-transform-feedback"))return 0;
    const float*actual=glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,(GLsizeiptr)((size_t)draw->mesh.vertex_count*TF_FLOATS*4),GL_MAP_READ_BIT);if(!actual)return fail(c,"transform-map","Transform-feedback buffer could not be mapped");const uint8_t*gold=vertex_gold(r,g,camera);
    for(unsigned i=0;i<draw->mesh.vertex_count;i++){c->transform_vertices++;c->part_transform_vertices[part]++;for(unsigned k=0;k<13;k++){float expect=f32(gold+(i*13+k)*4),got=actual[i*13+k],error=fabsf(expect-got);c->transform_components++;if(isfinite(error)&&error>c->max_transform_error)c->max_transform_error=error;if(!isfinite(got)||error>FLOAT_TOLERANCE){
        if(!c->transform_mismatches){c->first_transform_camera=camera;c->first_transform_part=part;c->first_transform_vertex=i;c->first_transform_component=k;c->first_transform_expected=expect;c->first_transform_actual=isfinite(got)?got:0;c->first_transform_actual_finite=isfinite(got);}
        c->transform_mismatches++;if(k<3)c->world_position_mismatches++;else if(k<6)c->normal_mismatches++;else if(k<9)c->eye_position_mismatches++;else c->clip_mismatches++;
    }}}
    if(!glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER))return fail(c,"transform-unmap","Transform-feedback data became invalid");glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);if(!glcheck(c,"transform-readback"))return 0;return c->transform_mismatches?fail(c,"transform-parity","GPU world/eye/clip/source-normal differs from source oracle"):1;
}
static void reference_vertices(const Report*r,Geometry*g,unsigned part,unsigned camera){
    const uint8_t*gold=vertex_gold(r,g,camera);for(unsigned i=0;i<r->scene.parts[part].mesh.vertex_count;i++){g->reference[i]=g->vertices[i];floats(gold+i*52+12,g->reference[i].normal,3);floats(gold+i*52+24,g->reference[i].eye,3);floats(gold+i*52+36,g->reference[i].clip,4);}
}
static void target_clear(Target*t){glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,WORLD_SIZE,WORLD_SIZE);glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClearColor(17/255.f,19/255.f,23/255.f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);}
static int part_draw(Cycle*c,Program*p,GLuint vao,GLuint vbo,GLuint ibo,const CohWorldPart*part,const Geometry*g,const Vertex*vertices,const GLuint*textures,const float*model,const float*view,const float*proj){
    glFrontFace(GL_CW);glCullFace(GL_BACK);if(part->flags&1u)glDisable(GL_CULL_FACE);else glEnable(GL_CULL_FACE);if(part->flags&2u){glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
    world_uniforms(p,part,textures,model,view,proj);vertex_layout(vao,vbo,ibo);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)part->mesh.vertex_count*sizeof(Vertex)),vertices,GL_DYNAMIC_DRAW);glBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)((size_t)part->mesh.index_count*4),g->indices,GL_DYNAMIC_DRAW);glDrawElements(GL_TRIANGLES,(GLsizei)part->mesh.index_count,GL_UNSIGNED_INT,(void*)0);return glcheck(c,"world-part-draw");
}
static int world_draw(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,GLuint ibo,const Report*r,const Geometry*g,const GLuint*textures,const float eye[6][12],const float*proj,int reference,int only_part,uint8_t*out){
    target_clear(t);for(unsigned i=0;i<r->scene.part_count;i++)if(only_part<0||i==(unsigned)only_part)if(!part_draw(c,p,vao,vbo,ibo,&r->scene.parts[i],&g[i],reference?g[i].reference:g[i].vertices,textures,r->world[r->scene.parts[i].node],eye[r->scene.parts[i].node],proj))return 0;
    glDisable(GL_BLEND);if(out){glReadPixels(0,0,WORLD_SIZE,WORLD_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,out);return glcheck(c,"world-image-readback");}return 1;
}
/* Homogeneous Sutherland-Hodgman clipping includes real near/far and side-plane
 * edges in the same fixed two-pixel guard as ordinary triangle boundaries. */
static float plane_distance(const float*p,unsigned plane){unsigned axis=plane/2;return p[3]+(plane%2?-p[axis]:p[axis]);}
static void triangle_edges(const Vertex*v,const uint32_t*idx,uint8_t*mask){
    float polygon[12][4],next[12][4];unsigned count=3;for(unsigned i=0;i<3;i++)memcpy(polygon[i],v[idx[i]].clip,16);
    for(unsigned plane=0;plane<6&&count;plane++){unsigned out=0;for(unsigned i=0;i<count;i++){const float*a=polygon[i],*b=polygon[(i+1)%count];float da=plane_distance(a,plane),db=plane_distance(b,plane);int ina=da>=0,inb=db>=0;
        if(ina&&out<12)memcpy(next[out++],a,16);if(ina!=inb&&out<12){float t=da/(da-db);for(unsigned k=0;k<4;k++)next[out][k]=a[k]+t*(b[k]-a[k]);out++;}}
        count=out;memcpy(polygon,next,count*16);
    }
    for(unsigned i=0;i<count;i++){const float*a=polygon[i],*b=polygon[(i+1)%count];if(a[3]>1e-8f&&b[3]>1e-8f)edge_mark(mask,(a[0]/a[3]+1)*(.5f*WORLD_SIZE),(a[1]/a[3]+1)*(.5f*WORLD_SIZE),(b[0]/b[3]+1)*(.5f*WORLD_SIZE),(b[1]/b[3]+1)*(.5f*WORLD_SIZE));}
}
static void image_edges(const Report*r,const Geometry*g,int part,uint8_t*mask){memset(mask,0,WORLD_SIZE*WORLD_SIZE);for(unsigned p=0;p<r->scene.part_count;p++)if(part<0||p==(unsigned)part)for(unsigned i=0;i<r->scene.parts[p].mesh.index_count;i+=3)triangle_edges(g[p].reference,g[p].indices+i,mask);}
static int compare_image(Cycle*c,const uint8_t*actual,const uint8_t*expected,const uint8_t*edges,unsigned camera,int part){
    uint64_t useful=0,compared=0,excluded=0,mismatch=0;unsigned max=0;
    for(unsigned i=0;i<WORLD_SIZE*WORLD_SIZE;i++){if(edges[i]){excluded++;continue;}compared++;unsigned e=pixel_error(actual+i*4,expected+i*4,4);if(e>max)max=e;if(e>BYTE_TOLERANCE){if(!c->world_mismatches&&!mismatch){c->first_image_camera=camera;c->first_image_part=part<0?UINT32_MAX:(unsigned)part;c->first_image_x=i%WORLD_SIZE;c->first_image_y=i/WORLD_SIZE;memcpy(c->first_image_actual,actual+i*4,4);memcpy(c->first_image_expected,expected+i*4,4);}mismatch++;}
        if(expected[i*4]!=17||expected[i*4+1]!=19||expected[i*4+2]!=23)useful++;
    }
    if(part>=0){c->part_image_compared_pixels[part]+=compared;c->part_image_mismatches[part]+=mismatch;c->part_interior_pixels[part]+=useful;}
    else{c->world_poses++;c->world_pose_compared[camera]=compared;c->world_pose_excluded[camera]=excluded;c->world_pose_interiors[camera]=useful;c->world_compared_pixels+=compared;c->world_edge_excluded_pixels+=excluded;c->world_interior_pixels+=useful;c->world_mismatches+=mismatch;if(max>c->world_max_byte_error)c->world_max_byte_error=max;if(useful<64)return fail(c,"world-image-coverage","A controlled perspective camera lacks 64 unguarded object pixels");}
    return mismatch?fail(c,"world-image-parity","Native perspective geometry image differs from independent source geometry image outside fixed two-pixel triangle guards"):1;
}
static int world_render(Cycle*c,Target*t,Program*world,Program*reference,GLuint vao,GLuint vbo,GLuint ibo,const Report*r,Geometry*g,const GLuint*textures,unsigned camera,const float eye[6][12],const float*proj,uint8_t*actual,uint8_t*expected,uint8_t*edges){
    for(unsigned p=0;p<r->scene.part_count;p++)reference_vertices(r,&g[p],p,camera);
    for(unsigned p=0;p<r->scene.part_count;p++){if(!world_draw(c,t,world,vao,vbo,ibo,r,g,textures,eye,proj,0,(int)p,actual)||!world_draw(c,t,reference,vao,vbo,ibo,r,g,textures,eye,proj,1,(int)p,expected))return 0;image_edges(r,g,(int)p,edges);if(!compare_image(c,actual,expected,edges,camera,(int)p))return 0;}
    if(!world_draw(c,t,world,vao,vbo,ibo,r,g,textures,eye,proj,0,-1,actual)||!world_draw(c,t,reference,vao,vbo,ibo,r,g,textures,eye,proj,1,-1,expected))return 0;image_edges(r,g,-1,edges);return compare_image(c,actual,expected,edges,camera,-1);
}
static int diagnostic_draw(Cycle*c,GLuint program,GLuint vao,GLuint vbo,float z,int reverse,int triangle,int near_cross){
    const float quad[6][2]={{-.8f,-.8f},{-.8f,.8f},{.8f,.8f},{-.8f,-.8f},{.8f,.8f},{.8f,-.8f}};
    const float tri[3][2]={{-.8f,-.8f},{0,.8f},{.8f,-.8f}};float data[6][4];unsigned count=triangle?3:6;
    for(unsigned i=0;i<count;i++){unsigned source=reverse?count-1-i:i;data[i][0]=triangle?tri[source][0]:quad[source][0];data[i][1]=triangle?tri[source][1]:quad[source][1];data[i][2]=near_cross&&source==1?-2.f:z;data[i][3]=1;}
    glUseProgram(program);glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)(count*sizeof data[0]),data,GL_DYNAMIC_DRAW);glVertexAttribPointer(0,4,GL_FLOAT,GL_FALSE,16,(void*)0);glEnableVertexAttribArray(0);glDrawArrays(GL_TRIANGLES,0,(GLsizei)count);return glcheck(c,"controlled-depth-cull-clip-draw");
}
static int diagnostic_check(Cycle*c,Target*t,GLuint program,GLuint vao,GLuint vbo){
    for(unsigned test=0;test<5;test++){
        target_clear(t);glDisable(GL_BLEND);glEnable(GL_CULL_FACE);glFrontFace(GL_CW);glCullFace(GL_BACK);glUseProgram(program);GLint color=glGetUniformLocation(program,"uColor");
        if(test<2){for(unsigned draw=0;draw<2;draw++){int near=(test==0?draw==0:draw==1);glUniform4f(color,near?0.f:1.f,near?1.f:0.f,0,1);if(!diagnostic_draw(c,program,vao,vbo,near?-.5f:.5f,0,0,0))return 0;}}
        if(test==2){glUniform4f(color,0,1,0,1);if(!diagnostic_draw(c,program,vao,vbo,0,0,0,0))return 0;glUniform4f(color,1,0,0,1);if(!diagnostic_draw(c,program,vao,vbo,0,1,0,0))return 0;}
        if(test==3){glUniform4f(color,0,1,0,1);if(!diagnostic_draw(c,program,vao,vbo,0,0,1,1))return 0;}
        if(test==4){glUniform4f(color,1,0,0,1);if(!diagnostic_draw(c,program,vao,vbo,2,0,0,0))return 0;}
        for(unsigned iy=0;iy<5;iy++)for(unsigned ix=0;ix<5;ix++){
            const float ys[5]={-.5f,-.3f,-.1f,.2f,.4f};float x=-.15f+.075f*ix,y=test==3?ys[iy]:-.15f+.075f*iy;
            unsigned px=(unsigned)((x+1)*(.5f*WORLD_SIZE)),py=(unsigned)((y+1)*(.5f*WORLD_SIZE));uint8_t actual[4];glReadPixels((GLint)px,(GLint)py,1,1,GL_RGBA,GL_UNSIGNED_BYTE,actual);const uint8_t green[4]={0,255,0,255},clear[4]={17,19,23,255};const uint8_t*expect=test==4||(test==3&&iy>=3)?clear:green;c->diagnostic_pixels++;if(pixel_error(actual,expect,4)>BYTE_TOLERANCE)c->diagnostic_mismatches++;
        }
        if(!glcheck(c,"controlled-depth-cull-clip-readback"))return 0;c->diagnostic_cases++;
    }
    return c->diagnostic_mismatches?fail(c,"controlled-depth-cull-clip","Labelled diagnostic depth ordering/CW culling/near crossing/far reject pixels differ"):1;
}
static int camera_preview(Cycle*c,EGLDisplay d,EGLSurface surface,Target*t,Program*world,GLuint present,GLuint vao,GLuint vbo,GLuint ibo,GLuint qvao,GLuint qvbo,const Report*r,const Geometry*g,const GLuint*textures,uint8_t*actual,uint8_t*first_image){
    struct timespec start;if(clock_gettime(CLOCK_MONOTONIC,&start))return fail(c,"preview-clock","Monotonic clock unavailable");float distinct[PREVIEW_FRAMES][28];
    for(unsigned tick=0;tick<PREVIEW_FRAMES;tick++){
        CohWorldInputs live=r->scene.inputs;float tvalue=(float)tick/44.f;const CohWorldCamera*a=&r->scene.inputs.cameras[0],*b=&r->scene.inputs.cameras[1];float amount=tvalue<=.5f?tvalue*2.f:(1.f-tvalue)*2.f;CohWorldCamera*camera=&live.cameras[0];
        for(unsigned k=0;k<3;k++){camera->position[k]=a->position[k]+amount*(b->position[k]-a->position[k]);camera->pyr_degrees[k]=a->pyr_degrees[k]+amount*(b->pyr_degrees[k]-a->pyr_degrees[k]);}
        camera->fovy=a->fovy+amount*(b->fovy-a->fovy);camera->aspect=a->aspect+amount*(b->aspect-a->aspect);camera->znear=a->znear+amount*(b->znear-a->znear);camera->zfar=a->zfar+amount*(b->zfar-a->zfar);camera->flip_x=a->flip_x;camera->flip_y=a->flip_y;
        float view[12],proj[16],flat[28],eye[6][12];if(coh_world_camera(&live,0,0,view,proj)||coh_world_group_eye_matrices(&live,view,eye))return fail(c,"preview-source-camera","Native source camera evaluation failed");memcpy(flat,view,48);memcpy(flat+12,proj,64);int known=0;for(unsigned i=0;i<c->distinct_camera_views;i++)if(!memcmp(distinct[i],flat,sizeof flat)){known=1;break;}if(!known){memcpy(distinct[c->distinct_camera_views],flat,sizeof flat);c->distinct_camera_views++;}
        int capture=tick==0||tick==15||tick==30;if(!world_draw(c,t,world,vao,vbo,ibo,r,g,textures,eye,proj,0,-1,capture?actual:NULL))return 0;
        if(capture){c->preview_image_samples++;if(!tick)memcpy(first_image,actual,WORLD_SIZE*WORLD_SIZE*4);else{uint64_t changed=0;for(unsigned i=0;i<WORLD_SIZE*WORLD_SIZE;i++)if(pixel_error(actual+i*4,first_image+i*4,4)>BYTE_TOLERANCE)changed++;if(changed)c->preview_changed_image_samples++;c->preview_pixels_changed_from_first+=changed;}}
        if(!display_window(c,d,surface,t,present,qvao,qvbo,NULL,0))return 0;c->preview_frames++;
        uint64_t ns=(uint64_t)start.tv_nsec+(uint64_t)(tick+1)*(1000000000u/30u);struct timespec deadline={start.tv_sec+(time_t)(ns/1000000000u),(long)(ns%1000000000u)};int status;do{status=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&deadline,NULL);}while(status==EINTR);if(status)return fail(c,"preview-pacing","Bounded camera preview pacing failed");
    }
    struct timespec end;if(clock_gettime(CLOCK_MONOTONIC,&end))return fail(c,"preview-clock","Monotonic end clock unavailable");c->preview_elapsed_ms=monotonic_ms(&end)-monotonic_ms(&start);
    if(c->preview_frames!=45||c->distinct_camera_views<2||c->preview_image_samples!=3||!c->preview_changed_image_samples||c->preview_pixels_changed_from_first<64)return fail(c,"preview-coverage","Preview lacks 45 native camera views and actual visible temporal change");c->camera_preview_passed=1;glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glReadPixels(0,0,WORLD_SIZE,WORLD_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,actual);if(!glcheck(c,"preview-final-image"))return 0;return display_window(c,d,surface,t,present,qvao,qvbo,actual,1);
}
static int cycle_run(ANativeWindow*window,const Report*r,Geometry*g,uint8_t*actual,uint8_t*expected,uint8_t*edges,Cycle*c){
    EGLDisplay d=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;int initialized=0,current=0,success=0;
    GLuint textures[COH_WORLD_TEXTURES]={0},controlled=0,vao=0,vbo=0,ibo=0,tf=0,qvao=0,qvbo=0;Program world={0},reference={0},material={0},present={0},diagnostic={0};Target world_target={0},material_target={0};
    EGLint maj=0,min=0,n=0,visual=0;EGLConfig config=NULL;const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT_KHR,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,0,EGL_STENCIL_SIZE,0,EGL_NONE};const EGLint ctxattrs[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
    const char*pv="#version 300 es\nlayout(location=0) in vec2 aPosition; void main(){gl_Position=vec4(aPosition,0,1);}\n";
    const char*pf="#version 300 es\nprecision highp float;precision highp int;uniform highp sampler2D uImage;uniform ivec4 uViewport;layout(location=0)out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy)-uViewport.xy;ivec2 t=((2*p+ivec2(1))*ivec2(512))/(2*uViewport.zw);t=clamp(t,ivec2(0),ivec2(511));color=vec4(texelFetch(uImage,t,0).rgb,1.0);}\n";
    const char*dv="#version 300 es\nlayout(location=0)in vec4 aClip;void main(){gl_Position=aClip;}\n";
    const char*df="#version 300 es\nprecision highp float;uniform vec4 uColor;layout(location=0)out vec4 color;void main(){color=uColor;}\n";
#define EGL_REQUIRE(call,stage) if(!(call)){egfail(c,stage);goto cleanup;}
#define GL_REQUIRE(call) if(!(call))goto cleanup
    GL_REQUIRE(math_check(c,r));d=eglGetDisplay(EGL_DEFAULT_DISPLAY);if(d==EGL_NO_DISPLAY){egfail(c,"egl-display");goto cleanup;}EGL_REQUIRE(eglInitialize(d,&maj,&min),"egl-initialize");initialized=1;textcopy(c->egl_vendor,eglQueryString(d,EGL_VENDOR));textcopy(c->egl_version,eglQueryString(d,EGL_VERSION));EGL_REQUIRE(eglBindAPI(EGL_OPENGL_ES_API),"egl-bind-api");EGL_REQUIRE(eglChooseConfig(d,attrs,&config,1,&n),"egl-config");if(!n){fail(c,"egl-config","No RGBA8 GLES3 window configuration");goto cleanup;}EGL_REQUIRE(eglGetConfigAttrib(d,config,EGL_NATIVE_VISUAL_ID,&visual),"egl-native-format");if(ANativeWindow_setBuffersGeometry(window,0,0,visual)){fail(c,"window-format","Native window buffer format failed");goto cleanup;}
    surface=eglCreateWindowSurface(d,config,window,NULL);if(surface==EGL_NO_SURFACE){egfail(c,"egl-window-surface");goto cleanup;}context=eglCreateContext(d,config,EGL_NO_CONTEXT,ctxattrs);if(context==EGL_NO_CONTEXT){egfail(c,"egl-context");goto cleanup;}c->context_created=1;EGL_REQUIRE(eglMakeCurrent(d,surface,surface,context),"egl-current");current=1;
    textcopy(c->gl_vendor,(const char*)glGetString(GL_VENDOR));textcopy(c->gl_renderer,(const char*)glGetString(GL_RENDERER));textcopy(c->gl_version,(const char*)glGetString(GL_VERSION));textcopy(c->glsl_version,(const char*)glGetString(GL_SHADING_LANGUAGE_VERSION));GLint maxtex=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxtex);GL_REQUIRE(glcheck(c,"gl-capabilities"));if(maxtex<WORLD_SIZE){fail(c,"texture-limit","512-square world FBO exceeds GL capability");goto cleanup;}
    for(unsigned i=0;i<r->scene.texture_count;i++)if(r->scene.textures[i].width>(unsigned)maxtex||r->scene.textures[i].height>(unsigned)maxtex){fail(c,"texture-limit","Actual fixture texture exceeds GL capability");goto cleanup;}
    glDisable(GL_DITHER);glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);glDisable(GL_CULL_FACE);glDisable(GL_STENCIL_TEST);glDisable(GL_SAMPLE_COVERAGE);glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    GL_REQUIRE(program_create(c,&world,kWorldVertex,kWorldFragment,1));GL_REQUIRE(program_create(c,&reference,kWorldReferenceVertex,kWorldFragment,0));GL_REQUIRE(program_create(c,&material,kQuadVertex,kWorldFragment,0));GL_REQUIRE(program_create(c,&present,pv,pf,0));GL_REQUIRE(program_create(c,&diagnostic,dv,df,0));
    if(world.model<0||world.modelview<0||world.projection<0||world.base<0||world.dual<0||world.mode<0||reference.base<0||reference.dual<0||reference.mode<0||material.reference_color<0||material.reference_fog<0||material.mode<0){fail(c,"uniform-contract","Required reviewed world shader uniform missing");goto cleanup;}
    for(unsigned i=0;i<r->scene.texture_count;i++){const CohWorldTexture*t=&r->scene.textures[i];GL_REQUIRE(texture_create(c,&textures[i],t->width,t->height,t->rgba));}const uint8_t controlled_rgba[4]={51,153,230,128};GL_REQUIRE(texture_create(c,&controlled,1,1,controlled_rgba));GL_REQUIRE(target_create(c,&world_target,WORLD_SIZE,1));GL_REQUIRE(target_create(c,&material_target,64,0));GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_LINEAR));
    glGenVertexArrays(1,&vao);glGenBuffers(1,&vbo);glGenBuffers(1,&ibo);glGenBuffers(1,&tf);glGenVertexArrays(1,&qvao);glGenBuffers(1,&qvbo);GL_REQUIRE(glcheck(c,"geometry-create"));
    for(unsigned camera=0;camera<6;camera++){float view[12],proj[16],eye[6][12];if(coh_world_camera(&r->scene.inputs,camera,0,view,proj)||coh_world_group_eye_matrices(&r->scene.inputs,view,eye)){fail(c,"source-camera","Native source camera failed");goto cleanup;}
        for(unsigned part=0;part<r->scene.part_count;part++)GL_REQUIRE(transform_check(c,&world,vao,vbo,ibo,tf,r,&g[part],textures,part,camera,eye[r->scene.parts[part].node],proj));GL_REQUIRE(world_render(c,&world_target,&world,&reference,vao,vbo,ibo,r,g,textures,camera,eye,proj,actual,expected,edges));}
    for(unsigned i=0;i<r->scene.part_count;i++)if(c->part_interior_pixels[i]<64||c->part_transform_vertices[i]!=(uint64_t)r->scene.parts[i].mesh.vertex_count*6||!c->part_image_compared_pixels[i]||c->part_image_mismatches[i]){fail(c,"part-coverage","An original material partition lacks useful image or all-vertex transform coverage");goto cleanup;}
    c->world_transform_match=1;c->world_render_match=1;c->scene_assembly_match=1;GL_REQUIRE(diagnostic_check(c,&world_target,diagnostic.id,qvao,qvbo));GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_NEAREST));GL_REQUIRE(material_check(c,&material_target,&material,qvao,qvbo,textures,controlled,r,expected));c->material_pixel_match=1;GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_LINEAR));GL_REQUIRE(camera_preview(c,d,surface,&world_target,&world,present.id,vao,vbo,ibo,qvao,qvbo,r,g,textures,actual,expected));success=1;c->completed=1;textcopy(c->stage,"complete");
cleanup:
    if(current){glDisable(GL_RASTERIZER_DISCARD);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);target_delete(&world_target);target_delete(&material_target);for(unsigned i=0;i<r->scene.texture_count;i++)if(textures[i])glDeleteTextures(1,&textures[i]);if(controlled)glDeleteTextures(1,&controlled);if(vao)glDeleteVertexArrays(1,&vao);if(qvao)glDeleteVertexArrays(1,&qvao);if(vbo)glDeleteBuffers(1,&vbo);if(ibo)glDeleteBuffers(1,&ibo);if(tf)glDeleteBuffers(1,&tf);if(qvbo)glDeleteBuffers(1,&qvbo);if(world.id)glDeleteProgram(world.id);if(reference.id)glDeleteProgram(reference.id);if(material.id)glDeleteProgram(material.id);if(present.id)glDeleteProgram(present.id);if(diagnostic.id)glDeleteProgram(diagnostic.id);if(!glcheck(c,"gpu-cleanup"))success=0;}
    int released=1;if(current&&!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)){egfail(c,"egl-release-current");released=0;}if(surface!=EGL_NO_SURFACE&&!eglDestroySurface(d,surface)){egfail(c,"egl-destroy-surface");released=0;}if(context!=EGL_NO_CONTEXT&&!eglDestroyContext(d,context)){egfail(c,"egl-destroy-context");released=0;}if(initialized&&!eglTerminate(d)){egfail(c,"egl-terminate");released=0;}if(!eglReleaseThread()){egfail(c,"egl-release-thread");released=0;}c->released=released;c->passed=success&&released;return c->passed;
#undef EGL_REQUIRE
#undef GL_REQUIRE
}
static int allcycles(const Report*r,unsigned flag){if(r->attempted!=2)return 0;for(unsigned i=0;i<2;i++){const Cycle*c=&r->cycles[i];switch(flag){case 0:if(!c->passed)return 0;break;case 1:if(!c->group_transform_match)return 0;break;case 2:if(!c->camera_match)return 0;break;case 3:if(!c->world_transform_match)return 0;break;case 4:if(!c->world_render_match)return 0;break;case 5:if(!c->scene_assembly_match)return 0;break;case 6:if(!c->camera_preview_passed)return 0;break;case 7:if(!c->material_pixel_match)return 0;break;case 8:if(!c->window_pixel_match)return 0;break;case 9:if(c->diagnostic_cases!=5||c->diagnostic_pixels!=125||c->diagnostic_mismatches)return 0;break;default:return 0;}}return 1;}
static void counts_json(Json*j,const char*name,const uint64_t*v,unsigned n){append(j,",");string(j,name);append(j,":[");for(unsigned i=0;i<n;i++){if(i)append(j,",");append(j,"%"PRIu64,v[i]);}append(j,"]");}
static void bytes_json(Json*j,const uint8_t*v,unsigned n){append(j,"[");for(unsigned i=0;i<n;i++){if(i)append(j,",");append(j,"%u",(unsigned)v[i]);}append(j,"]");}
static jstring report_json(JNIEnv*env,const Report*r){
    char*buffer=malloc(JSON_CAP);if(!buffer)return (*env)->NewStringUTF(env,"{\"passed\":false,\"failure\":\"Report allocation failed\"}");Json j={buffer,0,1};
    append(&j,"{\"schema\":1,\"probe\":\"coh-native-source-world-camera-gles3\",\"platform\":\"Android Bionic\",\"passed\":%s,\"mesh_valid\":%s,\"world_valid\":%s,\"group_transform_match\":%s,\"camera_match\":%s,\"world_transform_match\":%s,\"world_render_match\":%s,\"scene_assembly_match\":%s,\"camera_preview_passed\":%s,\"material_pixel_match\":%s,\"alpha_fog_passed\":%s,\"offscreen_passed\":%s,\"context_recreation_passed\":%s,\"window_pixel_match\":%s,\"controlled_depth_cull_clip_passed\":%s,\"pointer_bytes\":%zu,\"long_bytes\":%zu,\"required_cycles\":2,\"attempted_cycles\":%d,\"surface_width\":%d,\"surface_height\":%d,",
        boolstr(r->passed),boolstr(r->world_valid),boolstr(r->world_valid),boolstr(allcycles(r,1)),boolstr(allcycles(r,2)),boolstr(allcycles(r,3)),boolstr(allcycles(r,4)),boolstr(allcycles(r,5)),boolstr(allcycles(r,6)),boolstr(allcycles(r,7)),boolstr(allcycles(r,7)),boolstr(allcycles(r,4)&&allcycles(r,7)&&allcycles(r,9)),boolstr(allcycles(r,0)),boolstr(allcycles(r,8)),boolstr(allcycles(r,9)),sizeof(void*),sizeof(long),r->attempted,r->attempted?r->cycles[r->attempted-1].width:0,r->attempted?r->cycles[r->attempted-1].height:0);
    append(&j,"\"world_part_count\":%u,\"group_node_count\":6,\"camera_count\":6,\"mesh_vertices\":%u,\"mesh_indices\":%u,\"source_mesh_vertices\":256,\"unique_textures\":%u,\"world_fbo_width\":512,\"world_fbo_height\":512,\"material_case_count\":%u,\"transform_absolute_tolerance\":0.0001,\"rgba_byte_tolerance\":2,\"triangle_edge_exclusion_pixels\":2,\"window_alpha_compared\":false,\"original_cg_execution\":false,\"reference_matrices_drive_rendering\":false,\"reference_geometry_drive_rendering\":false,\"reference_geometry_scope\":\"comparison images only; native source hierarchy/camera drives preview and qualified actual image\",\"front_face\":\"CW\",\"cull_face\":\"BACK except source DoubleSided\",\"depth_write\":true,\"world_texture_filter\":\"GL_LINEAR\",\"material_probe_texture_filter\":\"GL_NEAREST\",\"window_image_filter\":\"GL_NEAREST\",\"mip_policy\":\"base level only; original mip chain unqualified\",\"normal_policy\":\"source rigid precomposed eye hierarchy transform, unnormalized; controlled diffuse zero\",\"lighting_profile\":\"controlled original no-specular FF lighting branch with ambient .25 and diffuse zero; original Atlas light-grid and baked RGB unqualified\",\"material_profile\":\"actual Signmetal MULTIPLY with grey and modern_bench COLORBLEND_DUAL with white\",\"high_quality_materials_qualified\":false,\"draw_order\":\"source original material partition order\",\"projection\":\"original view X mirror and perspective kernels rebuilt from six raw controlled camera inputs\",\"controlled_diagnostic_scope\":\"five labelled clip-space witnesses: both opaque depth orders, CW/BACK culling, near-plane crossing, far-plane rejection; diagnostic vertices are not game geometry\",\"preview_scope\":\"45 paced native camera input interpolations between controlled cameras 0 and 1; elapsed time is not a performance measurement\",\"failure\":",
        r->scene.part_count,r->scene.vertices,r->scene.indices,r->scene.texture_count,r->materials.count);string(&j,r->failure);append(&j,",\"cycles\":[");
    for(int i=0;i<r->attempted;i++){const Cycle*c=&r->cycles[i];if(i)append(&j,",");append(&j,"{\"index\":%d,\"completed\":%s,\"passed\":%s,\"context_created\":%s,\"objects_released\":%s,\"swap_passed\":%s,\"group_transform_match\":%s,\"camera_match\":%s,\"world_transform_match\":%s,\"world_render_match\":%s,\"scene_assembly_match\":%s,\"camera_preview_passed\":%s,\"material_pixel_match\":%s,\"window_pixel_match\":%s,\"surface_width\":%d,\"surface_height\":%d,\"viewport\":[%d,%d,%d,%d]",
        i,boolstr(c->completed),boolstr(c->passed),boolstr(c->context_created),boolstr(c->released),boolstr(c->swap_passed),boolstr(c->group_transform_match),boolstr(c->camera_match),boolstr(c->world_transform_match),boolstr(c->world_render_match),boolstr(c->scene_assembly_match),boolstr(c->camera_preview_passed),boolstr(c->material_pixel_match),boolstr(c->window_pixel_match),c->width,c->height,c->viewport_x,c->viewport_y,c->viewport_w,c->viewport_h);
#define COUNT(name) append(&j,",\""#name"\":%"PRIu64,c->name)
#define NUMBER(name) append(&j,",\""#name"\":%u",c->name)
#define FLOAT(name) append(&j,",\""#name"\":%.9g",c->name)
    COUNT(group_local_components);COUNT(group_local_mismatches);FLOAT(group_local_max_error);COUNT(group_world_components);COUNT(group_world_mismatches);FLOAT(group_world_max_error);COUNT(camera_view_components);COUNT(camera_view_mismatches);FLOAT(camera_view_max_error);COUNT(projection_components);COUNT(projection_mismatches);FLOAT(projection_max_error);COUNT(modelview_components);COUNT(modelview_mismatches);FLOAT(modelview_max_error);COUNT(transform_vertices);COUNT(transform_components);COUNT(transform_mismatches);FLOAT(max_transform_error);COUNT(world_position_mismatches);COUNT(eye_position_mismatches);COUNT(normal_mismatches);COUNT(clip_mismatches);
    NUMBER(world_poses);COUNT(world_compared_pixels);COUNT(world_interior_pixels);COUNT(world_edge_excluded_pixels);COUNT(world_mismatches);NUMBER(world_max_byte_error);NUMBER(material_cases);NUMBER(real_material_cases);NUMBER(synthetic_semantic_cases);COUNT(material_pixels);COUNT(material_mismatches);NUMBER(material_max_byte_error);COUNT(material_discard_clear_pixels);append(&j,",\"material_blended_cases\":%u",c->blend_cases);NUMBER(window_samples);NUMBER(window_mismatches);NUMBER(preview_frames);NUMBER(distinct_camera_views);NUMBER(preview_image_samples);NUMBER(preview_changed_image_samples);COUNT(preview_pixels_changed_from_first);COUNT(preview_elapsed_ms);NUMBER(diagnostic_cases);NUMBER(diagnostic_pixels);NUMBER(diagnostic_mismatches);NUMBER(gl_errors);NUMBER(first_gl_error);NUMBER(egl_error);
#undef COUNT
#undef NUMBER
#undef FLOAT
    counts_json(&j,"world_pose_interior_pixels",c->world_pose_interiors,6);counts_json(&j,"world_pose_compared_pixels",c->world_pose_compared,6);counts_json(&j,"world_pose_edge_excluded_pixels",c->world_pose_excluded,6);counts_json(&j,"part_transform_vertices",c->part_transform_vertices,r->scene.part_count);counts_json(&j,"part_interior_pixels",c->part_interior_pixels,r->scene.part_count);counts_json(&j,"part_image_compared_pixels",c->part_image_compared_pixels,r->scene.part_count);counts_json(&j,"part_image_mismatches",c->part_image_mismatches,r->scene.part_count);
    append(&j,",\"first_transform_mismatch\":{\"observed\":%s,\"camera\":%u,\"part\":%u,\"vertex\":%u,\"component\":%u,\"expected\":%.9g,\"actual\":%.9g,\"actual_finite\":%s},\"first_image_mismatch\":{\"camera\":%u,\"part\":%u,\"pixel_xy\":[%u,%u],\"actual_rgba\":",boolstr(c->transform_mismatches!=0),c->first_transform_camera,c->first_transform_part,c->first_transform_vertex,c->first_transform_component,c->first_transform_expected,c->first_transform_actual,boolstr(c->first_transform_actual_finite),c->first_image_camera,c->first_image_part,c->first_image_x,c->first_image_y);bytes_json(&j,c->first_image_actual,4);append(&j,",\"expected_rgba\":");bytes_json(&j,c->first_image_expected,4);append(&j,"},\"stage\":");string(&j,c->stage);append(&j,",\"failure\":");string(&j,c->failure);append(&j,",\"gl_vendor\":");string(&j,c->gl_vendor);append(&j,",\"gl_renderer\":");string(&j,c->gl_renderer);append(&j,",\"gl_version\":");string(&j,c->gl_version);append(&j,",\"glsl_version\":");string(&j,c->glsl_version);append(&j,",\"egl_vendor\":");string(&j,c->egl_vendor);append(&j,",\"egl_version\":");string(&j,c->egl_version);append(&j,"}");
    }
    append(&j,"]}");jstring result=(*env)->NewStringUTF(env,j.ok?buffer:"{\"passed\":false,\"failure\":\"Report capacity exceeded\"}");free(buffer);return result;
}
JNIEXPORT jstring JNICALL Java_org_coh_worldprobe_ProbeNative_probe(JNIEnv*env,jclass clazz,jobject java_surface,jbyteArray java_world,jbyteArray java_reference,jbyteArray java_materials){
    (void)clazz;Report report={0};Bytes b[3]={{0}};ANativeWindow*window=NULL;Geometry geometry[COH_WORLD_PARTS]={{0}};uint8_t*actual=NULL,*expected=NULL,*edges=NULL;
    jbyteArray inputs[3]={java_world,java_reference,java_materials};size_t total=0;
    if(!java_surface){textcopy(report.failure,"A live Android Surface is required");goto cleanup;}
    for(unsigned i=0;i<3;i++){if(!inputs[i]){textcopy(report.failure,"All three immutable fixture byte arrays are required");goto cleanup;}jsize n=(*env)->GetArrayLength(env,inputs[i]);if(n<=0||(size_t)n>MAX_ASSET){textcopy(report.failure,"Input exceeds 16 MiB per asset");goto cleanup;}total+=(size_t)n;if(total>32u*1024u*1024u){textcopy(report.failure,"Fixture inputs exceed 32 MiB total");goto cleanup;}}
    for(unsigned i=0;i<3;i++)if(!copy_java(env,inputs[i],&b[i])){textcopy(report.failure,"JNI immutable fixture copy failed");goto cleanup;}
    if(coh_world_scene_parse(b[0].p,b[0].n,&report.scene)){textcopy(report.failure,"Original material-partition world fixture validation failed");goto cleanup;}report.world_valid=1;
    if(!world_reference_parse(b[1],&report.scene,&report.reference)||!material_parse(b[2],&report.scene,&report.materials)){textcopy(report.failure,"Independent source matrix/geometry/material reference validation failed");goto cleanup;}
    if(coh_world_group_matrices(&report.scene.inputs,report.local,report.world)){textcopy(report.failure,"Native original six-link group hierarchy failed");goto cleanup;}
    unsigned first=0;for(unsigned p=0;p<report.scene.part_count;p++){const CohMeshView*m=&report.scene.parts[p].mesh;Geometry*g=&geometry[p];g->first_vertex=first;first+=m->vertex_count;g->vertices=calloc(m->vertex_count,sizeof(Vertex));g->reference=calloc(m->vertex_count,sizeof(Vertex));g->indices=malloc((size_t)m->index_count*4);if(!g->vertices||!g->reference||!g->indices){textcopy(report.failure,"Bounded real mesh/reference allocation failed");goto cleanup;}
        for(unsigned i=0;i<m->vertex_count;i++){CohMeshVertex v;if(coh_mesh_vertex(m,i,&v)){textcopy(report.failure,"Original rigid vertex lookup failed");goto cleanup;}memcpy(g->vertices[i].position,v.position,12);memcpy(g->vertices[i].normal,v.normal,12);memcpy(g->vertices[i].uv0,v.uv,8);memcpy(g->vertices[i].uv1,v.uv,8);}
        for(unsigned i=0;i<m->index_count;i++)if(coh_mesh_index(m,i,&g->indices[i])){textcopy(report.failure,"Original material-partition triangle index lookup failed");goto cleanup;}
    }
    actual=malloc(WORLD_SIZE*WORLD_SIZE*4);expected=malloc(WORLD_SIZE*WORLD_SIZE*4);edges=malloc(WORLD_SIZE*WORLD_SIZE);if(!actual||!expected||!edges){textcopy(report.failure,"Bounded image/triangle-edge allocation failed");goto cleanup;}
    window=ANativeWindow_fromSurface(env,java_surface);if((*env)->ExceptionCheck(env))(*env)->ExceptionClear(env);if(!window){textcopy(report.failure,"Android Surface is unavailable");goto cleanup;}
    report.passed=1;for(unsigned i=0;i<2;i++){report.attempted++;if(!cycle_run(window,&report,geometry,actual,expected,edges,&report.cycles[i])){report.passed=0;textcopy(report.failure,report.cycles[i].failure);break;}}
cleanup:
    if(window)ANativeWindow_release(window);for(unsigned i=0;i<COH_WORLD_PARTS;i++){free(geometry[i].vertices);free(geometry[i].reference);free(geometry[i].indices);}free(actual);free(expected);free(edges);jstring result=report_json(env,&report);for(unsigned i=0;i<3;i++)free(b[i].p);return result;
}
