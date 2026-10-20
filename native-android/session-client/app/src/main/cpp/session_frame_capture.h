#ifndef COH_SESSION_FRAME_CAPTURE_H
#define COH_SESSION_FRAME_CAPTURE_H
#include <stddef.h>
#include <stdint.h>
#ifndef COH_FULLSCREEN_DIAGNOSTIC
#define COH_FULLSCREEN_DIAGNOSTIC 0
#endif
#if COH_FULLSCREEN_DIAGNOSTIC
#define COH_CAPTURE_WIDTH 640u
#define COH_CAPTURE_HEIGHT 360u
#else
#define COH_CAPTURE_WIDTH 192u
#define COH_CAPTURE_HEIGHT 108u
#endif
#define COH_CAPTURE_HEADER 128u
#define COH_CAPTURE_PIXELS (COH_CAPTURE_WIDTH*COH_CAPTURE_HEIGHT*4u)
#define COH_CAPTURE_BYTES (COH_CAPTURE_HEADER+COH_CAPTURE_PIXELS)
#if COH_FULLSCREEN_DIAGNOSTIC
#define COH_CAPTURE_RESERVE (coh_frame_capture_reserve_bytes())
#else
#define COH_CAPTURE_RESERVE (1024u*1024u)
#endif
#define COH_CAPTURE_SCENE_LIMIT (96u*1024u*1024u)
#define COH_CAPTURE_WAIT 12u
typedef struct CohFrameCapture CohFrameCapture;
typedef struct {
    uint32_t viewport_width,viewport_height,entity_index;
    uint64_t frame,epoch,pose_generation,pose_lock_frame,world_packets,entity_draws,base_charge;
    float pose[3];
} CohFrameCaptureInfo;
/* Source payload inventory, separate from driver/JVM/provider overhead and
 * observed RSS/PSS. The fullscreen reserve is derived in the concrete owner:
 * old+candidate records/control, FBO pixels, native JNI temporary +Java JNI
 * array, Java export snapshot, fixed headers, I/O/hash scratch, bounded JSON
 * copies and64KiB charged native stack. It does not enlarge the96MiB ceiling.
 * Historical0.1.16 keeps its192x108/1MiB subpolicy unchanged. */
uint32_t coh_frame_capture_reserve_bytes(void);
CohFrameCapture *coh_frame_capture_create(uint64_t base_charge);
void coh_frame_capture_destroy(CohFrameCapture **);
int coh_frame_capture_begin(CohFrameCapture *,const CohFrameCaptureInfo *,uint8_t **,uint32_t *,uint32_t *);
void coh_frame_capture_publish(CohFrameCapture *,int presented);
/* Caller holds Session mutex while copying; GL never holds that mutex. */
const uint8_t *coh_frame_capture_data(const CohFrameCapture *,size_t *,uint64_t after_frame);
size_t coh_frame_capture_owned_bytes(const CohFrameCapture *);
#endif
