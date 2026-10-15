# Gameplay continuation ownership and integration contract

Pinned starting revision: `3c5da1d8cd501d778e270d395109d40666fbe37a`.
Remote `native-android` was fetched before work began. The historical checkpoint
`132a813df53d94c38b441932f85ec42741123abf` is its immediate parent.

Six actual workers run concurrently in separate detached Git worktrees. No
remote worker branches exist. Their local commits are reviewed before ordinary
fast-forward publication to `native-android`.

| Worker | Exclusive write scope | Existing qualification reused | Remaining focus |
| --- | --- | --- | --- |
| A | `support-client/tools/`, `README.md`, `emulator-scenario.json`, `qualification-next/` | 13-scenario hosted support run 38702695275 | APK/source/signature recovery and reusable qualification checks |
| B | `engine/appearance/` | Costume assembly, seven genuine GEO files, Wretch palette | Explicit geometry/material/rig closure and rendering admission |
| C | `engine/ui/` | Source-font HUD, touch/controller/IME, local intents | Authentic power icon resource/rendering adapter |
| D | `engine/physics/` | BVH, immutable segments, source WALK | Missing-neighbor admission and retained scene ownership |
| E | `engine/sequencer/` | Source family playback, recursive blend, bounded cues | Multi-actor offline showcase and typed cue routing |
| F | `engine/audio/`, `engine/perf/` | Mixer, AAudio, Vorbis, resampling, fixed observer/cache | Camera listener and explicitly observed cumulative counters |

Coordinator exclusively owns this directory, support-client C/Java integration,
its build source manifest and, if needed, its dedicated workflow. Other
workflows, root build files, accepted Session Client and shared renderer remain
read-only. Worker A requests ownership before changing another support path.

## Primary agent boundary

The primary checkout and its nine linked worktrees under
`/workspace/scratch/cd30b2fc1c9e/` are read-only to this batch. The primary
checkout was clean at recovery; this does not establish that an external agent
has no additional unpublished work. None of its processes, workflows, branch
state or runtime files are changed by this batch.

Gates 25–27 and all network/auth/dbclient/login/mapclient/live/session/
replication and server-adaptation source/configuration are excluded. Recent
commits added native session interoperability and a combined server application;
those commits are retained without evaluating or repairing their implementations.
No proposed future session adapter authorizes modifications to these paths.

## Shared public boundaries

Actors carry explicit actor, appearance, rig, clip and immutable resource
generation identities. Appearance resolves source paths without substitution;
rig/morph compatibility is admitted explicitly. Animation owns its playback
clock/state per actor and writes caller-owned poses and bounded local cues.
The GL owner uploads admitted packets and invalidates GPU handles per Surface
generation while retaining logical state.

Collision snapshots own their immutable copied segment and coverage data.
Unknown neighboring cells fail admission rather than imply empty terrain.
Prepared movement windows own their data independently of the snapshot owner.
Accepted source WALK/CTri arithmetic remains the movement implementation.

The existing copied `CohHudState` and typed `CohHudIntent` boundary remains
stable: mock power, target, character and chat actions are local intents.
No worker implements packets. Original fonts/icons retain separate source pins;
UI and input state survive Surface replacement independently of GPU resources.

Audio emitters/listeners are copied through a bounded control-thread mailbox.
Only the decoder/backend owner invokes codecs, asset reads and AAudio control;
the realtime callback never allocates, decodes or blocks. Callback counters are
exported at joined/quiescent checkpoints. Camera coordinates use the accepted
world-view convention and original source spatial calculations.

Performance observations name their source and generation. Unobserved counters
remain unknown. Cumulative counters reset on owner generation changes and never
underflow across scene/Surface resets. Module-accounted bytes, process RSS/PSS,
and thermal availability are distinct observations. No synchronous GPU timing
or readback is introduced into frame profiling.

## Acceptance, integration and rollback

The accepted 0.3.0 APK SHA256 remains
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Gates 1–24 remain physically accepted within their original scopes. New code
uses separate implemented/host/ARM64/emulator/physical status; no new physical
acceptance follows from host or emulator success.

The recovered support 0.1.0 source is
`b69bbf232e1746f1fb35ef1aa624a636f2cce490`, artifact 11957750066 in run
38702695275. It is reused unless runtime changes justify a new build. A new
offline support APK retains package `org.coh.nativesupport` and needs no server.

Before integration the coordinator refetches remote HEAD, compares intervening
paths with every worker commit, and stops conflicting integrations. Workers
remain isolated until their own validation completes. No reset, force push,
history rewrite, primary workflow restart, accepted APK replacement or imported
asset/user-data modification is permitted.

Rollback uses ordinary revert commits or removes opt-in adapter linkage in
reverse dependency order. Removing only `org.coh.nativesupport` restores the
device's prior testing setup. Existing accepted applications and evidence remain
available. Each worker adds its exact validation and rollback contract locally.
