#include <jni.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include "coh_input.h"
#include "coh_audio.h"
#include "coh_protocol.h"

static CohInputState input;
static pthread_mutex_t input_mutex=PTHREAD_MUTEX_INITIALIZER;
static jstring result(JNIEnv *env, const char *text) { return (*env)->NewStringUTF(env,text); }
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm,void *reserved) {
    (void)vm;(void)reserved;coh_input_init(&input);return JNI_VERSION_1_6;
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeFocus(JNIEnv *env,jclass cls,jboolean focused) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);
    coh_input_focus(&input,focused?1:0);pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeAudioForeground(JNIEnv *env,jclass cls,jboolean focused) {
    (void)env;(void)cls;coh_audio_set_foreground(focused?1:0);
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeKey(JNIEnv *env,jclass cls,jint key,jboolean down) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);
    coh_input_key(&input,(uint32_t)key,down?1:0);pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeAxes(JNIEnv *env,jclass cls,jfloat x,jfloat y,jfloat z,jfloat rz) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);
    coh_input_axes(&input,x,y,z,rz);pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeTouch(JNIEnv *env,jclass cls,jint action,jint id,jfloat x,jfloat y) {
    (void)env;(void)cls;pthread_mutex_lock(&input_mutex);
    coh_input_touch(&input,action,id,x,y);pthread_mutex_unlock(&input_mutex);
}
JNIEXPORT jstring JNICALL Java_org_coh_systemsprobe_MainActivity_nativeFrame(JNIEnv *env,jclass cls,jfloat seconds) {
    (void)cls;CohInputFrame frame;memset(&frame,0,sizeof frame);
    pthread_mutex_lock(&input_mutex);int rc=coh_input_frame(&input,seconds,&frame);pthread_mutex_unlock(&input_mutex);
    char json[1600];snprintf(json,sizeof json,
        "{\"result\":%d,\"held\":%u,\"pressed\":%u,\"released\":%u,\"frames\":%u,"
        "\"clear_count\":%u,\"rejected\":%u,\"clipped\":%u,\"delta_x\":%d,\"delta_y\":%d,"
        "\"pyr\":[%.9g,%.9g,%.9g],\"target_pyr\":[%.9g,%.9g,%.9g],\"axes\":[%.9g,%.9g,%.9g,%.9g]}",
        rc,frame.held,frame.pressed,frame.released,frame.frames,frame.clear_count,frame.rejected,frame.clipped,
        frame.delta_x,frame.delta_y,frame.pyr[0],frame.pyr[1],frame.pyr[2],
        frame.target_pyr[0],frame.target_pyr[1],frame.target_pyr[2],frame.axes[0],frame.axes[1],frame.axes[2],frame.axes[3]);
    return result(env,json);
}
JNIEXPORT jstring JNICALL Java_org_coh_systemsprobe_MainActivity_nativeChecks(JNIEnv *env,jclass cls,jbyteArray blob) {
    (void)cls;CohInputProof i;CohProtocolProof p;memset(&i,0,sizeof i);memset(&p,0,sizeof p);
    int ir=coh_input_selftest(&i),pr=coh_protocol_selftest(&p);
    CohAudioFixture fixture;memset(&fixture,0,sizeof fixture);
    jsize size=blob?(*env)->GetArrayLength(env,blob):0;
    jbyte *bytes=blob?(*env)->GetByteArrayElements(env,blob,NULL):NULL;
    int ar=bytes?coh_audio_parse((const uint8_t*)bytes,(size_t)size,&fixture):COH_AUDIO_INVALID;
    CohAudioProof apf;memset(&apf,0,sizeof apf);
    int gain=coh_audio_selftest(&apf);
    int ap=ar==COH_AUDIO_OK && gain==COH_AUDIO_OK && !apf.failed && apf.checks>0;
    if(bytes)(*env)->ReleaseByteArrayElements(env,blob,bytes,JNI_ABORT);
    int ip=ir==1 && !i.failed && i.checks>0,pp=pr==0 && p.passed && p.checks>0;
    char json[1700];snprintf(json,sizeof json,
        "{\"passed\":%s,\"input\":{\"passed\":%s,\"result\":%d,\"checks\":%u,\"failed\":%u,\"source_cases\":%u,\"adapter_cases\":%u,\"max_source_error\":%.9g},"
        "\"audio_source\":{\"passed\":%s,\"result\":%d,\"sample_rate\":%u,\"channels\":%u,\"frames\":%u,\"pcm_bytes\":%u,\"checks\":%u,\"failed\":%u,\"source_cases\":%u,\"max_source_error\":%.9g},"
        "\"protocol\":{\"passed\":%s,\"result\":%d,\"checks\":%u,\"wire_cases\":%u,\"bit_cases\":%u,\"malformed_cases\":%u,\"unaligned_cases\":%u}}",
        ip&&ap&&pp?"true":"false",ip?"true":"false",ir,i.checks,i.failed,i.source_cases,i.adapter_cases,(double)i.max_source_error,
        ap?"true":"false",ar,fixture.sample_rate,fixture.channels,fixture.frames,fixture.pcm_bytes,
        apf.checks,apf.failed,apf.source_cases,apf.maximum_source_error,
        pp?"true":"false",pr,p.checks,p.wire_cases,p.bit_cases,p.malformed_cases,p.unaligned_cases);
    return result(env,json);
}
JNIEXPORT jstring JNICALL Java_org_coh_systemsprobe_MainActivity_nativePlay(JNIEnv *env,jclass cls,jbyteArray blob) {
    (void)cls;CohAudioPlayback a;memset(&a,0,sizeof a);
    jsize length=blob?(*env)->GetArrayLength(env,blob):0;
    jbyte *bytes=blob?(*env)->GetByteArrayElements(env,blob,NULL):NULL;
    CohAudioFixture f;memset(&f,0,sizeof f);
    int fixture_ok=bytes && coh_audio_parse((const uint8_t*)bytes,(size_t)length,&f)==COH_AUDIO_OK;
    int rc=bytes?coh_audio_play((const uint8_t*)bytes,(size_t)length,&a):COH_AUDIO_INVALID;
    if(bytes)(*env)->ReleaseByteArrayElements(env,blob,bytes,JNI_ABORT);
    int64_t expected_frames=(int64_t)f.frames*3+(int64_t)(f.sample_rate*15/100)*2;
    int pass=fixture_ok && rc==COH_AUDIO_OK && a.opened && a.started && a.stopped && a.closed && !a.cancelled &&
        !a.backend_errors && a.requested_clips==3 && a.completed_clips==3 && a.write_calls>0 &&
        a.actual_rate==(int)f.sample_rate && a.actual_channels==(int)f.channels && a.actual_format==1 &&
        a.submitted_frames==expected_frames && a.read_frames>=a.submitted_frames;
    char json[2400];snprintf(json,sizeof json,
        "{\"passed\":%s,\"result\":%d,\"requested_rate\":%d,\"actual_rate\":%d,\"actual_channels\":%d,\"actual_format\":%d,"
        "\"opened\":%s,\"started\":%s,\"stopped\":%s,\"closed\":%s,\"cancelled\":%s,\"backend_errors\":%d,"
        "\"requested_clips\":%d,\"completed_clips\":%d,\"partial_writes\":%d,\"write_calls\":%d,\"xrun_count\":%d,"
        "\"timestamp_available\":%s,\"submitted_frames\":%lld,\"read_frames\":%lld,\"timestamp_frame\":%lld,\"timestamp_ns\":%lld,"
        "\"source_volume_db\":%d,\"source_effective_gain\":%.9g,\"quiet_volume_db\":%d,\"quiet_effective_gain\":%.9g,\"duration_ns\":%lld}",
        pass?"true":"false",rc,a.requested_rate,a.actual_rate,a.actual_channels,a.actual_format,
        a.opened?"true":"false",a.started?"true":"false",a.stopped?"true":"false",a.closed?"true":"false",
        a.cancelled?"true":"false",a.backend_errors,a.requested_clips,a.completed_clips,a.partial_writes,a.write_calls,a.xrun_count,
        a.timestamp_available?"true":"false",(long long)a.submitted_frames,(long long)a.read_frames,(long long)a.timestamp_frame,
        (long long)a.timestamp_ns,a.source_volume_db,(double)a.source_effective_gain,a.quiet_volume_db,
        (double)a.quiet_effective_gain,(long long)a.duration_ns);
    return result(env,json);
}
JNIEXPORT void JNICALL Java_org_coh_systemsprobe_MainActivity_nativeCancelAudio(JNIEnv *env,jclass cls) {
    (void)env;(void)cls;coh_audio_cancel();
}
JNIEXPORT jboolean JNICALL Java_org_coh_systemsprobe_MainActivity_nativeAudioActive(JNIEnv *env,jclass cls) {
    (void)env;(void)cls;return coh_audio_is_active()?JNI_TRUE:JNI_FALSE;
}
