/* Explicit minimal host JNI function-table double; no Android/JNI ABI proof. */
#ifndef COH_INTEROP_TEST_JNI_H
#define COH_INTEROP_TEST_JNI_H
#include <stdint.h>
typedef int32_t jint;typedef int64_t jlong;typedef uint16_t jchar;typedef uint8_t jboolean;typedef int8_t jbyte;typedef jint jsize;
typedef void *jobject;typedef jobject jclass;typedef jobject jstring;typedef jobject jbyteArray;
struct JNINativeInterface_;typedef const struct JNINativeInterface_ *JNIEnv;
struct JNINativeInterface_ {
 jsize (*GetStringLength)(JNIEnv*,jstring);
 const jchar *(*GetStringChars)(JNIEnv*,jstring,jboolean*);
 void (*ReleaseStringChars)(JNIEnv*,jstring,const jchar*);
 jboolean (*ExceptionCheck)(JNIEnv*);
 jbyteArray (*NewByteArray)(JNIEnv*,jsize);
 void (*SetByteArrayRegion)(JNIEnv*,jbyteArray,jsize,jsize,const jbyte*);
 void (*DeleteLocalRef)(JNIEnv*,jobject);
 jstring (*NewStringUTF)(JNIEnv*,const char*);
};
#define JNIEXPORT
#define JNICALL
#define JNI_FALSE 0
#define JNI_TRUE 1
#endif
