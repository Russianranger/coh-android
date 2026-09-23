#include "serverError.h"
#include <utilitieslib/utils/utils.h>
#include <utilitieslib/utils/error.h>
#include <utilitieslib/version/AppVersion.h>
#include <utilitieslib/assert/assert.h>
#include "dbcomm/dbcomm.h"
#include <utilitieslib/utils/winutil.h>
#include <utilitieslib/utils/sysutil.h>
#include "cmdparse/cmdserver.h"
#include "dbcomm/logcomm.h"
#include <utilitieslib/utils/file.h>

static int dialogBoxOverride;

static void addErrorToQueue(char *str);

//------------------------------------------------------------
// Error callbacks
//------------------------------------------------------------
#define NEVER_SHOW_DIALOG_BOX 1
#define FORCE_SHOW_DIALOG_BOX 2

void serverErrorfSetNeverShowDialog()
{
    dialogBoxOverride = NEVER_SHOW_DIALOG_BOX;
}

void serverErrorfSetForceShowDialog()
{
    dialogBoxOverride = FORCE_SHOW_DIALOG_BOX;
}

void serverErrorfCallback(char* errMsg)
{
    extern int write_templates;

    if( isDevelopmentMode() )
        printf_stderr("%s\n", errMsg);

    LOG( LOG_ERROR, LOG_LEVEL_IMPORTANT, LOG_LOCAL, "%s", errMsg);

    // Put up a blocking dialog box if this is a local mapserver (not a spawned mapserver)
    if ((dialogBoxOverride == FORCE_SHOW_DIALOG_BOX
            // These items are overridden by FORCE_SHOW_DIALOG_BOX
            || (dialogBoxOverride != NEVER_SHOW_DIALOG_BOX && db_state.local_server && !server_state.tsr))
        // These items are not overridden by FORCE_SHOW_DIALOG_BOX
        && ErrorfCount() < 5 && !server_state.create_bins && !write_templates)
    {
        errorDialog(compatibleGetConsoleWindow(), errMsg, 0, NULL, errorWasForceShown());
    }
    else
    {
        addErrorToQueue(errMsg);
    }

    // Rather than have Errorf silently send log messages to logserver, I'd rather make that call more explicit
    //dbLogBug("\n(Server Error Msg)\nServer Ver:%s\n%s\n@@END\n\n\n\n\n\n\n\n\n", getExecutablePatchVersion("CoH Server"), errMsg);
}

//------------------------------------------------------------
// Error queuing
//------------------------------------------------------------
static int error_queue_count,error_queue_max;
static char *error_queue;

static void addErrorToQueue(char *str)
{
    char    *s;

    s = dynArrayAdd(&error_queue,1,&error_queue_count,&error_queue_max,(int)strlen(str)+1);
    strcpy(s,str);
    s[strlen(s)] = 0;
}

char *errorGetQueued()
{
    char    *s;
    static    int        curr_pos;

    if (!error_queue_count)
        return 0;
    s = error_queue + curr_pos;
    curr_pos += (int)strlen(s)+1;
    if (curr_pos >= error_queue_count)
    {
        error_queue_count = 0;
        curr_pos = 0;
    }
    return s;
}
