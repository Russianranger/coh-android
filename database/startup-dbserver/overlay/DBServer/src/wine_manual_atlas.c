#include "wine_manual_atlas.h"
#include <stdio.h>

static int exactEnabled(const char *name)
{
    char value[2];
    DWORD length = GetEnvironmentVariableA(name, value, sizeof(value));
    return length == 1 && value[0] == '1';
}

int cohDbManualAtlasLauncherWait(int start_static, int fake_auth, int auth_server_present,
    int queue_server, int use_logserver, int launcher_count, int launchers_connecting)
{
    char value[2];
    DWORD length;

    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_DB_MANUAL_ATLAS_ENVIRONMENT, value, sizeof(value));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    if (length != 1 || value[0] != '1' || start_static != 0 || !fake_auth
        || auth_server_present || queue_server || use_logserver || launcher_count
        || launchers_connecting || !exactEnabled("COH_WINE_DB_FIXED_INPUTS")
        || !exactEnabled("COH_WINE_DB_LOOPBACK_ONLY")) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return -1;
    }
    fprintf(stdout, "\n%s\n", COH_DB_MANUAL_ATLAS_ACK);
    fflush(stdout);
    return 1;
}
