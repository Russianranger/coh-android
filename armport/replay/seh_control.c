/* Real handled-exception control for the pinned Wine +seh host rejection. */
#include <windows.h>
#include <stdio.h>
static volatile LONG handled;
static LONG CALLBACK handler(EXCEPTION_POINTERS *exception)
{
    if (exception->ExceptionRecord->ExceptionCode != 0xe0424242)
        return EXCEPTION_CONTINUE_SEARCH;
    handled++;
    return EXCEPTION_CONTINUE_EXECUTION;
}
int main(void)
{
    PVOID registration = AddVectoredExceptionHandler(1, handler);
    if (!registration) return 2;
    RaiseException(0xe0424242, 0, 0, NULL);
    RemoveVectoredExceptionHandler(registration);
    if (handled != 1) return 3;
    puts("ARMPORT_HANDLED_SEH_CONTROL passed");
    return 0;
}
