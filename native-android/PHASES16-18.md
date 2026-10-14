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

Implementation and first host checks are complete; Android build/emulator
qualification is in progress. Physical Thor acceptance of this new batch is
pending. These statuses must be updated from the actual final build evidence;
the accepted gates 13–15 do not establish new batch acceptance.

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
