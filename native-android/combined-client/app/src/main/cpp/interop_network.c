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
#include "coh_initial_create_probe.h"
#include "coh_initial_pose_probe.h"
#include "coh_initial_sequence_probe.h"
#include "coh_initial_triggered_probe.h"
#include "coh_initial_aianim_probe.h"
#include "coh_initial_netfx_probe.h"
#include "coh_initial_costume_probe.h"
#include "coh_initial_reward_probe.h"
#include "coh_initial_reward_list_probe.h"
#include "coh_initial_costume_slots_probe.h"
#include "coh_initial_costume_body_probe.h"
#include "coh_initial_appearance_probe.h"
#include "coh_initial_sgcolors_probe.h"
#include "coh_initial_scales_probe.h"
#include "coh_initial_partcount_probe.h"
#include "coh_local_bodypart_default.h"
#include "coh_original_costume_receive.h"
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
    CohInitialCreateProbe initial_create;
    CohInitialPoseProbe initial_pose;
    CohInitialPoseSample initial_pose_sample;
    CohInitialSequenceProbe initial_sequence;
    CohInitialTriggeredProbe initial_triggered;
    CohInitialAiAnimProbe initial_aianim;
    CohInitialNetFxProbe initial_netfx;
    CohInitialCostumeProbe initial_costume;
    CohInitialRewardProbe initial_reward;
    CohInitialRewardListProbe initial_reward_list;
    CohInitialCostumeSlotsProbe initial_costume_slots;
    CohInitialCostumeBodyProbe initial_costume_body;
    CohInitialAppearanceProbe initial_appearance;
    CohInitialSgcolorsProbe initial_sgcolors;
    CohInitialScalesProbe initial_scales;
    CohInitialPartcountProbe initial_partcount;
    uint32_t pinned_bodyparts;CohStatus bodyparts_cache_status;
    CohOriginalCostumeWorkspace costume_workspace;
    CohOriginalCostumeReport initial_costume_continuation;
    unsigned costume_continuation_attempted;
    CohReceiveProjection receive;
#ifdef COH_INTEROP_REQUEST_TX
    CohRequestTxWitness *request;
    unsigned request_retired;
#endif
} Interop;
static Interop *active;
static uint64_t next_token=1;
static CohStatus configured_bodyparts_status=COH_NOT_FOUND;
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
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_InteropNative_configureBodyPartsCache(JNIEnv *env,jclass cls,jstring input) {
    (void)cls;if(active)return COH_STATE;
    configured_bodyparts_status=COH_INVALID;uint32_t consistency_count=0;
    if(!input)return COH_INVALID;
    jsize length=(*env)->GetStringLength(env,input);
    if((*env)->ExceptionCheck(env)||length<1||length>=1024)return COH_INVALID;
    const jchar *chars=(*env)->GetStringChars(env,input,NULL);
    if(!chars)return COH_INVALID;
    char path[1024];int valid=1;
    for(jsize i=0;i<length;i++){if(chars[i]<32||chars[i]>126){valid=0;break;}path[i]=(char)chars[i];}
    path[length]=0;(*env)->ReleaseStringChars(env,input,chars);
    if(valid&&!(*env)->ExceptionCheck(env))configured_bodyparts_status=coh_local_bodypart_default_file(path,&consistency_count);
    coh_db_wipe(path,sizeof(path));return configured_bodyparts_status;
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
    /* The pinned CLIENT ParseBodyPart catalog defines GetBodyPartCount().
     * An optional server-cache comparison never controls client admission. */
    h->pinned_bodyparts=COH_LOCAL_BODYPART_COUNT;h->bodyparts_cache_status=configured_bodyparts_status;
    configured_bodyparts_status=COH_NOT_FOUND;
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
        /* The exact owned loan supplies the post-command reader, schema and
         * selected DBID. A bounded syntax refusal is retained separately from
         * successful packet observation; it grants no character/ACK permit. */
        (void)coh_initial_create_probe(&lease.reader,&lease.schema,lease.selected_dbid,&h->initial_create);
        if(h->initial_create.create_validated&&h->initial_create.stage==COH_INITIAL_PROBE_RECORD_BODY) {
            CohRepReader body=lease.reader;body.cursor=h->initial_create.create_end_bit;
            if(lease.message_id)(void)coh_initial_pose_probe_with_sample(&body,lease.message_id,&h->initial_pose,&h->initial_pose_sample);
            else h->initial_pose=(CohInitialPoseProbe){.status=COH_STATE,.stage=COH_INITIAL_POSE_INPUT,
                .begin_bit=body.cursor,.failure_bit=body.cursor};
            coh_db_wipe(&body,sizeof(body));
            if(h->initial_pose.pose_validated&&h->initial_pose.stage==COH_INITIAL_POSE_SEQUENCE) {
                CohRepReader sequence=lease.reader;sequence.cursor=h->initial_pose.pose_end_bit;
                (void)coh_initial_sequence_probe(&sequence,&h->initial_sequence);
                coh_db_wipe(&sequence,sizeof(sequence));
                if(h->initial_sequence.sequence_validated&&h->initial_sequence.stage==COH_INITIAL_SEQUENCE_TRIGGERS) {
                    CohRepReader triggered=lease.reader;triggered.cursor=h->initial_sequence.sequence_end_bit;
                    (void)coh_initial_triggered_probe(&triggered,&h->initial_triggered);
                    coh_db_wipe(&triggered,sizeof(triggered));
                    if(h->initial_triggered.triggered_moves_validated&&h->initial_triggered.stage==COH_INITIAL_TRIGGERED_AI_ANIMATION) {
                        CohRepReader ai=lease.reader;ai.cursor=h->initial_triggered.triggered_end_bit;
                        (void)coh_initial_aianim_probe(&ai,&h->initial_aianim);
                        coh_db_wipe(&ai,sizeof(ai));
                        if(h->initial_aianim.ai_animation_validated&&h->initial_aianim.stage==COH_INITIAL_AIANIM_NETFX) {
                            CohRepReader fx=lease.reader;fx.cursor=h->initial_aianim.ai_end_bit;
                            (void)coh_initial_netfx_probe(&fx,&h->initial_netfx);
                            coh_db_wipe(&fx,sizeof(fx));
                            if(h->initial_netfx.netfx_validated&&h->initial_netfx.stage==COH_INITIAL_NETFX_COSTUME) {
                                CohRepReader costume=lease.reader;costume.cursor=h->initial_netfx.netfx_end_bit;
                                (void)coh_initial_costume_probe(&costume,h->initial_create.is_self,&h->initial_costume);
                                coh_db_wipe(&costume,sizeof(costume));
                                if(h->initial_costume.stage==COH_INITIAL_COSTUME_REWARD_STRING) {
                                    CohRepReader reward=lease.reader;reward.cursor=h->initial_costume.prefix_end_bit;
                                    (void)coh_initial_reward_probe(&reward,&h->initial_reward);
                                    coh_db_wipe(&reward,sizeof(reward));
                                    if(h->initial_reward.literal_validated&&h->initial_reward.stage==COH_INITIAL_REWARD_CONTINUATION&&
                                       h->initial_costume.type==1&&h->initial_costume.self_seen&&h->initial_costume.self_wire_consistent&&h->initial_create.is_self) {
                                        CohRepReader rewards=lease.reader;
                                        rewards.cursor=h->initial_costume.selector_end_bit+(lease.reader.compressed?8u:1u);
                                        (void)coh_initial_reward_list_probe(&rewards,&h->initial_reward_list);
                                        coh_db_wipe(&rewards,sizeof(rewards));
                                        if(h->initial_reward_list.list_validated&&h->initial_reward_list.stage==COH_INITIAL_REWARD_LIST_SLOTS) {
                                            CohRepReader slots=lease.reader;slots.cursor=h->initial_reward_list.end_bit;
                                            (void)coh_initial_costume_slots_probe(&slots,&h->initial_costume_slots);
                                            coh_db_wipe(&slots,sizeof(slots));
                                            if(h->initial_costume_slots.framing_validated&&h->initial_costume_slots.stage==COH_INITIAL_COSTUME_SLOTS_BODY) {
                                                CohRepReader body_prefix=lease.reader;body_prefix.cursor=h->initial_costume_slots.end_bit;
                                                (void)coh_initial_costume_body_probe(&body_prefix,&h->initial_costume_body);
                                                coh_db_wipe(&body_prefix,sizeof(body_prefix));
                                                if(h->initial_costume_body.prefix_validated&&h->initial_costume_body.stage==COH_INITIAL_COSTUME_BODY_BODYTYPE) {
                                                    CohRepReader appearance=lease.reader;appearance.cursor=h->initial_costume_body.end_bit;
                                                    (void)coh_initial_appearance_probe(&appearance,&h->initial_appearance);
                                                    coh_db_wipe(&appearance,sizeof(appearance));
                                                    if(h->initial_appearance.scalars_validated&&h->initial_appearance.stage==COH_INITIAL_APPEARANCE_COLORS) {
                                                        CohRepReader sgcolors=lease.reader;sgcolors.cursor=h->initial_appearance.end_bit;
                                                        (void)coh_initial_sgcolors_probe(&sgcolors,&h->initial_sgcolors);
                                                        coh_db_wipe(&sgcolors,sizeof(sgcolors));
                                                        if(h->initial_sgcolors.array_validated&&h->initial_sgcolors.stage==COH_INITIAL_SGCOLORS_SCALES) {
                                                            CohRepReader scales=lease.reader;scales.cursor=h->initial_sgcolors.end_bit;
                                                            (void)coh_initial_scales_probe(&scales,&h->initial_scales);
                                                            coh_db_wipe(&scales,sizeof(scales));
                                                            if(h->initial_scales.scales_validated&&h->initial_scales.stage==COH_INITIAL_SCALES_PART_COUNT) {
                                                                CohRepReader partcount=lease.reader;partcount.cursor=h->initial_scales.end_bit;
                                                                (void)coh_initial_partcount_probe(&partcount,&h->initial_partcount);
                                                                coh_db_wipe(&partcount,sizeof(partcount));
                                                                if(h->pinned_bodyparts&&h->initial_partcount.framing_validated) {
                                                                    CohRepReader original=lease.reader;original.cursor=h->initial_costume_slots.end_bit;
                                                                    h->costume_continuation_attempted=1;
                                                                    /* Actual fixed owner storage + borrowed decoded message +
                                                                     * native call/lease reserve under the existing8MiB initial
                                                                     * domain. This is not a claim about guest/process RSS. */
                                                                    size_t named=sizeof(*h)+sizeof(lease)+COH_ORIGINAL_COSTUME_STACK_RESERVE;
                                                                    if(named<=8u*1024u*1024u&&lease.reader.bytes.size<=8u*1024u*1024u-named)
                                                                        (void)coh_original_costume_receive(&original,h->pinned_bodyparts,&h->costume_workspace,&h->initial_costume_continuation);
                                                                    else h->initial_costume_continuation=(CohOriginalCostumeReport){.status=COH_LIMIT,.begin_bit=original.cursor,.failure_bit=original.cursor};
                                                                    coh_db_wipe(&original,sizeof(original));
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
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
/* The control plane never depends on JSON fitting. Bits are shared with Java:
 * PRESENT=1, TERMINAL=2, INITIAL_OBSERVED=4, CHARACTERS_READY=8. No token or
 * pointer is exported. The executor remains the single owner of JNI calls. */
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_InteropNative_controlState(JNIEnv *env,jclass cls,jlong token) {
    (void)env;(void)cls;Interop *h=owner(token);if(!h)return 0;
    unsigned state=1,terminal=h->terminal||h->suspended||h->disconnected;
    if(h->allents_callbacks==1)state|=4;
    if(h->busy)return 0; /* unavailable sample, never a negative observation */
    CohInitialCaptureDiagnostics d;memset(&d,0,sizeof(d));coh_initial_capture_diagnostics(h->capture,&d);
    terminal|=d.phase>=COH_INITIAL_CAPTURED;
    if(terminal)state|=2;
    if(!terminal&&d.local.phase==COH_LOCAL_CHARACTERS_READY)state|=8;
    coh_db_wipe(&d,sizeof(d));return (jint)state;
}
/* Stable omission bit order; a null from an unobserved probe is not omission.
 * Core observations, request and receive counters precede these optional
 * projections. Reserve includes every null field and the worst metadata tail.
 * Serialization allocates no heap and retains the established 7,168 B cap. */
#define INTEROP_REPORT_BYTES 7168u
#define INTEROP_REPORT_TAIL_RESERVE 512u
static const char *const report_detail_names[]={"first_create","first_record_pose","first_record_sequence",
    "first_record_triggered_moves","first_record_ai_animation","first_record_netfx",
    "first_record_costume_prefix","first_reward_string","first_reward_progress"};
static int report_details(char *json,size_t *used,const char *const values[8],unsigned invalid) {
    size_t minimum=INTEROP_REPORT_TAIL_RESERVE;
    for(unsigned i=0;i<8;i++)minimum+=strlen(report_detail_names[i])+8; /* ,\"key\":null */
    unsigned omitted=invalid;
    if(*used>=INTEROP_REPORT_BYTES||minimum>=INTEROP_REPORT_BYTES-*used)return 0;
    for(unsigned i=0;i<8;i++) {
        const char *value=values[i];size_t key=strlen(report_detail_names[i])+4;
        minimum-=key+4;
        size_t bytes=strlen(value);
        if((invalid&(1u<<i))||key+bytes>=INTEROP_REPORT_BYTES-*used-minimum) {
            if(strcmp(value,"null")||(invalid&(1u<<i)))omitted|=1u<<i;
            value="null";
        }
        if(!append(json,INTEROP_REPORT_BYTES,used,",\"")||
           !append(json,INTEROP_REPORT_BYTES,used,report_detail_names[i])||
           !append(json,INTEROP_REPORT_BYTES,used,"\":")||
           !append(json,INTEROP_REPORT_BYTES,used,value))return 0;
    }
    char suffix[192];int n=snprintf(suffix,sizeof(suffix),
        ",\"report_limit_bytes\":7168,\"report_truncated\":%s,\"report_omitted_mask\":%u,\"report_invalid_mask\":%u,\"report_omitted_fields\":[",
        omitted?"true":"false",omitted,invalid);
    if(n<=0||(size_t)n>=sizeof(suffix)||!append(json,INTEROP_REPORT_BYTES,used,suffix))return 0;
    unsigned count=0;
    for(unsigned i=0;i<9;i++)if(omitted&(1u<<i)) {
        if((count++&&!append(json,INTEROP_REPORT_BYTES,used,","))||
           !append(json,INTEROP_REPORT_BYTES,used,"\"")||
           !append(json,INTEROP_REPORT_BYTES,used,report_detail_names[i])||
           !append(json,INTEROP_REPORT_BYTES,used,"\""))return 0;
    }
    return append(json,INTEROP_REPORT_BYTES,used,"]}");
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
/* An actual selected-self wire pose already parsed from this one ALLENTS loan.
 * This diagnostic marker does not wait for unrelated later costume fields. */
JNIEXPORT jbyteArray JNICALL Java_org_coh_nativecombined_InteropNative_observedSelfPose(JNIEnv *env,jclass cls,jlong token) {
    (void)cls;Interop *h=owner(token);
    if(!h||h->busy||!h->initial_create.create_validated||!h->initial_create.is_self||
       !h->initial_create.self_dbid_matches_handoff||!h->initial_pose_sample.valid)return NULL;
    uint32_t values[4]={h->initial_create.entity_index,0,0,0};jbyte bytes[16];
    memcpy(&values[1],&h->initial_pose_sample.position.x,4);memcpy(&values[2],&h->initial_pose_sample.position.y,4);memcpy(&values[3],&h->initial_pose_sample.position.z,4);
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)bytes[i*4+j]=(jbyte)(values[i]>>(j*8));
    jbyteArray result=(*env)->NewByteArray(env,16);
    if(result)(*env)->SetByteArrayRegion(env,result,0,16,bytes);
    coh_db_wipe(values,sizeof(values));coh_db_wipe(bytes,sizeof(bytes));return result;
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
    if(!h)return (*env)->NewStringUTF(env,"{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"CLOSED\",\"owner_present\":false,\"owner_terminal\":true,\"initial_observation_known\":false,\"initial_observed\":null,\"diagnostic_only\":true,\"authserver_authenticated\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,\"live_world_rendered\":false}");
    if(h->busy)return (*env)->NewStringUTF(env,"{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"OWNER_BUSY\",\"owner_present\":true,\"initial_observation_known\":false,\"initial_observed\":null,\"report_truncated\":true,\"packet_copy_retained\":false,\"world_authority\":false}");
    CohInitialCaptureDiagnostics d;memset(&d,0,sizeof(d));coh_initial_capture_diagnostics(h->capture,&d);
    const CohLocalDiagnostics *local=&d.local;const CohMapDiagnostics *map=&local->map_protocol;
    const CohNetUdpDiagnostics *udp=&map->udp;
    const CohInitialCaptureFailureSnapshot *first=&d.first_failure;
    CohInitialCaptureFailure failure=first->valid?first->failure:d.failure;
    unsigned terminal=h->suspended||h->disconnected||d.phase>=COH_INITIAL_CAPTURED;
    unsigned cleanup=terminal&&local->opened_sockets==local->closed_sockets;
    char json[INTEROP_REPORT_BYTES],request[1536]="null",receive[COH_RECEIVE_REPORT_MAX]="null";
    char first_create[COH_INITIAL_PROBE_REPORT_MAX]="null";unsigned request_available=0,invalid=0;
    char first_pose[COH_INITIAL_POSE_REPORT_MAX]="null";
    char first_sequence[COH_INITIAL_SEQUENCE_REPORT_MAX]="null";
    char first_triggered[COH_INITIAL_TRIGGERED_REPORT_MAX]="null";
    char first_aianim[COH_INITIAL_AIANIM_REPORT_MAX]="null",first_netfx[COH_INITIAL_NETFX_REPORT_MAX]="null";
    char first_costume[COH_INITIAL_COSTUME_REPORT_MAX]="null";
    char first_reward[COH_INITIAL_REWARD_REPORT_MAX]="null";
    /* Essential, pointer-free source progress survives optional detail omission.
     * Only the original composed validator can publish catalog stages41/43. */
    char catalog_boundary[COH_INITIAL_REWARD_LIST_REPORT_MAX]="null";
    char continuation[192]="null";
    if(h->costume_continuation_attempted) {
        const CohOriginalCostumeReport *c=&h->initial_costume_continuation;
        int n=snprintf(continuation,sizeof(continuation),"[%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%llu]",
            status_number(c->status),c->field,c->part,c->part_count,c->parts_read,c->strings_read,c->colors_read,
            c->dictionary_required,c->count_validated,c->costume_complete,(unsigned long long)c->end_bit,(unsigned long long)c->failure_bit);
        if(n<0||(size_t)n>=sizeof(continuation))strcpy(continuation,"null");
    }
    int create_written=coh_initial_create_probe_json(&h->initial_create,first_create,sizeof(first_create));
    if(create_written<=0||(size_t)create_written>=sizeof(first_create)){strcpy(first_create,"null");invalid|=1u<<0;}
    int pose_written=coh_initial_pose_probe_json(&h->initial_pose,first_pose,sizeof(first_pose));
    if(pose_written<=0||(size_t)pose_written>=sizeof(first_pose)){strcpy(first_pose,"null");invalid|=1u<<1;}
    int sequence_written=coh_initial_sequence_probe_json(&h->initial_sequence,first_sequence,sizeof(first_sequence));
    if(sequence_written<=0||(size_t)sequence_written>=sizeof(first_sequence)){strcpy(first_sequence,"null");invalid|=1u<<2;}
    int triggered_written=coh_initial_triggered_probe_json(&h->initial_triggered,first_triggered,sizeof(first_triggered));
    if(triggered_written<=0||(size_t)triggered_written>=sizeof(first_triggered)){strcpy(first_triggered,"null");invalid|=1u<<3;}
    int ai_written=coh_initial_aianim_probe_json(&h->initial_aianim,first_aianim,sizeof(first_aianim));
    if(ai_written<=0||(size_t)ai_written>=sizeof(first_aianim)){strcpy(first_aianim,"null");invalid|=1u<<4;}
    int fx_written=coh_initial_netfx_probe_json(&h->initial_netfx,first_netfx,sizeof(first_netfx));
    if(fx_written<=0||(size_t)fx_written>=sizeof(first_netfx)){strcpy(first_netfx,"null");invalid|=1u<<5;}
    int costume_written=coh_initial_costume_probe_json(&h->initial_costume,first_costume,sizeof(first_costume));
    if(costume_written<=0||(size_t)costume_written>=sizeof(first_costume)){strcpy(first_costume,"null");invalid|=1u<<6;}
    int reward_written=coh_initial_reward_probe_json(&h->initial_reward,first_reward,sizeof(first_reward));
    if(reward_written<=0||(size_t)reward_written>=sizeof(first_reward)){strcpy(first_reward,"null");invalid|=1u<<7;}
    if(h->initial_reward_list.stage&&reward_written>1&&(size_t)reward_written<sizeof(first_reward)&&first_reward[reward_written-1]=='}') {
        char progress[COH_INITIAL_REWARD_LIST_REPORT_MAX];
        int progress_written=h->initial_partcount.stage?
            coh_initial_partcount_progress_json(&h->initial_reward_list,&h->initial_costume_slots,&h->initial_costume_body,&h->initial_appearance,&h->initial_sgcolors,&h->initial_scales,&h->initial_partcount,progress,sizeof(progress)):
            h->initial_scales.stage?
            coh_initial_scales_progress_json(&h->initial_reward_list,&h->initial_costume_slots,&h->initial_costume_body,&h->initial_appearance,&h->initial_sgcolors,&h->initial_scales,progress,sizeof(progress)):
            h->initial_sgcolors.stage?
            coh_initial_sgcolors_progress_json(&h->initial_reward_list,&h->initial_costume_slots,&h->initial_costume_body,&h->initial_appearance,&h->initial_sgcolors,progress,sizeof(progress)):
            h->initial_appearance.stage?
            coh_initial_appearance_progress_json(&h->initial_reward_list,&h->initial_costume_slots,&h->initial_costume_body,&h->initial_appearance,progress,sizeof(progress)):
            h->initial_costume_body.stage?
            coh_initial_costume_body_progress_json(&h->initial_reward_list,&h->initial_costume_slots,&h->initial_costume_body,progress,sizeof(progress)):
            h->initial_costume_slots.stage?
            coh_initial_costume_slots_progress_json(&h->initial_reward_list,&h->initial_costume_slots,progress,sizeof(progress)):
            coh_initial_reward_list_probe_json(&h->initial_reward_list,progress,sizeof(progress));
        if(progress_written>0&&(size_t)progress_written<sizeof(progress)) {
            if(!h->initial_costume_continuation.count_validated&&(h->initial_partcount.stage==COH_INITIAL_PARTCOUNT_DEFAULT_CATALOG||
               h->initial_partcount.stage==COH_INITIAL_PARTCOUNT_CATALOG))
                memcpy(catalog_boundary,progress,(size_t)progress_written+1);
            size_t at=(size_t)reward_written-1,room=sizeof(first_reward)-at;
            int appended=snprintf(first_reward+at,room,",\"progress\":%s}",progress);
            if(appended<0||(size_t)appended>=room){first_reward[at]='}';first_reward[at+1]=0;invalid|=1u<<8;}
        } else invalid|=1u<<8;
    }
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
        "\"owner_present\":true,\"owner_terminal\":%s,\"initial_observation_known\":true,\"initial_observed\":%s,"
        "\"local_development_auth\":%s,\"server_identity_bound\":%s,\"selected_owner_bound\":%s,"
        "\"groups_observed\":%s,\"raw_allents_observed\":%s,\"groups_observations\":%u,\"allents_observations\":%u,\"reqallents_sent\":%u,"
        "\"groups_lease_callbacks\":%u,\"initial_lease_callbacks\":%u,\"observer_status\":%u,"
        "\"groups_present_files\":%u,\"groups_roots\":%u,\"groups_bytes\":%llu,\"groups_bits\":%llu,\"initial_bytes\":%llu,\"initial_bits\":%llu,\"initial_post_command_cursor\":%llu,"
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
        "\"bodyparts_default\":[%u,%u],\"bodyparts_server_cache_status\":%u,\"costume_continuation\":%s,\"catalog_boundary\":%s,\"request_tx_available\":%s,\"request_tx\":%s,\"receive_diagnostics\":%s",
        phase_name(h,&d),(unsigned)d.phase,status_number(first->valid?first->status:d.status),status_number(h->last_status),failure_name(failure),(unsigned)failure,
        terminal?"true":"false",d.raw_allents_observed&&h->allents_callbacks==1?"true":"false",
        local->local_development_auth?"true":"false",local->server_identity_bound?"true":"false",local->selected_dbid_owner_bound?"true":"false",
        d.groups_observed&&h->groups_callbacks==1?"true":"false",d.raw_allents_observed&&h->allents_callbacks==1?"true":"false",
        d.groups_observations,d.allents_observations,d.reqallents_sent,h->groups_callbacks,h->allents_callbacks,status_number(h->observer_status),
        d.groups.present_files,d.groups.roots,U64(h->groups_bytes),U64(h->groups_bits),U64(h->initial_bytes),U64(h->initial_bits),U64(h->initial_cursor),
        (unsigned)local->db_phase,(unsigned)local->map_phase,U64(local->attempts),U64(local->character_lists),U64(local->character_choices),U64(local->map_handoffs),
        U64(local->opened_sockets),U64(local->closed_sockets),cleanup?"true":"false",h->suspended?"true":"false",h->disconnected?"true":"false",
        first->valid?"true":"false",(unsigned)first->local_phase,(unsigned)first->db_phase,(unsigned)first->map_phase,status_number(first->status),(unsigned)first->failure,
        d.edit_messages_handled,(unsigned)d.edit_message_last_type,d.edit_message_last_bytes,d.refused_command_valid?"true":"false",
        coh_initial_capture_command_name(d.refused_command_kind),(unsigned)map->phase,(unsigned)map->stage,status_number(map->last_status),U64(map->scene_structures),
        (unsigned)udp->state,U64(udp->datagrams_sent),U64(udp->datagrams_received),U64(udp->send_would_block),U64(udp->interrupted),U64(udp->io_errors),
        U64(udp->link.sent),U64(udp->link.received),U64(udp->link.retransmits),U64(udp->link.acknowledged),udp->link.tx_pending,
        status_number(COH_OK),h->pinned_bodyparts,status_number(h->bodyparts_cache_status),continuation,catalog_boundary,request_available?"true":"false",request,receive);
    const char *const details[8]={first_create,first_pose,first_sequence,first_triggered,first_aianim,first_netfx,first_costume,first_reward};
    size_t used=written>0?(size_t)written:sizeof(json);
    int complete=written>0&&(size_t)written<sizeof(json)&&report_details(json,&used,details,invalid);
    /* This emergency core is unreachable for supported numeric widths (covered
     * by the maximum-width regression); retain actual state if a future core
     * extension violates its reservation instead of replacing it with a phase. */
    if(!complete)snprintf(json,sizeof(json),
        "{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"diagnostic_only\":true,\"phase\":\"%s\","
        "\"capture_phase\":%u,\"owner_present\":true,\"owner_terminal\":%s,\"initial_observation_known\":true,\"initial_observed\":%s,"
        "\"groups_observed\":%s,\"groups_present_files\":%u,\"groups_roots\":%u,\"groups_bytes\":%llu,\"groups_bits\":%llu,"
        "\"reqallents_sent\":%u,\"raw_allents_observed\":%s,\"initial_bytes\":%llu,\"initial_bits\":%llu,\"initial_post_command_cursor\":%llu,"
        "\"status\":%u,\"failure\":%u,\"failure_code\":\"%s\",\"first_failure\":{\"valid\":%s,\"local_phase\":%u,\"db_phase\":%u,\"map_phase\":%u,\"status\":%u,\"failure\":%u},"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"cleanup_verified\":%s,\"packet_copy_retained\":false,"
        "\"report_limit_bytes\":7168,\"report_truncated\":true,\"report_core_limit\":true,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,\"live_world_rendered\":false}",
        phase_name(h,&d),(unsigned)d.phase,terminal?"true":"false",d.raw_allents_observed&&h->allents_callbacks==1?"true":"false",
        d.groups_observed?"true":"false",d.groups.present_files,d.groups.roots,U64(h->groups_bytes),U64(h->groups_bits),d.reqallents_sent,
        d.raw_allents_observed?"true":"false",U64(h->initial_bytes),U64(h->initial_bits),U64(h->initial_cursor),
        status_number(first->valid?first->status:d.status),(unsigned)failure,failure_name(failure),first->valid?"true":"false",
        (unsigned)first->local_phase,(unsigned)first->db_phase,(unsigned)first->map_phase,status_number(first->status),(unsigned)first->failure,
        U64(local->opened_sockets),U64(local->closed_sockets),cleanup?"true":"false");
#undef U64
    coh_db_wipe(&d,sizeof(d));return (*env)->NewStringUTF(env,json);
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
