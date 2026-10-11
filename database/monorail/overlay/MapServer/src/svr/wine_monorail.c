#include "wine_monorail.h"
#include <stdio.h>
#include <string.h>

static char session[33], reply_path[MAX_PATH];
static DWORD main_thread, sequence, request_sequence, request_started, last_reply_poll;
static int initialized, pending_map, pending_target, pending_db;
static DWORD pending_auth;

int cohMonorailInit(void)
{
    DWORD n, i;
    if (initialized++) return -1;
    n = GetEnvironmentVariableA(COH_MONORAIL_SESSION_ENV, session, sizeof(session));
    if (!n && GetLastError() == ERROR_ENVVAR_NOT_FOUND) return 0;
    if (n != 32) return -1;
    for (i = 0; i < 32; ++i)
        if (!((session[i] >= '0' && session[i] <= '9') || (session[i] >= 'a' && session[i] <= 'f'))) return -1;
    n = GetEnvironmentVariableA(COH_MONORAIL_REPLY_ENV, reply_path, sizeof(reply_path));
    if (n < 4 || n >= sizeof(reply_path) || reply_path[1] != ':' || reply_path[2] != '\\') return -1;
    main_thread = GetCurrentThreadId();
    return 1;
}

int cohMonorailEnabled(void) { return main_thread != 0; }
int cohMonorailMapAllowed(int map_id) { return !cohMonorailEnabled() || map_id == 1 || map_id == 5; }

static int identity(int map, int db, DWORD auth, const char *name, const char *account)
{
    return main_thread && GetCurrentThreadId() == main_thread && sequence != 0xffffffffUL &&
        (map == 1 || map == 5 || map == 101) && db == 1 && auth && name && account &&
        !strcmp(name, "THORHERO") && !strcmp(account, "COHLOCAL");
}

static void emit(const char *kind, int map, int db, DWORD auth, int port, float x, float y, float z)
{
    FILETIME now;
    ULARGE_INTEGER ticks;
    GetSystemTimeAsFileTime(&now);
    ticks.LowPart = now.dwLowDateTime; ticks.HighPart = now.dwHighDateTime;
    printf("\nCOH_ZONING_EVENT_V1 session=%s pid=%lu tid=%lu sequence=%lu kind=%s "
        "utc_ms=%I64u map_id=%d db_id=%d auth_id=%lu name=THORHERO account=COHLOCAL "
        "peer=127.0.0.1:%d request=%lu target=%d position=<%.2f,%.2f,%.2f>\n",
        session, GetCurrentProcessId(), main_thread, ++sequence, kind,
        ticks.QuadPart / 10000 - 11644473600000ULL, map, db, auth, port,
        request_sequence, pending_target, x, y, z);
    fflush(stdout);
}

void cohZoningEvent(const char *kind, int map, int db, DWORD auth,
    const char *name, const char *account, const char *peer, int port, float x, float y, float z)
{
    if (!identity(map, db, auth, name, account)) return;
    if (!strcmp(kind, "ready")) {
        if (!peer || strcmp(peer, "127.0.0.1") || port < 1 || port > 65535) return;
    } else if (strcmp(kind, "position") || port) return;
    emit(kind, map, db, auth, port, x, y, z);
}

int cohMonorailRequest(int map, int destination, int db, DWORD auth, const char *name, const char *account)
{
    if (!identity(map, db, auth, name, account) || request_sequence ||
        !((map == 1 && destination == 5) || (map == 5 && destination == 1))) return 0;
    /* The next emitted sequence uniquely binds this station choice. */
    request_sequence = sequence + 1;
    request_started = GetTickCount();
    last_reply_poll = request_started - 250UL;
    pending_map = map; pending_target = destination; pending_db = db; pending_auth = auth;
    emit("station_request", map, db, auth, 0, 0, 0, 0);
    return 1;
}

void cohMonorailCancel(void) { request_sequence = 0; pending_map = pending_target = pending_db = 0; pending_auth = 0; }

int cohMonorailPoll(int map, int db, DWORD auth)
{
    HANDLE file;
    DWORD size, got, now;
    BY_HANDLE_FILE_INFORMATION info;
    char actual[256], expected[256];
    int n;
    if (!request_sequence) return 0;
    if (GetCurrentThreadId() != main_thread || map != pending_map || db != pending_db || auth != pending_auth ||
        (DWORD)(GetTickCount() - request_started) > 600000UL) { cohMonorailCancel(); return -1; }
    now = GetTickCount();
    if ((DWORD)(now - last_reply_poll) < 250UL) return 0;
    last_reply_poll = now;
    file = CreateFileA(reply_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!GetFileInformationByHandle(file, &info) ||
        (info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY))) {
        CloseHandle(file); return 0;
    }
    size = GetFileSize(file, NULL);
    if (size >= sizeof(actual) || !ReadFile(file, actual, sizeof(actual)-1, &got, NULL)) { CloseHandle(file); return 0; }
    CloseHandle(file);
    if (got != size) return 0;
    actual[got] = 0;
    n = _snprintf(expected, sizeof(expected), "COH_MONORAIL_REPLY_V1 session=%s pid=%lu request=%lu target=%d ready=1\n",
        session, GetCurrentProcessId(), request_sequence, pending_target);
    if (n < 0 || got != (DWORD)n || memcmp(actual, expected, got)) return 0;
    emit("station_departure", map, db, auth, 0, 0, 0, 0);
    cohMonorailCancel();
    return 1;
}
