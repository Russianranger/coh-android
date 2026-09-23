#ifndef _UISCRIPT_H
#define    _UISCRIPT_H

#include "UI/uiInclude.h"
#include <utilitieslib/stdtypes.h>
#include "storyarc/ScriptUIEnum.h"
#include "UI/uiCompass.h" // For ScriptUIClientWidget

extern int scriptUIIsDetached;

int scriptUIWindow();
void detachScriptUIWindow(int detach);
void scriptUIReceiveDetach(Packet *pak);

#endif