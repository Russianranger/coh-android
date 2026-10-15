# Incremental native engine contracts, ABI 1

These opt-in modules are outside every existing APK build and JNI path. Gates 19–21, accepted kernels, source pins, fixtures, receipts, root Gradle/CMake and workflows are read-only for workers. No production server changes. Shared files and eventual Android adapter are coordinator-owned.

- Asset identity is the original virtual path plus content generation. Modules borrow input spans only for a call unless their public API explicitly retains ownership. Retained objects have explicit acquire/release; caches have byte and entry limits and observable counters. Never treat serialized 32-bit pointer slots as native pointers.
- Assets expose indexed lookup, bounded owned reads and typed decoder adapters. Renderer accepts immutable indexed geometry/material submissions, column-major source transforms, explicit texture/sampler/blend/depth state, with no path-specific branches. Asset-to-renderer bridge is coordinator-owned; renderer may use immutable test inputs.
- Animation owns simulation state and emits caller-owned poses; actor and rig IDs are data, not global renderer state. Source clocks/ticks are explicit. Existing Huge locomotion remains a separate accepted adapter.
- Network separates bounded datagram transport, reliable framing and session state. Messages are borrowed on dispatch and copied into bounded retained queues. No authentication credentials in diagnostics. Source/reference packet provenance and unsupported commands must be explicit.
- UI owns a bounded widget tree and draw list. Bindings use stable IDs and explicit state updates; input focus, touch/controller navigation and text commit are independent of transport and rendering. Android Surface generation invalidates GPU handles, not logical state.
- Audio events have source/emitter IDs, category, priority, source gain, location and schedule frame. Decoder/cache work happens off the audio callback. Callback mixing must not allocate, block, invoke diagnostic callbacks or decode compressed data.
- Every module is single-owner-thread unless explicitly documented otherwise. Cross-thread interaction requires bounded copied queues. Renderer calls stay on the GL thread; audio callback has exclusive realtime state. Cancellation is cooperative outside realtime callbacks; teardown is idempotent after producers stop.
- Public errors use CohStatus where practical; preserve preexisting kernel return conventions via adapters. Output remains valid or unchanged on failure as documented. Counters and deterministic reports distinguish implementation, host qualification, Android build, emulator and physical acceptance.

## Ownership

| Worker | Exclusive scope |
|---|---|
| A / 22 | `native-android/engine/assets/` |
| B / 24 | `native-android/engine/renderer/` |
| C / 25 | `native-android/engine/network/` |
| D / 33 | `native-android/engine/sequencer/` |
| E / 34 | `native-android/engine/ui/` |
| F / 43 | `native-android/engine/audio/` |

Workers own implementation, source provenance, standalone test driver, negative/oracle tests, performance/memory diagnostics and integration/rollback notes within their directory. Each produces a local commit only. Coordinator owns this contract, cross-module adapters, receipts and aggregate driver. No remote worker branches.

## Integration and rollback

Modules stay opt-in until individually qualified and bridged by coordinator-owned tests. Re-fetch native-android and inspect intervening paths before cherry-picking local commits; ordinary fast-forward push only. A push race requires reconciliation and rerunning affected checks. Roll back an integrated module with an additive revert after inspecting dependencies; never reset branch history. Existing accepted APKs and qualification receipts remain immutable.
