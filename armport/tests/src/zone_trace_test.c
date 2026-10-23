/* Reproduce tex.c's include order: file.h replaces fprintf, but the zone
 * trace must still write a CRT stderr stream. No game initialization needed. */
#include <utilitieslib/stdtypes.h>
#include <utilitieslib/utils/file.h>
#include <utilitieslib/utils/armport_zone_trace.h>

int main(void)
{
    FileWrapper wrapped = {0};
    wrapped.fptr = stderr;
    wrapped.iomode = IO_CRT;
    if (_putenv("ARMPORT_STDIO_LOG=1")) return 1;
    armportZoneTrace("regression.crt", "file.h included first");
    /* The header must restore file.h's macro for its caller. */
    if (fprintf(&wrapped, "zone trace wrapper restored\n") <= 0) return 2;
    return 0;
}
