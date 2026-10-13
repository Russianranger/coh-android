/* Scoped native material/controlled-pose qualification; no game integration.
 * Bytes and every EGL/GL object are owned by one bounded, serialized JNI call. */
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
#include "coh_mesh.h"
#include "shader_sources.h"

#define CYCLES 2
#define SKIN_SIZE 384
#define BYTE_TOLERANCE 2
#define FLOAT_TOLERANCE 0.0001f
#define MAX_ASSET (16u * 1024u * 1024u)
#define TEXT_CAP 512
#define JSON_CAP 16384
#define TF_FLOATS 9u

typedef struct { uint8_t *p; size_t n; } Bytes;
typedef struct { float position[3],normal[3],uv0[2],uv1[2],weights[2]; int32_t rows[2]; } Vertex;
typedef struct {
    uint32_t count,bones,vertices,stride;
    const uint8_t *data;
} Poses;
typedef struct {
    uint32_t width,height,count,base_w,base_h,dual_w,dual_h;
    size_t stride;
    const uint8_t *data;
} Materials;
typedef struct {
    GLuint id; GLint projection,bones,light,diffuse,ambient,base,dual,const0,const1;
    GLint fog_params,fog_color,alpha_ref,reference_color,reference_fog;
} Program;
typedef struct { GLuint fbo,color,depth; int width,height; } Target;
typedef struct {
    int completed,passed,released,swap_passed,context_created;
    int skin_transform_match,skin_render_match,material_pixel_match,window_pixel_match;
    int width,height,viewport_x,viewport_y,viewport_w,viewport_h;
    unsigned gl_errors,first_gl_error,egl_error;
    uint64_t transform_vertices,transform_components,transform_mismatches;
    float max_transform_error;
    uint64_t position_mismatches,normal_mismatches;
    float max_position_error,max_normal_error,max_normal_length_error;
    uint32_t first_transform_pose,first_transform_vertex,first_transform_component;
    float first_transform_expected,first_transform_actual;
    int first_transform_actual_finite;
    uint64_t stock_normal_components,stock_normal_mismatches;
    float stock_normal_max_error,stock_normal_max_length_error;
    uint32_t stock_first_pose,stock_first_vertex,stock_first_component;
    float stock_first_expected,stock_first_actual;
    int stock_first_actual_finite;
    uint64_t skin_compared_pixels,skin_interior_pixels,skin_edge_excluded_pixels,skin_mismatches;
    uint64_t skin_pose_interiors[2],skin_pose_excluded[2],skin_pose_compared[2];
    unsigned skin_max_byte_error,skin_poses;
    uint64_t material_pixels,material_mismatches,material_discard_clear_pixels;
    unsigned material_max_byte_error,material_cases,blend_cases,real_material_cases,synthetic_semantic_cases;
    unsigned window_samples,window_mismatches;
    char stage[TEXT_CAP],failure[TEXT_CAP],gl_vendor[TEXT_CAP],gl_renderer[TEXT_CAP];
    char gl_version[TEXT_CAP],glsl_version[TEXT_CAP],egl_vendor[TEXT_CAP],egl_version[TEXT_CAP];
} Cycle;
typedef struct {
    int passed,mesh_valid,attempted;
    CohMeshView mesh; Poses poses; Materials materials;
    char failure[TEXT_CAP]; Cycle cycles[CYCLES];
} Report;
typedef struct { char *s; size_t n; int ok; } Json;

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
static int allcycles(const Report *r,int kind){if(r->attempted!=CYCLES)return 0;for(int i=0;i<CYCLES;i++){const Cycle*c=&r->cycles[i];if(kind==0&&!c->passed)return 0;if(kind==1&&!c->skin_transform_match)return 0;if(kind==2&&!c->skin_render_match)return 0;if(kind==3&&!c->material_pixel_match)return 0;if(kind==4&&!c->window_pixel_match)return 0;}return 1;}

static jstring report_json(JNIEnv *env,const Report *r){
    char *s=malloc(JSON_CAP);if(!s)return (*env)->NewStringUTF(env,"{\"passed\":false,\"failure\":\"report allocation failed\"}");
    Json j={s,0,1};
    append(&j,"{\"schema\":1,\"probe\":\"coh-material-skin-gles3\",\"platform\":\"Android Bionic\",\"passed\":%s,\"mesh_valid\":%s,\"skin_transform_match\":%s,\"skin_render_match\":%s,\"material_pixel_match\":%s,\"alpha_fog_passed\":%s,\"offscreen_passed\":%s,\"context_recreation_passed\":%s,\"window_pixel_match\":%s,\"pointer_bytes\":%zu,\"long_bytes\":%zu,\"required_cycles\":2,\"attempted_cycles\":%d,\"surface_width\":%d,\"surface_height\":%d,\"mesh_vertices\":%u,\"mesh_indices\":%u,\"mesh_bones\":%u,\"pose_count\":%u,\"material_case_count\":%u,\"skin_fbo_width\":384,\"skin_fbo_height\":384,\"transform_absolute_tolerance\":0.0001,\"rgba_byte_tolerance\":2,\"triangle_edge_exclusion_pixels\":2,\"window_alpha_compared\":false,\"original_cg_execution\":false,\"failure\":",
        boolstr(r->passed),boolstr(r->mesh_valid),boolstr(allcycles(r,1)),boolstr(allcycles(r,2)),boolstr(allcycles(r,3)),boolstr(allcycles(r,3)),boolstr(allcycles(r,2)&&allcycles(r,3)),boolstr(allcycles(r,0)),boolstr(allcycles(r,4)),sizeof(void*),sizeof(long),r->attempted,r->attempted?r->cycles[r->attempted-1].width:0,r->attempted?r->cycles[r->attempted-1].height:0,r->mesh.vertex_count,r->mesh.index_count,r->mesh.bone_count,r->poses.count,r->materials.count);
    string(&j,r->failure);append(&j,",\"normal_policy\":\"post-blend inverse square root with one Newton refinement\",\"stock_normal_diagnostic_only\":true,\"transform_feedback_floats_per_vertex\":9,\"real_material_case_count\":14,\"synthetic_semantic_case_count\":4,\"controlled_dual_rgba\":[51,153,230,128],\"cycles\":[");
    for(int i=0;i<r->attempted;i++){
        const Cycle*c=&r->cycles[i];if(i)append(&j,",");
        append(&j,"{\"index\":%d,\"completed\":%s,\"passed\":%s,\"context_created\":%s,\"objects_released\":%s,\"swap_passed\":%s,\"skin_transform_match\":%s,\"skin_render_match\":%s,\"material_pixel_match\":%s,\"window_pixel_match\":%s,\"surface_width\":%d,\"surface_height\":%d,\"viewport\":[%d,%d,%d,%d],\"transform_vertices\":%"PRIu64",\"transform_components\":%"PRIu64",\"transform_mismatches\":%"PRIu64",\"max_transform_error\":%.9g,\"skin_poses\":%u,\"skin_compared_pixels\":%"PRIu64",\"skin_interior_pixels\":%"PRIu64",\"skin_edge_excluded_pixels\":%"PRIu64",\"skin_mismatches\":%"PRIu64",\"skin_max_byte_error\":%u,\"material_cases\":%u,\"material_pixels\":%"PRIu64",\"material_mismatches\":%"PRIu64",\"material_max_byte_error\":%u,\"material_blended_cases\":%u,\"material_discard_clear_pixels\":%"PRIu64",\"window_samples\":%u,\"window_mismatches\":%u,\"gl_errors\":%u,\"first_gl_error\":%u,\"egl_error\":%u,\"stage\":",
            i,boolstr(c->completed),boolstr(c->passed),boolstr(c->context_created),boolstr(c->released),boolstr(c->swap_passed),boolstr(c->skin_transform_match),boolstr(c->skin_render_match),boolstr(c->material_pixel_match),boolstr(c->window_pixel_match),c->width,c->height,c->viewport_x,c->viewport_y,c->viewport_w,c->viewport_h,c->transform_vertices,c->transform_components,c->transform_mismatches,c->max_transform_error,c->skin_poses,c->skin_compared_pixels,c->skin_interior_pixels,c->skin_edge_excluded_pixels,c->skin_mismatches,c->skin_max_byte_error,c->material_cases,c->material_pixels,c->material_mismatches,c->material_max_byte_error,c->blend_cases,c->material_discard_clear_pixels,c->window_samples,c->window_mismatches,c->gl_errors,c->first_gl_error,c->egl_error);
        string(&j,c->stage);append(&j,",\"skin_pose_interior_pixels\":[%"PRIu64",%"PRIu64"],\"skin_pose_edge_excluded_pixels\":[%"PRIu64",%"PRIu64"],\"skin_pose_compared_pixels\":[%"PRIu64",%"PRIu64"],\"real_material_cases\":%u,\"synthetic_semantic_cases\":%u,\"position_mismatches\":%"PRIu64",\"normal_mismatches\":%"PRIu64",\"max_position_error\":%.9g,\"max_normal_error\":%.9g,\"max_normal_length_error\":%.9g,\"first_transform_mismatch\":{\"observed\":%s,\"pose\":%u,\"vertex\":%u,\"component\":%u,\"expected\":%.9g,\"actual\":%.9g,\"actual_finite\":%s},",c->skin_pose_interiors[0],c->skin_pose_interiors[1],c->skin_pose_excluded[0],c->skin_pose_excluded[1],c->skin_pose_compared[0],c->skin_pose_compared[1],c->real_material_cases,c->synthetic_semantic_cases,c->position_mismatches,c->normal_mismatches,c->max_position_error,c->max_normal_error,c->max_normal_length_error,boolstr(c->transform_mismatches!=0),c->first_transform_pose,c->first_transform_vertex,c->first_transform_component,c->first_transform_expected,c->first_transform_actual,boolstr(c->first_transform_actual_finite));
        append(&j,"\"stock_normal_components\":%"PRIu64",\"stock_normal_mismatches\":%"PRIu64",\"stock_normal_max_error\":%.9g,\"stock_normal_max_length_error\":%.9g,\"stock_first_mismatch\":{\"observed\":%s,\"pose\":%u,\"vertex\":%u,\"component\":%u,\"expected\":%.9g,\"actual\":%.9g,\"actual_finite\":%s},\"failure\":",c->stock_normal_components,c->stock_normal_mismatches,c->stock_normal_max_error,c->stock_normal_max_length_error,boolstr(c->stock_normal_mismatches!=0),c->stock_first_pose,c->stock_first_vertex,c->stock_first_component,c->stock_first_expected,c->stock_first_actual,boolstr(c->stock_first_actual_finite));string(&j,c->failure);
        append(&j,",\"gl_vendor\":");string(&j,c->gl_vendor);append(&j,",\"gl_renderer\":");string(&j,c->gl_renderer);append(&j,",\"gl_version\":");string(&j,c->gl_version);append(&j,",\"glsl_version\":");string(&j,c->glsl_version);append(&j,",\"egl_vendor\":");string(&j,c->egl_vendor);append(&j,",\"egl_version\":");string(&j,c->egl_version);append(&j,"}");
    }
    append(&j,"]}");jstring out=(*env)->NewStringUTF(env,j.ok?s:"{\"passed\":false,\"failure\":\"report capacity exceeded\"}");free(s);return out;
}

static int copy_java(JNIEnv*env,jbyteArray a,Bytes*out){if(!a)return 0;jsize n=(*env)->GetArrayLength(env,a);if(n<=0||(size_t)n>MAX_ASSET)return 0;out->p=malloc((size_t)n);if(!out->p)return 0;out->n=(size_t)n;(*env)->GetByteArrayRegion(env,a,0,n,(jbyte*)out->p);if((*env)->ExceptionCheck(env)){(*env)->ExceptionClear(env);return 0;}return 1;}
static int pose_parse(Bytes b,const CohMeshView*m,Poses*out){
    if(b.n<64||memcmp(b.p,"COHPOSE1",8)||u32(b.p+8)!=1||u32(b.p+12)!=64||u32(b.p+16)!=2||u32(b.p+20)!=m->vertex_count||u32(b.p+24)!=m->bone_count||u32(b.p+28)!=48||u32(b.p+36)!=64||u32(b.p+40)!=b.n)return 0;
    for(unsigned o=44;o<64;o+=4)if(u32(b.p+o))return 0;
    size_t stride=(size_t)m->bone_count*48+(size_t)m->vertex_count*24;
    if(u32(b.p+32)!=stride||b.n!=64+2*stride)return 0;
    for(size_t o=64;o<b.n;o+=4){float f=f32(b.p+o);if(!isfinite(f)||fabsf(f)>1000000)return 0;}
    *out=(Poses){2,m->bone_count,m->vertex_count,(uint32_t)stride,b.p+64};return 1;
}
static int material_parse(Bytes b,Bytes base,Bytes dual,Materials*out){
    if(b.n<48||memcmp(b.p,"COHMAT6\0",8)||u32(b.p+8)!=1||u32(b.p+12)!=64||u32(b.p+16)!=64||u32(b.p+20)!=18||u32(b.p+24)!=112||u32(b.p+44))return 0;
    uint32_t bw=u32(b.p+28),bh=u32(b.p+32),dw=u32(b.p+36),dh=u32(b.p+40);
    if(!bw||!bh||!dw||!dh||bw>4096||bh>4096||dw>4096||dh>4096||base.n!=(size_t)bw*bh*4||dual.n!=(size_t)dw*dh*4)return 0;
    size_t stride=112+64*64*4;if(b.n!=48+18*stride)return 0;
    unsigned controlled=0;
    for(unsigned i=0;i<18;i++){const uint8_t*p=b.p+48+i*stride;for(unsigned o=0;o<104;o+=4){float f=f32(p+o);if(!isfinite(f)||fabsf(f)>1000000)return 0;}uint32_t flags=u32(p+104);if(f32(p+100)<0||f32(p+100)>1||(flags&~3u)||u32(p+108))return 0;if(flags&2u)controlled++;}
    if(controlled!=4)return 0;
    *out=(Materials){64,64,18,bw,bh,dw,dh,stride,b.p+48};return 1;
}
static void floats(const uint8_t*p,float*f,unsigned n){for(unsigned i=0;i<n;i++)f[i]=f32(p+i*4);}
static const uint8_t*pose_data(const Poses*p,unsigned i){return p->data+(size_t)i*p->stride;}
static const uint8_t*golden_data(const Poses*p,unsigned i){return pose_data(p,i)+(size_t)p->bones*48;}

static GLuint shader(Cycle*c,GLenum type,const char*source){GLuint s=glCreateShader(type);if(!s){fail(c,"shader-create","Shader allocation failed");return 0;}glShaderSource(s,1,&source,NULL);glCompileShader(s);GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char log[TEXT_CAP]={0};glGetShaderInfoLog(s,TEXT_CAP,NULL,log);fail(c,"shader-compile",log[0]?log:"Shader compilation failed");glDeleteShader(s);return 0;}return s;}
static int program_create(Cycle*c,Program*p,const char*v,const char*f,int transform){
    GLuint vs=shader(c,GL_VERTEX_SHADER,v);if(!vs)return 0;GLuint fs=shader(c,GL_FRAGMENT_SHADER,f);if(!fs){glDeleteShader(vs);return 0;}
    p->id=glCreateProgram();if(!p->id){glDeleteShader(vs);glDeleteShader(fs);return fail(c,"program-create","Program allocation failed");}
    glAttachShader(p->id,vs);glAttachShader(p->id,fs);if(transform){const char*varyings[]={"vViewPosition","vNormal","vUnrefinedNormal"};glTransformFeedbackVaryings(p->id,3,varyings,GL_INTERLEAVED_ATTRIBS);}glLinkProgram(p->id);glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;glGetProgramiv(p->id,GL_LINK_STATUS,&ok);if(!ok){char log[TEXT_CAP]={0};glGetProgramInfoLog(p->id,TEXT_CAP,NULL,log);return fail(c,"program-link",log[0]?log:"Program linking failed");}
#define U(field,name) p->field=glGetUniformLocation(p->id,name)
    U(projection,"uProjection");U(bones,"uBoneRows[0]");U(light,"uLightDir");U(diffuse,"uDiffuse");U(ambient,"uAmbient");U(base,"uBase");U(dual,"uDual");U(const0,"uConst0");U(const1,"uConst1");U(fog_params,"uFogParams");U(fog_color,"uFogColor");U(alpha_ref,"uAlphaRef");U(reference_color,"uReferenceColor");U(reference_fog,"uReferenceFogCoord");
#undef U
    return glcheck(c,"program-build");
}
static int texture_create(Cycle*c,GLuint*out,unsigned w,unsigned h,const uint8_t*rgba){glGenTextures(1,out);glBindTexture(GL_TEXTURE_2D,*out);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,(GLsizei)w,(GLsizei)h);if(rgba)glTexSubImage2D(GL_TEXTURE_2D,0,0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,rgba);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return glcheck(c,"texture-create");}
static int target_create(Cycle*c,Target*t,int size,int depth){t->width=t->height=size;if(!texture_create(c,&t->color,(unsigned)size,(unsigned)size,NULL))return 0;glGenFramebuffers(1,&t->fbo);glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t->color,0);if(depth){glGenRenderbuffers(1,&t->depth);glBindRenderbuffer(GL_RENDERBUFFER,t->depth);glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT24,size,size);glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,t->depth);}if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail(c,"fbo-status","RGBA8 framebuffer incomplete");return glcheck(c,"fbo-create");}
static void target_delete(Target*t){if(t->fbo)glDeleteFramebuffers(1,&t->fbo);if(t->color)glDeleteTextures(1,&t->color);if(t->depth)glDeleteRenderbuffers(1,&t->depth);}
static void bind_textures(Program*p,GLuint base,GLuint dual){glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,base);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,dual);glUniform1i(p->base,0);glUniform1i(p->dual,1);}
static void material_uniforms(Program*p,const uint8_t*record){float v[24];floats(record,v,24);glUniform4fv(p->const0,1,v);glUniform4fv(p->const1,1,v+4);glUniform4fv(p->reference_color,1,v+8);glUniform4fv(p->fog_params,1,v+12);glUniform4fv(p->fog_color,1,v+16);glUniform1f(p->reference_fog,f32(record+96));glUniform1f(p->alpha_ref,f32(record+100));}
static void projection(const Poses*p,float*out){float lo[3]={INFINITY,INFINITY,INFINITY},hi[3]={-INFINITY,-INFINITY,-INFINITY};for(unsigned k=0;k<p->count;k++){const uint8_t*g=golden_data(p,k);for(unsigned v=0;v<p->vertices;v++)for(unsigned j=0;j<3;j++){float x=f32(g+v*24+j*4);if(x<lo[j])lo[j]=x;if(x>hi[j])hi[j]=x;}}float half=fmaxf(hi[0]-lo[0],hi[1]-lo[1])*.55f;if(half<.0001f)half=1;float zhalf=(hi[2]-lo[2])*.55f;if(zhalf<.0001f)zhalf=1;memset(out,0,16*sizeof(float));out[0]=out[5]=1/half;out[10]=-1/zhalf;out[12]=-(hi[0]+lo[0])*.5f/half;out[13]=-(hi[1]+lo[1])*.5f/half;out[14]=(hi[2]+lo[2])*.5f/zhalf;out[15]=1;}
static void vertex_layout(GLuint vao,GLuint vbo,GLuint indices){glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,indices);
#define A(loc,count,field) glVertexAttribPointer(loc,count,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)offsetof(Vertex,field));glEnableVertexAttribArray(loc)
    A(0,3,position);A(1,3,normal);A(2,2,uv0);A(3,2,uv1);A(4,2,weights);
#undef A
    glVertexAttribIPointer(5,2,GL_INT,sizeof(Vertex),(void*)offsetof(Vertex,rows));glEnableVertexAttribArray(5);
}
static unsigned pixel_error(const uint8_t*a,const uint8_t*b,unsigned channels){unsigned max=0;for(unsigned k=0;k<channels;k++){unsigned d=a[k]>b[k]?a[k]-b[k]:b[k]-a[k];if(d>max)max=d;}return max;}
static void edge_mark(uint8_t*mask,float ax,float ay,float bx,float by){
    int minx=(int)floorf(fminf(ax,bx)-2.0f),maxx=(int)ceilf(fmaxf(ax,bx)+2.0f),miny=(int)floorf(fminf(ay,by)-2.0f),maxy=(int)ceilf(fmaxf(ay,by)+2.0f);
    if(minx<0)minx=0;if(miny<0)miny=0;if(maxx>=SKIN_SIZE)maxx=SKIN_SIZE-1;if(maxy>=SKIN_SIZE)maxy=SKIN_SIZE-1;
    float dx=bx-ax,dy=by-ay,len=dx*dx+dy*dy;
    for(int y=miny;y<=maxy;y++)for(int x=minx;x<=maxx;x++){float px=x+.5f-ax,py=y+.5f-ay,t=len>0?(px*dx+py*dy)/len:0;if(t<0)t=0;if(t>1)t=1;float ex=px-t*dx,ey=py-t*dy;if(ex*ex+ey*ey<=4.0f)mask[y*SKIN_SIZE+x]=1;}
}
static void edge_mask(const Vertex*reference,const uint32_t*indices,uint32_t n,const float*proj,uint8_t*mask){memset(mask,0,SKIN_SIZE*SKIN_SIZE);for(uint32_t i=0;i<n;i+=3){float x[3],y[3];for(unsigned j=0;j<3;j++){const float*p=reference[indices[i+j]].position;x[j]=(proj[0]*p[0]+proj[12]+1)*(.5f*SKIN_SIZE);y[j]=(proj[5]*p[1]+proj[13]+1)*(.5f*SKIN_SIZE);}for(unsigned j=0;j<3;j++)edge_mark(mask,x[j],y[j],x[(j+1)%3],y[(j+1)%3]);}}

static int transform_check(Cycle*c,Program*p,GLuint vao,GLuint vbo,GLuint index,GLuint tf,
                          const Vertex*vertices,const Poses*poses,unsigned pose,const float*proj){
    float rows[COH_MESH_MAX_BONES*12];floats(pose_data(poses,pose),rows,poses->bones*12);
    glUseProgram(p->id);glUniformMatrix4fv(p->projection,1,GL_FALSE,proj);glUniform4fv(p->bones,(GLsizei)poses->bones*3,rows);glUniform3f(p->light,0,0,1);glUniform4f(p->diffuse,.2f,.2f,.2f,0);glUniform4f(p->ambient,.05f,.05f,.05f,1);
    vertex_layout(vao,vbo,index);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)poses->vertices*sizeof(Vertex)),vertices,GL_DYNAMIC_DRAW);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(GLsizeiptr)((size_t)poses->vertices*TF_FLOATS*sizeof(float)),NULL,GL_DYNAMIC_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,tf);
    glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,(GLsizei)poses->vertices);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);
    if(!glcheck(c,"skin-transform-feedback"))return 0;
    float*actual=glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,(GLsizeiptr)((size_t)poses->vertices*TF_FLOATS*sizeof(float)),GL_MAP_READ_BIT);if(!actual)return fail(c,"transform-map","Transform-feedback buffer could not be mapped");
    const uint8_t*g=golden_data(poses,pose);
    for(uint32_t v=0;v<poses->vertices;v++){
        c->transform_vertices++;
        float *normal=actual+(size_t)v*TF_FLOATS+3;
        float normal_error=fabsf(sqrtf(normal[0]*normal[0]+normal[1]*normal[1]+normal[2]*normal[2])-1);
        if(isfinite(normal_error)&&normal_error>c->max_normal_length_error)c->max_normal_length_error=normal_error;
        for(unsigned k=0;k<6;k++){
            float expected=f32(g+v*24+k*4),got=actual[(size_t)v*TF_FLOATS+k],delta=fabsf(expected-got);
            c->transform_components++;
            if(isfinite(delta)){
                if(delta>c->max_transform_error)c->max_transform_error=delta;
                if(k<3&&delta>c->max_position_error)c->max_position_error=delta;
                if(k>=3&&delta>c->max_normal_error)c->max_normal_error=delta;
            }
            if(!isfinite(got)||delta>FLOAT_TOLERANCE){
                if(!c->transform_mismatches){
                    c->first_transform_pose=pose;c->first_transform_vertex=v;c->first_transform_component=k;
                    c->first_transform_expected=expected;c->first_transform_actual=isfinite(got)?got:0;
                    c->first_transform_actual_finite=isfinite(got);
                }
                c->transform_mismatches++;
                if(k<3)c->position_mismatches++;else c->normal_mismatches++;
            }
        }
        float *stock=actual+(size_t)v*TF_FLOATS+6;
        float stock_length_error=fabsf(sqrtf(stock[0]*stock[0]+stock[1]*stock[1]+stock[2]*stock[2])-1);
        if(isfinite(stock_length_error)&&stock_length_error>c->stock_normal_max_length_error)c->stock_normal_max_length_error=stock_length_error;
        for(unsigned k=0;k<3;k++){
            float expected=f32(g+v*24+(k+3)*4),got=stock[k],delta=fabsf(expected-got);
            c->stock_normal_components++;
            if(isfinite(delta)&&delta>c->stock_normal_max_error)c->stock_normal_max_error=delta;
            if(!isfinite(got)||delta>FLOAT_TOLERANCE){
                if(!c->stock_normal_mismatches){c->stock_first_pose=pose;c->stock_first_vertex=v;c->stock_first_component=k;c->stock_first_expected=expected;c->stock_first_actual=isfinite(got)?got:0;c->stock_first_actual_finite=isfinite(got);}
                c->stock_normal_mismatches++;
            }
        }
    }
    if(!glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER))return fail(c,"transform-unmap","Transform-feedback data became invalid");
    glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);
    if(!glcheck(c,"transform-readback"))return 0;
    return c->transform_mismatches?fail(c,"transform-parity","GPU position/normalized-normal differs from independent pose golden"):1;
}

static void skin_uniforms(Program*p,const float*proj,GLuint base,GLuint dual){
    glUseProgram(p->id);glUniformMatrix4fv(p->projection,1,GL_FALSE,proj);glUniform3f(p->light,.188144f,.282216f,.940721f);glUniform4f(p->diffuse,.18f,.18f,.18f,0);glUniform4f(p->ambient,.055f,.055f,.055f,1);glUniform4f(p->const0,1,.85f,.6f,1);glUniform4f(p->const1,.2f,.35f,.65f,1);glUniform4f(p->fog_params,0,0,1000000,1);glUniform4f(p->fog_color,0,0,0,1);glUniform1f(p->alpha_ref,0);bind_textures(p,base,dual);
}
static int skin_draw(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,GLuint index,
                     const Vertex*vertices,uint32_t count,uint32_t index_count,const float*rows,uint32_t bones,uint8_t*out){
    glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,SKIN_SIZE,SKIN_SIZE);glDisable(GL_BLEND);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClearColor(17/255.f,19/255.f,23/255.f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
    glUseProgram(p->id);glUniform4fv(p->bones,(GLsizei)bones*3,rows);vertex_layout(vao,vbo,index);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)count*sizeof(Vertex)),vertices,GL_DYNAMIC_DRAW);glDrawElements(GL_TRIANGLES,(GLsizei)index_count,GL_UNSIGNED_INT,(void*)0);glReadPixels(0,0,SKIN_SIZE,SKIN_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,out);return glcheck(c,"skin-render-readback");
}
static int skin_render(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,GLuint index,
                       const Vertex*vertices,Vertex*reference,const uint32_t*indices,
                       const CohMeshView*mesh,const Poses*poses,unsigned pose,const float*proj,
                       uint8_t*actual,uint8_t*expected,uint8_t*edges){
    const uint8_t*g=golden_data(poses,pose);for(uint32_t v=0;v<mesh->vertex_count;v++){reference[v]=vertices[v];floats(g+v*24,reference[v].position,3);floats(g+v*24+12,reference[v].normal,3);reference[v].weights[0]=1;reference[v].weights[1]=0;reference[v].rows[0]=reference[v].rows[1]=0;}
    const float identity[12]={1,0,0,0,0,1,0,0,0,0,1,0};
    if(!skin_draw(c,t,p,vao,vbo,index,reference,mesh->vertex_count,mesh->index_count,identity,1,expected))return 0;
    float rows[COH_MESH_MAX_BONES*12];floats(pose_data(poses,pose),rows,poses->bones*12);
    if(!skin_draw(c,t,p,vao,vbo,index,vertices,mesh->vertex_count,mesh->index_count,rows,poses->bones,actual))return 0;
    edge_mask(reference,indices,mesh->index_count,proj,edges);uint64_t interior=0;const uint8_t clear[4]={17,19,23,255};
    for(size_t v=0;v<SKIN_SIZE*SKIN_SIZE;v++){if(edges[v]){c->skin_edge_excluded_pixels++;c->skin_pose_excluded[pose]++;continue;}c->skin_compared_pixels++;c->skin_pose_compared[pose]++;if(memcmp(expected+v*4,clear,4)){c->skin_interior_pixels++;interior++;}unsigned delta=pixel_error(actual+v*4,expected+v*4,4);if(delta>c->skin_max_byte_error)c->skin_max_byte_error=delta;if(delta>BYTE_TOLERANCE)c->skin_mismatches++;}
    c->skin_pose_interiors[pose]=interior;
    c->skin_poses++;if(interior<64)return fail(c,"skin-coverage","Fewer than 64 useful non-background, non-edge mesh pixels");
    return c->skin_mismatches?fail(c,"skin-image-parity","GPU skinned mesh differs from independent reference geometry outside excluded edges"):1;
}

static int material_check(Cycle*c,Target*t,Program*p,GLuint quad_vao,GLuint quad_vbo,
                          GLuint base,GLuint dual,GLuint controlled,const Materials*m,uint8_t*readback){
    static const float quad[]={-1,-1,0,0,1,-1,1,0,1,1,1,1,-1,-1,0,0,1,1,1,1,-1,1,0,1};
    glBindVertexArray(quad_vao);glBindBuffer(GL_ARRAY_BUFFER,quad_vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)0);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)(2*sizeof(float)));glEnableVertexAttribArray(0);glEnableVertexAttribArray(2);
    glUseProgram(p->id);bind_textures(p,base,dual);glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,64,64);glDisable(GL_DEPTH_TEST);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    for(uint32_t i=0;i<m->count;i++){const uint8_t*r=m->data+i*m->stride;uint32_t flags=u32(r+104);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,(flags&2u)?controlled:dual);if(flags&2u)c->synthetic_semantic_cases++;else c->real_material_cases++;float clear[4];floats(r+80,clear,4);glClearColor(clear[0],clear[1],clear[2],clear[3]);glClear(GL_COLOR_BUFFER_BIT);if(flags&1){glEnable(GL_BLEND);c->blend_cases++;}else glDisable(GL_BLEND);material_uniforms(p,r);glDrawArrays(GL_TRIANGLES,0,6);glReadPixels(0,0,64,64,GL_RGBA,GL_UNSIGNED_BYTE,readback);if(!glcheck(c,"material-draw-readback"))return 0;
        uint8_t clear_bytes[4];for(unsigned k=0;k<4;k++){float v=fminf(1,fmaxf(0,clear[k]));clear_bytes[k]=(uint8_t)floorf(v*255+.5f);}
        const uint8_t*golden=r+112;for(unsigned v=0;v<64*64;v++){unsigned delta=pixel_error(readback+v*4,golden+v*4,4);c->material_pixels++;if(delta>c->material_max_byte_error)c->material_max_byte_error=delta;if(delta>BYTE_TOLERANCE)c->material_mismatches++;if(!memcmp(golden+v*4,clear_bytes,4))c->material_discard_clear_pixels++;}c->material_cases++;
    }
    glDisable(GL_BLEND);return c->material_mismatches?fail(c,"material-pixel-parity","Source-semantic dual-tint/alpha/fog/blend golden differs from shader RGBA"):1;
}

static int display_window(Cycle*c,EGLDisplay d,EGLSurface surface,Target*t,GLuint program,
                          GLuint vao,GLuint vbo,const uint8_t*image){
    EGLint w=0,h=0;if(!eglQuerySurface(d,surface,EGL_WIDTH,&w)||!eglQuerySurface(d,surface,EGL_HEIGHT,&h))return egfail(c,"surface-query");
    if(w<=0||h<=0||w>16384||h>16384)return fail(c,"surface-size","Surface dimensions outside bounded positive range");c->width=w;c->height=h;
    int size=w<h?w:h;c->viewport_w=c->viewport_h=size;c->viewport_x=(w-size)/2;c->viewport_y=(h-size)/2;
    const float quad[]={-1,-1,1,-1,1,1,-1,-1,1,1,-1,1};glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,2*sizeof(float),(void*)0);glEnableVertexAttribArray(0);glDisableVertexAttribArray(2);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glViewport(0,0,w,h);glClearColor(.04f,.04f,.06f,1);glClear(GL_COLOR_BUFFER_BIT);glViewport(c->viewport_x,c->viewport_y,size,size);glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,t->color);glUniform1i(glGetUniformLocation(program,"uImage"),0);glUniform4i(glGetUniformLocation(program,"uViewport"),c->viewport_x,c->viewport_y,size,size);glDrawArrays(GL_TRIANGLES,0,6);if(!glcheck(c,"window-draw"))return 0;
    for(int gy=1;gy<=7;gy++)for(int gx=1;gx<=7;gx++){int lx=gx*size/8,ly=gy*size/8;if(lx>=size)lx=size-1;if(ly>=size)ly=size-1;unsigned tx=(unsigned)(((uint64_t)(2*lx+1)*SKIN_SIZE)/(2u*(unsigned)size)),ty=(unsigned)(((uint64_t)(2*ly+1)*SKIN_SIZE)/(2u*(unsigned)size));uint8_t got[4]={0};glReadPixels(c->viewport_x+lx,c->viewport_y+ly,1,1,GL_RGBA,GL_UNSIGNED_BYTE,got);if(!glcheck(c,"window-readback"))return 0;c->window_samples++;if(pixel_error(got,image+((size_t)ty*SKIN_SIZE+tx)*4,3))c->window_mismatches++;}
    if(c->window_mismatches)return fail(c,"window-parity","Opaque RGB window samples differ from final qualified mesh FBO");c->window_pixel_match=1;if(!eglSwapBuffers(d,surface))return egfail(c,"swap-buffers");c->swap_passed=1;return glcheck(c,"post-swap");
}

static int cycle_run(ANativeWindow*window,const CohMeshView*mesh,const Poses*poses,
                     const Materials*materials,Bytes base,Bytes dual,const Vertex*vertices,
                     Vertex*reference,const uint32_t*indices,const float*proj,uint8_t*actual,
                     uint8_t*expected,uint8_t*edges,Cycle*c){
    EGLDisplay d=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;int initialized=0,current=0,success=0;
    GLuint base_tex=0,dual_tex=0,controlled_tex=0,vao=0,vbo=0,ibo=0,tf=0,quad_vao=0,quad_vbo=0;Program skin={0},material={0},present={0};Target skin_target={0},material_target={0};
    EGLint maj=0,min=0,n=0,visual=0;EGLConfig config=NULL;const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT_KHR,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,0,EGL_STENCIL_SIZE,0,EGL_NONE};const EGLint ctxattrs[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
    const char*pv="#version 300 es\nlayout(location=0) in vec2 aPosition; void main(){gl_Position=vec4(aPosition,0,1);}\n";
    const char*pf="#version 300 es\nprecision highp float;precision highp int;uniform highp sampler2D uImage;uniform ivec4 uViewport;layout(location=0)out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy)-uViewport.xy;ivec2 t=((2*p+ivec2(1))*ivec2(384))/(2*uViewport.zw);t=clamp(t,ivec2(0),ivec2(383));color=vec4(texelFetch(uImage,t,0).rgb,1.0);}\n";
#define EGL_REQUIRE(call,stage) if(!(call)){egfail(c,stage);goto cleanup;}
#define GL_REQUIRE(call) if(!(call))goto cleanup
    d=eglGetDisplay(EGL_DEFAULT_DISPLAY);if(d==EGL_NO_DISPLAY){egfail(c,"egl-display");goto cleanup;}EGL_REQUIRE(eglInitialize(d,&maj,&min),"egl-initialize");initialized=1;textcopy(c->egl_vendor,eglQueryString(d,EGL_VENDOR));textcopy(c->egl_version,eglQueryString(d,EGL_VERSION));EGL_REQUIRE(eglBindAPI(EGL_OPENGL_ES_API),"egl-bind-api");EGL_REQUIRE(eglChooseConfig(d,attrs,&config,1,&n),"egl-config");if(!n){fail(c,"egl-config","No RGBA8 GLES3 window configuration");goto cleanup;}EGL_REQUIRE(eglGetConfigAttrib(d,config,EGL_NATIVE_VISUAL_ID,&visual),"egl-native-format");if(ANativeWindow_setBuffersGeometry(window,0,0,visual)){fail(c,"window-format","Native window buffer format failed");goto cleanup;}
    surface=eglCreateWindowSurface(d,config,window,NULL);if(surface==EGL_NO_SURFACE){egfail(c,"egl-window-surface");goto cleanup;}context=eglCreateContext(d,config,EGL_NO_CONTEXT,ctxattrs);if(context==EGL_NO_CONTEXT){egfail(c,"egl-context");goto cleanup;}c->context_created=1;EGL_REQUIRE(eglMakeCurrent(d,surface,surface,context),"egl-current");current=1;
    textcopy(c->gl_vendor,(const char*)glGetString(GL_VENDOR));textcopy(c->gl_renderer,(const char*)glGetString(GL_RENDERER));textcopy(c->gl_version,(const char*)glGetString(GL_VERSION));textcopy(c->glsl_version,(const char*)glGetString(GL_SHADING_LANGUAGE_VERSION));GLint maxtex=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxtex);GL_REQUIRE(glcheck(c,"gl-capabilities"));if(maxtex<SKIN_SIZE||materials->base_w>(unsigned)maxtex||materials->base_h>(unsigned)maxtex||materials->dual_w>(unsigned)maxtex||materials->dual_h>(unsigned)maxtex){fail(c,"texture-limit","Fixture exceeds GL texture capability");goto cleanup;}
    glDisable(GL_DITHER);glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);glDisable(GL_CULL_FACE);glDisable(GL_STENCIL_TEST);glDisable(GL_SAMPLE_COVERAGE);glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    GL_REQUIRE(program_create(c,&skin,kSkinVertex,kMaterialFragment,1));GL_REQUIRE(program_create(c,&material,kQuadVertex,kMaterialFragment,0));GL_REQUIRE(program_create(c,&present,pv,pf,0));
    if(skin.projection<0||skin.bones<0||skin.light<0||skin.diffuse<0||skin.ambient<0||skin.base<0||skin.dual<0||skin.const0<0||skin.const1<0||skin.fog_params<0||skin.fog_color<0||skin.alpha_ref<0||material.base<0||material.dual<0||material.const0<0||material.const1<0||material.fog_params<0||material.fog_color<0||material.alpha_ref<0||material.reference_color<0||material.reference_fog<0||glGetUniformLocation(present.id,"uImage")<0||glGetUniformLocation(present.id,"uViewport")<0){fail(c,"uniform-contract","Required material/skin shader uniform is missing");goto cleanup;}
    const uint8_t controlled_rgba[4]={51,153,230,128};
    GL_REQUIRE(texture_create(c,&base_tex,materials->base_w,materials->base_h,base.p));GL_REQUIRE(texture_create(c,&dual_tex,materials->dual_w,materials->dual_h,dual.p));GL_REQUIRE(texture_create(c,&controlled_tex,1,1,controlled_rgba));GL_REQUIRE(target_create(c,&skin_target,SKIN_SIZE,1));GL_REQUIRE(target_create(c,&material_target,64,0));
    glGenVertexArrays(1,&vao);glGenBuffers(1,&vbo);glGenBuffers(1,&ibo);glGenBuffers(1,&tf);glBindVertexArray(vao);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ibo);glBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)((size_t)mesh->index_count*4),indices,GL_STATIC_DRAW);glGenVertexArrays(1,&quad_vao);glGenBuffers(1,&quad_vbo);GL_REQUIRE(glcheck(c,"geometry-upload"));
    for(unsigned pose=0;pose<poses->count;pose++){
        /* Keep sampler bindings disjoint from the current FBO even during
         * transform feedback with rasterization discarded. */
        skin_uniforms(&skin,proj,base_tex,dual_tex);
        GL_REQUIRE(transform_check(c,&skin,vao,vbo,ibo,tf,vertices,poses,pose,proj));
        skin_uniforms(&skin,proj,base_tex,dual_tex);
        GL_REQUIRE(skin_render(c,&skin_target,&skin,vao,vbo,ibo,vertices,reference,indices,mesh,poses,pose,proj,actual,expected,edges));
    }
    c->skin_transform_match=1;c->skin_render_match=1;
    GL_REQUIRE(material_check(c,&material_target,&material,quad_vao,quad_vbo,base_tex,dual_tex,controlled_tex,materials,expected));c->material_pixel_match=1;
    GL_REQUIRE(display_window(c,d,surface,&skin_target,present.id,quad_vao,quad_vbo,actual));success=1;c->completed=1;textcopy(c->stage,"complete");
cleanup:
    if(current){glDisable(GL_RASTERIZER_DISCARD);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);target_delete(&skin_target);target_delete(&material_target);if(base_tex)glDeleteTextures(1,&base_tex);if(dual_tex)glDeleteTextures(1,&dual_tex);if(controlled_tex)glDeleteTextures(1,&controlled_tex);if(vao)glDeleteVertexArrays(1,&vao);if(quad_vao)glDeleteVertexArrays(1,&quad_vao);if(vbo)glDeleteBuffers(1,&vbo);if(ibo)glDeleteBuffers(1,&ibo);if(tf)glDeleteBuffers(1,&tf);if(quad_vbo)glDeleteBuffers(1,&quad_vbo);if(skin.id)glDeleteProgram(skin.id);if(material.id)glDeleteProgram(material.id);if(present.id)glDeleteProgram(present.id);if(!glcheck(c,"gpu-cleanup"))success=0;}
    int released=1;if(current&&!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)){egfail(c,"egl-release-current");released=0;}if(surface!=EGL_NO_SURFACE&&!eglDestroySurface(d,surface)){egfail(c,"egl-destroy-surface");released=0;}if(context!=EGL_NO_CONTEXT&&!eglDestroyContext(d,context)){egfail(c,"egl-destroy-context");released=0;}if(initialized&&!eglTerminate(d)){egfail(c,"egl-terminate");released=0;}if(!eglReleaseThread()){egfail(c,"egl-release-thread");released=0;}c->released=released;c->passed=success&&released;return c->passed;
#undef EGL_REQUIRE
#undef GL_REQUIRE
}

JNIEXPORT jstring JNICALL Java_org_coh_materialprobe_ProbeNative_probe(JNIEnv*env,jclass clazz,
    jobject java_surface,jbyteArray java_mesh,jbyteArray java_base,jbyteArray java_dual,
    jbyteArray java_poses,jbyteArray java_materials){
    (void)clazz;Report report={0};Bytes b[5]={{0}};ANativeWindow*window=NULL;Vertex*vertices=NULL,*reference=NULL;uint32_t*indices=NULL;uint8_t*actual=NULL,*expected=NULL,*edges=NULL;
    jbyteArray inputs[5]={java_mesh,java_base,java_dual,java_poses,java_materials};size_t total=0;
    if(!java_surface){textcopy(report.failure,"A live Android Surface is required");goto cleanup;}
    for(unsigned i=0;i<5;i++){if(!inputs[i]){textcopy(report.failure,"All five fixture byte arrays are required");goto cleanup;}jsize n=(*env)->GetArrayLength(env,inputs[i]);if(n<=0||(size_t)n>MAX_ASSET){textcopy(report.failure,"Fixture input exceeds 16-MiB per-asset bound");goto cleanup;}total+=(size_t)n;if(total>32u*1024u*1024u){textcopy(report.failure,"Fixture inputs exceed 32-MiB total bound");goto cleanup;}}
    for(unsigned i=0;i<5;i++)if(!copy_java(env,inputs[i],&b[i])){textcopy(report.failure,"JNI fixture input copy/allocation failed");goto cleanup;}
    if(coh_mesh_parse(b[0].p,b[0].n,&report.mesh)){textcopy(report.failure,"Canonical real mesh validation failed");goto cleanup;}
    if(!pose_parse(b[3],&report.mesh,&report.poses)||!material_parse(b[4],b[1],b[2],&report.materials)){textcopy(report.failure,"Independent pose/material reference validation failed");goto cleanup;}
    vertices=calloc(report.mesh.vertex_count,sizeof(Vertex));reference=calloc(report.mesh.vertex_count,sizeof(Vertex));indices=malloc((size_t)report.mesh.index_count*4);actual=malloc(SKIN_SIZE*SKIN_SIZE*4);expected=malloc(SKIN_SIZE*SKIN_SIZE*4);edges=malloc(SKIN_SIZE*SKIN_SIZE);
    if(!vertices||!reference||!indices||!actual||!expected||!edges){textcopy(report.failure,"Bounded mesh/reference/readback allocation failed");goto cleanup;}
    for(uint32_t i=0;i<report.mesh.vertex_count;i++){CohMeshVertex v;if(coh_mesh_vertex(&report.mesh,i,&v)){textcopy(report.failure,"Validated mesh vertex lookup failed");goto cleanup;}memcpy(vertices[i].position,v.position,sizeof(v.position));memcpy(vertices[i].normal,v.normal,sizeof(v.normal));memcpy(vertices[i].uv0,v.uv,sizeof(v.uv));memcpy(vertices[i].uv1,v.uv,sizeof(v.uv));memcpy(vertices[i].weights,v.weights,sizeof(v.weights));vertices[i].rows[0]=(int32_t)v.bones[0]*3;vertices[i].rows[1]=(int32_t)v.bones[1]*3;}
    for(uint32_t i=0;i<report.mesh.index_count;i++)if(coh_mesh_index(&report.mesh,i,&indices[i])){textcopy(report.failure,"Validated triangle index lookup failed");goto cleanup;}
    report.mesh_valid=1;float proj[16];projection(&report.poses,proj);window=ANativeWindow_fromSurface(env,java_surface);if((*env)->ExceptionCheck(env))(*env)->ExceptionClear(env);if(!window){textcopy(report.failure,"Android Surface is unavailable");goto cleanup;}
    report.passed=1;for(int i=0;i<CYCLES;i++){report.attempted++;if(!cycle_run(window,&report.mesh,&report.poses,&report.materials,b[1],b[2],vertices,reference,indices,proj,actual,expected,edges,&report.cycles[i])){report.passed=0;textcopy(report.failure,report.cycles[i].failure);break;}}
cleanup:
    if(window)ANativeWindow_release(window);for(unsigned i=0;i<5;i++)free(b[i].p);free(vertices);free(reference);free(indices);free(actual);free(expected);free(edges);return report_json(env,&report);
}
