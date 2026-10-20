#ifndef COH_TEST_ASSET_MANAGER_JNI_H
#define COH_TEST_ASSET_MANAGER_JNI_H
#include <jni.h>
#include "asset_manager.h"
AAssetManager *AAssetManager_fromJava(JNIEnv *,jobject);
#endif
