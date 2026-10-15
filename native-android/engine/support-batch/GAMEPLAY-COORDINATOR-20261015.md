# Native gameplay continuation — coordinator report

## Recovery and ownership

All six real workers ran concurrently in independent detached worktrees pinned
to `3c5da1d8cd501d778e270d395109d40666fbe37a`. This was the actual fetched
`native-android` HEAD, newer than the supplied historical `132a813df5` checkpoint.
Existing six-module receipts and the qualified support 0.1 APK were recovered.
Its archive, both APK signatures, 105 runtime/header identities and seven accepted
0.3 assets were independently verified. No accepted gates 1–24 build was repeated.

The primary checkout and its linked worktrees were inspected read-only. One
primary worker retained 29 unpublished dbclient/login/mapclient files; none
matched our changed paths. While we worked, the primary published `5637133133`
(import/driver corrections in its combined launcher). Our publication preserved
that commit unchanged. No active primary process, workflow, source/configuration,
Session Client, conventional launcher, imported asset or character data was
modified. No main update, force push, remote worker branch or history reset occurred.

The local Git client had no push credentials. Reviewed local deltas were published
as ordered GitHub commits on top of the rechecked remote parent, with a
non-forced expected-HEAD update. All published runtime files were then fetched
and compared. Protected paths and the primary combined launcher were byte-identical
to the concurrent primary revision. Worktree isolation and shared boundaries are
in [the ownership contract](GAMEPLAY-BATCH-20261015.md).

Original source kernels are pinned to
`0b75ade0c801735e10c5798f641948a45cc50488`, original data to
`d51533ec8e6a9cf726b9214968077a05fdcf19f3` where applicable. Each worker records
individual source/member hashes, bounded acquisition provenance and exact
comparison limits. Whole archive hashes were not inferred from ranged members.

## Code and validation

| Worker | Published code commits | Implemented and independently checked |
| --- | --- | --- |
| A: Support qualification | `fde1ad0804`, `26f1d7d872` | Retained exact old APK/evidence; strict installed-version binding; recursive compiler header/generated-input closure; signer receipts; nine real-owner audio fault scenarios and maximum-width JSON export |
| B: Appearance | `eacf8bf415`, `506294d722` | Native GEO-to-mesh and generation-aware CPU-skin/render-packet bridge; explicit material/texture/socket/rig admission; morphology ownership contract |
| C: HUD/input | `3b886f3d9b`, `72b9fcf755` | Authentic source tray ring and1–9,0 numeral artwork; original-font HUD; bounded analog focus hysteresis/repeat |
| D: Physics | `120fc1be5a` | Retained immutable collision snapshots, truthful missing/empty/loaded coverage cells, exact segment generations and transactional neighborhood admission |
| E: Animation | `e54e715aaa` | Transactional selection/pose/cue bridge, explicit actor/appearance/rig/clip generations, typed local audio/effect/attachment cues and three source families |
| F: Audio/performance | `c70a8f9df7` | Correct reflected-source-camera listener, cumulative/delta counter bindings, unknown-versus-measured flags and distinct memory gauges |
| Coordinator runtime | `f347cdc8e5`, `c14a831b55` | One support APK: genuine tray textures, atomic analog mailbox, HAT/device-removal ownership, chat keyboard focus, audio-focus/routes/failed-close recovery, actual camera listener and explicit frame observations |

Representative independent results (not an additive combined test count):

- Appearance: 402 genuine body models/79,687 vertices and31 Wretch models;
  1,326,591 original-source scalar comparisons;1,206 neutral rig/socket part poses;
  521 defensive cases. Host GLES:132,840 components, two contexts, maximum error
  1.15e-6 at1e-4 tolerance. These are **partial untextured body-part packets**.
- Physics:10,566 checks, four connected synthetic source-qualified graded regions,
  160 exact source WALK ticks, seven refreshes,65,536 coverage cells and8,000
  concurrent original CTri queries. Zero query/tick allocator calls and no
  outstanding tracked allocations.
- Animation:14,648,961 new actor checks,12,000 original sequencer comparisons,
  14,516,000 pose scalars with zero error; three genuine body actors over 9,000
  interleaved ticks and6,636 bounded routed cues. Separate original family
  regeneration compared 5,478,444 more scalars. Missing-resource/cue/edge rollback passed.
- UI:8,224 original decoded tray bytes, original numbering,18 malformed inputs,
  18,504 real GLES channel comparisons and retained 30,759 source-color comparisons.
  Actual integrated SupportUi:104 GPU frames,14 pointer cases,2,000 snapshot and
  2,000 navigation calls; exact analog power 1003 intent, pause suppression and
  Surface/chat retention. The HAT/UI-first-disconnect policy passed19 host Java checks.
- Audio/performance:53,090 checks,5,000 camera roundtrips,10,000 independent original
  spatial comparisons,1,000-step counter oracle; fixed 648-byte observer bridge and
  24-byte listener pose. Real support owner fault injection passed nine scenarios,
  five opens/five closes, zero retained assets/mixers/streams/sinks. JSON bounds
  tests used actual exporters with maximum-width values.

ASan/UBSan passed in applicable C modules and integrated adapters. LeakSanitizer
could not inspect sandbox `/proc/.../task`; affected runners explicitly disabled
LSan and separately tracked retained allocations. This is not an unrestricted
LeakSanitizer pass. Every worker produced an ARM64 API26 build/link or object
check with exact scope in its receipt. These results are distinct from Android
execution. The optional appearance CMake target built; physics direct complete
host/ARM64 linkage passed where the CMake CLI was unavailable.

## APK integration and gate status

The updated package is `org.coh.nativesupport`, version `0.2.0-gameplay`, code 200.
It coexists with accepted Session Client 0.3.0 and needs no server. Its visible
character remains authentic Wretch/Huge in the bounded Atlas scene. Character
choices remain labelled mock data; action previews are not completed combat.

New render-admission, collision-coverage and multi-actor interfaces are committed
and qualified independently. Full additional-body rendering, truthful larger-map
loader coverage and multiple visible actor integration remain pending; they were
not wired using fabricated assets or invented metadata. The existing six
support subsystem adapters remain in the consolidated application.

| Gate/workstream | Implemented | Host/source qualified | ARM64 built | Android emulator | Physical Thor |
| --- | --- | --- | --- | --- | --- |
| Gates 1–24 | Accepted original scope | Preserved | Accepted APK unchanged | Prior evidence preserved | Accepted original scope |
| Gates 25–27 | Primary owner only | Not assessed or modified | Primary owner only | Primary owner only | Primary owner only |
| A: Support client | Yes | Yes | Yes | Final qualification below | Pending |
| Gate 31 complete character | Partial mesh/rig/material bridge | Yes; partial host GPU proof | Yes | Complete new bodies pending | Pending |
| Gate 32 larger-world physics | Partial; coverage/ownership boundary | Yes | Yes | Existing bounded WALK scene; new larger coverage integration pending | Pending new scope |
| Gate 33 animation/effects | Partial; three-family actor/cue bridge | Yes | Yes | Existing Huge previews; multiple visible actors pending | Pending new scope |
| Gates 34–36 HUD/mobile input | Partial integrated HUD/tray/controls/chat | Yes | Yes | Final support scope below; physical analog/HAT/IME observation pending | Pending |
| Gate 43 audio | Partial integrated focus/routes/listener | Yes | Yes | Final support playback/lifecycle scope below; actual routes/focus interruptions pending | Pending |
| Gates 44–45 performance | Partial explicit observers/cache | Yes | Yes | Bounded offline CPU/cache/counter scope only | Pending Adreno/full-map measurements |

No new full gameplay gate or physical acceptance is claimed.30+FPS remains a
target. The small offline scene cannot qualify full-game FPS, RAM, thermal
behavior, combat, authored FX or real-server gameplay.

## Android qualification and exact handoff

Final support source: `c14a831b55163dbcf2b3e63b4c52805785fceafa`.
The earlier `eacf8bf415` runtime passed all 13 Android framework scenarios in
[run 38764195471](https://github.com/Russianranger/coh-android/actions/runs/38764195471).
Review then found and fixed HAT-only navigation and UI-first controller removal;
the corrected source requires its own qualification rather than inheriting that pass.

[Final successful workflow 38765087744](https://github.com/Russianranger/coh-android/actions/runs/38765087744)
passed all 13 Android 13 framework scenarios, exact source/package/version/APK
binding, Near/Far, touch/HUD-drag camera isolation, chat, controller-key intents,
Home/audio recovery and Surface recreation. Native analog/HAT policy and actual
SupportUi have separate host/ASan/UBSan proof; real physical joystick/disconnect,
audibility, external focus interruption and output-route changes are pending.

**[Download the exact APK/report/screenshot artifact](https://github.com/Russianranger/coh-android/actions/runs/38765087744/artifacts/11990195263).**
Choose `CoH-Native-Support-Client-0.2.0-gameplay-arm64.apk` (2,413,935 bytes).

- APK SHA256: `26bad28b029fef86931108b531f883c9a948a16aff1dc2cdba9d8447c6c4d935`.
- Signer certificate SHA256: `51c72fc0355533257734e5a6a7ea359e0bd59dcfb81d5e93ccd8171dbe0fba7b`.
- Artifact archive SHA256: `8cbf1be4b0fe880d341b3eb96f476f49db4879230349fda92cfe088e03181c81`.
- Package `org.coh.nativesupport`, version `0.2.0-gameplay`, code 200.
- Final source `c14a831b55163dbcf2b3e63b4c52805785fceafa`.

The archive digest/CRC, both APK signatures and hashes, all packaged assets,
106 local runtime/header identities, installed emulator APK and source binding
were independently checked after download. ARM64 and x86_64 native libraries
are byte-identical between clean local and hosted builds. The accepted seven
source-scene payloads remain byte-identical to the accepted 0.3 APK.

Final emulator export: 1,006 scene frames, three started/two completed contexts
(final context still live), zero GL/transform/support failures, zero invalid
performance samples. Joined audio checkpoint: 4,538 callbacks and zero
stream-underrun frames. Measured frame operations include 85,304 draw calls,
178,956,656 actor/HUD uploaded bytes,95,430,144 skin-cache copied bytes,
1,952,356 source-kernel skinned vertices and 2,994 WALK triangle tests. These are
bounded offline counters, not full-game or physical device measurements. The
raw build/emulator/pause reports and independent verification are retained in
[evidence/gameplay-continuation](evidence/gameplay-continuation/).


Accepted Session Client 0.3.0 SHA256 remains
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Its source, assets, original APK and acceptance reports were preserved.

## One combined Thor test

1. Keep accepted 0.3.0 installed. Install the ARM64 support APK from the exact
   artifact above. If replacing an older support debug certificate, export its
   report and uninstall **only org.coh.nativesupport** first.
2. Confirm authentic Atlas/Wretch, font, ring/numerals and updating health/endurance.
   Check Near/Far, left/right sticks, touch camera and short grounded WALK against
   floor/walls/sliding. Reset; preview punch/jump-power/reaction and restore WALK.
3. Turn UI navigation ON. Test left stick, D-pad/HAT, shoulders/A, power and target
   panels, mock character choices, touch and Android keyboard/chat. Disconnect and
   reconnect the controller while a direction is held; focus must stop repeating.
4. Listen to music and positional ambient sound while moving the camera and
   triggering previews. Change output route and briefly let another app take
   audio focus. Recreate three times and Home/resume three times; confirm one
   scene/sound, retained chat/HUD and cleared movement/focus.
5. Sustain 10 visible active minutes. Home for several seconds to join audio and
   capture current callback counters; resume and export JSON. Send the report,
   Near/Far screenshots and visual/audio/input observations together. The new
   active_foreground_ms excludes background time but is not itself a visual pass.

Pending physical evidence includes genuine sound quality/positioning, actual
Thor analog/HAT/touch/IME behavior, output routes/audio focus, multiple Surfaces,
foreground recovery and sustained operation. The physical-review matrix is
[saved separately](../../support-client/qualification-next/thor-physical-review-template.json).

## Future integration and next independent batch

Gates 25–27 remain entirely with the primary agent. Future session integration
supplies copied HUD state and receives typed local intents; it owns dispatch.
Appearance/animation keep matching immutable rig/clip/morph ownership. Neutral
sequencer poses use morph=NULL; Huge morphology requires a pose composed with
that same morphology. GL resources are rebuilt per Surface generation. Loaders
must attest truthful collision coverage rather than manufacture empty cells.
Audio emitter/listener copies stay on its bounded control queue; real-time
callbacks do no decoding, allocation or blocking. Unconnected metrics stay unknown.

The next six independent assignments can be:

1. Close one complete authentic Male/Female/Huge costume each: exact geometry,
   textures, materials and morphology, retaining Wretch regression comparisons.
2. Integrate those complete actor packets and source pose families into the
   offline renderer, then qualify textured GPU/material/pose parity on Android.
3. Admit larger genuine Atlas segments through loader-supplied collision coverage;
   test seams/elevations and missing-neighbor recovery without live prediction.
4. Render simultaneous animated actors and close authored local FX/attachment
   dependencies, preserving transactional bounded event delivery.
5. Recover genuine ability-specific icons and Unicode/font/layout resources;
   qualify physical controller reconnect, IME and aspect-ratio coverage.
6. Measure actual Thor audio routes/latency, world upload bytes and Adreno timings
   through safely supported asynchronous queries; retain unknown flags otherwise.

## Rollback

Remove only the support package on-device, or install the retained qualified 0.1
support artifact for its historical bounded scope. Never remove the accepted
Session Client or conventional launcher. Code rollback uses ordinary reverse
reverts of opt-in adapters/integration commits, preserving later primary work.
No branch reset or force push is required. Each worker's API/provenance/rollback
contract and exact receipts remain alongside its implementation.
