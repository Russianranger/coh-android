/* Reproduce tex.c's include order: file.h replaces fprintf, but the zone
 * trace must still write a CRT stderr stream. No game initialization needed. */
#include <utilitieslib/stdtypes.h>
#include <utilitieslib/utils/file.h>
#include <utilitieslib/utils/armport_zone_trace.h>
/* This standalone logger test uses only Win32 thread state, not game TLS. */
#undef CreateThread

static DWORD WINAPI traceWriter(void *unused)
{
    char message[8192];
    int i;
    memset(message, 'x', sizeof(message));
    message[1] = '\n'; message[2] = '"'; message[3] = '\\'; message[4] = (char)255;
    message[sizeof(message) - 1] = 0;
    for (i = 0; i < 16; ++i) armportZoneTrace("client.error", message);
    return 0;
}

int main(void)
{
    FileWrapper wrapped = {0};
    HANDLE threads[4];
    int i;
    wrapped.fptr = stderr;
    wrapped.iomode = IO_CRT;
    if (_putenv("ARMPORT_STDIO_LOG=1")) return 1;
    DeleteFileA("zone-trace-test.jsonl");
    if (_putenv("ARMPORT_ZONE_LOG=zone-trace-test.jsonl")) return 3;
    armportZoneTrace("regression.crt", "file.h included first");
    /* The header must restore file.h's macro for its caller. */
    if (fprintf(&wrapped, "zone trace wrapper restored\n") <= 0) return 2;
    for (i = 0; i < 4; ++i)
    {
        threads[i] = CreateThread(NULL, 0, traceWriter, NULL, 0, NULL);
        if (!threads[i]) return 4;
    }
    if (WaitForMultipleObjects(4, threads, TRUE, 30000) != WAIT_OBJECT_0) return 5;
    for (i = 0; i < 4; ++i) CloseHandle(threads[i]);
    if (getenv("ARMPORT_WINE_BOUNDARY_LOG"))
    {
        if (fprintf(&wrapped, "boundary control before\n") <= 0) return 6;
        fflush(&wrapped);
        armportZoneTrace("map.start", "boundary control");
        if (fprintf(&wrapped, "boundary control after\n") <= 0) return 7;
        fflush(&wrapped);
    }
    return 0;
}
