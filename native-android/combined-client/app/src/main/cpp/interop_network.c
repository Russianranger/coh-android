/* Separate nonshipping JNI role. Exactly one executor owns all calls.
 * The synchronous lease is observed numerically and wiped, never copied into
 * a packet/file/world owner. No native pointer, account or character identity
 * appears in report(). Core symbols must be hidden in this diagnostic DSO. */
#include <jni.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/rand.h>
#include "coh_initial_capture.h"
#include "coh_session_crypto.h"
#include "../../../../diagnostics/gates25-27-thor-20261018/server-initial-investigation-worker-c/coh_receive_projection.h"
#ifdef COH_INTEROP_REQUEST_TX
#include "coh_request_tx.h"
#endif

typedef struct {
    CohInitialCapture *capture;
    uint64_t token,groups_generation;
    CohStatus last_status,observer_status;
    unsigned busy,suspended,disconnected,terminal,groups_callbacks,allents_callbacks;
    size_t groups_bytes,groups_bits,initial_bytes,initial_bits,initial_cursor;
    CohReceiveProjection receive;
#ifdef COH_INTEROP_REQUEST_TX
    CohRequestTxWitness *request;
    unsigned request_retired;
#endif
} Interop;
static Interop *active;
static uint64_t next_token=1;
static void sample_receive(Interop*h){
    CohInitialCaptureDiagnostics d;memset(&d,0,sizeof(d));coh_initial_capture_diagnostics(h->capture,&d);
    coh_receive_sample(&h->receive,&d.local.map_protocol.udp);coh_db_wipe(&d,sizeof(d));
}
static void retire_request(Interop *h) {
#ifdef COH_INTEROP_REQUEST_TX
    if(!h->request_retired){coh_request_tx_retire(h->request);h->request_retired=1;}
#else
    (void)h;
#endif
}
static void close_capture(Interop *h) {
    sample_receive(h);
#ifdef COH_INTEROP_REQUEST_TX
    if(!h->request_retired)coh_request_tx_close(h->request,h->capture);
    else coh_initial_capture_close(h->capture);
#else
    coh_initial_capture_close(h->capture);
#endif
    retire_request(h);
    sample_receive(h);
}
static Interop *owner(jlong value) {
    return value>0&&active&&active->token==(uint64_t)value?active:NULL;
}
static unsigned status_number(CohStatus status) {
    return (unsigned)status<=COH_STATE?(unsigned)status:COH_STATE;
}
static const char *failure_name(CohInitialCaptureFailure failure) {
    static const char *const names[]={"NONE","INPUT","OWNER","PROTOCOL","GROUPS","REQUEST",
        "COMMAND","HEADER","OBSERVER","RELEASE","TIMEOUT","CANCELLED","MEMORY"};
    return (unsigned)failure<sizeof(names)/sizeof(names[0])?names[failure]:"OWNER";
}
static const char *phase_name(const Interop *h,const CohInitialCaptureDiagnostics *d) {
    static const char *const local[]={"IDLE","DB_CONNECTING","CHARACTERS_READY","MAP_CONNECTING",
        "SCENE_INCOMPLETE","CLOSED","SUSPENDED","CANCELLED","FAILED","TIMED_OUT","UNSUPPORTED"};
    if(h->disconnected)return "CLOSED";
    if(h->suspended)return "SUSPENDED";
    if(d->phase==COH_INITIAL_CAPTURED)return "INITIAL_OBSERVED";
    if(d->phase==COH_INITIAL_CAPTURE_WAIT_ALLENTS)return "WAIT_ALLENTS";
    if(d->phase==COH_INITIAL_CAPTURE_WAIT_GROUPS)return "WAIT_GROUPS";
    if(d->phase==COH_INITIAL_CAPTURE_FAILED)return
        (d->first_failure.valid?d->first_failure.failure:d->failure)==COH_INITIAL_CAPTURE_FAILURE_TIMEOUT?"TIMED_OUT":"FAILED";
    if(d->phase==COH_INITIAL_CAPTURE_CANCELLED)return "CANCELLED";
    if(d->phase==COH_INITIAL_CAPTURE_CLOSED)return "CLOSED";
    return (unsigned)d->local.phase<sizeof(local)/sizeof(local[0])?local[d->local.phase]:"FAILED";
}
static int account_copy(JNIEnv *env,jstring input,char out[15]) {
    if(!input)return 0;
    jsize length=(*env)->GetStringLength(env,input);
    if((*env)->ExceptionCheck(env)||length<1||length>14)return 0;
    const jchar *chars=(*env)->GetStringChars(env,input,NULL);
    if(!chars)return 0;
    int valid=1;
    for(jsize i=0;i<length;i++) {
        if(chars[i]<33||chars[i]>126){valid=0;break;}
        out[i]=(char)chars[i];
    }
    (*env)->ReleaseStringChars(env,input,chars);out[length]=0;
    return valid&&!(*env)->ExceptionCheck(env);
}
JNIEXPORT jlong JNICALL Java_org_coh_nativecombined_InteropNative_begin(JNIEnv *env,jclass cls,
    jint port,jstring account,jint version,jboolean required,jboolean compressed,jlong now) {
    (void)cls;
    if(active||!next_token||next_token>INT64_MAX||port<1||port>65535||version<0||version>5||
       (required!=JNI_FALSE&&required!=JNI_TRUE)||(compressed!=JNI_FALSE&&compressed!=JNI_TRUE)||now<0)return 0;
    char name[15]={0};uint32_t ids[2]={0};CohDbLogin policy={0};
    CohLocalConfig config;memset(&config,0,sizeof(config));Interop *h=NULL;
    if(!account_copy(env,account,name))goto failed;
    h=calloc(1,sizeof(*h));if(!h)goto failed;
    config=coh_local_default_config();config.local_development_enabled=1;
    config.db.transport.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.db.transport.link.version=config.map.udp.link.version=(unsigned)version;
    config.db.transport.encryption_required=config.map.udp.encryption_required=required?1:0;
    config.db.outbound_compressed=compressed?1:0;
    config.db.transport.key_exchange=config.map.udp.key_exchange=coh_session_key_exchange;
    config.db.transport.key_context=config.map.udp.key_context=(void*)coh_auth_openssl_provider();
    h->last_status=coh_local_login_policy(&policy);
    if(h->last_status!=COH_OK||!config.db.transport.key_context||RAND_bytes((unsigned char*)ids,(int)sizeof(ids))!=1)goto failed;
    ids[0]=(ids[0]&UINT32_C(0x7ffffffc))+1;ids[1]=ids[0]+1;
    h->capture=coh_initial_capture_create(&config);if(!h->capture)goto failed;
    h->last_status=coh_initial_capture_begin(h->capture,&policy,name,ids[0],ids[1],(uint64_t)now);
    if(h->last_status!=COH_OK)goto failed;
#ifdef COH_INTEROP_REQUEST_TX
    h->request=coh_request_tx_create(h->capture,(uint64_t)now);
#endif
    h->token=next_token++;active=h;
    coh_db_wipe(name,sizeof(name));coh_db_wipe(ids,sizeof(ids));
    coh_db_wipe(&policy,sizeof(policy));coh_db_wipe(&config,sizeof(config));return (jlong)h->token;
failed:
    if(h){coh_initial_capture_close(h->capture);coh_initial_capture_destroy(h->capture);coh_db_wipe(h,sizeof(*h));free(h);}
    coh_db_wipe(name,sizeof(name));coh_db_wipe(ids,sizeof(ids));
    coh_db_wipe(&policy,sizeof(policy));coh_db_wipe(&config,sizeof(config));return 0;
}
static CohStatus observe(void *context,const CohInitialCapture *capture,const CohInitialCaptureEvent *event) {
    Interop *h=context;CohInitialCaptureLease lease;memset(&lease,0,sizeof(lease));
    CohStatus status=coh_initial_capture_lease(capture,event,&lease);
    if(status!=COH_OK)goto done;
    if(!h->busy||h->capture!=capture||!event||lease.kind!=event->kind||!lease.local_development_authorized||
       !lease.selected_dbid_owner_bound||!lease.selected_dbid||!lease.message_generation||
       lease.source_generation_admitted||lease.complete_initial_character||lease.actor_publication||
       lease.ack_permitted||lease.world_authority||!lease.reader.bytes.size||
       lease.reader.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||lease.reader.bits>lease.reader.bytes.size*8||
       lease.reader.cursor>lease.reader.bits){status=COH_STATE;goto done;}
    if(event->kind==COH_INITIAL_CAPTURE_GROUPS) {
        if(h->groups_callbacks||h->allents_callbacks){status=COH_STATE;goto done;}
        h->groups_callbacks=1;h->groups_generation=lease.message_generation;
        h->groups_bytes=lease.reader.bytes.size;h->groups_bits=lease.reader.bits;
    } else if(event->kind==COH_INITIAL_CAPTURE_ALLENTS) {
        if(h->groups_callbacks!=1||h->allents_callbacks||lease.groups_message_generation!=h->groups_generation||
           lease.message_generation<=h->groups_generation||lease.update.command!=COH_REP_ALLENTS){status=COH_STATE;goto done;}
        h->allents_callbacks=1;h->initial_bytes=lease.reader.bytes.size;
        h->initial_bits=lease.reader.bits;h->initial_cursor=lease.reader.cursor;
    } else status=COH_STATE;
done:
    h->observer_status=status;coh_db_wipe(&lease,sizeof(lease));return status;
}
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_InteropNative_service(JNIEnv *env,jclass cls,jlong token,jlong now) {
    (void)env;(void)cls;Interop *h=owner(token);
    if(!h||now<0)return COH_INVALID;
    if(h->busy||h->suspended||h->disconnected||h->terminal)return COH_STATE;
    h->busy=1;
#ifdef COH_INTEROP_REQUEST_TX
    h->last_status=coh_request_tx_service(h->request,h->capture,(uint64_t)now,(CohCancel){0},observe,h,sizeof(*h));
#else
    h->last_status=coh_initial_capture_service(h->capture,(uint64_t)now,(CohCancel){0},observe,h,sizeof(*h));
#endif
    CohInitialCaptureDiagnostics d;memset(&d,0,sizeof(d));coh_initial_capture_diagnostics(h->capture,&d);
    coh_receive_sample(&h->receive,&d.local.map_protocol.udp);
    h->terminal=d.phase>=COH_INITIAL_CAPTURED;coh_db_wipe(&d,sizeof(d));
    if(h->terminal)retire_request(h);
    h->busy=0;return (jint)h->last_status;
}
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_InteropNative_choose(JNIEnv *env,jclass cls,jlong token,jint slot,jlong now) {
    (void)env;(void)cls;Interop *h=owner(token);
    if(!h||slot<0||slot>=(jint)COH_DB_SLOTS_MAX||now<0)return COH_INVALID;
    if(h->busy||h->suspended||h->disconnected||h->terminal)return COH_STATE;
    h->busy=1;h->last_status=coh_initial_capture_choose_character(h->capture,(uint32_t)slot,(uint64_t)now);
    h->busy=0;return (jint)h->last_status;
}
static int append(char *out,size_t capacity,size_t *used,const char *text) {
    size_t bytes=strlen(text);if(*used>=capacity||bytes>=capacity-*used)return 0;
    memcpy(out+*used,text,bytes);*used+=bytes;out[*used]=0;return 1;
}
static int append_string(char *out,size_t capacity,size_t *used,const char *text,size_t maximum) {
    if(!append(out,capacity,used,"\""))return 0;
    size_t i;
    for(i=0;i<maximum&&text[i];i++) {
        unsigned char byte=(unsigned char)text[i];char escaped[7]={0};
        if(byte=='"'||byte=='\\'){escaped[0]='\\';escaped[1]=(char)byte;}
        else if(byte<32)(void)snprintf(escaped,sizeof(escaped),"\\u%04x",byte);
        else escaped[0]=(char)byte;
        if(!append(out,capacity,used,escaped))return 0;
    }
    return i<maximum&&append(out,capacity,used,"\"");
}
JNIEXPORT jbyteArray JNICALL Java_org_coh_nativecombined_InteropNative_characters(JNIEnv *env,jclass cls,jlong token) {
    (void)cls;Interop *h=owner(token);if(!h||h->busy||h->suspended||h->disconnected||h->terminal)return NULL;
    CohLocalCharacters *list=calloc(1,sizeof(*list));char *json=calloc(1,65536);jbyteArray result=NULL;
    if(!list||!json)goto done;
    h->busy=1;CohStatus status=coh_initial_capture_characters(h->capture,list);h->busy=0;
    size_t used=0;int ok=status==COH_OK&&list->count<=COH_DB_SLOTS_MAX&&append(json,65536,&used,"[");
    for(uint32_t i=0;ok&&i<list->count;i++) {
        const CohDbPlayer *p=&list->players[i];char numbers[192];
        int selectable=!p->empty&&!p->visitor&&!p->invalid&&!p->slot_lock;
        int n=snprintf(numbers,sizeof(numbers),"%s{\"wire_slot\":%u,\"level\":%u,\"selectable\":%s,\"name\":",
            i?",":"",p->wire_slot,p->level,selectable?"true":"false");
        ok=n>0&&(size_t)n<sizeof(numbers)&&append(json,65536,&used,numbers)&&
            append_string(json,65536,&used,p->name,sizeof(p->name))&&append(json,65536,&used,",\"map\":")&&
            append_string(json,65536,&used,p->map_name,sizeof(p->map_name))&&append(json,65536,&used,"}");
    }
    if(ok)ok=append(json,65536,&used,"]");
    if(ok) {
        result=(*env)->NewByteArray(env,(jsize)used);
        if(result&&!(*env)->ExceptionCheck(env))(*env)->SetByteArrayRegion(env,result,0,(jsize)used,(const jbyte*)json);
        if((*env)->ExceptionCheck(env)&&result){(*env)->DeleteLocalRef(env,result);result=NULL;}
    }
done:
    if(list){coh_db_wipe(list,sizeof(*list));free(list);}if(json){coh_db_wipe(json,65536);free(json);}return result;
}
JNIEXPORT jstring JNICALL Java_org_coh_nativecombined_InteropNative_report(JNIEnv *env,jclass cls,jlong token) {
    (void)cls;Interop *h=owner(token);
    if(!h||h->busy)return (*env)->NewStringUTF(env,"{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"CLOSED\",\"diagnostic_only\":true,\"authserver_authenticated\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,\"live_world_rendered\":false}");
    CohInitialCaptureDiagnostics d;memset(&d,0,sizeof(d));coh_initial_capture_diagnostics(h->capture,&d);
    const CohLocalDiagnostics *local=&d.local;const CohMapDiagnostics *map=&local->map_protocol;
    const CohNetUdpDiagnostics *udp=&map->udp;
    const CohInitialCaptureFailureSnapshot *first=&d.first_failure;
    CohInitialCaptureFailure failure=first->valid?first->failure:d.failure;
    unsigned terminal=h->suspended||h->disconnected||d.phase>=COH_INITIAL_CAPTURED;
    unsigned cleanup=terminal&&local->opened_sockets==local->closed_sockets;
    char json[7168],request[1536]="null",receive[COH_RECEIVE_REPORT_MAX]="null";unsigned request_available=0;
    int receive_written=coh_receive_json(&h->receive,terminal,cleanup,receive,sizeof(receive));
    if(receive_written<=0||(size_t)receive_written>=sizeof(receive))strcpy(receive,"null");
#ifdef COH_INTEROP_REQUEST_TX
    if(h->request) {
        CohRequestTxDiagnostics tx;memset(&tx,0,sizeof(tx));coh_request_tx_diagnostics(h->request,&tx);
        int n=snprintf(request,sizeof(request),"{\"diagnostic_only\":true,\"valid\":%s,\"witness_retired\":%s,"
            "\"queue_attempted\":%s,\"queue_succeeded\":%s,\"queue_status\":%u,\"first_send_accepted\":%s,"
            "\"peer_transport_ack_observed\":%s,\"refusal\":%u,\"retirement\":%u,"
            "\"first_send_attempts\":%u,\"retry_send_attempts\":%u,\"successful_retries\":%u,\"deferred_send_callbacks\":%u,\"failed_send_callbacks\":%u,"
            "\"queue_offset_ms\":%llu,\"first_send_offset_ms\":%llu,\"last_send_offset_ms\":%llu,\"retirement_offset_ms\":%llu,"
            "\"command_specific_emission_proved\":false,\"server_receipt_proved\":false,\"ack_permitted\":false,\"world_authority\":false}",
            tx.valid?"true":"false",tx.witness_retired?"true":"false",tx.queue_attempted?"true":"false",tx.queue_succeeded?"true":"false",
            status_number(tx.queue_status),tx.first_send_accepted?"true":"false",tx.peer_transport_ack_observed?"true":"false",(unsigned)tx.refusal,(unsigned)tx.retirement,
            tx.first_send_attempts,tx.retry_send_attempts,tx.successful_retries,tx.deferred_send_callbacks,tx.failed_send_callbacks,
            (unsigned long long)tx.queue_offset_ms,(unsigned long long)tx.first_send_offset_ms,(unsigned long long)tx.last_send_offset_ms,(unsigned long long)tx.retirement_offset_ms);
        coh_db_wipe(&tx,sizeof(tx));
        if(n>0&&(size_t)n<sizeof(request))request_available=1;else strcpy(request,"null");
    }
#endif
#define U64(value) (unsigned long long)(value)
    int written=snprintf(json,sizeof(json),"{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"diagnostic_only\":true,\"phase\":\"%s\","
        "\"capture_phase\":%u,\"status\":%u,\"last_status\":%u,\"failure_code\":\"%s\",\"failure\":%u,"
        "\"local_development_auth\":%s,\"server_identity_bound\":%s,\"selected_owner_bound\":%s,"
        "\"groups_observed\":%s,\"raw_allents_observed\":%s,\"groups_observations\":%u,\"allents_observations\":%u,\"reqallents_sent\":%u,"
        "\"groups_lease_callbacks\":%u,\"initial_lease_callbacks\":%u,\"observer_status\":%u,"
        "\"groups_bytes\":%llu,\"groups_bits\":%llu,\"initial_bytes\":%llu,\"initial_bits\":%llu,\"initial_post_command_cursor\":%llu,"
        "\"db_phase\":%u,\"map_phase\":%u,\"attempts\":%llu,\"character_lists\":%llu,\"character_choices\":%llu,\"map_handoffs\":%llu,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"cleanup_verified\":%s,\"cleanup_scope\":\"owned_transport_counters\","
        "\"suspend_requested\":%s,\"disconnect_requested\":%s,\"packet_copy_retained\":false,"
        "\"first_failure\":{\"valid\":%s,\"local_phase\":%u,\"db_phase\":%u,\"map_phase\":%u,\"status\":%u,\"failure\":%u},"
        "\"edit_messages_handled\":%u,\"edit_message_last_type\":%u,\"edit_message_last_bytes\":%u,"
        "\"refused_command_valid\":%s,\"refused_command_kind\":\"%s\","
        "\"map_protocol\":{\"phase\":%u,\"stage\":%u,\"last_status\":%u,\"scene_structures\":%llu,"
        "\"udp\":{\"state\":%u,\"datagrams_sent\":%llu,\"datagrams_received\":%llu,\"send_would_block\":%llu,\"interrupted\":%llu,\"io_errors\":%llu,"
        "\"link\":{\"sent\":%llu,\"received\":%llu,\"retransmits\":%llu,\"acknowledged\":%llu,\"tx_pending\":%u}}},"
        "\"authserver_authenticated\":false,\"normal_version_admitted\":false,\"checksum_reference_admitted\":false,"
        "\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,"
        "\"sends_ready\":false,\"sends_received_character\":false,\"sends_full_update_ack\":false,\"world_authority\":false,\"live_world_rendered\":false,"
        "\"request_tx_available\":%s,\"request_tx\":%s,\"receive_diagnostics\":%s}",
        phase_name(h,&d),(unsigned)d.phase,status_number(first->valid?first->status:d.status),status_number(h->last_status),failure_name(failure),(unsigned)failure,
        local->local_development_auth?"true":"false",local->server_identity_bound?"true":"false",local->selected_dbid_owner_bound?"true":"false",
        d.groups_observed&&h->groups_callbacks==1?"true":"false",d.raw_allents_observed&&h->allents_callbacks==1?"true":"false",
        d.groups_observations,d.allents_observations,d.reqallents_sent,h->groups_callbacks,h->allents_callbacks,status_number(h->observer_status),
        U64(h->groups_bytes),U64(h->groups_bits),U64(h->initial_bytes),U64(h->initial_bits),U64(h->initial_cursor),
        (unsigned)local->db_phase,(unsigned)local->map_phase,U64(local->attempts),U64(local->character_lists),U64(local->character_choices),U64(local->map_handoffs),
        U64(local->opened_sockets),U64(local->closed_sockets),cleanup?"true":"false",h->suspended?"true":"false",h->disconnected?"true":"false",
        first->valid?"true":"false",(unsigned)first->local_phase,(unsigned)first->db_phase,(unsigned)first->map_phase,status_number(first->status),(unsigned)first->failure,
        d.edit_messages_handled,(unsigned)d.edit_message_last_type,d.edit_message_last_bytes,d.refused_command_valid?"true":"false",
        coh_initial_capture_command_name(d.refused_command_kind),(unsigned)map->phase,(unsigned)map->stage,status_number(map->last_status),U64(map->scene_structures),
        (unsigned)udp->state,U64(udp->datagrams_sent),U64(udp->datagrams_received),U64(udp->send_would_block),U64(udp->interrupted),U64(udp->io_errors),
        U64(udp->link.sent),U64(udp->link.received),U64(udp->link.retransmits),U64(udp->link.acknowledged),udp->link.tx_pending,
        request_available?"true":"false",request,receive);
#undef U64
    coh_db_wipe(&d,sizeof(d));
    if(written<0||(size_t)written>=sizeof(json))return (*env)->NewStringUTF(env,"{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"REPORT_LIMIT\",\"world_authority\":false}");
    return (*env)->NewStringUTF(env,json);
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_InteropNative_suspend(JNIEnv *env,jclass cls,jlong token) {
    (void)env;(void)cls;Interop *h=owner(token);if(!h||h->busy||h->disconnected||h->suspended)return;
    h->busy=1;h->suspended=1;
#ifdef COH_INTEROP_REQUEST_TX
    if(!h->request_retired)coh_request_tx_cancel(h->request,h->capture);
    else coh_initial_capture_cancel(h->capture);
#else
    coh_initial_capture_cancel(h->capture);
#endif
    retire_request(h);h->terminal=1;h->busy=0;
    sample_receive(h);
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_InteropNative_disconnect(JNIEnv *env,jclass cls,jlong token) {
    (void)env;(void)cls;Interop *h=owner(token);if(!h||h->busy||h->disconnected)return;
    h->busy=1;h->disconnected=1;close_capture(h);h->terminal=1;h->busy=0;
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_InteropNative_close(JNIEnv *env,jclass cls,jlong token) {
    (void)env;(void)cls;Interop *h=owner(token);if(!h||h->busy)return;
    h->busy=1;close_capture(h);
#ifdef COH_INTEROP_REQUEST_TX
    coh_request_tx_destroy(h->request);
#endif
    coh_initial_capture_destroy(h->capture);
    active=NULL;coh_db_wipe(h,sizeof(*h));free(h);
}
