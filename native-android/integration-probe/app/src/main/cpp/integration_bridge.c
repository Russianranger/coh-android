#include <jni.h>
#include <android/native_window_jni.h>
#include <pthread.h>
#include <stdatomic.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "coh_input.h"
#include "coh_audio.h"
#include "coh_decode.h"
#include "coh_transport.h"
#include "coh_interactive_world.h"

static CohInputState input;
static CohInputFrame latest;
static uint64_t input_revision;
static pthread_mutex_t input_mutex=PTHREAD_MUTEX_INITIALIZER;
static atomic_uint_fast64_t world_epoch=0;
static atomic_int world_foreground=0, world_active=0;
typedef struct { uint8_t *data; size_t length; } OwnedBytes;
typedef struct { uint64_t epoch; } WorldSession;
static jstring string_result(JNIEnv *env,const char *s) { return (*env)->NewStringUTF(env,s); }
static int copy_array(JNIEnv *env,jbyteArray source,size_t maximum,OwnedBytes *out) {
    if(!source)return 0;
    jsize n=(*env)->GetArrayLength(env,source);
    if(n<=0||(size_t)n>maximum)return 0;
    uint8_t *data=malloc((size_t)n);
    if(!data)return 0;
    (*env)->GetByteArrayRegion(env,source,0,n,(jbyte *)data);
    if((*env)->ExceptionCheck(env)){(*env)->ExceptionClear(env);free(data);return 0;}
    out->data=data;out->length=(size_t)n;return 1;
}
static void decode_json(char *out,size_t capacity,const CohDecodeProof *p) {
    snprintf(out,capacity,
        "{\"passed\":%s,\"result\":%d,\"codec_result\":%d,\"opened\":%s,\"cleared\":%s,\"eos\":%s,\"streams\":%d,"
        "\"sample_rate\":%u,\"channels\":%u,\"frames\":%u,\"pcm_bytes\":%u,\"pages\":%u,"
        "\"read_callbacks\":%u,\"seek_callbacks\":%u,\"tell_callbacks\":%u,\"close_callbacks\":%u,\"callback_bytes\":%" PRIu64 ","
        "\"ov_read_calls\":%u,\"maximum_sample_error\":%u,\"different_samples\":%u,\"compared_samples\":%u,"
        "\"absolute_sample_error\":%" PRIu64 ",\"squared_sample_error\":%" PRIu64 ",\"sample_rms_error\":%.12g,\"maximum_allowed_sample_error\":%u,"
        "\"reference_compared\":%s,\"reference_passed\":%s,\"callback_limit\":%s,"
        "\"checks\":%u,\"failed\":%u,\"rejected_inputs\":%u,\"repeated_decodes\":%u}",
        p->result==0&&p->reference_passed&&!p->failed?"true":"false",p->result,p->codec_result,
        p->opened?"true":"false",p->cleared?"true":"false",p->eos?"true":"false",p->streams,
        p->sample_rate,p->channels,p->frames,p->pcm_bytes,p->pages,
        p->read_callbacks,p->seek_callbacks,p->tell_callbacks,p->close_callbacks,p->callback_bytes,
        p->ov_read_calls,p->maximum_sample_error,p->different_samples,p->compared_samples,
        p->absolute_sample_error,p->squared_sample_error,p->sample_rms_error,COH_DECODE_MAX_SAMPLE_ERROR,
        p->reference_compared?"true":"false",p->reference_passed?"true":"false",p->callback_limit?"true":"false",
        p->checks,p->failed,p->rejected_inputs,p->repeated_decodes);
}
static void transport_json(char *out,size_t capacity,int result,const CohTransportProof *p) {
    snprintf(out,capacity,
        "{\"passed\":%s,\"result\":%d,\"cancelled\":%s,\"expected_cancel\":%s,\"session_failure\":%s,\"opened\":%s,\"closed\":%s,"
        "\"checks\":%u,\"datagrams_sent\":%u,\"datagrams_received\":%u,\"clear_frames\":%u,\"encrypted_frames\":%u,"
        "\"expected_rejects\":%u,\"endpoint_checks\":%u,\"byte_parity_checks\":%u,\"decoded_payloads\":%u,"
        "\"truncated_datagrams\":%u,\"zero_datagrams\":%u,\"timeouts\":%u,\"blocked_polls\":%u,"
        "\"interrupted_blocked_poll\":%u,\"sockets_opened\":%u,\"sockets_closed\":%u,\"backend_errors\":%u,\"elapsed_ms\":%u,"
        "\"scope\":\"127.0.0.1 UDP only; no game server or authentication\"}",
        p->passed?"true":"false",result,p->cancelled?"true":"false",p->expected_cancel?"true":"false",p->session_failure?"true":"false",p->sockets_opened?"true":"false",
        p->sockets_opened&&p->sockets_opened==p->sockets_closed?"true":"false",
        p->checks,p->datagrams_sent,p->datagrams_received,p->clear_frames,p->encrypted_frames,
        p->expected_rejects,p->endpoint_checks,p->byte_parity_checks,p->decoded_payloads,
        p->truncated_datagrams,p->zero_datagrams,p->timeouts,p->blocked_polls,
        p->interrupted_blocked_poll,p->sockets_opened,p->sockets_closed,p->backend_errors,p->elapsed_ms);
}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm,void *reserved) {
    (void)vm;(void)reserved;coh_input_init(&input);memset(&latest,0,sizeof latest);return JNI_VERSION_1_6;
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeFocus(JNIEnv *env,jclass cls,jboolean value) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);coh_input_focus(&input,value?1:0);
    if(!value){coh_input_frame(&input,0,&latest);}input_revision++;pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeResetCamera(JNIEnv *env,jclass cls) {
    (void)env;(void)cls;atomic_fetch_add(&world_epoch,1);pthread_mutex_lock(&input_mutex);coh_input_init(&input);coh_input_focus(&input,1);
    coh_input_frame(&input,0,&latest);input_revision++;pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeKey(JNIEnv *env,jclass cls,jint key,jboolean down) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);coh_input_key(&input,(uint32_t)key,down?1:0);input_revision++;pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeAxes(JNIEnv *env,jclass cls,jfloat x,jfloat y,jfloat z,jfloat rz) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);coh_input_axes(&input,x,y,z,rz);input_revision++;pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeTouch(JNIEnv *env,jclass cls,jint action,jint id,jfloat x,jfloat y) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);coh_input_touch(&input,action,id,x,y);input_revision++;pthread_mutex_unlock(&input_mutex);
}
static int world_cancelled(void *opaque) {
    WorldSession *s=opaque;return !atomic_load(&world_foreground)||atomic_load(&world_epoch)!=s->epoch;
}
static int world_sample(void *opaque,float seconds,CohInputFrame *frame,uint64_t *revision) {
    if(world_cancelled(opaque))return 0;
    pthread_mutex_lock(&input_mutex);
    if(world_cancelled(opaque)){pthread_mutex_unlock(&input_mutex);return 0;}
    int result=coh_input_frame(&input,seconds,frame);
    latest=*frame;*revision=input_revision;pthread_mutex_unlock(&input_mutex);return result==1?1:-1;
}
JNIEXPORT jstring JNICALL Java_org_coh_integrationprobe_MainActivity_nativeFrame(JNIEnv *env,jclass cls,jfloat seconds) {
    (void)cls;CohInputFrame f;pthread_mutex_lock(&input_mutex);int result=1;
    if(!atomic_load(&world_active))result=coh_input_frame(&input,seconds,&latest);
    f=latest;pthread_mutex_unlock(&input_mutex);
    char json[1600];snprintf(json,sizeof json,
        "{\"result\":%d,\"held\":%u,\"pressed\":%u,\"released\":%u,\"frames\":%u,\"clear_count\":%u,"
        "\"rejected\":%u,\"clipped\":%u,\"delta_x\":%d,\"delta_y\":%d,\"pyr\":[%.9g,%.9g,%.9g],"
        "\"target_pyr\":[%.9g,%.9g,%.9g],\"axes\":[%.9g,%.9g,%.9g,%.9g]}",
        result,f.held,f.pressed,f.released,f.frames,f.clear_count,f.rejected,f.clipped,f.delta_x,f.delta_y,
        f.pyr[0],f.pyr[1],f.pyr[2],f.target_pyr[0],f.target_pyr[1],f.target_pyr[2],f.axes[0],f.axes[1],f.axes[2],f.axes[3]);
    return string_result(env,json);
}
JNIEXPORT jstring JNICALL Java_org_coh_integrationprobe_MainActivity_nativeChecks(JNIEnv *env,jclass cls,jbyteArray ogg,jbyteArray reference) {
    (void)cls;OwnedBytes a={0},b={0};CohDecodeProof d={0};CohTransportProof t={0};CohInputProof i={0};
    int copied=copy_array(env,ogg,COH_DECODE_MAX_COMPRESSED,&a)&&copy_array(env,reference,1024u*1024u,&b);
    int dr=copied?coh_decode_selftest(a.data,a.length,b.data,b.length,&d):COH_DECODE_INVALID;
    if(!copied)d.result=dr;
    int tr=coh_transport_selftest(&t),ir=coh_input_selftest(&i);
    free(a.data);free(b.data);
    char dj[2500],tj[2200],json[6000];decode_json(dj,sizeof dj,&d);transport_json(tj,sizeof tj,tr,&t);
    snprintf(json,sizeof json,"{\"passed\":%s,\"decode\":%s,\"transport\":%s,"
        "\"input_source\":{\"passed\":%s,\"result\":%d,\"checks\":%u,\"failed\":%u,\"source_cases\":%u,\"adapter_cases\":%u,\"max_source_error\":%.9g}}",
        dr==0&&d.reference_passed&&!d.failed&&tr==0&&t.passed&&ir==1&&!i.failed?"true":"false",dj,tj,
        ir==1&&!i.failed?"true":"false",ir,i.checks,i.failed,i.source_cases,i.adapter_cases,(double)i.max_source_error);
    return string_result(env,json);
}
JNIEXPORT jstring JNICALL Java_org_coh_integrationprobe_MainActivity_nativePlay(JNIEnv *env,jclass cls,jbyteArray ogg,jbyteArray reference) {
    (void)cls;OwnedBytes a={0},b={0};CohDecodedAudio decoded={0};CohDecodeProof d={0};CohAudioPlayback playback={0};
    int copied=copy_array(env,ogg,COH_DECODE_MAX_COMPRESSED,&a)&&copy_array(env,reference,1024u*1024u,&b);
    int dr=copied?coh_decode_ogg(a.data,a.length,&decoded,&d):COH_DECODE_INVALID;
    if(dr==0)dr=coh_decode_compare_reference(&decoded,b.data,b.length,&d);
    if(!copied)d.result=dr;
    int rc=dr==0?coh_audio_play(decoded.data,decoded.length,&playback):COH_AUDIO_INVALID;
    CohAudioFixture fixture={0};int fixture_ok=decoded.data&&coh_audio_parse(decoded.data,decoded.length,&fixture)==0;
    int64_t expected=(int64_t)fixture.frames*3+(int64_t)(fixture.sample_rate*15/100)*2;
    int passed=dr==0&&fixture_ok&&rc==0&&playback.opened&&playback.started&&playback.stopped&&playback.closed&&!playback.cancelled&&!playback.backend_errors&&
        playback.completed_clips==3&&playback.actual_rate==(int)fixture.sample_rate&&playback.actual_channels==(int)fixture.channels&&
        playback.actual_format==1&&playback.submitted_frames==expected&&playback.read_frames>=expected;
    char dj[2500],json[6000];decode_json(dj,sizeof dj,&d);
    snprintf(json,sizeof json,
        "{\"passed\":%s,\"result\":%d,\"decode\":%s,\"decoded_audio_played\":%s,\"playback_origin\":\"on-device Ogg decode; no reference PCM fallback\","
        "\"requested_rate\":%d,\"actual_rate\":%d,\"actual_channels\":%d,\"actual_format\":%d,"
        "\"opened\":%s,\"started\":%s,\"stopped\":%s,\"closed\":%s,\"cancelled\":%s,\"backend_errors\":%d,"
        "\"requested_clips\":%d,\"completed_clips\":%d,\"partial_writes\":%d,\"write_calls\":%d,\"xrun_count\":%d,"
        "\"timestamp_available\":%s,\"submitted_frames\":%lld,\"read_frames\":%lld,\"timestamp_frame\":%lld,\"timestamp_ns\":%lld,"
        "\"source_volume_db\":%d,\"source_effective_gain\":%.9g,\"quiet_volume_db\":%d,\"quiet_effective_gain\":%.9g,\"duration_ns\":%lld}",
        passed?"true":"false",rc,dj,dr==0&&playback.started?"true":"false",
        playback.requested_rate,playback.actual_rate,playback.actual_channels,playback.actual_format,
        playback.opened?"true":"false",playback.started?"true":"false",playback.stopped?"true":"false",playback.closed?"true":"false",
        playback.cancelled?"true":"false",playback.backend_errors,playback.requested_clips,playback.completed_clips,playback.partial_writes,playback.write_calls,playback.xrun_count,
        playback.timestamp_available?"true":"false",(long long)playback.submitted_frames,(long long)playback.read_frames,(long long)playback.timestamp_frame,(long long)playback.timestamp_ns,
        playback.source_volume_db,(double)playback.source_effective_gain,playback.quiet_volume_db,(double)playback.quiet_effective_gain,(long long)playback.duration_ns);
    coh_decode_release(&decoded);free(a.data);free(b.data);return string_result(env,json);
}
JNIEXPORT jstring JNICALL Java_org_coh_integrationprobe_MainActivity_nativeTransportWait(JNIEnv *env,jclass cls,jint milliseconds) {
    (void)cls;CohTransportProof p={0};int rc=coh_transport_wait(milliseconds>0?(unsigned)milliseconds:0,&p);
    char json[2200];transport_json(json,sizeof json,rc,&p);return string_result(env,json);
}
JNIEXPORT jlong JNICALL Java_org_coh_integrationprobe_MainActivity_nativeWorldTicket(JNIEnv *env,jclass cls){(void)env;(void)cls;return (jlong)atomic_load(&world_epoch);}
JNIEXPORT jstring JNICALL Java_org_coh_integrationprobe_MainActivity_nativeWorld(JNIEnv *env,jclass cls,jobject surface,jbyteArray world,jbyteArray reference,jbyteArray materials,jlong expected_ticket) {
    (void)cls;OwnedBytes a={0},b={0},c={0};CohInteractiveWorldReport report={0};WorldSession session={(uint64_t)expected_ticket};
    int copied=copy_array(env,world,16u*1024u*1024u,&a)&&copy_array(env,reference,16u*1024u*1024u,&b)&&copy_array(env,materials,1024u*1024u,&c);
    ANativeWindow *window=surface?ANativeWindow_fromSurface(env,surface):NULL;
    if(copied&&window&&!world_cancelled(&session)){
        pthread_mutex_lock(&input_mutex);atomic_store(&world_active,1);pthread_mutex_unlock(&input_mutex);
        CohInteractiveWorldControl control={&session,world_sample,world_cancelled};
        coh_interactive_world_run(window,a.data,a.length,b.data,b.length,c.data,c.length,&control,&report);
        pthread_mutex_lock(&input_mutex);atomic_store(&world_active,0);pthread_mutex_unlock(&input_mutex);
    }else{report.cancelled=world_cancelled(&session);report.obsolete=report.cancelled;
        report.expected_cancel=copied&&report.cancelled;report.session_failure=!report.expected_cancel;report.objects_released=1;
        snprintf(report.failure,sizeof report.failure,"Missing/cancelled Surface or bounded fixture input");}
    if(window){ANativeWindow_release(window);}free(a.data);free(b.data);free(c.data);
    char *json=coh_interactive_world_json(&report);jstring result=string_result(env,json?json:"{\"passed\":false,\"error\":\"World report allocation failed\"}");free(json);return result;
}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeWorldCancel(JNIEnv *env,jclass cls){(void)env;(void)cls;atomic_fetch_add(&world_epoch,1);}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeWorldForeground(JNIEnv *env,jclass cls,jboolean value){(void)env;(void)cls;atomic_store(&world_foreground,value?1:0);if(!value)atomic_fetch_add(&world_epoch,1);}
JNIEXPORT jboolean JNICALL Java_org_coh_integrationprobe_MainActivity_nativeWorldActive(JNIEnv *env,jclass cls){(void)env;(void)cls;return atomic_load(&world_active)?JNI_TRUE:JNI_FALSE;}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeCancelAudio(JNIEnv *env,jclass cls){(void)env;(void)cls;coh_audio_cancel();}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeAudioForeground(JNIEnv *env,jclass cls,jboolean value){(void)env;(void)cls;coh_audio_set_foreground(value?1:0);}
JNIEXPORT jboolean JNICALL Java_org_coh_integrationprobe_MainActivity_nativeAudioActive(JNIEnv *env,jclass cls){(void)env;(void)cls;return coh_audio_is_active()?JNI_TRUE:JNI_FALSE;}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeTransportCancel(JNIEnv *env,jclass cls){(void)env;(void)cls;coh_transport_cancel();}
JNIEXPORT void JNICALL Java_org_coh_integrationprobe_MainActivity_nativeTransportForeground(JNIEnv *env,jclass cls,jboolean value){(void)env;(void)cls;coh_transport_foreground(value?1:0);}
JNIEXPORT jboolean JNICALL Java_org_coh_integrationprobe_MainActivity_nativeTransportActive(JNIEnv *env,jclass cls){(void)env;(void)cls;return coh_transport_active()?JNI_TRUE:JNI_FALSE;}
