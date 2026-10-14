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
pixels, real bench occlusion and opaque reverse draw-order depth equality.
These checks precede continuous rendering. It does not read back every gameplay
frame or recenter the logical camera between diagnostic rounds.

Java foreground/Surface epochs are also native tickets. A queued render call
cannot reset cancellation after its epoch becomes obsolete. Focus loss clears
controls. Ordinary context reconstruction retains logical state; process death
or a new app launch starts a fresh offline session. Reset actor is explicit.
Reports are immutable export snapshots and atomic, coalesced internal writes.

## Validation and device boundary

The dedicated [session workflow](../.github/workflows/native-session-client.yml)
builds and lints ARM64, builds a separate x86_64 package, verifies APK signature,
manifest, ELF machine and exact assets, then drives actual Android keyboard
input and touch. It checks idle/run/release, all four movement directions,
scene visibility/depth, recreated Surface state, Home state and real document
export. Source-host qualification and original reports are retained.

Implementation and first host checks are complete; Android build/emulator
qualification is in progress. Physical Thor acceptance of this new batch is
pending. These statuses must be updated from the actual final build evidence;
the accepted gates 13–15 do not establish new batch acceptance.

The conventional launcher/client, earlier native probes, existing asset packs
and user data are unchanged. Work remains on `native-android` only.

See [one combined Thor check](session-client/THOR-TEST.md).
