#!/usr/bin/env python3
"""Execute exact shipped marker setter/camera/draw bodies with GL call observers."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];NATIVE=ROOT/'native-android'
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(command,**kw):
 r=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kw)
 if r.returncode:raise RuntimeError(r.stdout[-2000:]+r.stderr[-4000:])
 return r.stdout
HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include "coh_world.h"
#include "coh_debug_entity.h"
#include "session_stream_world.h"
#define PI 3.14159265358979323846f
#define JNIEXPORT
#define JNICALL
typedef void JNIEnv;typedef void*jclass;typedef int64_t jlong;typedef int32_t jint;typedef float jfloat;typedef unsigned GLuint;
typedef struct {pthread_mutex_t mutex;struct{CohWorldInputs inputs;}world;struct{float position[3],body_yaw;}motion;float camera_yaw,camera_pitch,camera_target_height,camera_position[3],view_radius,accumulator;uint32_t observed_entity_index;float observed_entity_position[3];uint64_t observed_entity_updates,observed_entity_draws,capture_lock_frame,capture_draws,frames;CohSessionWorld*stream_world;CohSessionWorldStats stream_stats;char failure[512];int failed;}Session;
typedef struct{int unused;}Graphics;
static unsigned checks,actor_calls,observed_queries,offline_queries,marker_calls,input_clears;
static float queried[3];static uint32_t drawn_index;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"session observed line%d %s\n",__LINE__,#x);exit(1);}}while(0)
static int fail(Session*s,const char*why){s->failed=1;(void)why;return 0;}
static int glcheck(Session*s,const char*where){(void)s;(void)where;return 1;}
static void clear_input(Session*s){(void)s;input_clears++;}
#define glBindFramebuffer(...) ((void)0)
#define glViewport(...) ((void)0)
#define glEnable(...) ((void)0)
#define glDepthMask(...) ((void)0)
#define glDepthFunc(...) ((void)0)
#define glClearDepthf(...) ((void)0)
#define glClearColor(...) ((void)0)
#define glClear(...) ((void)0)
#define glFrontFace(...) ((void)0)
#define glCullFace(...) ((void)0)
#define glDisable(...) ((void)0)
#define glReadPixels(...) ((void)0)
static void draw_actor(Session*s,Graphics*g,const float*m,const float*eye,const float*p,int alpha){(void)s;(void)g;(void)m;(void)eye;(void)p;(void)alpha;actor_calls++;}
static void draw_world(Session*s,Graphics*g,float eye[6][12],const float*p){(void)s;(void)g;(void)eye;(void)p;}
int coh_session_world_draw(CohSessionWorld*w,const float v[12],const float p[16],const float c[3],float r,CohSessionWorldStats*out,char*e,size_t cap){(void)w;(void)v;(void)p;(void)r;(void)out;(void)e;(void)cap;offline_queries++;memcpy(queried,c,sizeof queried);return 1;}
int coh_session_world_draw_observed(CohSessionWorld*w,const float v[12],const float p[16],const float c[3],float r,CohSessionWorldStats*out,char*e,size_t cap){(void)w;(void)v;(void)p;(void)r;(void)out;(void)e;(void)cap;observed_queries++;memcpy(queried,c,sizeof queried);return 1;}
int coh_session_world_observed_entity(CohSessionWorld*w,const float v[12],const float p[16],uint32_t index,const float position[3],CohSessionWorldStats*out,char*e,size_t cap){(void)w;(void)out;(void)e;(void)cap;CohInitialPoseSample sample={.position={position[0],position[1],position[2]},.valid=1};float gl[16];coh_world_gl_matrix(v,gl);CohRenderDraw d;CohRenderTexture white={73,COH_WRAP_CLAMP,COH_WRAP_CLAMP,COH_FILTER_NEAREST,COH_FILTER_NEAREST};CHECK(coh_debug_entity_draw(&sample,index,gl,p,white,&d)==COH_OK);marker_calls++;drawn_index=index;return 1;}
/*SHIPPED*/
static uint32_t word(FILE*f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
int main(int argc,char**argv){CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f&&word(f)==91);uint32_t row[18];for(unsigned i=0;i<18;i++)row[i]=word(f);uint8_t*wire=malloc(row[0]);CHECK(wire&&fread(wire,1,row[0],f)==row[0]);CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,row[0]},row[1],(int)row[2],COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[8];CohInitialPoseProbe probe;CohInitialPoseSample sample;CHECK(coh_initial_pose_probe_with_sample(&reader,row[5],&probe,&sample)!=COH_OK&&sample.valid);
 Session s={0};CHECK(!pthread_mutex_init(&s.mutex,NULL));for(unsigned i=0;i<6;i++)s.world.inputs.nodes[i].parent=i?i-1:UINT32_MAX;s.world.inputs.cameras[0].aspect=1;s.camera_pitch=.16f;s.camera_target_height=3.8f;s.view_radius=24;s.motion.position[0]=999;s.motion.position[1]=888;s.motion.position[2]=777;Graphics g={0};jlong handle=(jlong)(intptr_t)&s;
 Java_org_coh_sessionclient_SessionNative_observedEntity(NULL,NULL,handle,17,sample.position.x,sample.position.y,sample.position.z);CHECK(s.observed_entity_index==17&&s.observed_entity_updates==1&&!memcmp(s.observed_entity_position,&sample.position,sizeof sample.position)&&input_clears==1);CHECK(scene_draw(&s,&g,0,1280,720,0,0,NULL));CHECK(marker_calls==1&&s.observed_entity_draws==1&&drawn_index==17&&observed_queries==1&&!offline_queries&&!actor_calls&&!memcmp(queried,&sample.position,sizeof sample.position));
 CHECK(s.camera_position[0]==sample.position.x);CHECK(fabsf(s.camera_position[1]-(sample.position.y+3.8f+22*sinf(.16f)))<.02f);CHECK(fabsf(s.camera_position[2]-(sample.position.z+22*cosf(.16f)))<.02f);CHECK(s.motion.position[0]==999&&s.motion.position[1]==888&&s.motion.position[2]==777);
 Java_org_coh_sessionclient_SessionNative_observedEntity(NULL,NULL,handle,0,1,2,3);Java_org_coh_sessionclient_SessionNative_observedEntity(NULL,NULL,handle,18,NAN,2,3);CHECK(s.observed_entity_index==17&&s.observed_entity_updates==1&&!memcmp(s.observed_entity_position,&sample.position,sizeof sample.position));
 for(unsigned i=0;i<32;i++){CHECK(scene_draw(&s,&g,0,1280,720,0,i&1,NULL));CHECK(!actor_calls&&!memcmp(queried,&sample.position,sizeof sample.position));}CHECK(marker_calls==33&&s.observed_entity_draws==33);
 Java_org_coh_sessionclient_SessionNative_clearObservedEntity(NULL,NULL,handle);CHECK(!s.observed_entity_index&&input_clears==2);CHECK(scene_draw(&s,&g,0,1280,720,0,0,NULL)&&offline_queries==1&&actor_calls==2&&marker_calls==33&&queried[0]==999&&queried[1]==888&&queried[2]==777);
 CHECK(!pthread_mutex_destroy(&s.mutex));free(wire);CHECK(!fclose(f));printf("{\"passed\":true,\"checks\":%u,\"observed_box_draws\":%u,\"actual_decoded_coordinate_preserved\":true,\"offline_actor_suppressed\":true,\"camera_and_query_center_on_server_sample\":true,\"clear_restores_offline_preview\":true,\"GL_calls_observed_not_executed\":true}\n",checks,marker_calls);return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();work=a.work.resolve()
 if work.exists():p.error('Fresh external work directory required')
 work.mkdir(parents=True);runtime=NATIVE/'session-client/app/src/main/cpp/session_renderer.c';text=runtime.read_text();extract=module('source_session_extract',HERE/'lifecycle_host_check.py').method
 signatures=['static void multiply(const float *a,const float *b,float *c)','static void actor_matrix(const Session *s,float *m)','static const float* scene_center(const Session*s)','static int camera(Session *s,float aspect,float *view,float *projection,float *actor,float *actor_eye,float eye[6][12])','static int scene_draw(Session *s,Graphics *g,GLuint fbo,int width,int height,int mode,int reverse,uint8_t *image)','JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_observedEntity(JNIEnv*e,jclass c,jlong handle,jint index,jfloat x,jfloat y,jfloat z)','JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_clearObservedEntity(JNIEnv*e,jclass c,jlong handle)']
 bodies={name:extract(text,name) for name in signatures};source=work/'session-marker.c';source.write_text(HARNESS.replace('/*SHIPPED*/','\n'.join(bodies.values())))
 inputs=[runtime,Path(__file__),HERE/'lifecycle_host_check.py',NATIVE/'world/coh_world.c',NATIVE/'engine/renderer/coh_debug_entity.c',NATIVE/'engine/renderer/coh_renderer.c',NATIVE/'engine/initial-capture/coh_initial_pose_probe.c',NATIVE/'engine/replication/coh_replication.c',NATIVE/'engine/entities/coh_entities.c'];pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};modes={};same=None
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  worldobj=work/(mode+'-world.o');run(['cc','-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off',*flags,'-c',inputs[3],'-o',worldobj])
  binary=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,'-I'+str(NATIVE/'world'),'-I'+str(NATIVE/'engine/renderer'),'-I'+str(runtime.parent),source,*inputs[4:],worldobj,'-lm','-pthread','-o',binary]);out=run([binary,a.fixtures],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));checks=json.loads(out)
  if same is None:same=checks
  else:assert same==checks
  modes[mode]={'checks':checks,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()};print(json.dumps({'mode':mode,**checks}),flush=True)
 assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
 receipt={'passed':True,'modes':modes,'source_sha256':pins,'shipped_body_sha256':{name:hashlib.sha256(body.encode()).hexdigest() for name,body in bodies.items()},'generated_harness_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'fixtures_sha256':hashlib.sha256(a.fixtures.read_bytes()).hexdigest(),'observer_scope':'Exact production setter/camera/draw bodies, actual source camera and decoded-pose helpers; explicit storage/JNI/input/GL/stream call observers, not full Android ABI or GLES execution','Android_or_actual_server_execution':False,'leak_sanitizer':False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
if __name__=='__main__':main()
