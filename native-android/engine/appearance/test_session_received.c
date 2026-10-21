/* Exact Session setter with explicit host JNI/world/actor/GPU doubles.
 * The actor double has 13 parts; this is NOT a source-geometry rendering proof. */
#define COH_LIVE_COSTUME_DIAGNOSTIC 1
#define COH_FULLSCREEN_DIAGNOSTIC 1
#define COH_FRAME_CAPTURE_DIAGNOSTIC 1
#include "../../session-client/app/src/main/cpp/session_renderer.c"
#include <errno.h>
#include <dirent.h>
#include <stdatomic.h>
#include <sched.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

static unsigned checks;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
static size_t alloc_calls,alloc_fail,alloc_live;
void *__wrap_malloc(size_t n){if(++alloc_calls==alloc_fail)return NULL;void*p=__real_malloc(n);if(p)alloc_live++;return p;}
void *__wrap_calloc(size_t n,size_t z){if(++alloc_calls==alloc_fail)return NULL;void*p=__real_calloc(n,z);if(p)alloc_live++;return p;}
void __wrap_free(void*p){if(p){CHECK(alloc_live>0);alloc_live--;}__real_free(p);}

struct CohReceivedCostume {CohReceivedCostumeStats stats;};
static uint64_t world_cpu=4096,world_gpu=8192,world_parent,captured_parent;
static unsigned prepare_calls,owner_destroys,parent_calls,parent_fail,prepare_fail,fd_reads;
static Session *active;static unsigned action,action_at;static int exception_flag;
static uint64_t expected_epoch;static uint64_t gpu_draws;
static int mutex_was_held;static pthread_t cancelling_thread;static int cancel_at_parent;static atomic_int cancel_started;
static void *cancel_thread(void*unused){(void)unused;atomic_store(&cancel_started,1);Java_org_coh_sessionclient_SessionNative_cancel(NULL,NULL,(jlong)(intptr_t)active);return NULL;}
static unsigned fds_open(void){DIR*d=opendir("/proc/self/fd");CHECK(d!=NULL);unsigned n=0;struct dirent*e;while((e=readdir(d)))if(strcmp(e->d_name,".")&&strcmp(e->d_name,".."))n++;closedir(d);return n;}
static unsigned initial_fds;
static void mutate(void);
int coh_session_world_owned_bytes(const CohSessionWorld*w,uint64_t*c,uint64_t*g){(void)w;*c=world_cpu;*g=world_gpu;return 1;}
int coh_session_world_parent_bytes(CohSessionWorld*w,uint64_t n,char*error,size_t cap){
 (void)w;parent_calls++;int rc=pthread_mutex_trylock(&active->mutex);mutex_was_held=rc==EBUSY;if(!rc)pthread_mutex_unlock(&active->mutex);
 if(parent_fail){snprintf(error,cap,"test world parent refusal");return 0;}
 if(cancel_at_parent){atomic_store(&cancel_started,0);CHECK(!pthread_create(&cancelling_thread,NULL,cancel_thread,NULL));while(!atomic_load(&cancel_started))sched_yield();CHECK(mutex_was_held);}
 world_parent=n;return 1;
}
size_t coh_walk_world_owned_bytes(const CohWalkWorld*w){(void)w;return 1024;}
void coh_walk_clear(CohWalkState*w){(void)w;}
const char *coh_locomotion_move_name(unsigned m){(void)m;return "test";}
uint32_t coh_frame_capture_reserve_bytes(void){return 1u<<20;}
CohStatus coh_received_costume_prepare(const CohReceivedCostumeInputs*in,CohReceivedCostume**out,CohReceivedCostumeStats*stats){
 prepare_calls++;captured_parent=in->parent_bytes;CHECK(!*out);CHECK(in->source_epoch==expected_epoch);
 unsigned char byte=0;CohStatus r=in->archives[0].read_at(in->archives[0].context,0,&byte,1);fd_reads++;if(r)return r;
 if(action_at==2)mutate();if(in->cancel.poll&&in->cancel.poll(in->cancel.context))return COH_CANCELLED;
 if(prepare_fail)return COH_UNSUPPORTED;
 const uint64_t cpu=100u<<10,gpu=200u<<10,backend=4096;
 if(in->parent_bytes>COH_RECEIVED_COSTUME_LIMIT-cpu-gpu-backend-COH_RECEIVED_COSTUME_STACK)return COH_LIMIT;
 CohReceivedCostume*a=calloc(1,sizeof*a);if(!a)return COH_LIMIT;
 a->stats=(CohReceivedCostumeStats){.cpu_bytes=cpu,.gpu_reserve_bytes=gpu,.renderer_cpu_reserve_bytes=backend,.source_epoch=in->source_epoch,.entity_index=in->entity_index,.bodytype=4,.parts=13,.vertices=3,.indices=3,.textures=0,.height_scale=1.0497f};
 a->stats.prepare_peak_bytes=in->parent_bytes+cpu+gpu+backend+COH_RECEIVED_COSTUME_STACK;*stats=a->stats;*out=a;return COH_OK;
}
void coh_received_costume_destroy(CohReceivedCostume**p){if(p&&*p){owner_destroys++;free(*p);*p=NULL;}}
CohStatus coh_received_costume_texture(const CohReceivedCostume*a,uint32_t i,CohBytes*b,uint32_t*w,uint32_t*h,const char**n){(void)a;(void)i;(void)b;(void)w;(void)h;(void)n;return COH_INVALID;}
CohStatus coh_received_costume_bind(CohReceivedCostume*a,uint32_t g,const uint32_t*h,uint32_t n){(void)a;(void)g;(void)h;(void)n;return COH_OK;}
CohStatus coh_received_costume_draws(CohReceivedCostume*a,const float v[12],const float p[16],const float pos[3],const CohRenderDraw**out,size_t*n){(void)a;(void)v;(void)p;(void)pos;static CohRenderDraw draws[13];*out=draws;*n=13;return COH_OK;}
struct CohGlesRenderer {unsigned dummy;};struct CohRenderer {unsigned dummy;};
static struct CohGlesRenderer fake_gles;static struct CohRenderer fake_renderer;
static unsigned gpu_fail;
CohStatus coh_renderer_gles_create(size_t v,size_t i,CohGlesRenderer**o,CohRenderBackend*b){(void)v;(void)i;memset(b,0,sizeof*b);if(gpu_fail)return COH_LIMIT;*o=&fake_gles;return COH_OK;}
CohStatus coh_renderer_create(const CohRendererConfig*c,const CohRenderBackend*b,CohRenderer**o){(void)c;(void)b;*o=&fake_renderer;return COH_OK;}
void coh_renderer_surface_lost(CohRenderer*r,uint32_t g,int a){(void)r;(void)g;(void)a;}
void coh_renderer_destroy(CohRenderer*r){(void)r;}
void coh_renderer_gles_destroy(CohGlesRenderer*r,int a){(void)r;(void)a;}
CohStatus coh_renderer_begin(CohRenderer*r,uint32_t g){(void)r;(void)g;return COH_OK;}
CohStatus coh_renderer_submit(CohRenderer*r,const CohRenderDraw*d){(void)r;(void)d;gpu_draws++;return COH_OK;}
CohStatus coh_renderer_flush(CohRenderer*r,CohCancel c){(void)r;(void)c;return COH_OK;}
void GL_APIENTRY glGenTextures(GLsizei n,GLuint*t){for(GLsizei i=0;i<n;i++)t[i]=(GLuint)i+1;}
void GL_APIENTRY glBindTexture(GLenum t,GLuint v){(void)t;(void)v;}
void GL_APIENTRY glTexImage2D(GLenum t,GLint l,GLint i,GLsizei w,GLsizei h,GLint b,GLenum f,GLenum ty,const void*p){(void)t;(void)l;(void)i;(void)w;(void)h;(void)b;(void)f;(void)ty;(void)p;}
void GL_APIENTRY glTexParameteri(GLenum t,GLenum p,GLint v){(void)t;(void)p;(void)v;}
GLenum GL_APIENTRY glGetError(void){return GL_NO_ERROR;}
void GL_APIENTRY glDeleteTextures(GLsizei n,const GLuint*t){(void)n;(void)t;}

typedef struct {jsize size;void*data;} Array;
static char json[JSON_CAP];
static jsize length(JNIEnv*e,jbyteArray a){(void)e;return ((Array*)a)->size;}
static void bytes(JNIEnv*e,jbyteArray a,jsize start,jsize n,jbyte*out){(void)e;Array*x=a;CHECK(start>=0&&n>=0&&start<=x->size&&n<=x->size-start);memcpy(out,(unsigned char*)x->data+start,(size_t)n);if(start==32){if(action_at==1)mutate();if(action_at==3)exception_flag=1;}}
static void ints(JNIEnv*e,jintArray a,jsize start,jsize n,jint*out){(void)e;Array*x=a;CHECK(start>=0&&n>=0&&start<=x->size&&n<=x->size-start);memcpy(out,(jint*)x->data+start,(size_t)n*sizeof*out);}
static void longs(JNIEnv*e,jlongArray a,jsize start,jsize n,jlong*out){(void)e;Array*x=a;CHECK(start>=0&&n>=0&&start<=x->size&&n<=x->size-start);memcpy(out,(jlong*)x->data+start,(size_t)n*sizeof*out);}
static jboolean exception(JNIEnv*e){(void)e;return (jboolean)exception_flag;}
static jstring string(JNIEnv*e,const char*s){(void)e;CHECK(strlen(s)<sizeof json);memcpy(json,s,strlen(s)+1);return json;}
static const struct JNINativeInterface_ functions={.GetIntArrayRegion=ints,.GetLongArrayRegion=longs,.GetArrayLength=length,.GetByteArrayRegion=bytes,.ExceptionCheck=exception,.NewStringUTF=string};
static JNIEnv env=&functions;
static void mutate(void){
 if(action==1)Java_org_coh_sessionclient_SessionNative_state(&env,NULL,(jlong)(intptr_t)active,(jlong)(active->epoch+1),JNI_FALSE);
 else if(action==2)Java_org_coh_sessionclient_SessionNative_clearObservedEntity(&env,NULL,(jlong)(intptr_t)active);
 else if(action==3){active->observed_entity_updates++;}
 else if(action==4){active->observed_entity_index++;}
 else if(action==5){active->received_invalidations++;}
 else if(action==6)Java_org_coh_sessionclient_SessionNative_cancel(&env,NULL,(jlong)(intptr_t)active);
}
static unsigned char frame_data[48384];static jint fd_values[COH_RECEIVED_COSTUME_ARCHIVES];static jlong zeros[COH_RECEIVED_COSTUME_ARCHIVES],fd_sizes[COH_RECEIVED_COSTUME_ARCHIVES];
static Array frame={48384,frame_data},fds={2,fd_values},offsets={2,zeros},sizes={2,fd_sizes};
static void put32(unsigned char*p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));}
static void reset_input(Session*s){
 s->failed=0;s->cancel=0;s->running=0;s->epoch=7;s->foreground=1;s->observed_entity_index=125;s->observed_entity_updates=3;s->received_invalidations=2;
 action=action_at=exception_flag=parent_fail=prepare_fail=gpu_fail=0;expected_epoch=99;
 memset(frame_data,0,sizeof frame_data);memcpy(frame_data,"COHCST01",8);put32(frame_data+8,32);put32(frame_data+12,sizeof(CohOriginalCostumeSnapshot));put32(frame_data+16,99);put32(frame_data+24,125);
 frame.size=48384;fds.size=offsets.size=sizes.size=2;for(unsigned i=0;i<COH_RECEIVED_COSTUME_ARCHIVES;i++){zeros[i]=0;fd_values[i]=fd_values[0];fd_sizes[i]=fd_sizes[0];}
}
static jint call(Session*s,jlong jbytes,jlong source){return Java_org_coh_sessionclient_SessionNative_observedCostume(&env,NULL,(jlong)(intptr_t)s,&frame,&fds,&offsets,&sizes,jbytes,source);}
static void unchanged(Session*s,CohReceivedCostume*old,uint64_t parent,size_t live){CHECK(s->received_actor==old);CHECK(world_parent==parent);CHECK(!s->received_preparing);CHECK(alloc_live==live);CHECK(fds_open()==initial_fds);CHECK(!exception_flag||action_at==3);}
static void check_json(Session*s,const char*kind){Java_org_coh_sessionclient_SessionNative_snapshot(&env,NULL,(jlong)(intptr_t)s);CHECK(strstr(json,kind)!=NULL);CHECK(strstr(json,"\"complete_actor\":false")!=NULL);}
int main(void){
 Session session;memset(&session,0,sizeof session);CHECK(!pthread_mutex_init(&session.mutex,NULL));active=&session;session.stream_world=(CohSessionWorld*)(uintptr_t)1;session.runtime_world_status=1;
 char path[]="/tmp/coh-setter-XXXXXX";int fd=mkstemp(path);CHECK(fd>=0);unsigned char body[32]={0};CHECK(write(fd,body,sizeof body)==(ssize_t)sizeof body);CHECK(!fchmod(fd,0400));close(fd);fd=open(path,O_RDONLY|O_CLOEXEC);CHECK(fd>=0);unlink(path);fd_values[0]=fd;fd_sizes[0]=32;
 initial_fds=fds_open();
 for(unsigned n=1;n<=COH_RECEIVED_COSTUME_ARCHIVES;n+=COH_RECEIVED_COSTUME_ARCHIVES-1){reset_input(&session);fds.size=offsets.size=sizes.size=(jsize)n;CHECK(call(&session,48384,775621)==COH_OK);coh_received_costume_destroy(&session.received_actor);CHECK(alloc_live==0&&fds_open()==initial_fds);}
 reset_input(&session);fds.size=offsets.size=sizes.size=0;CHECK(call(&session,48384,775621)==COH_INVALID);
 reset_input(&session);fds.size=offsets.size=sizes.size=COH_RECEIVED_COSTUME_ARCHIVES+1;CHECK(call(&session,48384,775621)==COH_INVALID);
 fd_reads=0;reset_input(&session);CHECK(call(&session,48384,775621)==COH_OK);const uint64_t initial_parent=captured_parent;CHECK(session.received_actor&&session.received_stats.parts==13);CHECK(mutex_was_held);CHECK(!session.received_preparing);CHECK(alloc_live==1);CHECK(fd_reads==1);CHECK(fcntl(fd,F_GETFD)>=0);
 CHECK(captured_parent>=775621+48384+sizeof(CohOriginalCostumeSnapshot)+coh_received_costume_fds_allocation_bytes()+COH_RECEIVED_COSTUME_STACK+COH_CAPTURE_RESERVE);
 check_json(&session,"\"kind\":\"box\"");Graphics graphics={0};float view[12]={0},projection[16]={0};CHECK(received_draw(&session,&graphics,view,projection)==1);CHECK(gpu_draws==13&&session.received_last_draw);session.observed_entity_draws=1;check_json(&session,"\"kind\":\"received_huge\"");CHECK(strstr(json,"\"box_draws\":0")!=NULL);received_surface_delete(&graphics,0);
 CohReceivedCostume*old=session.received_actor;uint64_t old_parent=world_parent;size_t live=alloc_live;
 /* Complete invalid-input preflight must not allocate or disturb old state. */
 for(unsigned which=0;which<11;which++){reset_input(&session);size_t calls=alloc_calls;switch(which){case 0:frame_data[0]='X';break;case 1:put32(frame_data+8,31);break;case 2:put32(frame_data+12,1);break;case 3:put32(frame_data+16,0);break;case 4:put32(frame_data+24,126);break;case 5:put32(frame_data+28,1);break;case 6:frame.size--;break;case 7:fds.size--;break;case 8:zeros[1]=1;break;case 9:fd_values[1]=-1;break;case 10:fd_sizes[1]=0;break;}
  CHECK(call(&session,48384,775621)!=COH_OK);CHECK(alloc_calls==calls);unchanged(&session,old,old_parent,live);
 }
 reset_input(&session);session.running=1;CHECK(call(&session,48384,775621)==COH_STATE);unchanged(&session,old,old_parent,live);
 reset_input(&session);session.received_preparing=1;CHECK(call(&session,48384,775621)==COH_STATE);session.received_preparing=0;unchanged(&session,old,old_parent,live);
 reset_input(&session);CHECK(call(&session,48383,775621)==COH_INVALID);CHECK(call(&session,48384,0)==COH_INVALID);CHECK(call(&session,INT64_MAX,775621)==COH_LIMIT);CHECK(call(&session,48384,INT64_MAX)==COH_LIMIT);unchanged(&session,old,old_parent,live);
 /* Real state/clear/cancel calls and direct token-component changes at copy/read. */
 for(unsigned at=1;at<=2;at++)for(unsigned change=1;change<=6;change++){reset_input(&session);action_at=at;action=change;CHECK(call(&session,48384,775621)==COH_CANCELLED);unchanged(&session,old,old_parent,live);}
 reset_input(&session);action_at=3;CHECK(call(&session,48384,775621)==COH_INVALID);unchanged(&session,old,old_parent,live);
 reset_input(&session);prepare_fail=1;CHECK(call(&session,48384,775621)==COH_UNSUPPORTED);unchanged(&session,old,old_parent,live);
 reset_input(&session);parent_fail=1;CHECK(call(&session,48384,775621)==COH_LIMIT);unchanged(&session,old,old_parent,live);
 /* Snapshot, real FD owner, and actor candidate allocation failures. */
 for(size_t n=1;n<=3;n++){reset_input(&session);alloc_fail=alloc_calls+n;CHECK(call(&session,48384,775621)==COH_LIMIT);alloc_fail=0;unchanged(&session,old,old_parent,live);}
 /* Original FDs remain owned by caller; duplicate failure/immutability refuses. */
 reset_input(&session);fd_values[1]=999999;CHECK(call(&session,48384,775621)==COH_IO);unchanged(&session,old,old_parent,live);
 reset_input(&session);CHECK(!fchmod(fd,0600));CHECK(call(&session,48384,775621)==COH_STATE);CHECK(!fchmod(fd,0400));unchanged(&session,old,old_parent,live);
 /* Replacement's preparation includes old CPU/GPU/source, before retirement. */
 reset_input(&session);unsigned before=owner_destroys;uint64_t first_parent=captured_parent;CHECK(call(&session,48384,775621)==COH_OK);CHECK(session.received_actor!=old&&owner_destroys==before+1);CHECK(alloc_live==1);CHECK(captured_parent==first_parent);CHECK(captured_parent==initial_parent+session.received_stats.cpu_bytes+session.received_stats.gpu_reserve_bytes+session.received_stats.renderer_cpu_reserve_bytes+775621);CHECK(!session.received_last_draw);check_json(&session,"\"kind\":\"box\"");
 reset_input(&session);old=session.received_actor;old_parent=world_parent;uint64_t saved_cpu=world_cpu;world_cpu=96u<<20;unsigned prep=prepare_calls;CHECK(call(&session,48384,775621)==COH_LIMIT);CHECK(prepare_calls==prep);world_cpu=saved_cpu;unchanged(&session,old,old_parent,1);
 /* Candidate accounting admits this source charge without old actor, but
  * refuses the concrete simultaneous old+candidate overlap. */
 reset_input(&session);uint64_t candidate=100u*1024u+200u*1024u+4096u+COH_RECEIVED_COSTUME_STACK;
 uint64_t source_charge=COH_RECEIVED_COSTUME_LIMIT-candidate+1-(captured_parent-775621);
 CHECK(initial_parent-775621+source_charge+candidate<COH_RECEIVED_COSTUME_LIMIT);
 CHECK(call(&session,48384,(jlong)source_charge)==COH_LIMIT);unchanged(&session,old,old_parent,1);
 /* Cancellation cannot interleave world-parent mutation and publication:
  * a competing real cancel blocks on the shared mutex until both complete. */
 reset_input(&session);cancel_at_parent=1;CHECK(call(&session,48384,775621)==COH_OK);CHECK(!pthread_join(cancelling_thread,NULL));cancel_at_parent=0;CHECK(session.cancel&&session.received_invalidations==3);CHECK(mutex_was_held);CHECK(alloc_live==1);CHECK(fds_open()==initial_fds);
 /* GPU failure is visual fallback only, and reported honestly. */
 Graphics failed={0};gpu_fail=1;CHECK(!received_draw(&session,&failed,view,projection));CHECK(session.received_status==COH_LIMIT&&!session.received_last_draw);check_json(&session,"\"kind\":\"box\"");
 coh_received_costume_destroy(&session.received_actor);CHECK(!alloc_live);CHECK(!pthread_mutex_destroy(&session.mutex));CHECK(!close(fd));
 printf("{\"passed\":true,\"checks\":%u,\"actual_geometry\":false,\"native_setter\":true,\"mock_actor_parts\":13,\"prepare_calls\":%u,\"parent_calls\":%u,\"allocation_live\":%zu}\n",checks,prepare_calls,parent_calls,alloc_live);return 0;
}
