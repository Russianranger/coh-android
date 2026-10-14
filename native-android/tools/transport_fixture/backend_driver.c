/* Host-only access to static primitives for a real POLLNVAL error case.
 * The application compiles coh_transport.c normally without this harness. */
#include "coh_transport.c"
#include <stdio.h>
int main(void) {
    CohTransportProof proof = {0}; Loop loop; loop_init(&loop);
    if (loop_open(&loop, &proof) != RECEIVE_OK) return 1;
    int dead = loop.fd[0];
    if (close(dead)) return 2;
    loop.fd[0] = -1; proof.sockets_closed++;
    Received out; memset(&out, 0xa5, sizeof(out));
    /* A closed positive descriptor reaches POLLNVAL; negative descriptors
     * would instead be ignored by poll and merely hit their deadline. */
    loop.fd[0] = dead;
    CohBlowfish cipher;
    if (coh_bf_init(&cipher, protocol_key, sizeof(protocol_key))) return 3;
    int result = receive_packet(&loop, 0, &loop.addr[1], &cipher, 0, 100, &out, &proof);
    loop.fd[0] = -1;
    loop_close(&loop, &proof);
    if (result != RECEIVE_BACKEND || proof.backend_errors != 1 ||
        !untouched(&out, sizeof(out)) || proof.timeouts ||
        proof.sockets_opened != 2 || proof.sockets_closed != 2) return 4;
    printf("{\"passed\":true,\"backend_error_cases\":1,\"transactional_backend_failure\":true,\"sockets_opened\":2,\"sockets_closed\":2}\n");
    return 0;
}
