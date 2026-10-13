# Phase 5: native Android Surface/EGL proof

The standalone **COH Native Surface Probe 0.1.0-phase5** APK is built for Android ARM64. Its separate package is `org.coh.nativeprobe`; it does not open the shipping launcher, game or server profiles. The fixture and its original Windows RGBA golden are bundled, so no user asset import is needed.

[Qualified build and Android emulator run](https://github.com/Russianranger/coh-android/actions/runs/38450326655), code `f5f4127693d4cab8d82b9c30c6f8b6c031639f2c`, passed. The ARM64 APK is 403,518 bytes, SHA256 `0c1f1a4addcdcfb9275665411319c5270441973651ea23ae29df89eee055fe51`. Signature verification, package metadata, ARM64-only ELF64 AArch64 native library and bundled golden hash were checked. The test APK uses an isolated debug signing key.

## Observed Android execution

Android13/API33 x86_64 emulator, pinned stable emulator37.2.12/build16428233 with SwiftShader:

- Four successful native checks, three actual Surface generations, and two actual Surface sizes: 1038x764 and 778x764.
- Eight complete EGL context lifetimes with all app GPU objects released; each fresh context rebuilt its texture, FBO and shaders.
- **1,048,576 FBO pixel comparisons**, zero mismatches; **392 window RGB samples**, zero mismatches.
- Actual resize, Surface destruction/recreation and Home/foreground return passed.
- Packaged DDS SHA and original Win32 golden SHA matched; Android CPU decoding matched every golden byte before drawing.
- The final screenshot was visually inspected: the real texture remains displayed after native cleanup, with the qualification status passed.

These are repeated checks of one real texture, not one million distinct source texels or a game-scene benchmark. The GL renderer reports Android Emulator OpenGL ES Translator (Google SwiftShader). **Thor/Adreno execution remains pending.**

The real fixture is `chest_5c_night_chest_01.texture`, decoded 256x512 RGBA. DDS SHA256 `378dbd7be97eed26a0ad3e454efadaab6a52f4f9c01579d94dc20934d8ec44b7`; original normalized Win32 RGBA SHA256 `e8d9492e39d13211aa5196c834725feb7f0113739daa3d7d7f1195b1478ddaef`. Fixture preparation verifies the decoded output against the Phase4 original-SDK record before packaging. The APK runtime rechecks both asset hashes and CPU/golden parity.

## Reconstruction requirements made concrete

`ANativeWindow` and EGL/GLES3 replace the traced WGL boundary in this proof. Each bounded JNI call owns its input copies and native window reference, creates and uses a context on one worker thread, presents an aspect-fitted textured triangle pair, releases resources and repeats with a fresh context. Framebuffer checks cover every RGBA texel; window checks cover RGB samples before successful `eglSwapBuffers`. The visible window forces opaque alpha, separating presentation from Android compositor alpha semantics.

Java Surface callbacks schedule serial native requests. Results from an obsolete size/generation or a paused/destroyed activity cannot qualify the current surface. Active-session failures remain sticky even when old history is evicted. The report saves current and historical events; export captures the foreground result before the document picker changes lifecycle state.

This qualifies controlled context recreation and normal Surface lifecycle handling. It does not exercise an unexpected hardware GPU reset, full-game state restoration, frame pacing, all sampler/material/Cg variants, skinned geometry, fog, audio, input or networking. GLES3 identity texture shaders replace no complete Cg program family yet. Full RGBA FBO parity is separate from compositor alpha, filtering/mipmap and screen color-management fidelity.

## Thor acceptance

Install the ARM64 APK and open **COH Native Surface Probe**. The first texture check runs automatically. Confirm the clothing texture appears, use **Resize surface**, then **Recreate surface**, and wait for **SURFACE GATE PASSED**. Press Home, return and wait for the current surface to pass again. Use **Export report**, save the JSON in Downloads and return it for review.

Accept only a report from the Thor showing the expected fixture hashes, actual ARM64/device identity and Adreno renderer, CPU/golden and GPU parity, successful swaps, at least two actual sizes/generations, clean context recreation and foreground recovery. Export any failure before restarting the probe to retry. See `surface-probe/README.md` for reproduction and the separate debug-package update behavior.

Next after device acceptance: a real material and skinned fixture with captured shader parameter/bone contracts, plus alpha/fog/offscreen-pass validation. No playable native client, world entry, FPS or startup/zone improvement is claimed by this texture proof.
