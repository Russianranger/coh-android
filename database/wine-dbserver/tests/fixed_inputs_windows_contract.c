/* Exercise the actual Win32 environment parser with a controlled library hook.
 * The parent verifies stderr independently, including rejected requests. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "wine_fixed_inputs.h"

static unsigned hook_calls;
static int hook_accepts = 1;

int FolderCacheSetFixedInputsMode(void)
{
    ++hook_calls;
    return hook_accepts;
}

int main(int argc, char **argv)
{
    int status;
    DWORD error;

    if (argc == 2 && !strcmp(argv[1], "--late-cache"))
        hook_accepts = 0;
    else if (argc != 1)
        return 2;

    SetLastError(ERROR_SUCCESS);
    status = cohDbFixedInputsInit();
    error = GetLastError();
    printf("{\"status\":%d,\"error\":%lu,\"hook_calls\":%u,"
           "\"invalid_parameter\":%lu,\"invalid_state\":%lu}\n",
           status, error, hook_calls, (DWORD)ERROR_INVALID_PARAMETER,
           (DWORD)ERROR_INVALID_STATE);
    return 0;
}
