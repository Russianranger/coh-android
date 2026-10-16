/* Nonshipping normal-send baseline. Preserve every original probe/core byte.
 * A larger syscall cap does not guarantee any particular TCP receive boundary. */
#include "winsock_compat.h"
static int coh_intact_limits(unsigned outgoing, unsigned incoming, int fault) {
    if (outgoing != 7 || incoming != 11 || (fault != 0 && fault != 1)) {
        errno = EINVAL;
        return -1;
    }
    return coh_win_limits(1024, incoming, fault);
}
#define coh_win_limits coh_intact_limits
#include "auth_only_probe.c"
