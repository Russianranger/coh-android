#include "wine_loopback.h"
#include <stdio.h>

extern int sockSetLoopbackOnlyMode(void);

int cohDbLoopbackInit(void)
{
    char value[2];
    DWORD length;

    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_DB_LOOPBACK_ENVIRONMENT, value, sizeof(value));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    if (length != 1 || value[0] != '1') {
        SetLastError(ERROR_INVALID_PARAMETER);
        return -1;
    }
    if (!sockSetLoopbackOnlyMode()) {
        SetLastError(ERROR_INVALID_STATE);
        return -1;
    }
    fprintf(stdout, "\n%s\n", COH_DB_LOOPBACK_ACK);
    fflush(stdout);
    return 1;
}
