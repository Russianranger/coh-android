/* Focused new report regression. Old qualifier main is deliberately not run.
 * Core/JNI/socket/provider doubles are explicit; probe parsers and formatters
 * are the production sources over the retained source-layout sender fixture. */
#define coh_initial_capture_command_name retained_default_command_name
#define coh_request_tx_diagnostics retained_default_tx_diagnostics
#define main previous_qualifier_not_executed
#include "../diagnostics/interop-adapter-20261018/test_interop_adapter.c"
#undef main
#undef coh_request_tx_diagnostics
#undef coh_initial_capture_command_name
static unsigned maximum_request;
const char *coh_initial_capture_command_name(CohInitialCaptureCommandKind kind) {
    if(!maximum_request)return retained_default_command_name(kind);
    static const char *const names[]={
#define COH_INITIAL_CAPTURE_COMMAND(name,id) #name,
#include "coh_initial_command_kinds.inc"
#undef COH_INITIAL_CAPTURE_COMMAND
    };
    const char *longest=names[0];
    for(size_t i=1;i<sizeof(names)/sizeof(names[0]);i++)if(strlen(names[i])>strlen(longest))longest=names[i];
    return longest;
}
void coh_request_tx_diagnostics(const CohRequestTxWitness *w,CohRequestTxDiagnostics *out) {
    retained_default_tx_diagnostics(w,out);
    if(maximum_request) {
        out->first_send_attempts=out->retry_send_attempts=out->successful_retries=out->deferred_send_callbacks=out->failed_send_callbacks=maximum_request==2?UINT32_MAX:COH_REQUEST_TX_EVENT_MAX;
        out->queue_offset_ms=out->first_send_offset_ms=out->last_send_offset_ms=out->retirement_offset_ms=maximum_request==2?UINT64_MAX:COH_REQUEST_TX_OFFSET_MAX;
        out->refusal=COH_REQUEST_TX_CALLBACK;out->retirement=COH_REQUEST_TX_QUEUES_CLEARED;
    }
}
#include "../app/src/main/cpp/interop_network.c"
static size_t full_details_bytes(void) {
    char value[COH_INITIAL_PROBE_REPORT_MAX];size_t total=0;int n;
#define ADD(field,probe,formatter) do {n=formatter(&active->probe,value,sizeof(value));CHECK(n>0&&(size_t)n<sizeof(value));total+=strlen(field)+4+(size_t)n;}while(0)
    ADD("first_create",initial_create,coh_initial_create_probe_json);
    ADD("first_record_pose",initial_pose,coh_initial_pose_probe_json);
    ADD("first_record_sequence",initial_sequence,coh_initial_sequence_probe_json);
    ADD("first_record_triggered_moves",initial_triggered,coh_initial_triggered_probe_json);
    ADD("first_record_ai_animation",initial_aianim,coh_initial_aianim_probe_json);
    ADD("first_record_netfx",initial_netfx,coh_initial_netfx_probe_json);
    ADD("first_record_costume_prefix",initial_costume,coh_initial_costume_probe_json);
    ADD("first_reward_string",initial_reward,coh_initial_reward_probe_json);
#undef ADD
    if(active->initial_partcount.stage) {
        char progress[COH_INITIAL_REWARD_LIST_REPORT_MAX];
        n=coh_initial_partcount_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,&active->initial_appearance,&active->initial_sgcolors,&active->initial_scales,&active->initial_partcount,progress,sizeof(progress));
        if(n>0&&(size_t)n<sizeof(progress))total+=strlen("progress")+4+(size_t)n;
    }
    return total;
}
static void emit(const char *label) {
    const char *json=report();CHECK(strlen(json)<INTEROP_REPORT_BYTES);
    CHECK(!strstr(json,"REPORT_LIMIT")&&!strstr(json,"report_core_limit"));
    CHECK(strstr(json,"\"request_tx\":{")&&strstr(json,"\"receive_diagnostics\":{"));
    CHECK(strstr(json,"\"initial_observation_known\":true"));
    CHECK(strstr(json,"\"catalog_boundary\":null"));
    CHECK(strstr(json,"\"bodyparts_default\":[0,28]"));
    CHECK(strstr(json,"\"bodyparts_server_cache_status\":3"));
    CHECK(strstr(json,"\"costume_continuation\":["));
    CHECK(active->costume_continuation_attempted);
    CHECK(active->initial_costume_continuation.bodytype_validated&&active->initial_costume_continuation.count_validated);
    CHECK(active->initial_costume_continuation.part_count==(active->initial_partcount.explicit_count?active->initial_partcount.part_count:28u));
    CHECK(!active->initial_costume_continuation.costume_complete);
    printf("{\"label\":\"%s\",\"bytes\":%zu,\"unbounded_detail_bytes\":%zu,\"report\":%s}\n",label,strlen(json),full_details_bytes(),json);
}
static void captured(unsigned default_path) {
    fixture();partcount_fixture=1;
    if(default_path){partcount_scalar(COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_BEGIN,1,0);partcount_bits=COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_COUNT_BEGIN;}
    start();
    CHECK(JNI(controlState)(&env,NULL,current)==1);
    CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);
    CHECK(JNI(controlState)(&env,NULL,current)==9);
    CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);
    CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
    CHECK(JNI(controlState)(&env,NULL,current)==1);
    CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
    CHECK(JNI(controlState)(&env,NULL,current)==7);
    CHECK(active->initial_create.create_validated&&active->initial_costume.stage==COH_INITIAL_COSTUME_REWARD_STRING);
    CHECK(active->initial_reward.literal_validated&&active->initial_partcount.stage);
    CHECK(capture.d.raw_allents_observed&&capture.d.phase==COH_INITIAL_CAPTURED);
    CHECK(capture.d.local.opened_sockets==capture.d.local.closed_sockets);
}
static void receive_maximum(void) {
    CohReceiveProjection *p=&active->receive;
#define SET_MAX(name,value) p->name=COH_RECEIVE_COUNT_MAX;
    COH_RECEIVE_FIELDS(SET_MAX)
#undef SET_MAX
    p->sample_count=COH_RECEIVE_COUNT_MAX;p->rx_pending=p->max_rx_pending_sampled=COH_NET_RX_MAX;
    p->fragment_groups=p->max_fragment_groups_sampled=COH_NET_GROUP_MAX;
    p->decode_failure_kind=COH_NET_DECODE_STREAM;p->decode_compressed_bytes=COH_NET_MESSAGE_MAX;
    p->decode_declared_raw_bytes=UINT32_MAX;p->decode_output_budget=COH_NET_DECODED_MAX;
}
int main(void) {
    captured(0);capture.d.groups.present_files=508;capture.d.groups.roots=33;
    active->groups_bytes=42889;active->groups_bits=343112;
    emit("source-layout-initial-observed");strcpy(sample_report,report_text);
    CHECK(strstr(report_text,"\"catalog_boundary\":null"));
    unsigned allocation_before=alloc_calls;CHECK(!strcmp(report(),sample_report));CHECK(alloc_calls==allocation_before);
    receive_maximum();maximum_request=1;emit("source-layout-maximum-receive");
    /* Saturate legal fixed diagnostic scalar widths separately from authentic
     * packet parsing. This is serializer robustness, never a protocol claim. */
    maximum_request=2;
    active->groups_bytes=active->groups_bits=active->initial_bytes=active->initial_bits=active->initial_cursor=SIZE_MAX;
    capture.d.groups.present_files=capture.d.groups.roots=UINT32_MAX;
    capture.d.groups_observations=capture.d.allents_observations=capture.d.reqallents_sent=UINT32_MAX;
    capture.d.edit_messages_handled=capture.d.edit_message_last_bytes=UINT32_MAX;
    capture.d.first_failure=(CohInitialCaptureFailureSnapshot){1,(CohLocalPhase)UINT32_MAX,(CohDbSessionPhase)UINT32_MAX,(CohMapPhase)UINT32_MAX,COH_STATE,(CohInitialCaptureFailure)UINT32_MAX};
    capture.d.refused_command_valid=1;
    capture.d.edit_message_last_type=(CohInitialCaptureEditMessageType)UINT32_MAX;
    capture.d.local.db_phase=(CohDbSessionPhase)UINT32_MAX;capture.d.local.map_phase=(CohMapPhase)UINT32_MAX;
    capture.d.local.map_protocol.phase=(CohMapPhase)UINT32_MAX;capture.d.local.map_protocol.stage=(CohMapStage)UINT32_MAX;
    capture.d.local.map_protocol.scene_structures=UINT64_MAX;
    active->observer_status=COH_STATE;active->last_status=COH_STATE;
    capture.d.local.attempts=capture.d.local.character_lists=capture.d.local.character_choices=capture.d.local.map_handoffs=UINT64_MAX;
    capture.d.local.opened_sockets=capture.d.local.closed_sockets=UINT64_MAX;
    CohNetUdpDiagnostics *u=&capture.d.local.map_protocol.udp;
    u->state=(CohNetUdpState)UINT32_MAX;
    u->datagrams_sent=u->datagrams_received=u->send_would_block=u->interrupted=u->io_errors=UINT64_MAX;
    u->link.sent=u->link.received=u->link.retransmits=u->link.acknowledged=UINT64_MAX;u->link.tx_pending=UINT32_MAX;
    active->initial_create.header_end_bit=active->initial_create.create_end_bit=active->initial_create.failure_bit=SIZE_MAX;
    emit("maximum-width-scalars");
    active->initial_reward.failure_bit=SIZE_MAX;active->initial_reward.literal_bytes=UINT32_MAX;active->initial_partcount.status=COH_STATE;
    emit("reward-progress-local-refusal");
    CHECK(strstr(report_text,"\"report_invalid_mask\":256"));
    /* First-failure snapshot must survive report truncation and later cleanup. */
    capture.d.first_failure=(CohInitialCaptureFailureSnapshot){1,COH_LOCAL_MAP_CONNECTING,COH_DB_HANDOFF_READY,COH_MAP_SCENE_INCOMPLETE,COH_IO,COH_INITIAL_CAPTURE_FAILURE_OBSERVER};
    capture.d.failure=COH_INITIAL_CAPTURE_FAILURE_OWNER;capture.d.status=COH_STATE;
    capture.d.phase=COH_INITIAL_CAPTURE_FAILED;active->terminal=1;
    emit("first-failure-retained");
    /* Return to accepted limits before ordinary owned lifecycle cleanup. */
    memset(u,0,sizeof(*u));JNI(disconnect)(&env,NULL,current);
    CHECK(JNI(controlState)(&env,NULL,current)==7);emit("closed-initial-sticky");
    finish();CHECK(JNI(controlState)(&env,NULL,current)==0);
    captured(1);emit("client-default-admitted");JNI(disconnect)(&env,NULL,current);emit("client-default-closed");
    CHECK(strstr(report_text,"\"catalog_boundary\":null"));finish();
    fixture();start();CHECK(strstr(report(),"\"catalog_boundary\":null"));finish();
    fixture();start();active->busy=1;
    CHECK(JNI(controlState)(&env,NULL,current)==0);
    CHECK(strstr(report(),"OWNER_BUSY")&&strstr(report_text,"\"initial_observed\":null"));
    active->busy=0;finish();
    /* Every optional field and nested-progress failure is identified. */
    char output[INTEROP_REPORT_BYTES];size_t used=0;
    const char *const nulls[8]={"null","null","null","null","null","null","null","null"};
    CHECK(append(output,sizeof(output),&used,"{\"phase\":\"WAIT_ALLENTS\""));
    CHECK(report_details(output,&used,nulls,511));
    printf("{\"label\":\"invalid-optional-fields\",\"bytes\":%zu,\"report\":%s}\n",strlen(output),output);
    CHECK(freed==wiped&&!live);
    printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"max_report_bytes\":%zu,\"JNI_controller_provider_and_socket_doubles\":true,\"production_probe_parsers_and_serializers\":true,\"old_qualifier_main_executed\":false,\"Android_or_Thor_execution\":false,\"world_authority\":false}\n",checks,scenarios,max_report_bytes);
    return 0;
}
