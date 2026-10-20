#ifndef COH_SESSION_FRAME_CAPTURE_H
#define COH_SESSION_FRAME_CAPTURE_H
#include <stddef.h>
#include <stdint.h>
#define COH_CAPTURE_WIDTH 192u
#define COH_CAPTURE_HEIGHT 108u
#define COH_CAPTURE_HEADER 128u
#define COH_CAPTURE_PIXELS (COH_CAPTURE_WIDTH*COH_CAPTURE_HEIGHT*4u)
#define COH_CAPTURE_BYTES (COH_CAPTURE_HEADER+COH_CAPTURE_PIXELS)
#define COH_CAPTURE_RESERVE (1024u*1024u)
#define COH_CAPTURE_SCENE_LIMIT (96u*1024u*1024u)
#define COH_CAPTURE_WAIT 12u
typedef struct CohFrameCapture CohFrameCapture;
typedef struct {
    uint32_t viewport_width,viewport_height,entity_index;
    uint64_t frame,epoch,pose_generation,pose_lock_frame,world_packets,entity_draws,base_charge;
    float pose[3];
} CohFrameCaptureInfo;
/* Actual render owner only. Reserve includes old/candidate pixels, FBO, JNI and
 * export copies, bounded zip/hash buffers and a charged 64 KiB native stack.
 * Known worst-case overlap: two 83,072 B records +owner metadata, 82,944 B FBO,
 * 2 * 83,072 B native/JNI copies, 83,200 B Java export snapshot, 2 * 16 KiB I/O/hash scratch,
 * 3 * 8 KiB JSON/string copies and 64 KiB native stack: less than 650 KiB.
 * The 1 MiB policy reservation rounds this source inventory upward. GL driver
 * overhead and actual Java/native RSS/PSS are not measured by this inventory.
 * Existing scene owners remain charged separately; no reservation ticket. */
CohFrameCapture *coh_frame_capture_create(uint64_t base_charge);
void coh_frame_capture_destroy(CohFrameCapture **);
int coh_frame_capture_begin(CohFrameCapture *,const CohFrameCaptureInfo *,uint8_t **,uint32_t *,uint32_t *);
void coh_frame_capture_publish(CohFrameCapture *,int presented);
/* Caller holds Session mutex while copying; GL never holds that mutex. */
const uint8_t *coh_frame_capture_data(const CohFrameCapture *,size_t *,uint64_t after_frame);
size_t coh_frame_capture_owned_bytes(const CohFrameCapture *);
#endif
