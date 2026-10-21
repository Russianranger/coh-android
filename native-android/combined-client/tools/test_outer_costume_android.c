/* The shipping new-profile observer, with explicit JNI/transport API doubles.
 * Engine tests separately execute whole original source senders. This fixture
 * composes the retained original sender header to isolate owner integration. */
#define COH_CLIENT_SLOTS_TEST_MAIN retained_client_slot_suite_not_executed
#include "test_client_slots_android.c"
CohStatus coh_initial_capture_local_password_digest(CohInitialCapture*owner,const uint8_t digest[16]){static const uint8_t empty[]={0xd4,0x1d,0x8c,0xd9,0x8f,0x00,0xb2,0x04,0xe9,0x80,0x09,0x98,0xec,0xf8,0x42,0x7e};CHECK(owner&&digest&&!memcmp(digest,empty,16));return COH_OK;}
static size_t observer_continuation_charge;static unsigned observer_finish_calls;
size_t coh_initial_capture_continuation_bytes(const CohInitialCapture*owner){CHECK(owner);return observer_continuation_charge;/* Optional replay charges the measured real product owner. */}
CohStatus coh_initial_capture_finish_initial(const CohInitialCapture*owner,const CohInitialCaptureEvent*event,size_t bits){CHECK(owner&&event&&event->kind==COH_INITIAL_CAPTURE_ALLENTS&&bits==loan.reader.bits);observer_finish_calls++;return COH_OK;}
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
static unsigned observer_partial_calls;
CohStatus coh_initial_capture_finish_partial_tail(const CohInitialCapture*owner,const CohInitialCaptureEvent*event,size_t update,size_t begin,size_t body,uint32_t command){CHECK(owner&&event&&event->kind==COH_INITIAL_CAPTURE_ALLENTS&&update<=begin&&begin<body&&body<loan.reader.bits&&command);observer_partial_calls++;return COH_OK;}
#endif
static unsigned outer_cases;static size_t last_power_begin,last_full_bits,last_inventory_begin,last_inventory_end;
static const char *outer_report(void){CHECK(JNI(report)(&env,NULL,current));CHECK(strstr(report_text,"coh-native-initial-interop-numeric-v1")&&!strstr(report_text,"PRIVATE_")&&!strstr(report_text,"909090"));CHECK(strstr(report_text,"\"world_authority\":false")&&strstr(report_text,"\"ack_permitted\":false"));return report_text;}
static unsigned char replay_output[COH_INITIAL_REPLAY_BYTES+COH_INITIAL_REPLAY_HEADER_BYTES];
static jsize replay_output_bytes;static unsigned replay_fault,replay_sets,replay_deletes;
static jbyteArray replay_new(JNIEnv *e,jsize count){(void)e;CHECK(count>0&&(size_t)count<=sizeof(replay_output));if(replay_fault==1){exception_pending=1;return NULL;}replay_output_bytes=count;return replay_output;}
static void replay_set(JNIEnv *e,jbyteArray target,jsize at,jsize count,const jbyte *data){(void)e;CHECK(target==replay_output&&at>=0&&count>=0&&at<=replay_output_bytes-count);replay_sets++;if(replay_fault==replay_sets+1){exception_pending=1;return;}memcpy(replay_output+at,data,(size_t)count);}
static void replay_delete(JNIEnv *e,jobject value){(void)e;CHECK(value==replay_output);replay_deletes++;}
static jbyteArray replay_export(void){struct JNINativeInterface_ table=methods;table.NewByteArray=replay_new;table.SetByteArrayRegion=replay_set;table.DeleteLocalRef=replay_delete;JNIEnv capture_env=&table;replay_sets=0;return JNI(exportInitialReplay)(&capture_env,NULL,current);}
static uint64_t replay_word64(const uint8_t *p){uint64_t value=0;for(unsigned i=0;i<8;i++)value|=(uint64_t)p[i]<<(8*i);return value;}
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
static jbyteArray costume_export(void){struct JNINativeInterface_ table=methods;table.NewByteArray=replay_new;table.SetByteArrayRegion=replay_set;table.DeleteLocalRef=replay_delete;JNIEnv capture_env=&table;replay_sets=0;return JNI(observedSelfCostume)(&capture_env,NULL,current);}
static void check_costume_snapshot(void){
 const size_t bytes=32+sizeof(active->selected_costume);size_t retained=initial_retained(active),saved_charge=observer_continuation_charge;
 CHECK(bytes==48384&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==(jlong)retained);
 CHECK(costume_export()==replay_output&&replay_output_bytes==(jsize)bytes&&replay_sets==2);
 CHECK(!memcmp(replay_output,"COHCST01",8)&&load32(replay_output+8)==32&&load32(replay_output+12)==48352&&replay_word64(replay_output+16)==(uint64_t)current&&load32(replay_output+24)==active->initial_create.entity_index&&!load32(replay_output+28));
 CHECK(!memcmp(replay_output+32,&active->selected_costume,sizeof(active->selected_costume)));replay_output[32]^=1;CHECK(memcmp(replay_output+32,&active->selected_costume,sizeof(active->selected_costume)));
 for(replay_fault=1;replay_fault<=3;replay_fault++){unsigned deleted=replay_deletes;CHECK(!costume_export()&&exception_pending);CHECK(replay_deletes==deleted+(replay_fault!=1));exception_pending=0;}replay_fault=0;
 active->busy=1;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);active->busy=0;
 active->suspended=1;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);active->suspended=0;
 active->disconnected=1;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);active->disconnected=0;
 exception_pending=1;CHECK(!costume_export());exception_pending=0;
 uint32_t selected=active->initial_outer.selected_complete;active->initial_outer.selected_complete=0;CHECK(!costume_export());active->initial_outer.selected_complete=selected;
 uint32_t matched=active->initial_create.self_dbid_matches_handoff;active->initial_create.self_dbid_matches_handoff=0;CHECK(!costume_export());active->initial_create.self_dbid_matches_handoff=matched;
 jlong saved_token=current;current++;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);current=saved_token;
 observer_continuation_charge=8u*1024u*1024u;CHECK(!costume_export());observer_continuation_charge=SIZE_MAX;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);observer_continuation_charge=saved_charge;
 size_t saved_mapped=active->client_slots.mapped_bytes;active->client_slots.mapped_bytes=SIZE_MAX;CHECK(!costume_export()&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==-1);active->client_slots.mapped_bytes=saved_mapped;
 CHECK(costume_export()==replay_output&&JNI(observedSelfCostumeSourceBytes)(&env,NULL,current)==(jlong)retained);
}
static void check_partial_predicate(void){
 CohOriginalEntCostumeReport saved_outer=active->initial_outer;CohOriginalRareReport saved_rare=active->initial_rare;CohOriginalInitialTailReport saved_tail=active->initial_packet_tail;CohOriginalCommandTailReport saved_command=active->initial_commands;size_t saved_bits=active->initial_bits;
 active->initial_outer.selected_complete=active->initial_rare.entity_suffix_complete=active->initial_packet_tail.source_tail_complete=1;active->initial_packet_tail.end_bit=100;active->initial_bits=200;
 active->initial_commands=(CohOriginalCommandTailReport){0};CohOriginalCommandTailReport*r=&active->initial_commands;r->status=COH_UNSUPPORTED;r->unimplemented_handler=1;r->active_command=4;r->command_begin_bit=101;r->end_bit=110;CHECK(initial_partial_eligible(active));
 r->unknown_command=1;CHECK(!initial_partial_eligible(active));r->unknown_command=0;r->unimplemented_handler=0;CHECK(!initial_partial_eligible(active));r->unimplemented_handler=1;
 for(unsigned status=0;status<=7;status++){r->status=(CohStatus)status;CHECK(initial_partial_eligible(active)==(status==COH_UNSUPPORTED));}r->status=COH_UNSUPPORTED;
 r->terminator=1;CHECK(!initial_partial_eligible(active));r->terminator=0;r->tail_complete=1;CHECK(!initial_partial_eligible(active));r->tail_complete=0;
 r->active_command=0;CHECK(!initial_partial_eligible(active));r->active_command=4;r->command_begin_bit=99;CHECK(!initial_partial_eligible(active));r->command_begin_bit=110;CHECK(!initial_partial_eligible(active));r->command_begin_bit=101;r->end_bit=200;CHECK(!initial_partial_eligible(active));r->end_bit=110;
 active->initial_outer.selected_complete=0;CHECK(!initial_partial_eligible(active));active->initial_outer.selected_complete=1;active->initial_rare.entity_suffix_complete=0;CHECK(!initial_partial_eligible(active));active->initial_rare.entity_suffix_complete=1;active->initial_packet_tail.source_tail_complete=0;CHECK(!initial_partial_eligible(active));
 active->initial_outer=saved_outer;active->initial_rare=saved_rare;active->initial_packet_tail=saved_tail;active->initial_commands=saved_command;active->initial_bits=saved_bits;
}
#endif
static unsigned char sized_packet[COH_INITIAL_REPLAY_BYTES+1];static size_t sized_bytes;static unsigned alias_source;
static CohStatus sized_observe(void *context,const CohInitialCapture *c,const CohInitialCaptureEvent *event){
 CHECK(event->kind==COH_INITIAL_CAPTURE_ALLENTS);Interop *h=context;
 loan.reader.bytes=(CohBytes){alias_source?h->initial_replay:sized_packet,sized_bytes};loan.reader.bits=multi_bits;
 return observe(context,c,event);
}
static void check_replay(void){
 CHECK(active->replay_bytes==sizeof(multi_packet)&&!memcmp(active->initial_replay,multi_packet,sizeof(multi_packet)));
 CHECK(replay_export()==replay_output&&replay_output_bytes==(jsize)(COH_INITIAL_REPLAY_HEADER_BYTES+sizeof(multi_packet)));
 CHECK(!memcmp(replay_output,"COHIRP01",8)&&load32(replay_output+8)==88&&load32(replay_output+12)==sizeof(multi_packet));
 CHECK(replay_word64(replay_output+16)==multi_bits&&replay_word64(replay_output+24)==COH_PARTCOUNT_JNI_FIXTURE_POST_COMMAND);
 CHECK(replay_word64(replay_output+32)==active->initial_costume.begin_bit&&load32(replay_output+40)==0&&load32(replay_output+44)==active->initial_costume_slots.current&&load32(replay_output+48)==28&&load32(replay_output+52)==COH_REP_ALLENTS);
 unsigned char digest[32];CHECK(SHA256(multi_packet,sizeof(multi_packet),digest)&&!memcmp(digest,replay_output+56,32));CHECK(!memcmp(replay_output+88,multi_packet,sizeof(multi_packet)));
 active->busy=1;CHECK(!replay_export());active->busy=0;
 for(replay_fault=1;replay_fault<=3;replay_fault++){unsigned deleted=replay_deletes;CHECK(!replay_export()&&exception_pending);CHECK(replay_deletes==deleted+(replay_fault!=1));exception_pending=0;}replay_fault=0;
 CHECK(replay_export()==replay_output);
}
static void outer_capture(const char *path,unsigned bodies,unsigned selected,unsigned truncate){
 fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;
 const size_t begin=COH_PARTCOUNT_JNI_FIXTURE_BODY_BEGIN,end=COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_END;
 partcount_scalar(COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_BEGIN,1,1);partcount_scalar(COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_COUNT_BEGIN,4,0);
 memset(multi_packet,0,sizeof(multi_packet));
 for(size_t bit=0;bit<begin;bit++)set_bits(multi_packet,bit,1,(partcount_packet[bit/8]>>(bit%8))&1u);
 set_bits(multi_packet,COH_COSTUME_SLOTS_JNI_FIXTURE_CURRENT_BEGIN,8,selected);
 set_bits(multi_packet,COH_COSTUME_SLOTS_JNI_FIXTURE_MULTIPLE_BEGIN,1,1);set_bits(multi_packet,COH_COSTUME_SLOTS_JNI_FIXTURE_COUNT_BEGIN,4,bodies);
 multi_bits=begin;
 for(unsigned body=0;body<bodies;body++){
  size_t body_begin=multi_bits;for(size_t bit=begin;bit<end;bit++)set_bits(multi_packet,multi_bits++,1,(partcount_packet[bit/8]>>(bit%8))&1u);
  set_bits(multi_packet,body_begin+COH_PARTCOUNT_JNI_FIXTURE_BODYTYPE_BEGIN-begin,6,body%9);
 }
 /* Source SupergroupCostume0, specialFX0, NPCfallthrough0, Xlucency0. */
 for(unsigned i=0;i<4;i++)set_bits(multi_packet,multi_bits++,1,0);
 last_power_begin=multi_bits;
 /* Original PowerCust absent, titles absent, ragdoll absent, unchanged stats
  * when the earlier authentic pchar flag is present. */
 unsigned pchar=(partcount_packet[COH_PARTCOUNT_JNI_FIXTURE_AI_END/8]>>(COH_PARTCOUNT_JNI_FIXTURE_AI_END%8))&1u;
 for(unsigned i=0;i<3+pchar;i++)set_bits(multi_packet,multi_bits++,1,0);
 /* The source Auto0 encoding is bin0 + two zero value bits. Exercise empty
  * vision flags, and the original absent target/status/inventory branches. */
 for(unsigned i=0;i<3+pchar;i++){set_bits(multi_packet,multi_bits,4,0);multi_bits+=4;}
 if(pchar)for(unsigned i=0;i<3;i++)set_bits(multi_packet,multi_bits++,1,0);
 /* Original architect absent, flashback Pack1 zero, parameters absent. */
 for(unsigned i=0;i<3;i++)set_bits(multi_packet,multi_bits++,1,0);
 last_full_bits=multi_bits;if(truncate)multi_bits-=truncate;
 slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
 active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},multi_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
 const CohOriginalEntCostumeReport *r=&active->initial_outer;outer_cases++;
 CHECK(active->costume_bodies_expected==bodies&&active->costume_bodies_read==bodies);
 CHECK(r->begin_bit==active->initial_costume.begin_bit&&r->selected_complete&&r->selected_body==selected);
 CHECK(active->selected_costume.bodytype==selected%9&&active->selected_costume.part_count==0);
 CHECK(!r->entity_complete&&!r->message_complete&&r->end_bit<=multi_bits);
 CHECK(r->appearance_complete&&r->xlucency_complete&&r->power_complete);
 CHECK(r->status==(truncate?COH_INVALID:COH_OK));
 CHECK(strstr(outer_report(),"\"costume_outer\":")&&strstr(report_text,"\"selected_costume\":[1,"));
 CHECK(strstr(report_text,"\"initial_observed\":true")&&strstr(report_text,"\"ack_permitted\":false")&&!strstr(report_text,"REPORT_LIMIT"));
 if(!truncate)CHECK(strstr(report_text,"\"costume_next\":\"later very-rare entity fields\"")&&strstr(report_text,"\"costume_next_kind\":\"implementation remaining\"")&&r->titles_complete&&r->ragdoll_complete&&r->basic_stats_complete&&r->vision_complete&&r->taskforce_complete&&r->end_bit==multi_bits);
 check_replay();CHECK(strstr(outer_report(),"\"packet_copy_retained\":true")&&strstr(report_text,"\"initial_replay\":[8192,0]"));
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
 if(outer_cases==1){check_costume_snapshot();check_partial_predicate();}
#endif
 #define RECEIVE_MAX(name,value) active->receive.name=COH_RECEIVE_COUNT_MAX;
 COH_RECEIVE_FIELDS(RECEIVE_MAX)
 #undef RECEIVE_MAX
 stress_request=1;CHECK(strlen(outer_report())<7168&&!strstr(report_text,"REPORT_LIMIT")&&strstr(report_text,"\"selected_costume\":[1,"));stress_request=0;
 JNI(disconnect)(&env,NULL,current);CHECK(active->initial_outer.selected_complete&&active->selected_costume.bodytype==selected%9&&!active->replay_bytes&&!replay_export());
 for(size_t i=0;i<sizeof(active->initial_replay);i++)CHECK(!active->initial_replay[i]);
 finish();CHECK(!map_live&&!live);
}
static void replay_bounds(const char *path){
 memset(sized_packet,0,sizeof(sized_packet));memcpy(sized_packet,multi_packet,sizeof(multi_packet));
 for(unsigned kind=0;kind<3;kind++){
  fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;sized_bytes=COH_INITIAL_REPLAY_BYTES+(kind==1);alias_source=kind==2;
  slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
  active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},sized_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
  CHECK(strstr(outer_report(),"\"initial_observed\":true"));
  if(kind==0){CHECK(active->replay_bytes==65536&&!active->replay_omitted&&replay_export()==replay_output&&replay_output_bytes==65624);CHECK(!memcmp(replay_output+88,sized_packet,65536));}
  else {CHECK(!active->replay_bytes&&active->replay_omitted==(kind==1?1u:3u)&&!replay_export());}
  JNI(suspend)(&env,NULL,current);CHECK(!active->replay_bytes);finish();CHECK(!map_live&&!live);
 }
 alias_source=0;
}
static void test_auto(size_t *at,uint32_t value){const unsigned widths[]={2,10,24,32};unsigned bin=0;while(bin<3&&value>=(1u<<widths[bin]))bin++;set_bits(multi_packet,*at,2,bin);*at+=2;set_bits(multi_packet,*at,widths[bin],value);*at+=widths[bin];}
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
/* Maximum-width projection only: this explicit transport double does not send. */
static void bounded_report_stress(void){
 CohInitialContinuation saved=capture.d.continuation,*c=&capture.d.continuation;memset(c,0,sizeof(*c));
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
 CohOriginalInitialTailReport saved_tail=active->initial_packet_tail;CohOriginalCommandTailReport saved_command=active->initial_commands;uint64_t saved_bits=active->initial_bits;
#endif
 c->full_update_ack_queued=c->client_ready_queued=c->full_update_ack_sent=c->client_ready_sent=c->waiting_for_full_update=1;
 c->post_messages=128;c->post_rows=16;c->post_row_overflow=16;c->post_window_complete=1;c->abort_reason=COH_INITIAL_ABORT_MESSAGE_LIMIT;
 c->post_begin_ms=UINT64_MAX-20000;c->post_end_ms=UINT64_MAX;c->post_first_ms=UINT64_MAX-19999;c->post_last_ms=UINT64_MAX;c->post_between_sends=1;
 for(unsigned i=0;i<16;i++){CohInitialPostCommand*r=&c->post[i];r->kind=(CohInitialCaptureCommandKind)(i+2);r->count=7;r->min_bytes=r->max_bytes=4194304;r->total_bytes=UINT64_C(7)*4194304;r->total_bits=r->total_bytes*8;c->post_total_bytes+=r->total_bytes;c->post_total_bits+=r->total_bits;}
 c->post_overflow_bytes=UINT64_C(16)*4194304;c->post_overflow_bits=c->post_overflow_bytes*8;c->post_total_bytes+=c->post_overflow_bytes;c->post_total_bits+=c->post_overflow_bits;
 c->ack_delivery=(CohInitialDelivery){UINT64_MAX-20001,UINT64_MAX-20000,UINT64_MAX-19000,65536,16384,131072,3,2,1,1,0,COH_OK,0};c->ready_delivery=c->ack_delivery;c->ready_delivery.first_sent_ms++;
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
 c->post_response_begin_ms=UINT64_MAX-19999;c->post_ready_messages=126;
 c->source_entity_update_complete=c->partial_tail=c->diagnostic_ack_intent=1;c->skipped_tail_command=UINT32_MAX;c->source_update_end_bit=33554400;c->tail_command_begin_bit=33554401;c->tail_body_begin_bit=33554403;c->tail_remaining_bits=29;
 active->initial_packet_tail.source_tail_complete=1;active->initial_bits=33554432;active->initial_commands=(CohOriginalCommandTailReport){.status=COH_UNSUPPORTED,.begin_bit=33554400,.command_begin_bit=33554401,.end_bit=33554403,.active_command=UINT32_MAX,.commands_read=UINT32_MAX,.unimplemented_handler=1};
#endif
 #define BOUNDED_STRESS(name,value) active->receive.name=COH_RECEIVE_COUNT_MAX;
 COH_RECEIVE_FIELDS(BOUNDED_STRESS)
 #undef BOUNDED_STRESS
 stress_request=1;CHECK(JNI(report)(&env,NULL,current)&&strlen(report_text)<7168&&!strstr(report_text,"REPORT_LIMIT")&&!strstr(report_text,"REPORT_UNAVAILABLE")&&!strstr(report_text,"report_core_limit"));
 CHECK(strstr(report_text,"\"initial_observed\":true")&&strstr(report_text,"\"power_unresolved\":[343,343,")&&strstr(report_text,"\"post_totals\":[128,536870912,4294967296,")&&strstr(report_text,"\"ack_delivery\":[")&&strstr(report_text,"\"ready_delivery\":[")&&strstr(report_text,"\"continuation_abort\":\"message limit\""));stress_request=0;capture.d.continuation=saved;
#ifdef COH_INITIAL_ACK_FALLBACK_DIAGNOSTIC
 CHECK(strstr(report_text,"\"initial_packet_complete\":false")&&strstr(report_text,"\"initial_partial_tail\":[1,1,0,1,4294967295,33554400,33554401,33554403,29,1]")&&strstr(report_text,"\"sends_ready\":true")&&strstr(report_text,"\"ack_permitted\":false"));active->initial_packet_tail=saved_tail;active->initial_commands=saved_command;active->initial_bits=saved_bits;
#endif
}
#endif
static void unresolved_power(const char *path,unsigned count){
 fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;
 uint8_t tail[128]={0};size_t tail_bits=last_full_bits-last_power_begin-1;CHECK(tail_bits<=sizeof(tail)*8);
 for(size_t bit=0;bit<tail_bits;bit++)set_bits(tail,bit,1,(multi_packet[(last_power_begin+1+bit)/8]>>((last_power_begin+1+bit)%8))&1u);
 size_t at=last_power_begin;
 /* Whole original source tolerates NULL BasePower: CRC, tint, tint and token
  * still consume their original framing. No dictionary is required to drain. */
 set_bits(multi_packet,at++,1,1);set_bits(multi_packet,at,2,1);at+=2;set_bits(multi_packet,at++,1,1);
 set_bits(multi_packet,at,8,0);at+=8;set_bits(multi_packet,at,8,1);at+=8;set_bits(multi_packet,at++,1,0);set_bits(multi_packet,at++,1,1);test_auto(&at,count);
 for(unsigned i=0;i<count;i++){test_auto(&at,0x80443357u+i);test_auto(&at,i);test_auto(&at,i+1);set_bits(multi_packet,at,8,0);at+=8;}
 size_t power_end=at;
 for(size_t bit=0;bit<tail_bits;bit++)set_bits(multi_packet,at++,1,(tail[bit/8]>>(bit%8))&1u);
 multi_bits=at;CHECK(multi_bits<=sizeof(multi_packet)*8);
 slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
 active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},multi_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
 CHECK(active->initial_outer.status==COH_OK&&active->initial_outer.field==COH_ENT_COSTUME_RARE_PREFIX&&!active->initial_outer.required_table);
 CHECK(active->initial_outer.power_complete&&active->initial_outer.power_entries_read==count&&active->initial_outer.power_unresolved_count==count);
 CHECK(active->initial_outer.power_first_unresolved_crc==0x80443357u&&active->initial_outer.power_last_unresolved_crc==0x80443357u+count-1);
 CHECK(active->initial_outer.power_end_bit==power_end&&active->initial_outer.end_bit==multi_bits&&active->initial_outer.selected_complete);
 CHECK(active->initial_outer.power_scratch_bytes>0&&active->initial_outer.power_scratch_bytes<=COH_ORIGINAL_COSTUME_WORKSPACE_BYTES);
 last_inventory_begin=active->initial_outer.inventory_begin_bit;last_inventory_end=active->initial_outer.inventory_end_bit;
 CHECK(strstr(outer_report(),"\"costume_next_kind\":\"implementation remaining\"")&&strstr(report_text,"\"power_unresolved\":["));
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
 bounded_report_stress();
#endif
 check_replay();finish();CHECK(!map_live&&!live);
}
static void test_pack(size_t *at,unsigned width,uint32_t value){while(width<32&&value>=(UINT32_C(1)<<width)-1u){uint32_t step=(UINT32_C(1)<<width)-1u;set_bits(multi_packet,*at,width,step);*at+=width;value-=step;width=width>16?32:width*2;}set_bits(multi_packet,*at,width,value);*at+=width;}
static void inventory_and_rare(const char *path,const char *suffix){
 static uint8_t original[sizeof(multi_packet)],source[sizeof(multi_packet)];uint8_t header[4];
 FILE *file=fopen(suffix,"rb");CHECK(file&&fread(header,1,4,file)==4);size_t source_bits=load32(header),source_bytes=(source_bits+7)/8;
 CHECK(source_bits&&source_bytes<=sizeof(source)&&fread(source,1,source_bytes,file)==source_bytes&&fgetc(file)==EOF&&!fclose(file));
 CHECK(last_inventory_begin&&last_inventory_end==last_inventory_begin+1);memcpy(original,multi_packet,sizeof(original));size_t old_end=multi_bits;
 size_t at=last_inventory_begin;test_pack(&at,1,1);test_pack(&at,3,1);test_pack(&at,8,UINT32_MAX);test_pack(&at,8,10);test_pack(&at,8,20);test_pack(&at,8,30);size_t inventory_end=at;
 for(size_t bit=last_inventory_end;bit<old_end;bit++)set_bits(multi_packet,at++,1,(original[bit/8]>>(bit%8))&1u);
 size_t rare_begin=at;for(size_t bit=0;bit<source_bits;bit++)set_bits(multi_packet,at++,1,(source[bit/8]>>(bit%8))&1u);CHECK(at<=sizeof(multi_packet)*8);
 for(unsigned trim=0;trim<3;trim++){
  multi_bits=at-(trim==2?8:trim);fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;slot_begin();
  CHECK(JNI(service)(&env,NULL,current,101)==COH_OK&&JNI(choose)(&env,NULL,current,2,102)==COH_OK&&JNI(service)(&env,NULL,current,103)==COH_OK);
  active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},multi_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
  CHECK(active->initial_outer.status==COH_OK&&active->initial_outer.inventory_begin_bit==last_inventory_begin&&active->initial_outer.inventory_end_bit==inventory_end);
  CHECK(active->initial_outer.inventory_count==1&&active->initial_outer.inventory_values_read==4&&active->initial_outer.inventory_negative_words==1);
  CHECK(active->initial_rare.begin_bit==rare_begin&&active->initial_rare.end_bit<=multi_bits&&!active->initial_outer.entity_complete&&!active->initial_outer.message_complete);
  CHECK(active->initial_rare.status==(trim?COH_INVALID:COH_OK)&&active->initial_rare.entity_suffix_complete==!trim);
  if(!trim)CHECK(active->initial_rare.end_bit==at&&active->initial_rare.stage==COH_ORIGINAL_RARE_COMPLETE&&strstr(outer_report(),"\"initial_suffix_next\":\"entity list sentinel\""));
  static const CohOriginalRareWorkspace zero;CHECK(!memcmp(&active->rare_workspace,&zero,sizeof(zero)));
  CHECK(strstr(outer_report(),"\"initial_observed\":true")&&strstr(report_text,"\"inventory_words\":[")&&strstr(report_text,"\"rare_suffix\":[")&&!strstr(report_text,"REPORT_LIMIT"));
  check_replay();finish();CHECK(!map_live&&!live);
 }
}

#ifndef COH_OUTER_TEST_MAIN
#define COH_OUTER_TEST_MAIN main
#endif
int COH_OUTER_TEST_MAIN(int argc,char **argv){
 CHECK(argc==3);
 for(unsigned bodies=1;bodies<=10;bodies++)for(unsigned selected=0;selected<bodies;selected++)for(unsigned truncate=0;truncate<3;truncate++)outer_capture(argv[1],bodies,selected,truncate);
 replay_bounds(argv[1]);
 unresolved_power(argv[1],343);
 inventory_and_rare(argv[1],argv[2]);
 CHECK(opens==closed_files&&asset_opens==asset_closes&&maps==unmaps&&!map_live&&!live&&freed==wiped);
 printf("{\"passed\":true,\"checks\":%u,\"outer_cases\":%u,\"interop_owner_bytes\":%zu,\"snapshot_bytes\":%zu,\"report_peak_bytes\":%zu,\"stack_reserve\":%u,\"initial_limit\":8388608,\"physical_packet_replayed\":false,\"entity_or_message_complete\":false}\n",checks,outer_cases,sizeof(Interop),sizeof(CohOriginalCostumeSnapshot),max_report_bytes,COH_ORIGINAL_INITIAL_STACK_RESERVE);return 0;
}
