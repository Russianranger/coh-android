/* Authored NPC costume native character qualification; no full sequencer/game integration.
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
#include "coh_character.h"
#include "coh_scene.h"
#include "shader_sources.h"

#define CYCLES 2
#define SKIN_SIZE 512
#define BYTE_TOLERANCE 2
#define FLOAT_TOLERANCE 0.0001f
#define MAX_ASSET (16u * 1024u * 1024u)
#define TEXT_CAP 512
#define JSON_CAP 65536
#define TF_FLOATS 9u
#define CHECKPOINTS 6u
#define PREVIEW_FRAMES 45u
#define IMAGE_DIAGNOSTICS 8u
#define TRIANGLE_DIAGNOSTICS 4u

typedef struct { uint8_t *p; size_t n; } Bytes;
typedef struct { float position[3],normal[3],uv0[2],uv1[2],weights[2]; int32_t rows[2]; } Vertex;
typedef struct {
    uint32_t count,bones,vertices,stride;
    const uint8_t *data;
} Poses;

typedef struct { uint32_t count; size_t stride; const uint8_t *data; } Materials;
typedef struct {
    const uint8_t *ids,*parents,*btt,*scales,*root,*draws,*cases;
    uint32_t count,bones,parts,vertices,stride,local,world,scaled,palettes,geometry;
} CharacterReference;
typedef struct {
    int sample_match,hierarchy_match,morph_match,palette_match,clock_match;
    uint64_t local_components,local_mismatches,world_components,world_mismatches;
    uint64_t scaled_components,scaled_mismatches,btt_components,btt_mismatches;
    uint64_t scale_components,scale_mismatches,palette_components,palette_mismatches;
    float local_max_error,world_max_error,scaled_max_error,btt_max_error;
    float scale_max_error,palette_max_error;
    unsigned samples,hierarchy_nodes,hierarchy_parents,clock_cases,clock_mismatches;
    unsigned base_fallback_samples,palettes_sampled;
} AnimationStats;
typedef struct {
    GLuint id; GLint projection,bones,light,diffuse,ambient,base,dual,const0,const1;
    GLint fog_params,fog_color,alpha_ref,reference_color,reference_fog;
} Program;
typedef struct { GLuint fbo,color,depth; int width,height; } Target;
typedef struct {
    uint32_t triangle,expected_inside,actual_inside;
    double expected_uv[2],actual_uv[2],expected_depth,actual_depth;
    uint32_t expected_depth24,actual_depth24;
    uint32_t expected_base_xy[2],actual_base_xy[2],expected_dual_xy[2],actual_dual_xy[2];
    uint8_t expected_base[4],actual_base[4],expected_dual[4],actual_dual[4];
} TriangleDiagnostic;
typedef struct {
    uint32_t part,sample,x,y,candidates;
    uint8_t expected[4],actual[4],expected_neighborhood[36],actual_neighborhood[36];
    TriangleDiagnostic triangles[TRIANGLE_DIAGNOSTICS];
} ImageDiagnostic;
typedef struct {
    int completed,passed,released,swap_passed,context_created;
    int skin_transform_match,skin_render_match,material_pixel_match,window_pixel_match;
    int character_assembly_match,width,height,viewport_x,viewport_y,viewport_w,viewport_h;
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
    uint64_t skin_pose_interiors[CHECKPOINTS],skin_pose_excluded[CHECKPOINTS],skin_pose_compared[CHECKPOINTS];
    uint64_t part_interior_pixels[COH_SCENE_PARTS],part_transform_vertices[COH_SCENE_PARTS];
    uint64_t part_palette_components[COH_SCENE_PARTS];
    uint64_t part_image_compared_pixels[COH_SCENE_PARTS],part_image_mismatches[COH_SCENE_PARTS];
    uint64_t standalone_compared_pixels,standalone_mismatches;
    unsigned standalone_max_byte_error;
    unsigned image_diagnostic_count;
    ImageDiagnostic image_diagnostics[IMAGE_DIAGNOSTICS];
    unsigned skin_max_byte_error,skin_poses;
    uint64_t material_pixels,material_mismatches,material_discard_clear_pixels;
    unsigned material_max_byte_error,material_cases,blend_cases,real_material_cases,synthetic_semantic_cases;
    unsigned window_samples,window_mismatches;
    AnimationStats animation;
    int animated_preview_passed;
    unsigned preview_frames,preview_clock_steps,preview_clock_wraps,distinct_animated_poses;
    unsigned preview_image_samples,preview_changed_image_samples;
    uint64_t preview_pixels_changed_from_first,preview_elapsed_ms;
    float preview_first_frame,preview_last_frame,preview_next_frame;
    char stage[TEXT_CAP],failure[TEXT_CAP],gl_vendor[TEXT_CAP],gl_renderer[TEXT_CAP];
    char gl_version[TEXT_CAP],glsl_version[TEXT_CAP],egl_vendor[TEXT_CAP],egl_version[TEXT_CAP];
} Cycle;
typedef struct {
    Vertex *vertices,*reference;
    float *feedback; /* actual GPU outputs, retained for mismatch diagnostics only */
    uint32_t *indices,ids[COH_ANIMATION_PALETTE];
    Poses poses; uint8_t *storage;
} Geometry;
typedef struct {
    int passed,character_valid,rig_valid,morph_valid,attempted;
    CohScene scene; CohAnimationRig *rig; CohCharacterMorph *morph;
    CharacterReference reference; Materials materials;
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

static int copy_java(JNIEnv*env,jbyteArray a,Bytes*out){if(!a)return 0;jsize n=(*env)->GetArrayLength(env,a);if(n<=0||(size_t)n>MAX_ASSET)return 0;out->p=malloc((size_t)n);if(!out->p)return 0;out->n=(size_t)n;(*env)->GetByteArrayRegion(env,a,0,n,(jbyte*)out->p);if((*env)->ExceptionCheck(env)){(*env)->ExceptionClear(env);return 0;}return 1;}
static void floats(const uint8_t*p,float*f,unsigned n){for(unsigned i=0;i<n;i++)f[i]=f32(p+i*4);}
static void put_float(uint8_t*p,float f){uint32_t b;memcpy(&b,&f,4);for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(b>>(i*8));}
static const uint8_t*pose_data(const Poses*p,unsigned i){return p->data+(size_t)i*p->stride;}
static const uint8_t*golden_data(const Poses*p,unsigned i){return pose_data(p,i)+(size_t)p->bones*48;}
static int reserved_zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
static int character_reference_parse(Bytes b,const CohScene*s,const CohAnimationRig*r,CharacterReference*out){
    const uint32_t fields[][2]={{8,1},{12,128},{16,6},{20,60},{24,11},{28,2626},{32,128},{36,368},{40,608},{44,1328},{48,2048},{52,2096},{56,2448},{60,72628},{64,438216},{68,4},{72,1684},{76,4564},{80,7444},{84,9604},{88,45},{92,32}};
    if(b.n!=438216||memcmp(b.p,"COHCHR01",8)||r->node_count!=60)return 0;
    for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(u32(b.p+fields[i][0])!=fields[i][1])return 0;
    if(f32(b.p+96)!=30||f32(b.p+100)!=1||f32(b.p+104)!=25||!reserved_zero(b.p+108,20))return 0;
    for(unsigned i=0;i<60;i++){uint32_t id=u32(b.p+128+i*4);if(id>=99||r->parent[id]==-2||(i&&u32(b.p+128+(i-1)*4)>=id)||(int32_t)u32(b.p+368+i*4)!=r->parent[id])return 0;}
    uint32_t first_vertex=0,first_palette=0;
    for(unsigned i=0;i<11;i++){const uint8_t*d=b.p+2096+i*32;const CohScenePart*p=&s->parts[i];
        if(u32(d)!=p->socket||u32(d+4)!=p->mesh.bone_count||u32(d+8)!=p->mesh.vertex_count||u32(d+12)!=first_vertex||u32(d+16)!=first_palette||u32(d+20)!=7444+first_palette*48||u32(d+24)!=9604+first_vertex*24||u32(d+28))return 0;
        first_vertex+=p->mesh.vertex_count;first_palette+=p->mesh.bone_count;
    }
    if(first_vertex!=2626||first_palette!=45)return 0;
    for(size_t o=608;o<2096;o+=4)if(!isfinite(f32(b.p+o))||fabsf(f32(b.p+o))>1000000)return 0;
    const float times[6]={1,1.5f,5.25f,12.5f,24.5f,25};
    for(unsigned i=0;i<6;i++){const uint8_t*c=b.p+2448+i*72628;if(f32(c)!=times[i])return 0;for(unsigned o=4;o<72628;o+=4)if(!isfinite(f32(c+o))||fabsf(f32(c+o))>1000000)return 0;}
    *out=(CharacterReference){b.p+128,b.p+368,b.p+608,b.p+1328,b.p+2048,b.p+2096,b.p+2448,6,60,11,2626,72628,4,1684,4564,7444,9604};return 1;
}
static int material_parse(Bytes b,const CohScene*s,Materials*out){
    if(b.n<64||memcmp(b.p,"COHCMAT8",8)||u32(b.p+8)!=1||u32(b.p+12)!=64||u32(b.p+16)!=64||u32(b.p+20)!=64||u32(b.p+24)!=s->part_count*6||u32(b.p+28)!=128||u32(b.p+32)!=s->part_count||u32(b.p+36)!=16384||u32(b.p+40)!=16512||u32(b.p+44)!=64||u32(b.p+48)!=b.n||!reserved_zero(b.p+52,12)||b.n!=64+s->part_count*6*16512)return 0;
    for(unsigned i=0;i<s->part_count*6;i++){const uint8_t*p=b.p+64+i*16512;
        for(unsigned o=0;o<104;o+=4)if(!isfinite(f32(p+o))||fabsf(f32(p+o))>1000000)return 0;
        if(f32(p+100)<0||f32(p+100)>1||(u32(p+104)&~3u)||u32(p+108)!=i/6||u32(p+112)!=i%6||!reserved_zero(p+116,12))return 0;
        for(unsigned k=0;k<8;k++){float expected=k==3&&i%6==1?.5f:k<4?s->parts[i/6].const0[k]:s->parts[i/6].const1[k-4];if(f32(p+k*4)!=expected)return 0;}
        const uint32_t expected_flags[6]={0,1,0,1,2,3};const float expected_ref[6]={0,0,0,1,0,.6f};
        if(u32(p+104)!=expected_flags[i%6]||f32(p+100)!=expected_ref[i%6]||f32(p+96)!=(i%6==2?15.f:0.f))return 0;
    }
    *out=(Materials){s->part_count*6,16512,b.p+64};return 1;
}
static void compare_scalar(float actual,float expected,uint64_t*count,uint64_t*mismatches,float*max){(*count)++;float error=fabsf(actual-expected);if(isfinite(error)&&error>*max)*max=error;if(!isfinite(actual)||error>FLOAT_TOLERANCE)(*mismatches)++;}
/* QUALIFICATION */
static int clock_check(const CohAnimationRig*r,AnimationStats*s){
    const float tests[8][5]={{1,1,1,1,2},{24.5f,.5f,1,1,25},{25,.5f,1,1,1.5f},{25,1,1,1,2},{25,100,1,1,1},{24,2,1,0,-1234},{14,10,0,1,14},{24,0,1,1,24}};
    for(unsigned i=0;i<8;i++){float next=-1234;s->clock_cases++;int status=coh_animation_step(r,tests[i][0],tests[i][1],tests[i][2],(int)tests[i][3],&next);int expected_status=i==5?2:0;if(status!=expected_status||next!=tests[i][4])s->clock_mismatches++;}
    s->clock_match=s->clock_mismatches==0;return s->clock_match;
}
static int prepare_runtime_poses(Cycle*c,const Report*r,Geometry*g){
    AnimationStats*s=&c->animation;const CharacterReference*ref=&r->reference;
    for(unsigned k=0;k<12;k++)compare_scalar(r->morph->actor_root_rows[k],f32(ref->root+k*4),&s->scale_components,&s->scale_mismatches,&s->scale_max_error);
    for(uint32_t i=0;i<ref->bones;i++){uint32_t id=u32(ref->ids+i*4);s->hierarchy_nodes++;s->hierarchy_parents++;
        if((int32_t)u32(ref->parents+i*4)!=r->rig->parent[id])return fail(c,"hierarchy-parents","Source hierarchy identity differs from reference");
        for(unsigned k=0;k<3;k++){compare_scalar(r->rig->bind_translation[id][k],f32(ref->btt+i*12+k*4),&s->btt_components,&s->btt_mismatches,&s->btt_max_error);compare_scalar(r->morph->bone_scales[id][k],f32(ref->scales+i*12+k*4),&s->scale_components,&s->scale_mismatches,&s->scale_max_error);}
    }
    for(unsigned sample=0;sample<ref->count;sample++){
        const uint8_t*gold=ref->cases+(size_t)sample*ref->stride;CohAnimationPose pose;
        if(coh_character_sample(r->rig,r->morph,f32(gold),&pose))return fail(c,"actor-sample","Native original raw-key/morph/hierarchy sample failed");s->samples++;
        for(uint32_t i=0;i<ref->bones;i++){uint32_t id=u32(ref->ids+i*4);const uint8_t*local=gold+ref->local+i*28;
            if(!r->rig->motion.tracks[id].present)s->base_fallback_samples++;
            for(unsigned k=0;k<4;k++)compare_scalar(pose.rotation[id][k],f32(local+k*4),&s->local_components,&s->local_mismatches,&s->local_max_error);
            for(unsigned k=0;k<3;k++)compare_scalar(pose.position[id][k],f32(local+16+k*4),&s->local_components,&s->local_mismatches,&s->local_max_error);
            for(unsigned k=0;k<12;k++){compare_scalar(pose.world_rows[id][k],f32(gold+ref->world+i*48+k*4),&s->world_components,&s->world_mismatches,&s->world_max_error);float scaled=pose.world_rows[id][k];if(k%4<3)scaled*=r->morph->bone_scales[id][k%4];compare_scalar(scaled,f32(gold+ref->scaled+i*48+k*4),&s->scaled_components,&s->scaled_mismatches,&s->scaled_max_error);}
        }
        for(unsigned part=0;part<r->scene.part_count;part++){const CohScenePart*p=&r->scene.parts[part];const uint8_t*d=ref->draws+part*32;float rows[COH_ANIMATION_PALETTE*12];
            if(coh_character_palette(r->rig,r->morph,&pose,p->socket,g[part].ids,p->mesh.bone_count,rows))return fail(c,"actor-socket-palette","Source two-stage inverse-bind/attachment fold failed");s->palettes_sampled++;
            uint8_t*runtime=g[part].storage+(size_t)sample*g[part].poses.stride;
            for(uint32_t k=0;k<p->mesh.bone_count*12;k++){compare_scalar(rows[k],f32(gold+u32(d+20)+k*4),&s->palette_components,&s->palette_mismatches,&s->palette_max_error);put_float(runtime+k*4,rows[k]);c->part_palette_components[part]++;}
            memcpy(runtime+p->mesh.bone_count*48,gold+u32(d+24),(size_t)p->mesh.vertex_count*24);
        }
    }
    s->sample_match=s->samples==6&&!s->local_mismatches;
    s->hierarchy_match=!s->world_mismatches&&!s->btt_mismatches;
    s->morph_match=!s->scale_mismatches&&!s->scaled_mismatches;
    s->palette_match=!s->palette_mismatches&&s->palettes_sampled==66;
    if(!clock_check(r->rig,s))return fail(c,"animation-clock","Original strict-end subtract-once clock differs");
    if(!s->sample_match||!s->hierarchy_match||!s->morph_match||!s->palette_match)return fail(c,"actor-stage-parity","Native actor local/hierarchy/morph/socket stages differ from independent source goldens");return 1;
}
static int projection(Cycle*c,const Report*r,const Geometry*g,float*out){
    float lo[3]={INFINITY,INFINITY,INFINITY},hi[3]={-INFINITY,-INFINITY,-INFINITY};float frame=1;
    for(unsigned tick=0;tick<PREVIEW_FRAMES;tick++){CohAnimationPose pose;if(coh_character_sample(r->rig,r->morph,frame,&pose))return fail(c,"projection-sample","Native actor sample failed while fitting all preview frames");
        for(unsigned p=0;p<r->scene.part_count;p++){const CohScenePart*part=&r->scene.parts[p];float rows[COH_ANIMATION_PALETTE*12];if(coh_character_palette(r->rig,r->morph,&pose,part->socket,g[p].ids,part->mesh.bone_count,rows))return fail(c,"projection-palette","Native actor palette failed while fitting preview");
            for(uint32_t v=0;v<part->mesh.vertex_count;v++){CohMeshVertex vertex;CohSkinnedVertex skin;if(coh_mesh_vertex(&part->mesh,v,&vertex)||coh_mesh_skin_vertex(&vertex,rows,part->mesh.bone_count,&skin))return fail(c,"projection-skin","Native preview bounds skin failed");for(unsigned k=0;k<3;k++){float x=skin.position[k];if(x<lo[k])lo[k]=x;if(x>hi[k])hi[k]=x;}}
        }
        if(coh_animation_step(r->rig,frame,1,1,1,&frame))return fail(c,"projection-clock","Native clock failed while fitting preview");
    }
    /* Include fractional independent checkpoints as well as all live frames. */
    for(unsigned p=0;p<r->scene.part_count;p++)for(unsigned sample=0;sample<6;sample++){const uint8_t*gold=golden_data(&g[p].poses,sample);for(uint32_t v=0;v<g[p].poses.vertices;v++)for(unsigned k=0;k<3;k++){float x=f32(gold+v*24+k*4);if(x<lo[k])lo[k]=x;if(x>hi[k])hi[k]=x;}}
    float half=fmaxf(hi[0]-lo[0],hi[1]-lo[1])*.60f,zhalf=(hi[2]-lo[2])*.60f;if(half<.0001f||zhalf<.0001f)return fail(c,"projection-degenerate","Character bounds are degenerate");
    memset(out,0,16*sizeof(float));out[0]=out[5]=1/half;out[10]=-1/zhalf;out[12]=-(hi[0]+lo[0])*.5f/half;out[13]=-(hi[1]+lo[1])*.5f/half;out[14]=(hi[2]+lo[2])*.5f/zhalf;out[15]=1;return 1;
}
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
                          const Vertex*vertices,const Poses*poses,unsigned pose,const float*proj,float*feedback){
    float rows[COH_MESH_MAX_BONES*12];floats(pose_data(poses,pose),rows,poses->bones*12);
    glUseProgram(p->id);glUniformMatrix4fv(p->projection,1,GL_FALSE,proj);glUniform4fv(p->bones,(GLsizei)poses->bones*3,rows);glUniform3f(p->light,0,0,1);glUniform4f(p->diffuse,.2f,.2f,.2f,0);glUniform4f(p->ambient,.05f,.05f,.05f,1);
    vertex_layout(vao,vbo,index);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)poses->vertices*sizeof(Vertex)),vertices,GL_DYNAMIC_DRAW);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(GLsizeiptr)((size_t)poses->vertices*TF_FLOATS*sizeof(float)),NULL,GL_DYNAMIC_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,tf);
    glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,(GLsizei)poses->vertices);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);
    if(!glcheck(c,"skin-transform-feedback"))return 0;
    float*actual=glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,(GLsizeiptr)((size_t)poses->vertices*TF_FLOATS*sizeof(float)),GL_MAP_READ_BIT);if(!actual)return fail(c,"transform-map","Transform-feedback buffer could not be mapped");
    /* These outputs explain failures; they never replace independent goldens
     * or drive the CPU reference image, camera, palette or acceptance gate. */
    memcpy(feedback,actual,(size_t)poses->vertices*TF_FLOATS*sizeof(float));
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

static int display_window(Cycle*c,EGLDisplay d,EGLSurface surface,Target*t,GLuint program,
                          GLuint vao,GLuint vbo,const uint8_t*image,int validate){
    EGLint w=0,h=0;if(!eglQuerySurface(d,surface,EGL_WIDTH,&w)||!eglQuerySurface(d,surface,EGL_HEIGHT,&h))return egfail(c,"surface-query");
    if(w<=0||h<=0||w>16384||h>16384)return fail(c,"surface-size","Surface dimensions outside bounded positive range");c->width=w;c->height=h;
    int size=w<h?w:h;c->viewport_w=c->viewport_h=size;c->viewport_x=(w-size)/2;c->viewport_y=(h-size)/2;
    const float quad[]={-1,-1,1,-1,1,1,-1,-1,1,1,-1,1};glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,2*sizeof(float),(void*)0);glEnableVertexAttribArray(0);glDisableVertexAttribArray(2);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glViewport(0,0,w,h);glClearColor(.04f,.04f,.06f,1);glClear(GL_COLOR_BUFFER_BIT);glViewport(c->viewport_x,c->viewport_y,size,size);glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,t->color);glUniform1i(glGetUniformLocation(program,"uImage"),0);glUniform4i(glGetUniformLocation(program,"uViewport"),c->viewport_x,c->viewport_y,size,size);glDrawArrays(GL_TRIANGLES,0,6);if(!glcheck(c,"window-draw"))return 0;
    if(validate){
        for(int gy=1;gy<=7;gy++)for(int gx=1;gx<=7;gx++){int lx=gx*size/8,ly=gy*size/8;if(lx>=size)lx=size-1;if(ly>=size)ly=size-1;unsigned tx=(unsigned)(((uint64_t)(2*lx+1)*SKIN_SIZE)/(2u*(unsigned)size)),ty=(unsigned)(((uint64_t)(2*ly+1)*SKIN_SIZE)/(2u*(unsigned)size));uint8_t got[4]={0};glReadPixels(c->viewport_x+lx,c->viewport_y+ly,1,1,GL_RGBA,GL_UNSIGNED_BYTE,got);if(!glcheck(c,"window-readback"))return 0;c->window_samples++;if(pixel_error(got,image+((size_t)ty*SKIN_SIZE+tx)*4,3))c->window_mismatches++;}
        if(c->window_mismatches)return fail(c,"window-parity","Opaque RGB window samples differ from final qualified mesh FBO");c->window_pixel_match=1;
    }
    if(!eglSwapBuffers(d,surface))return egfail(c,"swap-buffers");c->swap_passed=1;return glcheck(c,"post-swap");
}


static void skin_uniforms(Program*p,const float*proj,const CohScenePart*part,const GLuint*textures){
    glUseProgram(p->id);glUniformMatrix4fv(p->projection,1,GL_FALSE,proj);glUniform3f(p->light,.188144f,.282216f,.940721f);
    glUniform4f(p->diffuse,.18f*part->diffuse_scale,.18f*part->diffuse_scale,.18f*part->diffuse_scale,0);
    glUniform4f(p->ambient,.055f*part->ambient_scale,.055f*part->ambient_scale,.055f*part->ambient_scale,1);
    glUniform4fv(p->const0,1,part->const0);glUniform4fv(p->const1,1,part->const1);glUniform4f(p->fog_params,0,0,1000000,1);glUniform4f(p->fog_color,0,0,0,1);glUniform1f(p->alpha_ref,part->alpha_ref);bind_textures(p,textures[part->base_texture],textures[part->dual_texture]);
}
static void target_clear(Target*t){glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,SKIN_SIZE,SKIN_SIZE);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClearColor(17/255.f,19/255.f,23/255.f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);}
static void reference_vertices(Geometry*g,unsigned sample){const uint8_t*gold=golden_data(&g->poses,sample);for(uint32_t v=0;v<g->poses.vertices;v++){g->reference[v]=g->vertices[v];floats(gold+v*24,g->reference[v].position,3);floats(gold+v*24+12,g->reference[v].normal,3);g->reference[v].weights[0]=1;g->reference[v].weights[1]=0;g->reference[v].rows[0]=g->reference[v].rows[1]=0;}}
static int part_draw(Cycle*c,Program*p,GLuint vao,GLuint vbo,GLuint ibo,const CohScenePart*part,const Geometry*g,const Vertex*vertices,const float*rows,unsigned bones,const float*proj,const GLuint*textures){
    glFrontFace(GL_CW);glCullFace(GL_BACK);if(part->flags&1u)glDisable(GL_CULL_FACE);else glEnable(GL_CULL_FACE);
    if(part->flags&2u){glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
    skin_uniforms(p,proj,part,textures);glUniform4fv(p->bones,(GLsizei)bones*3,rows);vertex_layout(vao,vbo,ibo);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)((size_t)part->mesh.vertex_count*sizeof(Vertex)),vertices,GL_DYNAMIC_DRAW);glBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)((size_t)part->mesh.index_count*4),g->indices,GL_DYNAMIC_DRAW);glDrawElements(GL_TRIANGLES,(GLsizei)part->mesh.index_count,GL_UNSIGNED_INT,(void*)0);return glcheck(c,"character-part-draw");
}
static int character_draw(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,GLuint ibo,const Report*r,const Geometry*g,const GLuint*textures,const float*proj,const float rows[COH_SCENE_PARTS][COH_ANIMATION_PALETTE*12],int reference,uint8_t*out){
    const float identity[12]={1,0,0,0,0,1,0,0,0,0,1,0};target_clear(t);glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    for(unsigned i=0;i<r->scene.part_count;i++)if(!part_draw(c,p,vao,vbo,ibo,&r->scene.parts[i],&g[i],reference?g[i].reference:g[i].vertices,reference?identity:rows[i],reference?1:r->scene.parts[i].mesh.bone_count,proj,textures))return 0;
    if(out)glReadPixels(0,0,SKIN_SIZE,SKIN_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,out);return glcheck(c,"character-render-readback");
}
static int standalone_projection(Cycle*c,const Geometry*g,float*out){
    float lo[3]={INFINITY,INFINITY,INFINITY},hi[3]={-INFINITY,-INFINITY,-INFINITY};
    for(unsigned sample=0;sample<g->poses.count;sample++){const uint8_t*gold=golden_data(&g->poses,sample);for(uint32_t v=0;v<g->poses.vertices;v++)for(unsigned k=0;k<3;k++){float x=f32(gold+v*24+k*4);if(x<lo[k])lo[k]=x;if(x>hi[k])hi[k]=x;}}
    float half=fmaxf(hi[0]-lo[0],hi[1]-lo[1])*.60f,zhalf=(hi[2]-lo[2])*.60f;
    if(!isfinite(half)||!isfinite(zhalf)||half<.0001f||zhalf<.0001f)return fail(c,"standalone-projection","Real part checkpoint bounds are degenerate");
    memset(out,0,16*sizeof(float));out[0]=out[5]=1/half;out[10]=-1/zhalf;out[12]=-(hi[0]+lo[0])*.5f/half;out[13]=-(hi[1]+lo[1])*.5f/half;out[14]=(hi[2]+lo[2])*.5f/zhalf;out[15]=1;return 1;
}
static int diagnostic_barycentric(const Geometry*g,const uint32_t*indices,int actual,const float*proj,unsigned x,unsigned y,double*bary,double*depth){
    double xy[3][2],z[3];
    for(unsigned j=0;j<3;j++){const float*p=actual?g->feedback+(size_t)indices[j]*TF_FLOATS:g->reference[indices[j]].position;xy[j][0]=((double)p[0]*proj[0]+proj[12]+1)*(.5*SKIN_SIZE);xy[j][1]=((double)p[1]*proj[5]+proj[13]+1)*(.5*SKIN_SIZE);z[j]=((double)p[2]*proj[10]+proj[14]+1)*.5;}
    double area=(xy[1][0]-xy[0][0])*(xy[2][1]-xy[0][1])-(xy[1][1]-xy[0][1])*(xy[2][0]-xy[0][0]);if(fabs(area)<1e-12)return 0;
    double px=x+.5,py=y+.5;
    bary[0]=((xy[1][0]-px)*(xy[2][1]-py)-(xy[1][1]-py)*(xy[2][0]-px))/area;
    bary[1]=((xy[2][0]-px)*(xy[0][1]-py)-(xy[2][1]-py)*(xy[0][0]-px))/area;bary[2]=1-bary[0]-bary[1];*depth=bary[0]*z[0]+bary[1]*z[1]+bary[2]*z[2];return bary[0]>=0&&bary[1]>=0&&bary[2]>=0;
}
static void diagnostic_texel(const CohSceneTexture*t,const double*uv,uint32_t*xy,uint8_t*rgba){
    double x=floor(uv[0]*t->width),y=floor(uv[1]*t->height);if(x<0)x=0;if(y<0)y=0;if(x>=t->width)x=t->width-1;if(y>=t->height)y=t->height-1;xy[0]=(uint32_t)x;xy[1]=(uint32_t)y;memcpy(rgba,t->rgba+((size_t)xy[1]*t->width+xy[0])*4,4);
}
static uint32_t diagnostic_depth24(double depth){if(depth<0)depth=0;if(depth>1)depth=1;return (uint32_t)floor(depth*16777215.0+.5);}
static void image_diagnostic(Cycle*c,const Report*r,const Geometry*g,unsigned part,unsigned sample,unsigned x,unsigned y,const float*proj,const uint8_t*actual,const uint8_t*expected){
    if(c->image_diagnostic_count>=IMAGE_DIAGNOSTICS)return;ImageDiagnostic*d=&c->image_diagnostics[c->image_diagnostic_count++];d->part=part;d->sample=sample;d->x=x;d->y=y;memcpy(d->expected,expected+((size_t)y*SKIN_SIZE+x)*4,4);memcpy(d->actual,actual+((size_t)y*SKIN_SIZE+x)*4,4);
    unsigned k=0;for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){int xx=(int)x+dx,yy=(int)y+dy;if(xx<0)xx=0;if(yy<0)yy=0;if(xx>=SKIN_SIZE)xx=SKIN_SIZE-1;if(yy>=SKIN_SIZE)yy=SKIN_SIZE-1;memcpy(d->expected_neighborhood+k*4,expected+((size_t)yy*SKIN_SIZE+(unsigned)xx)*4,4);memcpy(d->actual_neighborhood+k*4,actual+((size_t)yy*SKIN_SIZE+(unsigned)xx)*4,4);k++;}
    const CohScenePart*p=&r->scene.parts[part];
    for(uint32_t tri=0;tri<p->mesh.index_count;tri+=3){const uint32_t*ids=g->indices+tri;double eb[3]={0},ab[3]={0},ed=0,ad=0;int ei=diagnostic_barycentric(g,ids,0,proj,x,y,eb,&ed),ai=diagnostic_barycentric(g,ids,1,proj,x,y,ab,&ad);if(!ei&&!ai)continue;
        TriangleDiagnostic t={0};t.triangle=tri/3;t.expected_inside=(uint32_t)ei;t.actual_inside=(uint32_t)ai;t.expected_depth=ed;t.actual_depth=ad;t.expected_depth24=diagnostic_depth24(ed);t.actual_depth24=diagnostic_depth24(ad);
        for(unsigned j=0;j<3;j++)for(unsigned component=0;component<2;component++){t.expected_uv[component]+=eb[j]*g->vertices[ids[j]].uv0[component];t.actual_uv[component]+=ab[j]*g->vertices[ids[j]].uv0[component];}
        diagnostic_texel(&r->scene.textures[p->base_texture],t.expected_uv,t.expected_base_xy,t.expected_base);diagnostic_texel(&r->scene.textures[p->base_texture],t.actual_uv,t.actual_base_xy,t.actual_base);diagnostic_texel(&r->scene.textures[p->dual_texture],t.expected_uv,t.expected_dual_xy,t.expected_dual);diagnostic_texel(&r->scene.textures[p->dual_texture],t.actual_uv,t.actual_dual_xy,t.actual_dual);
        /* Retain the four nearest covering triangles, with source draw IDs.
         * UV/depth are double CPU reconstructions, not GPU interpolator capture. */
        unsigned slot=d->candidates;if(slot<TRIANGLE_DIAGNOSTICS){d->triangles[slot]=t;d->candidates++;}else {slot=0;for(unsigned j=1;j<TRIANGLE_DIAGNOSTICS;j++)if(fmin(d->triangles[j].expected_depth,d->triangles[j].actual_depth)>fmin(d->triangles[slot].expected_depth,d->triangles[slot].actual_depth))slot=j;if(fmin(t.expected_depth,t.actual_depth)<fmin(d->triangles[slot].expected_depth,d->triangles[slot].actual_depth))d->triangles[slot]=t;}
    }
}
static int skin_render(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,GLuint ibo,const Report*r,Geometry*g,const GLuint*textures,unsigned sample,const float*proj,uint8_t*actual,uint8_t*expected,uint8_t*edges,uint8_t*temporary_edges){
    float rows[COH_SCENE_PARTS][COH_ANIMATION_PALETTE*12];const float identity[12]={1,0,0,0,0,1,0,0,0,0,1,0};const uint8_t clear[4]={17,19,23,255};memset(edges,0,SKIN_SIZE*SKIN_SIZE);
    for(unsigned i=0;i<r->scene.part_count;i++){const CohScenePart*part=&r->scene.parts[i];reference_vertices(&g[i],sample);floats(pose_data(&g[i].poses,sample),rows[i],part->mesh.bone_count*12);
        /* Preserve the whole-actor triangle guard in the whole-actor camera.
         * Small dense parts then receive a separate diagnostic camera below. */
        edge_mask(g[i].reference,g[i].indices,part->mesh.index_count,proj,temporary_edges);
        for(size_t k=0;k<SKIN_SIZE*SKIN_SIZE;k++)if(temporary_edges[k])edges[k]=1;
        float part_projection[16];if(!standalone_projection(c,&g[i],part_projection))return 0;
        /* Standalone visibility prevents an omitted/small part from hiding
         * behind aggregate coverage or the other costume draws. */
        target_clear(t);glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        if(!part_draw(c,p,vao,vbo,ibo,part,&g[i],g[i].reference,identity,1,part_projection,textures))return 0;
        glReadPixels(0,0,SKIN_SIZE,SKIN_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,expected);if(!glcheck(c,"part-coverage-readback"))return 0;
        edge_mask(g[i].reference,g[i].indices,part->mesh.index_count,part_projection,temporary_edges);
        target_clear(t);if(!part_draw(c,p,vao,vbo,ibo,part,&g[i],g[i].vertices,rows[i],part->mesh.bone_count,part_projection,textures))return 0;glReadPixels(0,0,SKIN_SIZE,SKIN_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,actual);if(!glcheck(c,"part-gpu-reference-readback"))return 0;
        uint64_t part_interior=0;
        for(size_t k=0;k<SKIN_SIZE*SKIN_SIZE;k++){if(temporary_edges[k])continue;if(memcmp(expected+k*4,clear,4)){c->part_interior_pixels[i]++;part_interior++;}c->part_image_compared_pixels[i]++;c->standalone_compared_pixels++;unsigned error=pixel_error(actual+k*4,expected+k*4,4);if(error>c->standalone_max_byte_error)c->standalone_max_byte_error=error;if(error>BYTE_TOLERANCE){c->part_image_mismatches[i]++;c->standalone_mismatches++;image_diagnostic(c,r,&g[i],i,sample,(unsigned)(k%SKIN_SIZE),(unsigned)(k/SKIN_SIZE),part_projection,actual,expected);}}
        if(part_interior<64)return fail(c,"part-zoom-coverage","Fewer than 64 isolated source-material pixels outside triangle edges in the part camera");
    }
    if(c->standalone_mismatches)return fail(c,"part-image-parity","An isolated GPU costume draw differs from independent CPU geometry outside excluded edges");
    if(!character_draw(c,t,p,vao,vbo,ibo,r,g,textures,proj,rows,1,expected)||!character_draw(c,t,p,vao,vbo,ibo,r,g,textures,proj,rows,0,actual))return 0;
    uint64_t interior=0;
    for(size_t k=0;k<SKIN_SIZE*SKIN_SIZE;k++){if(edges[k]){c->skin_edge_excluded_pixels++;c->skin_pose_excluded[sample]++;continue;}c->skin_compared_pixels++;c->skin_pose_compared[sample]++;if(memcmp(expected+k*4,clear,4)){c->skin_interior_pixels++;interior++;}unsigned error=pixel_error(actual+k*4,expected+k*4,4);if(error>c->skin_max_byte_error)c->skin_max_byte_error=error;if(error>BYTE_TOLERANCE)c->skin_mismatches++;}
    c->skin_pose_interiors[sample]=interior;c->skin_poses++;if(interior<64)return fail(c,"character-image-coverage","Fewer than 64 assembled character pixels outside triangle edges");return c->skin_mismatches?fail(c,"character-image-parity","Assembled GPU character differs from independent CPU geometry outside excluded edges"):1;
}
static int material_check(Cycle*c,Target*t,Program*p,GLuint vao,GLuint vbo,const GLuint*textures,GLuint controlled,const Report*r,uint8_t*readback){
    static const float quad[]={-1,-1,0,0,1,-1,1,0,1,1,1,1,-1,-1,0,0,1,1,1,1,-1,1,0,1};glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)0);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,4*sizeof(float),(void*)(2*sizeof(float)));glEnableVertexAttribArray(0);glEnableVertexAttribArray(2);
    glUseProgram(p->id);glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glViewport(0,0,64,64);glDisable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    for(uint32_t i=0;i<r->materials.count;i++){const uint8_t*record=r->materials.data+i*r->materials.stride;const CohScenePart*part=&r->scene.parts[u32(record+108)];uint32_t flags=u32(record+104);bind_textures(p,textures[part->base_texture],flags&2u?controlled:textures[part->dual_texture]);if(flags&2u)c->synthetic_semantic_cases++;else c->real_material_cases++;float clear[4];floats(record+80,clear,4);glClearColor(clear[0],clear[1],clear[2],clear[3]);glClear(GL_COLOR_BUFFER_BIT);if(flags&1u){glEnable(GL_BLEND);c->blend_cases++;}else glDisable(GL_BLEND);material_uniforms(p,record);glDrawArrays(GL_TRIANGLES,0,6);glReadPixels(0,0,64,64,GL_RGBA,GL_UNSIGNED_BYTE,readback);if(!glcheck(c,"character-material-readback"))return 0;
        uint8_t clear_bytes[4];for(unsigned k=0;k<4;k++){float x=fminf(1,fmaxf(0,clear[k]));clear_bytes[k]=(uint8_t)floorf(x*255+.5f);}const uint8_t*golden=record+128;for(unsigned k=0;k<64*64;k++){unsigned error=pixel_error(readback+k*4,golden+k*4,4);c->material_pixels++;if(error>c->material_max_byte_error)c->material_max_byte_error=error;if(error>BYTE_TOLERANCE)c->material_mismatches++;if(!memcmp(golden+k*4,clear_bytes,4))c->material_discard_clear_pixels++;}c->material_cases++;
    }
    glDisable(GL_BLEND);return c->material_mismatches?fail(c,"character-material-parity","Actual per-part texture/color CPU references differ from native dual shader"):1;
}
static uint64_t monotonic_ms(const struct timespec*t){return (uint64_t)t->tv_sec*1000+(uint64_t)t->tv_nsec/1000000;}
static int animated_preview(Cycle*c,EGLDisplay d,EGLSurface surface,Target*t,Program*skin,GLuint present,GLuint vao,GLuint vbo,GLuint ibo,GLuint qvao,GLuint qvbo,const Report*r,const Geometry*g,const GLuint*textures,const float*proj,uint8_t*actual,uint8_t*first_image){
    struct timespec start;if(clock_gettime(CLOCK_MONOTONIC,&start))return fail(c,"preview-clock","Monotonic clock unavailable");
    float distinct[PREVIEW_FRAMES][45*12],frame=r->rig->first_frame;c->preview_first_frame=frame;
    for(unsigned tick=0;tick<PREVIEW_FRAMES;tick++){CohAnimationPose pose;float rows[COH_SCENE_PARTS][COH_ANIMATION_PALETTE*12],flat[45*12];unsigned offset=0;
        if(coh_character_sample(r->rig,r->morph,frame,&pose))return fail(c,"preview-actor-sample","Live raw-key actor sampling failed");
        for(unsigned i=0;i<r->scene.part_count;i++){const CohScenePart*p=&r->scene.parts[i];if(coh_character_palette(r->rig,r->morph,&pose,p->socket,g[i].ids,p->mesh.bone_count,rows[i]))return fail(c,"preview-part-palette","Live per-part palette generation failed");memcpy(flat+offset,rows[i],p->mesh.bone_count*48);offset+=p->mesh.bone_count*12;}
        int known=0;for(unsigned i=0;i<c->distinct_animated_poses;i++)if(!memcmp(distinct[i],flat,sizeof flat)){known=1;break;}if(!known){memcpy(distinct[c->distinct_animated_poses],flat,sizeof flat);c->distinct_animated_poses++;}
        int capture=tick==0||tick==15||tick==30;if(!character_draw(c,t,skin,vao,vbo,ibo,r,g,textures,proj,rows,0,capture?actual:NULL))return 0;
        if(capture){c->preview_image_samples++;if(!tick)memcpy(first_image,actual,SKIN_SIZE*SKIN_SIZE*4);else{uint64_t changed=0;for(size_t i=0;i<SKIN_SIZE*SKIN_SIZE;i++)if(pixel_error(actual+i*4,first_image+i*4,4)>BYTE_TOLERANCE)changed++;if(changed)c->preview_changed_image_samples++;c->preview_pixels_changed_from_first+=changed;}}
        if(!display_window(c,d,surface,t,present,qvao,qvbo,NULL,0))return 0;c->preview_frames++;c->preview_last_frame=frame;float next;if(coh_animation_step(r->rig,frame,1,1,1,&next))return fail(c,"preview-source-clock","Original source clip clock failed");c->preview_clock_steps++;if(next<frame)c->preview_clock_wraps++;frame=next;c->preview_next_frame=frame;
        uint64_t ns=(uint64_t)start.tv_nsec+(uint64_t)(tick+1)*(1000000000u/30u);struct timespec deadline={start.tv_sec+(time_t)(ns/1000000000u),(long)(ns%1000000000u)};int status;do{status=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&deadline,NULL);}while(status==EINTR);if(status)return fail(c,"preview-pacing","Bounded preview pacing failed");
    }
    struct timespec end;if(clock_gettime(CLOCK_MONOTONIC,&end))return fail(c,"preview-clock","Monotonic end clock unavailable");c->preview_elapsed_ms=monotonic_ms(&end)-monotonic_ms(&start);
    if(c->preview_frames!=45||c->distinct_animated_poses<2||!c->preview_clock_wraps||c->preview_image_samples!=3||!c->preview_changed_image_samples||c->preview_pixels_changed_from_first<64||c->preview_first_frame!=1||c->preview_last_frame!=21||c->preview_next_frame!=22)return fail(c,"preview-coverage","Preview lacks 45 source-clock frames and visible assembled character motion");c->animated_preview_passed=1;
    glBindFramebuffer(GL_FRAMEBUFFER,t->fbo);glReadPixels(0,0,SKIN_SIZE,SKIN_SIZE,GL_RGBA,GL_UNSIGNED_BYTE,actual);if(!glcheck(c,"preview-final-image"))return 0;return display_window(c,d,surface,t,present,qvao,qvbo,actual,1);
}
static int cycle_run(ANativeWindow*window,const Report*r,Geometry*g,uint8_t*actual,uint8_t*expected,uint8_t*edges,uint8_t*temporary_edges,Cycle*c){
    EGLDisplay d=EGL_NO_DISPLAY;EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;int initialized=0,current=0,success=0;
    GLuint textures[COH_SCENE_TEXTURES]={0},controlled=0,vao=0,vbo=0,ibo=0,tf=0,qvao=0,qvbo=0;Program skin={0},material={0},present={0};Target skin_target={0},material_target={0};float proj[16];
    EGLint maj=0,min=0,n=0,visual=0;EGLConfig config=NULL;const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT_KHR,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,0,EGL_STENCIL_SIZE,0,EGL_NONE};const EGLint ctxattrs[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
    const char*pv="#version 300 es\nlayout(location=0) in vec2 aPosition; void main(){gl_Position=vec4(aPosition,0,1);}\n";
    const char*pf="#version 300 es\nprecision highp float;precision highp int;uniform highp sampler2D uImage;uniform ivec4 uViewport;layout(location=0)out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy)-uViewport.xy;ivec2 t=((2*p+ivec2(1))*ivec2(512))/(2*uViewport.zw);t=clamp(t,ivec2(0),ivec2(511));color=vec4(texelFetch(uImage,t,0).rgb,1.0);}\n";
#define EGL_REQUIRE(call,stage) if(!(call)){egfail(c,stage);goto cleanup;}
#define GL_REQUIRE(call) if(!(call))goto cleanup
    GL_REQUIRE(prepare_runtime_poses(c,r,g));GL_REQUIRE(projection(c,r,g,proj));
    d=eglGetDisplay(EGL_DEFAULT_DISPLAY);if(d==EGL_NO_DISPLAY){egfail(c,"egl-display");goto cleanup;}EGL_REQUIRE(eglInitialize(d,&maj,&min),"egl-initialize");initialized=1;textcopy(c->egl_vendor,eglQueryString(d,EGL_VENDOR));textcopy(c->egl_version,eglQueryString(d,EGL_VERSION));EGL_REQUIRE(eglBindAPI(EGL_OPENGL_ES_API),"egl-bind-api");EGL_REQUIRE(eglChooseConfig(d,attrs,&config,1,&n),"egl-config");if(!n){fail(c,"egl-config","No RGBA8 GLES3 window configuration");goto cleanup;}EGL_REQUIRE(eglGetConfigAttrib(d,config,EGL_NATIVE_VISUAL_ID,&visual),"egl-native-format");if(ANativeWindow_setBuffersGeometry(window,0,0,visual)){fail(c,"window-format","Native window buffer format failed");goto cleanup;}
    surface=eglCreateWindowSurface(d,config,window,NULL);if(surface==EGL_NO_SURFACE){egfail(c,"egl-window-surface");goto cleanup;}context=eglCreateContext(d,config,EGL_NO_CONTEXT,ctxattrs);if(context==EGL_NO_CONTEXT){egfail(c,"egl-context");goto cleanup;}c->context_created=1;EGL_REQUIRE(eglMakeCurrent(d,surface,surface,context),"egl-current");current=1;
    textcopy(c->gl_vendor,(const char*)glGetString(GL_VENDOR));textcopy(c->gl_renderer,(const char*)glGetString(GL_RENDERER));textcopy(c->gl_version,(const char*)glGetString(GL_VERSION));textcopy(c->glsl_version,(const char*)glGetString(GL_SHADING_LANGUAGE_VERSION));GLint maxtex=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxtex);GL_REQUIRE(glcheck(c,"gl-capabilities"));if(maxtex<SKIN_SIZE){fail(c,"texture-limit","512-square character FBO exceeds GL capability");goto cleanup;}
    for(unsigned i=0;i<r->scene.texture_count;i++)if(r->scene.textures[i].width>(unsigned)maxtex||r->scene.textures[i].height>(unsigned)maxtex){fail(c,"texture-limit","Actual costume texture exceeds GL capability");goto cleanup;}
    glDisable(GL_DITHER);glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);glDisable(GL_CULL_FACE);glDisable(GL_STENCIL_TEST);glDisable(GL_SAMPLE_COVERAGE);glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    GL_REQUIRE(program_create(c,&skin,kSkinVertex,kMaterialFragment,1));GL_REQUIRE(program_create(c,&material,kQuadVertex,kMaterialFragment,0));GL_REQUIRE(program_create(c,&present,pv,pf,0));
    if(skin.projection<0||skin.bones<0||skin.light<0||skin.diffuse<0||skin.ambient<0||skin.base<0||skin.dual<0||skin.const0<0||skin.const1<0||skin.fog_params<0||skin.fog_color<0||skin.alpha_ref<0||material.base<0||material.dual<0||material.const0<0||material.const1<0||material.fog_params<0||material.fog_color<0||material.alpha_ref<0||material.reference_color<0||material.reference_fog<0||glGetUniformLocation(present.id,"uImage")<0||glGetUniformLocation(present.id,"uViewport")<0){fail(c,"uniform-contract","Accepted shader required uniform is missing");goto cleanup;}
    for(unsigned i=0;i<r->scene.texture_count;i++){const CohSceneTexture*t=&r->scene.textures[i];GL_REQUIRE(texture_create(c,&textures[i],t->width,t->height,t->rgba));}
    const uint8_t controlled_rgba[4]={51,153,230,128};GL_REQUIRE(texture_create(c,&controlled,1,1,controlled_rgba));GL_REQUIRE(target_create(c,&skin_target,SKIN_SIZE,1));GL_REQUIRE(target_create(c,&material_target,64,0));
    /* Source rt_tex.c defaults MAG to LINEAR and nonmipped MIN to LINEAR.
     * The character gate admits the reviewed base level only. Analytic quad
     * diagnostics below deliberately retain their exact nearest references. */
    GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_LINEAR));
    glGenVertexArrays(1,&vao);glGenBuffers(1,&vbo);glGenBuffers(1,&ibo);glGenBuffers(1,&tf);glGenVertexArrays(1,&qvao);glGenBuffers(1,&qvbo);GL_REQUIRE(glcheck(c,"geometry-create"));
    for(unsigned sample=0;sample<6;sample++){
        for(unsigned part=0;part<r->scene.part_count;part++){skin_uniforms(&skin,proj,&r->scene.parts[part],textures);GL_REQUIRE(transform_check(c,&skin,vao,vbo,ibo,tf,g[part].vertices,&g[part].poses,sample,proj,g[part].feedback));c->part_transform_vertices[part]+=r->scene.parts[part].mesh.vertex_count;}
        GL_REQUIRE(skin_render(c,&skin_target,&skin,vao,vbo,ibo,r,g,textures,sample,proj,actual,expected,edges,temporary_edges));
    }
    for(unsigned i=0;i<r->scene.part_count;i++)if(!c->part_interior_pixels[i]||c->part_transform_vertices[i]!=(uint64_t)r->scene.parts[i].mesh.vertex_count*6||c->part_palette_components[i]!=(uint64_t)r->scene.parts[i].mesh.bone_count*12*6){fail(c,"part-coverage","A real costume draw lacks independent palette, GPU transform or visible image coverage");goto cleanup;}
    c->skin_transform_match=1;c->skin_render_match=1;c->character_assembly_match=1;
    GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_NEAREST));
    GL_REQUIRE(material_check(c,&material_target,&material,qvao,qvbo,textures,controlled,r,expected));c->material_pixel_match=1;
    GL_REQUIRE(scene_texture_filter(c,textures,r->scene.texture_count,GL_LINEAR));
    GL_REQUIRE(animated_preview(c,d,surface,&skin_target,&skin,present.id,vao,vbo,ibo,qvao,qvbo,r,g,textures,proj,actual,expected));success=1;c->completed=1;textcopy(c->stage,"complete");
cleanup:
    if(current){glDisable(GL_RASTERIZER_DISCARD);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);target_delete(&skin_target);target_delete(&material_target);for(unsigned i=0;i<r->scene.texture_count;i++)if(textures[i])glDeleteTextures(1,&textures[i]);if(controlled)glDeleteTextures(1,&controlled);if(vao)glDeleteVertexArrays(1,&vao);if(qvao)glDeleteVertexArrays(1,&qvao);if(vbo)glDeleteBuffers(1,&vbo);if(ibo)glDeleteBuffers(1,&ibo);if(tf)glDeleteBuffers(1,&tf);if(qvbo)glDeleteBuffers(1,&qvbo);if(skin.id)glDeleteProgram(skin.id);if(material.id)glDeleteProgram(material.id);if(present.id)glDeleteProgram(present.id);if(!glcheck(c,"gpu-cleanup"))success=0;}
    int released=1;if(current&&!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)){egfail(c,"egl-release-current");released=0;}if(surface!=EGL_NO_SURFACE&&!eglDestroySurface(d,surface)){egfail(c,"egl-destroy-surface");released=0;}if(context!=EGL_NO_CONTEXT&&!eglDestroyContext(d,context)){egfail(c,"egl-destroy-context");released=0;}if(initialized&&!eglTerminate(d)){egfail(c,"egl-terminate");released=0;}if(!eglReleaseThread()){egfail(c,"egl-release-thread");released=0;}c->released=released;c->passed=success&&released;return c->passed;
#undef EGL_REQUIRE
#undef GL_REQUIRE
}
static int allcycles(const Report*r,int k){if(r->attempted!=2)return 0;for(int i=0;i<2;i++){const Cycle*c=&r->cycles[i];if(k==0&&!c->passed)return 0;if(k==1&&!c->animation.sample_match)return 0;if(k==2&&!c->animation.hierarchy_match)return 0;if(k==3&&!c->animation.morph_match)return 0;if(k==4&&!c->animation.palette_match)return 0;if(k==5&&!c->character_assembly_match)return 0;if(k==6&&!c->animation.clock_match)return 0;if(k==7&&!c->animated_preview_passed)return 0;if(k==8&&!c->skin_transform_match)return 0;if(k==9&&!c->skin_render_match)return 0;if(k==10&&!c->material_pixel_match)return 0;if(k==11&&!c->window_pixel_match)return 0;}return 1;}
static void counts_json(Json*j,const char*name,const uint64_t*v,unsigned n){append(j,",");string(j,name);append(j,":[");for(unsigned i=0;i<n;i++){if(i)append(j,",");append(j,"%"PRIu64,v[i]);}append(j,"]");}
static void animation_json(Json*j,const Cycle*c){const AnimationStats*s=&c->animation;
    append(j,",\"actor_sample_match\":%s,\"hierarchy_match\":%s,\"morph_scale_match\":%s,\"socket_palette_match\":%s,\"animation_clock_match\":%s,\"character_assembly_match\":%s,\"animated_preview_passed\":%s,\"animation_samples\":%u,\"hierarchy_nodes_verified\":%u,\"hierarchy_parent_comparisons\":%u,\"local_components\":%"PRIu64",\"local_mismatches\":%"PRIu64",\"local_max_error\":%.9g,\"world_components\":%"PRIu64",\"world_mismatches\":%"PRIu64",\"world_max_error\":%.9g,\"scaled_world_components\":%"PRIu64",\"scaled_world_mismatches\":%"PRIu64",\"scaled_world_max_error\":%.9g,\"btt_components\":%"PRIu64",\"btt_mismatches\":%"PRIu64",\"btt_max_error\":%.9g,\"morph_scale_components\":%"PRIu64",\"morph_scale_mismatches\":%"PRIu64",\"morph_scale_max_error\":%.9g,\"palette_components\":%"PRIu64",\"palette_mismatches\":%"PRIu64",\"palette_max_error\":%.9g,\"part_palettes_sampled\":%u,\"animation_clock_cases\":%u,\"animation_clock_mismatches\":%u,\"base_fallback_samples\":%u,\"preview_frames\":%u,\"preview_clock_steps\":%u,\"preview_clock_wraps\":%u,\"distinct_animated_poses\":%u,\"preview_elapsed_ms\":%"PRIu64",\"preview_first_frame\":%.9g,\"preview_last_frame\":%.9g,\"preview_next_frame\":%.9g,\"preview_image_samples\":%u,\"preview_changed_image_samples\":%u,\"preview_pixels_changed_from_first\":%"PRIu64,
        boolstr(s->sample_match),boolstr(s->hierarchy_match),boolstr(s->morph_match),boolstr(s->palette_match),boolstr(s->clock_match),boolstr(c->character_assembly_match),boolstr(c->animated_preview_passed),s->samples,s->hierarchy_nodes,s->hierarchy_parents,s->local_components,s->local_mismatches,s->local_max_error,s->world_components,s->world_mismatches,s->world_max_error,s->scaled_components,s->scaled_mismatches,s->scaled_max_error,s->btt_components,s->btt_mismatches,s->btt_max_error,s->scale_components,s->scale_mismatches,s->scale_max_error,s->palette_components,s->palette_mismatches,s->palette_max_error,s->palettes_sampled,s->clock_cases,s->clock_mismatches,s->base_fallback_samples,c->preview_frames,c->preview_clock_steps,c->preview_clock_wraps,c->distinct_animated_poses,c->preview_elapsed_ms,c->preview_first_frame,c->preview_last_frame,c->preview_next_frame,c->preview_image_samples,c->preview_changed_image_samples,c->preview_pixels_changed_from_first);
}
static void byte_array_json(Json*j,const uint8_t*v,unsigned n){append(j,"[");for(unsigned i=0;i<n;i++){if(i)append(j,",");append(j,"%u",(unsigned)v[i]);}append(j,"]");}
static void image_diagnostics_json(Json*j,const Cycle*c){
    append(j,",\"image_mismatch_diagnostics\":[");
    for(unsigned i=0;i<c->image_diagnostic_count;i++){const ImageDiagnostic*d=&c->image_diagnostics[i];if(i)append(j,",");append(j,"{\"part\":%u,\"checkpoint\":%u,\"pixel_xy\":[%u,%u],\"expected_rgba\":",d->part,d->sample,d->x,d->y);byte_array_json(j,d->expected,4);append(j,",\"actual_rgba\":");byte_array_json(j,d->actual,4);append(j,",\"expected_neighborhood_rgba\":");byte_array_json(j,d->expected_neighborhood,36);append(j,",\"actual_neighborhood_rgba\":");byte_array_json(j,d->actual_neighborhood,36);append(j,",\"nearest_covering_triangle_cpu_reconstructions\":[");
        for(unsigned k=0;k<d->candidates;k++){const TriangleDiagnostic*t=&d->triangles[k];if(k)append(j,",");append(j,"{\"triangle\":%u,\"expected_inside\":%s,\"actual_inside\":%s,\"expected_uv\":[%.17g,%.17g],\"actual_uv\":[%.17g,%.17g],\"expected_depth\":%.17g,\"actual_depth\":%.17g,\"expected_depth24_estimate\":%u,\"actual_depth24_estimate\":%u,\"expected_base_texel_xy\":[%u,%u],\"actual_base_texel_xy\":[%u,%u],\"expected_dual_texel_xy\":[%u,%u],\"actual_dual_texel_xy\":[%u,%u],\"expected_base_texel_rgba\":",
            t->triangle,boolstr(t->expected_inside),boolstr(t->actual_inside),t->expected_uv[0],t->expected_uv[1],t->actual_uv[0],t->actual_uv[1],t->expected_depth,t->actual_depth,t->expected_depth24,t->actual_depth24,t->expected_base_xy[0],t->expected_base_xy[1],t->actual_base_xy[0],t->actual_base_xy[1],t->expected_dual_xy[0],t->expected_dual_xy[1],t->actual_dual_xy[0],t->actual_dual_xy[1]);byte_array_json(j,t->expected_base,4);append(j,",\"actual_base_texel_rgba\":");byte_array_json(j,t->actual_base,4);append(j,",\"expected_dual_texel_rgba\":");byte_array_json(j,t->expected_dual,4);append(j,",\"actual_dual_texel_rgba\":");byte_array_json(j,t->actual_dual,4);append(j,"}");}
        append(j,"]}");
    }
    append(j,"],\"image_diagnostic_scope\":\"up to eight failed non-edge pixels, 3x3 neighborhoods bottom-left origin, and four nearest triangles reconstructed in double precision from independent reference and actual transform-feedback positions; UV and depth estimates are not GPU interpolator captures and never alter acceptance\"");
}
static jstring report_json(JNIEnv*env,const Report*r){
    char*buffer=malloc(JSON_CAP);if(!buffer)return (*env)->NewStringUTF(env,"{\"passed\":false,\"failure\":\"Report allocation failed\"}");Json j={buffer,0,1};
    append(&j,"{\"schema\":1,\"probe\":\"coh-native-authored-character-gles3\",\"platform\":\"Android Bionic\",\"passed\":%s,\"mesh_valid\":%s,\"rig_valid\":%s,\"morph_valid\":%s,\"character_valid\":%s,\"actor_sample_match\":%s,\"hierarchy_match\":%s,\"morph_scale_match\":%s,\"socket_palette_match\":%s,\"character_assembly_match\":%s,\"animation_clock_match\":%s,\"animated_preview_passed\":%s,\"skin_transform_match\":%s,\"skin_render_match\":%s,\"material_pixel_match\":%s,\"alpha_fog_passed\":%s,\"offscreen_passed\":%s,\"context_recreation_passed\":%s,\"window_pixel_match\":%s,\"pointer_bytes\":%zu,\"long_bytes\":%zu,\"required_cycles\":2,\"attempted_cycles\":%d,\"surface_width\":%d,\"surface_height\":%d,",
        boolstr(r->passed),boolstr(r->character_valid),boolstr(r->rig_valid),boolstr(r->morph_valid),boolstr(r->character_valid),boolstr(allcycles(r,1)),boolstr(allcycles(r,2)),boolstr(allcycles(r,3)),boolstr(allcycles(r,4)),boolstr(allcycles(r,5)),boolstr(allcycles(r,6)),boolstr(allcycles(r,7)),boolstr(allcycles(r,8)),boolstr(allcycles(r,9)),boolstr(allcycles(r,10)),boolstr(allcycles(r,10)),boolstr(allcycles(r,9)&&allcycles(r,10)),boolstr(allcycles(r,0)),boolstr(allcycles(r,11)),sizeof(void*),sizeof(long),r->attempted,r->attempted?r->cycles[r->attempted-1].width:0,r->attempted?r->cycles[r->attempted-1].height:0);
    append(&j,"\"character_part_count\":%u,\"costume_category_count\":10,\"mesh_vertices\":%u,\"mesh_indices\":%u,\"blended_vertices\":%u,\"palette_matrix_count\":45,\"unique_textures\":%u,\"pose_count\":6,\"hierarchy_bones\":60,\"base_tracks\":60,\"motion_tracks\":44,\"first_frame\":1,\"last_frame\":25,\"ticks_per_second\":30,\"effective_rate\":1,\"skin_fbo_width\":512,\"skin_fbo_height\":512,\"material_case_count\":%u,\"transform_absolute_tolerance\":0.0001,\"rgba_byte_tolerance\":2,\"triangle_edge_exclusion_pixels\":2,\"window_alpha_compared\":false,\"original_cg_execution\":false,\"reference_palettes_drive_rendering\":false,\"runtime_palette_origin\":\"native original raw keys plus actual Wretch morphology, hierarchy, inverse bind and source sockets\",\"normal_policy\":\"source transformed normals normalized after blend; inverse square root with one Newton refinement\",\"stock_normal_diagnostic_only\":true,\"material_profile\":\"source automatic COLORBLEND_DUAL fallback; MULTITEX and BUMPMAPS disabled\",\"high_quality_materials_qualified\":false,\"missing_right_glove_policy\":\"source accepts absent LarmR geometry as None; no mirroring\",\"front_face\":\"CW\",\"cull_face\":\"BACK except source Hair and Neck DoubleSided\",\"draw_order\":\"authored diagnostic order; world transparency sorting unqualified\",\"hair_alpha_blend\":\"SRC_ALPHA, ONE_MINUS_SRC_ALPHA\",\"depth_write\":true,\"projection\":\"fits all 45 runtime frames plus fractional checkpoints with 20 percent margin\",\"failure\":",
        r->scene.part_count,r->scene.vertices,r->scene.indices,r->scene.blended_vertices,r->scene.texture_count,r->materials.count);string(&j,r->failure);
    append(&j,",\"standalone_projection_scope\":\"per-part-six-checkpoint-union\",\"standalone_projection_method\":\"orthographic fit of each part's six independent geometry checkpoints with 20 percent margin; GPU and CPU geometry share this camera\",\"standalone_minimum_interior_pixels_per_part_pose\":64,\"assembled_projection_independent_of_standalone\":true,\"character_texture_filter\":\"GL_LINEAR\",\"material_probe_texture_filter\":\"GL_NEAREST\",\"window_image_filter\":\"GL_NEAREST\",\"mip_policy\":\"base level only; original mip chain unqualified\",\"texture_filter_source_scope\":\"original rt_tex.c default without POINTSAMPLE overrides; analytic quad and exact window transfer use separate nearest sampling\",\"cycles\":[");
    for(int i=0;i<r->attempted;i++){const Cycle*c=&r->cycles[i];if(i)append(&j,",");
        append(&j,"{\"index\":%d,\"completed\":%s,\"passed\":%s,\"context_created\":%s,\"objects_released\":%s,\"swap_passed\":%s,\"skin_transform_match\":%s,\"skin_render_match\":%s,\"material_pixel_match\":%s,\"window_pixel_match\":%s,\"surface_width\":%d,\"surface_height\":%d,\"viewport\":[%d,%d,%d,%d],\"transform_vertices\":%"PRIu64",\"transform_components\":%"PRIu64",\"transform_mismatches\":%"PRIu64",\"max_transform_error\":%.9g,\"position_mismatches\":%"PRIu64",\"normal_mismatches\":%"PRIu64",\"max_position_error\":%.9g,\"max_normal_error\":%.9g,\"max_normal_length_error\":%.9g,\"stock_normal_components\":%"PRIu64",\"stock_normal_mismatches\":%"PRIu64",\"stock_normal_max_error\":%.9g,\"stock_normal_max_length_error\":%.9g,",
            i,boolstr(c->completed),boolstr(c->passed),boolstr(c->context_created),boolstr(c->released),boolstr(c->swap_passed),boolstr(c->skin_transform_match),boolstr(c->skin_render_match),boolstr(c->material_pixel_match),boolstr(c->window_pixel_match),c->width,c->height,c->viewport_x,c->viewport_y,c->viewport_w,c->viewport_h,c->transform_vertices,c->transform_components,c->transform_mismatches,c->max_transform_error,c->position_mismatches,c->normal_mismatches,c->max_position_error,c->max_normal_error,c->max_normal_length_error,c->stock_normal_components,c->stock_normal_mismatches,c->stock_normal_max_error,c->stock_normal_max_length_error);
        append(&j,"\"first_transform_mismatch\":{\"observed\":%s,\"pose\":%u,\"vertex\":%u,\"component\":%u,\"expected\":%.9g,\"actual\":%.9g,\"actual_finite\":%s},\"skin_poses\":%u,\"skin_compared_pixels\":%"PRIu64",\"skin_interior_pixels\":%"PRIu64",\"skin_edge_excluded_pixels\":%"PRIu64",\"skin_mismatches\":%"PRIu64",\"skin_max_byte_error\":%u,\"material_cases\":%u,\"real_material_cases\":%u,\"synthetic_semantic_cases\":%u,\"material_pixels\":%"PRIu64",\"material_mismatches\":%"PRIu64",\"material_max_byte_error\":%u,\"material_blended_cases\":%u,\"material_discard_clear_pixels\":%"PRIu64",\"window_samples\":%u,\"window_mismatches\":%u,\"gl_errors\":%u,\"first_gl_error\":%u,\"egl_error\":%u,\"stage\":",
            boolstr(c->transform_mismatches!=0),c->first_transform_pose,c->first_transform_vertex,c->first_transform_component,c->first_transform_expected,c->first_transform_actual,boolstr(c->first_transform_actual_finite),c->skin_poses,c->skin_compared_pixels,c->skin_interior_pixels,c->skin_edge_excluded_pixels,c->skin_mismatches,c->skin_max_byte_error,c->material_cases,c->real_material_cases,c->synthetic_semantic_cases,c->material_pixels,c->material_mismatches,c->material_max_byte_error,c->blend_cases,c->material_discard_clear_pixels,c->window_samples,c->window_mismatches,c->gl_errors,c->first_gl_error,c->egl_error);string(&j,c->stage);
        counts_json(&j,"skin_pose_interior_pixels",c->skin_pose_interiors,6);counts_json(&j,"skin_pose_edge_excluded_pixels",c->skin_pose_excluded,6);counts_json(&j,"skin_pose_compared_pixels",c->skin_pose_compared,6);counts_json(&j,"part_interior_pixels",c->part_interior_pixels,11);counts_json(&j,"part_transform_vertices",c->part_transform_vertices,11);counts_json(&j,"part_palette_components",c->part_palette_components,11);counts_json(&j,"part_image_compared_pixels",c->part_image_compared_pixels,11);counts_json(&j,"part_image_mismatches",c->part_image_mismatches,11);append(&j,",\"standalone_compared_pixels\":%"PRIu64",\"standalone_mismatches\":%"PRIu64",\"standalone_max_byte_error\":%u",c->standalone_compared_pixels,c->standalone_mismatches,c->standalone_max_byte_error);animation_json(&j,c);image_diagnostics_json(&j,c);
        append(&j,",\"failure\":");string(&j,c->failure);append(&j,",\"gl_vendor\":");string(&j,c->gl_vendor);append(&j,",\"gl_renderer\":");string(&j,c->gl_renderer);append(&j,",\"gl_version\":");string(&j,c->gl_version);append(&j,",\"glsl_version\":");string(&j,c->glsl_version);append(&j,",\"egl_vendor\":");string(&j,c->egl_vendor);append(&j,",\"egl_version\":");string(&j,c->egl_version);append(&j,"}");
    }
    append(&j,"]}");jstring result=(*env)->NewStringUTF(env,j.ok?buffer:"{\"passed\":false,\"failure\":\"Report capacity exceeded\"}");free(buffer);return result;
}
JNIEXPORT jstring JNICALL Java_org_coh_characterprobe_ProbeNative_probe(JNIEnv*env,jclass clazz,jobject java_surface,jbyteArray java_scene,jbyteArray java_rig,jbyteArray java_morph,jbyteArray java_reference,jbyteArray java_materials){
    (void)clazz;Report report={0};Bytes b[5]={{0}};ANativeWindow*window=NULL;Geometry geometry[COH_SCENE_PARTS]={{0}};uint8_t*actual=NULL,*expected=NULL,*edges=NULL,*temporary_edges=NULL;
    jbyteArray inputs[5]={java_scene,java_rig,java_morph,java_reference,java_materials};size_t total=0;
    if(!java_surface){textcopy(report.failure,"A live Android Surface is required");goto cleanup;}
    for(unsigned i=0;i<5;i++){if(!inputs[i]){textcopy(report.failure,"All five fixture byte arrays are required");goto cleanup;}jsize n=(*env)->GetArrayLength(env,inputs[i]);if(n<=0||(size_t)n>MAX_ASSET){textcopy(report.failure,"Input exceeds 16 MiB per asset");goto cleanup;}total+=(size_t)n;if(total>32u*1024u*1024u){textcopy(report.failure,"Fixture inputs exceed 32 MiB total");goto cleanup;}}
    for(unsigned i=0;i<5;i++)if(!copy_java(env,inputs[i],&b[i])){textcopy(report.failure,"JNI immutable fixture copy failed");goto cleanup;}
    if(coh_scene_parse(b[0].p,b[0].n,&report.scene)){textcopy(report.failure,"Real authored costume scene validation failed");goto cleanup;}report.character_valid=1;
    report.rig=calloc(1,sizeof(*report.rig));report.morph=calloc(1,sizeof(*report.morph));if(!report.rig||!report.morph){textcopy(report.failure,"Bounded actor allocation failed");goto cleanup;}
    if(coh_animation_parse(b[1].p,b[1].n,report.rig)||report.rig->node_count!=60||report.rig->base.track_count!=60||report.rig->motion.track_count!=44||report.rig->socket_id!=72||report.rig->first_frame!=1||report.rig->last_frame!=25||report.rig->ticks_per_second!=30){textcopy(report.failure,"Original Huge base/run rig and source clock validation failed");goto cleanup;}report.rig_valid=1;
    if(coh_character_parse_morph(b[2].p,b[2].n,report.morph)){textcopy(report.failure,"Actual source Wretch morph validation failed");goto cleanup;}report.morph_valid=1;
    if(!character_reference_parse(b[3],&report.scene,report.rig,&report.reference)||!material_parse(b[4],&report.scene,&report.materials)){textcopy(report.failure,"Independent actor or per-part material reference validation failed");goto cleanup;}
    for(unsigned p=0;p<report.scene.part_count;p++){const CohMeshView*m=&report.scene.parts[p].mesh;Geometry*g=&geometry[p];uint32_t stride=m->bone_count*48+m->vertex_count*24;g->storage=malloc((size_t)6*stride);g->poses=(Poses){6,m->bone_count,m->vertex_count,stride,g->storage};g->vertices=calloc(m->vertex_count,sizeof(Vertex));g->reference=calloc(m->vertex_count,sizeof(Vertex));g->feedback=calloc((size_t)m->vertex_count*TF_FLOATS,sizeof(float));g->indices=malloc((size_t)m->index_count*4);
        if(!g->storage||!g->vertices||!g->reference||!g->feedback||!g->indices){textcopy(report.failure,"Bounded per-part mesh/reference allocation failed");goto cleanup;}
        for(unsigned i=0;i<m->bone_count;i++)if(coh_mesh_global_bone(m,i,&g->ids[i])){textcopy(report.failure,"Canonical palette identity lookup failed");goto cleanup;}
        for(uint32_t i=0;i<m->vertex_count;i++){CohMeshVertex v;if(coh_mesh_vertex(m,i,&v)){textcopy(report.failure,"Canonical real vertex lookup failed");goto cleanup;}memcpy(g->vertices[i].position,v.position,sizeof v.position);memcpy(g->vertices[i].normal,v.normal,sizeof v.normal);memcpy(g->vertices[i].uv0,v.uv,sizeof v.uv);memcpy(g->vertices[i].uv1,v.uv,sizeof v.uv);memcpy(g->vertices[i].weights,v.weights,sizeof v.weights);g->vertices[i].rows[0]=(int32_t)v.bones[0]*3;g->vertices[i].rows[1]=(int32_t)v.bones[1]*3;}
        for(uint32_t i=0;i<m->index_count;i++)if(coh_mesh_index(m,i,&g->indices[i])){textcopy(report.failure,"Canonical triangle index lookup failed");goto cleanup;}
    }
    actual=malloc(SKIN_SIZE*SKIN_SIZE*4);expected=malloc(SKIN_SIZE*SKIN_SIZE*4);edges=malloc(SKIN_SIZE*SKIN_SIZE);temporary_edges=malloc(SKIN_SIZE*SKIN_SIZE);if(!actual||!expected||!edges||!temporary_edges){textcopy(report.failure,"Bounded image/triangle edge allocation failed");goto cleanup;}
    window=ANativeWindow_fromSurface(env,java_surface);if((*env)->ExceptionCheck(env))(*env)->ExceptionClear(env);if(!window){textcopy(report.failure,"Android Surface is unavailable");goto cleanup;}
    report.passed=1;for(int i=0;i<2;i++){report.attempted++;if(!cycle_run(window,&report,geometry,actual,expected,edges,temporary_edges,&report.cycles[i])){report.passed=0;textcopy(report.failure,report.cycles[i].failure);break;}}
cleanup:
    if(window)ANativeWindow_release(window);for(unsigned i=0;i<COH_SCENE_PARTS;i++){free(geometry[i].vertices);free(geometry[i].reference);free(geometry[i].feedback);free(geometry[i].indices);free(geometry[i].storage);}free(actual);free(expected);free(edges);free(temporary_edges);
    jstring result=report_json(env,&report);for(unsigned i=0;i<5;i++)free(b[i].p);free(report.rig);free(report.morph);return result;
}
