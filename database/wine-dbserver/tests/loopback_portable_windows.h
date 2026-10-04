/* Linux-only test shim. The contract also builds against actual Win32/Winsock
 * with MSVC; this shim does not claim to qualify those APIs on Windows. */
#ifndef COH_LOOPBACK_TEST_WINDOWS_H
#define COH_LOOPBACK_TEST_WINDOWS_H
#include <stdlib.h>
#include <string.h>
typedef unsigned long DWORD;
typedef long LONG;
#define ERROR_SUCCESS 0UL
#define ERROR_ENVVAR_NOT_FOUND 203UL
#define ERROR_INVALID_PARAMETER 87UL
#define ERROR_INVALID_STATE 5023UL
extern DWORD coh_test_error;
static void SetLastError(DWORD error) { coh_test_error = error; }
static DWORD GetLastError(void) { return coh_test_error; }
static DWORD GetEnvironmentVariableA(const char *name, char *buffer, DWORD capacity)
{
    const char *value = getenv(name);
    size_t length;
    if (!value) { SetLastError(ERROR_ENVVAR_NOT_FOUND); return 0; }
    length = strlen(value);
    if (length >= capacity) return (DWORD)length + 1;
    memcpy(buffer, value, length + 1);
    return (DWORD)length;
}
#define InterlockedCompareExchange(target, value, expected) __sync_val_compare_and_swap(target, expected, value)
#endif
