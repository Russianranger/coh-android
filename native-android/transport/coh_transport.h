#ifndef COH_TRANSPORT_H
#define COH_TRANSPORT_H
#include <stdint.h>

/* Gate 14 is an IPv4 loopback UDP adapter for the accepted gate 12 profile.
 * These diagnostics cannot connect to a server or perform game login. */
typedef struct {
    uint32_t passed, checks, cancelled, expected_cancel, session_failure;
    uint32_t datagrams_sent, datagrams_received;
    uint32_t clear_frames, encrypted_frames, expected_rejects;
    uint32_t endpoint_checks, byte_parity_checks, decoded_payloads;
    uint32_t truncated_datagrams, zero_datagrams;
    uint32_t timeouts, blocked_polls, interrupted_blocked_poll;
    uint32_t sockets_opened, sockets_closed, backend_errors, elapsed_ms;
} CohTransportProof;

/* All opened descriptors belong to the calling worker. Each function closes
 * them before returning, including cancellation and every error path. */
int coh_transport_selftest(CohTransportProof *out);
/* An ordinary foreground selftest can be aborted by Android Home. Only an
 * explicit CANCELLED socket operation sets expected_cancel. Such a partial
 * receipt is retryable, never a transport pass or the explicit Home witness.
 * Every observed parity/check/backend/cleanup failure remains session_failure,
 * including when cancellation arrives after that failure. */
/* Opens two loopback endpoints and performs a bounded empty receive. Success
 * requires cancellation during that poll, not merely expiration. 1..5000ms.
 * Call active() from the UI before requesting Android Home to qualify an
 * interruption of an actual native wait. */
int coh_transport_wait(unsigned timeout_ms, CohTransportProof *out);
/* Mutex protected epochs: UI calls never close a worker's descriptors.
 * foreground(0) also cancels. foreground(1) permits new runs; an old run still
 * sees its changed epoch. cancel() also cancels without backgrounding. */
void coh_transport_cancel(void);
void coh_transport_foreground(int foreground);
int coh_transport_active(void);
#endif
