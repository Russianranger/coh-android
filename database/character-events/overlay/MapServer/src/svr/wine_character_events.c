#include "wine_character_events.h"
#include <stdio.h>
#include <string.h>

static char character_session[33];
static DWORD character_event_sequence;
static DWORD character_event_thread;
static int character_events_initialized;

int cohCharacterEventsInit(void)
{
    DWORD length;
    unsigned int i;
    if (character_events_initialized) {
        SetLastError(ERROR_ALREADY_EXISTS);
        return -1;
    }
    character_events_initialized = 1;
    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_CHARACTER_EVENTS_ENVIRONMENT,
                                     character_session, sizeof(character_session));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    if (length != 32) {
        character_session[0] = 0;
        SetLastError(ERROR_INVALID_PARAMETER);
        return -1;
    }
    for (i = 0; i < 32; ++i) {
        if (!((character_session[i] >= '0' && character_session[i] <= '9') ||
              (character_session[i] >= 'a' && character_session[i] <= 'f'))) {
            character_session[0] = 0;
            SetLastError(ERROR_INVALID_PARAMETER);
            return -1;
        }
    }
    character_event_thread = GetCurrentThreadId();
    return 1;
}

static void characterEvent(const char *kind, int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, int port, float x, float y, float z)
{
    FILETIME now;
    ULARGE_INTEGER ticks;
    unsigned __int64 utc_ms;
    /* Only the requested owned test character on Atlas is observable. The
     * startup token and main thread are checked once; disabled builds do no I/O.
     * Never wrap a sequence and accidentally make old events appear fresh. */
    if (!character_session[0] || GetCurrentThreadId() != character_event_thread ||
        character_event_sequence == 0xffffffffUL || map_id != 1 || db_id <= 0 ||
        auth_id == 0 || !name || !account || strcmp(name, "THORHERO") ||
        strcmp(account, "COHLOCAL"))
        return;
    GetSystemTimeAsFileTime(&now);
    ticks.LowPart = now.dwLowDateTime;
    ticks.HighPart = now.dwHighDateTime;
    utc_ms = ticks.QuadPart / 10000 - 11644473600000ULL;
    ++character_event_sequence;
    /* This is intentionally separate from sorted LOG_ENT. One short line per
     * successful resume and per stock 30-second physics observation is flushed
     * immediately through the existing owned process console pipe. */
    printf("\nCOH_CHARACTER_EVENT_V1 session=%s pid=%lu tid=%lu sequence=%lu kind=%s "
           "utc_ms=%I64u map_id=%d db_id=%d auth_id=%lu name=THORHERO account=COHLOCAL "
           "peer=127.0.0.1:%d position=<%.2f,%.2f,%.2f>\n",
           character_session, GetCurrentProcessId(), character_event_thread,
           character_event_sequence, kind, utc_ms, map_id, db_id, auth_id, port, x, y, z);
    fflush(stdout);
}

void cohCharacterEventReady(int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, const char *peer, int port)
{
    if (!peer || strcmp(peer, "127.0.0.1") || port < 1 || port > 65535)
        return;
    characterEvent("ready", map_id, db_id, auth_id, name, account, port, 0, 0, 0);
}

void cohCharacterEventPosition(int map_id, int db_id, DWORD auth_id,
    const char *name, const char *account, float x, float y, float z)
{
    characterEvent("position", map_id, db_id, auth_id, name, account, 0, x, y, z);
}
