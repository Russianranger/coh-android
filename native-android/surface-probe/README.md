# CoH native Surface probe

Standalone package `org.coh.nativeprobe`, version 0.1.0-phase5, Android 8/API26 or newer and GLES3. The device APK contains only ARM64 native code. It includes one hash-qualified real DDS and RGBA golden; no external asset import is required. It does not open a game, server or launcher profile.

Each native call verifies Android CPU decoding against the original Windows NVIDIA output, compares every RGBA pixel of a GLES3 texture-sized FBO, checks 49 RGB samples from the actual EGL window and presents it. It destroys all graphics resources and repeats with a fresh context. The visible texture is opaque RGB; FBO tests retain the original alpha. Android compositor alpha fidelity is separate.

The app automatically checks its first surface. For Thor acceptance:

1. Install the ARM64 APK and open **COH Native Surface Probe**. Confirm that a clothing texture appears and the native check passes.
2. Tap **Resize surface**; wait for the check to finish.
3. Tap **Recreate surface**; wait for **SURFACE GATE PASSED**.
4. Press Home, return to the app and wait for the current surface check to pass again.
5. Tap **Export report**, save the JSON in Downloads and return it for review.

The report records fixture/golden hashes, actual surface dimensions and generations, GL renderer/vendor/version, per-cycle parity/errors and resource cleanup. Obsolete/background requests cannot qualify. Any active-session failure remains recorded; export it before starting a fresh session to retry. Export snapshots the foreground report before opening the document picker.

The initial test APK uses an isolated CI debug key. If a later build cannot update it, uninstall only this probe after exporting its report; the production CoH application is separate.

## Reproduce

On a Linux build host with JDK17 and the Android SDK:

```bash
python3 native-android/tools/corpus/acquire.py --output native-android/results/real-corpus
python3 native-android/tools/prepare_surface_fixture.py --corpus native-android/results/real-corpus --output native-android/surface-probe/app/src/main/assets
python3 native-android/surface-probe/gradle.py :app:assembleDebug :app:lintDebug
```

The bootstrap verifies Gradle8.9; AGP8.7.3, SDK35, NDK28.2.13676358 and CMake3.22.1 are pinned. Generated fixture assets and build outputs are ignored by git. The dedicated workflow makes a second x86_64 APK for an Android13 emulator and tests real rendering, actual Surface resizing/recreation and foreground return. Emulator results do not qualify the Thor's Adreno driver.
