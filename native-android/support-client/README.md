# Offline native support client

This separate test package exercises new opt-in support libraries without editing
the accepted Session Client, production launcher or gates 25–27. Package identity
is `org.coh.nativesupport`. The retained qualified artifact is `0.1.0-support-batch`;
the next integrated build is `0.2.0-gameplay` (manifest code `200`). It coexists with the
physically accepted 0.3.0 client. It does not require a server.

The coordinator-owned `offline_scene.c` is a test-harness derivative of the
accepted offline scene. The original renderer/JNI/Java files remain unchanged.
It retains the original Wretch/Huge actor and bounded Atlas asset selection,
adds static BVH-backed WALK, exact CPU skin-result caching, source-font GLES HUD,
mock neutral authentic animation clips and streamed Atlas Plaza/steam audio.
The tray uses authentic original ring and 1–9,0 numeral artwork; ability-specific icons remain unavailable. UI-navigation mode routes the left stick through bounded focus hysteresis/repeat, and D-pad/A continue to navigate. Character choices change mock data only. Male/Female/Huge costume assemblies
have independent host evidence; this APK does not render their full resource
closures. Jump-and-smash is an animation preview, not jump physics.

`CohHudState` and `CohHudIntent` are copied game-state/intent boundaries. Future
session integration must marshal them to the HUD owner, and marshal animation,
appearance and emitter events to their respective owners. No network packet,
authentication or session state machine is linked by this application.

Build preparation verifies the exact accepted APK SHA256
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`,
its seven asset pins, additional original raw animations/font/sound identities,
and generated envelopes. Binary inputs stay in external packs. Preparation is
reproducible from clean checkout using bounded range requests; it does not claim
to hash the complete remote archives. Font mask bytes can vary with FreeType
version, which is recorded in preparation evidence.

Run `tools/prepare_assets.py --help` and `tools/build_apk.py --help` for explicit
SDK/NDK/corpus paths. The standalone workflow builds ARM64 and emulator x86_64
APKs and runs `emulator-scenario.json`. It uploads exact commit, checksum,
packaged identities, framework commands, JSON reports and screenshots. Existing
CI workflows and shared root build files are unchanged. A local successful
build does not imply an emulator or device pass.

The test application is intentionally debuggable for `run-as` report collection;
it is not a production release. The native audio worker owns decoding, asset
reads and AAudio control. Mixer callbacks do not decode, allocate or take the
control mutex. Pause closes/joins the sink before exporting current mixer
counters. While running, `diagnostics_valid=0` means callback diagnostics are
from the last quiescent checkpoint. A failed close retains the whole native
Session and AssetManager; one process-wide cleanup slot blocks another Session
until cleanup succeeds. Both Java and native admission enforce this bound.

The retained 0.1.0 harness records CPU frame/stage timing. Generic performance counters
that have no caller adapter remain uninstrumented; their zero values do not
mean the scene made no allocations, copies or draw calls. Module cache/physics/
audio/HUD receipts report their own explicit bytes and counters.

CPU frame/stage measurements include only explicit scopes. No GPU timer adapter
is installed, so GPU timing is unavailable. This small offline scene cannot
establish full-game FPS, full-map memory use or Adreno performance.

## Combined Thor procedure

1. Keep the accepted 0.3.0 APK installed. Install the separate ARM64 support APK
   from the named Actions artifact; check its SHA256 against `SHA256SUMS`.
   The support release uses a separately verified disposable debug certificate;
   export its report and uninstall only the previous support app first.
2. Open **CoH Native Support**. Confirm scene and source-font HUD render,
   mock health/endurance update, and music plus positional ambient audio play.
3. With UI navigation OFF, use left/right sticks, short WASD/D-pad movement and touch dragging; check
   grounded movement, blocking, sliding and Near/Far selection. Reset actor.
4. Press **Mock animation** four times, observing punch, jump-power, reaction
   and restoration of accepted grounded locomotion. New previews are neutral
   poses; do not evaluate body morph parity from these clips.
5. Touch a power slot, target and Characters. Select mock character data; the
   visible scene actor remains Wretch. Toggle **UI navigation: ON** and use
   left stick, D-pad/shoulders/A. Enter a short message with Android keyboard and **Send**.
6. Press **Recreate** twice, Home/resume three times, and test an audio route
   change and another app briefly taking audio focus. Confirm HUD/chat persist, movement clears on focus loss, audio
   resumes, and no duplicate scene or sound remains.
7. Run for 10 active minutes with movement, scene selection and simultaneous sound. The new `support.active_foreground_ms` accumulates foreground time across Surface lifetimes; background time is excluded.
   Home for several seconds so audio diagnostics become quiescent, resume,
   and **Export report**. Share JSON, Far/Near screenshots and observed sound,
   input and visual issues in one consolidated session.

Physical acceptance requires the exported device evidence, zero relevant
source/GL/cleanup errors and explicit human visual/audio/input checks. No
physical result is recorded yet. Remove only `org.coh.nativesupport` to roll
back the test application; the accepted client and launcher remain installed.
Opt-in library commits may be reverted additively in reverse dependency order;
never reset or rewrite the shared branch.

The source-bound artifact recovery checker and complete pending physical review
matrix are documented in [qualification-next/INTEGRATION.md](qualification-next/INTEGRATION.md).
The retained artifact passed 13 Android emulator scenarios; these have not been
repeated. Its report incorrectly labels version code `1` although the verified
APK manifest code is `100`. New builds must report installed package metadata
and pass the stricter emulator identity checks. Original font glyphs are present;
baseline original UI icon/skin closure remains incomplete.

## Gameplay continuation scope

This runtime changes only the separate support package and opts into new tray,
analog-focus, listener and diagnostic adapters. Spatial sound follows the actual
source scene camera; emitters are anchored near the bounded scene spawn. Android
audio focus loss pauses playback, output-route changes close/join then reopen on
the native owner, and platform error/failed-close recovery retains callback state.
Surface recreation currently pauses/reopens audio and is part of the test.

The new generation-aware body-mesh render bridge, retained collision coverage
snapshots and transactional multi-actor animation bridge are separately
host/source/sanitizer/ARM64 qualified. Their complete character, streamed-map and
multi-character GPU integrations remain pending; this APK keeps the accepted
Wretch/Atlas regression scene. No new full gameplay gate is accepted.

JSON now reads installed package version metadata, includes a monotonic
foreground-duration observation, partial Java/native-heap bytes and explicit
unknown RSS/PSS/thermal flags. No GPU timer, full-map FPS or physical qualification
is inferred. Export must identify package org.coh.nativesupport, version
0.2.0-gameplay/code200, the installed APK SHA and all original asset identities.
