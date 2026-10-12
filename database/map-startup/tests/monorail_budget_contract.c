/* Real Win32 bridge fixture; only its elapsed clock is deterministic. */
#include "wine_monorail.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static DWORD fixture_tick = 1000;
DWORD WINAPI cohMonorailFixtureTick(void) { return fixture_tick; }

int main(void)
{
    char command[80];
    int status = cohMonorailInit();
    printf("STATUS %d %lu %lu\n", status, GetCurrentProcessId(), GetCurrentThreadId());
    fflush(stdout);
    while (fgets(command, sizeof(command), stdin)) {
        if (!strncmp(command, "advance ", 8)) {
            fixture_tick += (DWORD)strtoul(command + 8, NULL, 10);
            printf("TICK %lu\n", fixture_tick);
        } else if (!strncmp(command, "tick ", 5)) {
            fixture_tick = (DWORD)strtoul(command + 5, NULL, 10);
            printf("TICK %lu\n", fixture_tick);
        } else if (!strncmp(command, "request", 7)) {
            int accepted = cohMonorailRequest(1, 5, 1, 17, "THORHERO", "COHLOCAL");
            printf("REQUEST %d\n", accepted);
        } else if (!strncmp(command, "foreignrequest", 14)) {
            printf("FOREIGN %d %d %d\n",
                cohMonorailRequest(1, 5, 2, 17, "THORHERO", "COHLOCAL"),
                cohMonorailRequest(1, 5, 1, 17, "OTHER", "COHLOCAL"),
                cohMonorailRequest(1, 1, 1, 17, "THORHERO", "COHLOCAL"));
        } else if (!strncmp(command, "foreignpoll", 11)) {
            printf("POLL %d\n", cohMonorailPoll(1, 2, 17));
        } else if (!strncmp(command, "poll", 4)) {
            printf("POLL %d\n", cohMonorailPoll(1, 1, 17));
        } else if (!strncmp(command, "cancel", 6)) {
            cohMonorailCancel(); puts("CANCELLED");
        } else if (!strncmp(command, "reinit", 6)) {
            printf("REINIT %d\n", cohMonorailInit());
        }
        fflush(stdout);
    }
    return 0;
}
