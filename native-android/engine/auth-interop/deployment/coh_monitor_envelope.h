#ifndef COH_MONITOR_ENVELOPE_H
#define COH_MONITOR_ENVELOPE_H
#include "../../network/coh_net.h"
/* Payload-only request, original command10 (+5 for explicit legacy profile).
 * Packed/uncompressed only, no cookieSend/Echo. No socket, handshake or ACK.
 * Output and bit-count storage must be disjoint; known overlap/range overflow
 * refuses before writing either output. */
CohStatus coh_monitor_request(unsigned legacy,uint8_t output[8],uint32_t *bits);
typedef struct {size_t used,expected;unsigned failed;uint8_t data[COH_PROTOCOL_FRAME_MAX];} CohMonitorStream;
typedef struct {size_t size;uint8_t data[COH_PROTOCOL_FRAME_MAX];} CohMonitorFrame;
void coh_monitor_stream_reset(CohMonitorStream *);
/* Consumes at most one source TCP frame. NOT_FOUND means more bytes needed;
 * consumed preserves remaining coalesced bytes. On every non-OK return frame
 * is unchanged. Invalid lengths poison until explicit reset. No CRC/decrypt,
 * packet command or process/channel ownership is established by assembly.
 * State, input, consumed and output spans must be pairwise disjoint. Known
 * overlaps or pointer-range overflow refuse before any write, including consumed. */
CohStatus coh_monitor_stream_feed(CohMonitorStream *,CohBytes,size_t *consumed,CohMonitorFrame *);
#endif
