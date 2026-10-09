#ifndef COH_WINE_FIXED_INPUTS_H
#define COH_WINE_FIXED_INPUTS_H

#include <windows.h>

#define COH_DB_FIXED_INPUTS_ENVIRONMENT "COH_WINE_DB_FIXED_INPUTS"
#define COH_DB_FIXED_INPUTS_ACK "COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved"

/* Normal startup only, before any FolderCacheCreate: absent=0, exact "1"=1,
 * otherwise -1 with GetLastError. A successful request prints the exact ACK. */
int cohDbFixedInputsInit(void);

#endif
