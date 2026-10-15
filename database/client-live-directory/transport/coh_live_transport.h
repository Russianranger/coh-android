/* Source-only protocol consumer. Registration and socket custody are external. */
#ifndef COH_LIVE_TRANSPORT_H
#define COH_LIVE_TRANSPORT_H
#include <stdint.h>
#include <stddef.h>
#define COH_TRANSPORT_MAX_CURSORS 16u
#define COH_TRANSPORT_MAX_PATH 1024u
#define COH_TRANSPORT_REQUEST_BYTES 96u
#define COH_TRANSPORT_REPLY_BYTES 32u
#define COH_TRANSPORT_OK 1
#define COH_TRANSPORT_END 0
#define COH_TRANSPORT_INITIAL_DECLINE (-1)
#define COH_TRANSPORT_TERMINAL (-2)

typedef enum CohLiveTransportReason {
 COH_TRANSPORT_REASON_NONE=0, COH_TRANSPORT_REASON_CONFIG,
 COH_TRANSPORT_REASON_PATH, COH_TRANSPORT_REASON_LIMIT,
 COH_TRANSPORT_REASON_DUPLICATE_TOKEN, COH_TRANSPORT_REASON_HANDLE,
 COH_TRANSPORT_REASON_ALLOCATION, COH_TRANSPORT_REASON_SEQUENCE,
 COH_TRANSPORT_REASON_WRITE, COH_TRANSPORT_REASON_READ,
 COH_TRANSPORT_REASON_REPLY_MAGIC, COH_TRANSPORT_REASON_REPLY_VERSION,
 COH_TRANSPORT_REASON_REPLY_STATUS, COH_TRANSPORT_REASON_REPLY_SEQUENCE,
 COH_TRANSPORT_REASON_REPLY_PAYLOAD, COH_TRANSPORT_REASON_REPLY_RESERVED,
 COH_TRANSPORT_REASON_REPLY_ERROR, COH_TRANSPORT_REASON_BATCH,
 COH_TRANSPORT_REASON_PEER_DECLINE, COH_TRANSPORT_REASON_PEER_TERMINAL,
 COH_TRANSPORT_REASON_ACK_RECIPE, COH_TRANSPORT_REASON_ACK_RESERVED,
 COH_TRANSPORT_REASON_ACK_IDENTITY
} CohLiveTransportReason;

/* Blocking callbacks transfer >0 bytes, <=requested; 0 means EOF/failure,
 * negative means failure. Partial transfers are continued without replay.
 * Platform wrappers retain errno/LastError in their own context. No transient
 * zero-byte result is permitted: the consumer never polls or busy-spins. */
typedef struct CohLiveTransportIo {
 void *context;
 int32_t (*read)(void *, unsigned char *, uint32_t);
 int32_t (*write)(void *, const unsigned char *, uint32_t);
 void (*close)(void *);
 void *(*allocate)(void *, size_t);
 void (*release)(void *, void *);
} CohLiveTransportIo;
typedef struct CohLiveTransportCursor CohLiveTransportCursor;
typedef struct CohLiveTransport {
 CohLiveTransportIo io;
 unsigned char operation[16], nonce[32];
 CohLiveTransportCursor *cursors[COH_TRANSPORT_MAX_CURSORS];
 unsigned char *receive_frame;
 uint32_t request_sequence, handle_sequence, active_cursors;
 uint64_t rows_returned;
 int dead, peer_closed, shutdown_complete, result;
 CohLiveTransportReason reason;
 /* Durable first-failure attribution, retained by close/shutdown. These are
  * observations, not proof of operation/provider/thread ownership. */
 uint32_t failure_handle, failure_request_sequence;
 uint64_t failure_cursor_rows;
 uint32_t backend_status, backend_error, reply_sequence;
 int backend_reply_observed;
 uint64_t observed_device, observed_inode;
} CohLiveTransport;

/* Initialize once with an already-connected, exclusively owned peer. Caller
 * independently admits native Game/session/main-thread/bind/provider identity.
 * OPEN creates an opaque handle; stale handles and duplicate active tokens are
 * refused. A returned WFD pointer remains valid until the next batch for that
 * handle, CLOSE, or shutdown. It contains exactly 320 bytes. */
int cohLiveTransportInit(CohLiveTransport *, const CohLiveTransportIo *,
 const unsigned char operation[16], const unsigned char nonce[32]);
int cohLiveTransportOpen(CohLiveTransport *, const char *normalized_guest_path,
 const unsigned char directory_token[16], uint64_t expected_device,
 uint64_t expected_native_inode, uint32_t *handle);
int cohLiveTransportIdentity(const CohLiveTransport *, uint32_t handle,
 uint64_t *device, uint64_t *inode);
int cohLiveTransportNext(CohLiveTransport *, uint32_t handle,
 const unsigned char **wfd);
int cohLiveTransportClose(CohLiveTransport *, uint32_t *handle);
/* Always frees owned frames/cursors and closes the peer at most once. Does not
 * clear or downgrade durable errors. No transport reconnect or retry exists. */
void cohLiveTransportShutdown(CohLiveTransport *);
#endif
