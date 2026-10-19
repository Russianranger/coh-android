/* New JNI adapter against explicit JNI/controller/provider doubles only. */
#include <jni.h>
#include "coh_initial_capture.h"
#include "coh_session_crypto.h"
#ifdef COH_INTEROP_REQUEST_TX
#include "coh_request_tx.h"
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../engine/initial-capture/qualification/initial-pose-20261019/jni-fixture.h"
static unsigned pose_fixture;
static unsigned checks,scenarios,alloc_calls,fail_alloc,freed,wiped,live,release_chars,deleted_refs;
static int fault,exception_pending;static jlong current;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"interop test line %u: %s\n",(unsigned)__LINE__,#x);exit(1);}}while(0)
#define JNI(name) Java_org_coh_nativecombined_InteropNative_##name
jlong JNI(begin)(JNIEnv*,jclass,jint,jstring,jint,jboolean,jboolean,jlong);
jint JNI(service)(JNIEnv*,jclass,jlong,jlong);jint JNI(choose)(JNIEnv*,jclass,jlong,jint,jlong);
jbyteArray JNI(characters)(JNIEnv*,jclass,jlong);jstring JNI(report)(JNIEnv*,jclass,jlong);
void JNI(suspend)(JNIEnv*,jclass,jlong);void JNI(disconnect)(JNIEnv*,jclass,jlong);void JNI(close)(JNIEnv*,jclass,jlong);
static struct {void*p;size_t bytes;} allocations[8];
void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_calloc(size_t n,size_t bytes){alloc_calls++;if(fail_alloc==alloc_calls)return NULL;void*p=__real_calloc(n,bytes);CHECK(p);unsigned i;for(i=0;i<8&&allocations[i].p;i++);CHECK(i<8);allocations[i].p=p;allocations[i].bytes=n*bytes;live++;return p;}
void __wrap_free(void*p){if(!p)return;unsigned i;for(i=0;i<8&&allocations[i].p!=p;i++);CHECK(i<8);unsigned char sum=0;for(size_t j=0;j<allocations[i].bytes;j++)sum|=((unsigned char*)p)[j];CHECK(!sum);wiped++;allocations[i].p=NULL;allocations[i].bytes=0;live--;freed++;__real_free(p);}
void coh_db_wipe(void*p,size_t bytes){volatile unsigned char*q=p;while(bytes--)*q++=0;}
static struct {jsize length;jchar data[20];} input;
static char report_text[8192],sample_report[8192],private_bytes[65536];static jsize byte_count;
static jsize get_length(JNIEnv*e,jstring value){(void)e;CHECK(value==&input);if(fault==1)exception_pending=1;return input.length;}
static const jchar*get_chars(JNIEnv*e,jstring value,jboolean*copy){(void)e;CHECK(value==&input&&!copy);if(fault==2){exception_pending=1;return NULL;}return input.data;}
static void release(JNIEnv*e,jstring value,const jchar*p){(void)e;CHECK(value==&input&&p==input.data);release_chars++;}
static jboolean has_exception(JNIEnv*e){(void)e;return (jboolean)exception_pending;}
static jbyteArray new_bytes(JNIEnv*e,jsize count){(void)e;CHECK(count>0&&count<(jsize)sizeof(private_bytes));if(fault==3){exception_pending=1;return NULL;}byte_count=count;return private_bytes;}
static void set_bytes(JNIEnv*e,jbyteArray target,jsize at,jsize count,const jbyte*data){(void)e;CHECK(target==private_bytes&&!at&&count==byte_count);if(fault==4){exception_pending=1;return;}memcpy(private_bytes,data,(size_t)count);private_bytes[count]=0;}
static void delete_ref(JNIEnv*e,jobject value){(void)e;CHECK(value==private_bytes);deleted_refs++;}
static jstring new_string(JNIEnv*e,const char*text){(void)e;if(fault==5){exception_pending=1;return NULL;}CHECK(strlen(text)<sizeof(report_text));strcpy(report_text,text);return report_text;}
static const struct JNINativeInterface_ methods={get_length,get_chars,release,has_exception,new_bytes,set_bytes,delete_ref,new_string};
static JNIEnv env=&methods;
static CohAuthCrypto provider;static unsigned creates,begins,services,chooses,closes,destroys,cancels,lease_calls;
struct CohInitialCapture {CohInitialCaptureDiagnostics d;unsigned step,chosen;};static struct CohInitialCapture capture;
static const CohInitialCaptureEvent *live_event;static CohInitialCaptureLease loan;static unsigned char packet[64]="PRIVATE_PACKET_SENTINEL";
const CohAuthCrypto*coh_auth_openssl_provider(void){return fault==6?NULL:&provider;}
int RAND_bytes(unsigned char*out,int count){CHECK(count==8);if(fault==7)return 0;memset(out,0x63,(size_t)count);return 1;}
CohStatus coh_session_key_exchange(void*a,const uint8_t b[64],uint8_t c[64],CohBlowfish*d){(void)a;(void)b;(void)c;(void)d;return COH_UNSUPPORTED;}
CohLocalConfig coh_local_default_config(void){CohLocalConfig c;memset(&c,0,sizeof(c));c.db.request_timeout_ms=c.map.application_timeout_ms=120000;return c;}
CohStatus coh_local_login_policy(CohDbLogin*out){memset(out,0,sizeof(*out));out->protocol_version=COH_DB_PROTOCOL_VERSION;return fault==8?COH_STATE:COH_OK;}
CohInitialCapture*coh_initial_capture_create(const CohLocalConfig*c){creates++;CHECK(c->local_development_enabled==1&&c->db.transport.peer.port==7000&&c->db.transport.peer.address[0]==127&&c->db.transport.link.version==5&&c->map.udp.link.version==5&&!c->db.transport.encryption_required&&!c->map.udp.encryption_required&&!c->db.outbound_compressed&&c->db.transport.key_context==&provider&&c->map.udp.key_context==&provider);if(fault==9)return NULL;memset(&capture,0,sizeof(capture));return &capture;}
CohStatus coh_initial_capture_begin(CohInitialCapture*c,const CohDbLogin*p,const char*name,uint32_t db,uint32_t map,uint64_t now){begins++;CHECK(c==&capture&&!strcmp(name,"PRIVATE_USER")&&p->protocol_version==COH_DB_PROTOCOL_VERSION&&db&&map==db+1&&now==100);if(fault==10)return COH_IO;c->d.phase=COH_INITIAL_CAPTURE_CONNECTING;c->d.local.phase=COH_LOCAL_DB_CONNECTING;c->d.local.local_development_auth=1;c->d.local.opened_sockets=1;c->d.local.attempts=1;return COH_OK;}
CohStatus coh_initial_capture_characters(const CohInitialCapture*c,CohLocalCharacters*out){CHECK(c==&capture);if(fault==11)return COH_STATE;memset(out,0,sizeof(*out));out->count=fault==12?COH_DB_SLOTS_MAX+1:1;out->players[0].wire_slot=2;out->players[0].level=4;strcpy(out->players[0].name,"PRIVATE_CHARACTER\"\\\n");strcpy(out->players[0].map_name,"PRIVATE_MAP");if(fault==13)memset(out->players[0].name,'X',sizeof(out->players[0].name));return COH_OK;}
CohStatus coh_initial_capture_choose_character(CohInitialCapture*c,uint32_t slot,uint64_t now){CHECK(c==&capture&&slot==2&&now==102);chooses++;c->chosen=1;c->d.local.phase=COH_LOCAL_MAP_CONNECTING;c->d.local.opened_sockets=2;c->d.local.character_choices=1;c->d.local.map_handoffs=1;return COH_OK;}
static void closed(CohInitialCapture*c){c->d.local.closed_sockets=c->d.local.opened_sockets;c->d.local.phase=COH_LOCAL_CLOSED;}
CohStatus coh_initial_capture_service(CohInitialCapture*c,uint64_t now,CohCancel cancel,CohInitialCaptureObserver observer,void*context,size_t bytes){CHECK(c==&capture&&now>=101&&!cancel.poll&&observer&&context&&bytes);services++;if(fault==14){CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_STATE);JNI(close)(&env,NULL,current);JNI(suspend)(&env,NULL,current);JNI(disconnect)(&env,NULL,current);CHECK(JNI(characters)(&env,NULL,current)==NULL);CHECK(JNI(report)(&env,NULL,current));}
 if(!c->chosen){c->d.local.phase=COH_LOCAL_CHARACTERS_READY;c->d.local.character_lists=1;return COH_OK;}
 CohInitialCaptureEvent event={c->step?COH_INITIAL_CAPTURE_ALLENTS:COH_INITIAL_CAPTURE_GROUPS};memset(&loan,0,sizeof(loan));loan.kind=event.kind;loan.reader.bytes=(CohBytes){packet,sizeof(packet)};loan.reader.bits=sizeof(packet)*8;loan.reader.cursor=16;loan.reader.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX;loan.message_generation=c->step?2:1;loan.groups_message_generation=c->step?1:0;loan.local_development_authorized=loan.selected_dbid_owner_bound=1;loan.selected_dbid=909090;loan.update.command=COH_REP_ALLENTS;if(fault==15)loan.world_authority=1;if(fault==16)loan.groups_message_generation=55;if(pose_fixture&&c->step){loan.reader.bytes=(CohBytes){coh_pose_jni_fixture,sizeof(coh_pose_jni_fixture)};loan.reader.bits=pose_fixture==3?COH_POSE_JNI_FIXTURE_POSE_END-1:pose_fixture==4?COH_POSE_JNI_FIXTURE_POSE_END:COH_POSE_JNI_FIXTURE_BITS;loan.reader.cursor=COH_POSE_JNI_FIXTURE_POST_COMMAND;loan.message_id=pose_fixture==2?0:17;}live_event=&event;CohStatus status=observer(context,c,&event);live_event=NULL;
 if(status!=COH_OK){c->d.first_failure=(CohInitialCaptureFailureSnapshot){1,c->d.local.phase,COH_DB_HANDOFF_READY,COH_MAP_SCENE_INCOMPLETE,status,COH_INITIAL_CAPTURE_FAILURE_OBSERVER};c->d.failure=COH_INITIAL_CAPTURE_FAILURE_OBSERVER;c->d.phase=COH_INITIAL_CAPTURE_FAILED;c->d.status=status;closed(c);return status;}
 if(!c->step++){c->d.groups_observed=1;c->d.groups_observations=1;c->d.reqallents_sent=1;c->d.phase=COH_INITIAL_CAPTURE_WAIT_ALLENTS;return COH_OK;}
 c->d.raw_allents_observed=1;c->d.allents_observations=1;c->d.phase=COH_INITIAL_CAPTURED;c->d.status=COH_UNSUPPORTED;closed(c);return COH_UNSUPPORTED;}
CohStatus coh_initial_capture_lease(const CohInitialCapture*c,const CohInitialCaptureEvent*e,CohInitialCaptureLease*out){CHECK(c==&capture&&e==live_event&&out);lease_calls++;if(fault==17)return COH_STATE;*out=loan;return COH_OK;}
void coh_initial_capture_diagnostics(const CohInitialCapture*c,CohInitialCaptureDiagnostics*out){CHECK(c==&capture&&out);*out=c->d;}
void coh_initial_capture_close(CohInitialCapture*c){if(!c)return;CHECK(c==&capture);closes++;closed(c);if(c->d.phase!=COH_INITIAL_CAPTURED&&c->d.phase!=COH_INITIAL_CAPTURE_FAILED&&c->d.phase!=COH_INITIAL_CAPTURE_CANCELLED)c->d.phase=COH_INITIAL_CAPTURE_CLOSED;}
void coh_initial_capture_destroy(CohInitialCapture*c){if(!c)return;CHECK(c==&capture);destroys++;}
void coh_initial_capture_cancel(CohInitialCapture*c){CHECK(c==&capture);cancels++;if(!c->d.first_failure.valid)c->d.first_failure=(CohInitialCaptureFailureSnapshot){1,c->d.local.phase,COH_DB_WAIT_PLAYERS,COH_MAP_IDLE,COH_CANCELLED,COH_INITIAL_CAPTURE_FAILURE_CANCELLED};c->d.phase=COH_INITIAL_CAPTURE_CANCELLED;closed(c);}
const char*coh_initial_capture_command_name(CohInitialCaptureCommandKind kind){(void)kind;return "NONE";}
#ifdef COH_INTEROP_REQUEST_TX
struct CohRequestTxWitness {const CohInitialCapture*owner;unsigned retired;};static struct CohRequestTxWitness witness;
CohRequestTxWitness*coh_request_tx_create(const CohInitialCapture*owner,uint64_t start){CHECK(owner==&capture&&start==100);if(fault==18)return NULL;witness=(struct CohRequestTxWitness){owner,0};return &witness;}
CohStatus coh_request_tx_service(CohRequestTxWitness*w,CohInitialCapture*owner,uint64_t now,CohCancel c,CohInitialCaptureObserver o,void*ctx,size_t bytes){CHECK(!w||(!w->retired&&w->owner==owner));return coh_initial_capture_service(owner,now,c,o,ctx,bytes);}
void coh_request_tx_close(CohRequestTxWitness*w,CohInitialCapture*owner){CHECK(!w||(!w->retired&&w->owner==owner));coh_initial_capture_close(owner);}
void coh_request_tx_cancel(CohRequestTxWitness*w,CohInitialCapture*owner){CHECK(!w||(!w->retired&&w->owner==owner));coh_initial_capture_cancel(owner);}
void coh_request_tx_retire(CohRequestTxWitness*w){if(w){CHECK(!w->retired);w->retired=1;w->owner=NULL;}}
void coh_request_tx_diagnostics(const CohRequestTxWitness*w,CohRequestTxDiagnostics*out){CHECK(w);memset(out,0,sizeof(*out));out->diagnostic_only=1;out->valid=w->retired;out->witness_retired=w->retired;out->queue_attempted=out->queue_succeeded=capture.d.reqallents_sent;out->queue_status=COH_OK;out->first_send_attempts=out->first_send_accepted=capture.d.reqallents_sent;out->peer_transport_ack_observed=capture.d.raw_allents_observed;}
void coh_request_tx_destroy(CohRequestTxWitness*w){if(w)CHECK(w->retired&&!w->owner);}
#endif
static void fixture(void){CHECK(!live);pose_fixture=0;fault=exception_pending=0;alloc_calls=fail_alloc=0;memset(&input,0,sizeof(input));const char*n="PRIVATE_USER";input.length=(jsize)strlen(n);for(jsize i=0;i<input.length;i++)input.data[i]=(jchar)n[i];}
static void start(void){current=JNI(begin)(&env,NULL,7000,&input,5,JNI_FALSE,JNI_FALSE,100);CHECK(current>0&&live==1);}
static const char*report(void){CHECK(JNI(report)(&env,NULL,current));CHECK(strstr(report_text,"coh-native-initial-interop-numeric-v1")&&!strstr(report_text,"PRIVATE_")&&!strstr(report_text,"909090"));CHECK(strstr(report_text,"\"world_authority\":false")&&strstr(report_text,"\"packet_copy_retained\":false"));return report_text;}
static void finish(void){JNI(close)(&env,NULL,current);CHECK(!live);CHECK(JNI(service)(&env,NULL,current,101)==COH_INVALID);current=0;scenarios++;}
int main(void){
 fixture();CHECK(!JNI(begin)(&env,NULL,0,&input,5,0,0,100));CHECK(!JNI(begin)(&env,NULL,7000,&input,6,0,0,100));CHECK(!JNI(begin)(&env,NULL,7000,&input,5,2,0,100));CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,-1));CHECK(!JNI(begin)(&env,NULL,7000,NULL,5,0,0,100));
 for(int f=1;f<=2;f++){fixture();fault=f;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live&&exception_pending);scenarios++;}
 for(int f=6;f<=10;f++){fixture();fault=f;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);scenarios++;}
 fixture();input.length=15;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);fixture();input.length=0;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);fixture();input.data[3]=127;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);fixture();input.data[3]=0;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);fixture();fail_alloc=1;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!live);
 fixture();start();jlong stale=current;CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100));CHECK(JNI(service)(&env,NULL,current,-1)==COH_INVALID);CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(strstr(report(),"CHARACTERS_READY"));CHECK(JNI(characters)(&env,NULL,current)&&strstr(private_bytes,"PRIVATE_CHARACTER\\\"\\\\\\u000a")&&byte_count>0);
 for(int f=3;f<=4;f++){fault=f;exception_pending=0;CHECK(!JNI(characters)(&env,NULL,current)&&exception_pending&&live==1);}fault=0;exception_pending=0;
 for(int f=11;f<=13;f++){fault=f;CHECK(!JNI(characters)(&env,NULL,current)&&live==1);}fault=0;
 fail_alloc=alloc_calls+1;CHECK(!JNI(characters)(&env,NULL,current)&&live==1);fail_alloc=alloc_calls+2;CHECK(!JNI(characters)(&env,NULL,current)&&live==1);fail_alloc=0;
 CHECK(JNI(choose)(&env,NULL,current,64,102)==COH_INVALID);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(strstr(report(),"WAIT_ALLENTS")&&strstr(report_text,"\"reqallents_sent\":1"));CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"raw_allents_observed\":true")&&strstr(report_text,"\"cleanup_verified\":true"));CHECK(strstr(report_text,"\"first_create\":{\"schema\":\"coh-initial-first-create-v1\""));strcpy(sample_report,report_text);CHECK(JNI(service)(&env,NULL,current,105)==COH_STATE);fault=5;CHECK(!JNI(report)(&env,NULL,current)&&exception_pending);fault=0;exception_pending=0;JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"raw_allents_observed\":true"));finish();
 fixture();start();CHECK(current!=stale);JNI(close)(&env,NULL,stale);CHECK(live==1);JNI(suspend)(&env,NULL,current);CHECK(strstr(report(),"SUSPENDED")&&strstr(report_text,"CANCELLED")&&strstr(report_text,"\"cleanup_verified\":true"));CHECK(JNI(service)(&env,NULL,current,101)==COH_STATE);JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED"));finish();
 for(int f=14;f<=17;f++){fixture();start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);fault=f;CohStatus s=(CohStatus)JNI(service)(&env,NULL,current,103);if(f==14){CHECK(s==COH_OK);fault=0;CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);}else if(f==16){CHECK(s==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_STATE);}else CHECK(s==COH_STATE);CHECK(strstr(report(),"\"world_authority\":false"));JNI(disconnect)(&env,NULL,current);if(f!=14)CHECK(strstr(report(),"\"valid\":true"));finish();}
 #ifdef COH_INTEROP_REQUEST_TX
 fixture();fault=18;start();CHECK(strstr(report(),"\"request_tx_available\":false"));finish();
#endif
 for(unsigned v=1;v<=4;v++){
  fixture();pose_fixture=v;start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"create_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_pose\":{");CHECK(body);
  if(v==1||v==4){CHECK(strstr(body,"FIRST_SEQUENCE_BODY_REQUIRED")&&strstr(body,"\"pose_validated\":true")&&strstr(body,"\"pose_end_bit\":459"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"INPUT\"")&&strstr(body,"\"status\":7")&&strstr(body,"\"pose_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"ORIENTATION\"")&&strstr(body,"\"position_validated\":true")&&strstr(body,"\"pose_validated\":false"));
  CHECK(!strstr(body,"\"packet_id\"")&&!strstr(body,"\"position\"")&&!strstr(body,"\"quaternion\"")&&!strstr(body,"\"mode_value\""));
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"create_validated\":true")&&strstr(report_text,"\"first_record_pose\":{")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 CHECK(freed==wiped&&!live&&deleted_refs==1&&release_chars>0&&lease_calls>0&&creates&&begins&&chooses&&services&&closes&&destroys&&cancels);
 printf("{\"schema\":\"coh-new-interop-jni-adapter-double-controls-v1\",\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"wiped_frees\":%u,\"JNI_and_initial_capture_explicit_doubles\":true,\"actual_Android_or_protocol_or_original_server\":false,\"world_authority\":false,\"sample_report\":%s}\n",checks,scenarios,wiped,sample_report);return 0;
}
