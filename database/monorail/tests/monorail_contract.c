#include "wine_monorail.h"
#include <stdio.h>
#include <string.h>
int main(void)
{
    char command[80];
    int status = cohMonorailInit();
    printf("STATUS %d %lu %lu\n", status, GetCurrentProcessId(), GetCurrentThreadId()); fflush(stdout);
    while (fgets(command, sizeof(command), stdin)) {
        if (!strncmp(command, "request", 7)) {
            int accepted = cohMonorailRequest(1, 5, 1, 17, "THORHERO", "COHLOCAL");
            printf("REQUEST %d\n", accepted);
        } else if (!strncmp(command, "poll", 4)) printf("POLL %d\n", cohMonorailPoll(1, 1, 17));
        else if (!strncmp(command, "ready5", 6)) { cohZoningEvent("ready",5,1,17,"THORHERO","COHLOCAL","127.0.0.1",777,0,0,0); puts("READY"); }
        else if (!strncmp(command, "position5", 9)) { cohZoningEvent("position",5,1,17,"THORHERO","COHLOCAL",NULL,0,12,34,56); puts("POSITION"); }
        else if (!strncmp(command, "foreign", 7)) {
            cohZoningEvent("ready",6,1,17,"THORHERO","COHLOCAL","127.0.0.1",777,0,0,0);
            cohZoningEvent("ready",5,2,17,"THORHERO","COHLOCAL","127.0.0.1",777,0,0,0);
            cohZoningEvent("ready",5,1,17,"THORHERO","COHLOCAL","10.0.0.1",777,0,0,0);
            puts("FILTERED");
        } else if (!strncmp(command,"cancel",6)) {cohMonorailCancel(); puts("CANCELLED");}
        else if (!strncmp(command,"reinit",6)) printf("REINIT %d\n",cohMonorailInit());
        fflush(stdout);
    }
    return 0;
}
