# Phase 2: portable core and binary replacement seams

The isolated `native-android` branch now builds a small Android Bionic ARM64 core. It is not a native City of Heroes application. Shipping launcher and Game targets are unchanged.

## Reproducible qualification

Code qualification commit: `b800333ac01a9916650b23fba5c94c7cf73608f9`.
[Successful CI run](https://github.com/Russianranger/coh-android/actions/runs/38423690560) executes source-derivation checks, host tests, independent OpenSSL parity, sanitizers and Android cross-compilation. See `tools/build.py`, `tests/test_host.py` and the dedicated workflow.

| Slice | Evidence | Limit |
|---|---|---|
| Fixed-width Blowfish | 34 published vectors; 272 unaligned cases; 2,000 randomized cases / 32,716 blocks | No live server handshake or complete wire-frame qualification |
| Animation and geometry metadata | 11,184 truncations, 48 mutations, six geometry versions; actual pointers above 4 GiB | Synthetic fixtures; no real asset corpus or full decoding |
| Standalone core | 868 C assertions and ASan/UBSan | Local leak checking is blocked by PID/proc visibility; hosted standard sanitizer run passed |
| Android ARM64 | ELF64 AArch64, Bionic linker, system libc/libdl/libm dependencies | Cross-compiled; not executed on Thor |

The shared-library SHA256 is `bff7b4a0c860b190b58408ce1b3b6748a7d82111787cd82b0201fcef5679654f`.
The standalone Android test executable SHA256 is `6675e6b338c4ab58bb9c18475a064bfe734ba8f5d81ea0d01c08289817be851e`.
Local and hosted build receipts report matching Android binary hashes.

## Four newly deconstructed functions

Target: CityOfHeroes.exe, SHA256 `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b`.
REA's PE resource inspection succeeded. The native REA bridge remains blocked by its process-identity validation in this environment; its safeguards were not changed. A separate supervised, read-only Ghidra pass reused the Phase 1 partial project and decompiled these four functions. It did not execute the client or perform whole-program analysis.

| Address | Source correspondence | Native requirement |
|---|---|---|
| 0x0062e640 | `uncompressRawTexInfo`, texWords.c | Preserve DDS mip selection, row pitch, dimensions, B/R conversion and opaque-alpha expansion |
| 0x005ff490 | `nvDXTdecompressC`, dxtlibwrapper.cpp | Replace NVIDIA decoder and global stream/critical-section coupling with a bounded decoder; qualify channel order and malformed input |
| 0x008f6790 | `preloadDLLs`, sysutil.c | PhysX DLLs are eagerly loaded; runtime physics toggles do not remove the dependency. Establish an explicit native compile-time dependency boundary |
| 0x0067bc40 | `wglMakeCurrentSafeDirect`, rt_win_init.c | Replace WGL context/retry lifecycle with Android Surface/EGL handling and equivalent context-change state invalidation |

Names above are manually corroborated source correspondences, not recovered PDB symbols. Ghidra inferred prototypes are not authoritative. Assembly and source must determine argument types. `evidence/ghidra-phase2-seams.json` retains bounded instructions and pseudocode; `tools/CoHPhase2Seams.java` reproduces the focused pass against the matching saved project.

## Next implementation gates

1. Execute the standalone probe on Thor: require all assertions, 8-byte pointers/long and Android Bionic platform. This does not qualify gameplay.
2. Compare real animation/geometry assets with original Win32 outputs. Implement rotation expansion, delta data, decompression and collision only with bounded input and golden parity. Reject unsupported flags explicitly.
3. Replace the traced DDS decoder; compare dimensions, mips, row pitch and RGBA bytes across real texture fixtures. Audit remaining texture-format paths.
4. Build a minimal Android Surface/EGL renderer with one real material and skinned fixture. Translate the recovered Cg contract and validate image parity before importing the scene renderer.
5. Qualify complete protocol frames and an unchanged-server handshake, then native input/audio, physics boundary and ARM memory-ordering requirements.

A full client APK, world entry, FPS gains and startup/zone improvements remain unqualified. These experiments provide testable building blocks and concrete replacement requirements, not completion of those milestones.
