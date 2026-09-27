#include <windows.h>
#include <stdio.h>
typedef unsigned long (__cdecl *probe_fn)(void);
int main(void) {
    HMODULE fixture, odbc;
    probe_fn check;
    if (sizeof(void *) != 4) return 2;
    fixture = LoadLibraryA("probe.dll");
    if (!fixture) { fprintf(stderr, "FAIL probe DLL load: %lu\n", GetLastError()); return 3; }
    check = (probe_fn)GetProcAddress(fixture, "coh_probe_value");
    if (!check || check() != 0x434f4832UL) { FreeLibrary(fixture); return 4; }
    odbc = LoadLibraryA("odbc32.dll");
    if (!odbc || !GetProcAddress(odbc, "SQLDriverConnectA")) { FreeLibrary(fixture); return 5; }
    FreeLibrary(odbc);
    FreeLibrary(fixture);
    puts("COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified");
    return 0;
}
