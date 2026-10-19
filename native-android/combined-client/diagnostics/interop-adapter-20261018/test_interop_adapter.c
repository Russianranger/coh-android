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
#include "../../../engine/initial-capture/qualification/initial-sequence-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-triggered-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-aianim-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-netfx-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-costume-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-reward-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-reward-list-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-costume-slots-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-costume-body-20261019/jni-fixture.h"
#include "../../../engine/initial-capture/qualification/initial-appearance-20261019/jni-fixture.h"
static unsigned pose_fixture;
static unsigned sequence_fixture;
static unsigned triggered_fixture,aianim_fixture,netfx_fixture,costume_fixture,reward_fixture,reward_list_fixture,slots_fixture,body_fixture,appearance_fixture;
static unsigned char appearance_packet[sizeof(coh_appearance_jni_fixture)];
static unsigned char body_packet[sizeof(coh_costume_body_jni_fixture)];
static unsigned char slots_packet[sizeof(coh_costume_slots_jni_fixture)];
static unsigned char reward_list_packet[sizeof(coh_reward_list_jni_fixture)];
static unsigned char reward_packet[sizeof(coh_reward_jni_fixture)];
static unsigned char costume_packet[sizeof(coh_costume_jni_fixture)];
static unsigned char aianim_packet[sizeof(coh_aianim_jni_fixture)];
static size_t max_report_bytes;
static unsigned char sequence_packet[sizeof(coh_sequence_jni_fixture)];
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
static jstring new_string(JNIEnv*e,const char*text){(void)e;if(fault==5){exception_pending=1;return NULL;}size_t bytes=strlen(text);CHECK(bytes<7168);if(bytes>max_report_bytes)max_report_bytes=bytes;CHECK(bytes<sizeof(report_text));strcpy(report_text,text);return report_text;}
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
 CohInitialCaptureEvent event={c->step?COH_INITIAL_CAPTURE_ALLENTS:COH_INITIAL_CAPTURE_GROUPS};memset(&loan,0,sizeof(loan));loan.kind=event.kind;loan.reader.bytes=(CohBytes){packet,sizeof(packet)};loan.reader.bits=sizeof(packet)*8;loan.reader.cursor=16;loan.reader.max_bytes=COH_REP_BOUNDED_MESSAGE_MAX;loan.message_generation=c->step?2:1;loan.groups_message_generation=c->step?1:0;loan.local_development_authorized=loan.selected_dbid_owner_bound=1;loan.selected_dbid=909090;loan.update.command=COH_REP_ALLENTS;if(fault==15)loan.world_authority=1;if(fault==16)loan.groups_message_generation=55;if(pose_fixture&&c->step){loan.reader.bytes=(CohBytes){coh_pose_jni_fixture,sizeof(coh_pose_jni_fixture)};loan.reader.bits=pose_fixture==3?COH_POSE_JNI_FIXTURE_POSE_END-1:pose_fixture==4?COH_POSE_JNI_FIXTURE_POSE_END:COH_POSE_JNI_FIXTURE_BITS;loan.reader.cursor=COH_POSE_JNI_FIXTURE_POST_COMMAND;loan.message_id=pose_fixture==2?0:17;}if(sequence_fixture&&c->step){loan.reader.bytes=(CohBytes){sequence_packet,sizeof(sequence_packet)};loan.reader.bits=sequence_fixture==3?COH_SEQUENCE_JNI_FIXTURE_SEQUENCE_END-1:sequence_fixture==4?COH_SEQUENCE_JNI_FIXTURE_SEQUENCE_END:COH_SEQUENCE_JNI_FIXTURE_BITS;loan.reader.cursor=COH_SEQUENCE_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}if(triggered_fixture&&c->step){loan.reader.bytes=(CohBytes){coh_triggered_jni_fixture,sizeof(coh_triggered_jni_fixture)};loan.reader.bits=triggered_fixture==2?COH_TRIGGERED_JNI_FIXTURE_SEQUENCE_END:triggered_fixture==3?COH_TRIGGERED_JNI_FIXTURE_TRIGGERED_END-1:triggered_fixture==4?COH_TRIGGERED_JNI_FIXTURE_TRIGGERED_END:COH_TRIGGERED_JNI_FIXTURE_BITS;loan.reader.cursor=COH_TRIGGERED_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}if(aianim_fixture&&c->step){loan.reader.bytes=(CohBytes){aianim_packet,sizeof(aianim_packet)};loan.reader.bits=aianim_fixture==3?COH_AIANIM_JNI_FIXTURE_AI_END-1:aianim_fixture==4?COH_AIANIM_JNI_FIXTURE_AI_END:COH_AIANIM_JNI_FIXTURE_BITS;loan.reader.cursor=COH_AIANIM_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}
 if(netfx_fixture&&c->step){loan.reader.bytes=(CohBytes){coh_netfx_jni_fixture,sizeof(coh_netfx_jni_fixture)};loan.reader.bits=netfx_fixture==2?COH_NETFX_JNI_FIXTURE_AI_END:netfx_fixture==3?COH_NETFX_JNI_FIXTURE_NETFX_END-1:netfx_fixture==4?COH_NETFX_JNI_FIXTURE_NETFX_END:COH_NETFX_JNI_FIXTURE_BITS;loan.reader.cursor=COH_NETFX_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}
 if(costume_fixture&&c->step){loan.reader.bytes=(CohBytes){costume_packet,sizeof(costume_packet)};loan.reader.bits=costume_fixture==3?COH_COSTUME_JNI_FIXTURE_PREFIX_END-1:costume_fixture==4?COH_COSTUME_JNI_FIXTURE_PREFIX_END:COH_COSTUME_JNI_FIXTURE_BITS;loan.reader.cursor=COH_COSTUME_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}
 if(reward_fixture&&c->step){loan.reader.bytes=(CohBytes){reward_packet,sizeof(reward_packet)};loan.reader.bits=reward_fixture==3?COH_REWARD_JNI_FIXTURE_REWARD_END-1:reward_fixture==4?COH_REWARD_JNI_FIXTURE_REWARD_END:COH_REWARD_JNI_FIXTURE_BITS;loan.reader.cursor=COH_REWARD_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}
 if(reward_list_fixture&&c->step){loan.reader.bytes=(CohBytes){reward_list_packet,sizeof(reward_list_packet)};loan.reader.bits=reward_list_fixture==2?COH_REWARD_LIST_JNI_FIXTURE_LIST_END-1:reward_list_fixture==3?COH_REWARD_LIST_JNI_FIXTURE_FIRST_GROUP_END+31:reward_list_fixture==4?COH_REWARD_LIST_JNI_FIXTURE_LIST_END:COH_REWARD_LIST_JNI_FIXTURE_BITS;loan.reader.cursor=COH_REWARD_LIST_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;}
 if(slots_fixture&&c->step){
  size_t bits=COH_COSTUME_SLOTS_JNI_FIXTURE_BITS;
  if(slots_fixture==2)bits=COH_COSTUME_SLOTS_JNI_FIXTURE_CURRENT_BEGIN+7;
  if(slots_fixture==3)bits=COH_COSTUME_SLOTS_JNI_FIXTURE_ADDITIONAL_BEGIN+7;
  if(slots_fixture==4)bits=COH_COSTUME_SLOTS_JNI_FIXTURE_MULTIPLE_BEGIN;
  if(slots_fixture==6)bits=COH_COSTUME_SLOTS_JNI_FIXTURE_COUNT_BEGIN+3;
  if(slots_fixture==10)bits=COH_COSTUME_SLOTS_JNI_FIXTURE_SLOTS_END;
  loan.reader.bytes=(CohBytes){slots_packet,sizeof(slots_packet)};loan.reader.bits=bits;loan.reader.cursor=COH_COSTUME_SLOTS_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;
 }
 if(body_fixture&&c->step){
  size_t bits=COH_COSTUME_BODY_JNI_FIXTURE_BITS;
  if(body_fixture==6)bits=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN-1;
  if(body_fixture==7)bits=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN;
  if(body_fixture==8)bits=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_CACHE_BEGIN;
  if(body_fixture==9)bits=COH_COSTUME_BODY_JNI_FIXTURE_BODYTYPE_BEGIN;
  if(body_fixture==12)bits=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_CACHE_BEGIN;
  if(body_fixture==13)bits=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_STORAGE_BEGIN;
  loan.reader.bytes=(CohBytes){body_packet,sizeof(body_packet)};loan.reader.bits=bits;loan.reader.cursor=COH_COSTUME_BODY_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;
 }
 if(appearance_fixture&&c->step){
  size_t bits=COH_APPEARANCE_JNI_FIXTURE_BITS;
  if(appearance_fixture==2)bits=COH_APPEARANCE_JNI_FIXTURE_BODYTYPE_BEGIN+5;
  if(appearance_fixture==3)bits=COH_APPEARANCE_JNI_FIXTURE_SKIN_BEGIN+31;
  if(appearance_fixture==4)bits=COH_APPEARANCE_JNI_FIXTURE_CONVERTED_BEGIN;
  if(appearance_fixture==5)bits=COH_APPEARANCE_JNI_FIXTURE_SUPERSET_BEGIN+2;
  if(appearance_fixture==6)bits=COH_APPEARANCE_JNI_FIXTURE_EXTRA_BEGIN;
  if(appearance_fixture==8)bits=COH_APPEARANCE_JNI_FIXTURE_SCALARS_END;
  loan.reader.bytes=(CohBytes){appearance_packet,sizeof(appearance_packet)};loan.reader.bits=bits;loan.reader.cursor=COH_APPEARANCE_JNI_FIXTURE_POST_COMMAND;loan.message_id=17;
 }
 live_event=&event;CohStatus status=observer(context,c,&event);live_event=NULL;
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
static void fixture(void){CHECK(!live);pose_fixture=0;sequence_fixture=0;triggered_fixture=aianim_fixture=netfx_fixture=costume_fixture=reward_fixture=reward_list_fixture=slots_fixture=body_fixture=appearance_fixture=0;memcpy(appearance_packet,coh_appearance_jni_fixture,sizeof(appearance_packet));memcpy(body_packet,coh_costume_body_jni_fixture,sizeof(body_packet));memcpy(slots_packet,coh_costume_slots_jni_fixture,sizeof(slots_packet));memcpy(reward_list_packet,coh_reward_list_jni_fixture,sizeof(reward_list_packet));memcpy(reward_packet,coh_reward_jni_fixture,sizeof(reward_packet));memcpy(costume_packet,coh_costume_jni_fixture,sizeof(costume_packet));memcpy(aianim_packet,coh_aianim_jni_fixture,sizeof(aianim_packet));memcpy(sequence_packet,coh_sequence_jni_fixture,sizeof(sequence_packet));fault=exception_pending=0;alloc_calls=fail_alloc=0;memset(&input,0,sizeof(input));const char*n="PRIVATE_USER";input.length=(jsize)strlen(n);for(jsize i=0;i<input.length;i++)input.data[i]=(jchar)n[i];}
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
 for(unsigned v=1;v<=4;v++){
  fixture();sequence_fixture=v;if(v==2)sequence_packet[COH_SEQUENCE_JNI_FIXTURE_POSE_END/8]&=(unsigned char)~(1u<<(COH_SEQUENCE_JNI_FIXTURE_POSE_END%8));
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"create_validated\":true")&&strstr(report_text,"\"pose_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_sequence\":{");CHECK(body);
  if(v==1||v==4){CHECK(strstr(body,"FIRST_TRIGGERED_MOVES_REQUIRED")&&strstr(body,"\"sequence_validated\":true")&&strstr(body,"\"sequence_end_bit\":475"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"UPDATE\"")&&strstr(body,"\"status\":2")&&strstr(body,"\"sequence_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"MOVEMENT_BITS\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"sequence_validated\":false"));
  CHECK(!strstr(body,"\"packet_id\"")&&!strstr(body,"\"index_value\"")&&!strstr(body,"\"tick_value\"")&&!strstr(body,"\"movement_bits_value\""));
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"create_validated\":true")&&strstr(report_text,"\"pose_validated\":true")&&strstr(report_text,"\"first_record_sequence\":{")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 for(unsigned v=1;v<=4;v++){
  fixture();triggered_fixture=v;start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"create_validated\":true")&&strstr(report_text,"\"pose_validated\":true")&&strstr(report_text,"\"sequence_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_triggered_moves\":{");CHECK(body);
  if(v==1||v==4){CHECK(strstr(body,"FIRST_AI_ANIMATION_REQUIRED")&&strstr(body,"\"triggered_moves_validated\":true")&&strstr(body,"\"triggered_end_bit\":560")&&strstr(body,"\"entries_validated\":2")&&strstr(body,"\"fx_entries\":1"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"COUNT\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"count_validated\":false")&&strstr(body,"\"triggered_moves_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"FX\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"entries_validated\":1")&&strstr(body,"\"triggered_moves_validated\":false"));
  CHECK(!strstr(body,"\"packet_id\"")&&!strstr(body,"\"index_value\"")&&!strstr(body,"\"tick_value\"")&&!strstr(body,"\"fx_id\""));
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"sequence_validated\":true")&&strstr(report_text,"\"first_record_triggered_moves\":{")&&strstr(report_text,"\"world_authority\":false"));finish();
 }

 for(unsigned v=1;v<=4;v++){
  fixture();aianim_fixture=v;if(v==2)aianim_packet[COH_AIANIM_JNI_FIXTURE_TRIGGERED_END/8]&=(unsigned char)~(1u<<(COH_AIANIM_JNI_FIXTURE_TRIGGERED_END%8));
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"triggered_moves_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_ai_animation\":{");CHECK(body);
  if(v==1||v==4){CHECK(strstr(body,"FIRST_NETFX_REQUIRED")&&strstr(body,"\"ai_animation_validated\":true")&&strstr(body,"\"ai_end_bit\":658")&&strstr(body,"\"string_bytes\":11"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"UPDATE\"")&&strstr(body,"\"status\":2")&&strstr(body,"\"ai_animation_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"STRING\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"ai_animation_validated\":false"));
  CHECK(!strstr(body,"\"text\"")&&!strstr(body,"\"animation_name\"")&&!strstr(body,"fixture.anim"));
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"triggered_moves_validated\":true")&&strstr(report_text,"\"first_record_ai_animation\":{")&&strstr(report_text,"\"ack_permitted\":false"));finish();
 }
 for(unsigned v=1;v<=4;v++){
  fixture();netfx_fixture=v;start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"ai_animation_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_netfx\":{");CHECK(body);
  if(v==1||v==4){CHECK(strstr(body,"FIRST_COSTUME_BODY_REQUIRED")&&strstr(body,"\"netfx_validated\":true")&&strstr(body,"\"netfx_end_bit\":1440")&&strstr(body,"\"effect_count\":3"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"FLAGS\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"netfx_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"BODY\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"effect_count\":0")&&strstr(body,"\"netfx_validated\":false"));
  CHECK(strstr(body,"\"cross_prefix_in_phase_verified\":false")&&!strstr(body,"\"net_id\"")&&!strstr(body,"\"handle\"")&&!strstr(body,"\"position\"")&&!strstr(body,"\"effects\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"ai_animation_validated\":true")&&strstr(report_text,"\"first_record_netfx\":{")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }

 for(unsigned v=1;v<=4;v++){
  fixture();costume_fixture=v;
  if(v==2){unsigned bit=COH_COSTUME_JNI_FIXTURE_NETFX_END+3u;costume_packet[bit/8]^=(unsigned char)(1u<<(bit%8));}
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"netfx_validated\":true"));
  const char*body=strstr(report_text,"\"first_record_costume_prefix\":{");CHECK(body);
  if(v==1||v==4){char expected[64];snprintf(expected,sizeof(expected),"\"prefix_end_bit\":%u",COH_COSTUME_JNI_FIXTURE_PREFIX_END);CHECK(strstr(body,expected)&&strstr(body,"FIRST_COSTUME_DICTIONARY_REQUIRED")&&strstr(body,"\"self_wire_consistent\":true")&&strstr(body,"\"framing_validated\":true"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"SELF\"")&&strstr(body,"\"status\":7")&&strstr(body,"\"self_wire_consistent\":false")&&strstr(body,"\"framing_validated\":false"));
  else CHECK(strstr(body,"\"stage\":\"STORED_COUNT\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"framing_validated\":false"));
  CHECK(!strstr(body,"\"current_slot\"")&&!strstr(body,"\"deferred\"")&&!strstr(body,"\"generation\"")&&!strstr(body,"\"dictionary\"")&&!strstr(body,"\"text\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"\"netfx_validated\":true")&&strstr(report_text,"\"first_record_costume_prefix\":{")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }

 for(unsigned v=1;v<=5;v++){
  fixture();reward_fixture=v;
  if(v==2){unsigned bit=COH_REWARD_JNI_FIXTURE_REWARD_BEGIN;reward_packet[bit/8]&=(unsigned char)~(1u<<(bit%8));}
  if(v==5){unsigned bit=COH_REWARD_JNI_FIXTURE_REWARD_BEGIN+1u;reward_packet[bit/8]|=(unsigned char)(1u<<(bit%8));}
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"\"netfx_validated\":true")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED"));
  const char*body=strstr(report_text,"\"first_reward_string\":{");CHECK(body);
  if(v==1||v==4){char expected[64];snprintf(expected,sizeof(expected),"\"bit\":%u",COH_REWARD_JNI_FIXTURE_REWARD_END);CHECK(strstr(body,expected)&&strstr(body,"FIRST_REWARD_CONTINUATION_REQUIRED")&&strstr(body,"\"bytes\":13")&&strstr(body,"\"literal_validated\":true"));CHECK(strstr(body,v==1?"\"status\":2":"\"status\":1"));}
  else if(v==2)CHECK(strstr(body,"\"stage\":\"PRESENCE\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"literal_validated\":false"));
  else if(v==3)CHECK(strstr(body,"\"stage\":\"TEXT\"")&&strstr(body,"\"status\":1")&&strstr(body,"\"literal_validated\":false"));
  else {char expected[64];snprintf(expected,sizeof(expected),"\"bit\":%u",COH_REWARD_JNI_FIXTURE_REWARD_BEGIN+2u);CHECK(strstr(body,expected)&&strstr(body,"FIRST_REWARD_DICTIONARY_REQUIRED")&&strstr(body,"\"literal_validated\":false")&&strstr(body,"\"status\":2"));}
  CHECK(!strstr(body,"\"text\"")&&!strstr(body,"\"name\"")&&!strstr(body,"\"generation\"")&&!strstr(body,"\"index\"")&&!strstr(body,"\"packet\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED")&&strstr(report_text,"\"first_reward_string\":{")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }

 for(unsigned v=1;v<=5;v++){
  fixture();reward_list_fixture=v;
  if(v==5){unsigned bit=COH_REWARD_LIST_JNI_FIXTURE_LATE_REWARD_BEGIN+1u;reward_list_packet[bit/8]|=(unsigned char)(1u<<(bit%8));}
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED"));
  const char*body=strstr(report_text,"\"first_reward_string\":{");CHECK(body);
  CHECK(strstr(body,"FIRST_REWARD_CONTINUATION_REQUIRED")&&strstr(body,"\"bytes\":13")&&strstr(body,"\"bit\":1591")&&strstr(body,"\"literal_validated\":true"));
  char expected[96];
  if(v==1)snprintf(expected,sizeof(expected),"\"progress\":[4,9,2,3,%u,9,479]",COH_REWARD_LIST_JNI_FIXTURE_LIST_END);
  else if(v==4)snprintf(expected,sizeof(expected),"\"progress\":[1,8,2,3,%u,0,0]",COH_REWARD_LIST_JNI_FIXTURE_LIST_END);
  else if(v==2)snprintf(expected,sizeof(expected),"\"progress\":[1,4,2,2,2,2,%u,0,4]",COH_REWARD_LIST_JNI_FIXTURE_LIST_END-8u);
  else if(v==3)snprintf(expected,sizeof(expected),"\"progress\":[1,2,2,0,2,0,%u,0,0]",COH_REWARD_LIST_JNI_FIXTURE_FIRST_GROUP_END);
  else snprintf(expected,sizeof(expected),"\"progress\":[2,5,2,0,2,0,%u,0,5]",COH_REWARD_LIST_JNI_FIXTURE_LATE_REWARD_BEGIN+2u);
  CHECK(strstr(body,expected));CHECK(!strstr(body,"\"text\"")&&!strstr(body,"\"name\"")&&!strstr(body,"\"generation\"")&&!strstr(body,"\"index\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,expected)&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 /* Accepted slot fixtures keep opaque body bytes; the new prefix may refuse them. */
 for(unsigned v=1;v<=12;v++){
  fixture();slots_fixture=v;
  if(v==5){unsigned b=COH_COSTUME_SLOTS_JNI_FIXTURE_MULTIPLE_BEGIN;slots_packet[b/8]&=(unsigned char)~(1u<<(b%8));}
  if(v==7||v==8){unsigned value=v==7?0:15;for(unsigned i=0;i<4;i++){unsigned b=COH_COSTUME_SLOTS_JNI_FIXTURE_COUNT_BEGIN+i;slots_packet[b/8]=(unsigned char)((slots_packet[b/8]&~(1u<<(b%8)))|(((value>>i)&1u)<<(b%8)));}}
  if(v==9){for(unsigned i=0;i<8;i++){unsigned b=COH_COSTUME_SLOTS_JNI_FIXTURE_CURRENT_BEGIN+i;slots_packet[b/8]=(unsigned char)((slots_packet[b/8]&~(1u<<(b%8)))|(((2u>>i)&1u)<<(b%8)));}}
  if(v==11){for(unsigned b=COH_COSTUME_SLOTS_JNI_FIXTURE_SLOTS_END;b<COH_COSTUME_SLOTS_JNI_FIXTURE_BITS;b++)slots_packet[b/8]^=(unsigned char)(1u<<(b%8));}
  if(v==12){unsigned b=COH_COSTUME_SLOTS_JNI_FIXTURE_SLOTS_BEGIN;slots_packet[b/8]&=(unsigned char)~(1u<<(b%8));}
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED"));
  const char*body=strstr(report_text,"\"first_reward_string\":{");CHECK(body);
  CHECK(strstr(body,"FIRST_REWARD_CONTINUATION_REQUIRED")&&strstr(body,"\"bit\":1591")&&strstr(body,"\"bytes\":13")&&strstr(body,"\"literal_validated\":true"));
  unsigned status=2,stage=13,delta=22,metadata=1u|(1u<<1)|(255u<<9)|(1u<<17)|(2u<<18)|(1u<<22);
  if(v==2){status=1;stage=9;delta=1;metadata=1;}
  if(v==3){status=1;stage=10;delta=9;metadata=3;}
  if(v==4){status=1;stage=11;delta=17;metadata=3u|(255u<<9);}
  if(v==5){stage=11;delta=18;metadata=3u|(255u<<9);}
  if(v==6){status=1;stage=12;delta=18;metadata=3u|(255u<<9)|(1u<<17);}
  if(v==7||v==8){status=4;stage=12;metadata=3u|(255u<<9)|(1u<<17)|((v==7?0u:15u)<<18);}
  if(v==9){status=4;stage=12;metadata=1u|(2u<<1)|(255u<<9)|(1u<<17)|(2u<<18);}
  if(v==10)status=1;
  if(v==12)metadata&=~1u;
  char expected[96];
  if(v==1||v==10||v==11||v==12){
   status=1;stage=v==10?14u:v==11?21u:16u;delta=v==10?22u:25u;
   metadata=1u|(255u<<4)|((v==12?0u:1u)<<12)|(2u<<13);
   if(v==11)metadata|=(2u<<17)|(1u<<19)|(2u<<21)|(3u<<24);
   else if(v!=10)metadata|=(1u<<17)|(1u<<24);
  }
  snprintf(expected,sizeof(expected),"\"progress\":[%u,%u,2,3,%u,%u,%u]",status,stage,COH_COSTUME_SLOTS_JNI_FIXTURE_SLOTS_BEGIN,delta,metadata);CHECK(strstr(body,expected));
  CHECK(!strstr(body,"\"text\"")&&!strstr(body,"\"name\"")&&!strstr(body,"\"generation\"")&&!strstr(body,"\"packet\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,expected)&&strstr(report_text,"\"server_identity_bound\":false")&&strstr(report_text,"\"selected_owner_bound\":false")&&strstr(report_text,"\"complete_initial_character\":false")&&strstr(report_text,"\"actor_publication\":false")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 /* Original source optional resource names, then the untouched body-type Pack. */
 for(unsigned v=1;v<=13;v++){
  fixture();body_fixture=v;
  unsigned change=0,value=0,mutate=1;
  if(v==2)change=COH_COSTUME_BODY_JNI_FIXTURE_BODY_BEGIN;
  else if(v==3){change=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_CACHE_BEGIN;value=1;}
  else if(v==4)change=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_PRESENCE_BEGIN;
  else if(v==5){change=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_STORAGE_BEGIN;value=1;}
  else if(v==11)change=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN;
  else mutate=0;
  if(mutate)body_packet[change/8]=(unsigned char)((body_packet[change/8]&~(1u<<(change%8)))|(value<<(change%8)));
  if(v==10)for(unsigned b=COH_COSTUME_BODY_JNI_FIXTURE_BODYTYPE_BEGIN;b<COH_COSTUME_BODY_JNI_FIXTURE_BITS;b++)body_packet[b/8]^=(unsigned char)(1u<<(b%8));
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED"));
  const char*body=strstr(report_text,"\"first_reward_string\":{");CHECK(body);
  CHECK(strstr(body,"FIRST_REWARD_CONTINUATION_REQUIRED")&&strstr(body,"\"bit\":1591")&&strstr(body,"\"bytes\":13")&&strstr(body,"\"literal_validated\":true"));
  unsigned status=2,stage=26,present=3,complete=3,cached=2,validated=1,seen=3;
  unsigned stop=COH_COSTUME_BODY_JNI_FIXTURE_BODYTYPE_BEGIN;
  if(v==2){present=cached=0;stop=COH_COSTUME_BODY_JNI_FIXTURE_BODY_BEGIN+2;}
  if(v==3){status=1;stage=15;present=seen=cached=1;complete=validated=0;stop=COH_COSTUME_BODY_JNI_FIXTURE_FIRST_CACHE_BEGIN+1;}
  if(v==4||v==5||v==6||v==12||v==13){status=v==5?2u:1u;stage=v==4?16u:v==5?19u:v==6?18u:v==12?15u:17u;present=seen=1;complete=cached=validated=0;stop=v==4?COH_COSTUME_BODY_JNI_FIXTURE_FIRST_PRESENCE_BEGIN+1:v==5?COH_COSTUME_BODY_JNI_FIXTURE_FIRST_STORAGE_BEGIN+1:v==6?COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN-8:v==12?COH_COSTUME_BODY_JNI_FIXTURE_FIRST_CACHE_BEGIN:COH_COSTUME_BODY_JNI_FIXTURE_FIRST_STORAGE_BEGIN;}
  if(v==7){status=1;stage=20;present=complete=seen=1;cached=validated=0;stop=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN;}
  if(v==8){status=1;stage=21;complete=1;cached=validated=0;stop=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_CACHE_BEGIN;}
  if(v==9)status=1;
  if(v==11){present=1;cached=0;stop=COH_COSTUME_BODY_JNI_FIXTURE_PREFIX_FLAG_BEGIN+1;}
  unsigned metadata=1u|(255u<<4)|(1u<<12)|(2u<<13)|(present<<17)|(complete<<19)|(cached<<21)|(validated<<23)|(seen<<24);
  if(v==1||v==2||v==9||v==10||v==11){
   /* Newly reached scalar fields in these accepted prefix controls. */
   status=v==9?1u:2u;stage=v==9?27u:v==1?32u:31u;
   unsigned consumed=v==9?0u:43u;
   stop+=consumed;
   metadata=1u|(255u<<4)|(1u<<12)|(2u<<13)|(present<<17)|((cached>>1)<<19)|(consumed<<21);
  }
  char expected[96];snprintf(expected,sizeof(expected),"\"progress\":[%u,%u,2,3,%u,%u,%u]",status,stage,COH_COSTUME_BODY_JNI_FIXTURE_LIST_END,stop-COH_COSTUME_BODY_JNI_FIXTURE_LIST_END,metadata);CHECK(strstr(body,expected));
  CHECK(!strstr(body,"FixtureEntity")&&!strstr(body,"fixtureentity")&&!strstr(body,"\"text\"")&&!strstr(body,"\"name\"")&&!strstr(body,"\"generation\"")&&!strstr(body,"\"packet\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,expected)&&strstr(report_text,"\"server_identity_bound\":false")&&strstr(report_text,"\"selected_owner_bound\":false")&&strstr(report_text,"\"complete_initial_character\":false")&&strstr(report_text,"\"actor_publication\":false")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 /* Source-qualified raw appearance syntax, with no value/catalog admission. */
 for(unsigned v=1;v<=13;v++){
  fixture();appearance_fixture=v;
  if(v==7){unsigned b=COH_APPEARANCE_JNI_FIXTURE_EXTRA_BEGIN;appearance_packet[b/8]&=(unsigned char)~(1u<<(b%8));}
  if(v==9)for(unsigned b=COH_APPEARANCE_JNI_FIXTURE_SCALARS_END;b<COH_APPEARANCE_JNI_FIXTURE_BITS;b++)appearance_packet[b/8]^=(unsigned char)(1u<<(b%8));
  if(v==10||v==12){unsigned b=v==10?COH_APPEARANCE_JNI_FIXTURE_CONVERTED_BEGIN:COH_APPEARANCE_JNI_FIXTURE_BODYTYPE_BEGIN;appearance_packet[b/8]^=(unsigned char)(1u<<(b%8));}
  if(v==11)for(unsigned i=0;i<3;i++){unsigned b=COH_APPEARANCE_JNI_FIXTURE_SUPERSET_BEGIN+i;appearance_packet[b/8]^=(unsigned char)(1u<<(b%8));}
  if(v==13){unsigned b=COH_APPEARANCE_JNI_FIXTURE_FIRST_STORAGE_BEGIN;appearance_packet[b/8]|=(unsigned char)(1u<<(b%8));}
  start();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
  CHECK(strstr(report(),"INITIAL_OBSERVED")&&strstr(report_text,"\"cleanup_verified\":true")&&strstr(report_text,"FIRST_COSTUME_REWARD_STRING_REQUIRED"));
  const char*body=strstr(report_text,"\"first_reward_string\":{");CHECK(body);
  CHECK(strstr(body,"FIRST_REWARD_CONTINUATION_REQUIRED")&&strstr(body,"\"bit\":1591")&&strstr(body,"\"bytes\":13")&&strstr(body,"\"literal_validated\":true"));
  unsigned status=2,stage=32,consumed=43;
  if(v==2){status=1;stage=27;consumed=0;}
  if(v==3){status=1;stage=28;consumed=6;}
  if(v==4){status=1;stage=29;consumed=38;}
  if(v==5){status=1;stage=30;consumed=39;}
  if(v==6){status=1;stage=31;consumed=42;}
  if(v==7)stage=31;
  if(v==8)status=1;
  unsigned metadata=1u|(255u<<4)|(1u<<12)|(2u<<13)|(3u<<17)|(1u<<19)|(consumed<<21);
  char expected[96];
  if(v==13)snprintf(expected,sizeof(expected),"\"progress\":[2,19,2,3,1695,26,16932849]");
  else snprintf(expected,sizeof(expected),"\"progress\":[%u,%u,2,3,%u,%u,%u]",status,stage,COH_APPEARANCE_JNI_FIXTURE_LIST_END,COH_APPEARANCE_JNI_FIXTURE_APPEARANCE_BEGIN-COH_APPEARANCE_JNI_FIXTURE_LIST_END+consumed,metadata);
  CHECK(strstr(body,expected));CHECK(!strstr(body,"\"body_type\"")&&!strstr(body,"\"skin_color\"")&&!strstr(body,"\"text\"")&&!strstr(body,"\"generation\""));
  if(v==1)strcpy(sample_report,report_text);
  JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"CLOSED")&&strstr(report_text,expected)&&strstr(report_text,"\"server_identity_bound\":false")&&strstr(report_text,"\"selected_owner_bound\":false")&&strstr(report_text,"\"complete_initial_character\":false")&&strstr(report_text,"\"actor_publication\":false")&&strstr(report_text,"\"source_generation_admitted\":false")&&strstr(report_text,"\"ack_permitted\":false")&&strstr(report_text,"\"world_authority\":false"));finish();
 }
 CHECK(freed==wiped&&!live&&deleted_refs==1&&release_chars>0&&lease_calls>0&&creates&&begins&&chooses&&services&&closes&&destroys&&cancels);
 printf("{\"schema\":\"coh-new-interop-jni-adapter-double-controls-v1\",\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"wiped_frees\":%u,\"max_report_bytes\":%zu,\"JNI_and_initial_capture_explicit_doubles\":true,\"actual_Android_or_protocol_or_original_server\":false,\"world_authority\":false,\"sample_report\":%s}\n",checks,scenarios,wiped,max_report_bytes,sample_report);return 0;
}
