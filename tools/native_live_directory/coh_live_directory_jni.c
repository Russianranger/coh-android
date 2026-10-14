/* Source-only JNI lifecycle. Linked only by the dedicated qualification lane. */
#define _GNU_SOURCE
#include "coh_live_directory_core.h"
#include <jni.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static pthread_mutex_t guard=PTHREAD_MUTEX_INITIALIZER;
static CohLiveNamespace *space;
static CohLiveDirectory *cursors[COH_LIVE_CURSOR_MAX];
static uint32_t generation=0,cursor_generation[COH_LIVE_CURSOR_MAX];
static uint64_t namespace_handle;

static void report(JNIEnv *env,const char *phase,int number,uint64_t rows,int fallback) {
    char message[240];jclass type;
    if((*env)->ExceptionCheck(env))return;
    snprintf(message,sizeof(message),"COH_LIVE_FAIL phase=%s errno=%d rows=%llu fallbackAllowed=%d",
        phase,number,(unsigned long long)rows,fallback);
    type=(*env)->FindClass(env,"java/io/IOException");
    if(type){(*env)->ThrowNew(env,type,message);(*env)->DeleteLocalRef(env,type);}
}
static int next_generation(JNIEnv *env) {
    if(generation==UINT32_MAX){report(env,"generation",EOVERFLOW,0,1);return 0;}
    generation++;return 1;
}
static uint64_t cursor_handle(size_t index) {
    return ((uint64_t)cursor_generation[index]<<32)|(uint64_t)(index+1);
}
static CohLiveDirectory *find_cursor(uint64_t handle,size_t *index) {
    uint32_t low=(uint32_t)handle;
    if(!low||low>COH_LIVE_CURSOR_MAX)return NULL;
    *index=low-1;
    if(!cursors[*index]||cursor_handle(*index)!=handle)return NULL;
    return cursors[*index];
}
static char *ascii_string(JNIEnv *env,jstring input) {
    const char *value;char *copy;jsize n;size_t bytes,i;
    if(!input){report(env,"string",EINVAL,0,1);return NULL;}
    n=(*env)->GetStringLength(env,input);
    if(n<1||n>=(jsize)COH_LIVE_PATH_MAX){report(env,"string",ENAMETOOLONG,0,1);return NULL;}
    value=(*env)->GetStringUTFChars(env,input,NULL);if(!value)return NULL;
    bytes=strlen(value);
    if(bytes!=(size_t)n){(*env)->ReleaseStringUTFChars(env,input,value);report(env,"string",EOPNOTSUPP,0,1);return NULL;}
    for(i=0;i<bytes;i++)if((unsigned char)value[i]<32||(unsigned char)value[i]>=127){
        (*env)->ReleaseStringUTFChars(env,input,value);report(env,"string",EOPNOTSUPP,0,1);return NULL;}
    copy=strdup(value);(*env)->ReleaseStringUTFChars(env,input,value);
    if(!copy)report(env,"string",ENOMEM,0,1);
    return copy;
}
#define JNI_NAME(name) Java_io_github_russianranger_cohclientinteractive_NativeLiveDirectory_##name

JNIEXPORT jlong JNICALL JNI_NAME(nativeCreate)(JNIEnv *env,jclass type,
    jobjectArray guest,jobjectArray host,jlongArray devices,jlongArray inodes,
    jintArray owners,jint uid,jint guest_uid,jboolean show_dot,jboolean case_sensitive) {
    CohLiveRootSpec roots[COH_LIVE_ROOT_MAX];jlong dev[COH_LIVE_ROOT_MAX],ino[COH_LIVE_ROOT_MAX];
    jint owner[COH_LIVE_ROOT_MAX];jsize count=0,i;CohLiveError error;uint64_t result=0;
    (void)type;memset(roots,0,sizeof(roots));pthread_mutex_lock(&guard);
    if(space){report(env,"create",EBUSY,0,1);goto done;}
    if(!guest||!host||!devices||!inodes||!owners){report(env,"create",EINVAL,0,1);goto done;}
    count=(*env)->GetArrayLength(env,guest);
    if(count<1||count>(jsize)COH_LIVE_ROOT_MAX||(*env)->GetArrayLength(env,host)!=count||
       (*env)->GetArrayLength(env,devices)!=count||(*env)->GetArrayLength(env,inodes)!=count||
       (*env)->GetArrayLength(env,owners)!=count||uid<0||guest_uid!=1000){report(env,"create",EINVAL,0,1);goto done;}
    (*env)->GetLongArrayRegion(env,devices,0,count,dev);(*env)->GetLongArrayRegion(env,inodes,0,count,ino);
    (*env)->GetIntArrayRegion(env,owners,0,count,owner);if((*env)->ExceptionCheck(env))goto done;
    for(i=0;i<count;i++){
        jstring a=(jstring)(*env)->GetObjectArrayElement(env,guest,i);
        jstring b=NULL;
        if((*env)->ExceptionCheck(env))goto done;
        roots[i].guest_prefix=ascii_string(env,a);
        if(a)(*env)->DeleteLocalRef(env,a);
        if((*env)->ExceptionCheck(env)||!roots[i].guest_prefix)goto done;
        b=(jstring)(*env)->GetObjectArrayElement(env,host,i);
        if((*env)->ExceptionCheck(env))goto done;
        roots[i].host_root=ascii_string(env,b);
        if(b)(*env)->DeleteLocalRef(env,b);
        if((*env)->ExceptionCheck(env)||!roots[i].host_root)goto done;
        if(!roots[i].guest_prefix||!roots[i].host_root||owner[i]<0||(*env)->ExceptionCheck(env)){
            report(env,"create",EINVAL,0,1);goto done;}
        roots[i].device=(uint64_t)dev[i];roots[i].inode=(uint64_t)ino[i];roots[i].uid=(uint32_t)owner[i];
    }
    if(!next_generation(env))goto done;
    if(!coh_live_namespace_open(&space,roots,(size_t)count,(uint32_t)uid,(uint32_t)guest_uid,
        show_dot?1:0,case_sensitive?1:0,&error)){
        report(env,"create",error.error_number,error.rows_emitted,error.fallback_allowed);goto done;}
    namespace_handle=((uint64_t)generation<<32)|UINT64_C(0x4e534331);result=namespace_handle;
done:
    for(i=0;i<(jsize)COH_LIVE_ROOT_MAX;i++){free((void *)roots[i].guest_prefix);free((void *)roots[i].host_root);}
    pthread_mutex_unlock(&guard);return (jlong)result;
}
JNIEXPORT jlong JNICALL JNI_NAME(nativeOpen)(JNIEnv *env,jclass type,jlong handle,
    jstring path,jbyteArray operation,jbyteArray directory) {
    unsigned char op[16],dir[16];char *guest=NULL;size_t index;uint64_t result=0;CohLiveError error;
    (void)type;pthread_mutex_lock(&guard);
    if(!space||(uint64_t)handle!=namespace_handle){report(env,"open",EBADF,0,1);goto done;}
    if(!operation||!directory||(*env)->GetArrayLength(env,operation)!=16||(*env)->GetArrayLength(env,directory)!=16){report(env,"open",EINVAL,0,1);goto done;}
    for(index=0;index<COH_LIVE_CURSOR_MAX&&cursors[index];index++);
    if(index==COH_LIVE_CURSOR_MAX){report(env,"open",EMFILE,0,1);goto done;}
    guest=ascii_string(env,path);if(!guest)goto done;
    (*env)->GetByteArrayRegion(env,operation,0,16,(jbyte *)op);(*env)->GetByteArrayRegion(env,directory,0,16,(jbyte *)dir);
    if((*env)->ExceptionCheck(env)||!next_generation(env))goto done;
    if(!coh_live_directory_open(space,&cursors[index],guest,op,dir,&error)){
        report(env,"open",error.error_number,error.rows_emitted,error.fallback_allowed);goto done;}
    cursor_generation[index]=generation;result=cursor_handle(index);
done:
    free(guest);pthread_mutex_unlock(&guard);return (jlong)result;
}
JNIEXPORT jbyteArray JNICALL JNI_NAME(nativeNext)(JNIEnv *env,jclass type,jlong handle) {
    size_t index,length;const unsigned char *bytes;CohLiveDirectory *cursor;CohLiveError error;jbyteArray result=NULL;
    (void)type;pthread_mutex_lock(&guard);cursor=find_cursor((uint64_t)handle,&index);
    if(!cursor){report(env,"next",EBADF,0,0);goto done;}
    if(!coh_live_directory_next(cursor,&bytes,&length,&error)){
        report(env,"next",error.error_number,error.rows_emitted,error.fallback_allowed);goto done;}
    result=(*env)->NewByteArray(env,(jsize)length);
    if(result)(*env)->SetByteArrayRegion(env,result,0,(jsize)length,(const jbyte *)bytes);
done:
    pthread_mutex_unlock(&guard);return result;
}
JNIEXPORT void JNICALL JNI_NAME(nativeCloseCursor)(JNIEnv *env,jclass type,jlong handle) {
    size_t index;CohLiveDirectory *cursor;(void)type;pthread_mutex_lock(&guard);
    cursor=find_cursor((uint64_t)handle,&index);
    if(!cursor)report(env,"closeCursor",EBADF,0,0);
    else{coh_live_directory_close(cursor);cursors[index]=NULL;cursor_generation[index]=0;}
    pthread_mutex_unlock(&guard);
}
JNIEXPORT void JNICALL JNI_NAME(nativeCloseNamespace)(JNIEnv *env,jclass type,jlong handle) {
    (void)type;pthread_mutex_lock(&guard);
    if(!space||(uint64_t)handle!=namespace_handle)report(env,"closeNamespace",EBADF,0,0);
    else{coh_live_namespace_close(space);space=NULL;namespace_handle=0;memset(cursors,0,sizeof(cursors));memset(cursor_generation,0,sizeof(cursor_generation));}
    pthread_mutex_unlock(&guard);
}
JNIEXPORT jlongArray JNICALL JNI_NAME(nativeStats)(JNIEnv *env,jclass type,jlong handle) {
    CohLiveStats stats;jlong values[6];jlongArray result=NULL;(void)type;pthread_mutex_lock(&guard);
    if(!space||(uint64_t)handle!=namespace_handle){report(env,"stats",EBADF,0,0);goto done;}
    coh_live_namespace_stats(space,&stats);
    values[0]=(jlong)stats.metadata_requests;values[1]=(jlong)stats.names_opened;values[2]=(jlong)stats.batches;
    values[3]=(jlong)stats.skipped_missing;values[4]=(jlong)stats.owned_heap_bytes;values[5]=(jlong)stats.peak_heap_bytes;
    result=(*env)->NewLongArray(env,6);if(result)(*env)->SetLongArrayRegion(env,result,0,6,values);
done:
    pthread_mutex_unlock(&guard);return result;
}
JNIEXPORT jlongArray JNICALL JNI_NAME(nativeIdentity)(JNIEnv *env,jclass type,jlong handle) {
    CohLiveDirectory *cursor;CohLiveError error;size_t index;uint64_t dev,ino;uint32_t uid;
    jlong values[3];jlongArray result=NULL;(void)type;pthread_mutex_lock(&guard);
    cursor=find_cursor((uint64_t)handle,&index);
    if(!cursor){report(env,"identity",EBADF,0,0);goto done;}
    if(!coh_live_directory_identity(cursor,&dev,&ino,&uid,&error)){
        report(env,"identity",error.error_number,error.rows_emitted,error.fallback_allowed);goto done;}
    values[0]=(jlong)dev;values[1]=(jlong)ino;values[2]=(jlong)uid;
    result=(*env)->NewLongArray(env,3);if(result)(*env)->SetLongArrayRegion(env,result,0,3,values);
done:
    pthread_mutex_unlock(&guard);return result;
}
JNIEXPORT jstring JNICALL JNI_NAME(nativeCanonicalGuestPath)(JNIEnv *env,jclass type,jlong handle) {
    CohLiveDirectory *cursor;size_t index;jstring result=NULL;(void)type;pthread_mutex_lock(&guard);
    cursor=find_cursor((uint64_t)handle,&index);
    if(!cursor)report(env,"guestPath",EBADF,0,0);
    else result=(*env)->NewStringUTF(env,coh_live_directory_guest_path(cursor));
    pthread_mutex_unlock(&guard);return result;
}
