# Second parallel batch: opt-in extension contracts

Base: native-android 2c32f5686246fa28cf3341e8e89dd1014eacd5f4. Accepted offline APK0.3.0 SHA25675ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639 is immutable. Existing ABI1 CohStatus/CohBytes/CohAssetId/CohVec3/CohGameEvent/CohCancel stay unchanged.

Gates25–27 are primary-agent exclusive. Workers may not modify engine/network, auth, session, replication, common contracts/build.py/check_all.py, accepted scene/JNI/renderer/kernels, root Gradle/CMake, workflows, prior receipts or the primary worktree. Unpublished primary additions outside these scopes must also be reused/read-only. No remote branches or worker pushes. All work remains opt-in.

Ownership:
A: engine/appearance/** (general costume/body/attachment assembly using existing character/asset/rig APIs).
B: engine/physics/** (spatial/streamed collision and new movement adapters around unchanged WALK).
C: NEW engine/sequencer/coh_seq_playback.* plus engine/sequencer/continuation/**; existing sequencer kernels/headers read-only.
D: NEW engine/ui/coh_hud.* plus engine/ui/gameplay/**; existing UI widget APIs read-only.
E: NEW engine/audio/coh_music.* and coh_resample.* plus engine/audio/android-integration/**; existing mixer/sink/lifecycle additions read-only.
F: engine/perf/** only (instrumentation/cache wrappers; no hot-path accepted-kernel edits).
Coordinator: engine/support-batch/** and a new isolated Android test harness if meaningful, shared JNI, packaging, new standalone CI only if nonconflicting; no edits existing active workflows.

Interfaces: immutable original-path+generation asset IDs, explicit body/rig/clip/material IDs. Borrow spans only synchronously; retained data has clear owner/bounds. Appearance emits bounded caller-owned part/attachment records and source transforms; no live session dependency. Physics consumes immutable world triangles/segment IDs and emits movement/contact results independent of networking. Sequencer continuation consumes existing CohSequencer/CohSeqSelection and raw rigs, emits caller-owned poses and deterministic typed events (actor/tick/kind); does not change kernel ABI. HUD consumes copied mock state via stable widget binding/actor IDs and emits local user intent events for future session adapter. Audio control/decoder thread resamples/streams decoded chunks through existing bounded SPSC rings, never decode/allocate/block in mixer/AAudio callback. Perf observes explicit begin/end/byte/counter samples without global allocator hooks in shipping code; caches include generation/pose identity and have byte/entry ceilings.

All public calls use existing status convention with transactional errors where practical, cancellation outside realtime callbacks, single-owner state except documented bounded SPSC queues. GL calls belong to GL thread; Surface generation invalidates resources, not logical actors/UI. No schema changes to network messages. Mocks are labelled and never called source-authentic or live-server proof. Every worker delivers check.py/tests/oracles/negatives/sanitizers/ARM64 evidence, measured memory, limitations, API + additive rollback docs and a local scope-only commit. Existing accepted behavior must remain byte/source-identical. Dedicated standalone CMake/host drivers may be created within ownership only.

Before publication, coordinator refetches remote, reconciles intervening files, verifies accepted APK/hash/assets and source receipts, integrates only nonconflicting additions, tests combined linkage and preserves history with ordinary fast-forward updates. No complete gate or physical acceptance based on host/compile results.
