#include "clientError.h"
#include "graphics/font.h"
#include "UI/uiConsole.h"
#include "win/win_init.h"
#include <utilitieslib/utils/error.h>
#include <utilitieslib/assert/assert.h>
#include <utilitieslib/utils/timing.h>
#include <utilitieslib/version/AppRegCache.h>
#include <utilitieslib/utils/RegistryReader.h>
#include "UI/sprite/sprite_text.h"
#include <utilitieslib/utils/utils.h>
#include <utilitieslib/utils/file.h>
#include "cmdparse/cmdgame.h"
#include "clientcomm/dbclient.h"
#include <utilitieslib/language/MessageStoreUtil.h>

//------------------------------------------------------------
// Error callbacks
//------------------------------------------------------------

static void letThemKnowWhy()
{
    static bool doneonce=false;
    char str[256];
    if (doneonce)
        return;
    doneonce = true;
    if (cmdAccessLevel()) {
        sprintf(str, "You are seeing pop-up errors because you have Access Level (%d) or you are on a QA server.  These will not be seen by customers.", cmdAccessLevel());
    } else {
        sprintf(str, "You are seeing pop-up errors because you are on a QA server.  These will not be seen by customers.");
    }
    conPrintf("%s", str);
    winMsgAlert(str);
}

void clientErrorfCallback(char* errMsg)
{
    printf("%s\n", errMsg);
    if( strlen(errMsg) < 1000 )
        printToScreenLog(1,"%s",errMsg);
    if (errorGetVerboseLevel() != 2)
    {
        if ( (ErrorfCount() < 5 || 0 == strnicmp( errMsg, "NO LIMIT", 8)) )
        {
            if (isDevelopmentMode() ||
                cmdAccessLevel() > 0 ||
                // Check IP for QA and internal test
                strncmp(db_info.address,"ip-stripped-todo",10)==0 ||
                strncmp(db_info.address,"ip-stripped-todo",13)==0 ||     // NCSoft CoH QA DBserver
                strncmp(db_info.address,"ip-stripped-todo",13)==0 ||     // NCSoft CoV QA DBserver
                game_state.local_map_server)
            {
                if (!isDevelopmentMode())
                    letThemKnowWhy();
            } else if (game_state.cs_address[0]) {
                char db_ip[100];
                strcpy(db_ip, makeIpStr(ipFromString(game_state.cs_address)));
                if (strncmp(db_ip,"ip-stripped-todo",10)==0 ||
                    strncmp(db_ip,"ip-stripped-todo",13)==0 ||     // NCSoft CoH QA DBserver
                    strncmp(db_ip,"ip-stripped-todo",13)==0)     // NCSoft CoV QA DBserver
                {
                    letThemKnowWhy();
                }
            }
        }
    }
}

void clientProductionCrashCallback(char *errMsg)
{
    // This is called in production when the client crashes.  Set a field in the registry to tell it to re-verify all files
    registryWriteInt(regGetAppKey(), "VerifyOnNextUpdate", 1);
}


static int client_submit_crash_report=1;
void noErrorReportsCallback(char* errMsg)
{
    winMsgAlert(textStd("CoHCrash"));
    windowExit(-1);
}

void disableClientCrashReports(void)
{
    client_submit_crash_report=0;
    setAssertMode(ASSERTMODE_CALLBACK|ASSERTMODE_EXIT);
    setAssertCallback(noErrorReportsCallback);
}

void clientFatalErrorfCallback(char* errMsg)
{
    winErrorDialog(errMsg, "Fatal Error", 0, 1);
    if (!fileIsUsingDevData() && client_submit_crash_report) {
        // Submit crash report
        assertmsg(0, errMsg);
    }
    windowExit(-1);
}

//------------------------------------------------------------
// Status printf
//------------------------------------------------------------
static char status_line[1000];
static int timer;

void status_printf(char const *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    Vsprintf(status_line, fmt, ap);
    va_end(ap);
#ifndef CLIENT
    printf("%s\n",status_line);
#else
    if (!timer)
        timer = timerAlloc();
    timerStart(timer);
#endif
}

#if CLIENT
void statusLineDraw()
{
    if (!timer || timerElapsed(timer) > 10.f)
        return;
    xyprintf(0,480/8-1 + TEXT_JUSTIFY,"%s",status_line);
}
#endif
