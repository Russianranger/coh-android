# Native Android experiments - Phase 2

Isolated C modules for Android Bionic `arm64-v8a`, based on the accepted client
source. These targets are independent of the shipping Game and launcher targets.

Implemented test slices:

- Fixed-width Blowfish with checked key/block lengths and unaligned-safe,
  explicitly little-endian game packet words.
- Fixed 596-byte animation headers and 20-byte bone records, offset/span
  validation and native-width borrowed views.
- Fixed 12-byte geometry pack descriptors and v3-v8 model-record metadata.

This is not a native game or a complete animation/geometry loader. Rotation
expansion, geometry delta/collision decoding, real-asset corpus parity, live
protocol exchange, Android Surface rendering and Thor execution are separate
gates. Results will distinguish host execution from Android cross-compilation.

The upstream sources are immutable. `tools/generate_crypto.py --check` verifies
the crypto derivative against the original source hash and preserves its author
notice. Generated buffers and test data do not access personal profiles.

Phase 3 adds a bounded legacy DXT1/3/5 DDS-to-RGBA decoder. See [PHASE3.md](PHASE3.md) for source contracts, test results and remaining real-asset parity gate.

[PHASE4.md](PHASE4.md) qualifies the selected real DXT1/DXT5 corpus against the original Win32 NVIDIA decoder and explains the separate legacy CPU API.

[PHASE5.md](PHASE5.md) adds an installable ARM64 Surface/EGL texture probe. Android13 emulator and physical AYN Thor/Adreno740 pixel/lifecycle checks passed. The [Thor acceptance receipt](evidence/phase5/thor-qualification.json) records 12 successful runs, 24 EGL context lifetimes and zero pixel mismatches or GL/EGL errors. The next gate is a real material and skinned fixture with shader, alpha/fog and offscreen-pass validation.

[PHASE6.md](PHASE6.md) reconstructs a real three-bone sleeve mesh and its default dual-color material in a separate native probe. Host source-function and malformed-input checks passed, and Android13 emulator execution qualified the mesh, pose, material and Surface lifecycle checks. Physical AYN Thor/Adreno 740 acceptance also passed: eight runs, sixteen EGL lifetimes, four Surface generations and zero comparison mismatches. The [Thor material receipt](evidence/phase6/thor-qualification.json) records the audited report. Phase 7 proceeds to original rig, socket and animation playback.

[PHASE7.md](PHASE7.md) adds original compressed huge run keys, full hierarchy, inverse-bind and sleeve-socket reconstruction in a separate native animation probe. Six independent reference checkpoints precede a bounded runtime animation preview and retained material/lifecycle checks. Host original-function and malformed-input tests passed. Android13 emulator and physical AYN Thor/Adreno 740 execution each passed six runs, twelve EGL lifetimes, 540 runtime animation frames and all CPU/GPU/material/lifecycle comparisons. The [hosted receipt](evidence/phase7/qualification.json) and [Thor animation receipt](evidence/phase7/thor-qualification.json) preserve the separate evidence. The next gate assembles and qualifies the complete character.
