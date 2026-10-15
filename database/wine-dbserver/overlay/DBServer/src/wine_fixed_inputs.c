#include "wine_fixed_inputs.h"
#include <stdio.h>

/* Defined by the staged UtilitiesLib FolderCache implementation. Keeping this
 * narrow declaration lets the flag contract compile without engine startup. */
extern int FolderCacheSetFixedInputsMode(void);

int cohDbFixedInputsInit(void)
{
    char value[2];
    DWORD length;

    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_DB_FIXED_INPUTS_ENVIRONMENT, value, sizeof(value));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    if (length != 1 || value[0] != '1') {
        SetLastError(ERROR_INVALID_PARAMETER);
        return -1;
    }
    if (!FolderCacheSetFixedInputsMode()) {
        SetLastError(ERROR_INVALID_STATE);
        return -1;
    }
    fprintf(stderr, "%s\n", COH_DB_FIXED_INPUTS_ACK);
    return 1;
}
