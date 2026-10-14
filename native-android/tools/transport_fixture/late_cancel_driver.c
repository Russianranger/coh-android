/* Host-only injected parity fault followed by a later UI cancellation. */
#include "coh_transport.h"
#include <stdio.h>
int main(void) {
    CohTransportProof proof;
    coh_transport_foreground(1);
    int result = coh_transport_selftest(&proof);
    if (!result || proof.passed || !proof.session_failure || proof.expected_cancel ||
        proof.cancelled || proof.backend_errors || proof.datagrams_sent != 1 ||
        proof.datagrams_received != 1 || proof.sockets_opened != 2 || proof.sockets_closed != 2) {
        fprintf(stderr,"late-cancel driver failed: independent parity failure was waived or cleanup differs\n");
        return 1;
    }
    printf("{\"passed\":true,\"real_socket_parity_fault\":true,\"later_ui_cancel\":true,\"sticky_session_failure\":true,\"expected_cancel\":false,\"sockets_opened\":2,\"sockets_closed\":2}\n");
    return 0;
}
