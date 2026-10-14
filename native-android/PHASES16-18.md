# Gates 16–18: persistent scene, source movement and authored locomotion

This batch follows physical AYN Thor acceptance of gates 13–15, recorded at
`5cf2247bbe3ab1af3fb3d5a81b1f9ee9df21870e`. The new isolated application is
`org.coh.sessionclient`, version `0.1.0-gates16-18`. It is an offline native
client slice. No source Game executable, full Atlas map, collision world,
server login or replication is claimed.

| Gate | Implemented functionality | Exact boundary |
| --- | --- | --- |
| 16 | Eleven authored Wretch draws and the authentic Atlas bench share one native session, source world/view/perspective transforms, depth and lifecycle ownership. Actor and camera persist through frame boundaries, Home and Surface recreation. | Accepted character morphology, raw keys, sockets and CPU skinning feed the accepted precise world shaders. Initial actor placement and follow-camera distance are explicitly declared scene adapters. Full-world rendering, GPU palette skinning and gameplay lighting remain pending. |
| 17 | Android stick, WASD and D-pad input drive source control timers, direction handling, yaw quantization and horizontal `MOVETYPE_NOCOLL` motion at 30 Hz. | Authentic offline debug movement accelerates rapidly, with an explicit ±96 source-unit X/Z safety bound around the initial position. This bound is not world collision. Normal walking, jumping, gravity, prediction and server authority remain pending. |
| 18 | Forward motion selects authored Huge Ready, RunCycle and RunPost clips, source time/rate calculations, raw-key sampling and SmoothSprint hip correction in the same actor session. | A bounded forward locomotion adapter is qualified, not the full sequencer. RunPre and its early-stop dependency, random idle variants, backward/strafe animations, combat and other state graphs remain pending. Other directions use the explicitly limited Ready/post profile. |

## Source and runtime separation

The unchanged accepted character/world kernels, source shader arithmetic and
fixtures remain shared inputs. Comparison references are packaged for evidence,
but are not arguments to the renderer and cannot supply poses, placement,
movement or camera matrices. Asset bytes are verified against the packaged
manifest before native session creation.

The motion host oracle compiles the pinned original source bodies and executes
2,440 direction/timing cases. The native adaptation matches 51,539 checks with
zero error and passes ASan/UBSan. See [motion contract](motion/README.md).
Authored locomotion dependencies and source clock/rate witnesses are pinned
separately under `tools/locomotion_fixture`; their complete qualification is
retained with the new batch evidence.

The shared renderer checks actual CPU/GPU transforms, visible actor/world
pixels and real bench occlusion. Opaque reverse draw-order checks require zero
non-tie color mismatches; each bounded color difference must have individually
verified, identical integer DEPTH24 values from the actual world, actor and
combined depth textures. Clear, world-front and actor-front controls reject
a constant or disconnected depth sampler. These checks precede continuous rendering. It does not read back every gameplay
frame or recenter the logical camera between diagnostic rounds.

Java foreground/Surface epochs are also native tickets. A queued render call
cannot reset cancellation after its epoch becomes obsolete. Focus loss clears
controls. Ordinary context reconstruction retains logical state; process death
or a new app launch starts a fresh offline session. Reset actor is explicit.
Java captures export bytes before opening the document picker. Android checks
verify a real Save, valid session evidence and pre-picker event ordering, and
retain the exported file hash; they do not compare that hash to an independently
recorded pre-picker byte digest. Internal writes are atomic and coalesced.

## Validation and device boundary

The dedicated [session workflow](../.github/workflows/native-session-client.yml)
builds and lints ARM64, builds a separate x86_64 package, verifies APK signature,
manifest, ELF machine and exact assets, then drives actual Android keyboard,
touch and framework joystick events. Framework injection does not establish
physical controller acceptance. It checks idle/run/release, all four movement directions,
scene visibility/depth, recreated Surface state, Home state and real document
export. Source-host qualification and original reports are retained. A strict
whole-tree guard can reuse exact previously signed APK bytes for driver-only
changes; runtime, asset or source-oracle changes require the full build. The
package source commit, qualification-driver commit and both workflow runs are
recorded separately, and original build/source receipts remain unchanged.

Host, sanitizer, build/lint/package and Android 13 x86_64 execution qualification
passed. The [qualification receipt](evidence/phases16-18/qualification.json)
binds runtime source `e88a02b284de16ed6f7caf1e6b689f2e85d0b6e8`, original package
build run `38631384218`, and the corrected qualification driver
`5cea4041c8c822b6a983f815e3b4814a2e0d3b5a`. Final
[session workflow 38637681649](https://github.com/Russianranger/coh-android/actions/runs/38637681649)
and [portable core workflow 38637681101](https://github.com/Russianranger/coh-android/actions/runs/38637681101)
succeeded. The final session job reused the exact signed packages after proving
that intervening changes were only driver, workflow, documentation and evidence.
Original source/build receipts remain byte-for-byte unchanged.

The installed emulator session presented 2,237 frames across four contexts and
verified 163,176 transform-feedback components with zero mismatches. Two raw
reverse-order color differences remain recorded: both were individually
verified exact DEPTH24 ties; zero non-tie mismatches and actual sampler positive
controls passed. Actual keyboard directions, touch camera, Recreate, held
framework joystick input at real Home, checked cleanup, preserved actor/camera
orientation, renewed input, document Save and rendered Reset passed. Recreate,
Home return and Reset presented 62, 63 and 44 fresh frames after their respective
callback/background baselines. Released fresh movement stayed stable for 35
frames. The exported JSON was 156,853 bytes, with its exact digest retained.
Framework joystick injection has no physical controller identity; no physical
controller acceptance is inferred from its motion callbacks.

Earlier failed attempts remain retained. They identified exact depth ties and
automation prerequisites: actual Surface bounds, Material button case, keyboard
release ordering at Home, virtual joystick provenance and fresh-frame anchoring.
None of their incomplete Home/export traces is relabeled as passing.

**Physical AYN Thor acceptance of gates 16–18 is pending.** The accepted gates
13–15 establish their earlier probe scope only.

## Exact ARM64 handoff

[Download the qualified Actions artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705)
and extract `CoH-Native-Session-Client-0.1.0-arm64.apk`.

- Package: `org.coh.sessionclient`, version `0.1.0-gates16-18`, code 1.
- ARM64 APK: 2,139,651 bytes; SHA256
  `eb763d8c6e5354da06a336e8fe09a244a893755e82ef708ea1d2139dc17b8634`.
- Only native ABI: `arm64-v8a`, ELF64 AArch64 machine 183. APK signature,
  manifest and all packaged fixture identities passed verification.
- Artifact ZIP: 6,868,754 bytes; SHA256
  `4fbcc6923136ad59347c3fc1919e8071655291f02a78a4e4c42a8f68046bc3f0`.
- Actions retention ends November 13, 2026. The APK and complete diagnostic
  archive were also delivered directly with the handoff.

The conventional launcher/client, earlier native probes, existing asset packs
and user data are unchanged. Work remains on `native-android` only.

See [one combined Thor check](session-client/THOR-TEST.md).

## Next related development batch

After physical acceptance of this batch, prioritize a bounded walkable native
world rather than another isolated transport or rendering probe:

| Gate | Proposed integrated milestone | Required dependency and acceptance |
| --- | --- | --- |
| 19 | Authentic Atlas ground and obstacle group with real collision data | Expand the authored geometry group beyond the bench; decode the GEO collision records and source flags. Render/collision transforms must match, with actual traversable ground and bounded loading. Current collision packs are metadata only. |
| 20 | Grounded source WALK movement and wall handling | Port the bounded `entWalk`/`DoPhysics` and `entWorldCollide`/surface/move/slide subset against real `collGrid` results from gate 19. Require stable grounding, ordinary speed, obstacle collision and source movement trace parity. Gravity/jump requires complete dependencies; server prediction remains separate. |
| 21 | Authored directional locomotion and transition closure | Resolve RunPre and early-stop `Idle_Walk_Post` → `Idle_Ready`, including Huge's inherited male/walk fallback, plus Huge backward/left/right clips and source interruption/member priorities and interpolation. Qualify short taps, release, reversal, diagonals and obstruction in the same scene. |

The current spawn height is a declared bench AABB placement adapter, not
terrain detection. Full sequencer execution, full Atlas loading and live
server authority remain separate. GPU palette skinning is a subsequent
performance milestone; the accepted CPU skinning path currently functions.
