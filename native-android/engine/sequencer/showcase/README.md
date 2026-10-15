# Gate 33: transactional multi-actor presentation bridge

Implemented, host/source qualified, ASan/UBSan qualified and Android API26 ARM64
object built. The new bridge has **no Android execution, GPU or Thor acceptance**.
The existing support-client Huge preview qualification remains unchanged.

Starting integration revision: `3c5da1d8cd501d778e270d395109d40666fbe37a`.
Original C source: `0b75ade0c801735e10c5798f641948a45cc50488`.
Original i24 data: `d51533ec8e6a9cf726b9214968077a05fdcf19f3`.

## Recovered foundation and actual new behavior

`coh_seq_playback` already supported original raw-key sampling, recursive blend
composition and bounded markers. Its prior three-body source/oracle, ASan/UBSan
and ARM64 receipts are preserved. `support_animation` already rendered neutral
Huge previews in the separately qualified support APK. Neither is replaced.

The missing integration safety was the gap between successful source selection
and a failed pose/cue delivery. Calling `coh_seq_step` and then a playback sampler
could consume animation time and transition state before a missing rig or short
output buffer was discovered. New `coh_seq_actor` composes those existing kernels
on private candidate state and commits them together. Missing source dependencies,
invalid input, cancellation and insufficient output capacity leave actor, pose,
cues and count unchanged. The caller can load the clip or enlarge its buffer and
retry the same simulation tick without inventing animation time or transitions.

The bridge adds stable appearance/rig/resource generations, independent state for
multiple actors, rig-space socket delivery and typed local audio/effect/attachment
requests. It preserves original graph priority and interruption rules. Routes
are local explicit presentation bindings, **not source PlayFx timing, server
commands or completed combat mechanics**. Unresolved original next edges remain
`COH_UNSUPPORTED`; missing clips remain `COH_NOT_FOUND`.

## Public interface and ownership

Include `../coh_seq_actor.h`; compile `coh_seq_actor.c` with the unchanged
`coh_sequencer.c`, `coh_seq_playback.c`, existing animation sampler and libm.
When compiling the character implementation, keep its existing inclusion of the
animation implementation rather than compiling it twice. No root build, JNI,
renderer, Session Client, workflow, server or gates 25–27 paths were changed.

- The asset owner retains immutable graph, clip, pose-binding, marker and cue-route
  tables plus original raw-key bytes. One `CohSeqActor` belongs to one simulation
  owner. Different actors can borrow different Male/Female/Huge base hierarchies.
- `coh_seq_actor_init` validates the graph and loaded pose/socket dependencies.
  Pass explicit nonzero appearance, rig and resource generation identifiers.
- `coh_seq_actor_step` takes the original bounded `CohSeqInput`, an increasing
  tick and caller-owned pose/cue outputs. Advance actors in stable application
  order. Dispatch cues only after success. The source 30 Hz timestep remains
  [0,3]; discard background wall-clock backlog.
- `coh_seq_actor_active_rig` plus the returned neutral local/world pose is the
  rendering contract. Use actual mesh bone IDs for palettes; the canonical test
  rigs' single-bone palette is raw-pose test metadata. Appearance owns morphs,
  root/registration transforms, skinning, material and attachment composition.
- Routed cues carry actor/rig/clip/move/tick, all resource generations and the
  recursively blended rig-space socket rows. Apply morphology and actor-root
  composition before rendering a world-space effect. Root routes use identity.
  No effect assets or unqualified authored FX are silently substituted.
- `coh_seq_actor_rebind` accepts strictly newer resource generations between
  ticks, retaining active identity, source range/rate, hierarchy, pose and clock.
  Appearance/rig-generation or graph changes require explicit reinitialization.
  Release old resource storage only after every borrowing actor has rebound.
  GL context generations remain the renderer owner's independent responsibility.
- `coh_seq_actor_snapshot` exposes bounded storage, transitions, blended bones,
  tick and cue counts for the coordinator's existing diagnostic export.

Each actor retains 8,328 bytes on this host ABI. The optimized bridge step has
26,304 bytes of compiler-reported stack plus called sampler frames. There are
no hot-path allocations, GL calls, locks or file operations; cancellation is the
single initial source-step poll. The symbol audit checks allocation/blocking
imports. This fixed stack budget must be included in Android thread sizing.

## Authentic offline showcase bindings

`authored_graph.h` provides an opt-in six-move source subset with distinct
namespaced state/move constants and Male/Female/Huge clip tables. It is reproduced
byte-for-byte from the unchanged original exporter and pinned source fixture:

| Source move | Canonical raw rig |
| --- | --- |
| JumpPost | `BODY-combat_postjump.bin` (`male-comb_postjump.bin`) |
| 1_2punch, 1_2punchpost | `BODY-1_2punch.bin` |
| jumpNsmash, jumpNsmash_post | `BODY-jump_n_smash.bin` |
| Fallout | `BODY-fallout.bin` |

Bind one `CohSeqPoseBinding` per move to its body's retained rig. The source clip
IDs/ranges come from the corresponding `coh_showcase_*_clips` table. Mock UI actions
set the actual required source bits and may request `force_interrupt`; the source
sequencer then chooses a permitted move. This does not make arbitrary previews
into gameplay or bypass unresolved next-move dependencies. Accepted idle/run/WALK
stays on its existing qualified locomotion path; complete player-graph closure
and all-body grounded/morph integration remain future work.

Acquire/regenerate the original family inputs without embedding them in Git:

```sh
python native-android/engine/sequencer/showcase/acquire.py --output /tmp/coh-families
python native-android/engine/sequencer/showcase/check.py \
  --source-root /path/to/upstream/ouroboros --corpus /tmp/coh-families \
  --output /tmp/coh-family-qualification/qualification.json \
  --android-clang /path/to/aarch64-linux-android26-clang
```

The source root's sibling `i24` must contain original sequencer declarations.
Acquisition uses the existing strict HTTP206 reader and 16 MiB ceiling, central
and local ZIP identity, exact size, CRC and existing raw-member SHA pins. The
Female base pin was newly established from this release's stable ETag, original
member identity and CRC, then fixed in `base-pins.json` before source-pose tests.
The full published outer/inner hashes are provenance; this subset acquisition
does not claim to hash those whole archives. No original asset bytes are modified.

## Validation and integration/rollback contract

`qualification/host-arm64.json` records host and ASan/UBSan runs, original source
function/file identities, acquisition bytes/member hashes, actual generated rigs,
Android object SHA and exact commands. New bridge coverage includes 12,000
original-source sequencer comparisons, 14,516,000 per-bone original transition /
hierarchy scalar comparisons (zero maximum error), 9,000 interleaved ticks with
three distinct authentic family actors, 6,636 routed markers, deterministic cue
order, missing-resource retry, unresolved source edges, capacity rollback,
cancellation, invalid socket rejection, resource rebinding and range guards.
The recovered family regeneration independently compares original scalar raw-key
and per-bone kernels again before admitting the actual three-body inputs.
ASan/UBSan are active; LeakSanitizer is disabled for the executor's `/proc` limit.
Recorded elapsed times are host test timings, not mobile FPS or GPU claims.

Coordinator-owned support integration is additive and opt-in: add the actor
module, retain canonical family buffers, bind actual body meshes through the
appearance bridge, drive local source bits from mock controls, and export actor
snapshots/cue generations. No callback from this module enters live session code.
The required Android checks are multi-actor rendering and transitions, interruption,
attachments, Surface recreation, pause/resume without backlog and stable memory.
The user must supply a physical Thor report before any new device acceptance.

Rollback is an ordinary revert of this additive commit and any opt-in coordinator
bridge after checking consumers. Existing playback/sequencer kernels, accepted
0.3.0 APK/reports, prior support APK, conventional client and primary live session
remain intact. No remote worker branch or push is performed by this worker.
