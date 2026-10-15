# Moving listener and observable performance bindings

Worker F starting revision: `3c5da1d8cd501d778e270d395109d40666fbe37a`.
Exclusive edits are inside `native-android/engine/audio/` and
`native-android/engine/perf/`. Existing accepted audio/mixer/perf/source kernels,
Session Client, server/session/networking, JNI, application builds and workflows
are unchanged. The two standalone module CMake targets add their respective new
source. No gate is accepted by this worker receipt.

## Recovery and scope

Existing audio PCM mixer/AAudio/lifecycle, streaming Vorbis, resampler, authentic
music corpus and performance/cache receipts remain intact. They were already
host/ARM64 qualified; the bounded support APK has separate emulator evidence.
Those expensive qualifications were not restarted. New qualification covers the
two missing integration contracts below; it does not supersede those receipts.

### Camera to listener

`coh_audio_listener_source_view(view, &pose)` consumes the **actual accepted
source camera view**, not the OpenGL projection or an actor transform. Original
camera math applies an X mirror in `rdrFixMat`; the original sound head-right is
therefore `{-view[0], -view[3], -view[6]}`. Taking the ordinary view row without
that source correction swaps stereo. The helper inverts the rigid reflected
basis to recover position and normalizes head-right. All output is staged, so
invalid/nonfinite/scaled/sheared/unreflected input leaves output unchanged.

Send the immutable 24-byte pose through the existing bounded owner mailbox.
The serialized audio producer calls `coh_audio_listener_apply(mixer, &pose)`.
On `COH_LIMIT` keep/retry the newest pose rather than dropping it or blocking the
callback. A paused owner should retain the newest pose and apply it before or
on resume. The helper does no allocation, file/clock/GL/platform operation.
Focus/route changes and AAudio lifetime stay with the Android application owner.
Surface recreation by itself does not imply audio focus loss.

The explicit `coh_audio_listener_pose(position,right,&pose)` alternative accepts
already-owned original `head_mat[3]`/`head_mat[0]` equivalents. Double normalization
avoids overflow/underflow for finite nonzero directions. The source-view inverse
has binary32 roundtrip tolerance up to 0.025 source units at +/-32500 positions;
the helper can use known original camera position via this alternative when
available. No world-space origin or fake listener is substituted.

### Owner totals to performance counters

Create a zeroed/fresh `CohPerfBridge` with `coh_perf_bridge_init()` alongside the
new observer. It owns 648 bytes of fixed storage on both tested 64-bit ABIs.

- `coh_perf_bridge_total(binding, perf, counter, owner_generation, total)`
  consumes a monotonically increasing **cumulative total**. Its first observation
  sets a baseline without counting unknown earlier work. Observe zero before
  the first real operation if that first operation should be included.
- Duplicate totals add zero. A new nonzero owner generation rebases without
  adding previous-generation work. A decreasing total within one generation is
  rejected with `COH_STATE`, retains the old baseline and increments a rejection
  diagnostic. It is never guessed to be counter wrap. Keep generations and
  observations serialized; arbitrary out-of-order snapshots are not supported.
- Paused or disabled observations advance the baseline, so excluded background
  work does not appear as a spike at resume. Submit a baseline at the paused
  boundary if the owner can perform operations while the bridge is not sampled.
- `coh_perf_bridge_delta()` consumes already-measured explicit operation deltas.
  Use one mode and one source per counter; mode mixing is rejected. Combine
  actor/world totals at the owner before feeding their one draw counter, or
  submit actual per-frame deltas instead. Existing observer saturation applies.
- `coh_perf_bridge_memory()` accepts separately typed module-accounted, RSS and
  PSS byte measurements. These are separate gauges with individual high-water
  marks and presence. Do not sum overlapping module storage into process memory.
  The function itself performs no OS measurement; obtaining OS values belongs
  on a control/report path.

`coh_perf_bridge_json()` exports a sibling JSON object to `coh_perf_json()`.
Every counter has `known`, mode, source generation/total, observations, rebases
and rejections. A known measured zero is distinguishable from an unconnected
zero. Unknown RSS/PSS remain explicitly unknown. All sample operations have no
allocation, locking, file I/O, clock or graphics calls. JSON formatting belongs
on the owner/export thread. Values are uint64; preserve precision above 2^53.
This module neither observes another thread's live counters nor adds a new
process-global allocator hook. It does not introduce GPU queries, readbacks or
`glFinish`; GPU timing remains unavailable unless a separate ready-only adapter
supplies real results.

## Validation and provenance

Run the additive check without fetching dependencies or modifying old receipts:

```sh
python3 native-android/engine/perf/check_bindings.py \
  --source-root /path/to/read-only-full-coh-source \
  --ndk /path/to/android-ndk-r28c \
  --output /tmp/bindings-qualification.json
```

The committed receipt is `evidence/bindings-qualification.json`.

| Level | Evidence |
|---|---|
| Implemented | Listener adapter and cumulative/delta diagnostic contracts |
| Host qualified | 53,090 checks, including malformed/output-preservation, queue saturation, stereo reversal, generation/reset/mode rejection, bounded JSON and unknown-memory cases |
| Independent source | 5,000 source camera roundtrips and 10,000 moving spatial channel comparisons against unchanged pinned Ouroboros sound functions and `createMat3YPR` |
| Independent arithmetic | 1,000 scripted cumulative totals, repeats, disabled/paused periods and generation changes compared with Python; exactly 2,619 admitted draws |
| ASan/UBSan | Passed with halt on first error. LeakSanitizer cannot inspect host process tasks; receipt records this restriction |
| Memory | 648-byte fixed bridge, 24-byte pose; zero directly linked malloc/calloc/realloc/free calls in all tested sample/listener/mixer regions |
| Android ARM64 | API26 AArch64 shared library links with no undefined symbols; SHA256 and compiler in receipt |
| Emulator | New integration pending coordinator APK qualification; no execution claimed by this worker |
| Physical Thor | Pending; no audibility/latency/xrun/FPS/device-memory/thermal claim |

Original source revision is `61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d`.
The checker validates entire original sound-file SHA256s, the normalized original
mathutil.c SHA256, and the unchanged `createMat3YPR` body SHA256 before compiling
an oracle. It uses the portable sinf/cosf source branch, controlled one-sphere
nonfading audio, the original gain quantization and panning formula. Original
camera construction is compared with the accepted `coh_world_camera` adapter;
the source camera adapter already has original-body parity receipts. Tests use
controlled positions/events and a labeled constant mock PCM for queue/stereo
behavior, not fabricated game assets or a claim of DirectSound sample parity.
No authentic audio/character asset identity is changed.

## Integration and rollback contract

The coordinator adds `engine/audio/coh_audio_listener.c` and
`engine/perf/coh_perf_bridge.c` to the dedicated support source manifest only.
It owns all JNI/mailbox/camera/renderer bridges and the support APK workflow.
Refetch and compare concurrent paths before cherry-picking this local commit.
Nothing in gates 25–27 is a dependency. No remote worker branch is required.

Populate only counters actually observed at their operation owners. Real draw
counts must include or explicitly scope HUD/world/actors; physics counters must
reflect real candidate/narrow-phase work; exact skin-cache counters remain with
their owner. Unconnected counters stay unknown. Do not infer no allocations,
GPU time, FPS, process memory or thermal behavior from host mocks or zeros.

Rollback first removes the coordinator's optional adapter references, then
reverts this additive worker commit. Preserve old receipts/APKs and branch
history. Existing renderer, mixer, camera, cache and performance core remain
available unchanged. New gate acceptance still requires the consolidated
Android emulator test and returned physical AYN Thor evidence.
