# Phase 3: bounded DDS decoder gate

Implemented `coh_dds_mip` and `coh_dds_rgba` for legacy 2D DXT1/3/5 DDS in `src/coh_dds.c`. These independent modules remain outside the shipping client. They produce tightly packed RGBA8 without heap allocation, global stream state, Windows APIs or NVIDIA libraries.

## Additional deconstruction

The Phase 2 binary traces identified the raw texture conversion and NVIDIA wrapper. Source-level continuation now traces the preceding `ddsLoad` in `Game/src/render/tex.c` and the consumer in `texWords.c`; these additional source findings are not newly recovered binary symbols.

| Stage | Existing behavior | Replacement contract |
|---|---|---|
| DDS load | Supports DXT1/3/5 and several uncompressed layouts | Recognize format explicitly; reject unsupported layouts rather than reinterpret them |
| Quality mip skip | Skips block-rounded payloads, halves dimensions with minimum 1 | Validate all declared levels, expose an explicitly selected level |
| Raw request | Rebuilds DDS header with reduced width/height/mip count and remaining bytes | Preserve selected mip semantics; do not treat mip count as a byte count |
| nvDXT wrapper | Global input pointer and offset protected by critical section; read callback has no length bound | Caller-owned bounded input and output; independent concurrent calls |
| Raw conversion | Swaps B/R for 32-bit results; expands 24-bit data with opaque alpha | New API emits RGBA directly; integration must skip the old swap/expansion |
| Normal upload | May use compressed S3TC directly | Keep CPU decode separate from GPU capability-dependent upload |

DDS 124-byte header plus 4-byte magic and 32-byte pixel-format metadata are decoded bytewise; no native `DDSURFACEDESC2` layout assumption. Source hashes are recorded in `evidence/phase3/source-hashes.json`.

The prototype accepts dimensions up to 16384, checks the complete declared mip chain before writing, handles zero mip count as one base level, and clamps mip dimensions to one. DXT1 three-color transparency, DXT3 explicit alpha and both DXT5 alpha interpolation modes are implemented. Cubemap/volume, DX10, uncompressed DDS and other formats return unsupported. Invalid input, inadequate output and overlapping input/output return failure without writing output. Caller owns allocation policy and must supply a disjoint output buffer.

## Qualification

- Pillow 12.3.0 independent oracle: **1,095 image/alignment checks**, **424 truncated inputs**, **9 invalid headers**, **1,095 capacity checks**, and **three selected mip levels** passed. Random corpus seed is fixed. Includes NPOT dimensions and partial blocks. These are synthetic fixtures, not game assets.
- Standalone C runner: **11,998 assertions** passed, including truncation guards and DXT alpha paths. Host ASan/UBSan passed; local LeakSanitizer remains disabled because of the environment's PID/proc visibility. Hosted CI runs default sanitizer settings.
- Existing crypto/asset oracle still passes: 34 known vectors, 2,000 randomized cipher cases and 11,184 asset truncation cases.
- Android Bionic AArch64 compilation succeeded; device execution remains unqualified. New binary receipts replace Phase 2 hashes for this code version; see `evidence/phase3/android-build.json`.

Reproduce with `tools/build.py`, `tests/test_host.py` and `tests/test_dds.py`. CI pins Pillow and builds the same test runner for Android.

## Gate status and next work

**Portable decoder experiment: passed synthetic qualification. Production replacement: pending.** Pixel rounding and channel semantics must still be compared against the original nvDXT output using a pinned real game texture corpus. The existing uncompressed formats require separate support or an explicit integration fallback. No real texture corpus, native rendering, full client APK or Thor result is claimed.

Next: extract representative real DDS inputs from the existing asset pack, preserve their source hashes, capture original Win32 decoded RGBA/mip outputs, and compare every decoded byte. After that parity gate, connect one qualified real texture to a minimal Android Surface/EGL renderer and validate context recreation and shader output. Do not wire this prototype into the shipping launcher before those checks.
