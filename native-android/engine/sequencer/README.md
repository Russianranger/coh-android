# Gate 33: reusable sequencer simulation

Status: implemented and host qualified for the documented selection/timing
subset; Android ARM64 object built. Emulator, new-clip visual qualification and
physical Thor acceptance are pending. **This is not a passed full Gate 33.**

This opt-in C module adds an actor-independent data graph outside all accepted
APKs and gates 19–21. It does not change Huge grounded locomotion, animation
decoding, the Session Client, JNI, root builds, workflows or the conventional
client. The production implementation contains no character, move-name or
asset-path selection branches.

`coh_sequencer.h` is the public API. Immutable `CohSeqGraph` tables describe
original requirements, interruption groups, priorities, flags, next moves,
complex cycles, authored rate and interpolation metadata. Per-actor immutable
`CohSeqClip` bindings supply source asset identity, range and TypeGfx rate;
multiple rigs can share a graph. The simulation emits `CohSeqSelection`, while
the optional `coh_seq_sample` adapter calls the existing encoded-key sampler into
a caller-owned pose. No renderer or GPU state is stored here.

The module preserves these original semantics:

- Every required bit must be set; requirements retain their declaration order.
  `setSparseBit` appends unique bits, and the first declared bit anchors cached
  source candidate ordering. Sorting requirements would change priority ties.
- Interruption is the intersection of candidate interrupt groups and current
  memberships. A lower-priority move can interrupt a higher-priority current
  move when the graph permits it. Highest priority is chosen among valid
  candidates, with source anchor-bit/declaration ordering and incrementor ties.
- A changed move, changed state or force flag triggers a search. A force search
  with no candidate does not advance the current move.
- CYCLE/REQINPUTS releases use NextMove immediately, except FINISHCYCLE postpones
  release until the strict end. Exact `frame == last` remains on the clip.
- TypeGfx scale overrides move scale only when it differs from one. Source
  complex-cycle random selection uses a defined wrapping version of the original
  Windows LCG. PICKRANDOMLY receives the session's explicit qrand result.
- Source one-wrap cycling includes the very-short-clip fallback. Two ordinary
  cycles preserve phase only in the interior of the destination range; a
  complex source cycle prevents that preservation.

## Ownership, lifecycle and bounds

One simulation-owner thread owns each `CohSequencer`. Graphs, strings and clips
borrow caller storage and must remain immutable while consumed. Initialization
validates bounds once. Loading/caching is the asset module's responsibility;
this sequencer never reads a file, decodes an asset or allocates heap storage.

If the asset owner's original clip duration is unknown, its binding stays
`ready=0`. Entering it returns `COH_NOT_FOUND`. An unimported original NextMove
is `COH_SEQ_NONE` and returns `COH_UNSUPPORTED`. Both leave actor and output
unchanged. Load off the simulation thread, prepare a new validated binding table,
call `coh_seq_rebind_clips` between steps and retry. Release older storage only
after all actors have rebound. Cancellation is polled once before any mutation.

The graph admits up to 4,096 moves, 876 original state bits, 12 requirements per
move, 448 interruption bits and five cycle targets. Final equal-priority ties
are limited to 100 rather than permitting the original fixed candidate array
to overflow. Larger *lower*-priority tie sets do not hide a later winner.
Search scans the graph once and orders at most 100 winners. Unchanged state and
move skip the search. A host actor occupies 216 bytes; candidate scratch is at
most 400 bytes plus a bounded actor/output copy. Graph/clip storage is separately
caller owned. Counters expose steps, searches, candidates, transitions and loops.

Ticks are explicit source frames at 30 Hz, bounded to [0,3] per call; caller
supplies the already computed actor-size/MoveScale factor. Pause/resume must not
replay a lifecycle backlog. Destroying actor storage after producers stop has no
external cleanup, allocation or GPU action. Preserve logical simulation across
Surface recreation and rebuild rendering resources independently.

## Qualification

Run from any directory:

```sh
python native-android/engine/sequencer/tools/check.py \
  --output /tmp/coh-sequencer-qualification \
  --source-root /path/to/repository-containing-upstream \
  --sanitize \
  --android-clang /path/to/aarch64-linux-android26-clang
```

`--source-root` also accepts the original `ouroboros` directory. `--asset-root`
can override its sibling `i24` directory. With no source root, the bundled,
hash-pinned metadata fixture and ordinary tests still run, while the report
explicitly states that original-kernel execution was not performed. No tests
write outside the selected output directory or alter accepted fixtures.

The recorded run in `qualification/host-qualification.json` passed 1,848,320
checks, including 89,111 comparisons against unedited original functions,
30,000 bounded malformed graph/clip mutations and one million steady-state
steps. The trace suite tried 100,000 source-graph updates using male and Huge
binding sets; all twelve moves whose source explicitly declares both clip ends
were visited in each set. Six moves with unresolved original durations remain
unavailable. Across source traces 10,909 unavailable clip/link updates failed
without advancing state. ASan/UBSan passed. LeakSanitizer could not scan this
executor's `/proc` task view; ASan/UBSan remained enabled, and `nm` independently
confirmed no heap allocator, mutex or file-I/O dependency in the module object.

The million-step host timing is only a microbenchmark. It measures no skinning,
rendering, network, device thermal behavior or game FPS. Android evidence is an
API26 ARM64 object compilation, **not** emulator execution or a test APK.

## Remaining Gate 33 requirements

The 18-move reference graph includes jump, fall, kick combat, emote and a
knockdown-cycle family. Its ranges, paths and graph behavior are authentic source
metadata; the new non-ground `.anim` bytes have not yet been admitted by the
qualified raw decoder. Source timing checks are not evidence that the new
motions render correctly. The optional sampler adapter's integration test uses
an explicitly synthetic one-bone rig; no non-ground visual parity is claimed.

Still required: complete graph import and closure (including Ready's random idle
graph), original clip discovery/durations, qualified male/female/Huge encoded
clips and skeleton mapping, original per-bone transition blending, root motion,
attachment conventions and registration flags, PlayFx/child-output routing,
ragdolls, network-triggered states and authoritative reconciliation. Interpolation
and all source move flags are emitted for adapters but their visual/gameplay
side effects are not implemented in this simulation. TypeDef fallback is supplied
by the asset owner; the test's Huge-to-male binding fallback is a fixture choice,
not a qualified general TypeDef resolver.

## Integration and rollback

1. Review/cherry-pick only the worker's scoped commit after re-fetching
   `native-android`. Build this module with the unchanged accepted
   `native-android/animation/coh_animation.c` and `libm` in a coordinator-owned
   opt-in target. Its public error values use the shared ABI1 `CohStatus`.
2. Worker A supplies validated immutable clips and retained asset ownership.
   Animation/game-session code supplies original graph bits and explicit source
   clocks; Worker B consumes poses through a coordinator-owned rendering adapter.
   Audio/FX and UI observe selection/transition events through session bindings.
3. Keep accepted Huge locomotion on its existing execution path. Add a separate
   opt-in actor in one consolidated probe only after its new raw clips, blend
   adapter and graph closure pass independent references. Never replace the
   live gates 19–21 adapter while that agent is qualifying it.
4. Qualify Android execution, Surface recreation, pause/resume, input state,
   interruption timing, source-comparable poses and memory over a sustained
   session, then consolidate the meaningful new motions into a Thor test.
5. To roll back, disable the opt-in coordinator adapter and additively revert this
   module's integration commit after inspecting consumers. Do not reset history,
   change other branches, erase receipts or replace the previously qualified APK.
