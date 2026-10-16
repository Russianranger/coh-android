/* Read-only Win32 path admission observer. The build inserts unchanged path
 * functions and the exact path cap from the admitted nonshipping sink. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "sink-path-original.inc"

int main(int argc, char **argv)
{
    char path[COH_CATALOG_SINK_PATH_MAX + 1u], root[4];
    unsigned int i, length, admitted, first = 1u;
    DWORD root_attributes, root_error, attributes, error;
    if (argc != 2 || sizeof(void *) != 4 || strlen(argv[1]) > COH_CATALOG_SINK_PATH_MAX)
        return 3;
    strcpy(path, argv[1]);
    length = (unsigned int)strlen(path);
    if (length < 4u || path[1] != ':' || path[2] != '\\') return 3;
    memcpy(root, path, 3u); root[3] = 0;
    SetLastError(0); root_attributes = GetFileAttributesA(root); root_error = GetLastError();
    admitted = (unsigned int)coh_catalog_sink_path(path, length);
    SetLastError(0); attributes = GetFileAttributesA(path); error = GetLastError();
    admitted = admitted && attributes == INVALID_FILE_ATTRIBUTES && error == ERROR_FILE_NOT_FOUND;
    printf("{\"schema\":\"coh-win32-catalog-path-v1\",\"read_only\":true,"
           "\"pointer_bits\":32,\"admitted\":%s,\"root_attributes\":%lu,\"root_error\":%lu,"
           "\"target_attributes\":%lu,\"target_error\":%lu,\"parents\":[",
           admitted ? "true" : "false", (unsigned long)root_attributes, (unsigned long)root_error,
           (unsigned long)attributes, (unsigned long)error);
    for (i = 3u; i < length; ++i)
    {
        if (path[i] != '\\' && path[i] != '/') continue;
        path[i] = 0;
        SetLastError(0); attributes = GetFileAttributesA(path); error = GetLastError();
        path[i] = '\\';
        printf("%s{\"component_end\":%u,\"attributes\":%lu,\"error\":%lu}",
               first ? "" : ",", i, (unsigned long)attributes, (unsigned long)error);
        first = 0u;
    }
    puts("]}");
    return admitted ? 0 : 2;
}
