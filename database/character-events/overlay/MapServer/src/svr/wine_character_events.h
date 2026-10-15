#ifndef COH_WINE_CHARACTER_EVENTS_H
#define COH_WINE_CHARACTER_EVENTS_H

#include <windows.h>

#define COH_CHARACTER_EVENTS_ENVIRONMENT "COH_WINE_CHARACTER_EVENTS_SESSION"
#define COH_CHARACTER_EVENTS_FORMAT 1

/* Opt-in, read-only events from the already accepted native call sites.
 * No event changes entity state, client packets, physics or logger policy. */
int cohCharacterEventsInit(void);
void cohCharacterEventReady(int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, const char *peer, int port);
void cohCharacterEventPosition(int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, float x, float y, float z);

#endif
