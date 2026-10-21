/* ArmPort: MSVC intrinsics the client calls that clang does not provide on
 * ARM64 Windows. Declarations come from mingw-w64's intrin.h.
 *
 * __cpuid: x86 CPUID does not exist. Report all-zero feature words, so the
 * engine's SSE detection (ssemath.c) reports no SSE and uses its scalar
 * paths; renderUtil.c records zeros in its informational system specs.
 * __nop:   a real ARM64 NOP.
 */
void __cpuid(int info[4], int level)
{
	(void)level;
	info[0] = info[1] = info[2] = info[3] = 0;
}

void __nop(void)
{
	__asm__ __volatile__("nop");
}
