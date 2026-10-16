# Third parallel batch ownership and integration contract

Pinned common start: `58caf1d4ab3b39757190f194100ccbc697d57857`.
All six workers run concurrently in separate detached worktrees; local commits only.
No remote development branches. The primary checkout and all its linked worktrees
remain read-only. Its unpublished work is recorded in recovery-audit.json and is
neither integrated nor discarded by this batch.

| Worker | Exclusive source ownership |
| --- | --- |
| A | `native-android/support-client/` |
| B | `native-android/engine/appearance/` |
| C | new `native-android/engine/offline-world/` |
| D | `native-android/engine/ui/` |
| E | `native-android/engine/physics/`, `native-android/engine/sequencer/` |
| F | `native-android/engine/audio/`, `native-android/engine/perf/` |
| Coordinator | this directory, additive integration qualification and support-only workflow if necessary |

Protected source includes engine network/auth/dbclient/login/mapclient/live/session/
replication, combined-client, accepted Session Client, server source/configuration,
primary workflows, shared root builds, shared JNI and main renderer. Existing
world/assets/renderer libraries are read-only dependencies. Only A edits the support
application and its copied offline renderer/JNI. Shared changes require an explicit
ownership check; overlap is deferred, never overwritten.

## Interfaces and lifetime rules

1. Appearance actors identify source costume, body, rig, original virtual paths,
   asset generation and materials. Borrowed spans last only for documented calls;
   retained ownership is explicit. Missing original parts fail or remain explicitly
   incomplete, never silently substituted.
2. Animation binds actor ID, rig ID and resource generation with caller-owned poses
   and bounded typed cues. Source clocks, priorities and hierarchy conventions remain
   authoritative. Per-actor state must survive GPU Surface recreation.
3. Physics preparation occurs away from the simulation owner. Publication uses
   complete immutable generation-tagged snapshots; stale/canceled work cannot replace
   a newer scene. Missing collision neighborhoods are unknown, not empty terrain.
4. Renderer resources are GL-thread-owned and generation-tagged. Surface recreation
   invalidates GPU handles without discarding logical actor/UI state. No new hidden
   shared renderer state or synchronous GPU readback is introduced.
5. Preserve copied `CohHudState` and typed `CohHudIntent`. Additional presentation
   snapshots/intents are independent additive adapters. All actions remain offline
   and mock; no session pointers or packet construction.
6. Audio listener/emitter/lifecycle messages use bounded copied queues or mailboxes.
   Decode, IO and backend control run on the owner thread. Callbacks cannot allocate,
   block, decode, log or acquire control locks. Counters specify quiescent/live scope.
7. Performance values include observation provenance, units and generation. Unknown
   counters remain unknown. Module bytes differ from process RSS/PSS; host timing,
   emulator timing and physical Adreno performance remain separate.
8. UI input stays on Android UI owner and crosses to GL through bounded copied data.
   Teardown stops producers, cooperatively cancels queued work, joins owners outside
   callbacks, and retains resources if a backend cannot safely close.

## Qualification and promotion

Reuse exact recovered Support Client0.2.0 evidence for unchanged source, instead of
rebuilding to repeat established results. A meaningful integrated runtime change
requires new source-bound ARM64 and x86_64 builds, signatures/identity verification,
and actual Android13 emulator qualification. Every stage is recorded separately:
implemented, source/host qualified, ARM64 built, emulator executed, physical Thor
accepted. No mock test closes a live-game gate.

Immediately before promotion, fetch remote HEAD, inspect intervening paths and
workflow triggers/concurrency, then integrate only nonconflicting local commits.
Push only guarded fast-forward updates to native-android; no force/history rewrite,
workflow cancellation, server/account/runtime reset, accepted app replacement or
primary worktree mutation. Retain local patches when promotion is unsafe.
Rollback uses additive reverts in dependency order; never reset the shared branch.
