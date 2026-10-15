# Read-only audit and remaining optimization order

Audit baseline: detached worktree commit
`218b576a184a2807ca655e4b4a4c13d348277455`. Source hashes are in
`source-pins.json`; the qualification driver verifies them before testing. It
pins the immutable original source from `upstream/ouroboros` and `upstream/i24`
separately from this worker's read-only native sources. The existing Gate 6 audit
identifies its source lineage as `0b75ade0c801735e10c5798f641948a45cc50488`.

## Findings

| Area | Evidence from source | Implication |
|---|---|---|
| Accepted CPU skinning | Session `skin()` samples directional locomotion, builds each part's palette, then calls `coh_mesh_skin_vertex()` per vertex every render iteration. The kernel validates all palette floats per vertex. | Repeated exact poses repeat work. A wrapper can reuse exact outputs, while GPU palette skinning or bulk validation requires a separate source-parity gate. |
| Source deformation conventions | Original `rt_bonedmodel.c` has a software `DeformObject` path and bone upload. I24 `functions.cgh` uses two-bone lerp and normalized blended normals. | Retain the accepted GPU-contract normalization; original software fallback is not an interchangeable normal oracle. The new cache calls the accepted kernel unchanged. |
| Accepted Session geometry | Initialization owns source, deformed vertices and indices. `geometry_upload()` uses `glBufferData()` for the actor geometry each frame; static world geometry is created initially. | Dynamic geometry transfer bytes and present/submit duration should be counted separately before adopting another GPU update strategy. |
| Generalized renderer | `coh_renderer_gles.c` uploads both vertex and index data with `glBufferSubData()` per submitted draw into reusable buffers. The core sorts contiguous opaque runs using constant-storage heapsort and preserves translucent order. | Resident immutable index/geometry buffers can reduce transfer and driver work. Do not reorder translucent draws or claim draw-call merging from material sorting alone. |
| Shader lifetime | The renderer core owns a bounded lazy LRU for three material families; GLES recreates handles per Surface generation. | Existing shader caching should be observed and extended when variants grow, not duplicated. Program-binary caches require driver/ABI/source fingerprints and a recompile fallback. |
| Asset cache | Loader already uses indexed path lookup, bounded tracked allocations, unpinned LRU eviction and generation-aware identities. Existing map streaming pre-admits byte budgets. | Feed existing stats to the observer. Another unconstrained asset cache would duplicate memory and hide ownership. |
| WALK collision | `coh_walk.c` prepares triangles once and tests AABBs in a bounded linear scan before the accepted narrow phase. It already counts queries, triangle tests and hits. | Worker B can reduce candidates with spatial indexing; this worker only adds counters to consume its measured results. Existing narrow-phase/tie behavior stays unchanged. |
| Animation state | Existing sequencer scans a bounded move graph with no heap allocation in step operations; pose sampling and socket palettes are independent of GPU execution. | Stage timings must separate state selection, palette construction and deformation. Caching by approximate frame alone would be incorrect for morph/blend/rig changes. |
| Diagnostics | Accepted startup witness paths use transform feedback, mapped buffers and readbacks. They are correctness witnesses, not steady-state performance timers. | Tag startup separately; exclude it from ordinary gameplay percentiles. Do not remove correctness evidence or report it as steady-state render overhead. |
| Original collision profiling | `gridcollperftest.c` records dynamically growing collision records and cache counters. | Reuse the measurement categories but retain bounded fixed-storage snapshots on Android. No original desktop recorder is injected into the hot path. |

The original desktop engine's shader/bone/VBO cache code is provenance and design
context. This module does not claim its new histogram/cache policy is an original
game algorithm.

## Ranked next work

These rankings are engineering priorities based on the audit, not measured Thor
speedup estimates. Work can proceed independently of networking except where
representative full-game workloads are required.

| Rank | Work | Benefit to verify | Cost/risk and acceptance |
|---|---|---|---|
| 1 | Connect the fixed observer to the consolidated offline harness; record CPU frame/stage, transfers, asset and collision counters. Add a bounded ready-only GPU timer adapter if supported. | Identify CPU/GPU/present/streaming limits with actual device data. | No inferred GPU times, no forced synchronization, lifecycle scopes dropped correctly. Compare observer enabled/disabled overhead on Thor. |
| 2 | Evaluate the supplied exact skin cache for static/shared/repeated poses. | Deterministically avoid redundant kernel vertices and output uploads when bytes are identical. | It retains duplicate source/palette/output storage. Use small budgets; dynamic-pose misses can cost more. Require exact output and measured hit/copy ratio. Do not enable globally by assumption. |
| 3 | Add coordinator-owned resident immutable geometry/index buffers keyed by geometry identity, generation and Surface. | Lower redundant index/static vertex upload bytes in the generalized renderer. | Bounded GPU budget, no stale Surface handle reuse, evictions on GL thread; transform feedback/pixel parity and recreate tests. |
| 4 | Qualify source-accurate GPU palette skinning using the existing two-bone source contract. | Reduce CPU deformation plus vertex transfer for many animated characters. | Preserve precise source operation order, normal normalization, attachment palettes and CPU fallback. No accepted kernel replacement until GPU/source parity and Thor measurements. |
| 5 | Connect Worker B's spatial candidates to collision counters and representative map traces. | Reduce candidate/narrow-phase work as maps grow. | Source narrow phase and original triangle ordering/tie handling remain authoritative. Compare grounded/wall/jump traces before enabling. |
| 6 | Observe asset-cache byte/entry budgets and streaming visibility with larger real packs. | Reduce decompression churn and avoid resident growth. | Existing cache already bounds memory. Count pinned bytes and eviction churn; test constrained budgets, lifecycle and interrupted loads. |
| 7 | Extend shader cache only for actually needed material variants and qualify optional program-binary reuse. | Avoid repeated compilation on startup/Surface restore. | Version/source/driver fingerprints, checked binary length/format and safe source recompile fallback. Do not report compile-time savings without device measurements. |
| 8 | Reuse full poses/palettes across genuinely identical rig/morph/animation/blend inputs. | Reduce animation and socket work across instances. | Pose key must include all dependencies; validate byte/output parity. Approximate frame-only caches risk visual regressions. |
| 9 | Reduce per-frame Session structure copies and upload span width in a future coordinator adapter. | Lower CPU copied bytes when more actors/UI/world systems accumulate. | Current copy protects driver calls from shared session locks. Preserve cancellation, input responsiveness and lifecycle ownership. No speculative mutex removal. |
| 10 | Add long-duration physical CPU/GPU/memory/audio traces under representative load. | Validate 30+ FPS, frame-time variance, thermal sustainability and bounded resources. | Needs larger maps/characters/audio and eventually live gameplay. The current bounded scene and host fixture timings cannot establish full-game performance. |

No benchmark in this module establishes a speedup for full Atlas Park, a live
native session, physical Adreno rendering or sustained battery/thermal behavior.
