# M1 report: libraries on ARM64

Date: 2026-10-21. Branch `armport/m1-libs`. Evidence: CI run
[39662794538](https://github.com/Russianranger/coh-android/actions/runs/39662794538)
(`ArmPort build`, `ubuntu-24.04-arm`).

## Exit test: passed

Built for ARM64 Windows with llvm-mingw 20250910 (the release the app's Wine
runtime is built with) and run under that runtime's Wine 10
(`android/runtime-lock.json`, sha256-checked):

```json
{"pointer_bytes":8,"long_bytes":4,
 "text":{"parsed":1,"entries":28,"first":"Pants","last":"Tail","pass":true},
 "table_crc":"cf27aba3","bin_header_accepted":true,
 "bin":{"parsed":1,"entries":28,"first":"Pants","last":"Tail","pass":true},
 "pass":true}
```

- The original textparser and `ParseBodyPartBegin` table read
  `defs/ui/bodyparts.bp` to 28 entries.
- The 64-bit build computes the same parse-table checksum (`cf27aba3`) as the
  32-bit build wrote into the shipped client `BodyParts.bin`, and loads that
  file to 28 entries that match the text result record by record in every
  parsed field (name, bone count, influence cost, geometry, texture and base
  names, dont_clear). This shows the shipped `BodyParts.bin` loads correctly
  in the 64-bit client; other `.bin` files and cache formats are not tested
  yet.
- Upstream's mandatory precise floating-point check
  (`cox_precise_floating_point_test`) built and ran under the same Wine.

## What it took

Built: UtilitiesLib (all 165 files), zlib, Crypto++, SparseHash, CrashRpt,
the test program and the floating-point check. Patches
(`armport/patches/series`, applied to a copy by `armport/scripts/prepare.py`):

| Patch | Change |
|---|---|
| 0001 | CMake ARM64 Windows path: 64-bit allowed only for ARM64; MSVC-only options guarded; `-fms-extensions`, `-fno-strict-aliasing`, `-ffp-contract=off` (no fused multiply-add, to keep x86-identical floating point); MSVC-accepted clang errors downgraded; `#pragma comment(lib)` ignored (CMake links the same libraries) |
| 0002 | `ring.hpp`: ARM64 `yield` instead of x86 `_mm_pause` in spin waits |
| 0003 | `Breakpoint.c`: x86 debug-register data breakpoints are no-ops on ARM64 (debug aid only) |
| 0004 | `cpu_count.c`: no CPUID on ARM64; Hyper-Threading reported off, CPU count from the affinity mask |
| 0005 | sse2neon for x86 SSE headers; hook for `armport/tests` |
| 0006 | `SHARED_MEMORY` data in ordinary sections (the existing `DISABLE_SHARED_MEMORY_SEGMENT` switch) |
| 0007 | Crypto++ built as portable C++ (`CRYPTOPP_DISABLE_ASM`); `Windows.h` case shim |
| 0008 | ARM generic timer instead of `__rdtsc` for performance counters and the profiler; the game clock already uses `QueryPerformanceCounter` |

Nothing in `upstream/` is modified. Each patch is reviewable on its own;
`armport/scripts/patchwork.py` edits the series as git commits.

## Not covered yet (M2)

- Game and the Common files it compiles (16 first-error causes after the M0
  experiment fixes), linking `CityOfHeroes.exe`.
- The Cg runtime calls (81 functions, 231 call sites; see `M0-REPORT.md`).
- Pointer-to-int truncation fixes (460 warnings) and the below-4 GB heap
  safety net.
- GLEW, FreeType, JPEG, Ogg/Vorbis, CubeMapGen, nvparse builds.
