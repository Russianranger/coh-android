/* Interactive test driver for the actual opt-in producer. Its parent reads
 * the shared file independently while this process remains alive. */
#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wine_map_progress.h"

static unsigned own_threads(void)
{
    THREADENTRY32 entry;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    unsigned count = 0;
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    memset(&entry, 0, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (Thread32First(snapshot, &entry)) {
        do {
            if (entry.th32OwnerProcessID == GetCurrentProcessId()) ++count;
        } while (Thread32Next(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return count;
}

int main(void)
{
    char command[128];
    unsigned before = own_threads();
    int status = cohMapProgressInit();
    DWORD error = GetLastError();
    printf("{\"kind\":\"ready\",\"status\":%d,\"error\":%lu,\"pid\":%lu,\"tid\":%lu,"
           "\"threads_before\":%u,\"threads_after\":%u}\n", status, error,
           GetCurrentProcessId(), GetCurrentThreadId(), before, own_threads());
    fflush(stdout);
    while (fgets(command, sizeof(command), stdin)) {
        if (!strncmp(command, "mark ", 5)) {
            unsigned stage = (unsigned)strtoul(command + 5, NULL, 10);
            cohMapProgressMark((CohMapProgressStage)stage);
            printf("{\"kind\":\"marked\",\"stage\":%u}\n", stage);
            fflush(stdout);
        } else if (!strcmp(command, "init-again\n")) {
            int again = cohMapProgressInit();
            printf("{\"kind\":\"reinitialized\",\"status\":%d,\"error\":%lu}\n",
                   again, GetLastError());
            fflush(stdout);
        } else if (!strcmp(command, "close-and-mark\n")) {
            cohMapProgressClose();
            cohMapProgressMark(COH_MAP_STAGE_TICK_BEGIN);
            cohMapProgressClose();
            puts("{\"kind\":\"closed-and-marked\"}");
            fflush(stdout);
            return 0;
        } else if (!strcmp(command, "close\n")) {
            cohMapProgressClose();
            puts("{\"kind\":\"closed\"}");
            fflush(stdout);
            return 0;
        } else return 2;
    }
    cohMapProgressClose();
    return ferror(stdin) ? 2 : 0;
}
