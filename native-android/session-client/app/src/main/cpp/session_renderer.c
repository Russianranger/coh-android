/* Persistent, offline source-character session. This owns one EGL context at
 * a time. Accepted CPU character skinning feeds the accepted precise world
 * shader; this does not claim GPU palette skinning or a full game renderer. */
#define _POSIX_C_SOURCE 200809L
#include <jni.h>
#include <android/native_window.h>
#include <android/native_window_jni.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <pthread.h>
#include <stddef.h>
#include <stdarg.h>
#include <math.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "coh_world_scene.h"
#include "coh_scene.h"
#include "coh_character.h"
#include "coh_motion.h"
#include "coh_locomotion.h"
#include "coh_walk.h"
#include "coh_walkable_scene.h"
#include "world_shader_sources.h"
#include "session_stream_world.h"
#include "session_frame_capture.h"
#include "session_frame_capture_gl.h"
#ifndef COH_LIVE_COSTUME_DIAGNOSTIC
#define COH_LIVE_COSTUME_DIAGNOSTIC 0
#endif
#if COH_LIVE_COSTUME_DIAGNOSTIC
#include "../../../../../engine/appearance/coh_received_costume.h"
#include "../../../../../engine/appearance/coh_received_costume_fd.h"
#include "coh_renderer_gles.h"
#endif

#ifndef COH_FRAME_CAPTURE_DIAGNOSTIC
#define COH_FRAME_CAPTURE_DIAGNOSTIC 0
#endif
#define MAX_ASSET (16u*1024u*1024u)
#define SIZE 512
#define PI 3.14159265358979323846f
#define JSON_CAP 16384
#define INPUT_EDGES 32u
#define DEPTH_DIAGNOSTICS 16u
typedef struct { uint8_t *p; size_t n; } Bytes;
typedef struct { float position[3],normal[3],uv0[2],uv1[2]; } Vertex;
typedef struct {unsigned x,y,world_depth,actor_depth,combined_depth;uint8_t world[4],actor[4],forward[4],reverse[4];} DepthDiagnostic;
typedef struct {
    Vertex *vertices; CohMeshVertex *source; uint32_t *indices;
    uint32_t ids[COH_ANIMATION_PALETTE],count,index_count,bones;
    GLuint vao,vbo,ibo;
} Geometry;
typedef struct {
    pthread_mutex_t mutex; Bytes assets[7]; int valid,failed,cancel,running;
    uint64_t epoch; int foreground;
    CohWorldScene world; CohScene actor; CohAnimationRig rig;
    CohCharacterMorph morph; CohLocomotion locomotion; CohLocomotionState animation;
    CohLocomotionBlend blend; CohWalkableScene walkable; CohWalkWorld walk_world; CohWalkState walking;
    CohSessionWorld *stream_world; CohSessionWorldStats stream_stats; float view_radius;
    int runtime_world_status; uint64_t runtime_world_parent_bytes,runtime_world_reads,runtime_world_bytes; char runtime_world_failure[128];
    float render_dt_frames,benchmark_spawn[3],benchmark_yaw,obstacle_min[3],obstacle_max[3];
    uint64_t walkable_tf_components,walkable_tf_mismatches,walkable_visible_pixels;
    Geometry walkable_geometry[COH_WALKABLE_PARTS];
    uint32_t input_edges[INPUT_EDGES],input_edge_head,input_edge_count;
    uint64_t animation_move_samples[COH_LOCOMOTION_CLIPS],walking_ticks,walking_grounded_ticks,walking_blocked_ticks,walking_slide_ticks,walking_bounded_ticks,walkable_draws;
    CohMotionState motion; Geometry world_geometry[COH_WORLD_PARTS],actor_geometry[COH_SCENE_PARTS];
    float world_local[6][12],world_matrix[6][12];
    float camera_yaw,camera_pitch,camera_position[3],look_rate[2],look_delta[2];
    float forward,strafe,accumulator,spawn[3],camera_target_height;
    uint32_t observed_entity_index;float observed_entity_position[3];
    uint64_t observed_entity_updates,observed_entity_draws;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    CohReceivedCostume *received_actor;CohReceivedCostumeStats received_stats;
    uint64_t received_pose_updates,received_source_bytes,received_invalidations;
    uint64_t received_frames,received_draws;int received_preparing,received_status,received_last_draw;
#endif
    CohFrameCapture *frame_capture;
    uint64_t capture_lock_frame,capture_draws,capture_frame,capture_generation,capture_failures,capture_charge,capture_view_epoch;
    uint32_t capture_view_width,capture_view_height;
    uint32_t held_dirs,direction_mask;
    uint64_t frames,world_draws,actor_draws,skin_samples,contexts_started,contexts_completed;
    uint64_t tf_components,tf_mismatches,depth_order_mismatches,world_visible_pixels,actor_visible_pixels;
    uint64_t depth_order_color_differences,depth_order_ties;unsigned depth_diagnostics_count;DepthDiagnostic depth_diagnostics[DEPTH_DIAGNOSTICS];
    int depth_sampler_controls_passed;unsigned world_control_count,actor_control_count;
    int depth_codec_float_precision;
    DepthDiagnostic clear_control,world_controls[DEPTH_DIAGNOSTICS],actor_controls[DEPTH_DIAGNOSTICS],world_front_control,actor_front_control;
    uint64_t world_occludes_actor_pixels,actor_occludes_world_pixels,actor_changed_pixels;
    uint64_t idle_samples,run_samples,total_ms; unsigned gl_errors,egl_error,shader_version;
    unsigned expected_cancel_surface_errors,expected_cancel_egl_error;int surface_failure;
    unsigned cleanup_gl_errors,cleanup_egl_errors,cleanup_egl_error;
    float tf_max_error; int startup_checked,precise,objects_released,width,height;
    char failure[512],gl_vendor[256],gl_renderer[256];
} Session;
typedef struct { GLuint id; GLint model,modelview,projection,mode,light,diffuse,ambient;
    GLint base,dual,const0,const1,fog_params,fog_color,alpha_ref; } Program;
typedef struct { EGLDisplay display; EGLSurface surface; EGLContext context;
    ANativeWindow *window; Program program; GLuint world_textures[COH_WORLD_TEXTURES];
    GLuint walkable_textures[COH_WALKABLE_TEXTURES];
    GLuint actor_textures[COH_SCENE_TEXTURES],tf,fbo,color,depth;
    GLuint depth_program,depth_vao,pixel_fbo,pixel_color;GLint depth_sampler,depth_pixel;
    size_t tf_bytes;
    int initialized,context_current;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    CohGlesRenderer *received_gles;CohRenderer *received_renderer;
    GLuint received_textures[COH_RECEIVED_COSTUME_TEXTURES];int received_attempted;
#endif
} Graphics;
static uint64_t now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u; }
static float bounded(float x,float low,float high) { return x<low?low:(x>high?high:x); }
static float wrap(float x) { while(x>PI)x-=2*PI; while(x<=-PI)x+=2*PI; return x; }
static int fail(Session *s,const char *why) { if(!s->failed&&why!=s->failure)snprintf(s->failure,sizeof s->failure,"%s",why);s->failed=1;return 0; }
static int glcheck(Session *s,const char *where) { GLenum e;unsigned errors=0;
    for(unsigned i=0;i<32&&(e=glGetError())!=GL_NO_ERROR;i++)errors++;
    if(!errors)return 1;s->gl_errors+=errors;return fail(s,where); }
/* Original mulMat4 operation order, source columns of three floats. */
static void multiply(const float *a,const float *b,float *c) {
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)c[i*3+j]=b[i*3]*a[j]+b[i*3+1]*a[3+j]+b[i*3+2]*a[6+j];
    for(unsigned j=0;j<3;j++)c[9+j]=b[9]*a[j]+b[10]*a[3+j]+b[11]*a[6+j]+a[9+j];
}
static void actor_matrix(const Session *s,float *m) { float c=cosf(s->motion.body_yaw),q=sinf(s->motion.body_yaw);
    const float a[12]={c,0,-q,0,1,0,q,0,c,s->motion.position[0],s->motion.position[1],s->motion.position[2]};memcpy(m,a,sizeof a); }
static const float* scene_center(const Session*s){return s->observed_entity_index?s->observed_entity_position:s->motion.position;}
static int camera(Session *s,float aspect,float *view,float *projection,float *actor,float *actor_eye,float eye[6][12]) {
    CohWorldInputs inputs=s->world.inputs;CohWorldCamera *c=&inputs.cameras[0];
    c->pyr_degrees[0]=s->camera_pitch*180/PI;c->pyr_degrees[1]=s->camera_yaw*180/PI;c->pyr_degrees[2]=0;
    float cp=cosf(s->camera_pitch); const float distance=22;const float*center=scene_center(s);
    c->position[0]=center[0]+distance*sinf(s->camera_yaw)*cp;
    c->position[1]=center[1]+s->camera_target_height+distance*sinf(s->camera_pitch);
    c->position[2]=center[2]+distance*cosf(s->camera_yaw)*cp;
    c->fovy=60;c->znear=.1f;c->zfar=500;c->flip_x=0;c->flip_y=0;
    memcpy(s->camera_position,c->position,sizeof s->camera_position);
    if(coh_world_camera(&inputs,0,aspect,view,projection)||coh_world_group_eye_matrices(&inputs,view,eye))return fail(s,"Source session camera failed");
    actor_matrix(s,actor);multiply(view,actor,actor_eye);return 1;
}
static int geometry_create(Geometry *g,const CohMeshView *m) {
    g->count=m->vertex_count;g->index_count=m->index_count;g->bones=m->bone_count;
    g->vertices=calloc(g->count,sizeof(Vertex));g->source=calloc(g->count,sizeof(CohMeshVertex));g->indices=calloc(g->index_count,4);
    if(!g->vertices||!g->source||!g->indices)return 0;
    for(unsigned i=0;i<g->bones;i++)if(coh_mesh_global_bone(m,i,&g->ids[i]))return 0;
    for(unsigned i=0;i<g->count;i++) {
        if(coh_mesh_vertex(m,i,&g->source[i]))return 0;Vertex *v=&g->vertices[i];CohMeshVertex *a=&g->source[i];
        memcpy(v->position,a->position,12);memcpy(v->normal,a->normal,12);memcpy(v->uv0,a->uv,8);memcpy(v->uv1,a->uv,8);
    }
    for(unsigned i=0;i<g->index_count;i++)if(coh_mesh_index(m,i,&g->indices[i]))return 0;
    return 1;
}
static void geometry_free(Geometry *g) {free(g->vertices);free(g->source);free(g->indices);}
static int skin(Session *s) {
    const CohAnimationRig *rig=coh_locomotion_rig(&s->locomotion,&s->animation);CohAnimationPose pose;
    if(!rig||coh_locomotion_sample_directional(&s->locomotion,&s->animation,&s->morph,s->render_dt_frames,&s->blend,&pose))return fail(s,"Authored locomotion pose sampling failed");
    for(unsigned i=0;i<s->actor.part_count;i++) {
        Geometry *g=&s->actor_geometry[i];float rows[COH_ANIMATION_PALETTE*12];
        if(coh_character_palette(rig,&s->morph,&pose,s->actor.parts[i].socket,g->ids,g->bones,rows))return fail(s,"Source actor socket palette failed");
        for(unsigned j=0;j<g->count;j++) {CohSkinnedVertex skinned;
            if(coh_mesh_skin_vertex(&g->source[j],rows,g->bones,&skinned))return fail(s,"Source actor CPU skinning failed");
            memcpy(g->vertices[j].position,skinned.position,12);memcpy(g->vertices[j].normal,skinned.normal,12);
        }
    }
    s->skin_samples++;return 1;
}
static int copy_asset(JNIEnv *e,jbyteArray a,Bytes *out) {
    if(!a)return 0;jsize n=(*e)->GetArrayLength(e,a);if(n<=0||(size_t)n>MAX_ASSET)return 0;
    out->p=malloc((size_t)n);out->n=(size_t)n;if(!out->p)return 0;
    (*e)->GetByteArrayRegion(e,a,0,n,(jbyte*)out->p);return !(*e)->ExceptionCheck(e);
}
static void session_free(Session *s) {if(!s)return;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    coh_received_costume_destroy(&s->received_actor);
#endif
    coh_frame_capture_destroy(&s->frame_capture);coh_session_world_destroy(&s->stream_world);for(unsigned i=0;i<7;i++)free(s->assets[i].p);
    coh_walk_world_destroy(&s->walk_world);for(unsigned i=0;i<COH_WALKABLE_PARTS;i++)geometry_free(&s->walkable_geometry[i]);
    for(unsigned i=0;i<COH_WORLD_PARTS;i++)geometry_free(&s->world_geometry[i]);
    for(unsigned i=0;i<COH_SCENE_PARTS;i++)geometry_free(&s->actor_geometry[i]);pthread_mutex_destroy(&s->mutex);free(s); }

JNIEXPORT jlong JNICALL Java_org_coh_sessionclient_SessionNative_createSession(JNIEnv *e,jclass klass,jbyteArray world,jbyteArray actor,jbyteArray rig,jbyteArray morph,jbyteArray locomotion,jbyteArray walkable,jbyteArray map) {
    (void)klass;Session *s=calloc(1,sizeof *s);if(!s)return 0;pthread_mutex_init(&s->mutex,NULL);
    jbyteArray arrays[7]={world,actor,rig,morph,locomotion,walkable,map};size_t total=0;
    for(unsigned i=0;i<7;i++){if(!copy_asset(e,arrays[i],&s->assets[i]))goto error;total+=s->assets[i].n;}
    if(total>32u*1024u*1024u||coh_world_scene_parse(s->assets[0].p,s->assets[0].n,&s->world)||coh_scene_parse(s->assets[1].p,s->assets[1].n,&s->actor)||
        coh_animation_parse(s->assets[2].p,s->assets[2].n,&s->rig)||coh_character_parse_morph(s->assets[3].p,s->assets[3].n,&s->morph)||
        coh_locomotion_parse(s->assets[4].p,s->assets[4].n,&s->locomotion)||
        coh_walkable_scene_parse(s->assets[5].p,s->assets[5].n,&s->walkable))goto error;
    if(s->world.part_count!=2||s->actor.part_count!=11||coh_world_group_matrices(&s->world.inputs,s->world_local,s->world_matrix))goto error;
    for(unsigned i=0;i<s->world.part_count;i++)if(!geometry_create(&s->world_geometry[i],&s->world.parts[i].mesh))goto error;
    for(unsigned i=0;i<s->actor.part_count;i++)if(!geometry_create(&s->actor_geometry[i],&s->actor.parts[i].mesh))goto error;
    for(unsigned i=0;i<s->walkable.part_count;i++) {
        if(!geometry_create(&s->walkable_geometry[i],&s->walkable.parts[i].material.mesh))goto error;
        for(unsigned j=0;j<s->walkable_geometry[i].count;j++)for(unsigned k=0;k<2;k++) {
            s->walkable_geometry[i].vertices[j].uv0[k]*=s->walkable.parts[i].uv_scale0[k];
            s->walkable_geometry[i].vertices[j].uv1[k]*=s->walkable.parts[i].uv_scale1[k];
        }
    }
    if(!coh_walk_world_init(&s->walk_world,s->walkable.triangles,s->walkable.triangle_count,s->walkable.bounds_min,s->walkable.bounds_max))goto error;
    for(unsigned k=0;k<3;k++){s->obstacle_min[k]=1e9f;s->obstacle_max[k]=-1e9f;}
    unsigned obstacle_vertices=0;
    for(unsigned i=0;i<s->walkable.triangle_count;i++) {
        const CohWalkTriangle *t=&s->walkable.triangles[i];int elevated=0;
        for(unsigned j=0;j<3;j++)if(t->v[j][1]>s->walkable.spawn[1]+.1f)elevated=1;
        if(elevated) {
            for(unsigned j=0;j<3;j++) {
                for(unsigned k=0;k<3;k++) {
                    if(t->v[j][k]<s->obstacle_min[k])s->obstacle_min[k]=t->v[j][k];
                    if(t->v[j][k]>s->obstacle_max[k])s->obstacle_max[k]=t->v[j][k];
                }
            }
            obstacle_vertices+=3;
        }
    }
    if(!obstacle_vertices)goto error;
    /* Explicit authored-scene profile: source bench AABB foot plane; Wretch is
     * behind its middle relative to source camera-zero yaw, not recentered on
     * each run. This is initial placement, not a source NPC spawn claim. */
    float low[3]={1e9f,1e9f,1e9f},high[3]={-1e9f,-1e9f,-1e9f};
    const float identity[12]={1,0,0,0,1,0,0,0,1,0,0,0};const float projection[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    for(unsigned i=0;i<s->world.part_count;i++)for(unsigned j=0;j<s->world_geometry[i].count;j++) {
        float transformed[13];Vertex *v=&s->world_geometry[i].vertices[j];
        if(coh_world_vertex(s->world_matrix[s->world.parts[i].node],identity,projection,v->position,v->normal,transformed))goto error;
        for(unsigned k=0;k<3;k++){if(transformed[k]<low[k])low[k]=transformed[k];if(transformed[k]>high[k])high[k]=transformed[k];}
    }
    s->camera_yaw=s->world.inputs.cameras[0].pyr_degrees[1]*PI/180;s->camera_pitch=.16f;s->camera_target_height=3.8f;
    s->spawn[0]=(low[0]+high[0])*.5f-1.0f*sinf(s->camera_yaw);s->spawn[1]=low[1];s->spawn[2]=(low[2]+high[2])*.5f-1.0f*cosf(s->camera_yaw);
    memcpy(s->benchmark_spawn,s->spawn,sizeof s->spawn);s->benchmark_yaw=s->camera_yaw;
    memcpy(s->spawn,s->walkable.spawn,sizeof s->spawn);s->camera_yaw=wrap(s->walkable.spawn_yaw+PI);
    if(!coh_walk_init(&s->walking,&s->walk_world,s->spawn,s->walkable.spawn_yaw))goto error;
    s->motion=s->walking.controls;memcpy(s->motion.position,s->walking.position,sizeof s->motion.position);
    coh_locomotion_init(&s->animation);coh_locomotion_blend_init(&s->blend);
    s->view_radius=24;
    if(!coh_session_world_create(s->assets[6].p,s->assets[6].n,&s->stream_world,s->failure,sizeof s->failure))goto error;
    s->valid=1;return (jlong)(intptr_t)s;
error:session_free(s);return 0;
}

static GLuint compile(Session *s,GLenum kind,const char *source) {GLuint shader=glCreateShader(kind);glShaderSource(shader,1,&source,NULL);glCompileShader(shader);GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if(!ok){char log[512]={0};glGetShaderInfoLog(shader,sizeof log,NULL,log);fail(s,log[0]?log:"Source world shader compilation failed");glDeleteShader(shader);return 0;}return shader; }
static int extension(const char *name) {GLint count=0;glGetIntegerv(GL_NUM_EXTENSIONS,&count);if(count<0||count>8192)return 0;
    for(GLint i=0;i<count;i++){const char *v=(const char*)glGetStringi(GL_EXTENSIONS,(GLuint)i);if(v&&!strcmp(v,name))return 1;}return 0;}
static int program_create(Session *s,Program *p) {GLint major=0,minor=0;glGetIntegerv(GL_MAJOR_VERSION,&major);glGetIntegerv(GL_MINOR_VERSION,&minor);
    const char *v=kWorldVertex,*f=kWorldFragment;s->shader_version=300;s->precise=0;
    if(major>3||(major==3&&minor>=2)){v=kWorldVertexCore320;f=kWorldFragmentCore320;s->shader_version=320;s->precise=1;}
    else if(major==3&&minor>=1&&extension("GL_EXT_gpu_shader5")){v=kWorldVertexExt310;f=kWorldFragmentExt310;s->shader_version=310;s->precise=1;}
    else if(major==3&&minor>=1&&extension("GL_OES_gpu_shader5")){v=kWorldVertexOes310;f=kWorldFragmentOes310;s->shader_version=310;s->precise=1;}
    GLuint vs=compile(s,GL_VERTEX_SHADER,v),fs=compile(s,GL_FRAGMENT_SHADER,f);if(!vs||!fs){if(vs)glDeleteShader(vs);if(fs)glDeleteShader(fs);return 0;}
    p->id=glCreateProgram();glAttachShader(p->id,vs);glAttachShader(p->id,fs);const char *varyings[]={"vWorldPosition","vEyeNormal","vEyePosition","vClipPosition"};glTransformFeedbackVaryings(p->id,4,varyings,GL_INTERLEAVED_ATTRIBS);glLinkProgram(p->id);glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;glGetProgramiv(p->id,GL_LINK_STATUS,&ok);if(!ok){char log[512]={0};glGetProgramInfoLog(p->id,sizeof log,NULL,log);return fail(s,log[0]?log:"Source world shader linking failed");}
#define U(field,name) p->field=glGetUniformLocation(p->id,name)
    U(model,"uModel");U(modelview,"uModelView");U(projection,"uProjection");U(mode,"uMaterialMode");U(light,"uLightDir");U(diffuse,"uDiffuse");U(ambient,"uAmbient");U(base,"uBase");U(dual,"uDual");U(const0,"uConst0");U(const1,"uConst1");U(fog_params,"uFogParams");U(fog_color,"uFogColor");U(alpha_ref,"uAlphaRef");
#undef U
    return glcheck(s,"Source world program build produced GL errors");
}
/* Diagnostic only: texelFetch preserves the actual normalized DEPTH24 value.
 * Packing three bytes is exact for its 24-bit range and does not alter any
 * source geometry, shader, draw material or render acceptance tolerance. */
static int depth_program_create(Session *s,Graphics *g) {
    GLint range[2]={0},precision=0;glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER,GL_HIGH_FLOAT,range,&precision);s->depth_codec_float_precision=precision;
    if(!glcheck(s,"Actual fragment depth diagnostic precision query failed"))return 0;
    if(precision<23)return fail(s,"Actual DEPTH24 diagnostic requires at least float32 fragment precision");
    const char *vertex="#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}";
    const char *fragment="#version 300 es\nprecision highp float;precision highp int;uniform highp sampler2D uDepth;uniform ivec2 uPixel;layout(location=0)out vec4 color;void main(){uint z=uint(round(texelFetch(uDepth,uPixel,0).r*16777215.0));color=vec4(float(z&255u),float((z>>8)&255u),float((z>>16)&255u),255.0)/255.0;}";
    GLuint vs=compile(s,GL_VERTEX_SHADER,vertex),fs=compile(s,GL_FRAGMENT_SHADER,fragment);if(!vs||!fs){if(vs)glDeleteShader(vs);if(fs)glDeleteShader(fs);return 0;}
    g->depth_program=glCreateProgram();glAttachShader(g->depth_program,vs);glAttachShader(g->depth_program,fs);glLinkProgram(g->depth_program);glDeleteShader(vs);glDeleteShader(fs);
    GLint ok=0;glGetProgramiv(g->depth_program,GL_LINK_STATUS,&ok);if(!ok)return fail(s,"Depth24 diagnostic program linking failed");g->depth_sampler=glGetUniformLocation(g->depth_program,"uDepth");g->depth_pixel=glGetUniformLocation(g->depth_program,"uPixel");glGenVertexArrays(1,&g->depth_vao);
    return g->depth_sampler>=0&&g->depth_pixel>=0?glcheck(s,"Depth24 diagnostic program setup failed"):fail(s,"Depth24 diagnostic uniforms missing");
}
static int texture(Session *s,GLuint *id,uint32_t w,uint32_t h,const uint8_t *rgba) {glGenTextures(1,id);glBindTexture(GL_TEXTURE_2D,*id);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,(GLsizei)w,(GLsizei)h);if(rgba)glTexSubImage2D(GL_TEXTURE_2D,0,0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,rgba);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return glcheck(s,"Texture upload failed");}
static void geometry_upload(Geometry *g,int initial) {
    if(initial){glGenVertexArrays(1,&g->vao);glGenBuffers(1,&g->vbo);glGenBuffers(1,&g->ibo);}
    glBindVertexArray(g->vao);glBindBuffer(GL_ARRAY_BUFFER,g->vbo);glBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)(g->count*sizeof(Vertex)),g->vertices,GL_DYNAMIC_DRAW);
    if(initial){glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,g->ibo);glBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)(g->index_count*4),g->indices,GL_STATIC_DRAW);
#define A(location,count,field) glVertexAttribPointer(location,count,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)offsetof(Vertex,field));glEnableVertexAttribArray(location)
        A(0,3,position);A(1,3,normal);A(2,2,uv0);A(3,2,uv1);
#undef A
    }
}
static void uniforms(Program *p,const float *model,const float *eye,const float *projection,uint32_t mode,const float *const0,const float *const1,float diffuse,float ambient,float alpha,GLuint base,GLuint dual,int actor) {
    float m[16],e[16];coh_world_gl_matrix(model,m);coh_world_gl_matrix(eye,e);glUseProgram(p->id);glUniformMatrix4fv(p->model,1,GL_FALSE,m);glUniformMatrix4fv(p->modelview,1,GL_FALSE,e);glUniformMatrix4fv(p->projection,1,GL_FALSE,projection);glUniform1i(p->mode,(GLint)mode);glUniform3f(p->light,.188144f,.282216f,.940721f);
    glUniform4f(p->diffuse,actor?.18f*diffuse:0,actor?.18f*diffuse:0,actor?.18f*diffuse:0,0);glUniform4f(p->ambient,(actor?.055f:.25f)*ambient,(actor?.055f:.25f)*ambient,(actor?.055f:.25f)*ambient,1);glUniform4fv(p->const0,1,const0);glUniform4fv(p->const1,1,const1);glUniform4f(p->fog_params,0,0,1000000,1);glUniform4f(p->fog_color,0,0,0,1);glUniform1f(p->alpha_ref,alpha);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,base);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,dual);glUniform1i(p->base,0);glUniform1i(p->dual,1);
}
static void draw_world(Session *s,Graphics *g,const float eye[6][12],const float *projection) {
    for(unsigned i=0;i<s->world.part_count;i++){const CohWorldPart *p=&s->world.parts[i];Geometry *geo=&s->world_geometry[i];
        uniforms(&g->program,s->world_matrix[p->node],eye[p->node],projection,p->mode,p->const0,p->const1,p->diffuse_scale,p->ambient_scale,p->alpha_ref,g->world_textures[p->base_texture],g->world_textures[p->dual_texture],0);
        if(p->flags&1u)glDisable(GL_CULL_FACE);else glEnable(GL_CULL_FACE);glDisable(GL_BLEND);glBindVertexArray(geo->vao);glDrawElements(GL_TRIANGLES,(GLsizei)geo->index_count,GL_UNSIGNED_INT,NULL);s->world_draws++;
    }
}
static void draw_walkable(Session *s,Graphics *g,const float *view,const float *projection) {
    const float identity[12]={1,0,0,0,1,0,0,0,1,0,0,0};
    for(unsigned i=0;i<s->walkable.part_count;i++) {
        const CohWorldPart *p=&s->walkable.parts[i].material;Geometry *geo=&s->walkable_geometry[i];
        uniforms(&g->program,identity,view,projection,p->mode,p->const0,p->const1,p->diffuse_scale,p->ambient_scale,p->alpha_ref,g->walkable_textures[p->base_texture],g->walkable_textures[p->dual_texture],0);
        if(p->flags&1u)glDisable(GL_CULL_FACE);else glEnable(GL_CULL_FACE);glDisable(GL_BLEND);
        glBindVertexArray(geo->vao);glDrawElements(GL_TRIANGLES,(GLsizei)geo->index_count,GL_UNSIGNED_INT,NULL);s->walkable_draws++;
    }
}
static void draw_actor(Session *s,Graphics *g,const float *model,const float *eye,const float *projection,int alpha_only) {
    for(unsigned i=0;i<s->actor.part_count;i++){const CohScenePart *p=&s->actor.parts[i];if(!!(p->flags&2u)!=alpha_only)continue;Geometry *geo=&s->actor_geometry[i];
        uniforms(&g->program,model,eye,projection,1,p->const0,p->const1,p->diffuse_scale,p->ambient_scale,p->alpha_ref,g->actor_textures[p->base_texture],g->actor_textures[p->dual_texture],1);
        if(p->flags&1u)glDisable(GL_CULL_FACE);else glEnable(GL_CULL_FACE);if(alpha_only){glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
        glBindVertexArray(geo->vao);glDrawElements(GL_TRIANGLES,(GLsizei)geo->index_count,GL_UNSIGNED_INT,NULL);s->actor_draws++;
    }
}
#if COH_LIVE_COSTUME_DIAGNOSTIC
static void received_surface_delete(Graphics*g,int alive){
    if(g->received_renderer){coh_renderer_surface_lost(g->received_renderer,0,alive);coh_renderer_destroy(g->received_renderer);g->received_renderer=NULL;}
    if(g->received_gles){coh_renderer_gles_destroy(g->received_gles,alive);g->received_gles=NULL;}
    if(alive)glDeleteTextures(COH_RECEIVED_COSTUME_TEXTURES,g->received_textures);
    memset(g->received_textures,0,sizeof g->received_textures);
}
static int received_draw(Session*s,Graphics*g,const float view[12],const float projection[16]){
    s->received_last_draw=0;
    if(!s->received_actor||s->received_pose_updates!=s->observed_entity_updates||s->received_stats.entity_index!=s->observed_entity_index)return 0;
    CohStatus status=COH_OK;
    if(!g->received_attempted){
        g->received_attempted=1;CohRenderBackend backend={0};
        for(uint32_t i=0;i<s->received_stats.textures;i++){
            CohBytes pixels;uint32_t width,height;const char*name;
            status=coh_received_costume_texture(s->received_actor,i,&pixels,&width,&height,&name);if(status)break;
            glGenTextures(1,g->received_textures+i);glBindTexture(GL_TEXTURE_2D,g->received_textures[i]);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,(GLsizei)width,(GLsizei)height,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
            if(!g->received_textures[i]||glGetError()!=GL_NO_ERROR){status=COH_LIMIT;break;}
        }
        if(!status)status=coh_renderer_gles_create(s->received_stats.vertices,s->received_stats.indices,&g->received_gles,&backend);
        CohRendererConfig config={120,s->received_stats.vertices,s->received_stats.indices,3};
        if(!status)status=coh_renderer_create(&config,&backend,&g->received_renderer);
        if(!status){coh_renderer_surface_lost(g->received_renderer,1,1);status=coh_received_costume_bind(s->received_actor,1,g->received_textures,s->received_stats.textures);}
        if(status){received_surface_delete(g,1);s->received_status=status;for(unsigned error=0;error<32&&glGetError()!=GL_NO_ERROR;error++){}snprintf(s->received_stats.missing,sizeof s->received_stats.missing,"Huge GPU preparation status %d",status);}
    }
    if(!g->received_renderer)return 0;
    const CohRenderDraw*draws=NULL;size_t count=0;
    status=coh_received_costume_draws(s->received_actor,view,projection,s->observed_entity_position,&draws,&count);
    if(!status)status=coh_renderer_begin(g->received_renderer,1);
    for(size_t i=0;!status&&i<count;i++)status=coh_renderer_submit(g->received_renderer,draws+i);
    if(!status)status=coh_renderer_flush(g->received_renderer,(CohCancel){0});
    if(status){received_surface_delete(g,1);s->received_status=status;for(unsigned error=0;error<32&&glGetError()!=GL_NO_ERROR;error++){}snprintf(s->received_stats.missing,sizeof s->received_stats.missing,"Huge draw status %d",status);return 0;}
    s->received_frames++;s->received_draws+=count;s->received_last_draw=1;s->received_status=COH_OK;s->received_stats.missing[0]=0;return 1;
}
#endif
static int scene_draw(Session *s,Graphics *g,GLuint fbo,int width,int height,int mode,int reverse,uint8_t *image) {
    float view[12],projection[16],model[12],actor_eye[12],eye[6][12];if(!camera(s,(float)width/height,view,projection,model,actor_eye,eye))return 0;
    glBindFramebuffer(GL_FRAMEBUFFER,fbo);glViewport(0,0,width,height);glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClearColor(17/255.f,19/255.f,23/255.f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);glFrontFace(GL_CW);glCullFace(GL_BACK);
    int observed=s->observed_entity_index&&fbo==0;
    if(mode!=1&&reverse&&!observed)draw_actor(s,g,model,actor_eye,projection,0);
    if(mode!=2){if(fbo!=0)draw_world(s,g,eye,projection);else{
        int world_ok=observed?coh_session_world_draw_observed(s->stream_world,view,projection,scene_center(s),s->view_radius,&s->stream_stats,s->failure,sizeof s->failure):
            coh_session_world_draw(s->stream_world,view,projection,scene_center(s),s->view_radius,&s->stream_stats,s->failure,sizeof s->failure);
        if(!world_ok)return fail(s,s->failure[0]?s->failure:"Indexed Atlas scene draw failed");
    }}
    if(observed&&mode!=1){
        int actor=0;
#if COH_LIVE_COSTUME_DIAGNOSTIC
        actor=received_draw(s,g,view,projection);
#endif
        if(!actor&&!coh_session_world_observed_entity(s->stream_world,view,projection,s->observed_entity_index,s->observed_entity_position,&s->stream_stats,s->failure,sizeof s->failure))return fail(s,"Observed server entity box draw failed");
        s->observed_entity_draws++;
    }
    if(mode!=1&&!reverse&&!observed)draw_actor(s,g,model,actor_eye,projection,0);
    if(mode!=1&&!observed)draw_actor(s,g,model,actor_eye,projection,1);
    glDisable(GL_BLEND);if(image)glReadPixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,image);
    return glcheck(s,"Integrated source scene draw or controlled readback failed");
}
static int transform_check(Session *s,Graphics *g) {
    float view[12],projection[16],model[12],actor_eye[12],eye[6][12];if(!camera(s,1,view,projection,model,actor_eye,eye))return 0;
    for(unsigned kind=0;kind<2;kind++)for(unsigned i=0;i<(kind?s->actor.part_count:s->world.part_count);i++) {
        Geometry *geo=kind?&s->actor_geometry[i]:&s->world_geometry[i];const float *world=kind?model:s->world_matrix[s->world.parts[i].node],*mv=kind?actor_eye:eye[s->world.parts[i].node];
        const float white[4]={1,1,1,1};uniforms(&g->program,world,mv,projection,1,white,white,0,1,0,kind?g->actor_textures[0]:g->world_textures[0],kind?g->actor_textures[0]:g->world_textures[0],kind);
        size_t bytes=(size_t)geo->count*13*sizeof(float);g->tf_bytes=bytes;glBindVertexArray(geo->vao);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,g->tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(GLsizeiptr)bytes,NULL,GL_DYNAMIC_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,g->tf);glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,(GLsizei)geo->count);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);
        if(!glcheck(s,"Integrated transform feedback failed"))return 0;const float *actual=glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,(GLsizeiptr)bytes,GL_MAP_READ_BIT);if(!actual)return fail(s,"Integrated transform feedback map failed");
        for(unsigned j=0;j<geo->count;j++){float expected[13];if(coh_world_vertex(world,mv,projection,geo->vertices[j].position,geo->vertices[j].normal,expected)){glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER);return fail(s,"Source CPU transform failed");}
            for(unsigned k=0;k<13;k++){float error=fabsf(actual[j*13+k]-expected[k]);s->tf_components++;if(isfinite(error)&&error>s->tf_max_error)s->tf_max_error=error;if(!isfinite(error)||error>.0001f)s->tf_mismatches++;}
        }
        if(!glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER))return fail(s,"Integrated transform feedback became invalid");glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);
    }
    return s->tf_mismatches?fail(s,"Integrated source CPU/GPU transform mismatch"):glcheck(s,"Integrated transform feedback readback failed");
}
static int walkable_transform_check(Session *s,Graphics *g) {
    float view[12],projection[16],model[12],actor_eye[12],eye[6][12];
    const float identity[12]={1,0,0,0,1,0,0,0,1,0,0,0},white[4]={1,1,1,1};
    if(!camera(s,1,view,projection,model,actor_eye,eye))return 0;
    for(unsigned i=0;i<s->walkable.part_count;i++) {
        Geometry *geo=&s->walkable_geometry[i];
        uniforms(&g->program,identity,view,projection,1,white,white,0,1,0,g->walkable_textures[0],g->walkable_textures[0],0);
        size_t bytes=(size_t)geo->count*13*sizeof(float);g->tf_bytes=bytes;glBindVertexArray(geo->vao);glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER,g->tf);glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER,(GLsizeiptr)bytes,NULL,GL_DYNAMIC_READ);glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,g->tf);glEnable(GL_RASTERIZER_DISCARD);glBeginTransformFeedback(GL_POINTS);glDrawArrays(GL_POINTS,0,(GLsizei)geo->count);glEndTransformFeedback();glDisable(GL_RASTERIZER_DISCARD);
        if(!glcheck(s,"Authored walkable transform feedback failed"))return 0;
        const float *actual=glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER,0,(GLsizeiptr)bytes,GL_MAP_READ_BIT);if(!actual)return fail(s,"Authored walkable feedback map failed");
        for(unsigned j=0;j<geo->count;j++){float expected[13];if(coh_world_vertex(identity,view,projection,geo->vertices[j].position,geo->vertices[j].normal,expected)){glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER);return fail(s,"Authored world-space CPU transform failed");}
            for(unsigned k=0;k<13;k++){float error=fabsf(actual[j*13+k]-expected[k]);s->walkable_tf_components++;if(!isfinite(error)||error>.0001f)s->walkable_tf_mismatches++;}
        }
        if(!glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER))return fail(s,"Authored walkable feedback invalid");glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);
    }
    if(s->walkable_tf_mismatches)return fail(s,"Authored walkable CPU/GPU transform mismatch");
    glBindFramebuffer(GL_FRAMEBUFFER,g->fbo);glViewport(0,0,SIZE,SIZE);glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClearColor(17/255.f,19/255.f,23/255.f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);glFrontFace(GL_CW);glCullFace(GL_BACK);draw_walkable(s,g,view,projection);
    uint8_t *pixels=malloc(SIZE*SIZE*4u);if(!pixels)return fail(s,"Bounded walkable visibility allocation failed");glReadPixels(0,0,SIZE,SIZE,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
    for(unsigned i=0;i<SIZE*SIZE;i++)if(abs((int)pixels[i*4]-17)>2||abs((int)pixels[i*4+1]-19)>2||abs((int)pixels[i*4+2]-23)>2)s->walkable_visible_pixels++;
    free(pixels);return s->walkable_visible_pixels?glcheck(s,"Authored walkable visibility check failed"):fail(s,"Authored walkable visible geometry missing");
}
static unsigned difference(const uint8_t *a,const uint8_t *b) {unsigned max=0;for(unsigned k=0;k<3;k++){unsigned d=a[k]>b[k]?a[k]-b[k]:b[k]-a[k];if(d>max)max=d;}return max;}
static int depth_only_draw(Session *s,Graphics *g,int mode) {
    float view[12],projection[16],model[12],actor_eye[12],eye[6][12];if(!camera(s,1,view,projection,model,actor_eye,eye))return 0;
    glBindFramebuffer(GL_FRAMEBUFFER,g->fbo);glViewport(0,0,SIZE,SIZE);glEnable(GL_DEPTH_TEST);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);glClearDepthf(1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);glFrontFace(GL_CW);glCullFace(GL_BACK);
    if(mode!=2)draw_world(s,g,eye,projection);if(mode!=1)draw_actor(s,g,model,actor_eye,projection,0);
    return glcheck(s,"Opaque actual-mesh depth diagnostic draw failed");
}
static int depth_sample(Session *s,Graphics *g,unsigned x,unsigned y,unsigned *depth) {
    glBindFramebuffer(GL_FRAMEBUFFER,g->pixel_fbo);glViewport(0,0,1,1);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glUseProgram(g->depth_program);glBindVertexArray(g->depth_vao);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,g->depth);glUniform1i(g->depth_sampler,0);glUniform2i(g->depth_pixel,(GLint)x,(GLint)y);glDrawArrays(GL_TRIANGLES,0,3);uint8_t bytes[4];glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,bytes);
    if(!glcheck(s,"Actual DEPTH24 diagnostic sampling failed"))return 0;*depth=(unsigned)bytes[0]|(unsigned)bytes[1]<<8|(unsigned)bytes[2]<<16;return 1;
}
static int depth_tie_check(Session *s,Graphics *g) {
    if(s->depth_order_color_differences>DEPTH_DIAGNOSTICS){s->depth_order_mismatches=s->depth_order_color_differences;return fail(s,"Opaque depth order differences exceed bounded actual-depth diagnostics");}
    for(unsigned mode=1;mode<=3;mode++){
        if(!depth_only_draw(s,g,mode==3?0:(int)mode))return 0;
        for(unsigned i=0;i<s->depth_diagnostics_count;i++){DepthDiagnostic *d=&s->depth_diagnostics[i];unsigned *out=mode==1?&d->world_depth:(mode==2?&d->actor_depth:&d->combined_depth);if(!depth_sample(s,g,d->x,d->y,out))return 0;}
        for(unsigned i=0;i<1+s->world_control_count+s->actor_control_count;i++){
            DepthDiagnostic *d=i==0?&s->clear_control:(i<=s->world_control_count?&s->world_controls[i-1]:&s->actor_controls[i-1-s->world_control_count]);
            unsigned *out=mode==1?&d->world_depth:(mode==2?&d->actor_depth:&d->combined_depth);if(!depth_sample(s,g,d->x,d->y,out))return 0;
        }
    }
    if(s->clear_control.world_depth!=0xffffffu||s->clear_control.actor_depth!=0xffffffu||s->clear_control.combined_depth!=0xffffffu)return fail(s,"Actual DEPTH24 sampler clear control failed");
    int world_front=0,actor_front=0;
    for(unsigned group=0;group<2;group++)for(unsigned i=0;i<(group?s->actor_control_count:s->world_control_count);i++){
        const DepthDiagnostic *d=group?&s->actor_controls[i]:&s->world_controls[i];unsigned expected=d->world_depth<d->actor_depth?d->world_depth:d->actor_depth;
        if(d->combined_depth!=expected)return fail(s,"Actual DEPTH24 combined positive control is not minimum source-geometry depth");
        if(d->world_depth<0xffffffu&&d->actor_depth<0xffffffu){
            if(d->world_depth<d->actor_depth&&!world_front){s->world_front_control=*d;world_front=1;}
            if(d->actor_depth<d->world_depth&&!actor_front){s->actor_front_control=*d;actor_front=1;}
        }
    }
    if(!world_front||!actor_front)return fail(s,"Actual DEPTH24 sampler distinct source-world/source-actor controls missing");s->depth_sampler_controls_passed=1;
    for(unsigned i=0;i<s->depth_diagnostics_count;i++){const DepthDiagnostic *d=&s->depth_diagnostics[i];
        if(d->world_depth<0xffffffu&&d->world_depth==d->actor_depth&&d->world_depth==d->combined_depth)s->depth_order_ties++;
        else s->depth_order_mismatches++;
    }
    return s->depth_order_mismatches?fail(s,"Unequal actual DEPTH24 values changed opaque shared-depth order result"):1;
}
static int depth_check(Session *s,Graphics *g) {
    size_t bytes=SIZE*SIZE*4u;uint8_t *images=malloc(bytes*4);if(!images)return fail(s,"Bounded startup depth witness allocation failed");int ok=0;
    uint8_t *world=images,*actor=images+bytes,*both=images+bytes*2,*reverse=images+bytes*3;
    if(!scene_draw(s,g,g->fbo,SIZE,SIZE,1,0,world)||!scene_draw(s,g,g->fbo,SIZE,SIZE,2,0,actor)||!scene_draw(s,g,g->fbo,SIZE,SIZE,0,0,both)||!scene_draw(s,g,g->fbo,SIZE,SIZE,0,1,reverse))goto end;
    const uint8_t clear[4]={17,19,23,255};
    for(unsigned i=0;i<SIZE*SIZE;i++) {uint8_t *w=world+i*4,*a=actor+i*4,*b=both+i*4,*r=reverse+i*4;unsigned wc=difference(w,clear),ac=difference(a,clear);
        if(wc>2)s->world_visible_pixels++;if(ac>2)s->actor_visible_pixels++;if(difference(w,b)>2)s->actor_changed_pixels++;
        if(difference(b,r)>2){s->depth_order_color_differences++;if(s->depth_diagnostics_count<DEPTH_DIAGNOSTICS){DepthDiagnostic *d=&s->depth_diagnostics[s->depth_diagnostics_count++];d->x=i%SIZE;d->y=i/SIZE;memcpy(d->world,w,4);memcpy(d->actor,a,4);memcpy(d->forward,b,4);memcpy(d->reverse,r,4);}}
        if(wc>2&&ac>2&&difference(w,a)>2){
            if(difference(b,w)<=2){s->world_occludes_actor_pixels++;if(s->world_control_count<DEPTH_DIAGNOSTICS&&(s->world_occludes_actor_pixels==1||s->world_occludes_actor_pixels%32==1)){DepthDiagnostic *d=&s->world_controls[s->world_control_count++];d->x=i%SIZE;d->y=i/SIZE;}}
            if(difference(b,a)<=2){s->actor_occludes_world_pixels++;if(s->actor_control_count<DEPTH_DIAGNOSTICS&&(s->actor_occludes_world_pixels==1||s->actor_occludes_world_pixels%32==1)){DepthDiagnostic *d=&s->actor_controls[s->actor_control_count++];d->x=i%SIZE;d->y=i/SIZE;}}
        }
    }
    if(!depth_tie_check(s,g))goto end;
    if(s->depth_order_mismatches)fail(s,"Opaque draw order changed shared depth result (hair always last)");
    else if(!s->world_visible_pixels||!s->actor_visible_pixels||!s->actor_changed_pixels||!s->world_occludes_actor_pixels)fail(s,"Authored actor/world startup visibility or real occlusion witness missing");
    else {s->startup_checked=1;ok=1;}
end:free(images);return ok;
}
static void geometry_delete(Geometry *geo){if(geo->vao)glDeleteVertexArrays(1,&geo->vao);if(geo->vbo)glDeleteBuffers(1,&geo->vbo);if(geo->ibo)glDeleteBuffers(1,&geo->ibo);geo->vao=geo->vbo=geo->ibo=0;}
static int cleanup_egl_failure(Session *s,const char *operation) {
    unsigned code=(unsigned)eglGetError();s->cleanup_egl_errors++;s->cleanup_egl_error=code;if(!s->egl_error)s->egl_error=code;
    return fail(s,operation);
}
static void graphics_delete(Session *s,Graphics *g) {
    coh_session_world_surface_lost(s->stream_world,g->context_current,&s->stream_stats);
#if COH_LIVE_COSTUME_DIAGNOSTIC
    received_surface_delete(g,g->context_current);
#endif
    int released=1;
    /* No GL call is permitted against a partial context that never became
     * current. Any context-owned resources then disappear with its checked
     * destruction. Every driver call remains outside the shared mutex. */
    if(g->context_current){for(unsigned i=0;i<s->walkable.part_count;i++)geometry_delete(&s->walkable_geometry[i]);for(unsigned i=0;i<s->world.part_count;i++)geometry_delete(&s->world_geometry[i]);for(unsigned i=0;i<s->actor.part_count;i++)geometry_delete(&s->actor_geometry[i]);
        glDeleteTextures((GLsizei)s->walkable.texture_count,g->walkable_textures);glDeleteTextures((GLsizei)s->world.texture_count,g->world_textures);glDeleteTextures((GLsizei)s->actor.texture_count,g->actor_textures);if(g->program.id)glDeleteProgram(g->program.id);if(g->tf)glDeleteBuffers(1,&g->tf);if(g->fbo)glDeleteFramebuffers(1,&g->fbo);if(g->color)glDeleteTextures(1,&g->color);if(g->depth)glDeleteTextures(1,&g->depth);if(g->depth_program)glDeleteProgram(g->depth_program);if(g->depth_vao)glDeleteVertexArrays(1,&g->depth_vao);if(g->pixel_fbo)glDeleteFramebuffers(1,&g->pixel_fbo);if(g->pixel_color)glDeleteTextures(1,&g->pixel_color);
        unsigned previous_errors=s->gl_errors;if(!glcheck(s,"Session owned GL resource deletion failed")){s->cleanup_gl_errors+=s->gl_errors-previous_errors;released=0;}
    }
    if(g->initialized){
        if(g->context_current&&!eglMakeCurrent(g->display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)){cleanup_egl_failure(s,"Session EGL context unbind failed");released=0;}
        if(g->surface!=EGL_NO_SURFACE&&!eglDestroySurface(g->display,g->surface)){cleanup_egl_failure(s,"Session owned EGL Surface destruction failed");released=0;}
        if(g->context!=EGL_NO_CONTEXT&&!eglDestroyContext(g->display,g->context)){cleanup_egl_failure(s,"Session owned EGL context destruction failed");released=0;}
        if(!eglTerminate(g->display)){cleanup_egl_failure(s,"Session initialized EGL display termination failed");released=0;}
    }
    if(!eglReleaseThread()){cleanup_egl_failure(s,"Session EGL worker thread release failed");released=0;}
    if(g->window){ANativeWindow_release(g->window);g->window=NULL;}s->objects_released=released;
}
static int graphics_create(Session *s,Graphics *g) {
    g->display=eglGetDisplay(EGL_DEFAULT_DISPLAY);if(g->display==EGL_NO_DISPLAY||!eglInitialize(g->display,NULL,NULL)){s->egl_error=(unsigned)eglGetError();return fail(s,"Session EGL initialization failed");}
    g->initialized=1;if(!eglBindAPI(EGL_OPENGL_ES_API)){s->egl_error=(unsigned)eglGetError();return fail(s,"Session EGL API binding failed");}
    const EGLint attributes[]={EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT_KHR,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,24,EGL_NONE};EGLConfig config;EGLint count;
    if(!eglChooseConfig(g->display,attributes,&config,1,&count)||count!=1)return fail(s,"Session EGL depth24 configuration failed");EGLint visual;if(!eglGetConfigAttrib(g->display,config,EGL_NATIVE_VISUAL_ID,&visual))return fail(s,"Session EGL native format failed");ANativeWindow_setBuffersGeometry(g->window,0,0,visual);
    const EGLint context_attributes[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};g->context=eglCreateContext(g->display,config,EGL_NO_CONTEXT,context_attributes);
    if(g->context==EGL_NO_CONTEXT){s->egl_error=(unsigned)eglGetError();return fail(s,"Session EGL context allocation failed");}
    g->surface=eglCreateWindowSurface(g->display,config,g->window,NULL);
    if(g->surface==EGL_NO_SURFACE){s->egl_error=(unsigned)eglGetError();s->surface_failure=1;return fail(s,"Session native window Surface failed");}
    if(!eglMakeCurrent(g->display,g->surface,g->surface,g->context)){s->egl_error=(unsigned)eglGetError();s->surface_failure=1;return fail(s,"Session native Surface activation failed");}
    g->context_current=1;
    snprintf(s->gl_vendor,sizeof s->gl_vendor,"%s",(const char*)glGetString(GL_VENDOR));snprintf(s->gl_renderer,sizeof s->gl_renderer,"%s",(const char*)glGetString(GL_RENDERER));s->objects_released=0;
    if(!program_create(s,&g->program)||!skin(s))return 0;
    for(unsigned i=0;i<s->world.texture_count;i++){const CohWorldTexture *t=&s->world.textures[i];if(!texture(s,&g->world_textures[i],t->width,t->height,t->rgba))return 0;}
    for(unsigned i=0;i<s->walkable.texture_count;i++){const CohWorldTexture *t=&s->walkable.textures[i];if(!texture(s,&g->walkable_textures[i],t->width,t->height,t->rgba))return 0;if(i<2){glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);}}
    for(unsigned i=0;i<s->actor.texture_count;i++){const CohSceneTexture *t=&s->actor.textures[i];if(!texture(s,&g->actor_textures[i],t->width,t->height,t->rgba))return 0;}
    for(unsigned i=0;i<s->walkable.part_count;i++)geometry_upload(&s->walkable_geometry[i],1);
    for(unsigned i=0;i<s->world.part_count;i++)geometry_upload(&s->world_geometry[i],1);for(unsigned i=0;i<s->actor.part_count;i++)geometry_upload(&s->actor_geometry[i],1);glGenBuffers(1,&g->tf);
    if(!texture(s,&g->color,SIZE,SIZE,NULL))return 0;glGenFramebuffers(1,&g->fbo);glBindFramebuffer(GL_FRAMEBUFFER,g->fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,g->color,0);glGenTextures(1,&g->depth);glBindTexture(GL_TEXTURE_2D,g->depth);glTexStorage2D(GL_TEXTURE_2D,1,GL_DEPTH_COMPONENT24,SIZE,SIZE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,g->depth,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail(s,"Session startup depth witness FBO incomplete");
    if(!depth_program_create(s,g)||!texture(s,&g->pixel_color,1,1,NULL))return 0;glGenFramebuffers(1,&g->pixel_fbo);glBindFramebuffer(GL_FRAMEBUFFER,g->pixel_fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,g->pixel_color,0);if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail(s,"Actual-depth diagnostic pixel target incomplete");
    /* The accepted benchmark witness uses its original declared pose, on a
     * private startup snapshot. Actual authored WALK state is never recentered. */
    uint32_t saved_observed=s->observed_entity_index;s->observed_entity_index=0;
    CohMotionState saved_motion=s->motion;CohLocomotionState saved_animation=s->animation;CohLocomotionBlend saved_blend=s->blend;
    float saved_yaw=s->camera_yaw,saved_pitch=s->camera_pitch;
    memcpy(s->motion.position,s->benchmark_spawn,sizeof s->motion.position);s->motion.body_yaw=wrap(s->benchmark_yaw-PI);
    s->camera_yaw=s->benchmark_yaw;s->camera_pitch=.16f;coh_locomotion_init(&s->animation);coh_locomotion_blend_init(&s->blend);
    int qualified=skin(s);for(unsigned i=0;qualified&&i<s->actor.part_count;i++)geometry_upload(&s->actor_geometry[i],0);
    qualified=qualified&&transform_check(s,g)&&(s->startup_checked||depth_check(s,g));
    s->motion=saved_motion;s->animation=saved_animation;s->blend=saved_blend;s->camera_yaw=saved_yaw;s->camera_pitch=saved_pitch;
    if(!qualified)return 0;
    if(!skin(s))return 0;for(unsigned i=0;i<s->actor.part_count;i++)geometry_upload(&s->actor_geometry[i],0);
    if(!walkable_transform_check(s,g))return 0;
    float stream_view[12],stream_projection[16],stream_model[12],stream_eye[12],stream_groups[6][12];
    if(!camera(s,1,stream_view,stream_projection,stream_model,stream_eye,stream_groups))return 0;
    if(!coh_session_world_surface(s->stream_world,stream_view,stream_projection,scene_center(s),s->view_radius,&s->stream_stats,s->failure,sizeof s->failure))return fail(s,s->failure[0]?s->failure:"Indexed Atlas GPU admission failed");
    s->observed_entity_index=saved_observed;
    return glcheck(s,"Indexed scene admitted and accepted state restored");
}

/* Startup TF/pixel checks run against a private logical snapshot. UI state and
 * cancel calls remain responsive during GPU readbacks. Copy only graphics and
 * receipt fields back, never overwriting controls delivered during startup. */
static void startup_commit(Session *s,const Session *copy) {
    s->stream_stats=copy->stream_stats;
    memcpy(s->walkable_geometry,copy->walkable_geometry,sizeof s->walkable_geometry);
    s->walkable_tf_components=copy->walkable_tf_components;s->walkable_tf_mismatches=copy->walkable_tf_mismatches;s->walkable_visible_pixels=copy->walkable_visible_pixels;s->walkable_draws=copy->walkable_draws;
    memcpy(s->world_geometry,copy->world_geometry,sizeof s->world_geometry);memcpy(s->actor_geometry,copy->actor_geometry,sizeof s->actor_geometry);
    if(copy->failed&&!s->failed){s->failed=1;memcpy(s->failure,copy->failure,sizeof s->failure);}memcpy(s->gl_vendor,copy->gl_vendor,sizeof s->gl_vendor);memcpy(s->gl_renderer,copy->gl_renderer,sizeof s->gl_renderer);
    s->shader_version=copy->shader_version;s->precise=copy->precise;s->objects_released=copy->objects_released;
    s->tf_components=copy->tf_components;s->tf_mismatches=copy->tf_mismatches;s->tf_max_error=copy->tf_max_error;s->gl_errors=copy->gl_errors;
    s->depth_order_mismatches=copy->depth_order_mismatches;s->world_visible_pixels=copy->world_visible_pixels;s->actor_visible_pixels=copy->actor_visible_pixels;
    s->depth_order_color_differences=copy->depth_order_color_differences;s->depth_order_ties=copy->depth_order_ties;s->depth_diagnostics_count=copy->depth_diagnostics_count;memcpy(s->depth_diagnostics,copy->depth_diagnostics,sizeof s->depth_diagnostics);
    s->depth_sampler_controls_passed=copy->depth_sampler_controls_passed;s->clear_control=copy->clear_control;s->world_front_control=copy->world_front_control;s->actor_front_control=copy->actor_front_control;
    s->depth_codec_float_precision=copy->depth_codec_float_precision;
    s->world_occludes_actor_pixels=copy->world_occludes_actor_pixels;s->actor_occludes_world_pixels=copy->actor_occludes_world_pixels;s->actor_changed_pixels=copy->actor_changed_pixels;
    s->observed_entity_draws=copy->observed_entity_draws;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    s->received_stats=copy->received_stats;s->received_last_draw=copy->received_last_draw;s->received_frames=copy->received_frames;s->received_draws=copy->received_draws;
#endif
    s->runtime_world_reads=copy->runtime_world_reads;s->runtime_world_bytes=copy->runtime_world_bytes;
    s->startup_checked=copy->startup_checked;s->skin_samples=copy->skin_samples;s->world_draws=copy->world_draws;s->actor_draws=copy->actor_draws;
    s->egl_error=copy->egl_error;s->width=copy->width;s->height=copy->height;s->frames=copy->frames;
    s->expected_cancel_surface_errors=copy->expected_cancel_surface_errors;s->expected_cancel_egl_error=copy->expected_cancel_egl_error;
    s->cleanup_gl_errors=copy->cleanup_gl_errors;s->cleanup_egl_errors=copy->cleanup_egl_errors;s->cleanup_egl_error=copy->cleanup_egl_error;
}
/* Source-level allocations and GPU payloads, not driver RSS/PSS. Call only
 * between draws on the single render owner; no candidate is active here. */
static int capture_add(uint64_t *sum,uint64_t bytes){if(*sum>COH_CAPTURE_SCENE_LIMIT||bytes>COH_CAPTURE_SCENE_LIMIT-*sum)return 0;*sum+=bytes;return 1;}
static int capture_scene_charge(const Session*s,const Graphics*g,uint64_t*out){
    uint64_t cpu=0,gpu=0,total=0;
    if(!coh_session_world_owned_bytes(s->stream_world,&cpu,&gpu)||
       !capture_add(&total,cpu)||!capture_add(&total,gpu)||
       !capture_add(&total,2u*sizeof(Session)+sizeof(Graphics))||
       !capture_add(&total,coh_walk_world_owned_bytes(&s->walk_world)))return 0;
    for(unsigned i=0;i<7;i++)if(!capture_add(&total,s->assets[i].n))return 0;
    const Geometry *sets[]={s->world_geometry,s->actor_geometry,s->walkable_geometry};
    const unsigned counts[]={s->world.part_count,s->actor.part_count,s->walkable.part_count};
    for(unsigned set=0;set<3;set++)for(unsigned i=0;i<counts[set];i++){
        const Geometry*m=sets[set]+i;
        uint64_t vertices=(uint64_t)m->count*sizeof(Vertex),indices=(uint64_t)m->index_count*4u;
        if(!capture_add(&total,vertices+(uint64_t)m->count*sizeof(CohMeshVertex)+indices)||
           !capture_add(&total,vertices+indices))return 0;
    }
    for(unsigned i=0;i<s->world.texture_count;i++)if(!capture_add(&total,s->world.textures[i].bytes))return 0;
    for(unsigned i=0;i<s->actor.texture_count;i++)if(!capture_add(&total,s->actor.textures[i].bytes))return 0;
    for(unsigned i=0;i<s->walkable.texture_count;i++)if(!capture_add(&total,s->walkable.textures[i].bytes))return 0;
    #if COH_LIVE_COSTUME_DIAGNOSTIC
    if(s->received_actor&&(!capture_add(&total,s->received_stats.cpu_bytes)||!capture_add(&total,s->received_stats.gpu_reserve_bytes)||!capture_add(&total,s->received_stats.renderer_cpu_reserve_bytes)||!capture_add(&total,s->received_source_bytes)))return 0;
#endif
    if(!capture_add(&total,(uint64_t)SIZE*SIZE*8u+4u+g->tf_bytes))return 0;
    *out=total;return total<=COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE;
}
#if COH_LIVE_COSTUME_DIAGNOSTIC
static uint32_t received_u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t received_u64(const uint8_t*p){return received_u32(p)|(uint64_t)received_u32(p+4)<<32;}
typedef struct {Session*s;uint64_t epoch,updates,invalidation;uint32_t entity;} ReceivedCancel;
static int received_cancel(void*context){ReceivedCancel*t=context;Session*s=t->s;pthread_mutex_lock(&s->mutex);int stop=s->failed||s->epoch!=t->epoch||s->observed_entity_updates!=t->updates||s->observed_entity_index!=t->entity||s->received_invalidations!=t->invalidation;pthread_mutex_unlock(&s->mutex);return stop;}
/* Single renderWorker, after the old EGL loop/context returned. Every source
 * FD is dup-owned only through preparation. Main-thread cancel/clear merely
 * invalidates the token; they never wait for IO or release borrowed GL data. */
JNIEXPORT jint JNICALL Java_org_coh_sessionclient_SessionNative_observedCostume(JNIEnv*e,jclass c,jlong handle,jbyteArray frame,jintArray fds,jlongArray offsets,jlongArray lengths,jlong java_bytes,jlong source_bytes){
    (void)c;Session*s=(Session*)(intptr_t)handle;
    jsize archive_count=fds?(*e)->GetArrayLength(e,fds):0;
    if(!s||!frame||!fds||!offsets||!lengths||java_bytes<48384||source_bytes<=0||
       (*e)->GetArrayLength(e,frame)!=48384||archive_count<1||archive_count>(jsize)COH_RECEIVED_COSTUME_ARCHIVES||(*e)->GetArrayLength(e,offsets)!=archive_count||(*e)->GetArrayLength(e,lengths)!=archive_count)return COH_INVALID;
    uint64_t java_charge=(uint64_t)java_bytes,minimum_java=48384u+(uint64_t)archive_count*(sizeof(jint)+2u*sizeof(jlong));
    if(java_charge<minimum_java)java_charge=minimum_java;
    uint8_t header[32];jint descriptors[COH_RECEIVED_COSTUME_ARCHIVES];jlong starts[COH_RECEIVED_COSTUME_ARCHIVES],sizes[COH_RECEIVED_COSTUME_ARCHIVES];
    (*e)->GetByteArrayRegion(e,frame,0,32,(jbyte*)header);if((*e)->ExceptionCheck(e))return COH_INVALID;
    if(memcmp(header,"COHCST01",8)||received_u32(header+8)!=32||received_u32(header+12)!=sizeof(CohOriginalCostumeSnapshot)||!received_u64(header+16)||received_u32(header+28))return COH_INVALID;
    uint32_t entity=received_u32(header+24);if(!entity||entity>10239)return COH_INVALID;
    (*e)->GetIntArrayRegion(e,fds,0,archive_count,descriptors);if((*e)->ExceptionCheck(e))return COH_INVALID;
    (*e)->GetLongArrayRegion(e,offsets,0,archive_count,starts);if((*e)->ExceptionCheck(e))return COH_INVALID;
    (*e)->GetLongArrayRegion(e,lengths,0,archive_count,sizes);if((*e)->ExceptionCheck(e))return COH_INVALID;
    CohReceivedArchiveFd files[COH_RECEIVED_COSTUME_ARCHIVES];for(jsize i=0;i<archive_count;i++){if(descriptors[i]<0||starts[i]||sizes[i]<=0||sizes[i]>UINT32_MAX)return COH_INVALID;files[i]=(CohReceivedArchiveFd){descriptors[i],0,(uint64_t)sizes[i]};}
    pthread_mutex_lock(&s->mutex);
    if(s->running||s->received_preparing||s->failed||s->observed_entity_index!=entity){pthread_mutex_unlock(&s->mutex);return COH_STATE;}
    s->received_preparing=1;ReceivedCancel token={s,s->epoch,s->observed_entity_updates,s->received_invalidations,entity};pthread_mutex_unlock(&s->mutex);
    Graphics future={0};uint64_t parent=0,base=0,world_cpu=0,world_gpu=0;CohReceivedCostume*candidate=NULL;CohReceivedCostumeFds*imports=NULL;CohOriginalCostumeSnapshot*snapshot=NULL;CohReceivedCostumeStats stats={0};CohStatus status=COH_LIMIT;char reason[128]={0};
    const Geometry*sets[]={s->world_geometry,s->actor_geometry,s->walkable_geometry};const unsigned counts[]={s->world.part_count,s->actor.part_count,s->walkable.part_count};
    for(unsigned set=0;set<3;set++)for(unsigned i=0;i<counts[set];i++){uint64_t bytes=(uint64_t)sets[set][i].count*13u*sizeof(float);if(bytes>future.tf_bytes)future.tf_bytes=(size_t)bytes;}
    if(!capture_scene_charge(s,&future,&base))goto done;
    parent=base;
    if(!capture_add(&parent,java_charge)||!capture_add(&parent,(uint64_t)source_bytes)||!capture_add(&parent,sizeof* snapshot+coh_received_costume_fds_allocation_bytes()+COH_RECEIVED_COSTUME_STACK+COH_CAPTURE_RESERVE))goto done;
    snapshot=malloc(sizeof*snapshot);if(!snapshot)goto done;
    (*e)->GetByteArrayRegion(e,frame,32,sizeof*snapshot,(jbyte*)snapshot);if((*e)->ExceptionCheck(e)){status=COH_INVALID;goto done;}
    status=coh_received_costume_fds_open(files,(uint32_t)archive_count,&imports);if(status){snprintf(stats.missing,sizeof stats.missing,"loaded immutable archive descriptors");goto done;}
    CohReceivedCostumeInputs inputs={0};inputs.snapshot=snapshot;inputs.rig=&s->rig;inputs.parent_bytes=parent;inputs.source_epoch=received_u64(header+16);inputs.entity_index=entity;inputs.cancel=(CohCancel){received_cancel,&token};
    status=coh_received_costume_fds_sources(imports,inputs.archives);if(status)goto done;
    status=coh_received_costume_prepare(&inputs,&candidate,&stats);if(status)goto done;
    if(received_cancel(&token)){status=COH_CANCELLED;goto done;}
    /* The world owns its concrete old+candidate stream reservation. Add the
     * new actor and retained observer source to that same parent domain; do not
     * replace it with this module's independent96MiB check. */
    if(!coh_session_world_owned_bytes(s->stream_world,&world_cpu,&world_gpu)||base<world_cpu+world_gpu){status=COH_STATE;goto done;}
    uint64_t retained=base-world_cpu-world_gpu;
    if(s->received_actor){uint64_t old=s->received_stats.cpu_bytes+s->received_stats.gpu_reserve_bytes+s->received_stats.renderer_cpu_reserve_bytes+s->received_source_bytes;if(retained<old){status=COH_STATE;goto done;}retained-=old;}
    if(!capture_add(&retained,stats.cpu_bytes)||!capture_add(&retained,stats.gpu_reserve_bytes)||!capture_add(&retained,stats.renderer_cpu_reserve_bytes)||!capture_add(&retained,(uint64_t)source_bytes)||!capture_add(&retained,COH_CAPTURE_RESERVE)){status=COH_LIMIT;goto done;}
    pthread_mutex_lock(&s->mutex);
    int current=!s->failed&&s->epoch==token.epoch&&s->observed_entity_updates==token.updates&&s->observed_entity_index==token.entity&&s->received_invalidations==token.invalidation;
    CohReceivedCostume*old=NULL;
    /* Pure control/preflight update, no IO or driver calls. It shares final
     * identity validation with publication, so cancellation cannot undercharge
     * an old owner that remains live. Preparation already charged old+new. */
    if(current&&s->runtime_world_status==1&&!coh_session_world_parent_bytes(s->stream_world,retained,reason,sizeof reason)){status=COH_LIMIT;snprintf(stats.missing,sizeof stats.missing,"%s",reason);current=0;}
    if(current){old=s->received_actor;s->received_actor=candidate;candidate=NULL;s->received_stats=stats;s->received_source_bytes=(uint64_t)source_bytes;s->received_pose_updates=token.updates;s->received_status=COH_OK;s->received_last_draw=0;s->capture_lock_frame=s->frames;s->capture_draws=0;}else if(!status)status=COH_CANCELLED;
    pthread_mutex_unlock(&s->mutex);coh_received_costume_destroy(&old);
done:
    coh_received_costume_destroy(&candidate);coh_received_costume_fds_destroy(&imports);free(snapshot);
    pthread_mutex_lock(&s->mutex);s->received_preparing=0;
    if(status){s->received_status=status;if(!stats.missing[0])snprintf(stats.missing,sizeof stats.missing,"Huge preparation status %d",status);if(!s->received_actor)s->received_stats=stats;else snprintf(s->received_stats.missing,sizeof s->received_stats.missing,"%s",stats.missing);}
    pthread_mutex_unlock(&s->mutex);return status;
}
#endif
#if COH_FULLSCREEN_DIAGNOSTIC
/* Private initialization only, before Activity publishes its handle or a Surface.
 * The old stream remains owned until a complete FD-backed candidate exists. */
JNIEXPORT jint JNICALL Java_org_coh_sessionclient_SessionNative_runtimeWorld(JNIEnv *e,jclass c,jlong handle,jintArray fds,jlongArray offsets,jlongArray lengths,jlong java_bytes){
    (void)c;Session*s=(Session*)(intptr_t)handle;
    if(!s||!fds||!offsets||!lengths||java_bytes<0||
       (*e)->GetArrayLength(e,fds)!=3||(*e)->GetArrayLength(e,offsets)!=3||(*e)->GetArrayLength(e,lengths)!=3)return 0;
    jint descriptors[3];jlong starts[3],sizes[3];
    (*e)->GetIntArrayRegion(e,fds,0,3,descriptors);if((*e)->ExceptionCheck(e))return 0;
    (*e)->GetLongArrayRegion(e,offsets,0,3,starts);if((*e)->ExceptionCheck(e))return 0;
    (*e)->GetLongArrayRegion(e,lengths,0,3,sizes);if((*e)->ExceptionCheck(e))return 0;
    CohSessionWorldFd inputs[3];
    for(unsigned i=0;i<3;i++){
        if(descriptors[i]<0||starts[i]<0||sizes[i]<=0||starts[i]>INT64_MAX-sizes[i])return 0;
        inputs[i]=(CohSessionWorldFd){descriptors[i],(uint64_t)starts[i],(uint64_t)sizes[i]};
    }
    pthread_mutex_lock(&s->mutex);
    if(s->running||s->failed||s->frames||s->contexts_started||s->runtime_world_status){pthread_mutex_unlock(&s->mutex);return 0;}
    s->running=1;pthread_mutex_unlock(&s->mutex);
    Graphics future={0};uint64_t parent=0;
    const Geometry*sets[]={s->world_geometry,s->actor_geometry,s->walkable_geometry};
    const unsigned counts[]={s->world.part_count,s->actor.part_count,s->walkable.part_count};
    for(unsigned set=0;set<3;set++)for(unsigned i=0;i<counts[set];i++){
        uint64_t bytes=(uint64_t)sets[set][i].count*13u*sizeof(float);
        if(bytes>future.tf_bytes)future.tf_bytes=(size_t)bytes;
    }
    CohSessionWorld*candidate=NULL;char reason[128]={0};
    int ok=capture_scene_charge(s,&future,&parent)&&capture_add(&parent,(uint64_t)java_bytes)&&
        capture_add(&parent,(uint64_t)SIZE*SIZE*4u*4u)&&capture_add(&parent,COH_CAPTURE_RESERVE);
    if(ok)ok=coh_session_world_create_fds(s->assets[6].p,s->assets[6].n,inputs,parent,&candidate,reason,sizeof reason);
    else snprintf(reason,sizeof reason,"Runtime source candidate exceeds unchanged scene inventory");
    uint64_t reads=0,read_bytes=0;if(ok)coh_session_world_source_io(candidate,&reads,&read_bytes);
    pthread_mutex_lock(&s->mutex);CohSessionWorld*old=NULL;
    if(ok){old=s->stream_world;s->stream_world=candidate;candidate=NULL;s->runtime_world_reads=reads;s->runtime_world_bytes=read_bytes;memset(&s->stream_stats,0,sizeof s->stream_stats);}
    s->runtime_world_status=ok?1:-1;s->runtime_world_parent_bytes=parent;
    snprintf(s->runtime_world_failure,sizeof s->runtime_world_failure,"%s",reason);
    s->running=0;pthread_mutex_unlock(&s->mutex);
    coh_session_world_destroy(&old);coh_session_world_destroy(&candidate);return ok?1:0;
}
#endif
static int cancelled_surface_error(unsigned code){return code==EGL_BAD_NATIVE_WINDOW||code==EGL_BAD_SURFACE;}
JNIEXPORT jint JNICALL Java_org_coh_sessionclient_SessionNative_render(JNIEnv *e,jclass klass,jlong handle,jobject surface,jlong epoch) {
    (void)klass;Session *s=(Session*)(intptr_t)handle;if(!s||!surface)return -1;Graphics g={.display=EGL_NO_DISPLAY,.surface=EGL_NO_SURFACE,.context=EGL_NO_CONTEXT};uint64_t started=now_ms(),previous=started;
    Session *startup=malloc(sizeof *startup);if(!startup)return -1;
    pthread_mutex_lock(&s->mutex);if(s->running
#if COH_LIVE_COSTUME_DIAGNOSTIC
    ||s->received_preparing
#endif
    ||s->failed||!s->foreground||s->epoch!=(uint64_t)epoch){pthread_mutex_unlock(&s->mutex);free(startup);return 0;}s->cancel=0;s->running=1;s->contexts_started++;*startup=*s;pthread_mutex_unlock(&s->mutex);
    g.window=ANativeWindow_fromSurface(e,surface);if(!g.window)fail(startup,"Native Surface retention failed");else graphics_create(startup,&g);
    if(COH_FULLSCREEN_DIAGNOSTIC)coh_session_world_source_io(startup->stream_world,&startup->runtime_world_reads,&startup->runtime_world_bytes);
    pthread_mutex_lock(&s->mutex);
    /* A destroyed stale Surface is orderly cancellation. Source/GL arithmetic
     * failures stay sticky even if cancellation happened at the same time. */
    if(startup->failed&&startup->surface_failure&&(s->cancel||s->epoch!=(uint64_t)epoch)&&cancelled_surface_error(startup->egl_error)) {
        startup->expected_cancel_surface_errors++;startup->expected_cancel_egl_error=startup->egl_error;
        startup->failed=0;startup->failure[0]=0;startup->egl_error=0;
    }
    startup_commit(s,startup);pthread_mutex_unlock(&s->mutex);previous=now_ms();
    for(;;){pthread_mutex_lock(&s->mutex);if(s->cancel||s->failed){pthread_mutex_unlock(&s->mutex);break;}
        uint64_t current=now_ms();float seconds=bounded((float)(current-previous)/1000,0,.066667f);previous=current;
        s->camera_yaw=wrap(s->camera_yaw+s->look_rate[0]*seconds+s->look_delta[0]);s->camera_pitch=bounded(s->camera_pitch+s->look_rate[1]*seconds+s->look_delta[1],-.5f,.8f);s->look_delta[0]=s->look_delta[1]=0;
        s->accumulator+=seconds;if(s->observed_entity_index)s->accumulator=0;while(s->accumulator>=1.f/30&&!s->failed){s->accumulator-=1.f/30;float old[3];memcpy(old,s->motion.position,sizeof old);
            uint32_t directions=s->held_dirs,previous_bounds=s->walking.bounded_steps;
            if(s->input_edge_count){directions=s->input_edges[s->input_edge_head];s->input_edge_head=(s->input_edge_head+1u)%INPUT_EDGES;s->input_edge_count--;}
            if(!coh_walk_step(&s->walking,&s->walk_world,directions,wrap(s->camera_yaw-PI))){fail(s,"Source grounded WALK movement failed");break;}
            s->motion=s->walking.controls;memcpy(s->motion.position,s->walking.position,sizeof s->motion.position);
            s->walking_ticks++;s->walking_grounded_ticks+=s->walking.grounded;s->walking_blocked_ticks+=s->walking.blocked;s->walking_slide_ticks+=s->walking.sliding;
            s->walking_bounded_ticks+=s->walking.bounded_steps-previous_bounds;
            float dx=s->motion.position[0]-old[0],dz=s->motion.position[2]-old[2],speed=sqrtf(dx*dx+dz*dz);
            if(coh_locomotion_step_directional(&s->locomotion,&s->animation,s->motion.source_state_bits,1,speed,s->morph.geom_scale[1])){fail(s,"Source directional locomotion clock/state failed");break;}
            if(s->animation.move<COH_LOCOMOTION_CLIPS)s->animation_move_samples[s->animation.move]++;
            if(s->animation.move==COH_LOCOMOTION_RUN||s->animation.move==COH_LOCOMOTION_PRE||s->animation.move>=COH_LOCOMOTION_BACK_PRE)s->run_samples++;else s->idle_samples++;
        }
        s->render_dt_frames=seconds*30;if(!s->failed&&!s->observed_entity_index)skin(s);
        *startup=*s;pthread_mutex_unlock(&s->mutex);
        /* No shared session mutex is held by any driver call, including swap,
         * readbacks or context teardown. Main-thread focus/tickets stay live. */
        int surface_failed=0,capture_pending=0,capture_read=0,capture_presented=0;
        if(!startup->failed){for(unsigned i=0;!startup->observed_entity_index&&i<startup->actor.part_count;i++)geometry_upload(&startup->actor_geometry[i],0);EGLint width=0,height=0;
            if(!eglQuerySurface(g.display,g.surface,EGL_WIDTH,&width)||!eglQuerySurface(g.display,g.surface,EGL_HEIGHT,&height)){startup->egl_error=(unsigned)eglGetError();surface_failed=1;}
            else if(width<=0||height<=0||width>16384||height>16384)surface_failed=1;
            else {startup->width=width;startup->height=height;
                uint64_t packets_before=startup->stream_stats.draw_packets,entity_before=startup->observed_entity_draws;
                if(scene_draw(startup,&g,0,width,height,0,0,NULL)){
                    uint64_t packets=startup->stream_stats.draw_packets>=packets_before?startup->stream_stats.draw_packets-packets_before:0;
                    uint64_t entities=startup->observed_entity_draws>=entity_before?startup->observed_entity_draws-entity_before:0;
                    if(COH_FRAME_CAPTURE_DIAGNOSTIC&&startup->observed_entity_index&&packets&&entities
                       &&(!COH_FULLSCREEN_DIAGNOSTIC||(startup->capture_view_epoch==startup->epoch
                           &&startup->capture_view_width==(uint32_t)width&&startup->capture_view_height==(uint32_t)height))
                       &&++startup->capture_draws==COH_CAPTURE_WAIT){
                        uint64_t charge=0;
                        if(capture_scene_charge(startup,&g,&charge)){
                            if(!startup->frame_capture)startup->frame_capture=coh_frame_capture_create(charge);
                            CohFrameCaptureInfo info={(uint32_t)width,(uint32_t)height,startup->observed_entity_index,
                                startup->frames+1,startup->epoch,startup->observed_entity_updates,startup->capture_lock_frame,
                                packets,entities,charge,{startup->observed_entity_position[0],startup->observed_entity_position[1],startup->observed_entity_position[2]}};
                            uint8_t*pixels=NULL;uint32_t cw=0,ch=0;
                            if(coh_frame_capture_begin(startup->frame_capture,&info,&pixels,&cw,&ch)){
                                capture_pending=1;capture_read=coh_frame_capture_readback((uint32_t)width,(uint32_t)height,cw,ch,pixels);
                                startup->capture_charge=charge+COH_CAPTURE_RESERVE;
                            }
                        }
                        if(!capture_pending)startup->capture_failures++;
                    }
                    if(!eglSwapBuffers(g.display,g.surface)){startup->egl_error=(unsigned)eglGetError();surface_failed=1;}
                    else {startup->frames++;capture_presented=1;}
                }
            }
        }
        if(COH_FULLSCREEN_DIAGNOSTIC)coh_session_world_source_io(startup->stream_world,&startup->runtime_world_reads,&startup->runtime_world_bytes);
        pthread_mutex_lock(&s->mutex);
        if(!s->frame_capture)s->frame_capture=startup->frame_capture;
        if(s->observed_entity_updates==startup->observed_entity_updates&&s->observed_entity_index==startup->observed_entity_index){
            s->capture_draws=startup->capture_draws;s->capture_failures=startup->capture_failures;
        }
        if(capture_pending){
            int publish=capture_read&&capture_presented&&!s->cancel&&s->epoch==(uint64_t)epoch&&
                s->observed_entity_updates==startup->observed_entity_updates&&s->observed_entity_index==startup->observed_entity_index;
            coh_frame_capture_publish(startup->frame_capture,publish);
            if(publish){s->capture_frame=startup->frames;s->capture_generation=startup->observed_entity_updates;s->capture_charge=startup->capture_charge;}
            else s->capture_failures++;
        }
        if(surface_failed){
            if((s->cancel||s->epoch!=(uint64_t)epoch)&&cancelled_surface_error(startup->egl_error)){startup->expected_cancel_surface_errors++;startup->expected_cancel_egl_error=startup->egl_error;startup->egl_error=0;}
            else fail(startup,"Session live Surface query/swap failed");
        }
        startup_commit(s,startup);if(s->epoch==(uint64_t)epoch&&!s->cancel)memcpy(s->camera_position,startup->camera_position,sizeof s->camera_position);
        s->total_ms=now_ms()-started;int stopped=s->failed||s->cancel;pthread_mutex_unlock(&s->mutex);if(stopped)break;
        struct timespec sleep={0,1000000};nanosleep(&sleep,NULL);
    }
    pthread_mutex_lock(&s->mutex);*startup=*s;pthread_mutex_unlock(&s->mutex);graphics_delete(startup,&g);
    pthread_mutex_lock(&s->mutex);startup_commit(s,startup);s->running=0;s->contexts_completed++;int result=s->failed?-1:0;pthread_mutex_unlock(&s->mutex);free(startup);return result;
}
static void input_mask(Session *s,uint32_t mask) {
    if(mask!=s->held_dirs){
        if(s->input_edge_count==INPUT_EDGES){fail(s,"Bounded Android control edge queue overflow");return;}
        s->input_edges[(s->input_edge_head+s->input_edge_count)%INPUT_EDGES]=mask;s->input_edge_count++;
    }
    s->held_dirs=mask;s->direction_mask|=mask;
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_input(JNIEnv *e,jclass c,jlong handle,jfloat forward,jfloat strafe,jfloat look_x,jfloat look_y) {
    (void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s||!isfinite(forward)||!isfinite(strafe)||!isfinite(look_x)||!isfinite(look_y))return;
    pthread_mutex_lock(&s->mutex);if(s->foreground){s->forward=bounded(forward,-1,1);s->strafe=bounded(strafe,-1,1);s->look_rate[0]=bounded(look_x,-4,4);s->look_rate[1]=bounded(look_y,-4,4);input_mask(s,(forward>.15f?1u:0)|(forward<-.15f?2u:0)|(strafe<-.15f?4u:0)|(strafe>.15f?8u:0));}pthread_mutex_unlock(&s->mutex);
}
/* Preserve independent source binary directions, including opposing held keys.
 * pmotion resolves their ramp and per-frame tap state rather than Java summing
 * them to a vector before the source control kernel receives them. */
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_controls(JNIEnv *e,jclass c,jlong handle,jint dirs,jfloat look_x,jfloat look_y) {
    (void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s||dirs<0||dirs>15||!isfinite(look_x)||!isfinite(look_y))return;
    pthread_mutex_lock(&s->mutex);if(s->foreground){input_mask(s,(uint32_t)dirs);s->look_rate[0]=bounded(look_x,-4,4);s->look_rate[1]=bounded(look_y,-4,4);}pthread_mutex_unlock(&s->mutex);
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_look(JNIEnv *e,jclass c,jlong handle,jfloat dx,jfloat dy) {
    (void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s||!isfinite(dx)||!isfinite(dy))return;pthread_mutex_lock(&s->mutex);if(s->foreground){s->look_delta[0]+=bounded(dx,-.5f,.5f);s->look_delta[1]+=bounded(dy,-.5f,.5f);}pthread_mutex_unlock(&s->mutex);
}
static void clear_input(Session *s) {s->input_edge_head=s->input_edge_count=0;s->held_dirs=0;s->forward=s->strafe=0;memset(s->look_rate,0,sizeof s->look_rate);memset(s->look_delta,0,sizeof s->look_delta);coh_walk_clear(&s->walking);s->motion=s->walking.controls;memcpy(s->motion.position,s->walking.position,sizeof s->motion.position);}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_observedEntity(JNIEnv*e,jclass c,jlong handle,jint index,jfloat x,jfloat y,jfloat z){
    (void)e;(void)c;Session*s=(Session*)(intptr_t)handle;
    if(!s||index<=0||index>10239||!isfinite(x)||!isfinite(y)||!isfinite(z))return;
    pthread_mutex_lock(&s->mutex);clear_input(s);s->observed_entity_index=(uint32_t)index;
    s->observed_entity_position[0]=x;s->observed_entity_position[1]=y;s->observed_entity_position[2]=z;
    s->observed_entity_updates++;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    s->received_invalidations++;
#endif
    s->capture_lock_frame=s->frames;s->capture_draws=0;s->accumulator=0;pthread_mutex_unlock(&s->mutex);
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_clearObservedEntity(JNIEnv*e,jclass c,jlong handle){
    (void)e;(void)c;Session*s=(Session*)(intptr_t)handle;if(!s)return;
    pthread_mutex_lock(&s->mutex);
#if COH_LIVE_COSTUME_DIAGNOSTIC
    s->received_invalidations++;s->received_pose_updates=0;
#endif
    s->observed_entity_index=0;memset(s->observed_entity_position,0,sizeof s->observed_entity_position);clear_input(s);pthread_mutex_unlock(&s->mutex);
}
/* UI geometry for the current fullscreen Surface only. This controls optional
 * capture timing, never scene/entity admission or transport state. */
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_captureViewport(JNIEnv*e,jclass c,jlong handle,jlong epoch,jint width,jint height){
    (void)e;(void)c;Session*s=(Session*)(intptr_t)handle;
    if(!s||epoch<0||width<0||height<0||width>16384||height>16384)return;
    pthread_mutex_lock(&s->mutex);
    if(s->epoch==(uint64_t)epoch&&(s->capture_view_epoch!=(uint64_t)epoch||s->capture_view_width!=(uint32_t)width||s->capture_view_height!=(uint32_t)height)){
        s->capture_view_epoch=(uint64_t)epoch;s->capture_view_width=(uint32_t)width;s->capture_view_height=(uint32_t)height;
        s->capture_lock_frame=s->frames;s->capture_draws=0;
    }
    pthread_mutex_unlock(&s->mutex);
}
JNIEXPORT jbyteArray JNICALL Java_org_coh_sessionclient_SessionNative_frameCapture(JNIEnv*e,jclass c,jlong handle,jlong after){
    (void)c;Session*s=(Session*)(intptr_t)handle;if(!s||after<0)return NULL;
    uint8_t*copy=malloc(COH_CAPTURE_BYTES);if(!copy)return NULL;size_t size=0;
    pthread_mutex_lock(&s->mutex);const uint8_t*raw=coh_frame_capture_data(s->frame_capture,&size,(uint64_t)after);
    if(raw&&size<=COH_CAPTURE_BYTES)memcpy(copy,raw,size);else size=0;
    pthread_mutex_unlock(&s->mutex);
    jbyteArray out=size?(*e)->NewByteArray(e,(jsize)size):NULL;
    if(out)(*e)->SetByteArrayRegion(e,out,0,(jsize)size,(const jbyte*)copy);
    free(copy);return out;
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_viewDistance(JNIEnv *e,jclass c,jlong handle) {
    (void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;
    pthread_mutex_lock(&s->mutex);s->view_radius=s->view_radius<60?96:24;pthread_mutex_unlock(&s->mutex);
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_focus(JNIEnv *e,jclass c,jlong handle) {(void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;pthread_mutex_lock(&s->mutex);clear_input(s);pthread_mutex_unlock(&s->mutex);}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_cancel(JNIEnv *e,jclass c,jlong handle) {(void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;pthread_mutex_lock(&s->mutex);s->cancel=1;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    s->received_invalidations++;
#endif
    clear_input(s);pthread_mutex_unlock(&s->mutex);}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_state(JNIEnv *e,jclass c,jlong handle,jlong epoch,jboolean foreground) {(void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;pthread_mutex_lock(&s->mutex);s->epoch=(uint64_t)epoch;s->foreground=foreground?1:0;s->cancel=1;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    s->received_invalidations++;
#endif
    clear_input(s);pthread_mutex_unlock(&s->mutex);}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_reset(JNIEnv *e,jclass c,jlong handle) {(void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;pthread_mutex_lock(&s->mutex);clear_input(s);s->camera_yaw=wrap(s->walkable.spawn_yaw+PI);s->camera_pitch=.16f;if(!coh_walk_init(&s->walking,&s->walk_world,s->spawn,s->walkable.spawn_yaw))fail(s,"Authored ground reset failed");s->motion=s->walking.controls;memcpy(s->motion.position,s->walking.position,sizeof s->motion.position);coh_locomotion_init(&s->animation);coh_locomotion_blend_init(&s->blend);s->accumulator=0;pthread_mutex_unlock(&s->mutex);}
static void escaped(char *out,size_t capacity,const char *in) {size_t n=0;for(const unsigned char *p=(const unsigned char*)in;*p&&n+7<capacity;p++){if(*p=='"'||*p=='\\'){out[n++]='\\';out[n++]=(char)*p;}else if(*p<32||*p>=127){int used=snprintf(out+n,capacity-n,"\\u%04x",*p);n+=(size_t)used;}else out[n++]=(char)*p;}out[n]=0;}
typedef struct {char *p;size_t n;int ok;} Json;
static void jappend(Json *j,const char *format,...) __attribute__((format(printf,2,3)));
static void jappend(Json *j,const char *format,...) {if(!j->ok)return;va_list args;va_start(args,format);int n=vsnprintf(j->p+j->n,JSON_CAP-j->n,format,args);va_end(args);if(n<0||(size_t)n>=JSON_CAP-j->n){j->ok=0;return;}j->n+=(size_t)n;}
static void depth_json(Json *j,const DepthDiagnostic *d,int colors) {
    jappend(j,"{\"x\":%u,\"y\":%u,\"world_depth\":%u,\"actor_depth\":%u,\"combined_depth\":%u",d->x,d->y,d->world_depth,d->actor_depth,d->combined_depth);
    if(colors){const uint8_t *rgba[4]={d->world,d->actor,d->forward,d->reverse};const char *names[4]={"world_rgba","actor_rgba","forward_rgba","reverse_rgba"};for(unsigned i=0;i<4;i++)jappend(j,",\"%s\":[%u,%u,%u,%u]",names[i],rgba[i][0],rgba[i][1],rgba[i][2],rgba[i][3]);}jappend(j,"}");
}
JNIEXPORT jstring JNICALL Java_org_coh_sessionclient_SessionNative_snapshot(JNIEnv *e,jclass c,jlong handle) {
    (void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return (*e)->NewStringUTF(e,"{\"valid\":false}");char json[JSON_CAP],failure[1024],renderer[512];pthread_mutex_lock(&s->mutex);escaped(failure,sizeof failure,s->failure);escaped(renderer,sizeof renderer,s->gl_renderer);
    int n=snprintf(json,sizeof json,"{\"schema\":1,\"probe\":\"coh-native-offline-session\",\"valid\":%s,\"failed\":%s,\"running\":%s,\"failure\":\"%s\",\"pointer_bytes\":%zu,\"source_controlled\":true,\"collision\":true,\"live_server\":false,\"full_atlas\":false,\"gpu_palette_skinning\":false,\"skin_policy\":\"accepted source CPU skin then accepted world shader\",\"frames\":%"PRIu64",\"world_draws\":%"PRIu64",\"actor_draws\":%"PRIu64",\"skin_samples\":%"PRIu64",\"contexts_started\":%"PRIu64",\"contexts_completed\":%"PRIu64",\"objects_released\":%s,\"width\":%d,\"height\":%d,\"gl_renderer\":\"%s\",\"gl_errors\":%u,\"egl_error\":%u,\"shader_language_version\":%u,\"shader_precise\":%s,\"tf_components\":%"PRIu64",\"tf_mismatches\":%"PRIu64",\"tf_max_error\":%.9g,\"depth_order_mismatches\":%"PRIu64",\"world_visible_pixels\":%"PRIu64",\"actor_visible_pixels\":%"PRIu64",\"world_occludes_actor_pixels\":%"PRIu64",\"actor_occludes_world_pixels\":%"PRIu64",\"actor_changed_pixels\":%"PRIu64",\"startup_checked\":%s,\"movement_ticks\":%"PRIu64",\"direction_mask\":%u,\"held_dirs\":%u,\"actor_position\":[%.9g,%.9g,%.9g],\"spawn_position\":[%.9g,%.9g,%.9g],\"actor_yaw\":%.9g,\"camera_yaw\":%.9g,\"camera_pitch\":%.9g,\"camera_position\":[%.9g,%.9g,%.9g],\"animation_frame\":%.9g,\"animation_state\":%u,\"animation_transitions\":%u,\"idle_samples\":%"PRIu64",\"run_samples\":%"PRIu64",\"total_ms\":%"PRIu64"}",
        s->valid?"true":"false",s->failed?"true":"false",s->running?"true":"false",failure,sizeof(void*),s->frames,s->world_draws,s->actor_draws,s->skin_samples,s->contexts_started,s->contexts_completed,s->objects_released?"true":"false",s->width,s->height,renderer,s->gl_errors,s->egl_error,s->shader_version,s->precise?"true":"false",s->tf_components,s->tf_mismatches,s->tf_max_error,s->depth_order_mismatches,s->world_visible_pixels,s->actor_visible_pixels,s->world_occludes_actor_pixels,s->actor_occludes_world_pixels,s->actor_changed_pixels,s->startup_checked?"true":"false",(uint64_t)s->walking_ticks,s->direction_mask,s->held_dirs,s->motion.position[0],s->motion.position[1],s->motion.position[2],s->spawn[0],s->spawn[1],s->spawn[2],s->motion.body_yaw,s->camera_yaw,s->camera_pitch,s->camera_position[0],s->camera_position[1],s->camera_position[2],s->animation.frame,(unsigned)s->animation.move,(unsigned)s->animation.transitions,s->idle_samples,s->run_samples,s->total_ms);
    if(n>0&&(size_t)n<sizeof json){int extra=snprintf(json+n-1,sizeof json-(size_t)n+1,
        ",\"epoch\":%"PRIu64",\"foreground\":%s,\"expected_cancel_surface_errors\":%u,\"expected_cancel_egl_error\":%u,\"cleanup_gl_errors\":%u,\"cleanup_egl_errors\":%u,\"cleanup_egl_error\":%u,\"source_state_bits\":%u,\"motion_local\":[%.9g,%.9g,%.9g],\"motion_world\":[%.9g,%.9g,%.9g],\"nocoll_radius\":%.9g,\"bounded_steps\":%u,\"stopped_steps\":%u,\"animation_move\":\"%s\",\"animation_rate\":%.9g,\"ready_entries\":%u,\"run_entries\":%u,\"post_entries\":%u,\"animation_cycles\":%u,\"sampler\":\"GL_LINEAR CLAMP_TO_EDGE base level only\",\"depth_witness_scope\":\"actual source meshes; opaque order reversed with Hair always last; four startup images only\"}",
        s->epoch,s->foreground?"true":"false",s->expected_cancel_surface_errors,s->expected_cancel_egl_error,s->cleanup_gl_errors,s->cleanup_egl_errors,s->cleanup_egl_error,s->motion.source_state_bits,s->motion.local_input[0],s->motion.local_input[1],s->motion.local_input[2],s->motion.world_input[0],s->motion.world_input[1],s->motion.world_input[2],s->motion.radius,s->motion.bounded_steps,s->motion.stopped_steps,coh_locomotion_move_name(s->animation.move),s->animation.move_rate_scale,s->animation.ready_entries,s->animation.run_entries,s->animation.post_entries,s->animation.cycles);
        if(extra<0||(size_t)extra>=sizeof json-(size_t)n+1)n=-1;else n=n-1+extra;
    }
    if(n>0&&(size_t)n<sizeof json){Json j={json,(size_t)n-1,1};
        jappend(&j,",\"walkable_draws\":%"PRIu64",\"input_pending_edges\":%u,\"walk\":{\"grounded\":%s,\"ground_y\":%.9g,\"ground_hits\":%"PRIu64",\"blocked_ticks\":%"PRIu64",\"sliding_ticks\":%"PRIu64",\"bounded_ticks\":%"PRIu64",\"collision_queries\":%u,\"triangle_tests\":%u,\"triangles\":%u,\"bounded_scene\":true,\"spawn_yaw\":%.9g,\"obstacle_bounds_min\":[%.9g,%.9g,%.9g],\"obstacle_bounds_max\":[%.9g,%.9g,%.9g]}",s->walkable_draws,s->input_edge_count,s->walking.grounded?"true":"false",s->motion.position[1],s->walking_grounded_ticks,s->walking_blocked_ticks,s->walking_slide_ticks,s->walking_bounded_ticks,s->walking.collision_queries,s->walking.triangle_tests,s->walk_world.triangle_count,s->walkable.spawn_yaw,s->obstacle_min[0],s->obstacle_min[1],s->obstacle_min[2],s->obstacle_max[0],s->obstacle_max[1],s->obstacle_max[2]);
        jappend(&j,",\"walkable_tf_components\":%"PRIu64",\"walkable_tf_mismatches\":%"PRIu64",\"walkable_visible_pixels\":%"PRIu64",\"animation_move_samples\":[",s->walkable_tf_components,s->walkable_tf_mismatches,s->walkable_visible_pixels);
        for(unsigned i=0;i<COH_LOCOMOTION_CLIPS;i++)jappend(&j,"%s%"PRIu64,i?",":"",s->animation_move_samples[i]);jappend(&j,"]");
        jappend(&j,",\"walk_contact_hits\":%u,\"walk_wall_hits\":%u,\"walk_ground_hits\":%u",s->walking.contact_hits,s->walking.wall_hits,s->walking.ground_hits);
        uint64_t box_draws=s->observed_entity_draws;
#if COH_LIVE_COSTUME_DIAGNOSTIC
        box_draws=box_draws>=s->received_frames?box_draws-s->received_frames:0;
#endif
        jappend(&j,",\"observed_server_entity\":{\"active\":%s,\"entity_index\":%u,\"position\":[%.9g,%.9g,%.9g],\"updates\":%"PRIu64",\"box_draws\":%"PRIu64",\"visual\":\"orange diagnostic box at decoded server coordinate\",\"complete_actor\":false",s->observed_entity_index?"true":"false",s->observed_entity_index,s->observed_entity_position[0],s->observed_entity_position[1],s->observed_entity_position[2],s->observed_entity_updates,box_draws);
        if(COH_FULLSCREEN_DIAGNOSTIC)jappend(&j,",\"renderer_sends_application_ack\":false,\"transport_send_facts\":\"server_protocol.initial_continuation\"}");
        else jappend(&j,",\"application_ack\":false}");
        const CohSessionWorldStats *t=&s->stream_stats;
        jappend(&j,",\"stream\":{\"catalog_instances\":%"PRIu64",\"selected_instances\":%"PRIu64",\"resident_bytes\":%"PRIu64",\"budget_bytes\":%"PRIu64",\"peak_resident_bytes\":%"PRIu64",\"selection_updates\":%"PRIu64",\"cache_hits\":%"PRIu64",\"cache_misses\":%"PRIu64",\"evictions\":%"PRIu64",\"generation\":%u,\"draws\":%"PRIu64",\"view_radius\":%.9g}",t->catalog_instances,t->selected_instances,t->resident_bytes,t->budget_bytes,t->peak_resident_bytes,t->selection_updates,t->cache_hits,t->cache_misses,t->evictions,t->generation,t->draws,t->view_radius);
        jappend(&j,",\"source_assets\":{\"geo_loads\":%"PRIu64",\"texture_loads\":%"PRIu64",\"errors\":%"PRIu64"},\"static_renderer\":{\"draw_packets\":%"PRIu64",\"tf_components\":%"PRIu64",\"tf_mismatches\":%"PRIu64",\"visible_pixels\":%"PRIu64",\"material_mode_mask\":%u,\"owned_cpu_bytes\":%"PRIu64",\"gpu_bytes\":%"PRIu64",\"tf_max_error\":%.9g}",t->geo_loads,t->texture_loads,t->errors,t->draw_packets,t->tf_components,t->tf_mismatches,t->visible_pixels,t->material_mode_mask,t->owned_cpu_bytes,t->gpu_bytes,t->tf_max_error);
        jappend(&j,",\"depth_sampler_controls_passed\":%s,\"depth_codec_float_precision\":%d,\"raw_changed_pixels\":%"PRIu64",\"qualified_equal_depth_ties\":%"PRIu64",\"non_tie_mismatches\":%"PRIu64",\"depth_sampler_controls\":{\"clear\":",s->depth_sampler_controls_passed?"true":"false",s->depth_codec_float_precision,s->depth_order_color_differences,s->depth_order_ties,s->depth_order_mismatches);
        depth_json(&j,&s->clear_control,0);jappend(&j,",\"world_front\":");depth_json(&j,&s->world_front_control,0);jappend(&j,",\"actor_front\":");depth_json(&j,&s->actor_front_control,0);jappend(&j,"},\"depth_tie_diagnostics\":[");
        for(unsigned i=0;i<s->depth_diagnostics_count;i++){if(i)jappend(&j,",");depth_json(&j,&s->depth_diagnostics[i],1);}jappend(&j,"]");
        if(COH_FULLSCREEN_DIAGNOSTIC){char reason[256];escaped(reason,sizeof reason,s->runtime_world_failure);jappend(&j,",\"runtime_world\":{\"status\":%d,\"source\":\"%s\",\"parent_reservation_bytes\":%"PRIu64",\"archive_reads\":%"PRIu64",\"archive_bytes\":%"PRIu64",\"fallback_reason\":\"%s\"}",s->runtime_world_status,s->runtime_world_status==1?"verified_imported_archives":"accepted_fixture_fallback",s->runtime_world_parent_bytes,s->runtime_world_reads,s->runtime_world_bytes,reason);}
#if COH_LIVE_COSTUME_DIAGNOSTIC
        {char missing[512];escaped(missing,sizeof missing,s->received_stats.missing);
        int current=s->received_actor&&s->received_pose_updates==s->observed_entity_updates&&s->received_stats.entity_index==s->observed_entity_index;
        jappend(&j,",\"received_actor\":{\"kind\":\"%s\",\"status\":%d,\"preparing\":%s,\"entity_index\":%u,\"parts\":%u,\"frames\":%"PRIu64",\"draws\":%"PRIu64",\"cpu_bytes\":%"PRIu64",\"gpu_reserved_bytes\":%"PRIu64",\"prepare_peak_bytes\":%"PRIu64",\"source_retained_bytes\":%"PRIu64",\"height_scale\":%.9g,\"automatic_material_fallbacks\":%u,\"quality\":\"original_noMULTI_noBUMP_DUAL; LINEAR_REPEAT_noMip; Ready_base_inspection\",\"missing_asset\":\"%s\"}",current&&s->received_last_draw?"received_huge":"box",s->received_status,s->received_preparing?"true":"false",s->received_stats.entity_index,s->received_stats.parts,s->received_frames,s->received_draws,s->received_stats.cpu_bytes,s->received_stats.gpu_reserve_bytes,s->received_stats.prepare_peak_bytes,s->received_source_bytes,s->received_stats.height_scale,s->received_stats.material_fallbacks,missing);}
#endif
        if(COH_FRAME_CAPTURE_DIAGNOSTIC)jappend(&j,",\"frame_capture\":{\"frame\":%"PRIu64",\"pose_generation\":%"PRIu64",\"source_charge_bytes\":%"PRIu64",\"reserve_bytes\":%u,\"failures\":%"PRIu64",\"startup_witness\":false}",s->capture_frame,s->capture_generation,s->capture_charge,COH_CAPTURE_RESERVE,s->capture_failures);
        jappend(&j,"}");n=j.ok?(int)j.n:-1;
    }
    pthread_mutex_unlock(&s->mutex);if(n<0||(size_t)n>=sizeof json)return (*e)->NewStringUTF(e,"{\"valid\":false,\"failure\":\"Native snapshot capacity exceeded\"}");return (*e)->NewStringUTF(e,json);
}
JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_destroy(JNIEnv *e,jclass c,jlong handle) {(void)e;(void)c;Session *s=(Session*)(intptr_t)handle;if(!s)return;pthread_mutex_lock(&s->mutex);int running=s->running;
#if COH_LIVE_COSTUME_DIAGNOSTIC
    running|=s->received_preparing;s->received_invalidations++;
#endif
    s->cancel=1;pthread_mutex_unlock(&s->mutex);if(!running)session_free(s);}
