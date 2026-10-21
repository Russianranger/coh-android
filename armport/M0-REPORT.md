# M0 survey report

Date: 2026-10-21. Branch `armport/m0-survey`. All numbers come from
`armport/survey/results/*.json` and CI run 39657354638 (shaders).

## Decision: build the client as an ARM64 Windows program

The app's runtime is Wine 10 built natively for ARM64
(`--enable-archs=aarch64,i386`, llvm-mingw; see `android/runtime-lock.json`
and `Russianranger/lsb-android` `native/fex/Dockerfile`). FEX is used only to
run 32-bit x86 Windows code. An ARM64 Windows build of the original client
therefore runs in that same Wine with no x86 emulation.

Why this route rather than a Linux or Bionic build:

- The client's own Windows code (windowing, DirectInput, DirectSound, winmm,
  WGL/OpenGL, sockets, threads) stays unchanged; Wine provides it on ARM64.
- ARM64 Windows is LLP64: `long` stays 32-bit, so the Windows-vs-Linux `long`
  size problem does not arise. Pointers are still 64-bit (see below).
- The display, input and audio path the Wine client already uses on the Thor
  (Wine → Mesa Zink/Turnip → Xtigervnc → the app's VNC view) is reused.
- A Linux aarch64 build fails almost everywhere: 6 of 558 Game files and 5 of
  165 UtilitiesLib files compile, the rest stop on MSVC CRT headers
  (`crtdbg.h`, `excpt.h`, `io.h`). That route needs a Windows layer under
  nearly every file.

A native Android library with a direct Surface remains a possible later step
for speed and other devices; it is not needed to reach a playable port.

## Compile survey (syntax-only, aarch64-w64-mingw32, clang 18.1.3)

| Run | UtilitiesLib clean | Game clean | Errors (U / G) |
|---|---|---|---|
| Baseline, unmodified | 157 / 165 | 295 / 558 | 204 / 6,955 |
| Compiler flags only (MSVC-accepted errors downgraded) | 157 / 165 | 329 / 558 | 200 / 6,781 |
| Experiment: flags + 3 one-line fixes + SSE shims | 158 / 165 | 502 / 558 | 25 / 496 |

Most of the baseline error count is cascades from a few headers. The three
experiment fixes (`armport/survey/experiment/apply.sh`) are:

1. `renderUtil.h`: `rdrExamineDriversEarly(oivd)` typo for `(void)` (82 files).
2. `PowerMode` declared as an enum in `powers.h` and an `int` in
   `character_base.h` (98 files).
3. `NOVODEX 0` to drop the x86-only PhysX integration.

What remains after the experiment: 56 Game files with 16 distinct first-error
causes, and 7 UtilitiesLib files with 4 causes. The largest are `#pragma
section` conflicts (20 files), address-of-rvalue (16), and an `fxgeo.h` type
(6). UtilitiesLib needs the `cryptopp` and `crashrpt` include paths, NEON
replacements for `_mm_pause` and `cpuid`, and the x86 debug registers in
`Breakpoint.c`.

## 64-bit

- 460 pointer-to-int truncation warnings in 98 files (458 in 96 Game files,
  2 in UtilitiesLib), mostly UI callback data and scripting values stored in
  `int`. More will appear as the remaining files compile.
- `.bin` data files: the parse-table checksum ignores struct offsets and sizes
  (`UpdateCRCFromParseInfo`: "make ourselves insensitive to 64-bit"), and
  reading is field by field, so shipped bins should load. Raw fixed-size
  fields are the exception to check in M1.
- UtilitiesLib already has `_WIN64` / `_M_X64` branches (shared memory, stash
  tables, memory tracking).
- Plan: allocate the engine's heap below 4 GB as a safety net while the casts
  are fixed properly.

## x86-specific code

- SSE intrinsics: 68 uses in 9 files. The sse2neon shims cleared all but 8
  UtilitiesLib and 30 Game errors in the experiment.
- Inline assembly: 39 lines in 12 files (prefetch, timing, cpu count, texWords).

## Shaders

The original `cgc.exe` 2.2.0017 compiled 29 of 30 client shader files to ARB
assembly (`arbfp1`/`arbvp1`). The failure, `debugfp.cg`, is a debug shader
whose include `utilsfp.cgh` is not in the game data. The client also has a
prebaked-shader cache (`rt_shaderMgr.c`: `storePreBakedShader` /
`getPreBakedShaderText`) keyed by source path, content MD5 and build
options, so per-variant ARB text can be cached instead of calling Cg at run
time.

## Dependencies

- Build for ARM64 from source: zlib, Crypto++, SparseHash, FreeType, GLEW,
  libjpeg-turbo, jpgd, Ogg/Vorbis, CubeMapGen, nvparse.
- Turn off or stub: PhysX, AlienFX, NvCpl, NvDxt, crash reporting (or build
  `libs/crashrpt` for ARM64).
- Replace: Cg runtime, with precompiled or cached ARB programs.

## Testing without the Thor

The repo already runs the real server on `ubuntu-24.04-arm` runners with the
same Wine/FEX runtime. M1–M4 can run the ARM64 client there under that Wine,
with a virtual X server and software GL.
