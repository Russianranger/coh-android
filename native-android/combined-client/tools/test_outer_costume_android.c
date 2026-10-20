/* The shipping new-profile observer, with explicit JNI/transport API doubles.
 * Engine tests separately execute whole original source senders. This fixture
 * composes the retained original sender header to isolate owner integration. */
#define COH_CLIENT_SLOTS_TEST_MAIN retained_client_slot_suite_not_executed
#include "test_client_slots_android.c"
static unsigned outer_cases;
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
 if(truncate)multi_bits-=truncate;
 slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
 active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},multi_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
 const CohOriginalEntCostumeReport *r=&active->initial_outer;outer_cases++;
 CHECK(active->costume_bodies_expected==bodies&&active->costume_bodies_read==bodies);
 CHECK(r->begin_bit==active->initial_costume.begin_bit&&r->selected_complete&&r->selected_body==selected);
 CHECK(active->selected_costume.bodytype==selected%9&&active->selected_costume.part_count==0);
 CHECK(!r->entity_complete&&!r->message_complete&&r->end_bit==multi_bits);
 CHECK(r->appearance_complete==(truncate<2)&&r->xlucency_complete==!truncate);
 CHECK(r->status==(truncate?COH_INVALID:COH_OK));
 CHECK(strstr(report(),"\"costume_outer\":")&&strstr(report_text,"\"selected_costume\":[1,"));
 CHECK(strstr(report_text,"\"initial_observed\":true")&&strstr(report_text,"\"ack_permitted\":false")&&!strstr(report_text,"REPORT_LIMIT"));
 if(!truncate)CHECK(strstr(report_text,"\"costume_next\":\"Entity suffix\""));
 #define RECEIVE_MAX(name,value) active->receive.name=COH_RECEIVE_COUNT_MAX;
 COH_RECEIVE_FIELDS(RECEIVE_MAX)
 #undef RECEIVE_MAX
 stress_request=1;CHECK(strlen(report())<7168&&!strstr(report_text,"REPORT_LIMIT")&&strstr(report_text,"\"selected_costume\":[1,"));stress_request=0;
 JNI(disconnect)(&env,NULL,current);CHECK(active->initial_outer.selected_complete&&active->selected_costume.bodytype==selected%9);finish();CHECK(!map_live&&!live);
}
int main(int argc,char **argv){
 CHECK(argc==3);
 for(unsigned bodies=1;bodies<=10;bodies++)for(unsigned selected=0;selected<bodies;selected++)for(unsigned truncate=0;truncate<3;truncate++)outer_capture(argv[1],bodies,selected,truncate);
 CHECK(opens==closed_files&&asset_opens==asset_closes&&maps==unmaps&&!map_live&&!live&&freed==wiped);
 printf("{\"passed\":true,\"checks\":%u,\"outer_cases\":%u,\"interop_owner_bytes\":%zu,\"snapshot_bytes\":%zu,\"report_peak_bytes\":%zu,\"stack_reserve\":8192,\"initial_limit\":8388608,\"physical_packet_replayed\":false,\"entity_or_message_complete\":false}\n",checks,outer_cases,sizeof(Interop),sizeof(CohOriginalCostumeSnapshot),max_report_bytes);return 0;
}
