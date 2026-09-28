#ifndef COH_WINE_LOOPBACK_H
#define COH_WINE_LOOPBACK_H

#include <windows.h>

#define COH_DB_LOOPBACK_ENVIRONMENT "COH_WINE_DB_LOOPBACK_ONLY"
#define COH_DB_LOOPBACK_ACK "COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; endpoint verification required"

/* Must run before common startup and fixture dispatch. Absent=0, exact "1"=1,
 * otherwise -1 with GetLastError. Activation is one-way and refuses late calls. */
int cohDbLoopbackInit(void);

#endif
