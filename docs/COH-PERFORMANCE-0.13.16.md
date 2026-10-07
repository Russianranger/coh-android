# 0.13.16 client scene and frame performance continuation

This pass starts from continuation commit
`f346ccd3e2979dc12369de9c31f97e418745cb8f` and the exact audited, physically
tested 0.13.15 APK at `d31685579a04307c38356918a81a22997a858c83`.
The accepted Wine/FEX/Mesa llvmpipe stack, 800x600 presentation, Performance
preset, 10 FPS cap, controls, persistence, UI/GEO/beacon payloads and server
binaries remain preserved. This is Game-only native performance work; no
renderer experiment, asset reimport, beacon generation or zoning is included.

## Physical 0.13.15 baseline

Both exported 2026-10-06 Thor runs passed loaded-world native readiness,
character reopen, committed save and owned cleanup. The user reports greatly
improved startup: 13 minutes first run and 11:30 second run. The bounded report
and exact support-ZIP pins are in
`android-evidence/performance-0.13.15-thor-20261007.json`.

| Phase | 0.13.14 | 0.13.15 first | 0.13.15 warm |
| --- | ---: | ---: | ---: |
| Reopen to observed login | 19:10 | 11:37 | 9:53 |
| Reopen to observed world | 20:34 | 13:02 | 11:18 |
| DbServer stage | 8:59 | 1:10 | 1:02 |
| Server preparation, nested in preceding stage | 8:28 | 0:40 | 0:33 |
| Local Atlas startup | 3:19 | 3:56 | 3:23 |
| Actual client startup | 3:19 | 3:24 | 3:23 |
| Visual preparation | 1:10 | 1:10 | 0:32 |
| Client map connection to loaded-world native CLIENT_READY | — | 75.330 s | 77.793 s |

Both 0.13.15 runs reuse compatible server key `d3f6b18b9ea8bf59a848686a`
with zero new links/copies. Neither regenerates the native graph or repeats
geometry cache removal. Warm visual preparation reads/hashes/decompresses
zero payload bytes; metadata checks still take approximately 32 s. These facts
physically close the 0.13.15 cache-reuse milestone. Observed world markers
differ slightly from manually observed playable entry; neither interval is an
already-measured zone transfer. Nested phases and observer durations are not
added to containing startup totals.

The warm client connects to ready Atlas at 18:54:34.894 UTC and native
CLIENT_READY is recorded at 18:55:52.687 UTC. This 77.793-second interval
excludes character selection. Existing BIN profiles after connection account
for approximately 16.982 s across recorded open/freshness/decode intervals;
they do not explain the remaining wall interval. Before menu readiness,
freshness checks account for approximately 84.094 s of recorded intervals,
with FX, NPC, mapstats and LOD inputs dominant. Android delivered frames do
not measure native client frame times or establish a GPU/CPU bottleneck.

## Implemented native loading optimization

The stock `gfxReload` path calls `gfxTreeInit`, which initializes the character/
FX tree and preloads FX geometry. The following group/model invalidation frees
that just-loaded model cache; `gfxReload` then performs its required final FX
preload. The candidate's producer-gated opt-in defers only the preload whose
cache is discarded. Both invalidations and the surviving mandatory FX preload
remain. Ordinary tree initialization and default/fallback APIs retain stock
behavior; the separate final startup FX preload is also retained.

The old warm log's first/second FX markers are 10.424 s apart during scene entry
and 18.195 s apart during initial startup. These intervals include teardown
operations that are preserved, and the surviving preload may encounter colder
inputs. They are candidate cost segments, not guaranteed physical savings.
Actual 0.13.16 before/after scene and aggregate reload time remains a Thor test.

Native call-order fixtures compare unload modes and empty/populated FX
inventories, default/opt-in behavior and subsequent ordinary initialization.
Source reconstruction preserves network waits/failures, CRC/count checks,
group reset, collision/physics and all geometry/texture completion operations.

## Lightweight native measurements

`COH_CLIENT_SCENE_PHASE_V1` JSON records time actual graphics-tree reset,
group/model invalidation, surviving FX preload, group/library/reference loading,
collision/physics, entity loading, geometry completion, texture completion and
CLIENT_READY queuing. Records use fixed phase names, no resource paths or
per-frame prints, and a hard 128-record limit per translation unit. Parent
network/processing phases contain subphases; do not sum them twice.

`COH_CLIENT_FRAME_TIMING_V1` JSON records aggregate approximately ten-second
windows using the actual Win32 performance clock. Main-loop windows distinguish
menu/loading/gameplay/mixed states and measure entry intervals, bracketed wall
work, engine work, submission/backpressure and intentional pacing. The render
thread measures present-function intervals and actual `SwapBuffers` wall time.
These are not GPU completion or Android/RFB display-latency measurements.
Main/render thread CPU deltas are sampled only at window boundaries and exclude
llvmpipe/Wine/FEX worker CPU.

Each stream is thread-local, uses fixed histograms and bounded buffers, performs
no per-frame allocation/logging, and emits at most 120 records. Reports are
assembled as one complete bounded JSON line to avoid main/render interleaving.
Clock/format failures stop diagnostics without stopping the game. Histogram
p50/p95 values are bucket upper bounds; overflow is null. The final partial
window may be absent. The exact verified Game producer enables these controls
on both initial and owned retry launches. Old/unknown producers do not inherit
them. Shared Wine/server environments are untouched.

For this producer, bounded scene/frame measurements replace the legacy
per-resource BIN profiling output (2,275 lines in each baseline run). Only
diagnostic output is suppressed; known-length copy optimization, metadata
dependency preload, source freshness, CRC and failure checks remain enabled.

The bounded `tools/android/interactive/analyze_client_scene_performance.py`
reduces a complete support ZIP into startup, native scene-entry and separate
main/presentation frame summaries. It rejects corrupt/interleaved JSON,
duplicate keys, invalid sequence/budgets, nonfinite values and inconsistent
histogram/percentile/stutter counts rather than inventing measurements.

## Ranked candidates and deliberately deferred work

| Candidate | Expected benefit | Risk / decision |
| --- | --- | --- |
| Defer discarded FX preload in gfxReload | Avoid redundant model preparation at startup and scene entry | Moderate native loading risk; implemented with exact surviving-state fixtures and fallback |
| Replace thousands of BIN prints with bounded native phase/frame aggregates | Reduce diagnostic contention and make stalls attributable | Low; diagnostic policy only, correctness checks retained |
| Native frame/queue/pacing diagnostics | Select a measured FPS optimization | Low bounded overhead; implemented, physical results pending |
| Extend metadata preload to FX/NPC/mapstats/LOD | Initially appeared promising for 84 s freshness cost | Rejected this pass: actual retained BIN inventories prove dependencies already belong to trees stock FolderCache scans; another preload duplicates work |
| Skip repeated thread-priority writes | Possible Wine-call reduction | Rejected this pass: development-data mode may bypass the path already; no proven reachable benefit |
| Change cap, resolution, renderer or pacing | Potential frame-rate change | Deferred until native measurements; accepted profile remains intact |
| Offload Android capture PNG work | Potential periodic display-stutter reduction | Current code performs scan/encode/hash on the UI thread, but reports lack cost timings; preserve mandatory evidence and ownership boundaries pending a separate measured change |
| Broader shared-memory, resource-format or texture/physics changes | Potentially larger loading gains | Deferred; requires separate native correctness/coverage qualification |

## Qualification and focused Thor acceptance

The candidate lane builds the actual current Win32 Game through all accepted
source layers plus the reviewed scene/frame patches. It runs genuine Win32
clock/CPU/TLS and concurrent JSON-emission checks, then retained gameplay/UI/
beacon/persistence/recovery suites and all seven real PostgreSQL fixtures.
Only Game changes inside the retained client runtime; all 20 dependencies are
byte-identical. The outer APK retains server, asset, cache, DEX/resources and
renderer payloads, with only the client runtime, four typed diagnostic/migration
helpers and two manifests replaced. Warm client migration verifies the exact
previous producer and rebinds the unchanged texture inventory to the new Game;
server cache identity and character data remain preserved.

Publication is gated by full SDK/signer/source/inner-and-outer-payload auditing
in a fresh process and a separate read-only audit of the actual public APK,
checksum and testing notes. Completed source/run/tag/hash evidence will be
recorded in HANDOFF and
`android-evidence/performance-0.13.16-publication.json` after actual gates pass.
Hosted fixtures do not establish physical FPS or elapsed scene-time gains.

Follow `COH-Atlas-Gameplay-0.13.16-testing.txt`: first update and warm startup,
then thirty-second standing/walking/camera/population/combat/UI/objective
activities with local start times. Preserve ordinary save/logout/Finish and
export the complete outer ZIP after each run. The next report must establish
which native frame budget or resource phase is limiting performance; a
sub-30-second zone-transfer result is not claimed by this Atlas-only pass.
