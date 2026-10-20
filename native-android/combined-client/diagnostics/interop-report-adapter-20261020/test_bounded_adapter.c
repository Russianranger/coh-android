/* Additive compatibility role. The historical fixture and ALL of its original
 * assertions are included unchanged. Its report name is redirected ONLY here
 * to an explicitly TEST-ONLY full-detail view. The actual shipping report is
 * captured, bounds/omissions checked and emitted independently before that view.
 * No application source, JNI signature or resource limit is changed. */
#define Java_org_coh_nativecombined_InteropNative_report coh_test_only_full_detail_report
#define main retained_deep_adapter_assertions
#include "../interop-adapter-20261018/test_interop_adapter.c"
#undef main
#undef Java_org_coh_nativecombined_InteropNative_report
#include "../../app/src/main/cpp/interop_network.c"
static unsigned shipping_reports,shipping_omission_reports,test_only_views,busy_reports;
static char shipping_report[INTEROP_REPORT_BYTES];
static int optional_value(unsigned index,char *value,size_t capacity) {
    switch(index) {
    case 0:return coh_initial_create_probe_json(&active->initial_create,value,capacity);
    case 1:return coh_initial_pose_probe_json(&active->initial_pose,value,capacity);
    case 2:return coh_initial_sequence_probe_json(&active->initial_sequence,value,capacity);
    case 3:return coh_initial_triggered_probe_json(&active->initial_triggered,value,capacity);
    case 4:return coh_initial_aianim_probe_json(&active->initial_aianim,value,capacity);
    case 5:return coh_initial_netfx_probe_json(&active->initial_netfx,value,capacity);
    case 6:return coh_initial_costume_probe_json(&active->initial_costume,value,capacity);
    case 7: {
        int n=coh_initial_reward_probe_json(&active->initial_reward,value,capacity);
        if(active->initial_reward_list.stage&&n>1&&(size_t)n<capacity&&value[n-1]=='}') {
            char progress[COH_INITIAL_REWARD_LIST_REPORT_MAX];
            int p=active->initial_partcount.stage?
                coh_initial_partcount_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,&active->initial_appearance,&active->initial_sgcolors,&active->initial_scales,&active->initial_partcount,progress,sizeof(progress)):
                active->initial_scales.stage?
                coh_initial_scales_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,&active->initial_appearance,&active->initial_sgcolors,&active->initial_scales,progress,sizeof(progress)):
                active->initial_sgcolors.stage?
                coh_initial_sgcolors_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,&active->initial_appearance,&active->initial_sgcolors,progress,sizeof(progress)):
                active->initial_appearance.stage?
                coh_initial_appearance_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,&active->initial_appearance,progress,sizeof(progress)):
                active->initial_costume_body.stage?
                coh_initial_costume_body_progress_json(&active->initial_reward_list,&active->initial_costume_slots,&active->initial_costume_body,progress,sizeof(progress)):
                active->initial_costume_slots.stage?
                coh_initial_costume_slots_progress_json(&active->initial_reward_list,&active->initial_costume_slots,progress,sizeof(progress)):
                coh_initial_reward_list_probe_json(&active->initial_reward_list,progress,sizeof(progress));
            CHECK(p>0&&(size_t)p<sizeof(progress));size_t at=(size_t)n-1;
            int added=snprintf(value+at,capacity-at,",\"progress\":%s}",progress);
            CHECK(added>0&&(size_t)added<capacity-at);n=(int)at+added;
        }
        return n;
    }
    default:return -1;
    }
}
jstring coh_test_only_full_detail_report(JNIEnv *environment,jclass cls,jlong token) {
    jstring result=Java_org_coh_nativecombined_InteropNative_report(environment,cls,token);
    if(!result)return NULL; /* Preserve injected JNI allocation failure. */
    if(active&&owner(token)==active&&active->busy) {
        CHECK(strlen(report_text)<INTEROP_REPORT_BYTES&&strstr(report_text,"\"phase\":\"OWNER_BUSY\"")&&strstr(report_text,"\"owner_present\":true")&&strstr(report_text,"\"initial_observation_known\":false")&&strstr(report_text,"\"initial_observed\":null"));
        CHECK(Java_org_coh_nativecombined_InteropNative_controlState(environment,cls,token)==0);
        printf("{\"shipping_busy_report\":%s}\n",report_text);busy_reports++;return result;
    }
    CHECK(active&&owner(token)==active&&!active->busy);
    size_t bytes=strlen(report_text);CHECK(bytes<sizeof(shipping_report));
    memcpy(shipping_report,report_text,bytes+1);
    CHECK(!strstr(shipping_report,"REPORT_LIMIT")&&!strstr(shipping_report,"report_core_limit"));
    const char *mask=strstr(shipping_report,"\"report_omitted_mask\":");CHECK(mask);
    unsigned omitted=(unsigned)strtoul(mask+strlen("\"report_omitted_mask\":"),NULL,10);
    CHECK(omitted<256&&strstr(shipping_report,"\"report_invalid_mask\":0"));
    CHECK(strstr(shipping_report,"\"owner_present\":true")&&strstr(shipping_report,"\"initial_observation_known\":true"));
    CHECK(strstr(shipping_report,"\"request_tx\":")&&strstr(shipping_report,"\"receive_diagnostics\":{"));
    printf("{\"shipping_report_bytes\":%zu,\"shipping_report\":%s}\n",bytes,shipping_report);
    shipping_reports++;if(omitted)shipping_omission_reports++;
    /* A separate nested object retains the old deep assertions' visibility.
     * Its values come from the SAME owner populated by the production observer,
     * using the actual production optional formatters. It is never returned by
     * shipping JNI, exported by the application or called a bounded report. */
    CHECK(bytes>0&&report_text[bytes-1]=='}');size_t used=bytes-1;report_text[used]=0;
    CHECK(append(report_text,sizeof(report_text),&used,",\"test_only_full_detail_view\":true,\"test_only_omitted_probe_projection\":{"));
    unsigned count=0;
    for(unsigned i=0;i<8;i++)if(omitted&(1u<<i)) {
        char value[COH_INITIAL_PROBE_REPORT_MAX],null_field[96];
        int n=optional_value(i,value,sizeof(value));CHECK(n>0&&(size_t)n<sizeof(value)&&strcmp(value,"null"));
        int k=snprintf(null_field,sizeof(null_field),"\"%s\":null",report_detail_names[i]);CHECK(k>0&&(size_t)k<sizeof(null_field)&&strstr(shipping_report,null_field));
        if(count++)CHECK(append(report_text,sizeof(report_text),&used,","));
        CHECK(append(report_text,sizeof(report_text),&used,"\""));
        CHECK(append(report_text,sizeof(report_text),&used,report_detail_names[i]));
        CHECK(append(report_text,sizeof(report_text),&used,"\":"));
        CHECK(append(report_text,sizeof(report_text),&used,value));
    }
    CHECK(append(report_text,sizeof(report_text),&used,"}}"));test_only_views++;
    return result;
}
int main(void) {
    int status=retained_deep_adapter_assertions();
    CHECK(!status&&shipping_reports&&shipping_omission_reports&&test_only_views==shipping_reports&&busy_reports==1);
    printf("{\"bounded_shipping_reports\":%u,\"shipping_reports_with_omissions\":%u,\"explicit_test_only_full_detail_views\":%u,\"historical_assertions_executed_unchanged\":true,\"production_or_original_fixture_modified\":false}\n",shipping_reports,shipping_omission_reports,test_only_views);
    return status;
}
