#ifndef COH_ENGINE_NET_UDP_H
#define COH_ENGINE_NET_UDP_H
#include "coh_net.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Additive POSIX/Android UDP owner for NetLink. Every call has one owner thread.
 * No DNS, server discovery, blocking wait, JNI, account or secret logging.
 * Addresses are explicit IPv4 bytes; ports are host-order. Peer must be unicast.
 * The caller chooses an authorized endpoint; creation itself opens no socket. */
typedef struct { uint8_t address[4]; uint16_t port; } CohNetEndpoint;
typedef struct {
    CohNetConfig link;
    CohNetEndpoint peer, local;
    unsigned receive_budget; /* 1..64 datagrams per service call. */
    CohNetKeyExchange key_exchange;
    void *key_context; /* Borrowed until destroy, called on owner thread only. */
    int encryption_required;
} CohNetUdpConfig;
typedef enum { COH_UDP_IDLE, COH_UDP_ACTIVE, COH_UDP_SUSPENDED,
    COH_UDP_CLOSED, COH_UDP_CANCELLED, COH_UDP_FAILED,
    COH_UDP_ENCRYPTION_REQUIRED, COH_UDP_TIMED_OUT } CohNetUdpState;
typedef struct {
    uint64_t sockets_opened, sockets_closed, datagrams_sent, datagrams_received;
    uint64_t peer_rejects, truncated, empty, malformed, unsupported;
    uint64_t send_would_block, interrupted, io_errors, receive_budget_exhausted;
    uint64_t suspends, resumes, cancellations, timeouts;
    int last_system_error; /* errno only: never raw body, credential or key. */
    CohNetUdpState state;
    CohNetState link_state;
    CohNetDiagnostics link;
} CohNetUdpDiagnostics;
typedef struct CohNetUdp CohNetUdp;
/* Validation is reusable before creating. local.address=0.0.0.0 and port=0
 * request a wildcard ephemeral bind; other non-unicast local IPs are invalid. */
CohStatus coh_net_udp_config_validate(const CohNetUdpConfig *);
CohNetUdp *coh_net_udp_create(const CohNetUdpConfig *);
void coh_net_udp_destroy(CohNetUdp *);
/* Begin sends nothing until service(). Only IDLE/CLOSED may begin; a cancelled,
 * timed-out, failed or suspended session requires resume() with a fresh ID. */
CohStatus coh_net_udp_begin(CohNetUdp *, uint32_t connect_id, uint64_t now_ms);
/* Nonblocking. Reads at most receive_budget datagrams, then pumps bounded TX.
 * Malformed/unexpected peer packets are counted and ignored; missing crypto is
 * explicit ENCRYPTION_REQUIRED and closes the socket without a clear fallback.
 * A zero cancel callback is allowed. Times must be monotonic milliseconds. */
CohStatus coh_net_udp_service(CohNetUdp *, uint64_t now_ms, CohCancel);
CohStatus coh_net_udp_queue(CohNetUdp *, CohBytes, uint32_t bits,
    int reliable, int ordered, int compressed, uint64_t now_ms);
CohStatus coh_net_udp_next(CohNetUdp *, CohNetMessage *);
CohStatus coh_net_udp_disconnect(CohNetUdp *, uint64_t now_ms);
/* Suspend closes only on the owner thread, clears pending gameplay/reliability
 * and compression state, and leaves diagnostics. Resume recreates everything:
 * it must be explicitly requested with a connect_id different from the last.
 * Android UI enqueues a suspend/resume request for this owner; never close its
 * descriptor directly on a second thread. No background replay is possible. */
void coh_net_udp_suspend(CohNetUdp *);
CohStatus coh_net_udp_resume(CohNetUdp *, uint32_t connect_id, uint64_t now_ms);
void coh_net_udp_cancel(CohNetUdp *);
void coh_net_udp_close(CohNetUdp *);
CohNetUdpState coh_net_udp_state(const CohNetUdp *);
CohStatus coh_net_udp_local_endpoint(const CohNetUdp *, CohNetEndpoint *);
void coh_net_udp_diagnostics(const CohNetUdp *, CohNetUdpDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
