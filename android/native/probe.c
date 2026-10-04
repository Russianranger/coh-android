#include <windows.h>
__declspec(dllexport) unsigned long __cdecl coh_probe_value(void) { return 0x434f4832UL; }
BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)instance; (void)reason; (void)reserved;
    return TRUE;
}
