/* Actual saved INITIAL through the shipping JNI observer. Selection/session
 * are explicit test owners; this does not assert live handoff authentication. */
#define COH_OUTER_TEST_MAIN retained_outer_fixture_main
#include "test_outer_costume_android.c"
#include <sys/socket.h>
#include "actual-initial-source-fixture.h"
static unsigned actual_network_calls;
static uint8_t actual_packet[65536];static size_t actual_bytes,actual_bits,actual_post;static uint32_t actual_dbid;static unsigned actual_variant;
int __wrap_socket(int a,int b,int c){(void)a;(void)b;(void)c;actual_network_calls++;abort();}
ssize_t __wrap_sendto(int a,const void*b,size_t n,int f,const struct sockaddr*s,socklen_t l){(void)a;(void)b;(void)n;(void)f;(void)s;(void)l;actual_network_calls++;abort();}
static CohStatus actual_observe(void *context,const CohInitialCapture*c,const CohInitialCaptureEvent*e){
 CHECK(e->kind==COH_INITIAL_CAPTURE_ALLENTS);loan.reader=(CohRepReader){{actual_packet,actual_bytes},actual_bits-(actual_variant==5),actual_post,1,COH_REP_BOUNDED_MESSAGE_MAX};
 loan.schema.count=sizeof(actual_shortcuts)/sizeof(actual_shortcuts[0]);memcpy(loan.schema.entries,actual_shortcuts,sizeof(actual_shortcuts));loan.selected_dbid=actual_dbid+(actual_variant==1);loan.message_id=17;
 CohRepReader prefix=loan.reader;CHECK(coh_rep_update_prefix(&prefix,&loan.schema,COH_REP_ALLENTS,&loan.update)==COH_OK);
 if(actual_variant==2)loan.selected_dbid_owner_bound=0;
 if(actual_variant==3)loan.groups_message_generation=55;
 if(actual_variant==4)loan.message_generation=loan.groups_message_generation;
 return observe(context,c,e);
}
int main(int argc,char**argv){
 CHECK(argc==3);observer_continuation_charge=COH_ACTUAL_CONTINUATION_BYTES;FILE*f=fopen(argv[2],"rb");uint8_t header[88],hash[32];CHECK(f&&fread(header,1,88,f)==88);CHECK(!memcmp(header,"COHIRP01",8)&&load32(header+8)==88);actual_bytes=load32(header+12);actual_bits=(size_t)replay_word64(header+16);actual_post=(size_t)replay_word64(header+24);CHECK(actual_bytes<=sizeof(actual_packet)&&fread(actual_packet,1,actual_bytes,f)==actual_bytes&&fgetc(f)==EOF&&!fclose(f));CHECK(SHA256(actual_packet,actual_bytes,hash)&&!memcmp(hash,header+56,32));CHECK((actual_bits==301656||actual_bits==303112)&&actual_post==32&&load32(header+40)==1);
 CohRepSchema schema={0};schema.count=sizeof(actual_shortcuts)/sizeof(actual_shortcuts[0]);memcpy(schema.entries,actual_shortcuts,sizeof(actual_shortcuts));CohRepReader prefix={{actual_packet,actual_bytes},actual_bits,actual_post,1,COH_REP_BOUNDED_MESSAGE_MAX};CohRepUpdatePrefix update;CHECK(coh_rep_update_prefix(&prefix,&schema,COH_REP_ALLENTS,&update)==COH_OK&&prefix.cursor==880);uint32_t index,u;CohEntFailure failure;CHECK(coh_ent_next_index(&prefix,-1,&index,&failure)==COH_OK&&index==(actual_bits==301656?127u:125u));
 /* Fixture identity only: read the original checkEntCreate identity prefix to
  * seed a test-owned selection context. No real DB/Map authority is inferred. */
 CHECK(coh_rep_read(&prefix,1,&u)==COH_OK&&u==1);CHECK(coh_rep_read(&prefix,1,&u)==COH_OK&&u==0);CHECK(coh_rep_pack(&prefix,12,&u)==COH_OK);CHECK(coh_rep_pack(&prefix,2,&u)==COH_OK&&u==2);CHECK(coh_rep_read(&prefix,1,&u)==COH_OK&&u==1);CHECK(coh_rep_pack(&prefix,1,&u)==COH_OK);CHECK(coh_rep_pack(&prefix,22,&actual_dbid)==COH_OK&&actual_dbid&&actual_dbid<INT32_MAX);
 unsigned complete_cases=0;size_t max_aggregate=0,source_update_end=0,original_bits=actual_bits;
 unsigned cases=6;
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
 cases=10;
#endif
 for(actual_variant=0;actual_variant<cases;actual_variant++){
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
  /* Test-owned tail mutation ONLY after the authentic source update ended.
   * 222 is original SERVER_COMBAT_MESSAGE, still unimplemented. 999 is not
   * an original dispatch case. These four cases are not physical evidence. */
  if(actual_variant>=6){size_t cursor=source_update_end;CHECK(cursor&&cursor<original_bits&&!(cursor&7));if(actual_variant==9){set_bits(actual_packet,cursor,16,222);cursor+=16;}else{uint32_t value=actual_variant==6?222u:actual_variant==7?999u:0u;/* Original byte-aligned Pack1 is32bits. */set_bits(actual_packet,cursor,32,value);cursor+=32;set_bits(actual_packet,cursor,8,0);cursor+=8;}actual_bits=cursor;}
#endif
  fixture();CHECK(slots_configure(argv[1])==COH_OK);slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK&&JNI(choose)(&env,NULL,current,2,102)==COH_OK&&JNI(service)(&env,NULL,current,103)==COH_OK);unsigned before=observer_finish_calls;
  active->busy=1;CohStatus status=coh_initial_capture_service(active->capture,104,(CohCancel){0},actual_observe,active,sizeof(*active));active->busy=0;
  if(actual_variant==0){
   CHECK(status==COH_UNSUPPORTED&&active->initial_create.header_validated&&active->initial_create.create_validated&&active->initial_create.is_self&&active->initial_create.self_dbid_matches_handoff);CHECK(active->initial_create.header_end_bit==880&&active->initial_create.create_end_bit==1536&&active->initial_costume.begin_bit==replay_word64(header+32));CHECK(active->initial_outer.power_entries_read==343&&active->initial_outer.power_unresolved_count==343&&!active->initial_outer.required_table);CHECK(active->initial_commands.tail_complete&&active->initial_commands.terminator&&active->initial_commands.end_bit==actual_bits&&initial_complete(active));CHECK(active->completion_status==COH_OK&&observer_finish_calls==before+1);CHECK(active->initial_packet_tail.peak_aggregate_bytes<8388608&&active->initial_packet_tail.peak_mapped_bytes==5996544);max_aggregate=active->initial_packet_tail.peak_aggregate_bytes;source_update_end=active->initial_packet_tail.end_bit;complete_cases++;
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
   check_costume_snapshot();check_partial_predicate();
#endif

  }else{CHECK(observer_finish_calls==before&&!initial_complete(active));if(actual_variant==1)CHECK(!active->initial_create.self_dbid_matches_handoff);if(actual_variant>=2&&actual_variant<=4)CHECK(status==COH_STATE);if(actual_variant==5)CHECK(active->initial_commands.status!=COH_OK&&!active->initial_commands.tail_complete);
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
   if(actual_variant>=6){CHECK(active->initial_outer.selected_complete&&active->initial_packet_tail.source_tail_complete&&active->initial_packet_tail.end_bit==source_update_end);CHECK(observer_partial_calls==1);if(actual_variant==6)CHECK(active->completion_status==COH_OK&&active->initial_commands.unimplemented_handler&&!active->initial_commands.unknown_command&&initial_partial_eligible(active));else CHECK(!initial_partial_eligible(active));}
#endif
  }
  CHECK(JNI(report)(&env,NULL,current)&&strlen(report_text)<7168&&!strstr(report_text,"REPORT_LIMIT"));CHECK(strstr(report_text,"\"world_authority\":false")&&strstr(report_text,"\"actor_publication\":false")&&strstr(report_text,"\"sends_ready\":false")&&strstr(report_text,"\"sends_full_update_ack\":false"));
  if(actual_variant==0){CHECK(strstr(report_text,"\"initial_observed\":true")&&strstr(report_text,"\"power_unresolved\":[343,343,")&&strstr(report_text,actual_bits==301656?"301656":"303112"));
   #define ACTUAL_STRESS(name,value) active->receive.name=COH_RECEIVE_COUNT_MAX;
   COH_RECEIVE_FIELDS(ACTUAL_STRESS)
   #undef ACTUAL_STRESS
   stress_request=1;CHECK(JNI(report)(&env,NULL,current)&&strlen(report_text)<7168&&!strstr(report_text,"REPORT_LIMIT")&&strstr(report_text,"\"initial_observed\":true")&&strstr(report_text,"\"power_unresolved\":[343,343,"));stress_request=0;
  }
  finish();CHECK(!map_live&&!live&&!tail_mapping);
 }
 (void)source_update_end;CHECK(!actual_network_calls&&observer_finish_calls==1&&complete_cases==1&&opens==closed_files&&asset_opens==asset_closes&&maps==unmaps&&freed==wiped);
 printf("{\"passed\":true,\"checks\":%u,\"cases\":%u,\"mutated_tail_cases\":%u,\"exact_end\":%zu,\"unresolved\":343,\"report_peak_bytes\":%zu,\"aggregate_peak_bytes\":%zu,\"interop_owner_bytes\":%zu,\"stack_reserve\":%u,\"real_continuation_charge\":%zu,\"socket_or_send_calls\":%u,\"completion_calls\":%u}\n",checks,cases,cases-6,original_bits,max_report_bytes,max_aggregate,sizeof(Interop),COH_ORIGINAL_INITIAL_STACK_RESERVE,observer_continuation_charge,actual_network_calls,observer_finish_calls);return 0;
}
