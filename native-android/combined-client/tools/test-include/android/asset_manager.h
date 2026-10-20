/* Host API double declarations only; Android builds use the NDK headers. */
#ifndef COH_TEST_ASSET_MANAGER_H
#define COH_TEST_ASSET_MANAGER_H
#include <sys/types.h>
typedef struct AAssetManager AAssetManager;
typedef struct AAsset AAsset;
#define AASSET_MODE_RANDOM 1
AAsset *AAssetManager_open(AAssetManager *,const char *,int);
int AAsset_openFileDescriptor(AAsset *,off_t *,off_t *);
void AAsset_close(AAsset *);
#endif
