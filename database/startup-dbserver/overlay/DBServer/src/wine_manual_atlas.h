#ifndef COH_WINE_MANUAL_ATLAS_H
#define COH_WINE_MANUAL_ATLAS_H

#include <windows.h>

#define COH_DB_MANUAL_ATLAS_ENVIRONMENT "COH_WINE_DB_MANUAL_ATLAS"
#define COH_DB_MANUAL_ATLAS_ACK "COH_WINE_DB_MANUAL_ATLAS=1 active: unused Launcher connection wait skipped; manual Atlas launch; ordinary DbServer readiness required"

/* Absent=0; an exact, safely scoped request=1; a malformed or unsafe request=-1.
 * Call after launcherCommInit, before the ordinary connection wait. This never
 * bypasses listeners, map-list initialization, SQL draining or the main loop. */
int cohDbManualAtlasLauncherWait(int start_static, int fake_auth, int auth_server_present,
    int queue_server, int use_logserver, int launcher_count, int launchers_connecting);

#endif
