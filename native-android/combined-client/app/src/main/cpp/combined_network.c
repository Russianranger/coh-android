/* Additive JNI owner. Original transport, crypto and scene kernels are reused.
 * All methods for one handle run on one Java executor. No secret/packet logging. */
#include <jni.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "coh_local.h"
#include "coh_session_crypto.h"

typedef struct { CohLocal *local; CohStatus last_status; } Combined;
static Combined *owner(jlong value) { return (Combined *)(uintptr_t)value; }
static const char *phase_name(CohLocalPhase phase) {
    static const char *const names[]={"IDLE","DB_CONNECTING","CHARACTERS_READY",
        "MAP_CONNECTING","SCENE_INCOMPLETE","CLOSED","SUSPENDED","CANCELLED",
        "FAILED","TIMED_OUT","UNSUPPORTED"};
    return (unsigned)phase<sizeof(names)/sizeof(names[0])?names[phase]:"INVALID";
}
static int account_copy(JNIEnv *env,jstring source,char out[15]) {
    if(!source)return 0;
    jsize count=(*env)->GetStringLength(env,source);
    if(count<1||count>14)return 0;
    const jchar *chars=(*env)->GetStringChars(env,source,NULL);
    if(!chars)return 0;
    int valid=1;
    for(jsize i=0;i<count;i++) {
        if(chars[i]<33||chars[i]>126){valid=0;break;}
        out[i]=(char)chars[i];
    }
    (*env)->ReleaseStringChars(env,source,chars);
    out[count]=0;return valid;
}
JNIEXPORT jlong JNICALL Java_org_coh_nativecombined_LocalNative_begin(JNIEnv *env,
    jclass cls,jint port,jstring account,jint version,jboolean required,
    jboolean compressed,jlong now) {
    (void)cls;
    if(port<1||port>65535||version<0||version>5||now<0)return 0;
    char name[15]={0};
    if(!account_copy(env,account,name)){coh_db_wipe(name,sizeof(name));return 0;}
    Combined *h=calloc(1,sizeof(*h));CohDbLogin policy;
    memset(&policy,0,sizeof(policy));
    if(!h){coh_db_wipe(name,sizeof(name));return 0;}
    CohLocalConfig config=coh_local_default_config();
    config.local_development_enabled=1;
    config.db.transport.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.db.transport.link.version=(unsigned)version;
    config.map.udp.link.version=(unsigned)version;
    config.db.transport.encryption_required=required?1:0;
    config.map.udp.encryption_required=required?1:0;
    config.db.outbound_compressed=compressed?1:0;
    config.db.transport.key_exchange=coh_session_key_exchange;
    config.map.udp.key_exchange=coh_session_key_exchange;
    config.db.transport.key_context=(void *)coh_auth_openssl_provider();
    config.map.udp.key_context=(void *)coh_auth_openssl_provider();
    h->last_status=coh_local_login_policy(&policy);
    if(h->last_status==COH_OK)h->local=coh_local_create(&config);
    struct timespec tick={0};(void)clock_gettime(CLOCK_MONOTONIC,&tick);
    uint32_t id=((uint32_t)tick.tv_nsec ^ (uint32_t)tick.tv_sec)&UINT32_C(0x7ffffffe);
    if(!id)id=2;
    if(h->local)h->last_status=coh_local_begin(h->local,&policy,name,id,id+1,(uint64_t)now);
    coh_db_wipe(name,sizeof(name));coh_db_wipe(&policy,sizeof(policy));
    if(!h->local||h->last_status!=COH_OK){coh_local_destroy(h->local);free(h);return 0;}
    return (jlong)(uintptr_t)h;
}
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_LocalNative_service(JNIEnv *env,
    jclass cls,jlong handle,jlong now) {
    (void)env;(void)cls;Combined *h=owner(handle);
    if(!h||now<0)return COH_INVALID;
    h->last_status=coh_local_service(h->local,(uint64_t)now,(CohCancel){0});
    return (jint)h->last_status;
}
JNIEXPORT jint JNICALL Java_org_coh_nativecombined_LocalNative_choose(JNIEnv *env,
    jclass cls,jlong handle,jint slot,jlong now) {
    (void)env;(void)cls;Combined *h=owner(handle);
    if(!h||slot<0||slot>=(jint)COH_DB_SLOTS_MAX||now<0)return COH_INVALID;
    h->last_status=coh_local_choose_character(h->local,(uint32_t)slot,(uint64_t)now);
    return (jint)h->last_status;
}
/* JSON output is bounded before every append. Character content is excluded
 * from report(); this separate byte[] is decoded with Java's UTF-8 decoder. */
static int append_text(char *out,size_t cap,size_t *used,const char *text) {
    size_t n=strlen(text);if(n>=cap-*used)return 0;
    memcpy(out+*used,text,n);*used+=n;out[*used]=0;return 1;
}
static int append_string(char *out,size_t cap,size_t *used,const char *text,size_t limit) {
    if(!append_text(out,cap,used,"\""))return 0;
    size_t i;
    for(i=0;i<limit&&text[i];i++) {
        unsigned char value=(unsigned char)text[i];char escaped[7]={0};
        if(value=='"'||value=='\\'){escaped[0]='\\';escaped[1]=(char)value;}
        else if(value<32){(void)snprintf(escaped,sizeof(escaped),"\\u%04x",value);}
        else {escaped[0]=(char)value;}
        if(!append_text(out,cap,used,escaped))return 0;
    }
    if(i==limit)return 0;
    return append_text(out,cap,used,"\"");
}
JNIEXPORT jbyteArray JNICALL Java_org_coh_nativecombined_LocalNative_characters(JNIEnv *env,
    jclass cls,jlong handle) {
    (void)cls;Combined *h=owner(handle);if(!h)return NULL;
    CohLocalCharacters *list=calloc(1,sizeof(*list));char *json=calloc(1,65536);
    if(!list||!json){free(list);free(json);return NULL;}
    size_t used=0;int ok=coh_local_characters(h->local,list)==COH_OK;
    if(ok)ok=list->count<=COH_DB_SLOTS_MAX&&append_text(json,65536,&used,"[");
    for(uint32_t i=0;ok&&i<list->count;i++) {
        const CohDbPlayer *p=&list->players[i];char numbers[192];
        int selected=!p->empty&&!p->visitor&&!p->invalid&&!p->slot_lock;
        (void)snprintf(numbers,sizeof(numbers),"%s{\"wire_slot\":%u,\"level\":%u,\"selectable\":%s,\"name\":",
            i?",":"",p->wire_slot,p->level,selected?"true":"false");
        ok=append_text(json,65536,&used,numbers)&&append_string(json,65536,&used,p->name,sizeof(p->name))
            &&append_text(json,65536,&used,",\"map\":")&&append_string(json,65536,&used,p->map_name,sizeof(p->map_name))
            &&append_text(json,65536,&used,"}");
    }
    if(ok)ok=append_text(json,65536,&used,"]");
    jbyteArray result=NULL;
    if(ok){result=(*env)->NewByteArray(env,(jsize)used);if(result)(*env)->SetByteArrayRegion(env,result,0,(jsize)used,(const jbyte *)json);}
    coh_db_wipe(list,sizeof(*list));coh_db_wipe(json,65536);free(list);free(json);return result;
}
JNIEXPORT jstring JNICALL Java_org_coh_nativecombined_LocalNative_report(JNIEnv *env,
    jclass cls,jlong handle) {
    (void)cls;Combined *h=owner(handle);if(!h)return (*env)->NewStringUTF(env,"{\"phase\":\"CLOSED\"}");
    CohLocalDiagnostics d;memset(&d,0,sizeof(d));coh_local_diagnostics(h->local,&d);char json[3072];
    (void)snprintf(json,sizeof(json),"{\"schema\":\"coh-native-local-numeric-v1\",\"phase\":\"%s\","
        "\"local_development_auth\":%u,\"server_identity_bound\":%u,\"generation\":%u,\"selection_generation\":%u,"
        "\"db_phase\":%u,\"map_phase\":%u,\"last_status\":%u,\"attempts\":%llu,\"character_lists\":%llu,"
        "\"character_choices\":%llu,\"map_handoffs\":%llu,\"policy_rejections\":%llu,\"failures\":%llu,"
        "\"suspends\":%llu,\"cancellations\":%llu,\"opened_sockets\":%llu,\"closed_sockets\":%llu,"
        "\"authserver_authenticated\":false,\"live_world_rendered\":false}",phase_name(d.phase),
        d.local_development_auth,d.server_identity_bound,d.generation,d.selection_generation,
        (unsigned)d.db_phase,(unsigned)d.map_phase,(unsigned)d.last_status,
        (unsigned long long)d.attempts,(unsigned long long)d.character_lists,(unsigned long long)d.character_choices,
        (unsigned long long)d.map_handoffs,(unsigned long long)d.policy_rejections,(unsigned long long)d.failures,
        (unsigned long long)d.suspends,(unsigned long long)d.cancellations,
        (unsigned long long)d.opened_sockets,(unsigned long long)d.closed_sockets);
    return (*env)->NewStringUTF(env,json);
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_LocalNative_suspend(JNIEnv *env,jclass cls,jlong handle) {
    (void)env;(void)cls;Combined *h=owner(handle);if(h)coh_local_suspend(h->local);
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_LocalNative_disconnect(JNIEnv *env,jclass cls,jlong handle) {
    (void)env;(void)cls;Combined *h=owner(handle);if(h)coh_local_close(h->local);
}
JNIEXPORT void JNICALL Java_org_coh_nativecombined_LocalNative_close(JNIEnv *env,jclass cls,jlong handle) {
    (void)env;(void)cls;Combined *h=owner(handle);if(!h)return;
    coh_local_close(h->local);coh_local_destroy(h->local);coh_db_wipe(h,sizeof(*h));free(h);
}
