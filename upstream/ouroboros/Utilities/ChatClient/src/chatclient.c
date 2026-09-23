#include <stdio.h>
#include <stdlib.h>
#include "coh_net.h"
#include <conio.h>
#include "windows.h"

void main(int argc, char** argv)
{
    if (argc < 3)
    {
        printf("Usage: chatclient <username> <password>\n");
        exit(0);
    }
    sockStart();

    for (;;)
    {
        static const char* server = "localhost";

        while (!cohConnect(server))
        {
            printf("connecting to %s..\n", server);
            Sleep(1000);
        }
        if (!cohLogin(argv[1], argv[2]))
        {
            break;
        }
        for (;;)
        {
            char* s = cohGetMsg();
            if (s != NULL)
            {
                printf("%s\n", s);
            }
            Sleep(1);
            if (_kbhit())
            {
                char buf[10000];
                gets_s(buf, sizeof(buf));
                cohSendMsg(buf);
            }
            if (!cohConnected())
            {
                printf("lost connection.\n");
                break;
            }
        }
    }
}
