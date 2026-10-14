#define _POSIX_C_SOURCE 200809L
#include "coh_transport.h"
#include <dirent.h>
#include <pthread.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

typedef struct { CohTransportProof proof; unsigned timeout_ms; int result; } Worker;
static pthread_mutex_t test_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t test_poll = PTHREAD_COND_INITIALIZER;
static int observe_normal_poll, saw_normal_poll;
int __real_poll(struct pollfd *, nfds_t, int);
/* Observe a genuinely empty socket receive without adding a shipped hook.
 * --wrap=poll is used only in the host test executable. */
int __wrap_poll(struct pollfd *descriptors, nfds_t count, int timeout) {
    pthread_mutex_lock(&test_lock);
    int observe = observe_normal_poll;
    pthread_mutex_unlock(&test_lock);
    if (observe && timeout > 0 && __real_poll(descriptors, count, 0) == 0) {
        pthread_mutex_lock(&test_lock);
        if (observe_normal_poll) { saw_normal_poll = 1; pthread_cond_signal(&test_poll); }
        pthread_mutex_unlock(&test_lock);
    }
    return __real_poll(descriptors, count, timeout);
}
int __wrap___poll_chk(struct pollfd *descriptors, nfds_t count, int timeout, size_t bytes) {
    if (count > bytes / sizeof(*descriptors)) return -1;
    return __wrap_poll(descriptors, count, timeout);
}
static void pause_ms(unsigned ms) {
    struct timespec t = { ms / 1000, (long)(ms % 1000) * 1000000L };
    nanosleep(&t, NULL);
}
static void *run_wait(void *data) {
    Worker *w = data;
    w->result = coh_transport_wait(w->timeout_ms, &w->proof);
    return NULL;
}
static void *run_normal(void *data) {
    Worker *w = data;
    w->result = coh_transport_selftest(&w->proof);
    return NULL;
}
static int await_active(void) {
    for (unsigned i = 0; i < 500; i++) {
        if (coh_transport_active()) { pause_ms(5); return 1; }
        pause_ms(1);
    }
    return 0;
}
static unsigned descriptor_count(void) {
    DIR *dir = opendir("/proc/self/fd");
    if (!dir) return 0;
    unsigned count = 0; struct dirent *entry;
    while ((entry = readdir(dir))) if (entry->d_name[0] != '.') count++;
    closedir(dir);
    return count;
}
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "transport driver failed at line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(void) {
    unsigned before = descriptor_count(), cancelled_waits = 0, cancelled_normals = 0;
    REQUIRE(before != 0);
    CohTransportProof normal;
    REQUIRE(!coh_transport_selftest(&normal) && normal.passed);
    REQUIRE(!normal.cancelled && !normal.expected_cancel && !normal.session_failure);
    REQUIRE(normal.datagrams_sent == 84 && normal.datagrams_received == 84);
    REQUIRE(normal.expected_rejects == 18 && normal.truncated_datagrams == 4);
    REQUIRE(normal.zero_datagrams == 4 && normal.timeouts == 1);
    REQUIRE(normal.sockets_opened == 4 && normal.sockets_closed == 4);
    CohTransportProof timeout;
    REQUIRE(coh_transport_wait(40, &timeout) && !timeout.passed);
    REQUIRE(timeout.timeouts == 1 && !timeout.interrupted_blocked_poll);
    REQUIRE(!timeout.cancelled && !timeout.expected_cancel && !timeout.session_failure);
    REQUIRE(timeout.elapsed_ms >= 40 && timeout.elapsed_ms < 1000);
    REQUIRE(timeout.sockets_opened == 2 && timeout.sockets_closed == 2 && !timeout.backend_errors);
    REQUIRE(!coh_transport_active());
    for (unsigned i = 0; i < 10; i++) {
        Worker w; memset(&w, 0, sizeof(w)); w.timeout_ms = 400;
        pthread_t thread;
        REQUIRE(!pthread_create(&thread, NULL, run_wait, &w));
        REQUIRE(await_active());
        if (i % 2) {
            /* Restoration happens immediately: only the monotonic cancel
             * epoch prevents the old waiter being resurrected. */
            coh_transport_foreground(0);
            coh_transport_foreground(1);
        } else coh_transport_cancel();
        REQUIRE(!pthread_join(thread, NULL));
        REQUIRE(!w.result && w.proof.passed && w.proof.interrupted_blocked_poll == 1);
        REQUIRE(w.proof.cancelled && w.proof.expected_cancel && !w.proof.session_failure);
        REQUIRE(!w.proof.timeouts && !w.proof.backend_errors);
        REQUIRE(w.proof.elapsed_ms < 200 && w.proof.sockets_opened == 2 && w.proof.sockets_closed == 2);
        REQUIRE(!coh_transport_active());
        cancelled_waits++;
    }
    /* Two workers exercise the shared epoch/active count while every worker
     * retains its own descriptor ownership. */
    Worker both[2]; pthread_t threads[2]; memset(both, 0, sizeof(both));
    for (unsigned i = 0; i < 2; i++) { both[i].timeout_ms = 400;
        REQUIRE(!pthread_create(threads + i, NULL, run_wait, both + i)); }
    REQUIRE(await_active()); pause_ms(10); coh_transport_cancel();
    for (unsigned i = 0; i < 2; i++) {
        REQUIRE(!pthread_join(threads[i], NULL));
        REQUIRE(!both[i].result && both[i].proof.passed);
        REQUIRE(both[i].proof.sockets_opened == both[i].proof.sockets_closed);
        cancelled_waits++;
    }
    REQUIRE(!coh_transport_active());
    for (unsigned i = 0; i < 6; i++) {
        Worker w; memset(&w, 0, sizeof(w)); pthread_t thread;
        pthread_mutex_lock(&test_lock); observe_normal_poll = 1; saw_normal_poll = 0;
        pthread_mutex_unlock(&test_lock);
        REQUIRE(!pthread_create(&thread, NULL, run_normal, &w));
        struct timespec deadline; REQUIRE(!clock_gettime(CLOCK_REALTIME, &deadline)); deadline.tv_sec++;
        pthread_mutex_lock(&test_lock);
        while (!saw_normal_poll) REQUIRE(!pthread_cond_timedwait(&test_poll, &test_lock, &deadline));
        observe_normal_poll = 0; pthread_mutex_unlock(&test_lock);
        if (i % 2) { coh_transport_foreground(0); coh_transport_foreground(1); }
        else coh_transport_cancel();
        REQUIRE(!pthread_join(thread, NULL));
        REQUIRE(w.result && !w.proof.passed && w.proof.cancelled && w.proof.expected_cancel && !w.proof.session_failure);
        REQUIRE(!w.proof.backend_errors && w.proof.sockets_opened == 2 && w.proof.sockets_closed == 2);
        REQUIRE(w.proof.datagrams_sent == 82 && w.proof.datagrams_received == 82);
        REQUIRE(w.proof.expected_rejects == 18 && !w.proof.interrupted_blocked_poll);
        REQUIRE(!coh_transport_active()); cancelled_normals++;
    }
    coh_transport_foreground(0);
    REQUIRE(coh_transport_selftest(&timeout) && !timeout.passed && !timeout.sockets_opened);
    REQUIRE(timeout.cancelled && timeout.expected_cancel && !timeout.session_failure && !timeout.interrupted_blocked_poll);
    REQUIRE(coh_transport_wait(40, &timeout) && !timeout.passed && !timeout.sockets_opened);
    REQUIRE(timeout.cancelled && timeout.expected_cancel && !timeout.session_failure && !timeout.interrupted_blocked_poll);
    coh_transport_foreground(1);
    REQUIRE(coh_transport_wait(0, &timeout) && !timeout.sockets_opened);
    REQUIRE(coh_transport_wait(5001, &timeout) && !timeout.sockets_opened);
    REQUIRE(coh_transport_selftest(NULL) && coh_transport_wait(40, NULL));
    CohTransportProof reopened;
    REQUIRE(!coh_transport_selftest(&reopened) && reopened.passed);
    unsigned after = descriptor_count();
    REQUIRE(before == after);
    printf("{\"passed\":true,\"checks\":%u,\"datagrams_sent\":%u,\"datagrams_received\":%u,\"clear_frames\":%u,\"encrypted_frames\":%u,\"expected_rejects\":%u,\"endpoint_checks\":%u,\"byte_parity_checks\":%u,\"decoded_payloads\":%u,\"truncated_datagrams\":%u,\"zero_datagrams\":%u,\"timeouts\":%u,\"sockets_opened\":%u,\"sockets_closed\":%u,\"backend_errors\":%u,\"cancelled_waits\":%u,\"cancelled_ordinary_selftests\":%u,\"foreground_restore_cases\":8,\"concurrent_waiters\":2,\"descriptor_count_before\":%u,\"descriptor_count_after\":%u,\"reopened_passed\":true,\"elapsed_ms\":%u}\n",
        normal.checks, normal.datagrams_sent, normal.datagrams_received,
        normal.clear_frames, normal.encrypted_frames, normal.expected_rejects,
        normal.endpoint_checks, normal.byte_parity_checks, normal.decoded_payloads,
        normal.truncated_datagrams, normal.zero_datagrams, normal.timeouts,
        normal.sockets_opened, normal.sockets_closed, normal.backend_errors,
        cancelled_waits, cancelled_normals, before, after, normal.elapsed_ms);
    return 0;
}
