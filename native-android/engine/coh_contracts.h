#ifndef COH_ENGINE_CONTRACTS_H
#define COH_ENGINE_CONTRACTS_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ENGINE_ABI 1u
typedef enum { COH_OK=0, COH_INVALID=1, COH_UNSUPPORTED=2, COH_NOT_FOUND=3, COH_LIMIT=4, COH_CANCELLED=5, COH_IO=6, COH_STATE=7 } CohStatus;
/* Borrowed, immutable spans. Owner must outlive synchronous consumption. */
typedef struct { const uint8_t *data; size_t size; } CohBytes;
/* Original virtual path identity; UTF-8/NUL path is borrowed, never a disk pointer. */
typedef struct { const char *path; uint32_t generation; } CohAssetId;
typedef struct { float x,y,z; } CohVec3;
typedef struct { uint64_t tick; uint32_t actor; uint32_t kind; CohBytes payload; } CohGameEvent;
/* Poll only outside real-time callbacks. Null callback means not cancelled. */
typedef int (*CohCancelFn)(void *context);
typedef struct { CohCancelFn poll; void *context; } CohCancel;
typedef struct { uint32_t code; uint64_t count; size_t bytes; } CohDiagnostic;
#ifdef __cplusplus
}
#endif
#endif
