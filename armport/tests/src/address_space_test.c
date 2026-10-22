/* ArmPort: where does memory land for an ARM64 Windows program under Wine?
 * Prints the highest address seen from the CRT heap (small and large
 * blocks), HeapAlloc, VirtualAlloc, the stack and the image, as JSON.
 * Built twice: with and without IMAGE_FILE_LARGE_ADDRESS_AWARE. Without it,
 * Windows keeps a 64-bit process below 2 GB, which protects code that still
 * stores pointers in 32-bit integers. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static uintptr_t hi(uintptr_t a, uintptr_t b) { return a > b ? a : b; }

int main(void)
{
    uintptr_t small = 0, big = 0, heap = 0, virt = 0, stack = (uintptr_t)&small;
    int i;
    for (i = 0; i < 20000; i++) small = hi(small, (uintptr_t)malloc(64));
    for (i = 0; i < 64; i++) big = hi(big, (uintptr_t)malloc(16 << 20)); /* 1 GB total */
    for (i = 0; i < 1000; i++) heap = hi(heap, (uintptr_t)HeapAlloc(GetProcessHeap(), 0, 256));
    for (i = 0; i < 16; i++) virt = hi(virt, (uintptr_t)VirtualAlloc(NULL, 1 << 20, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
    {
        IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)GetModuleHandleA(NULL);
        IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)((char *)dos + dos->e_lfanew);
        int laa = !!(nt->FileHeader.Characteristics & IMAGE_FILE_LARGE_ADDRESS_AWARE);
        uintptr_t top = hi(hi(small, big), hi(hi(heap, virt), hi(stack, (uintptr_t)dos)));
        printf("{\"large_address_aware\":%d,\"malloc_small_max\":\"0x%llx\",\"malloc_16mb_max\":\"0x%llx\","
               "\"heapalloc_max\":\"0x%llx\",\"virtualalloc_max\":\"0x%llx\",\"stack\":\"0x%llx\","
               "\"image\":\"0x%llx\",\"all_below_2gb\":%s,\"all_below_4gb\":%s}\n",
               laa, (unsigned long long)small, (unsigned long long)big, (unsigned long long)heap,
               (unsigned long long)virt, (unsigned long long)stack, (unsigned long long)(uintptr_t)dos,
               top < 0x80000000ull ? "true" : "false", top < 0x100000000ull ? "true" : "false");
    }
    return 0;
}
