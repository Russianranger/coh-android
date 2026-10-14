#define _POSIX_C_SOURCE 200809L
#include "coh_transport.h"
#include "coh_protocol.h"
#include "protocol_goldens.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

enum ReceiveResult { RECEIVE_OK, RECEIVE_TIMEOUT, RECEIVE_CANCELLED,
    RECEIVE_MALFORMED, RECEIVE_ENDPOINT, RECEIVE_OVERSIZED, RECEIVE_BACKEND };
typedef struct { int fd[2]; struct sockaddr_in addr[2]; uint64_t epoch; } Loop;
typedef struct { CohProtocolPacket packet; size_t wire_bytes;
    uint8_t wire[COH_PROTOCOL_FRAME_MAX]; } Received;
static pthread_mutex_t lifecycle_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t lifecycle_epoch;
static int lifecycle_foreground = 1;
static uint32_t active_waiters;

static uint64_t milliseconds(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * UINT64_C(1000) + (uint64_t)t.tv_nsec / UINT64_C(1000000);
}
static int epoch_begin(uint64_t *out) {
    pthread_mutex_lock(&lifecycle_lock);
    *out = lifecycle_epoch;
    int allowed = lifecycle_foreground;
    pthread_mutex_unlock(&lifecycle_lock);
    return allowed;
}
static int cancelled(uint64_t epoch) {
    pthread_mutex_lock(&lifecycle_lock);
    int stop = !lifecycle_foreground || epoch != lifecycle_epoch;
    pthread_mutex_unlock(&lifecycle_lock);
    return stop;
}
void coh_transport_cancel(void) {
    pthread_mutex_lock(&lifecycle_lock);
    lifecycle_epoch++;
    pthread_mutex_unlock(&lifecycle_lock);
}
void coh_transport_foreground(int foreground) {
    pthread_mutex_lock(&lifecycle_lock);
    lifecycle_foreground = foreground != 0;
    if (!foreground) lifecycle_epoch++;
    pthread_mutex_unlock(&lifecycle_lock);
}
int coh_transport_active(void) {
    pthread_mutex_lock(&lifecycle_lock);
    int active = active_waiters != 0;
    pthread_mutex_unlock(&lifecycle_lock);
    return active;
}
static void active_change(int delta) {
    pthread_mutex_lock(&lifecycle_lock);
    if (delta > 0) active_waiters++;
    else if (active_waiters) active_waiters--;
    pthread_mutex_unlock(&lifecycle_lock);
}
static void loop_init(Loop *loop) {
    memset(loop, 0, sizeof(*loop));
    loop->fd[0] = loop->fd[1] = -1;
}
static void loop_close(Loop *loop, CohTransportProof *p) {
    for (unsigned i = 0; i < 2; i++) if (loop->fd[i] >= 0) {
        /* POSIX/Android Linux close owns the descriptor even on EINTR. Never
         * retry it and risk closing a subsequently reused descriptor. */
        if (close(loop->fd[i])) p->backend_errors++;
        else p->sockets_closed++;
        loop->fd[i] = -1;
    }
}
static int loop_open(Loop *loop, CohTransportProof *p) {
    if (!epoch_begin(&loop->epoch)) return RECEIVE_CANCELLED;
    for (unsigned i = 0; i < 2; i++) {
        if (cancelled(loop->epoch)) return RECEIVE_CANCELLED;
        loop->fd[i] = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (loop->fd[i] < 0) goto error;
        p->sockets_opened++;
        if (fcntl(loop->fd[i], F_SETFL, O_NONBLOCK) < 0 ||
            fcntl(loop->fd[i], F_SETFD, FD_CLOEXEC) < 0) goto error;
        loop->addr[i].sin_family = AF_INET;
        loop->addr[i].sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        loop->addr[i].sin_port = 0;
        if (bind(loop->fd[i], (struct sockaddr *)&loop->addr[i], sizeof(loop->addr[i]))) goto error;
        socklen_t length = sizeof(loop->addr[i]);
        if (getsockname(loop->fd[i], (struct sockaddr *)&loop->addr[i], &length) ||
            length != sizeof(loop->addr[i]) ||
            loop->addr[i].sin_family != AF_INET ||
            loop->addr[i].sin_addr.s_addr != htonl(INADDR_LOOPBACK) ||
            !loop->addr[i].sin_port) goto error;
    }
    if (loop->addr[0].sin_port == loop->addr[1].sin_port) goto error;
    return RECEIVE_OK;
error:
    p->backend_errors++;
    return RECEIVE_BACKEND;
}
static int send_bytes(Loop *loop, unsigned sender, const uint8_t *bytes,
    size_t n, CohTransportProof *p) {
    if (cancelled(loop->epoch)) return RECEIVE_CANCELLED;
    /* sendto is nonblocking. Unexpected send failure is reported; diagnostics
     * never spin or retry indefinitely on a full kernel queue. */
    ssize_t result = sendto(loop->fd[sender], bytes, n, 0,
        (struct sockaddr *)&loop->addr[1 - sender], sizeof(loop->addr[0]));
    if (result < 0 || (size_t)result != n) {
        p->backend_errors++;
        return RECEIVE_BACKEND;
    }
    p->datagrams_sent++;
    return RECEIVE_OK;
}
static int wait_readable(int fd, uint64_t epoch, unsigned timeout_ms,
    CohTransportProof *p, int explicit_wait) {
    uint64_t start = milliseconds(), deadline = start + timeout_ms;
    if (!start) { p->backend_errors++; return RECEIVE_BACKEND; }
    int result;
    int announced = 0;
    uint32_t polls_before = p->blocked_polls;
    for (;;) {
        if (cancelled(epoch)) {
            if (p->blocked_polls > polls_before) p->interrupted_blocked_poll++;
            result = RECEIVE_CANCELLED;
            break;
        }
        uint64_t now = milliseconds();
        if (!now) { p->backend_errors++; result = RECEIVE_BACKEND; break; }
        if (now >= deadline) { p->timeouts++; result = RECEIVE_TIMEOUT; break; }
        int slice = (int)(deadline - now);
        if (slice > 25) slice = 25;
        struct pollfd descriptor = { fd, POLLIN, 0 };
        p->blocked_polls++;
        if (explicit_wait && !announced) { active_change(1); announced = 1; }
        int ready = poll(&descriptor, 1, slice);
        if (ready < 0) {
            if (errno == EINTR) continue;
            p->backend_errors++; result = RECEIVE_BACKEND; break;
        }
        if (ready && (descriptor.revents & (POLLERR | POLLHUP | POLLNVAL))) {
            p->backend_errors++; result = RECEIVE_BACKEND; break;
        }
        if (ready && (descriptor.revents & POLLIN)) {
            /* Never consume a newly arrived packet after cancellation. */
            if (cancelled(epoch)) { result = RECEIVE_CANCELLED; break; }
            result = RECEIVE_OK;
            break;
        }
    }
    if (announced) active_change(-1);
    return result;
}
/* Transactional receiver: raw datagram and decode live in local storage.
 * Caller output changes only after source, length and decoder acceptance. */
static int receive_packet(Loop *loop, unsigned receiver,
    const struct sockaddr_in *expected, CohBlowfish *cipher, int encrypted,
    unsigned timeout_ms, Received *out, CohTransportProof *p) {
    int result = wait_readable(loop->fd[receiver], loop->epoch, timeout_ms, p, 0);
    if (result != RECEIVE_OK) return result;
    Received local;
    memset(&local, 0, sizeof(local));
    struct sockaddr_in source;
    memset(&source, 0, sizeof(source));
    struct iovec vector = { local.wire, sizeof(local.wire) };
    struct msghdr message;
    memset(&message, 0, sizeof(message));
    message.msg_name = &source; message.msg_namelen = sizeof(source);
    message.msg_iov = &vector; message.msg_iovlen = 1;
    ssize_t n = recvmsg(loop->fd[receiver], &message, MSG_TRUNC);
    if (n < 0) { p->backend_errors++; return RECEIVE_BACKEND; }
    p->datagrams_received++;
    p->endpoint_checks++;
    if (message.msg_namelen != sizeof(source) || source.sin_family != AF_INET ||
        source.sin_addr.s_addr != expected->sin_addr.s_addr ||
        source.sin_port != expected->sin_port) return RECEIVE_ENDPOINT;
    if ((message.msg_flags & MSG_TRUNC) || (size_t)n > sizeof(local.wire)) {
        p->truncated_datagrams++;
        return RECEIVE_OVERSIZED;
    }
    if (!n) { p->zero_datagrams++; return RECEIVE_MALFORMED; }
    local.wire_bytes = (size_t)n;
    if (coh_protocol_decode(cipher, encrypted, local.wire, local.wire_bytes,
        &local.packet)) return RECEIVE_MALFORMED;
    if (cancelled(loop->epoch)) return RECEIVE_CANCELLED;
    *out = local;
    return RECEIVE_OK;
}
static int untouched(const void *data, size_t bytes) {
    const uint8_t *b = data;
    for (size_t i = 0; i < bytes; i++) if (b[i] != 0xa5) return 0;
    return 1;
}
#define CHECK(condition) do { proof.checks++; if (!(condition)) { proof.session_failure = 1; goto done; } } while (0)
static void record_cancel(CohTransportProof *proof) {
    proof->cancelled = 1;
    proof->expected_cancel = 1;
}
/* A failed check and an explicit cancelled socket operation are distinct.
 * Cleanup never infers a clean cancellation from the current UI epoch. */
#define REQUIRE_RESULT(operation, wanted) do { \
    proof.checks++; int result_ = (operation); \
    if (result_ == RECEIVE_CANCELLED) { record_cancel(&proof); goto done; } \
    if (result_ != (wanted)) { proof.session_failure = 1; goto done; } \
} while (0)
static int exchange(Loop *loop, unsigned sender, const ProtocolGolden *g,
    CohBlowfish *cipher, CohTransportProof *p) {
    uint8_t frame[COH_PROTOCOL_FRAME_MAX]; size_t n = 0;
    p->checks++;
    if (coh_protocol_encode(cipher, g->encrypted, g->id, g->payload, g->bits,
        frame, sizeof(frame), &n) || n != g->wire_bytes || memcmp(frame, g->wire, n)) return RECEIVE_MALFORMED;
    int status = send_bytes(loop, sender, frame, n, p);
    if (status != RECEIVE_OK) return status;
    Received received;
    status = receive_packet(loop, 1 - sender, &loop->addr[sender], cipher,
        g->encrypted, 200, &received, p);
    if (status != RECEIVE_OK) return status;
    p->checks++;
    if (received.wire_bytes != n || memcmp(received.wire, g->wire, n)) return RECEIVE_MALFORMED;
    p->byte_parity_checks++;
    p->checks++;
    if (received.packet.packet_id != g->id || received.packet.payload_bits != g->bits ||
        received.packet.payload_bytes != (g->bits + 7u) / 8u ||
        memcmp(received.packet.payload, g->payload, received.packet.payload_bytes)) return RECEIVE_MALFORMED;
    p->decoded_payloads++;
    if (g->encrypted) p->encrypted_frames++; else p->clear_frames++;
    return RECEIVE_OK;
}
int coh_transport_selftest(CohTransportProof *out) {
    if (!out) return 1;
    CohTransportProof proof = {0}; CohBlowfish cipher;
    Loop loop; loop_init(&loop);
    uint64_t start = milliseconds();
    CHECK(start != 0);
    CHECK(coh_bf_init(&cipher, protocol_key, sizeof(protocol_key)) == 0);
    REQUIRE_RESULT(loop_open(&loop, &proof), RECEIVE_OK);
    for (size_t i = 0; i < sizeof(protocol_goldens) / sizeof(protocol_goldens[0]); i++)
        for (unsigned sender = 0; sender < 2; sender++)
            REQUIRE_RESULT(exchange(&loop, sender, protocol_goldens + i, &cipher, &proof), RECEIVE_OK);
    /* Actual zero, short, oversized and corrupt UDP datagrams, in both modes
     * and directions. MSG_TRUNC prevents accepting a valid-looking prefix. */
    for (int encrypted = 0; encrypted < 2; encrypted++) {
        const ProtocolGolden *g = protocol_goldens + encrypted;
        for (unsigned sender = 0; sender < 2; sender++) for (unsigned bad = 0; bad < 4; bad++) {
            uint8_t bytes[COH_PROTOCOL_FRAME_MAX + 257];
            memset(bytes, 0, sizeof(bytes));
            memcpy(bytes, g->wire, g->wire_bytes);
            size_t n;
            int expected_result = RECEIVE_MALFORMED;
            if (bad == 0) n = 0;
            else if (bad == 1) n = g->wire_bytes - 1;
            else if (bad == 2) { n = sizeof(bytes); expected_result = RECEIVE_OVERSIZED; }
            else { n = g->wire_bytes; bytes[4] ^= 1; }
            REQUIRE_RESULT(send_bytes(&loop, sender, bytes, n, &proof), RECEIVE_OK);
            Received received; memset(&received, 0xa5, sizeof(received));
            REQUIRE_RESULT(receive_packet(&loop, 1 - sender, &loop.addr[sender], &cipher,
                encrypted, 200, &received, &proof), expected_result);
            CHECK(untouched(&received, sizeof(received)));
            proof.expected_rejects++;
        }
    }
    /* Negative endpoint controls are real valid datagrams from a different
     * port than the receiver's expected peer, not fabricated sockaddr bytes. */
    for (unsigned sender = 0; sender < 2; sender++) {
        const ProtocolGolden *g = protocol_goldens + sender;
        REQUIRE_RESULT(send_bytes(&loop, sender, g->wire, g->wire_bytes, &proof), RECEIVE_OK);
        Received received; memset(&received, 0xa5, sizeof(received));
        REQUIRE_RESULT(receive_packet(&loop, 1 - sender, &loop.addr[1 - sender], &cipher,
            g->encrypted, 200, &received, &proof), RECEIVE_ENDPOINT);
        CHECK(untouched(&received, sizeof(received)));
        proof.expected_rejects++;
    }
    {
        Received received; memset(&received, 0xa5, sizeof(received));
        REQUIRE_RESULT(receive_packet(&loop, 0, &loop.addr[1], &cipher, 0, 40,
            &received, &proof), RECEIVE_TIMEOUT);
        CHECK(untouched(&received, sizeof(received)));
    }
    loop_close(&loop, &proof);
    CHECK(proof.sockets_closed == 2);
    REQUIRE_RESULT(loop_open(&loop, &proof), RECEIVE_OK);
    REQUIRE_RESULT(exchange(&loop, 0, protocol_goldens, &cipher, &proof), RECEIVE_OK);
    REQUIRE_RESULT(exchange(&loop, 1, protocol_goldens + 1, &cipher, &proof), RECEIVE_OK);
    loop_close(&loop, &proof);
    CHECK(proof.sockets_opened == 4 && proof.sockets_closed == 4);
    CHECK(proof.datagrams_sent == 84 && proof.datagrams_received == 84);
    CHECK(proof.byte_parity_checks == 66 && proof.decoded_payloads == 66);
    CHECK(proof.expected_rejects == 18 && proof.truncated_datagrams == 4 && proof.zero_datagrams == 4);
    /* Once all accepted work and cleanup completed, a later UI epoch change
     * does not retroactively turn the completed proof into a backend failure. */
    CHECK(proof.timeouts == 1 && !proof.backend_errors);
    proof.passed = 1;
done:
    loop_close(&loop, &proof);
    /* This is the ordinary selftest, never the explicit empty-poll Home
     * witness. Keep those two receipt kinds impossible to confuse. */
    proof.interrupted_blocked_poll = 0;
    if (proof.backend_errors || proof.sockets_opened != proof.sockets_closed) proof.session_failure = 1;
    if (proof.session_failure) { proof.passed = 0; proof.expected_cancel = 0; }
    proof.elapsed_ms = (uint32_t)(milliseconds() - start);
    *out = proof;
    return proof.passed ? 0 : 1;
}
int coh_transport_wait(unsigned timeout_ms, CohTransportProof *out) {
    if (!out) return 1;
    CohTransportProof proof = {0}; Loop loop; loop_init(&loop);
    uint64_t start = milliseconds();
    CHECK(start != 0 && timeout_ms >= 1 && timeout_ms <= 5000);
    REQUIRE_RESULT(loop_open(&loop, &proof), RECEIVE_OK);
    proof.checks++;
    int result = wait_readable(loop.fd[0], loop.epoch, timeout_ms, &proof, 1);
    if (result == RECEIVE_TIMEOUT) goto done; /* Bounded expiry is retryable. */
    if (result != RECEIVE_CANCELLED) { proof.session_failure = 1; goto done; }
    record_cancel(&proof);
    proof.checks++;
    if (!proof.interrupted_blocked_poll || !proof.blocked_polls) goto done;
    CHECK(proof.interrupted_blocked_poll == 1 && !proof.timeouts);
    loop_close(&loop, &proof);
    CHECK(proof.sockets_opened == 2 && proof.sockets_closed == 2 && !proof.backend_errors);
    proof.passed = 1;
done:
    loop_close(&loop, &proof);
    if (proof.backend_errors || proof.sockets_opened != proof.sockets_closed) proof.session_failure = 1;
    if (proof.session_failure) { proof.passed = 0; proof.expected_cancel = 0; }
    proof.elapsed_ms = (uint32_t)(milliseconds() - start);
    *out = proof;
    return proof.passed ? 0 : 1;
}
