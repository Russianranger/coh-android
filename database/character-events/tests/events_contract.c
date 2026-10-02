#include "wine_character_events.h"
#include <stdio.h>
#include <string.h>

/* Live pipe fixture: ready/position commands have no fixture flush or response.
 * The only response is the production emitter's flushed native record. */
int main(void)
{
    char command[128];
    int initialized;
    setvbuf(stdout, NULL, _IOFBF, 8192);
    initialized = cohCharacterEventsInit();
    printf("STATUS %d %lu %lu %lu\n", initialized, GetLastError(),
           GetCurrentProcessId(), GetCurrentThreadId());
    fflush(stdout);
    while (fgets(command, sizeof(command), stdin)) {
        if (!strcmp(command, "ready\n"))
            cohCharacterEventReady(1, 1, 17, "THORHERO", "COHLOCAL", "127.0.0.1", 12345);
        else if (!strcmp(command, "position\n"))
            cohCharacterEventPosition(1, 1, 17, "THORHERO", "COHLOCAL", 104.47f, 31.96f, -531.56f);
        else if (!strcmp(command, "foreign\n")) {
            cohCharacterEventReady(1, 1, 17, "OTHER", "COHLOCAL", "127.0.0.1", 12345);
            cohCharacterEventReady(1, 1, 17, "THORHERO", "COHLOCAL", "10.0.0.1", 12345);
            cohCharacterEventReady(2, 1, 17, "THORHERO", "COHLOCAL", "127.0.0.1", 12345);
            cohCharacterEventReady(1, 0, 17, "THORHERO", "COHLOCAL", "127.0.0.1", 12345);
            cohCharacterEventPosition(1, 1, 0, "THORHERO", "COHLOCAL", 0, 0, 0);
            printf("FILTERED\n");
            fflush(stdout);
        } else if (!strcmp(command, "disabled\n")) {
            cohCharacterEventReady(1, 1, 17, "THORHERO", "COHLOCAL", "127.0.0.1", 12345);
            printf("DISABLED\n");
            fflush(stdout);
        } else if (!strcmp(command, "init-again\n")) {
            initialized = cohCharacterEventsInit();
            printf("REINIT %d\n", initialized);
            fflush(stdout);
        } else if (!strcmp(command, "close\n")) {
            return 0;
        } else {
            return 3;
        }
    }
    return 0;
}
