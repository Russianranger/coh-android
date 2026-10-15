# Gates 44–45 preparation: opt-in performance observer and exact skin cache

This module is host qualified and builds for Android ARM64. It is not enabled in
the accepted Session Client, and it is not a full-game performance or memory
qualification. It changes no accepted kernel, renderer, asset cache, WALK,
sequencer, audio callback, JNI, workflow or networking implementation.

## Public API and ownership

`coh_perf.h` provides a caller-owned `CohPerf`. Initialize it with
`coh_perf_default_config()` and `coh_perf_init()`, call `coh_perf_surface()` with
the current Surface generation, then record explicit monotonic nanosecond frame
and stage boundaries. Stage selection and collection are configurable. Calls
record counters for bytes copied/uploaded, draws, state binds, vertices skinned,
collision tests, asset hits/misses/evictions, readbacks, waits and allocations.
The adapter must supply actual operation-count deltas, not repeatedly add an
owner's cumulative total; unconnected counters stay zero.
There is no process-global allocator interposition in shipping code. Tests alone
use linker allocation wrappers.

The observer has fixed storage: 257 histogram bins at 0.5 ms increments for each
frame, GPU and seven CPU stages. The final overflow bin starts at 128 ms. Exported
percentiles are conservative bucket upper bounds, capped by the observed maximum;
an overflow percentile returns the observed maximum. Sums and counters saturate
at `UINT64_MAX`. These are cumulative summaries, not an unbounded frame log.
`coh_perf_resident()` records a caller-supplied resident total and its peak; it
does not claim to measure RSS/PSS or driver allocations.

Pause, Surface change and configuration changes discard unfinished timings.
Background time is never folded into a completed frame. Surface changes retain
historical CPU data and increment the logical epoch. Stale/disjoint/not-ready GPU
results are counted separately. `coh_perf_gpu_sample_epoch()` rejects pending
queries created before pause/resume, even with the same Surface generation; save
the observer epoch when issuing the query. `coh_perf_gpu_sample()` is only for an
already-ready result created in the current epoch. Both consume only a result
already supplied by an asynchronous timer adapter; it makes no GL call, waits on
no fence, and never substitutes CPU time for GPU time. Unsupported timing must
call `coh_perf_gpu_unavailable()`.

All observer calls are single-owner-thread. A separate observer is needed for a
different thread; serialize/merge snapshots off the hot path. `coh_perf_json()`
uses bounded caller storage and belongs on the control/export thread. Other
observer operations allocate nothing and make no OS, clock or GL calls. Snapshot
JSON is specified by `diagnostics.schema.json`; do not treat uint64 counters as
lossless JavaScript doubles beyond 2^53.

`coh_skin_cache.h` is a separate optional CPU skin cache. It performs exactly the
unchanged `coh_mesh_skin_vertex()` operation on a miss and returns a borrowed,
immutable deformed span. It preallocates all slots and working/output storage at
creation under an entry and byte ceiling. Sampling never allocates. Identity
contains mesh, rig and pose IDs **and every content generation**. Retained source
vertex and palette bytes must also compare exactly before a hit, so stale caller
IDs, hash collisions, near-equal poses or changed rigs cannot produce a false hit.
There are no hash-only or epsilon-based hits.

Output pointers survive only until the next sample/invalidation/destruction.
There is no pinning or cross-thread sharing. Inputs are immutable borrowed spans
for the call, and cannot alias private cache storage. Failure leaves the output
pointer/hit argument unchanged; a partly computed victim is invalidated. LRU
evicts whole entries; explicit invalidation drops all entries. CPU pose storage
contains no GL handles and need not be discarded on Surface loss. Rig/source or
animation changes must update the relevant generations. The defensive exact
comparison still detects accidental identity reuse.

## Validation

Run from a checkout containing this module, with a full read-only source checkout
available separately:

```sh
python native-android/engine/perf/check.py \
  --source-root /path/to/full/coh-android \
  --apk /path/to/CoH-Native-Session-Client-0.3.0-arm64.apk \
  --ndk /path/to/android-ndk-r28c \
  --output /path/to/perf-qualification.json
```

The accepted APK must have SHA256
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Eleven authentic Wretch/Huge part meshes are extracted temporarily from that
immutable APK. The palette inputs used here are explicitly controlled test
transforms, not sampled gameplay poses. No game asset bytes are committed here.

The standalone driver performs:

- Exact full-span output comparisons between the unchanged baseline kernel and
  cache hit/miss paths on all eleven authentic meshes, plus every individual bit
  mutation of a vertex, malformed counts, invalid identities, nonfinite palette,
  arithmetic overflow, budget exhaustion and eviction/invalidation cases.
- Independent Python scalar interpretation of pinned original Cg position/normal
  blending, four controlled palettes and all authentic vertices. This is formula
  evidence, not original Cg/GPU execution. Tolerance is 2e-5 absolute + relative.
- Independent scripted-frame/stage/counter/lifecycle/GPU-result admission traces;
  CPU clock rollback, saturation, malformed scope ordering and JSON-capacity tests.
- ASan/UBSan on every mesh. LeakSanitizer cannot inspect `/proc/task` in this
  execution environment, and its initial run failed before test execution. The
  successful sanitizer suite disables LSan and verifies module allocation/free
  balance directly. This limitation is recorded in the receipt.
- Android API 26 AArch64 shared compilation using the real NDK with no undefined
  symbols, plus ELF architecture verification. Compilation is not execution.

`evidence/qualification.json` records all results, source hashes and host-only CPU
timings. Timing includes test assertions and the documented comparison cost. No
timing threshold is asserted on an unknown CI host. The nonflaky regression
invariants are exact output parity, fixed admitted memory, zero warm allocations,
and only one source-kernel evaluation per vertex for 1,000 repeated identical
poses. The dynamic pose workload is measured separately and can be slower than
uncached execution because a miss retains source/palette bytes.

## Integration and rollback

These additions can be linked independently now. No live session or server is
required. The coordinator owns GL/JNI integration: attach frame/stage boundaries
to its new offline harness, copy existing renderer/asset/physics counters without
resetting their owners, and export the nested snapshot on its control thread.
Use ready-only asynchronous timer results if the actual GL driver exposes a
qualified timer extension; retain the unavailable marker otherwise. Never add
`glFinish`, synchronous readback or a blocking query to collect performance data.

Do not automatically enable the skin cache for continuously moving/blending
actors. First record real pose repetition, copy bytes and hit ratios. The cache
is most useful for repeated poses shared by actors, fixed simulation poses drawn
multiple times, paused animation or static previews. Configure small caps and
compare against uncached outputs before selecting it. Existing accepted CPU
skinning remains the fallback.

The local commit is confined to `native-android/engine/perf/`. Integrate only after
refetching native-android and checking concurrent paths. No old receipt or APK is
replaced. Disable the new harness adapter to roll back at runtime; remove/revert
this additive module only after downstream references are removed. Never reset
or rewrite branch history. Gates 25–27 are independent of this work.

Remaining: coordinator Android adapter, actual Android observer/cache execution,
hardware asynchronous GPU timing, emulator lifecycle testing and a consolidated
Thor test. Gates 44 and 45 remain open, and sustainable 30+ FPS remains a device
engineering target.
