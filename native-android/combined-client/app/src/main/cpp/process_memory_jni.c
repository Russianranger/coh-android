/* Optional bounded /proc/self observation on the Java memory control worker.
 * Reuse the qualified observer, never walk guest PIDs or sample the GL path. */
#include <jni.h>
#include "coh_process_memory.h"
JNIEXPORT jstring JNICALL Java_org_coh_nativecombined_LocalNative_processMemory(JNIEnv *env,jclass cls) {
    (void)cls;
    CohProcessMemorySnapshot sample;
    char json[1024];size_t needed=0;
    (void)coh_process_memory_sample(&sample);
    if(coh_process_memory_json(&sample,json,sizeof(json),&needed)!=COH_OK)return NULL;
    return (*env)->NewStringUTF(env,json);
}
