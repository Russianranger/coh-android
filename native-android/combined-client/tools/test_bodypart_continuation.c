/* Actual shipping observer/parser exercised with existing source-layout packet
 * fixture and explicit transport/JNI doubles. Historical suite main is not run. */
#define coh_request_tx_diagnostics retained_bodypart_tx_diagnostics
#define main prior_report_qualifier_not_executed
#include "../diagnostics/interop-adapter-20261018/test_interop_adapter.c"
#undef main
#undef coh_request_tx_diagnostics
static unsigned stress_request,report_peak;
void coh_request_tx_diagnostics(const CohRequestTxWitness*w,CohRequestTxDiagnostics*out){
 retained_bodypart_tx_diagnostics(w,out);
 if(stress_request){out->first_send_attempts=out->retry_send_attempts=out->successful_retries=out->deferred_send_callbacks=out->failed_send_callbacks=UINT32_MAX;out->queue_offset_ms=out->first_send_offset_ms=out->last_send_offset_ms=out->retirement_offset_ms=UINT64_MAX;}
}
#include "../app/src/main/cpp/interop_network.c"
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
static unsigned opens,closed_files,short_reads,interrupt_read,fail_read;
static unsigned capture_cycles;
int __real_open(const char*,int,...);int __real_close(int);ssize_t __real_read(int,void*,size_t);
int __wrap_open(const char*p,int flags,...){int fd=__real_open(p,flags);if(fd>=0)opens++;return fd;}
int __wrap_close(int fd){int s=__real_close(fd);if(!s)closed_files++;return s;}
ssize_t __wrap_read(int fd,void*p,size_t n){if(interrupt_read){interrupt_read=0;errno=EINTR;return-1;}if(fail_read){errno=EIO;return-1;}return __real_read(fd,p,short_reads&&n>7?7:n);}
ssize_t __wrap___read_chk(int fd,void*p,size_t n,size_t capacity){if(n>capacity){fprintf(stderr,"fortified read bound\n");exit(1);}return __wrap_read(fd,p,n);}
static jchar file_path[1024];static jsize file_length;
static jsize file_get_length(JNIEnv*e,jstring s){(void)e;(void)s;return file_length;}
static const jchar*file_get_chars(JNIEnv*e,jstring s,jboolean*c){(void)e;(void)s;(void)c;return file_path;}
static void file_release(JNIEnv*e,jstring s,const jchar*c){(void)e;(void)s;CHECK(c==file_path);}
static CohStatus configure(const char*p){
 size_t n=strlen(p);CHECK(n<1024);file_length=(jsize)n;for(size_t i=0;i<n;i++)file_path[i]=(unsigned char)p[i];
 struct JNINativeInterface_ table=methods;table.GetStringLength=file_get_length;table.GetStringChars=file_get_chars;table.ReleaseStringChars=file_release;JNIEnv local=&table;
 return(CohStatus)JNI(configureBodyPartsCache)(&local,NULL,file_path);
}
static uint32_t load32(const unsigned char*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void run_capture(unsigned explicit_count,const char*path,CohStatus consistency){
 fixture();partcount_fixture=1;capture_cycles++;
 if(path)CHECK(configure(path)==consistency);
 else CHECK(configured_bodyparts_status==COH_NOT_FOUND);
 unsigned at=COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_BEGIN;
 partcount_scalar(at++,1,explicit_count);if(explicit_count){partcount_scalar(at,4,1);at+=4;}
 /* First actual part geom: cache0,present1,indexed1. Stop BEFORE index Pack. */
 partcount_scalar(at,3,6);partcount_bits=at+3;
 start();CHECK(active->pinned_bodyparts==28&&active->bodyparts_cache_status==consistency);
 CHECK(configure("/ignored/while-active.bin")==COH_STATE);
 CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);
 CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
 const CohOriginalCostumeReport*c=&active->initial_costume_continuation;
 CHECK(active->costume_continuation_attempted&&c->count_validated&&c->bodytype_validated);
 CHECK(c->part_count==(explicit_count?1u:28u)&&c->status==COH_UNSUPPORTED&&c->dictionary_required==COH_ORIGINAL_COSTUME_STRINGS);
 CHECK(c->field==COH_ORIGINAL_COSTUME_GEOM&&!c->parts_read&&c->failure_bit==partcount_bits);
 const char*json=report();if(strlen(json)>report_peak)report_peak=(unsigned)strlen(json);CHECK(strstr(json,"\"bodyparts_default\":[0,28]")&&strstr(json,"\"costume_continuation\":[2,3,0,"));char expected_server[96];snprintf(expected_server,sizeof(expected_server),"\"bodyparts_server_cache_status\":%u",(unsigned)consistency);CHECK(strstr(json,expected_server));CHECK(strstr(json,"\"catalog_boundary\":null"));CHECK(strlen(json)<7168&&!strstr(json,"REPORT_LIMIT"));
 CHECK(JNI(observedSelfPose)(&env,NULL,current)==private_bytes&&byte_count==16);
 CHECK(load32((const unsigned char*)private_bytes)==active->initial_create.entity_index);
 uint32_t expected[3];memcpy(&expected[0],&active->initial_pose_sample.position.x,4);memcpy(&expected[1],&active->initial_pose_sample.position.y,4);memcpy(&expected[2],&active->initial_pose_sample.position.z,4);
 for(unsigned i=0;i<3;i++)CHECK(load32((const unsigned char*)private_bytes+4*(i+1))==expected[i]);
 active->initial_create.self_dbid_matches_handoff=0;CHECK(!JNI(observedSelfPose)(&env,NULL,current));active->initial_create.self_dbid_matches_handoff=1;
 active->initial_create.is_self=0;CHECK(!JNI(observedSelfPose)(&env,NULL,current));active->initial_create.is_self=1;
 active->initial_pose_sample.valid=0;CHECK(!JNI(observedSelfPose)(&env,NULL,current));active->initial_pose_sample.valid=1;
 active->busy=1;CHECK(!JNI(observedSelfPose)(&env,NULL,current));active->busy=0;
 #define RECEIVE_MAX(name,value) active->receive.name=COH_RECEIVE_COUNT_MAX;
 COH_RECEIVE_FIELDS(RECEIVE_MAX)
 #undef RECEIVE_MAX
 active->receive.sample_count=COH_RECEIVE_COUNT_MAX;active->receive.rx_pending=active->receive.max_rx_pending_sampled=COH_NET_RX_MAX;active->receive.fragment_groups=active->receive.max_fragment_groups_sampled=COH_NET_GROUP_MAX;active->receive.decode_failure_kind=COH_NET_DECODE_STREAM;active->receive.decode_compressed_bytes=COH_NET_MESSAGE_MAX;active->receive.decode_declared_raw_bytes=UINT32_MAX;active->receive.decode_output_budget=COH_NET_DECODED_MAX;stress_request=1;
 CHECK(strlen(report())<7168&&!strstr(report_text,"REPORT_LIMIT"));if(strlen(report_text)>report_peak)report_peak=(unsigned)strlen(report_text);stress_request=0;
 JNI(disconnect)(&env,NULL,current);CHECK(JNI(observedSelfPose)(&env,NULL,current));finish();CHECK(!JNI(observedSelfPose)(&env,NULL,current));
}
int main(int argc,char**argv){
 CHECK(argc==6);uint32_t count=99;
 CHECK(coh_local_bodypart_default_file(argv[1],&count)==COH_OK&&count==28);
 count=99;CHECK(coh_local_bodypart_default_file(argv[5],&count)==COH_OK&&count==28);
 for(unsigned i=2;i<5;i++){count=99;CHECK(coh_local_bodypart_default_file(argv[i],&count)==COH_STATE&&count==99);}
 count=99;CHECK(coh_local_bodypart_default_file("/no-such-cache/bodyparts.bin",&count)==COH_NOT_FOUND&&count==99);
 CHECK(coh_local_bodypart_default_file(NULL,&count)==COH_INVALID&&count==99);
 CHECK(coh_local_bodypart_default_file(argv[1],NULL)==COH_INVALID);
 CHECK(coh_local_bodypart_default_file("relative.bin",&count)==COH_INVALID&&count==99);
 CHECK(coh_local_bodypart_default_file(argv[1],(uint32_t*)(void*)argv[1])==COH_INVALID);
 short_reads=interrupt_read=1;CHECK(coh_local_bodypart_default_file(argv[1],&count)==COH_OK&&count==28);short_reads=0;
 fail_read=1;count=99;CohStatus injected=coh_local_bodypart_default_file(argv[1],&count);CHECK(injected==COH_IO&&count==99);fail_read=0;
 for(unsigned i=0;i<16;i++){run_capture(0,argv[1],COH_OK);run_capture(1,argv[1],COH_OK);}
 /* Optional comparison absent, missing, mismatched, invalid or timestamp-only:
  * both default and explicit framing still use the same verified CLIENT count. */
 for(unsigned explicit_count=0;explicit_count<2;explicit_count++){
  run_capture(explicit_count,NULL,COH_NOT_FOUND);
  run_capture(explicit_count,"/no-such-cache/bodyparts.bin",COH_NOT_FOUND);
  run_capture(explicit_count,argv[2],COH_STATE);
  run_capture(explicit_count,"",COH_INVALID);
  run_capture(explicit_count,argv[5],COH_OK);
 }
 CHECK(opens==closed_files&&!live);
 printf("{\"checks\":%u,\"capture_cycles\":%u,\"file_opens\":%u,\"file_closes\":%u,\"report_peak_bytes\":%u,\"interop_owned_bytes\":%zu,\"workspace_bytes\":%zu,\"default_count\":28,\"first_real_unknown_dictionary\":1,\"raw_physical_packet_replayed\":false}\n",checks,capture_cycles,opens,closed_files,report_peak,sizeof(Interop),sizeof(CohOriginalCostumeWorkspace));return 0;
}
