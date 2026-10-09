# Thor .22 regression reviewed; .23 session repair and timing isolation — 2026-10-09

**First qualification passed; host-only receipt correction is ready. .23 is
not yet published.** Initial .23 source `d2e686582f493b6951eff4ad44b50b269081cabc`,
owner `37963422463`, passed all 107 suites / 1,556 tests / zero skips, including
all seven real PostgreSQL fixtures. Packaging stopped before writing an APK:
the new contract check compared JSON insertion order against a sorted
qualification record. Sorted typed comparison and a fresh-reader regression
repair that check without changing guest or native bytes. The new owner must
qualify its own source; no completed native Game build is repeated or relabeled.
Recovery
verified branch/head `71fca3f0679bc102f70297bbad395d1de5cacc6e`, open draft
PR #1 and main at `04d62616e2e1b41b10f35a04d4c798e43680d5ba`. No newer remote
work or active owner build was found. The pruned accessible workspace contained
no previous checkout or local build; a clean clone recovered the exact branch.
The current public APK remains .22 until the new owner completes publication.

The user reports .22 FPS worse and no walking after world entry, while clicks
and camera rotation work. Screenshot: 4.86 FPS / 205.8 ms. The attached export
confirms the published .22 Game and actual Zink / Turnip Adreno 740, GL 4.3 Mesa
22.3.6. GPU startup remains successful. Pure 30-cap gameplay windows measured
152.044 ms / 6.577 native cadence Hz across 2,192 frames / 333.294 seconds.
Main CPU averages 43.335 ms/frame; viewport wall averages 119.111 ms. Routes and
input availability differ from .21; this is not a matched performance experiment.

Movement is blocked by `character_session_budget_rejected`. Presentation-ready
+35 minutes ends at 16:40:51.426 UTC, but launcher +34 minutes emitted
16:40:53.901. Preparation lasted 62.475 seconds, exceeding the prior one-minute
allowance by 2.475 seconds. Android retains revision zero, so walking/Jump/save
are gated while pointer input remains open. The correction caps the guest at
the owned presentation clock as well as launcher/operation limits. It shortens
deadlines and preserves Android's strict guard, neutral and save reserves.

The inherited startup-only policy does not itself block movement or saving.
Its status wording remains misleading, but normal Save/strict committed proof/
Finish are supported when the budget is accepted. Keep this policy to preserve
tasks and avoid repeating the authored-task gate. The failed .22 test requested
no save; cleanup completed and no fatal native exception was observed.

.23 Reopen disables the added detailed pipeline timing after the typed current
Game gate, retaining earlier frame/scene/renderer counters. The exact .22 Game,
wakeup repair and completed original Windows proof are reused; no native or
GPU/probe build is repeated. Authenticated artifacts show identical .21/.22
optimized flags/toolchain. Scene CPU, hidden full-ring waits and instrumentation
cost remain unresolved. The next short test isolates added timing cost before
another native optimization; no FPS recovery or stable30 claim is made.

Three guest helpers change for .23. The nineteen authored Java sources, DEX,
resources, twenty DLLs, assets/resolution/effects, GPU archive/probes, Software
fallback, servers, Wine/FEX, prepared cache/schema and save acceptance remain
retained. Existing .21 physical GPU improvement and fidelity observations are
completed milestones, not invalidated by this separate .22 regression.

Evidence: `docs/android-evidence/session-repair-0.13.22-thor-20261009.json`;
implementation and interpretation limits: `docs/COH-PERFORMANCE-0.13.23.md`;
focused test: `docs/COH-Atlas-Gameplay-0.13.23-testing.txt`.
The exact next milestone is accepted walking/Jump/save authorization and a
90-second GPU standing/camera/walking route with RP timing disabled on the same
Game, ordinary Save/Finish and complete outer export. If FPS stays poor, measure
scene/sort/submission and full-ring blocking before choosing a native change.
Startup and zoning remain deferred; do not request another long Software run.

Earlier published checkpoints below remain history.

# Published render-worker continuation and completed Thor GPU milestone — 2026-10-09

**Current test APK: 0.13.22 / version code 37, published and independently
public-audited. All five publication jobs passed.** Frozen APK/runtime source:
`b8ea2e6c7edf67e5ffa8dc30d05d6f516930550e`. Actual Game build source:
`5af0e27ccf6fbb53d5b3ff5c2c2f3bf5a1d58396`, original Windows/native owner
`37924638566`; publication/qualification/public-audit owner `37928364819`.
Game was built once and reused without recompilation or relabeling.
Development remains on `codex/character-persistence-continuation`, draft PR #1;
main remains behind at `04d62616e2e1b41b10f35a04d4c798e43680d5ba`.

[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.22/COH-Atlas-Gameplay-0.13.22.apk)
· [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.22)
· [Publication qualification/public audit](https://github.com/Russianranger/coh-android/actions/runs/37928364819)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.22/COH-Atlas-Gameplay-0.13.22-testing.txt).

APK 1,560,308,488 bytes; SHA-256
`cae5d5700ef4f2d8a054709024a11263ec2fe442255554b4b68f3f28dc79876c`.
Release 407889321, APK asset 624900486; direct tag resolves to frozen APK source.
Signer remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
Game 9,494,016 bytes; SHA-256
`1953fa3ed1bee3dcdecaed14ccd369730a13bc4addf06ddfc283f7f6f9211b72`.

**1,527 tests / 105 suites / zero skips**, including all seven real PostgreSQL
fixtures, passed. The original actual Win32 Game build and native guard checks
passed; the recovery independently recomputed its native source recipe and
validated the original Game/CMake/Windows proof. Fresh-process SDK 35 version,
signature v2/v3, exact typed/canonical nested package, source/ancestry, payload
and donor-conservation checks passed before publication. A separate job
independently downloaded the public APK, checksum and testing notes and repeated
those audits. Exact original/current owners, artifact/container/member pins and
publication evidence are in
`docs/android-evidence/render-pipeline-0.13.22-publication.json`.
The separate local download also passed whole-file API pins, full typed/canonical
actual Game wrapper, original native artifact/CMake/Windows proof, 70/77 payload
conservation, all 19 Java sources/DEX/resources/20 DLLs, binary manifest version-only
change, and independently reconstructed outer provenance. Its complete result is
embedded in the publication receipt (raw result 12,036 bytes, SHA-256
`00d5f1f6536e630cf380fdd5ee2c05b54cc4610c59446b0deb00703dab093316`).
Local auditing did not reverify SDK signing or rerun Windows proof executables;
those checks passed in their recorded hosted jobs.

The continuation fixes a concrete render-worker event race: declaring sleep
after resetting the event and checking an empty queue could miss a producer's
wake. The consumer now arms sleep before reset/recheck and clears it after
finding work or returning from the wait. Queue order, draw commands, buffering
policy and unthreaded/full-queue behavior stay intact. Bounded new
`COH_CLIENT_RENDER_PIPELINE_V1` records separate main graphics phases, explicit
queue-flush waits, sampled active render-command wall time and gaps. No blocking
GPU query or glFinish is introduced. Main phase overlap, CPU/window scope and
independent renderer sampling remain explicit; command execution can include
driver blocking and gaps can include scheduling/producer waits.

**0.13.21 GPU Game startup and observed improvement are completed device
milestones.** The user reports regular 15–30 FPS, occasional lower dips,
substantially smoother gameplay than Software and no observed fidelity loss.
The supplied `coh-atlas-gameplay-20261009-111411.zip` confirms actual Game
`zink (Turnip Adreno (TM) 740)` / OpenGL 4.3 compatibility Mesa 22.3.6, successful
Android/guest completion, SQL/position/powers/costume, reopened identity and
cleanup. Keep these observations separate from the following log measurements.
Do not repeat the .21 WGL repair or an unchanged long Software benchmark.

Conservatively classified pure-gameplay 30-cap windows contain 5,196 samples
across 271.141 seconds: mean interval 52.189 ms / 19.161 native cadence Hz,
p95 histogram upper bound 125 ms, maximum 349.706 ms. Native cadence is neither
display refresh nor pure GPU completion or a controlled route comparison.
Main work averages 48.951 ms with 18.008 ms main CPU/frame. Slow renderer windows
have 53–69 ms non-swap batch wall time but only 6–7 ms renderer CPU; batches
include queue-idle gaps. About 3 ms swap, zero readback, small selected uploads
and 2.675 ms mean Android capture freeze do not explain the dominant native
cost. Capture encoding can compete for CPU. Existing evidence does not isolate
scene CPU, driver/GPU execution or queue synchronization as the remaining
limiter. Exact records, source/backend/report pins and limits are in
`docs/android-evidence/renderer-sync-0.13.21-thor-20261009.json` and
`docs/COH-PERFORMANCE-0.13.22.md`.

Recovery initially verified branch/head `75cc2947b180f34bb5c2ef8857bdfaf367ba85ef`,
main, tags/releases, draft PR #1 and all six successful .21 jobs; no newer work
or active COH build was present in the accessible workspace. That does not
establish the state of an inaccessible former workspace. The first .22 owner
completed the native build but qualification stopped because a shallow checkout
lacked the parent commit required by a retained routing test; it built/published
no APK. The host-only recovery adds history and an exact administrative routing
lane, authenticates the completed artifact and preserves its original metadata.
Local preflight passed all 1,527 tests but lacked seven PostgreSQL fixtures;
those fixtures then passed in the authoritative hosted qualification.

Exactly 70 of 77 runtime payloads stay byte-identical to the accepted .21 donor;
only Game's archive, four typed integration helpers and two manifests change.
All 19 Java sources, DEX/resources and 20 native DLLs stay exact. The working
GPU archive/probes, Software fallback, resolution/assets/shaders/features,
Android UI/controls/capture, servers, saving, character persistence, Wine/FEX
and prepared cache/schema remain retained. No Mesa/probe rebuild, asset
reimport, visual-feature reduction or save-rule relaxation occurred.

**Remaining uncertainty:** .22 has no physical FPS, temperature, visual or
control validation yet. Stable 30 FPS or better is the target, not a claim.
Startup and zoning remain deferred.

**Exact next milestone:** install .22 as an update, run Set up / update runtime
once, select GPU test before Reopen, keep the successful .21 800x600 Performance
preset/fan/charging state, select Show FPS and 30 FPS, and settle ten seconds.
Use about thirty seconds each standing, camera rotation, populated walking and
new-scenery approach, with ten-second gaps and segment/FPS/temperature/visual
notes. Save normally, wait for Saved character verified, Finish and export the
complete outer ZIP. Use its frame/phase/queue attribution to choose the largest
remaining rendering cost toward sustained 30 FPS. Only a GPU regression calls
for a short cleanup-proved Software fallback check. Earlier checkpoints below
remain history.

# Published Thor GPU-start repair — 2026-10-08

**Current test APK: 0.13.21 / version code 36, published and independently
audited. All six owner jobs passed.** Frozen APK source:
`20b559420b1bb0978b7eac6e6eecdfe2a468f693`; retained Game source:
`a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4`.

[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.21/COH-Atlas-Gameplay-0.13.21.apk)
· [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.21)
· [Owner qualification/public audit](https://github.com/Russianranger/coh-android/actions/runs/37837207655)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.21/COH-Atlas-Gameplay-0.13.21-testing.txt).

Release 407231536; APK asset 622911506. APK 1,560,283,912 bytes; SHA-256
`67a8fe01d8f6e7cbb5139d7d1cecc7706d33b25671d0072a93808b1fc04bbe76`.
Tag `coh-atlas-gameplay-v0.13.21` resolves directly to the frozen APK source.
Signer remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
The independently downloaded public APK passed SDK 35 package/version 36,
signature v2/v3, exact source/payload/retained-producer and donor conservation
checks; public checksum and testing notes were also downloaded and verified.

**1,470 tests / 99 suites / zero skips**, including all seven real PostgreSQL
fixtures, passed. Actual Windows PE32 production compilation and native guard
qualification passed with `/W4 /WX`. The earlier unpublished candidate at
`cbb62e7730c00914b2ad53cc79c96dbc8a337ec0`, run 37836795752, stopped at MSVC
C4701 on an uninitialized rectangle in a failed client-size query. Initializing
that rectangle preserved rejection behavior and fixed the production build;
no APK was published by that failed candidate.

Exactly 73 of 77 runtime payloads remain byte-identical; four helper/archive/
verification payloads change. Two reviewed Java evidence validators and DEX
change; seventeen authored Java sources and Android resources retain exact
bytes. Game and 20 DLLs, Turnip/Mesa/native Vulkan, servers, assets, Wine/FEX/rootfs,
display/input and strict save rules remain retained. No Mesa or native Game
recompilation occurred. All original GPU producer source/ABI proof stays
explicit in the probe-only repair receipt. Machine-readable publication,
input ZIP hashes, asset pins and evidence artifact IDs/ZIP digests are in
`docs/android-evidence/gpu-repair-0.13.21-publication.json`.

The physical .20 Software export measures 9.382 native Hz in 30-cap gameplay;
its guest save/reopen passes, while Android completion was falsely rejected
by the legacy 1210-second cap. Production-method replay now accepts only the
matching Android-approved bounded native budget. The physical GPU export
never starts Game; it passed driver/draw prerequisites and failed post-swap
GL_FRONT proof, then masked the original error on background-pipe cleanup.
The repaired visible two-pattern gate and cleanup retain all capability/
identity/safety boundaries. These are automated fixes, not physical .21
Game/GPU or performance validation.

One historical .13.4 recipe run 37836795523 rejected the newer two-Java boundary
against its frozen one-Java allowlist. Its regression guards pass in the .21
qualification; that old recipe was preserved, and no .13.4 APK was rebuilt.

**Next:** install .21 as an update, run Set up / update runtime once, select
GPU test before Reopen, and export the full outer report after failure or
Save/Finish. No clear-data/reimport and no repeated long Software benchmark.
If Atlas opens, corroborate actual Game hardware backend, use the matched
30-cap route, inspect material/input/combat/UI/save correctness, black tearing
and temperatures. Actual GPU Game FPS, visuals and black-glitch resolution
remain unverified; stable 30+ FPS remains the target. Continue from the test
evidence rather than repeating this completed release. Startup/zoning remain
deferred. The prepublication source checkpoint below is retained as history.

# Thor GPU-start failure repair — 2026-10-08

**0.13.21 candidate / version code 36; publication not yet claimed in this
source checkpoint.** The user's new .20 exports establish unchanged Software
performance and a failed GPU preflight before Game starts. Resume this narrow
repair; do not repeat .20/Mesa/Game builds or the unchanged Software benchmark.
Read `docs/COH-PERFORMANCE-0.13.21.md` for exact report hashes and measured
boundaries, and `docs/COH-Atlas-Gameplay-0.13.21-testing.txt` for device steps.

The GPU report passed Adreno 740/Turnip native queue and Wine WGL draw/texture/
ARB/VBO/FBO checks, then returned exit10 at GL_FRONT post-swap readback.
Background Wine output holders masked that original error during generic
shutdown. The helper now finalizes the isolated prefix, owned token workers
and EOF before classifying the failed leader, retains the raw original
failure, and permits fallback only with proven cleanup. Ordinary WGL timeout/
malformed/local output-bound rejection follows that proof; cancellation,
health/global output/deadline failures remain fatal. The real WGL V2
presentation gate requires two different actual screen-pixel patterns;
GL_FRONT remains diagnostic. No full Game/GPU or FPS claim is granted by it.

The Software guest strictly verified save/reopen/SQL/powers/costume but Android
rejected its valid 1304.498-second current-session observation against a legacy
1210-second cap. Two reviewed Java validators now require the guest budget to
match Android's already-approved native session/PID/time receipt and bounded
monotonic deadline. Save/producer/payload/current-APK checks stay strict.

The new probe-only package/build workflow retains the exact audited public
.20 donor APK, 73 of 77 outer runtime payloads, Game and 20 DLLs, Mesa/Turnip/native
Vulkan probe, assets, servers, Wine/FEX/rootfs, display/input and signing
identity. Only small WGL PE32 compilation, two Java validators/DEX, GPU helper,
GPU archive and verification/version metadata change. The old producer source/
ABI receipts remain explicit; no new driver/native Game compilation occurs.

**Release gates:** `.github/workflows/android-client-gpu-repair.yml` compiles
production Win32/WGL, packages the retained driver with the repaired probe,
runs all 96 retained suites plus 3 new/continuation suites with 7 real PostgreSQL
fixtures, builds/signs .21, audits before publishing, then independently
redownloads and audits the actual public APK. Record final owner source SHA,
run, release/asset/APK pins and zero-skip totals after all jobs pass. Existing
.20 and earlier publication evidence below remains preserved.

**Next physical milestone:** GPU preflight then actual Game renderer/Atlas
correctness and matched 30-cap route. Use actual frame cadence and renderer/
presentation costs to choose the next optimization. Black tearing remains
unresolved; do not promise 30 FPS or infer hardware Game rendering from probes.
Keep startup/zoning deferred and preserve character/imported data.

# Interrupted-session recovery and renderer report analysis — 2026-10-08

**Device APK remains the completed, published 0.13.20 below.** Recovery found
one clean working tree at `883effea98e4527eef6287af5f62e89ecb777838`, no stashes
or unfinished local APK, and no newer release or active release build. Live
GitHub release/tag/assets and all six jobs of owner run **37788954170** agree
with the existing audited publication. The two failed GPU recipe candidates
were already corrected before publication. No implementation, driver build,
Game compilation or APK publication needs to be repeated for that milestone.

The subsequent work is host tooling: a reusable bounded
`tools/android/interactive/analyze_client_renderer_performance.py`, focused
measurement/evidence tests and a read-only report-analysis CI job. It separates
stable native cap windows from transition/unclassified coverage, keeps renderer
and presentation streams unaligned, and includes GPU prerequisite/fallback versus
actual Game backend evidence, capture costs and strict save failures. See
[report analysis](COH-RENDERER-REPORT-ANALYSIS.md) for usage and measurement limits.
The complete latest `.19` ZIP was available and matched its already recorded
`592f0be66bf6da1eace77f5e7e13df9c5e5d2c051410cddcde4c99e8cd75dcea` hash.
All **19 report tests** passed locally (nine new renderer tests plus the ten
retained startup/scene tests); the CLI also processed that actual outer ZIP.
Runtime, Android, Game, server, assets and save rules are unchanged by this
host-only continuation. No new device FPS improvement is claimed.

**Next: physically compare Software and GPU test in 0.13.20, exporting each
complete outer report.** GPU selection/probe success alone is insufficient.
Fix a specific failed prerequisite if it falls back; if Game confirms Zink and
remains correct, use native frame/renderer costs to choose the next optimization.
Black tearing remains unexplained. Keep stable 30+ FPS as the primary target;
stay in Atlas and keep startup/zoning work deferred for this pass.

# Thor opt-in GPU continuation — 2026-10-08

**Current release: 0.13.20 / version code 35. All hosted and actual public-byte gates passed. GPU activation, stable 30 FPS, temperatures and visual correctness remain pending on AYN Thor. Startup is acceptable for this pass; stay in Atlas and do not begin zoning.** This checkpoint supersedes earlier test instructions below. Retain the accepted Game scene/frame optimizations.

## Published and audited 0.13.20

Frozen APK/Android/helper/GPU recipe source: `5a592380a5272a187248a1f971d9798a298ca5c0`.
Retained Game source: `a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4`.
Tag: `coh-atlas-gameplay-v0.13.20`; release **406916952**; APK asset **622047996**.
APK: **1,560,271,624 bytes**; SHA-256
`ac99a528e088bccce6e3164de62b55408624e3027ebaef24bce0f8c9f9e8b94e`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.20/COH-Atlas-Gameplay-0.13.20.apk) · [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.20) · [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.20/COH-Atlas-Gameplay-0.13.20-testing.txt).

[Owner run **37788954170**](https://github.com/Russianranger/coh-android/actions/runs/37788954170) passed all six jobs: changes, genuine Windows PE32/native probe qualification, source-built ARM64 GPU package, full gameplay qualification, APK/publication, and independent actual public-byte audit. **1,427 tests / 96 suites / zero skips**, including all seven real PostgreSQL fixtures. The continuation independently rehashed **9,676 source pins** and 19 authored Java sources, authenticated the small evidence archives and closed release/tag/asset/checksum/notes against the source-bound receipts. The public job separately downloaded the full published APK and ran SDK 35, signer, source/payload and donor conservation checks.

Exactly two authored Java sources change; seventeen remain retained. The 77 outer payloads contain 71 byte-identical donor payloads, four helper/manifest replacements and two additions. The entire retained client-runtime.zip, Game and twenty client DLLs remain byte-identical. Game is **9,487,872 bytes**, SHA-256 `adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44`; no current-run Game rebuild is claimed. Rootfs, Wine/FEX, servers, assets/beacons/caches, schema, Android resources, display transport and strict save acceptance remain retained. Runtime manifest SHA-256 is `acb477170c107810ad501d80e4774dbd69537bf899c60374754b7ef28a26605e`. Signer remains `92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`. Binary Android manifest changes only version fields. Exact source/archive/member/receipt and audit limits are in `docs/android-evidence/gpu-profile-0.13.20-publication.json`.

## Measured reason and completed changes

The .19 Thor export confirms llvmpipe at Performance 800x600. Clean 10-cap intervals average 8.102 Hz with 97.721 ms main work and 25.129 ms pacing; clean 30-cap intervals average 9.134 Hz with 108.808 ms work and 0.023 ms pacing. Renderer batch wall time in approximately aligned 30-cap intervals averages 95.439 ms, including 27.486 ms swap. Main-thread CPU is only about 20.77 ms/frame and excludes renderer workers. These are interval measurements, not matched-route FPS gains or pure GPU/CPU costs. They support testing hardware rendering rather than further relaxing the cap. The user reports similar 10/30 performance, occasional 11–12 FPS at 30, 61–69 C, and acceptable untimed startup. See `docs/COH-PERFORMANCE-0.13.20.md` and the pinned .19 analysis JSON.

The launch selector adds **Software (current)** and **GPU test**; Software remains the default. GPU test uses the retained native ARM64 Mesa 22.3.6 GLX Zink/Kopper with a source-built, exact-base ABI-audited ARM64 glibc KGSL Turnip 26.0.0 archive. Its WSI software transport flag keeps the existing X/RFB presentation path; it does not itself identify the rasterizer. Every owned GPU-test Game attempt verifies the exact old Game producer and current source-bound GPU archive, then runs bounded actual Vulkan device/queue/readback and private Wine WGL compatibility/pixel prerequisite checks. Ordinary check rejection can fall back to Software only after proven cleanup. Cancellation, server failure or uncertain owned cleanup stops launch. Private payloads are tracked from mkdir and removed only after owned processes stop; retries are bounded to four. No mid-Game renderer switch or blind llvmpipe thread/affinity override is added. Full Game/Cg/Android Surface/hardware execution authority remains false until Thor evidence corroborates it.

Two hosted recipe defects stopped unpublished candidates: Bookworm Python lacked tarfile's filter keyword; then compiled Mesa 26 lacked the assumed COPYING file. Only the new recipe and its tests were corrected, using confined bounded extraction and the eight actual upstream license-information texts. The affected producer suite passed 21 tests and all final hosted gates reran. Neither failed candidate published an APK or changed the accepted Game implementation.

The .19 strict save comparison **failed** when temporary Commuter UID 680838905 disappeared; the other fifteen powers had no semantic changes. Expiry is an inference without an authoritative stock grant/eligibility witness. Do not call that report a save pass, relax comparisons, or assume character loss/crash from that difference.

## Thor test and diagnostic export

Install as an update preserving app data, imports and character. **Run Set up / update runtime ONCE and wait for Runtime ready.** This release changes the helper/GPU/manifest generation. No asset reimport or data reset is required.

Follow `docs/COH-Atlas-Gameplay-0.13.20-testing.txt`: first Software, then GPU test selected before a new Reopen. Use Performance, 800x600, the same fan/charging conditions; close chat with B/Esc and tap Show FPS and 30 FPS. Commands and Enter / Start already include Return. Test the same thirty-second standing/camera/populated movement/building/unseen-scenery segments; record phase timestamps, FPS/ranges, geometry/texture/NPC pauses, black flashes/tearing, visual correctness, temperatures at world entry/end/peak and stability. Save/Finish and **Export latest report after EACH run**, before another operation replaces evidence. Preserve any FAILED export. Startup timing is optional; record a regression if observed. Do not zone.

Send both **complete outer `coh-atlas-gameplay-*.zip`** files and route/FPS/temperature notes. Outer `operation.log` and `android-client-report.json` contain Android launch/requested selection/capture evidence. Inner `guest-report.zip/latest-report.json` contains `client_gpu_profile`, bounded `client_gpu_profile_attempts`, requested/selected/state/fallback reason, archive/source pins, `vulkan_probe`, `wine_gl_probe`, `probe_process_cleanup`, and `client_gpu_payload_cleanup`. Raw prerequisite output is retained in processes labelled `gpu-native-vulkan-prerequisites` and `gpu-wine-prerequisites`; `wine_probe_initialization_and_execution_seconds` isolates private-prefix preflight delay. Record selected/fallback reason and corroborate the actual Game renderer in startup/log evidence; selecting GPU or passing probes alone does not establish Game hardware rendering.

`guest-report.zip/client-evidence/client-console.log` retains `COH_CLIENT_FRAME_TIMING_V1` for pacing/main wall/thread CPU, `COH_CLIENT_SCENE_PHASE_V1` for geometry/texture completion, and `COH_CLIENT_RENDERER_ATTRIBUTION_V1` for gfx/backpressure, renderer batch/swap, selected upload/VBO/readback and long-frame distributions. Gameplay profile/texture-error records remain retained. Thread CPU excludes workers; batches include gaps/waits/scheduling; callbacks do not isolate every disk/decode/GPU completion; nested phases overlap. Frame/renderer timing streams are bounded to 120 roughly ten-second windows per thread and state observations to 64, so begin the route promptly. The immutable published notes say “each native stream”; that window bound applies to these two timing streams only. Scene phases instead have up to 128 completion records per translation unit, gameplay profile emits once, and texture-error progress has up to 32 count-triggered records. Export a failed/fallback preflight too: its exact reason determines the next concrete fix.

Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; PR #1 remains open/draft. This checkpoint is documentation only. Audit/reproduce the APK from the frozen source above, rather than the later documentation head. Actual GPU activation, stable 30 FPS, lower temperatures and black-glitch improvement remain pending the next Thor run.

# Thor renderer attribution and background capture continuation — 2026-10-08

**Current release: 0.13.19 / version code 34. All hosted and actual public-byte gates passed; physical startup/FPS gains and any effect on the brief black glitches remain pending on AYN Thor. Stay in Atlas; zoning remains deferred.** This checkpoint supersedes older setup/testing instructions below. Do not reimplement the accepted scene/frame/0.13.17 optimizations.

## Published and audited 0.13.19

Frozen Game/APK/Android/helper source: `a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4`.
Tag: `coh-atlas-gameplay-v0.13.19`; release **406398364**; APK asset **620658511**.
APK: **1,557,408,356 bytes**; SHA-256
`e4c04aff16056ba2fb2560b818355ada6c3fe95d7f5c219a37d3b2945b330241`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.19/COH-Atlas-Gameplay-0.13.19.apk) · [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.19) · [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.19/COH-Atlas-Gameplay-0.13.19-testing.txt).

[Owner run **37723301707**](https://github.com/Russianranger/coh-android/actions/runs/37723301707): all five jobs passed (changes, genuine Win32/native client, qualification, APK, independent public audit). **1,345 tests / 91 suites / zero skips**, including all seven real PostgreSQL fixtures. Root independently rehashed all **9,656 source pins** and verified the authenticated native/qualification/build/public receipts, release/tag and asset/checksum/testing-note closure. The public job downloaded the actual full APK and independently ran SDK 35, signer, exact source/payload and predecessor-conservation checks.

Actual Game: **9,487,872 bytes**, SHA-256
`adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44`.
Four reviewed Java sources/DEX change; fifteen authored Java sources remain retained. Of 75 outer payloads, exactly seven Game/helper/manifest replacements change and 68 remain byte-identical. All 20 client DLLs, servers, visual assets, beacons, prepared caches, schema, graphics driver, Wine/FEX and Android resources remain retained. The binary Android manifest changes only version fields. Signer certificate remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
Runtime manifest SHA-256 is
`89f591caeb5e0d8731bcd28defeae35dc59c1435ed3b8d0a141702cfe805edf3`.
Source/asset/archive/member/receipt pins and exact audit limits are in `docs/android-evidence/renderer-attribution-0.13.19-publication.json`.

The first candidate `a32df4e24d1e80168f9b27897a2a1c2b8f9d9b57` / run **37721873467** passed genuine Win32 logic checks but the real Game build exposed the new header including windows.h before stock Winsock2. Nothing was published. Only the new renderer patch's include placement and its source-order regression were corrected; twelve affected tests passed and every hosted gate reran successfully. No old producer/layer, renderer, pacing or buffering policy changed.

## Completed changes and physical evidence boundary

The FPS label now reads FPS and ms/frame below the crowded top HUD at native (8,112), retaining native sampling and `/showfps`. Existing sidebar Show FPS/10 FPS/30 FPS commands include Enter; sidebar Enter / Start and controller Start remain paired, bounded input.

PixelCopy bitmap scanning, PNG compression and the encoder's initial SHA run on one process-wide worker with zero waiting queue, rather than the Android UI thread. Presentation resumes as soon as the copy finishes; immutable bitmap ownership, current session/generation, cancellation, PNG limits and gameplay screenshot proofs remain guarded. Independent retained-PNG verification/callback work still runs on its retained path and is excluded from encoder timing. `android_capture_diagnostics` aggregates current-session successful capture timings, including unretained/uniform captures, without granting readiness/save authority.

The append-only native layer adds main gfx/backpressure and renderer batch/swap/selected upload/VBO/readback wall-time distributions, numeric maxfps/showfps state observations and thread CPU measured at window boundaries. It preserves rendering, queue policy, FPS choices, resolution and worker configuration. Strict failed-save diagnostics add a typed after-snapshot/power delta and optional read-only stock lifecycle witnesses; save comparison is not relaxed and no server/SQL behavior changes.

The supplied 0.13.18 export and latest user observation are pinned in `docs/android-evidence/renderer-attribution-0.13.18-thor-20261008.json`; analysis is in `docs/COH-PERFORMANCE-0.13.19.md`. Startup was reported about unchanged, FPS was not visible to the user, and 30 had occasional brief black tearing. Unmatched native intervals average **8.422 Hz at 10** and **10.035 Hz at 30**, with explicit pacing **25.615 ms** and **0.005 ms** respectively. This does not establish a controlled gain or sustained 30 FPS; it points away from intentional pacing as the limiting factor in the sampled 30 intervals. Black-glitch cause remains unconfirmed.

That historical report's strict save comparison **failed** on one extra stock-compatible Commuter power, with all fifteen original semantic power rows preserved. There is no authoritative native DayJob grant/eligibility witness, so do not call the report a save pass or assume a crash/character loss. This release only improves evidence for a future failure. Do not add an unmeasured llvmpipe worker override.

## Next Thor run and diagnostic export

Install as an update preserving app data, imports and character. **Run Set up / update runtime ONCE and wait for Runtime ready:** Game/helpers/manifest changed, unlike Android-only 0.13.18. No asset reimport or data reset is required.

Follow `docs/COH-Atlas-Gameplay-0.13.19-testing.txt`. Keep Performance, 800x600 and llvmpipe. Capture first and warm launcher/Reopen-to-login/world times, displayed local Atlas/client durations, selection-to-visible/playable world and progressive appearance/stalls. Close chat with B/Esc, tap Show FPS, then compare 10 and 30 over the same timed standing/camera/populated movement/building/unseen-scenery route. Capture FPS/ranges, geometry/texture/NPC pauses, black-glitch location/frequency/duration, temperatures/fan/charging, stability/crashes and ordinary strict save/reopen. Begin promptly after world entry; do not zone.

Use **Export latest report after EACH run before another operation replaces it**, and send the **complete outer `coh-atlas-gameplay-*.zip`** with route timestamps and timing/FPS/temperature notes. Preserve FAILED exports if strict save comparison fails. The outer `operation.log` records Android stages/command submission; `android-client-report.json.android_capture_diagnostics` records copy/freeze/encoding wall/CPU/dispatch/coalescing and actual UI-encoder counts. The inner `guest-report.zip/latest-report.json` records identities/startup/lifecycle/save and typed failed comparison. `guest-report.zip/client-evidence/client-console.log` contains retained `COH_CLIENT_FRAME_TIMING_V1`, `COH_CLIENT_SCENE_PHASE_V1`, `COH_CLIENT_GAMEPLAY_PROFILE_V1`, `COH_CLIENT_TEXTURE_ERRORS_V1` and new **`COH_CLIENT_RENDERER_ATTRIBUTION_V1`**. Local Atlas is in `client-evidence/character-atlas-console.txt`; failed-after snapshots are retained in `client-evidence/character-reopen-failed-after-snapshot.json` when applicable.

Frame records separate intentional pacing and main work; scene phases identify geometry/texture loading; renderer records separate gfx/backpressure, batch/swap and selected callback costs/spikes. Thread CPU excludes llvmpipe/Wine/FEX workers. Renderer batches include queue gaps/driver waits/scheduling, and selected texture callbacks do not isolate disk/decode/GPU completion. Nested phases overlap and must not be summed. Each window stream stops after 120 roughly ten-second windows per thread; numeric state changes stop after 64. Hosted qualification establishes correctness only.

Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; PR #1 remains open/draft. This publication checkpoint is documentation only: reproduce/audit the APK from the frozen source above, rather than a later documentation head.

# Thor sidebar FPS controls and Start/Enter continuation — 2026-10-07

**Current release: 0.13.18 / version code 33. Physical Start/Enter and the controlled 10/30 FPS route remain pending on AYN Thor. Stay in Atlas; zoning remains deferred.** This checkpoint supersedes the incomplete 0.13.17 test instructions below. Continue scene/frame optimization from the next complete physical export; do not reimplement the accepted native changes.

## Published Android-only 0.13.18

All hosted qualification, Android build/signing, fresh prepublication audit and independent actual-public-APK audit passed.
Frozen APK/Android source: `d1e455f8d0047ac02398d17c5df1001375522f98`.
Retained Game/runtime source: `4a57ffe3b75612fb9c356de9c4150729736e849e`.
Tag: `coh-atlas-gameplay-v0.13.18`; release **405864570**; APK asset **618968033**.
APK: **1,557,379,684 bytes**; SHA-256
`d7fb00ae5406208a2497c7b9ea9659403a422dd0698404cd968112a4ba7b8ca1`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.18/COH-Atlas-Gameplay-0.13.18.apk) · [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.18) · [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.18/COH-Atlas-Gameplay-0.13.18-testing.txt).

Owner run **37637034415**: [qualification/publication/public audit](https://github.com/Russianranger/coh-android/actions/runs/37637034415).
All four jobs passed: changes, qualification, APK and public audit.
**1,264 tests / 84 suites / zero skips**, including all seven real PostgreSQL fixtures.
Independent continuation rehashed all **9,638 frozen source pins**, all 19 authored Java sources, the five authorized Java changes and fourteen retained sources. The exact published 0.13.17 Game and source-bound Win32/ancestry/schema/import proofs are reused and revalidated; no native rebuild was needed.
Game: **9,477,120 bytes**, SHA-256
`5b6cfb6d20eb5f6642d6d1124e6b5ba188e89f9ad58c26268f0be35d996134aa`.

Android Java/DEX is rebuilt; Android resources remain retained and the Android binary manifest changes only version fields. **All 75 outer runtime payloads are byte-identical to 0.13.17**, including native client/server archives, guest helpers, assets, beacons, caches and the runtime manifest. Runtime manifest SHA-256 remains
`09f2cd20846d99e44f950300177eb9b7cb14dea624c51487a93a19d4f953e113`.
SDK 35, signer identity, ZIP alignment, exact payload/source closure, checksum and testing notes passed both prepublication and independent actual public-byte audits. Signing certificate remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
Receipt/archive/API/source pins are in `docs/android-evidence/client-sidebar-0.13.18-publication.json`. The hosted public job fetched the full public APK; this continuation authenticated the small evidence archives and release asset digests rather than downloading another 1.55 GB APK.

## Completed fix and qualification boundary

The 0.13.17 physical comparison was blocked because controller Start was absent from the dispatch switch and Send text sends printable text without Return. Sidebar **Show FPS**, **10 FPS**, **30 FPS** now submit only the fixed native commands through the retained atomic chat route, including Enter. Sidebar **Enter / Start** and controller Start send a bounded paired Enter, once per physical press; repeats and release do not resubmit. Enter is available in the owned input-ready login phase; FPS actions require the current post-Atlas connection and fresh world views. Close existing chat/dialogs with B/Esc before each FPS command. Submission status is not native acknowledgement.

Owned session/PID/decoder/input-epoch, visibility/focus, cancellation, queue/deadline and save/task guards remain authoritative. Pending FPS input reserves the command route briefly; ordinary automatic Surface disable uses an ordered release, while explicit pause/focus loss/Stop cancels. Review found and corrected one concrete race: native accepted/completed task evidence must remain accepted during FPS typing. The executable regression runs the actual event blocks and preserves save readiness.

The first hosted candidate `e93419d067d3e9b62b02335de1557bb8a4166bab` / run **37635556758** stopped on a retained recovery host fixture missing the new pending-command field; nothing was published. The fixture now models the field and proves pending input defers creator Save without weakening the reopened task gate. Local review also caught an input suite advertised but absent from execution; the final 84-suite inventory explicitly includes `test_input` and rejects incomplete inventories before running. These narrow qualification corrections changed no native/runtime payload.

Install as an update preserving app data, imports and character. **If 0.13.17 already shows Runtime ready, this Android-only update needs no additional setup or asset import:** the audited runtime identity and bytes are unchanged. A new installation or older/unready runtime still needs ordinary setup. The sidebar setup label now reads **Set up / update runtime**. This conditional rule does not apply to future Game/helper/manifest updates; 0.13.17 itself required setup after its native/helper generation changed.

## Incomplete physical 0.13.17 evidence and next Thor run

The supplied `coh-atlas-gameplay-20261007-135706.zip` is pinned in
`docs/android-evidence/client-sidebar-0.13.17-thor-20261007.json`.
It confirms **662.886 s (11:03) to input readiness**, **223.323 s local Atlas**, **178.431 s client startup**, and **67.910 s observed login to world**. The extra **277.118 s before server login** is interaction/wait, not a native initialization stage. Reopen, normal save and owned cleanup passed; the requested FPS/control route was incomplete and temperatures were absent.

The actual native Performance launch selected 30 FPS, but the uncontrolled gameplay sample averaged **9.609 Hz**, **103.406 ms main work**, **70.479 ms submit wall time** and **0.023 ms explicit pacing**. This points away from intentional pacing in that sample; it does not prove a controlled FPS/startup gain. No gameplay missing-texture tuple errors or suppression progress records occurred, so this run did not exercise duplicate-error suppression benefit. Nested scene timings and worker-CPU limits remain as documented.

Follow `docs/COH-Atlas-Gameplay-0.13.18-testing.txt`:
verify short/held controller Start and sidebar Enter; after Atlas use Show FPS, then compare 10 and 30 over the same Performance/800x600/llvmpipe standing, camera, populated-movement and building/unseen-scenery route. Record each segment's timestamps, FPS/range, geometry/texture/NPC pauses, temperatures/fan/charging, progressive world appearance, all startup phases, stability and any crash. Verify normal save and warm reopen/persistence. Use **Export latest report after each run**, before another operation replaces its evidence, and send the **complete outer `coh-atlas-gameplay-*.zip`** plus timing/FPS/temperature notes.

New safe `performance_command_queued`, `performance_command_dispatch`, `performance_command_submitted` and `sidebar_enter_submitted` timestamps are in `operation.log` and the lifecycle in `android-client-report.json`. They prove submission only. Native records remain in `guest-report.zip/client-evidence/client-console.log`:
`COH_CLIENT_GAMEPLAY_PROFILE_V1`, `COH_CLIENT_TEXTURE_ERRORS_V1`,
`COH_CLIENT_FRAME_TIMING_V1` and `COH_CLIENT_SCENE_PHASE_V1`.
They separate explicit pacing, main work/thread CPU, submission/backpressure, presentation and long-frame distributions, with geometry/texture completion phases. Thread CPU excludes llvmpipe/Wine/FEX workers; GPU completion and individual texture decode/upload remain unisolated; nested phases must not be added twice. Streams are bounded to 120 roughly ten-second windows each, so begin the focused route promptly after world entry.

Main and draft PR #1 remain separate. The post-publication checkpoint is documentation only: audit/reproduce 0.13.18 from the frozen APK source above, not a later documentation head. Physical 0.13.18 control success, stability and performance gains remain pending.

# Thor 30 FPS continuation — 2026-10-07

**Current scope is the client scene/frame pass and 30 FPS experiment. Stay in Atlas; zoning remains deferred.** This checkpoint supersedes older instructions to keep gameplay capped at 10 FPS for every test and the incorrect advice that a Game/helper update needs no runtime setup. Historical release sections below remain preserved.

## Published 0.13.17 / version code 32

All hosted gates and the independent actual-public-APK audit passed.
Frozen Game/APK source: `4a57ffe3b75612fb9c356de9c4150729736e849e`.
Tag: `coh-atlas-gameplay-v0.13.17`; release **405766496**; APK asset **618702599**.
APK: **1,557,375,588 bytes**; SHA-256
`2da7436d165662b47780c19241cbcf3c16ef3bb903fb94f79b231f3f0c390bf3`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.17/COH-Atlas-Gameplay-0.13.17.apk) · [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.17)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.17/COH-Atlas-Gameplay-0.13.17-testing.txt).

Owner run **37622107943**: [qualification/publication/public audit](https://github.com/Russianranger/coh-android/actions/runs/37622107943).
All five jobs passed: changes, native client, qualification, APK and public audit.
**1,197 tests / 80 suites / zero skips**; all seven real PostgreSQL fixtures.
**9,628 source pins** and all 19 retained Java sources were rehashed locally against the frozen receipt. Actual Game is **9,477,120 bytes**, SHA-256
`5b6cfb6d20eb5f6642d6d1124e6b5ba188e89f9ad58c26268f0be35d996134aa`.
Genuine Win32 native scene/frame/gameplay proofs, actual CMake Game-only build, schema and DLL-import closure passed.
The 75 outer runtime payloads contain 68 byte-identical retained payloads and exactly seven authorized Game/helper/manifest replacements, zero additions. All 20 client DLLs, Android DEX/resources, server binaries and immutable visual/beacon payloads remain retained. SDK 35 source/payload/signature checks passed before publication and again on the actual public APK. The signing certificate remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.

Detailed source/asset/receipt/archive pins and audit scope are in
`docs/android-evidence/performance-0.13.17-publication.json`. Independent continuation checks authenticated five small evidence archives and their unique safe members, matched release/tag/API asset digests to APK/checksum/testing receipts, and revalidated the actual native package and complete qualification/source closure. The hosted public job independently downloaded the full APK, checksum and notes; this continuation did not download a second 1.55 GB APK.

Qualification review fixed one concrete integration issue before source freeze: the exact packaging receipt omitted the new actual-scene-predecessor proof field. A real typed ancestry integration test now binds the returned proof to the gate. No qualification failure required changes to the accepted scene/frame implementation.

Main and draft PR #1 remain separate; the post-publication checkpoint is documentation only. Do not rebuild or replace 0.13.17 from a later documentation head. Use the exact frozen source above for audits.

The 0.13.16 physical export confirmed reopen, save verification and owned cleanup. Its support ZIP is pinned in `docs/android-evidence/performance-0.13.16-thor-20261007.json`. Reopen-to-login was 691.012 s, login-to-world 67.676 s, local Atlas 227.043 s and actual client startup 193.541 s. The successful runtime setup took 99.431 s. This update run refreshed owned Atlas caches and revalidated visual bytes; an unchanged warm run is still needed. Do not claim a .16 startup/FPS gain from the stopwatch alone.

The gameplay sample averaged 123.047 ms per frame, 104.452 ms main wall work and 17.752 ms explicit pacing. Main-thread CPU averaged about 20.96 ms per frame in pure gameplay windows; wall work is not CPU time. The console had 24,856 custom-texture errors; nine identities accounted for 23,832 repetitions. See `docs/COH-PERFORMANCE-0.13.17.md` for evidence and measurement limits.

The new append-only Game layer selects only `COH_CLIENT_GAMEPLAY_FPS=10|30` after argument parsing, excludes cache generation, retains menu/background limits and preserves later `/maxfps` commands. Verified Performance launches request 30; standard/Compatibility request 10. It bounds repeated diagnostics at the two `changeTexture()` Errorf calls using 64 exact full keys and at most 32 progress records. Every texture load, fallback, assignment and appearance update remains. Further/null/oversized identities retain the original error path. Suppression records are progress lower bounds, not final totals. This is a diagnostic-overhead optimization, not an asset repair or proof of sustained 30 FPS. The old scene/frame patches and producers remain frozen. Android Java/DEX, server binaries, assets, graphics stack, resolution, persistence and gameplay validation stay retained.

Install the update preserving app data, imports, runtime and character, then run **Set up runtime once**, even though the retained UI button says “new install only.” Wait for Runtime ready before Reopen. The manifest generation changes with native/helper bytes and readiness deliberately remains fail closed. No data reset or asset reimport is needed.

Follow `docs/COH-Atlas-Gameplay-0.13.17-testing.txt`: record first and warm startup phases, progressive appearance and playable world entry; use `/showfps 1`, compare `/maxfps 10` then `/maxfps 30` over the same Performance route; capture stationary/camera/populated movement/building/unseen-scenery hitches, temperatures, stability, save and reopen. Export the complete outer `coh-atlas-gameplay-*.zip` after each run before later operations replace it. Native records are in `guest-report.zip/client-evidence/client-console.log`: retained `COH_CLIENT_SCENE_PHASE_V1` and `COH_CLIENT_FRAME_TIMING_V1`, plus new `COH_CLIENT_GAMEPLAY_PROFILE_V1` and `COH_CLIENT_TEXTURE_ERRORS_V1`. The report's current typed producer/control fields must bind the actual Game. Frame streams have 120 roughly ten-second windows each; begin focused tests promptly after entering the world. Thread CPU excludes llvmpipe/Wine/FEX workers; renderer submit/backpressure/presentation wall time is not GPU completion. Texture completion phases do not isolate per-texture decode/upload cost; nested phases must not be added twice.

Physical .17 performance and stability remain pending the next AYN Thor export. Continue optimization from that evidence; do not start zoning or reimplement accepted scene/frame changes.

# Release recovery verification — 2026-10-07

Recovered continuation head `7850376508fe544c1d4a4c817d20f241b3324f20`.
The interrupted-session screenshot was older than the repository evidence:
**0.13.16 had already completed qualification, publication, public APK audit
and handoff. No release/build gate remained unfinished.** Do not rebuild,
replace or renumber this APK without a concrete new defect/change. The next
action is physical Thor testing; zoning remains deferred.

This recovery independently checked the live PR/branch, release assets, tag
and all five owner-run jobs; downloaded and hash-verified the existing public
audit, qualification, native-build and packaging evidence archives; validated
their exact receipt bytes; and revalidated all **9,615 frozen source pins**,
the complete 76-suite qualification contract and actual source-bound Win32
scene/frame receipts. The previously completed independent public audit
downloaded and checked the actual APK, checksum and notes. This recovery did
not repeat that 1.55 GB APK download or claim a new physical performance test.

Independent read-only native/release reviews found no concrete defect. The
six scene/frame/contract/package/report suites passed again locally:
**34 tests, zero skips**. Separate review verification including the retained
preload-launch suite passed **42 tests, zero skips**; these counts overlap and
must not be added. The full 1,163-test/postgreSQL/SDK/signing/public audit remains
the completed hosted result at the frozen release source below.

Expanded physical instructions and precise measurement limits are in
[COH-Atlas-Gameplay-0.13.16-thor-test-plan.md](COH-Atlas-Gameplay-0.13.16-thor-test-plan.md).
They explicitly cover progressive world visibility, separate stationary/
camera/populated-movement FPS, building/unseen-scenery hitches, temperatures
and complete per-run exports. Native thread CPU and render/presentation wall
timings do not isolate llvmpipe workers or per-texture decode/upload cost.
This recovery changes documentation only; the release source, APK, checksum
and published testing notes stay frozen.

# Client scene-loading and native frame continuation — 2026-10-07

**Physical 0.13.15 first-update and warm runs are accepted. Scene loading and
gameplay smoothness are the current priority. Keep the accepted llvmpipe
renderer, 800×600 profile and 10 FPS cap. Zoning remains deferred.**

Starting continuation head: `f346ccd3e2979dc12369de9c31f97e418745cb8f` on
`codex/character-persistence-continuation`; main and draft PR #1 remain separate.
The accepted 0.13.15 APK/source/signing identity are unchanged. The two physical
support ZIPs are pinned in
`docs/android-evidence/performance-0.13.15-thor-20261007.json`. Both pass ordinary
save/reopen/cleanup proof; the existing character, powers and costume persist.

Observed first-update Reopen-to-world is **781.815 s**; warm is **677.999 s**
(user stopwatches approximately 13 min / 11:30). Private server preparation
fell from 508.398 s in 0.13.14 to 39.585 / 32.555 s; both use the same compatible
server cache with zero linked/copied files and no beacon regeneration. Warm
visual preparation performs zero archive reads, hashing, decoding or installs.
The 0.13.15 warm native client scene interval from MapServer connection to
current CLIENT_READY is **77.793 s** (first 75.330 s). Recorded post-connect BIN
open/freshness/decode work accounts for 16.982 s, leaving most scene wall time
unexplained by the existing diagnostics. Initial native client startup remains
approximately 203 s; local Atlas 203.396 s warm / 235.665 s first.

**0.13.16 / version code 31 is published. All hosted gates and the independent
actual-public-APK audit passed. Physical 0.13.16 timings remain unmeasured.**
Frozen Game/APK source: `d41aab3dd1a2f169a0ec71ff47d56767a8eb65e5`.
Tag: `coh-atlas-gameplay-v0.13.16`; release **405309851**; APK asset **617312668**.
Public APK: **1,557,359,204 bytes**; SHA-256
`ddb1f26913291295248cd4195d0184c02b24849921a6b47fda391dd7af26c7d7`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.16/COH-Atlas-Gameplay-0.13.16.apk)
· [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.16)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.16/COH-Atlas-Gameplay-0.13.16-testing.txt).
The existing application ID and certificate
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`
preserve install-as-update behavior. Keep runtime, imported assets, app data and
the existing character. Complete the offered Game/helper update once; measure
it separately and include it in true launcher-open-to-login elapsed time.

Hosted owner run **37559820885** at the frozen source:
[qualification and publication](https://github.com/Russianranger/coh-android/actions/runs/37559820885).
All five jobs passed: changes **112594362113**, native Game **112594493301**,
qualification **112597185524**, APK **112598693474**, public audit **112599879027**.
The Win32 Game is **9,473,024 bytes**, SHA-256
`4de0e49d028ed75271b44838bffb570ae0112460183d1c441174cf9d9dc282d4`.
Genuine Win32 QPC/thread-CPU/TLS/concurrent-JSON harnesses and the actual MSVC
Game build passed. Raw CMakeCache proves Win32 and persistence fixtures OFF for
this Game build; source/reverse-patch checks cover seven sources and two headers.
Native imports retain the same 21 DLL names with no delay imports. All 12 Actions
runs at this source completed successfully.

Final qualification: **1,163 tests / 76 suites / zero skips**, all seven real
PostgreSQL fixtures (three emission, four level-up), **9,615 source pins** and
**19 unchanged authored Java sources**. Fresh SDK 35/package/signer/source and
inner/outer conservation audits passed. The separate read-only public audit
downloaded the actual APK, checksum and testing notes and verified their bytes.
Exact run/job/artifact/receipt pins and preservation results are in
`docs/android-evidence/performance-0.13.16-publication.json`.

Implemented in 0.13.16:
- Opt-in `gfxReload` skips the FX preload immediately discarded by the following
  cache invalidation. Both invalidations, sky reset/order and mandatory surviving
  FX preload remain. Ordinary initialization and default fallback remain stock.
- Bounded native JSON scene diagnostics separate groups, entities, collision,
  geometry and texture completion, preload/invalidation and CLIENT_READY phases.
  Nested intervals must not be summed as independent work.
- Bounded native QPC frame aggregates distinguish menu/loading/gameplay, main
  work, engine time, cap/pacing wait, render submission, presentation interval and
  actual SwapBuffers wall time. Histogram bounds, stutter counts and calling
  thread CPU time are reported every 10 seconds, with fixed memory and report
  limits. These are native cadence/CPU measurements, not Android delivered FPS
  or GPU completion. llvmpipe/FEX worker CPU is outside the observed thread.
- The verified new Game launch replaces verbose per-resource BIN timing prints
  with these aggregates. Source freshness, BIN/schema/CRC validation and accepted
  known-string copy/dependency preload controls remain enabled and unchanged.
- Exact older-Game migration and texture-header receipt rebinding preserve warm
  worktree/server/texture caches; only the Game executable and four guest helpers
  plus their manifests may change. All 20 client dependencies and the other 68
  outer payload members must remain identical to 0.13.15.

Intentionally retained: Wine/FEX/Mesa stack, renderer/cap/resolution, Android
shell/dex/controls/audio, server binaries, all UI/visual/GEO/beacon payloads,
resource formats/freshness/collision/physics/network waits, quest tracking,
NPC movement, combat/task logic, character persistence and recovery. No asset
reimport, beacon generation, UI sweep, GPU experiment or zoning implementation.
Further BIN metadata preloading was rejected because actual accepted cache
dependencies already belong to stock-scanned trees. Android screenshot capture
and translated priority-call changes are deferred pending native frame evidence.

Hosted qualification retained all 70 prior suites plus six scene/frame/report
suites. Packaging proves exactly **75 outer payloads: 68 byte-identical, seven
authorized replacements, zero additions**. Only Game changes within the client
runtime; all **20 client dependencies** remain byte-identical. DEX/resources,
server extraction, all visual/UI/GEO/beacon/cache payloads and the signer remain
unchanged. Hosted checks establish retained contracts and payload preservation;
physical FX/UI/gameplay acceptance and elapsed/FPS gains remain next-Thor gates.

Windows staging now preserves LF. The frozen donor's native ancestry contains
two independently proven PostgreSQL C/H LF/CRLF variants and their three enclosing
digests. Only this new scene layer compares verified, normalized copies using
typed canonical JSON; raw histories and older-layer exact comparisons remain
unchanged. Actual external donor/new Win32 receipts and all four encoding
combinations pass; 11 foreign mutations, including boolean/float substitutions,
fail. Publication checks the live continuation head before draft creation and
again before making it public; superseded runs are cancelled. These fixes change
receipt validation/publication behavior and do not alter the native C patches.

Phase analysis and ranked candidates: `docs/COH-PERFORMANCE-0.13.16.md`.
Focused Thor instructions: `docs/COH-Atlas-Gameplay-0.13.16-testing.txt`.
Update in place, retain imported assets/runtime/app data/character, complete any
offered Game/helper update once and time it separately. Measure first and warm
launcher-open/Reopen-to-login/world, Atlas, actual client and login-to-world.
Spend 30 seconds each standing, walking, rotating the camera, in populated areas,
in several-NPC combat, opening UI and tracking objectives/pathing; note each
activity's local start time. Use ordinary Save/log out then Finish and export
both complete support ZIPs including operation.log, Android report, inner
guest-report.zip/latest-report.json and client/server consoles. The client
console must contain `COH_CLIENT_FRAME_TIMING_V1` and
`COH_CLIENT_SCENE_PHASE_V1`; use
`tools/android/interactive/analyze_client_scene_performance.py` for bounded
weighted summaries. Physical preservation and savings remain next-test gates.

---

# Current performance continuation — 2026-10-06

**Physical 0.13.14 is accepted for the observed UI, native Atlas beaconization,
quest objective tracking, NPC pursuit, combat and task completion. Performance
is the current priority; zoning is deferred. Historical pending statements below
are superseded by this checkpoint.**

Starting live continuation head: `8de212e60520d1af66dfcd2f25481f57a85e1d34`.
Keep branch `codex/character-persistence-continuation`, main separate and PR #1 draft.
The accepted public 0.13.14 APK/source/tag/signer are unchanged.

Physical input: `coh-atlas-gameplay-20261006-033901.zip`, 13,208,853 bytes,
SHA-256 `d698a8152880a321d29b94365d831b3eea9bde358baca76361095961dae5a60c`.
The report passes ordinary saved-character/SQL/owned-cleanup proof. User physical
observations establish gameplay acceptance independently of startup-only scope.

The approximately 21-minute report contains **508.398 s of private server
preparation** inside a 538.664 s DbServer stage. Native launch/config/schema is
only the remaining 30.266 s. The new 406-original-GEO contract properly rejected
three incompatible closed generations, triggering 186,535-leaf cold staging.
The returned compatible key `d3f6b18b9ea8bf59a848686a` is preserved by this pass.
Atlas readiness 198.838 s and actual client startup 198.172 s remain in the good
3–4 minute range. Reopen-to-observed-login was 1,150.129 s; observed world entry
1,233.935 s. First-update UI/beacon/header preparation is separately recorded.

**0.13.15 / version code 30 is published and all hosted release gates passed.**
Frozen APK/source commit: `d31685579a04307c38356918a81a22997a858c83`.
Tag: `coh-atlas-gameplay-v0.13.15`; release 404301936; APK asset 614432886.
Public APK: 1,557,338,724 bytes; SHA-256
`f43586fcc36ffc3a88fd8f3dfdb756d174604527e9a1dab140f97f36fbdaf8fb`.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.15/COH-Atlas-Gameplay-0.13.15.apk)
· [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.15)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.15/COH-Atlas-Gameplay-0.13.15-testing.txt).
The same application ID/signing certificate preserves install-as-update behavior.
Complete the offered helper/runtime update once before Reopen phase timing; retain
runtime, imported assets, app data and the existing saved character.
Record that update's duration separately; include it in true launcher-open to
login if it occurs during that interval. Only Reopen phase timings start after
the offered update. This clarifies the published testing notes' stopwatch scope.

Implemented:
- Invocation-scoped verified real-parent resolution during cold staging and
  single-pass directory receipt sealing, with strict leaf/containment/link and
  final parent checks. Fixture metadata calls 4608→793 (82.8% fewer).
- Exact cache identity preserved; unchanged warm fixture links/copies zero files.
- Startup timing separates geometry, cache checkout, cold mirror/seal or warm
  restore, native dependencies, server bins, animations, beacon preparation,
  configuration, native DbServer readiness and schema verification.
- After current native Atlas connection, use native progress/events with current event identity validation during
  gameplay and perform full fresh SQL/status/save proof on valid logout delivery.
- Registry main-loop proof only at startup and fresh final completion; preserve
  live process/window/console checks. This removes recurrent translated probes.
- Bounded support-ZIP phase analyzer; no extra native/per-frame instrumentation.

Intentionally retained: all 10,401 original visuals and 9,613 prior encoded streams,
406 original GEOs, native graph/date, native Game/MapServer/DbServer, accepted
Wine/FEX/Mesa llvmpipe renderer, 800×600 profile and 10 FPS cap, Android shell,
controls/audio, database/character persistence, rollback and recovery. No assets
reimport, UI sweep, beacon generation, GPU experiment or zoning work.

Hosted [run 37411543214](https://github.com/Russianranger/coh-android/actions/runs/37411543214)
completed **SUCCESS** at 2026-10-06 04:10:44 UTC on the exact frozen source.
Qualification job 112100983226 passed **1,124 scenarios across 70 suites, zero
skips and all seven real PostgreSQL 16.15 fixtures**, including retained UI,
beacon, quest/task/combat-save, persistence and recovery guards. Source closure
contains 9,590 files; all 19 authored Java files remain identical.
APK job 112101888443 passed the full SDK/signature/source/payload audit in a
fresh process before publishing. All 75 payload members are conserved: only
four guest helpers and two manifests differ; the other 69 are byte-identical,
with no additions. Native/runtime/UI/GEO/beacon/dex/resources remain intact.
Independent read-only public-audit job 112103210518 downloaded the actual public
APK, checksum and notes and repeated SDK, signer, source and payload checks;
its `COH_THOR_PERFORMANCE_PUBLIC_AUDIT_V1` receipt is `status=passed`.
Public audit artifact 11389553450 is 531 bytes, SHA-256
`91e7be3e5e35b2517f3d2633b61c386da49cbf1c112998a8613f70bd4c19ebb8`.
Qualification artifact 11388779701 and packaging artifact 11388964767 are pinned
in `docs/android-evidence/performance-0.13.15-publication.json`.
All 18 other workflows on this source commit also completed SUCCESS; finite
scope guards kept older native/UI/beacon publishers from rebuilding this pass.

Hosted metadata-call savings and eliminated probes do not prove new physical FPS/timing.
No hosted test substitutes for physical gameplay. The first-update and
second-warm Thor reports remain required; 0.13.15 physical validation is pending.

Phase comparison/candidate ranking: `docs/COH-PERFORMANCE-0.13.15.md`.
Focused Thor instructions: `docs/COH-Atlas-Gameplay-0.13.15-testing.txt`.
Export each complete outer support ZIP, preserving Android report, operation.log,
inner guest-report.zip/latest-report.json, client/server consoles and server logs.
Use ordinary Save character/log out then Finish; remain in Atlas.
Measure launcher-open to login, Reopen to login, displayed local Atlas startup,
actual client startup and login-to-playable-world for both runs. Note repeated
long preparation. Compare standing, walking, camera rotation, several-NPC combat,
populated areas, UI windows and objective/pathing stutters using the same preset.

---

# City of Heroes Android handoff

**0.13.14 is ready for physical AYN Thor testing. Its unchanged public APK passed the independent corrected SDK/source/payload audit. UI rendering, NPC pursuit and new startup timings remain physical checks.**

APK: **COH-Atlas-Gameplay-0.13.14.apk**, version code **29**,
application ID `io.github.russianranger.cohclientinteractive`.
Frozen build/source: **`25f821da9e782281953412543057054abd8dd320`**.
Public size: **1,557,338,724 bytes**.
SHA-256: **`1dab30d097978e6d8b7e299e868a932d73c924410dcc20d4e6e51f36353b11ee`**.
[Direct APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.14/COH-Atlas-Gameplay-0.13.14.apk)
· [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.14)
· [Testing notes](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.14/COH-Atlas-Gameplay-0.13.14-testing.txt).
Release 404193274 / APK asset 613990752 remains a public prerelease targeting that exact source.
Install as an update, preserving the runtime, imported data and saved THORHERO.

Independent read-only audit [37395657530](https://github.com/Russianranger/coh-android/actions/runs/37395657530)
at auditor source `8edc90d124c3a2291a161ff63066160daddc6684` completed **SUCCESS**.
Closed job **112050869207** completed at **2026-10-06 00:50:44 UTC**.
Artifact **11382438795** (`coh-ui-beacon-public-byte-audit`) is **3,470 bytes**,
SHA-256 `222d5e94a75be166ea4a421f2229b870e962cc003652c23c9f968086096648b0`.
Its `COH_UI_BEACON_PUBLIC_AUDIT_V2` receipt records `status=passed`, exact
APK bytes/hash/source, signer certificate
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`,
original failed-run history and the distinct current auditor provenance.

The audit authenticated the actual public APK/checksum/testing-note bytes and
all original proof artifacts. It ran all **16 reviewed package regressions with
zero skips**, then the original full Android SDK 35 / build-tools 35.0.0 signer,
badging, binary manifest, source closure, qualification receipt, all 75 payload
members and donor conservation checks against pristine released source25.
It loaded no signing key, rebuilt no APK and modified no release.
Original release qualification actually passed **1,102 scenarios across 68 suites,
zero skips and all seven real PostgreSQL fixtures**; the read-only audit preserves
and verifies that evidence rather than presenting it as a new test execution.

Original release run [37392793426](https://github.com/Russianranger/coh-android/actions/runs/37392793426)
remains **FAILED overall**. Build, SDK signing, same-process audit, publication
and public checksum passed, but its separate fresh-process verifier stopped at
2026-10-06 00:28:33 UTC with `Candidate provenance differs`.
Independent reviews found an audit serialization bug: unsorted JSON plus
frozenset iteration changed the insertion order of three equivalent manifest
keys. The corrected checker validates every logical field and actual embedded
payload pin, then uses the exact embedded manifest bytes for the runtime
reference. It changes no APK/runtime/source/qualification bytes.

Correction source `dd8bfebe748d59c383c423657a50dd3ce83aed42` contains checker blob
`86bea0a3f0a24753affa52334fe653df06e818e4` and test blob
`53685a11602e12590e8987e182c8497b91fa364a`.
Auditor blob `fc9d962fb6edb8d07eeb72f9d1014fb581486b1b` grafted only that reviewed
verification function into the original builder namespace; released source
files stayed pristine and every source/SDK/payload guard remained intact.
Publisher guard run 37395243623 actually passed and intentionally skipped all
four repackaging jobs because this release already exists. Never overwrite it.

This pass supplies **788 exact original UI resources**, preserving all 9,613
prior encoded visual streams, and the genuine native Atlas graph qualified in
two fresh layouts at CRC `0xb0c21ded`, full readback and **32 real routes each**.
The 406 required original object GEOs are prepared before server cache sealing.
A finite one-time refresh removes only owned affected private Atlas/model caches;
unchanged warm preparation avoids archive decoding, input payload hashing,
cache scans/removal and restaging. Existing character/XP/power persistence and
shipped Game/MapServer/DbServer bytes remain preserved. No new startup-speed
claim is made.

Physical test: compare first-update and second-warm timing reports by phase;
inspect tips, enhancements/slots, tray controls and NPC overhead indicators;
check absence of the native red beacon warning and Hellion pursuit around an
obstacle; inspect Ms. Liberty and complete training if a choice is available;
save/logout, Finish/export, then reopen and verify level/XP/powers.
At displayed level 2, the third power-set column is intentionally empty under
native Pool/Epic unlock rules. Keep testing in Atlas; **zoning is the next pass**.
Main remains separate and PR #1 remains draft.

Actual native run [37377053417](https://github.com/Russianranger/coh-android/actions/runs/37377053417)
at source `3124723b93b4ae83b211f9319ffa8d6d8a3e851d` completed generation,
fresh ordinary-world CRC, untouched version-9 date, graph readback and 32 real
routes, all at `0xb0c21ded`. Counts: combat 163,544; connected 163,527;
ground 1,805,050; raised 2,698,868; blocks 602. Its first subsequent bare-world
profile failed at 2026-10-05 23:16:31 UTC with actual CRC `0x1583f117`.
The overall run remains failed; NONE/ALL optional-geometry equality is disproved.

Successful read-only forensic run [37388593712](https://github.com/Russianranger/coh-android/actions/runs/37388593712)
at `66a430bdc1a1d0372aad8badcc08db4260f79996` found exactly 61 full-only model
rows and 15,771 triangles, with no bare-only models. The full world has
4,569,858 triangles versus 4,554,087 bare; first 32 differences are shop models.
Artifact 11379999575 contains the full finite model delta, original build receipt
and executable pins (75,058 bytes; SHA-256
`9140768eedc45d6426172f3a846f6821e74a448b745a393b070013e76dd861ab`).

This checkpoint requires all 406 exact original object-library GEOs already in
the frozen UI/client package, physical identity
`c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43`.
The package also contains 521 player GEOs; those are not additional common
server object GEOs. No broad asset import or algorithm change is authorized.
Schema 3 uses `required_geometry_cold` and `client_visual_reopen`: both carry
all 406 required GEOs; the latter also has the actual 10,401-leaf visual tree.
Both fresh processes must match exact CRC/date/counts/readback and 32 real routes.
NONE/partial sets fail closed.

The client helper prepares selected immutable GEOs before server-data cache
checkout/staging/seal and binds stable required geometry plus refresh policy into
the cache identity. A first preparation removes only owned private Atlas and
exact 406-derived `.bin/.dep/.bounds` caches, using the existing world allowlist,
and records their original pins. Native flattened map caches can retain missing
models and do not track newly supplied GEOs as freshness dependencies.
Imported definition bins, unrelated caches, source assets and saved databases are
preserved. Unchanged warm preparation performs no ZIP decode, payload hash,
cache scan/removal or restaging. Old NONE cache trees are retained but cannot be
reused under the new identity. The separate prepared server-cache donor accepts
only `data/server/bin/<leaf>.bin`, so cannot reinstall removed geometry caches.

The new recovery workflow authenticates the original failed run/source, actual
successful compile, artifact 11379217768 (33,296,543 bytes; SHA-256
`a23fe422656874009013f56bc8a41a243a0511afb1d4fcb828196c03054731a4`),
original source/build receipts, exact retained executable and primary native proof.
It then runs two new, source-bound fresh geometry proofs. Original four-role
generation and new qualification remain separate; no recompilation or repeated
77-minute generation fallback occurs. The original graph bytes, now qualified by the two fresh layouts, are:
39,069,559 bytes, SHA-256
`6a3c9a6661a07cc3aec3a11baa9ca29395cc9b64d783b21e58282b2eb20845f8`;
date is 12 bytes, SHA-256
`ce64be4b49e4a8a4e61f01b31c651e603dc955551fb5c471ad3b75d2bb4f1711`.

Source review of recovery, finite cache refresh, fixtures and launch order passed.
Actual recovery run [37390562231](https://github.com/Russianranger/coh-android/actions/runs/37390562231)
at source `d856c41b586c87fd2d093eaa4d17c28d3508b66d` passed the exact donor
audit and **161 targeted tests in 29.311 seconds** (job 112034358727).
Windows recovery/readback job **112034867969** and the overall run completed
**SUCCESS at 2026-10-06 00:05:14 UTC**. The actual native witness confirms
CRC `0xb0c21ded`, all recorded graph counts, version-9 date, full readback and
32 routes in each fresh required-geometry layout. No current compile or repeated
generation occurred. Native artifact **11381731123** is 33,402,802 bytes,
outer SHA-256 `c077f5cd6b231e6c6cc52af31e93ef9400d71bedd7754aee9946e6d00f4b4f8b`.
The generated graph ZIP is 16,150,904 bytes, SHA-256
`0c7f602d31a438c6e67409bbb89da5d45ee3aacf13c96a50de9401d7973b2949`.
Artifact **11381885926** separately retains original-host evidence (33,542,063
bytes; SHA-256 `24702896eefbb7b72ec07ee0f0bfda5dd160e63be675179514b4461310505e19`).
Read-only verifier [37392459561](https://github.com/Russianranger/coh-android/actions/runs/37392459561)
at source `72b764a0e3c9cf10028be7ccfda85d9ad59ea4c8` completed **SUCCESS**,
including all **57 routing tests in 0.438 seconds**. Its cloud receipt confirms
the actual original FAILED source, original four-role generation, new owned roles
0, two fresh native processes, both required-geometry proofs, empty owned geometry
caches, exact full 10,401-leaf visual layout and unchanged source/graph/date pins.
The manifest is 934,650 bytes, SHA-256
`ee11bb703eed85229948b30b41277c515faf80da31ccd0436171862765ba41f4`.
Guest archive size/hash and manifest hash are now frozen to these actual outputs.
Verification artifact **11381776802** is 7,750 bytes, SHA-256
`c14a095a5db87289244ca7ac03c46f09a27f6db2d33d523d99f8c80bc426444c`.
First verifier run 37392236344 stopped in its routing precheck: default shallow
checkout omitted HEAD^ required by the actual-change-set test (git exit 128).
Its artifact download passed; the pin-check step did not run. Fetching two commits
fixed this setup error, and the retry above passed every precheck and native pin
gate without skips. Native generation inputs and C/MapServer are unchanged. Preflight includes source/recovery,
guest, actual production runtime, packaging, finite change classifier and all 26
server-cache reuse fixtures. Only the exact future full-publication workflow test
is held while the preparation workflow remains active; final qualification must
restore it and run all 68 suites with seven actual PostgreSQL fixtures.

The successful UI preparation remains run 37379767112 at source
`52da9286c2fd1695c6c0c2979378fc418c418c99`, artifact 11373610942.
It adds 788 exact original UI resources while preserving all 9,613 prior encoded
streams. Do not rebuild this accepted artifact unnecessarily. Graph guest pins
are frozen to verified native outputs. The full publisher is enabled with actual
successful native recovery run 37390562231/source d856c41 and frozen successful
UI preparation 37379767112/source 52da928. The final full-workflow test is restored;
Actual release workflow [37392793426](https://github.com/Russianranger/coh-android/actions/runs/37392793426)
at APK source **`25f821da9e782281953412543057054abd8dd320`** completed
qualification job **112042175166 SUCCESS**: all **68 distinct suites / 1,102
host scenarios / zero skips**. Both mandatory PostgreSQL suites passed all seven
real fixtures (three emission + four level-up), with PostgreSQL 16.15 initialized.
Exact source closure and donor conservation passed. Artifact **11381713754**
(`coh-ui-beacon-qualification`) is 6,137,683 bytes, SHA-256
`4c42683fe1cad44f6bed1df5f0a649d36b0bc68761f91f2ad26e78d4ecc60c8a`.
APK job **112043909987** completed the build/signing/publication/checksum gates,
then failed the separate manifest audit described above. Do not claim APK availability or public audit success
until its actual gates complete. This docs-only checkpoint changes no APK
source/input and does not trigger the active publication lane. Candidate identity
is **0.13.14 / code 29**, unchanged app ID and signer. Payload boundary remains
65 donor-identical assets + 7 reviewed replacements + 3 additions. Physical UI,
NPC pursuit, saved-character reopen and new phase timing acceptance are pending. Main is unchanged, PR #1 stays draft, and zoning is later.

Earlier pending-run checkpoint follows; its pending/optional-profile statements are historical.

**UI sweep ready; corrected host compiled and passed 114 targeted tests. Genuine Atlas graph proof is running. Next candidate: 0.13.14 / code 29.**

The preceding real generation finished, but its later CRC marker used a
different runtime phase and failed qualification. Authenticated forensic run
**37376054116** recovered a fresh ordinary-map traversal with 4,569,858
triangles and CRC `0xb0c21ded`, accepted by the original native date matcher.
The later marker was `0xfe75bab6`. The exact cause of that later-state drift
is unproved; the sidecar format and matcher elision hypotheses were ruled out.

The host wrapper now calls the original fresh matcher unconditionally, stops
on false and captures its newly computed full-world CRC immediately before
navigation loading. Reader version, graph counts/connections and all 32 real
routes also have explicit fatal failure gates. Python requires one preceding
fresh CRC marker, the final full-readback/path witness and the untouched
12-byte version-9 sidecar CRC to agree exactly. Both fresh native profile
processes must still return the same complete witness and physical inventories.

Actual generated graph/date files are now captured with bounded pins into
explicitly unqualified diagnostic evidence before validation, including a
failed server's output. A later proof failure cannot silently lose them.
Bounded 60-second owned-role heartbeats improve host diagnostics. Actual run
[37377053417](https://github.com/Russianranger/coh-android/actions/runs/37377053417)
at generation source `3124723b93b4ae83b211f9319ffa8d6d8a3e851d` passed
**114 targeted tests in 17.390 seconds** (job 111988749980), including source,
fixture, missing/conflicting/late marker and evidence-retention cases. Independent
source review found no blocker. Windows job **111989203448** passed fresh
Win32 compilation and began its combined preparation/generation/readback step
at **2026-10-05 21:47:27 UTC**. New genuine graph/profile qualification is
pending; no failed graph or old path proof is reused. This docs-only checkpoint
changes no generation source/input and must not restart the active lane.

The previous owned phase was about 77 minutes, following about 12 minutes of
host input preparation. Keep its 90-minute owned deadline and each bounded
fresh-profile deadline; no timeout failure occurred. The current actual run must
complete genuine generation and both profile proofs before
freezing graph pins and enabling final 68-suite/seven-PostgreSQL-fixture signing
and public APK download audit. No 0.13.14 APK is published. The frozen UI sweep
adds 788 original resources while preserving all 9,613 prior streams. The
current `android-ui-beacon.yml` is **preparation only**. Its actual hosted run
[37379767112](https://github.com/Russianranger/coh-android/actions/runs/37379767112)
at exact source `52da9286c2fd1695c6c0c2979378fc418c418c99` succeeded (job
111998412560). The frozen pair and all 9,613 retained encoded streams passed.
Unexpired artifact **11373610942** (`coh-ui-beacon-visual`) is 907,668,082 bytes,
outer ZIP SHA-256
`ffd0e9e667ef460c662bdd8808d00a74600a61943c507e19daaadc162e97b364`.
Its inner UI ZIP remains 859,075,775 bytes, SHA-256
`5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60`;
plaintext manifest is 48,591,999 bytes, SHA-256
`8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2`.
This preparation did not restart or cancel native run 37377053417. Full
publication remains held. After real graph success and frozen
guest pins, replace that preparation workflow with the reviewed full publisher;
optional UI reuse requires the exact successful prep head/run and both frozen
size/SHA pairs, followed by all final conservation and qualification checks.
Main remains separate, PR #1 stays draft, and zoning remains a later pass.

Unmerged reviewed drafts are retained as exact Git blobs in this repository:

- Successful-native cloud verifier: `062a229425ac9d494cea2ae65c34915373f96450`.
  Replace the current forensic-only verification workflow only after native
  run 37377053417/source 3124723 completes successfully; parse its actual
  `COH_ATLAS_BEACON_CLOUD_VERIFICATION_V1` evidence for graph pins.
- Full UI/beacon publisher: `3b5e575e02a754433a1d5602fc5ad2880ae0fc5d`.
  This draft reuses only successful native run 37377053417/source 3124723
  and successful exact UI prep 37379767112/source 52da9286, with all
  provenance, current source, physical profile and frozen size/SHA gates.
- Full final workflow-contract tests:
  `b2bc7404158a2f0091e9043ca120cce4f5edbedc`.
  Restore with the full publisher after freezing the guest's three actual
  graph constants. The current committed tests support preparation only.

Independent final review found no blocker in the held publisher: all 68
suites and seven PostgreSQL fixtures remain mandatory without skips; 75
runtime payloads comprise 65 identical donor payloads, seven reviewed
replacements and three additions; app ID and retained signer are unchanged.
Final SDK checks and the full public-APK download audit must pass. These are
reviewed gates, not completed final execution or physical acceptance.

Focused cache review found no runtime sidecar rewrite: the pinned original
`beaconDoesTheBeaconFileMatchTheMap` calls the CRC reader, which opens the
version-9 date with `rb` and changes only in-memory state. Timestamp-based
freshness is disabled in this path; ordinary `beaconReload` reads the graph.
The date writer is reached by native graph generation, not normal loading.
Guest fingerprints exclude atime, so native reads preserve warm reuse;
changed graph/date contents are validated and refused rather than silently
replaced. No additional cache or shipped MapServer change is needed.

Earlier actual CRC failure checkpoint follows; its investigation status is historical.

**UI sweep ready; Atlas generation completed, but CRC qualification failed. No 0.13.14 APK is published.**

Actual native run [37363692462](https://github.com/Russianranger/coh-android/actions/runs/37363692462)
at source `57515789dfafab5c4eab3273c63e28beef20264c` passed 106 focused
tests, the exact donor audit, fresh host compilation and both physical input
inventories. The owned server returned zero and graph/date files existed.
Python then rejected the native witness at **2026-10-05 21:13:57 UTC**:
`Native loaded-world CRC and date sidecar differ`. This was a post-generation
qualification failure; the two fresh profile checks had not run.

The unqualified server marker reported CRC `0xfe75bab6`, 163,544 combat
beacons, 163,527 connected beacons, 1,805,050 ground connections, 2,698,868
raised connections, 602 blocks and 32 paths. These emitted values do not
establish accepted graph/CRC/profile proof. The pinned original sidecar
writer and reader agree on exactly 12 bytes: S32 version 9, U32 newest time,
U32 full-world CRC. Do not change that format or relax CRC equality.

Failure artifact **11370824751** contains 13 evidence files, 16,790,903 bytes,
ZIP SHA-256 `f5ea6e160a16fcd37971daf3fb8ee1e60f63ab03420da6e360b57d144dce79f1`.
Its fresh host executable is 6,880,256 bytes, SHA-256
`f21980e4b973e4e774b07ffc589e9fb9f9be667e01e3bcfb37a3d4cef938e1b5`.
The old failure collector did not retain the generated graph/date. A targeted
producer draft now captures bounded, explicitly unqualified output before
validation and prints bounded role heartbeats; it needs hosted tests before use.

Read-only forensic run **37375223395** authenticated the actual failed artifact
and recovered role markers/tails. The next forensic revision extracts the
earlier CRC/date lines and compiler flags. Review the freshly computed matcher
CRC, file aliases and optimized-build validation semantics before choosing a
source correction. Preserve strict full readback, native paths and both fresh
profiles. Freeze graph pins and commit the held publisher only after genuine
qualification succeeds. Main remains separate; draft PR #1 remains open.
The UI payload stays frozen at 788 additions; zoning remains a later pass.

Earlier active-run checkpoint follows; its pending status is historical.

**UI sweep ready; corrected host compiled; genuine Atlas graph proof is running. Next candidate: 0.13.14 / code 29.**

Source milestone: `57515789dfafab5c4eab3273c63e28beef20264c`.
Actual run [37363692462](https://github.com/Russianranger/coh-android/actions/runs/37363692462)
passed **106 focused tests** (12.451 seconds) and the SHA-pinned public-donor
audit. Windows job **111946023236** correctly refused the old incompatible
host compile, then compiled the corrected source successfully. Its native
generation/readback step began at **2026-10-05 19:44:23 UTC** and is still
active at this documentation checkpoint. No completed failure or successful
graph/profile proof is available yet; no 0.13.14 APK is published.

This docs-only checkpoint changes no generation source or input pin and must
not restart the active native lane. The next result must come from the actual
owned roles, full graph/CRC readback and two fresh profile processes with
32 successful paths each. Do not infer role readiness or graph qualification
from elapsed time. If successful, verify the actual package with the held
cloud verifier, freeze its real manifest/archive pins, then run the final
68-suite/seven-PostgreSQL-fixture/signing/public-download qualification.
The held verifier/publication drafts target run 37363692462 and actual source
57515789, and remain uncommitted until that run completes successfully.

The executor remains unavailable; hosted jobs are the execution evidence.
Main remains separate and unchanged. Keep ordinary fast-forward checkpoints
on the continuation branch and leave draft PR #1 open. Zoning remains later.

Earlier bind-repair checkpoint follows; pending statements below are historical.

**UI sweep ready; native Atlas port-bind repair ready for proof. Next candidate: 0.13.14 / code 29.**

Actual run [37361394686](https://github.com/Russianranger/coh-android/actions/runs/37361394686)
at `ba99eeb1ee242cb14aefb054f36b65a253d51087` passed **104 focused tests**,
the exact public-donor audit and source-compatible host compile reuse.
The directory-case repair is now executed and verified: **5,231 cold inputs
and 406 optional GEOs**, zero missing/extra/changed byte pins in either layout.
Cold inventory SHA-256 is
`3bd8cd7305d8066adb2e2ae88bf761d4bcac546c786257027e0b7d28f5a15a08`;
full inventory SHA-256 is
`039f2a761ac11c01338ec1060a8656c6a9c833dc47b294a65d4dfa90648555f8`.

Master, sentry and worker stayed alive; server exited 3 at
`beaconServerInitNetwork` with “Can't bind any ports in range 48812-48912”.
The recovered stack and native API show a concrete host-patch error:
`netInit(NetLinkList*, int udp_port, int tcp_port)` received an IP integer in
its UDP-port argument, so the roles collided on unintended UDP port 127.
This attempt did not reproduce the prior heap corruption. Failure artifact
**11367521746** is 16,525,519 bytes / SHA-256
`6cfc200ceef59a74ef53cc1bf6e5911d161fd8f2fc0189dddc0a4e24e254fc1f`.
It contains no accepted graph or path proof.

The repair restores the original TCP-only `netInit(..., 0, portToTry)` call
and forces `COH_GAME_LOOPBACK_ONLY=1` before every owned process starts.
The retained accepted startup activates that policy before common startup and
verifies bound address/type with getsockname/SO_TYPE. No port-range expansion
or assertion weakening is needed. New guards bind the real API signature,
original call, activation order, endpoint checks and inherited-env override.
Native source changed, so the old compile receipt must fail compatibility
and trigger fresh compilation. The native algorithms and shipped Android
binaries remain unchanged. Hosted proof of this latest repair is pending.

Hold graph pins and publication until genuine generation and both fresh native
profile readbacks pass the same collision CRC, full graph counts and 32 paths
each. The final APK also requires all 68 suites (including the held publication
workflow test), seven real PostgreSQL fixtures, retained signer and full public
APK download audit. No 0.13.14 APK is published. Zoning remains a later pass.

The local execution connection remains unavailable; new execution claims come
only from actual hosted jobs. Continue ordinary fast-forward commits on the
existing continuation branch and keep main unchanged. The held publication
and verifier workflows must be repinned to the next actual successful native
run/head; run 37361394686 failed and must not be accepted as graph evidence.

Earlier case-repair checkpoint follows; its pending statements are historical.

**Full UI sweep ready; actual Atlas graph remains unqualified. Next candidate: 0.13.14 / code 29.**

Latest hosted run [37357540374](https://github.com/Russianranger/coh-android/actions/runs/37357540374)
at `780b030b73fef34b5000b7303ba4fe828020a229` passed the actual public-donor
audit and **88 affected functional tests** (Ubuntu job 111923655360), then
compiled the unchanged host producer successfully (Windows job 111924222126).
Its importer/pre-role assertion retained decisive diagnostics: all **5,231 cold
inputs matched exactly**; the full layout had **405 missing lowercase-directory
keys and 405 extra canonical-directory keys, with zero changed byte pins**.
Examples include `fx` versus the importer's established `FX` directory.
Failure artifact **11366950301** retains the executable/PDB, build input,
importer and bounded profile evidence. No native role was started, no graph was
accepted, and no 0.13.14 APK is published.

The earlier rich-metadata explanation is disproved by the real donor audit:
all 406 optional records already contain only `bytes` and `sha256`; both raw
and physical SHA-256 equal
`c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43`.
The raw/physical contract separation remains useful, but was not the failing
condition and is not claimed as a verified repair. The guest optional-geometry
constant is now frozen to that actual audited identity; graph archive/manifest
pins remain pending.

The current repair uses the shipped world resolver's exact function bodies
for host preparation and its ordinary API on Android. It reuses existing
case-insensitive parent directories, preserves exact immutable leaf spelling,
rejects case aliases, maps actual inventory back to declared logical names
bijectively, and binds resolved physical paths in warm fingerprints.
Case-insensitive Bin/GeoBin/Server roots remain private in the cold mirror.
The authoritative resolver is now the eighth generation-source pin.
Six host and ten guest/profile regression cases cover this boundary.
Hosted preflight must execute these changes before actual native generation.
The C containment patch, native algorithms and shipped binaries are unchanged.
The retry may reuse only the exact successful host compile from the retained
artifact: authenticated run/job/step identity, ZIP bytes/hash, fresh native
build-input equality and actual Win32 executable identity are required. The
reuse receipt is bound into new generation evidence. No graph or role proof
is reused from that failed attempt.

Both fresh native profile readbacks must still prove identical real collision
CRC, full graph counts and 32 successful native paths each. Do not relax these
proofs, hide the warning, fabricate a graph or use the failed attempt as a
successful generation artifact. Only the explicitly uncommitted publication
workflow contract test is outside the focused preflight scope; final **68-suite
qualification and all seven real PostgreSQL fixtures** remain mandatory.

The local execution connection is unavailable. New source changes have no
local execution claim; hosted Actions provide executable verification.
Repository updates preserve the continuation branch and main through ordinary
fast-forward GitHub tree commits. The unpublished packaging workflow was
reconstructed from its authored excerpts and committed CLI contracts; this
does not claim byte-identical recovery of untracked files. Hold publication
until successful native evidence, verified graph pins and final qualification.

Earlier checkpoint details below remain historical.

**0.13.13 Thor reopen, training, save and persistence verified; UI sweep and Atlas beacon generation in progress for 0.13.14.**

Latest packaging checkpoint: `15a27d4da0665ab9c05ba1e3ddb0417e69196741`
on the existing continuation branch. The full UI sweep, fail-closed graph
installer, packaging gates and Thor testing notes are committed. Native run
**37343908071** recovered the exact inputs and compiled successfully, but its
master role exited before readiness. The mixed Windows-drive evidence upload
also failed, so no native graph or valid generation artifact was produced.
The source audit found an invalid empty progress environment variable in the
host roles, consistent with an early startup exit; the lost master log prevents
direct confirmation of that branch. The retry removes that variable, corrects
native FileWrapper stream setup/flush handling, enforces absolute role paths,
records bounded failure tails/exit codes, and copies build evidence into one
repository-drive tree before upload. Cross-platform checkouts retain exact LF
source bytes. Shipped binaries and progress instrumentation remain unchanged.
Guest archive/manifest pins remain pending. No 0.13.14 APK is published yet.
The packaging boundary passes 13 targeted checks and independent review.
The consistent local broad regression passed **1,030 scenarios / 67 suites**
without skips; this does not include real PostgreSQL execution. Full hosted
qualification with all seven real PostgreSQL fixtures remains mandatory.
Reuse a successful native artifact only after verifying its unchanged
producer/world identities.

Host retry fixes are pushed at `a81fcbbe77154fec4b6409fbc05e65e777c0878f`.
Native run **37347246417** passed master/sentry readiness, then the sentry exited
with heap-corruption status `0xc0000374`; graph generation did not complete.
Failure evidence artifact **11361951686** is preserved (ZIP SHA-256
`03a8f9eb47ea41817804f85ce1c4f25d3898df7a3d73a8a9099add633ba20074`).
The audit found an unsafe EString command-builder still evaluated at the
stubbed host relocation callsite; the host callsite is now removed, server
relocation arguments are skipped, and native self-update is rejected. Short runtime
paths and failure JSON before ASCII-safe console tails avoid further lost
diagnostics. This is isolated host producer work, not a physical Thor crash.
A subsequent production cache audit
reproduced two legitimate server layouts: retained pre-visual cache has no
visual-exclusive object GEOs, while a cache rebuild after client preparation
can acquire all **406 object GEOs / 16,559,517 bytes**. Client preparation occurs
after Atlas readiness, so neither layout may be assumed universally. Do not
freeze or ship the current single-layout generation output. The next proof
must read the same graph in fresh cold/full processes with matching native
collidable-triangle CRC, full graph reader and 32 native paths per layout, or
resolve the exact required collision geometry if the CRCs differ. Preserve
existing cache/geometry behavior and avoid preloading client UI on the server.
Three production staging/cache integration fixtures now reproduce cold, full
and mixed layouts; 71 affected profile/classifier/package checks pass. The
full qualifier is extended to 68 suites; final hosted execution remains pending.
The native retry lane passes four source guards and seven producer/evidence
tests. Its short `C:/bcn-run/r` and `c` runtimes preserve private cold caches;
both profile readers run in separate native processes. The graph remains
unqualified until this exact lane produces real matching native evidence.
Schema-2 guest installation is implemented and remains fail-closed on pending
native archive pins. Eight installer tests and ten production cache/profile
integration tests pass, including rejection of mixed geometry, wrong bytes,
unlisted GEOs, mismatched collision CRC and incomplete native path proofs.
These test fixtures are synthetic and do not qualify a real graph.

The live continuation branch and draft PR #1 were rechecked at
`6098d5e040d9a41654acec60e92c64be2b5aacee`; main remains separate at
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`. The current published test APK
remains **0.13.13 / code 28**, implementation
`be955678b4b82f889b31c4071b3b979b0aef6771`.
[Device results](ANDROID_UI_BEACON_DEVICE_RESULT.md) and
[finite evidence receipt](android-evidence/ui-beacon-0.13.13-device-result.json)
capture both new 2026-10-05 physical Thor exports.

The first session bought **Aimed Shot** through the native trainer at displayed
level 2, returned to gameplay, and saved **140 XP / 103 influence**. The next
session reopened with that level, XP, influence and all fifteen powers retained,
including every original positive power UniqueID. No runtime crash occurred and
both sessions completed clean shutdown. The diagnostic exports themselves
failed retained-row qualification: the first rejected training mutations, the
second rejected eleven stock automatic-power set-level normalizations. Their
native purchase/logout and committed SQL evidence remain independently valid;
do not describe these exports as passed qualification. The diagnostic repair
now handles actual lowercase attribute-map comparisons and only the exact
native load/save normalization, while preserving strict save checks.
[Validation repair](ANDROID_TRAINING_VALIDATION_REPAIR.md) records 19 targeted
scenarios and 59 retained save/reopen/task/ground scenarios, including both
actual SQL transitions. Private logout sender receipts in that host replay are
synthetic and do not retroactively pass the historical device reports.

Warm captured timings: **Atlas 210.356 s (3:30.356)**, **actual client 188.310 s
(3:08.310)**, operation start to observed login **556.889 s (9:16.889)**, and
login to world **84.519 s**. The user's client stopwatch was about 3:03.
The client phase is materially shorter than 0.13.11's 324.792 s warm phase;
Atlas remains around 3:30. Warm visual preparation reused its verified
fingerprint with zero archive reads, decoded files or installed files.
Keep setup, visual preparation, texture preparation/wait, Wine/FEX, native
dependency preload, client initialization and user login/world time separate.

The next authorized pass is a complete bounded original-client UI dependency
sweep plus **real Atlas beacon generation/loading**, with zoning deferred.
Inspirations and power icons are now visibly restored. Remaining photographed
issues include tips, enhancement slots/inventory and some NPC/status/nameplate
white squares. Verify the native semantics of the trainer's right pane before
calling intentional empty content an asset failure. Both Atlas logs explicitly
report the generated beacon file missing. Existing authored beacon placement
layers are not a generated navigation graph, and disabled legacy generation
commands must not be enabled as a substitute for the active native generator.
Preserve all working assets, character data, cache/freshness, controls and timing
instrumentation. Do not repeat broad world/model imports.

[The UI sweep](ANDROID_UI_TEXTURE_SWEEP.md) is now frozen: **788 exact original
textures / 23,704,759 decoded bytes**, for **10,401 visual leaves**. All 9,613
previous encoded streams remain byte-identical. Actual source ranges reproduce
the exact new ZIP and runtime manifest. The 184 UI modules, shared controls,
2,551 enhancement definitions, tips, overhead bars, ring/highlight overlays and
contact-marker dependencies were audited; 23 unavailable donor names stay
explicit without substitutes. The level-2 trainer's third Pool/Epic pane is
intentionally empty until displayed levels 4/35. The 35 new UI, 32 prior UI and
52 installer/cache scenarios pass. First updated preparation installs finite
new resources; unchanged warm preparation retains zero archive/decode I/O.
Physical UI confirmation remains pending.

The host-only native Atlas graph producer is staged and its six focused source,
CRC and transcript tests pass. Its standalone Windows workflow uses short
`C:/bcn-src` build paths and four owned localhost roles, preserving the real
generation/connection algorithms. It must pass a fresh ordinary loaded-world
CRC comparison, full native graph readback and 32 native path searches before
any graph can ship. Physical collision/group/trick inputs are pinned and proved
unchanged around generation. This executable never replaces the gameplay
MapServer; generation and Android graph consumption remain pending.
[The beacon installer](ANDROID_ATLAS_BEACONS.md) has eight passing scenarios,
including first proof, persistent warm reuse, changed geometry and mutations
that restore size/mtime/mode but change ctime. It exposes preparation timing and
never accepts pending native package hashes. Native host path checks use the
supported no-entity ground profile; the graph reader reloads a mutable map name.
Earlier host attempts stopped before compilation on standalone donor-helper,
reference-asset token and draft-asset read permissions; those are corrected.
The scoped permission follows the accepted server-cache draft-read workflow.
Source corrections supersede
unfinished host-only generation jobs and cannot replace published APKs.

**The 0.13.13 publication checkpoint below is historical; its pending physical
startup/training/persistence questions are now resolved by the evidence above.**

**0.13.13 published and independently public-byte verified; Thor reopen/training test pending.**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.13/COH-Atlas-Gameplay-0.13.13.apk),
version **0.13.13 / code 28**, source
`be955678b4b82f889b31c4071b3b979b0aef6771`. Continue the existing continuation
branch and open draft PR #1. Main remains
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`.
This publication documentation descendant does not imply another APK build.

[Production CI 37324515114](https://github.com/Russianranger/coh-android/actions/runs/37324515114)
passed all four jobs: fresh OptDebug Win32 DbServer, unadapted MSVC Win32
production thread formatter/EString and retained save contracts, **985 scenarios /
64 suites / zero skips / 6,815 source pins**, all seven real PostgreSQL save
fixtures, exact public 0.13.12 donor conservation, official SDK signature,
badging, alignment and version-only manifest checks, then publication.
The public APK is **1,535,592,811 bytes**, SHA-256
`81f199d6380faa09261a85efea6fd3abca6ed58749b8cc68c75d1cd579d454a4`.
The retained signer remains
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
[Independent publication receipt](android-evidence/reopen-startup-repair-0.13.13-publication.json)
binds a fresh public APK/notes/checksum download, release API digests, current
native package, qualification, source pins and artifact digests. All **72
payloads verify: 67 retained / five replaced / none added**. All 9,613 visual
leaves, 123 UI additions, Game, MapServer, twenty DLLs, native training helper,
Android DEX/resources, nineteen Java sources and caches remain exact. Local SDK
signature/badging rechecks were not performed; the hosted checks bind the
identical independently downloaded public SHA.

The [latest supplied device report](android-evidence/reopen-startup-repair-0.13.12-device-result.json)
was `coh-atlas-gameplay-20261005-135502.zip` from **0.13.12**, SHA-256
`d96a393d681b8068e84b0d2647997996b9cf42a568d969255fd6536a6e14209f`.
Reopen ended after 94.328 seconds inside DbServer, before MapServer or the client
started. SQL connected, then `quick_sprintf.c:101` asserted: the hosted
TaskThread header path is 123 bytes, and `x_beginthreadex` adds `(110)`, requiring
129 bytes including NUL in its old 128-byte diagnostic name buffer. The assertion
reporter opened TCP 52015; the endpoint guard correctly rejected it. Keep that
guard strict. Cleanup passed. No training, character-select/world entry or live
XP/level/power SQL snapshot was captured, so do not claim persistence loss or
client/Atlas speed measurements from this failed startup.

0.13.13 uses a temporary EString for the complete diagnostic thread name and
releases it after synchronous SetThreadName. The fresh DbServer is 1,664,512
bytes, SHA-256
`ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba`.
CRT thread arguments/results/IDs, freeze/naming calls, global formatter/assert
policy, FIFO and commit-before-ACK remain intact. The PostgreSQL reader repair's
patched source hash remains exactly `8eaae13bf59dbee9b76ee0c3dff447eef080eb83e943f546ba0da70d0b42c295`.
[Repair details](ANDROID_REOPEN_STARTUP_REPAIR.md) and the production fixture cover
the exact old assertion, 127/128/129-byte boundaries, longer paths, allocator
retry, thread creation failure and diagnostic lifetime. No listener exception,
SQL error suppression, database reset, asset reimport or foundational rebuild.

[Focused Thor instructions](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.13/COH-Atlas-Gameplay-0.13.13-testing.txt):
install over the existing app, Set up runtime once, keep all data. First verify
reopen reaches login, character selection and Atlas. Record setup/resource
preparation, Atlas, actual client, login-to-world and total timing separately.
Inspect inspirations, XP/level bubbles, tray labels, trainer controls and power
detail icons; train at Ms Liberty, choose a power, press Next, finish/close the
dialogue and confirm normal gameplay. Ordinary save/log out, Finish and export;
reopen again to verify level/XP/new power and export the second report. If startup
fails, stop and export once rather than repeating long boots. Existing creation,
tasks and known-good world/model milestones do not need repeating.

**Physical reopen, training/power persistence, UI restoration and startup
savings remain pending.** Preserve the 0.13.11 native phase baselines: Atlas
235.342s / 208.616s, actual client 334.499s / 324.792s. Five exact donor UI stems
remain unavailable; no substituted assets were introduced.

An automatically triggered historical Wine listener run
[37324515168](https://github.com/Russianranger/coh-android/actions/runs/37324515168)
timed out after 30 seconds compiling an unchanged MSVC listener fixture before
any assertions ran. It does not feed this release. The current production Win32
and PostgreSQL checks passed; no listener policy change was made for that timeout.
Historical 0.13.12 publication jobs correctly skipped the new native-only scope.

**0.13.12 publication checkpoint below is historical; its first Thor reopen failed.**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.12/COH-Atlas-Gameplay-0.13.12.apk),
version **0.13.12 / code 27**, implementation
`e552fadeb1f392ab2574be16df6b474933c8ed00`. Continue the existing continuation
branch and draft PR #1. Main stays `04d62616e2e1b41b10f35a04d4c798e43680d5ba`.
This publication documentation descendant does not imply another APK build.

[Production CI 37315299321](https://github.com/Russianranger/coh-android/actions/runs/37315299321)
passed all five jobs: exact donor recovery and frozen UI discovery, actual Win32
DbServer production build and native contracts, **962 scenarios / 62 suites /
zero skips / 6,804 source pins**, all three retained and four new real PostgreSQL
transaction fixtures, retained-signer SDK version/signature/alignment checks,
packaging and publication. The first failed run `37314436172` remains historical
evidence; its unsupported CLI argument and Windows fixture handle cleanup are
corrected and covered by the successful current run.

The public APK is **1,535,588,715 bytes**, SHA-256
`ca692d986d7f8bf50d11be03348f07c436e7f3f1b6c5fab83e8ebe2bc932e749`.
[Independent public-byte receipt](android-evidence/levelup-ui-repair-0.13.12-publication.json)
binds a fresh public download, release digest, checksum/testing notes and current
hosted build/qualification. All **72 payloads** verify: **62 retained / nine
replaced / one added**. Game, all twenty DLLs, MapServer, Android DEX/resources,
nineteen Java sources, server archives/caches and all **9,490 original visual
stored streams** remain exact. The new helper only observes native training and
committed SQL; the production DbServer keeps rollback and commit-before-ACK.
Hosted official SDK checks bind to the same independently downloaded APK bytes;
local SDK/signature rechecks were not performed.

The **123 original UI textures** append 5,384,150 decoded bytes, for **9,613
verified leaves**. XP/level indicators, inspirations, tray labels and trainer
selection controls have exact source/donor witnesses. Archery/Devices power
detail icons were already present; native trainer rows use ownership checkmarks.
Five exact donor stems remain unavailable, without substituted textures.
The saved-character and retry routes now enable the existing qualified Game
metadata preload. Warm visual preparation reuses its verified receipt without
archive reads/decoding; source freshness, native timing and cache guards remain.

Use the [published focused testing instructions](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.12/COH-Atlas-Gameplay-0.13.12-testing.txt):
install over the existing app, Set up runtime once and keep imports/profile/DB.
Reopen THORHERO, inspect the missing UI, train at Ms Liberty, choose a power,
press Next and complete/exit dialogue. Confirm normal gameplay and the power,
ordinary Save/log out, Finish and export the complete outer support ZIP. Reopen
again to verify trained level/XP/new power, then save/finish/export the second
report. Record Atlas, actual client and login-to-world timing independently of
setup, first UI/header preparation and user input. No accepted creation/tasks or
safe-ground milestone rerun is required.

**Physical training/UI success and startup savings remain pending.** The prior
native first/second Atlas times were 235.342s / 208.616s; actual client times
334.499s / 324.792s. Preserve those phase-specific baselines. The prior 115 XP
persisted, but the old failed training transaction rolled back; this build's
actual level/power persistence requires the new Thor pass.

**Pre-publication recovery checkpoint below is historical.**

**Recovered 0.13.12 source checkpoint ready for hosted qualification; publication pending.**
Implementation checkpoint `1485dfa12236b66a3e409a0423f297ce9bc6ff3a` preserves
the cut-off agent's complete work and finishes training validation. Hosted
run `37314436172` reached donor extraction, then refused an unsupported
`--requests` discovery argument in the recovered workflow. The corrected workflow
omits it; the producer reads its frozen source requests internally. The new regression
parses the exact hosted command through the production argument parser.
The Windows save assertions also passed before a fixture cleanup failure;
explicitly close the reopened SQLite connection so Windows can remove its file.
Keep this failed run as evidence; it did not publish an APK.
Continue branch `codex/character-persistence-continuation` from live checkpoint
`8f602b83095989cc936fc77f89bacceb4a960aee`; draft PR #1 stays open and unmerged.
Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`. Preserve the accepted
runtime, imported asset packs, THORHERO database and completed gameplay work.
No broad reimport, project reset or original appearance-pack recreation is needed.

The complete [device evidence](android-evidence/levelup-ui-repair-0.13.11-device-result.json)
binds both October 5 outer reports and intact guest evidence. The user sees all
models, including the police drone, loading. XP increases **50 → 115**, and the
second reopen SQL snapshot retains **115 XP / 89 influence / login count 7**.
Internal level remains zero before training (displayed level 1); completed
training to displayed level 2 and its chosen power were not committed by the
failed transaction. Keep this distinction explicit in future status reports.

Native first/second Atlas startup is **235.342s / 208.616s**; actual client
startup **334.499s / 324.792s**. User stopwatches are respectively Atlas 3:55 /
3:28, client 5:32 / 5:20 and whole reopen 15:36 / 13:10. The second visual pack
reuses all 9,490 leaves, the existing texture index produces 19,930 hits with zero
ordinary header reads, and other stages improve. Both native logs have **zero
COH_CLIENT_DEPENDENCY_PRELOAD_V1 acknowledgements**: the saved-character route
never enabled the already packaged Game opt-in. The candidate fixes the actual
initial/retry launch environment, preserves shared Wine/server environment, and
requires the current typed Game producer. Physical savings remain pending.
The unchanged native Atlas sequencer stage is still about 54 seconds.

The second failure is local **DbServer exit 3**, after PostgreSQL **23505** on
`AttribMods(ContainerId,SubId)=(1,0)` at 11:36:11.836. FIFO records the failure
and withholds acknowledgement; the generic report wording "during login"
describes the health-check location, although world entry was already verified.
There is no captured native-client exception. The production reader drops a
physical NULL/default child-row witness when preceding parent/power fields have
already increased its cumulative line count. Later training then treats that
row as absent and emits a conflicting INSERT. The narrow new PostgreSQL layer
retains per-row witnesses and also orders single-container child reads by SubId,
which the unchanged merger requires. Parent/MSSQL queries, row/column emission,
normal missing-row INSERT, prior cancelled-insert fix, FIFO rollback and
commit-before-ACK remain intact. No ignored SQL failure, UPSERT or schema reset.

[Finite original UI receipt](android-evidence/levelup-ui-repair-0.13.12-assets.json)
records **123 original textures / 5,384,150 decoded bytes** appended over all
9,490 accepted leaves. These cover XP bubbles, 27 standard inspiration icons,
five F-key labels and trainer selection/menu controls. Archery/Devices icons
already existed; the photographed power-row squares are owned-power checkmarks.
All 9,490 original stored streams and their complete ancestor recipe remain
exact. Five unavailable donor requests stay explicit, with no fuzzy replacement.
The composed pack is 9,613 leaves / 1,511,101,967 decoded bytes, ZIP
854,625,639 bytes, SHA `7a1760edc559871c0a99a15b9a52b8592e908a1c463b6e245edb99ecff6ac544`.

The intended next derivative is **0.13.12 / code 27**, from the exact public
0.13.11 donor and retained signer. It retains Game, all twenty client DLLs,
MapServer, server/cache payloads, DEX/resources, Java, imports and private state.
A finite read-only native purchase/SQL proof now recognizes this character's
first trained level (internal 0 → 1 / displayed 2) and preserves all prior
semantic powers by stable UniqueID, with native structural row renumbering
allowed only inside that witnessed transition. It accepts the exact successful
stock `BuyPower Click` log and corresponding selected power plus original
automatic grants. Thirteen untouched native/data producer files are explicitly
pinned. Only the typed current reader enables stock entity-category logging;
ordinary logout, native position, rewards and authored task guards remain.
The sequential host scenario trains/saves with native XP awards, then reopens
the exact trained character with its chosen power intact. All **962 local
regression scenarios / 62 suites** passed: 882 retained, 68 focused
persistence/UI/preload/package checks and twelve training scenarios.
Real PostgreSQL fixtures and full Win32 DbServer compilation remain hosted
qualification requirements. No physical fix or speed claim.
Formal real PostgreSQL fixtures, complete Win32 DbServer build, current payload
conservation, official SDK package/signature checks and publication are required
before delivering the APK. Do not describe this source checkpoint as a release.
Use [focused 0.13.12 instructions](COH-Atlas-Gameplay-0.13.12-testing.txt) after
publication; retain imports/profile, set up runtime once, train at Ms Liberty,
ordinary save/log out, and reopen to verify XP/level/new power.

**0.13.11 publication checkpoint below is historical.**

**0.13.11 published and independently public-byte verified; focused Thor comparison pending.**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.11/COH-Atlas-Gameplay-0.13.11.apk)
from implementation `a5ff474674393e898f9a5d4b3ad29ae51dd25a2a`, version
**0.13.11 / code 26**. Continue the existing branch and open draft PR #1.
Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; no merge, branch
recreation, accepted-milestone rerun or broad user reimport occurred.

[Production CI 37280737915](https://github.com/Russianranger/coh-android/actions/runs/37280737915)
passed all five jobs: exact Game source staging, real Win32 guarded freshness
qualification and Game-only build, frozen appearance discovery/materialization,
**895 scenarios / 57 suites / zero skips / 6,763 source pins**, all three real
PostgreSQL transaction fixtures, retained-signer official SDK version/signature
checks, APK packaging and publication. The staging correction binds Game to its
stock FolderCache, removes an unrelated Wine DbServer fixture patch and verifies
complete real production staging with stock-byte conservation and mutation
rejection. The actual native patch and frozen asset recipes remain unchanged.
Keep failed predecessor run `37260256058` as historical evidence.

The public APK is **1,535,252,759 bytes (about 1.43 GiB)**, SHA-256
`aa7c478797989a652594684fdb4c482422143680550ba164b77ee56db4dae1cc`.
[Independent publication receipt](android-evidence/client-startup-followup-0.13.11-publication.json)
binds a fresh public download, release API digest and exact hosted build receipt.
It verifies all **71 payloads: 62 retained / nine replaced / zero added**,
new source-bound Game, all 20 retained client DLLs, DEX/resources, server packs,
cache ancestry and every qualified source pin. Local official SDK rechecks were
not repeated; hosted checks bind to the identical independently downloaded APK.

All **9,490 visual files** pass decoded size/SHA, original-table MD5, native
headers and original stored-stream verification; all **5,476 immediate donor
compressed streams** remain byte-identical. The **4,014 original additions**
contain 462 GEO files and 3,552 textures, adding 632,462,533 decoded bytes.
Fresh hosted discovery reproduces the frozen plan byte-for-byte. Exact NPC
costume/model/material/alias/FX dependencies include the police drone and
Informant appearance. The Game-only metadata preload preserves ordinary
source selection, freshness failures, CRC and decoding; it does not preload
complete asset contents. DbServer and MapServer were not rebuilt.

Use [focused Thor instructions](COH-Atlas-Gameplay-0.13.11-testing.txt): install
over the existing app, run **Set up runtime once**, retain imports/profile/DB,
then perform one first and one subsequent saved-character reopen with the same
preset. Record local Atlas, actual client and login-to-playable-world separately;
keep setup/first visual installation/header preparation separate. Compare the
photographed faces/armor/drone and nearby/distant ground and world objects.
Ordinary Save/log out, Finish, then export the complete outer support ZIP with
its intact guest report and screenshots. Do not repeat accepted creation/tasks.

**Thor startup savings and physical appearance completeness remain pending.**
The last physical baseline is local Atlas **3:50 / 229.246s**, actual client
**5:22 / 319.732s**. There remain 100 exact donor/sequence/material dependencies
and 29 deeper source witnesses covering 22 targets; no fuzzy substitutions were
made. The unchanged Atlas sequencer post-load cost remains a separate future
server optimization. This documentation checkpoint is a descendant of the APK
source and does not imply another native/APK build.

**0.13.11 implementation checkpoint before qualification/publication (historical).**
Continuation recovered the exact `44fc834878b41814ddfcb7e08d33d96ff59eb424`
candidate and failed production [run 37260256058](https://github.com/Russianranger/coh-android/actions/runs/37260256058).
Appearance discovery/materialization passed, but Game staging refused the new
FolderCache source witness before native qualification or compilation. The new
producer incorrectly expected the separately built Wine DbServer's FolderCache;
the accepted Game PG/events/texture/graphics chain retains the stock file.
Its exact normalized SHA-256 is
`93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c`.
The correction pins that original source in producer and guest, removes the
fixture's unrelated Wine patch and exercises complete production staging with
stock-byte conservation and mutation rejection. No native patch or frozen asset
recipe changes. The failed run remains evidence; hosted Win32 qualification and
publication are still required before delivering 0.13.11.

Continue from the durable Thor evidence checkpoint
`ba876d2e27d9481c1262f19566c12ce3313ab1a3`, with the public 0.13.10 APK as the
exact immediate donor. This pass combines a bounded Game-only metadata preload
with an append-only original appearance supplement. Main, accepted runtime,
DbServer/MapServer, twenty client DLLs, Android DEX/resources, generated cache
formats, imports, profile and ordinary native reward/save proof are retained.
Neither 0.13.9 nor 0.13.10 is rebuilt or overwritten.

The client report attributes **65.796s** to power BIN freshness checks and
**149.238s** to all recorded BIN freshness checks, versus **18.032s** decoding
and **9.371s** opening. The original power file list has 4,539 dependencies
outside `defs/powers/`, under `Menu`. Before the existing checks, an explicitly
enabled Game-only layer requests the stock `Menu` metadata tree; the sequencer
path requests `player_library/animations`. These requests use the ordinary
FolderCache and retain loose/PIG timestamp selection, CRC validation, every
freshness failure branch and decoder behavior. No complete asset bytes are
preloaded and no persistent cache encoding changes. The exact caller guards,
original body equivalence, six native source witnesses and controlled lookup
reduction require source-bound Win32 qualification. **Thor startup savings are
unverified.** Atlas's **229.246s** native stage remains unresolved; its roughly
51-second sequencer post-load cost is distinct from BIN decoding and remains a
future server optimization target.

The appearance audit follows the exact retained Atlas map/encounter references:
44 maps, 18 exact encounter definitions, 1,048 NPC costumes, 178 EntTypes,
ten factions and their model, material, texture-alias and FX edges. It includes the otherwise silent police drone
`player_library/G_Police_Drone.geo` body and the Informant's `Model_Proton`
costume dependencies, cape/ground-effect layers, native aliases and dependent
FX models/textures. The final frozen set is **9,490 files: 5,476 retained +
4,014 original additions (462 GEOs + 3,552 textures)**. The earlier 4,012 scope
gained a traced megaphone GEO/texture pair; an intermediate 4,008 filter error
was corrected by restoring valid OneShotFX dependencies. No accepted file was
dropped. All 9,490 decoded sizes/SHA/original-table MD5/native headers pass, and
**all 5,476 prior encoded streams are byte-identical, including all 329 original
streams**. The new ZIP is **854,341,235 bytes**, SHA-256
`840619b3b40c24f206576580dfaedb779a66582f1df189f37002dd59c5399cb9`;
decoded payload is **1,505,717,817 bytes**, including **632,462,533 new bytes**.
The plaintext manifest is **42,257,673 bytes**, SHA-256
`8b3f579a9ff48e80f40e06e252c91fe3357daf9f0b01441dea5bceaa5801f1e6`.
Only these named visual inputs receive 1 GiB ZIP/64 MiB metadata/2 GiB decoded
bounds. Lossless source envelopes fit the existing source transport; the guest
receives the exact pinned plaintext. Fresh plan-only discovery reproduces both
frozen plan and request bytes. There are 5,776 appearance source pins, 1,388
composite aliases, 3,791 stock definitions and 70 native leaf backedges, with
zero ambiguous definitions, alias cycles or new retained-texture basename
collisions. See the [frozen asset receipt](android-evidence/client-startup-followup-0.13.11-assets.json).

Still unresolved in this finite scope: **100 dependencies** (five donor GEO
filenames, nine exact model names, three invalid native GEO model-count headers,
83 texture/material stems) and **29 deeper source witnesses / 22 unique targets**
(17 authored FX/behavior paths, two FX models, ten Parkour includes). The NPC
costume source graph itself closes without gaps; these are unsupported exact
donor/sequence/FX references, not failed downloads. Colon-prefixed behavior names
resolve against their owning FX directory, so same basenames elsewhere cannot
substitute. Historic `GEO_Collar_MAGIC` remains unsupported. Distant white
geometry, shader/material behavior and full physical visual completeness are
unconfirmed; no fuzzy substitutions or renderer/gameplay changes are made.

Local source/archive regression coverage is **57 suites / 894 scenarios** with
zero skips, and qualification resolves **6,763 source paths** without missing
files. Real hosted Win32 production qualification, three PostgreSQL transaction
fixtures, signing/publication and fresh public APK verification are still
pending. The [full-size host installation receipt](android-evidence/client-startup-followup-0.13.11-benchmark.json)
checks 4,014 additions, all 5,476 retained inode/byte/mode/timestamp identities,
Game/cache sentinels and absolute server links. Warm reuse of all 9,490 files
passes with ZIP opening, payload hashing and extraction forbidden. Its
2,509,324-byte marker fits the unchanged 4 MiB bound; fixture-inclusive host
peak is 242,108 KiB. Host installation evidence does not establish Thor timing
or memory behavior.

Use [focused 0.13.11 Thor instructions](COH-Atlas-Gameplay-0.13.11-testing.txt)
after publication: one first and one subsequent saved-character reopen with
the same preset, separate Atlas/client/login-to-world and first installation
timings, the photographed faces/armor/drone/world route, ordinary Save and
complete support ZIP export. Do not repeat accepted creation/task milestones,
clear app data or reimport existing assets.

**0.13.10 Thor follow-up and active startup/appearance continuation (October 5, 2026 UTC).**
The live branch was recovered at `37404945f3c53c0897c275beb94a2fec4ed915b2`,
after the accepted 0.13.10 APK source `9c36a5f411290400cb4aa4b2711a4bdcd39ca8cb`.
Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; use the existing
continuation branch and draft PR #1. The earlier transient checkout was gone,
but the published source, hosted sweep/packaging receipts and new local support
ZIP/screenshots were recovered. Do not redo the 0.13.10 milestone or overwrite
its release. The immediate 5,476 visual files are the next build's baseline.

The user confirms that ground and hands now load and substantially more models
appear, while white faces/armor and missing police drones remain. The raw
startup-only report passes, including ordinary Save and owned cleanup. THORHERO
keeps its identity, powers and costume; only native earned XP25→50,
influence14→28 and LoginCount5→6 change. These observations do not promote the
report's false full gameplay/rendering/controller qualification flags.
See the [pinned physical receipt](android-evidence/client-asset-closure-0.13.10-device-result.json).

Reported local Atlas is **3:50**, with stage **229.246s**. Reported actual client
is **5:22**, with native launcher **319.732s** and enclosing stage **320.203s**.
The first visual installation is separately **61.222s**: all 5,147 new files
installed and 329 reused. The client animation binding takes 14.320s and first
texture-header preparation takes 47.875s. Do not subtract these from the native
client duration or conflate total request-to-world time with a native stage.
The exported runtime manifest has a different serialization digest from the
embedded APK manifest; its parsed JSON content is identical.

The next bounded pass targets client filesystem metadata costs while retaining
stock freshness, CRC, source bytes and animation/gameplay behavior. New console
errors and silent ent-type geometry dependencies are being traced against the
original donor catalogue, retaining every existing visual ZIP member stream.
Publish a fresh 0.13.11 only after its relevant hosted qualification succeeds;
physical startup savings and remaining appearance fixes require focused Thor
comparison. Atlas's roughly 50-second sequencer post-load cost remains distinct
from the client BIN freshness costs and is not a reason to bypass validation.

**0.13.10 published and independently payload-verified; focused Thor visuals pending (October 5, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.10/COH-Atlas-Gameplay-0.13.10.apk)
from exact implementation **`9c36a5f411290400cb4aa4b2711a4bdcd39ca8cb`**, version
**0.13.10 / code 25**, on `codex/character-persistence-continuation` and existing
open draft PR #1. [Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.10)
is a published prerelease. Main remains **`04d62616e2e1b41b10f35a04d4c798e43680d5ba`**.
0.13.9 remains published from `7e905d6a9241848b4635a069a962c42382a9a200` and was
not rebuilt or overwritten. **Do not restart the sweep, recreate the branch/PR,
replace the accepted runtime or reimport existing assets.**

[Publication CI 37249488856](https://github.com/Russianranger/coh-android/actions/runs/37249488856)
passed all three jobs: **838 checks / 52 suites / zero skips / 1,162 source pins**,
all three real PostgreSQL transaction fixtures, official SDK version and v2/v3
signature checks with the retained signer, and publication.
[Fresh hosted discovery 37249488857](https://github.com/Russianranger/coh-android/actions/runs/37249488857)
passed 34 checks and reproduced the recovered final-v3 plan **byte-identically**.
The original Windows console-sharing PermissionError at documentation head
`09989889` remains a historical separate tooling failure; this candidate's
relevant hosted workflows passed, and accepted physical tests were not repeated.

The public APK is **1,194,150,167 bytes (about 1.11 GiB)**, SHA-256
`4c02b4f5f1ff9b82ab8b96fe5b4d2f402b687c3ee66ef1d8535a1a68f0c07d4a`.
[Independent publication receipt](android-evidence/client-asset-closure-0.13.10-publication.json)
checks a fresh public download, release/API/build digests, every one of the
**71 payloads: 64 retained / 7 replaced / zero added**, all qualified source pins,
all 5,878 original animation tracks, retained Game/20 DLLs, DEX/resources/server
binaries and cache lineage. It also verifies **all 5,476 final visual files**
against decoded size, SHA-256, original-table MD5/cached headers and frozen donor
metadata. **All 329 prior compressed streams remain byte-identical.** Local SDK
verification was not repeated; the official checks bind to this identical APK.
This documentation checkpoint descends from the APK source and implies no build.

The count remains exactly the recovered candidate: **329 retained + 5,147 added**
(**22 player GEOs, 390 object GEOs, 4,735 textures**). The visual ZIP remains
**515,813,056 bytes**, with **873,255,284 decoded bytes**, including **833,734,047
added bytes**. Source encoding is lossless; the packaged original manifest remains
**16,272,899 bytes / SHA-256 447868d63b0eea536cba6355fe69763e3d7b24a703a756b13e0ebafb4031a34b**.
Added categories address heads/body pieces, silent hand/glove failures, costume
textures, ground/bench/planter layers, material/geometry dependencies, native
aliases and FX geometry. Exact named larger visual input/staging budgets and
bounded report-only native reward acceptance are the only startup/server helper
exceptions. Native architecture and gameplay code are retained.

Still unresolved: **24 new exact names absent from the donor** (14 world, eight
NPC costume, two other/FX), plus inherited gaps. `GEO_Collar_MAGIC` lacks an exact
supported model in the retained donor namespace; no similarly named substitution
was made. Distant white geometry/material causes and physical visual completeness
remain unconfirmed. The prior raw device report remains failed; its legitimate
XP25/influence14 is now accepted only with exact owned native credit proof.

Follow [focused Thor instructions](COH-Atlas-Gameplay-0.13.10-testing.txt): install
over the existing app, run **Set up runtime once**, preserve imports/profile/DB,
then reopen THORHERO once with the same preset. Compare NPC heads/hands and pale
ground/white benches far and near. Record local Atlas, actual client and
login-to-world timings; keep first asset installation/header refresh separate.
Use ordinary Save/log out, Finish and export the complete outer support ZIP with
its intact nested guest report, plus screenshots. If a stage fails, Abort and
wait for owned cleanup before export. Do not clear app data, repeat accepted
combat/task/creation gates or require return-to-safe-ground testing.

**Next priority is the focused startup pass** against the observed **~4m15s
actual client / ~3m40s local Atlas** baseline. Do not claim savings from this
asset build or include first asset preparation in that client measurement.
Keep existing BIN freshness/decode and console/preparation instrumentation; use
new physical evidence to identify the remaining cost without discarding assets
or accepted gameplay. Visual, install/memory and ordinary Save acceptance on the
Thor are pending; software llvmpipe remains active.

**0.13.9 Thor evidence and recovered 0.13.10 asset implementation (October 5, 2026 UTC).**
The live continuation was confirmed at `09989889894861b0b91dadda113f000d033559f6`,
with open draft PR #1 and main still `04d62616e2e1b41b10f35a04d4c798e43680d5ba`.
The new [physical receipt](android-evidence/client-streaming-0.13.9-device-result.json)
pins `coh-atlas-gameplay-20261004-223940.zip` and all nine screenshots. The user
reports more visible models, continuing absent NPC heads/hands/gloves and pale
ground textures, actual client start **4m15s** and local Atlas stage **3m40s**.
Instrumented native readiness is **259.260s**, client stage **259.724s**, Atlas
stage **222.858s**; request-to-owned-Atlas is **322.451s** and is a different
boundary from local Atlas preparation. This is a modest client change, not a
new proven large startup improvement. Texture preparation takes **38.103s**.
The user successfully targets and defeats NPCs; screenshots show standing and
defeated Blood Brother Slicers and stock XP/influence/loot messages. Preserve
that demonstrated target/defeat milestone without claiming complete combat.

The raw final report is **failed**, despite world entry and zero owned workers
remaining: the reopen validator rejected ordinary earned rewards. Selected
`ents` rows changed only XP NULL→25, influence NULL→14, and LoginCount 4→5;
all selected `ents2`, seven powers and fourteen costume parts remain identical.
Two owned MapServer credits exactly total XP25/influence14. A bounded report
fix is being qualified that permits only exact native reward credits while
retaining identity, non-reward rows, task reward, logout and saved-position
checks. Do not classify the entire raw report as passed or clear device data.

The requested 60-minute asset sweep started **2026-10-04T22:42:58Z**. It covers
captured missing texture/material/catalogue diagnostics, all exact missing GEO
filenames, stock costume dependencies (including silently skipped glove models),
and every original model/material edge in the retained Atlas world GEOs. The
source console has **1,902,345 bytes**, SHA-256
`1f532e7a18c57b5e0cb77fa7e79d9d5f85dee628b7af6aa1a63de46995c9fba2`.
Some native diagnostic categories stop at 1,024 records; this finite evidence
does not prove complete global coverage. Resolve all exact original leaves and
all surviving blend/mask/bump/glow/enabled fallback dependencies without fuzzy
substitutions, native/render/cache changes, broad reimports or memory preloads. Only exact named
visual input and staging budgets are raised for the larger disk package.
Keep every immediate 329 visual leaf and its original compressed stream intact.
The new supplement deliberately has larger bounded disk/manifest ceilings and
streamed per-leaf installation. Record final bytes, pins, gaps and hosted/public
audit in this entry once the sweep and publication finish.

The interrupted workspace was recovered intact and reused. Independent replay
confirms **5,476 final files: 329 retained + 5,147 original additions**, comprising
**22 player GEOs, 390 object GEOs and 4,735 textures**. All decoded sizes, SHA-256,
original-table MD5, cached headers and stored streams match 57 frozen donor
metadata prefixes. All **329 prior compressed ZIP streams remain byte-identical**.
The archive is **515,813,056 bytes**; decoded total is **873,255,284 bytes**, including
**833,734,047 added bytes**. No further valid leaf was found after recovery; the
candidate and manifest remain identical to the recovered `final-v3` asset set.
Dependency replay covers 14,715 declarations in 1,585 stock trick files, 888
source pins, 488 retained world GEOs / 10,034 models and all 623 recovered missing
world-material leaves. Heads/body pieces, silent civilian/Vanguard/Rikti gloves,
ground/bench/planter material layers, aliases and FX geometry dependencies are
addressed. **24 new exact missing names** remain absent from the original donor:
14 world, eight NPC costume and two other/FX, in addition to inherited gaps.
`GEO_Collar_MAGIC` has no exact supported model among the 4,971 donor GEOs;
similarly named magic armor models are distinct and are not substituted.
Distant white-object rendering and physical coverage still require Thor evidence.

Recovery review found two real compatibility blockers: the retained startup
verifier capped this ZIP at 128 MiB, and server staging did not budget the larger
visual inventory. Narrow corrections permit only the named visual ZIP (512 MiB)
and manifest (16 MiB), and add the exact visual file/byte counts to staging.
Packaging conserves every unrelated startup/staging AST node, native binary,
DEX/resource and cache format. Seven of the 71 APK payloads change; 64 are retained.
The asset additions are disk installation, not memory preloading. Fresh physical
installation/memory and ordinary Save validation remain pending.

The source recipe uses a bounded lossless gzip/base64 JSON envelope because
GitHub's authenticated request limit includes JSON escaping and could not carry
the original 16,272,899-byte recipe. The 2,835,953-byte source envelope decodes
to that **exact original manifest SHA-256**; packaging writes the original raw
JSON, and the 515,813,056-byte visual archive is unchanged. Source envelope
and all decoded payloads remain independently pinned. No dependency evidence
or recipe fields were removed to meet the transport limit.

Startup remains the **following** priority. Preserve BIN instrumentation: this
run reports substantial freshness work (not pure decoding), especially powers,
FX, NPCs, costume and mapstats. Console identity work is only about 200ms across
144 observations; the full 104.964-second observer includes other work and is
not attributable to that parser. Do not skip freshness or invalidate stable
generated caches without bounded source/equivalence proof and device evidence.

**0.13.9 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.9/COH-Atlas-Gameplay-0.13.9.apk)
from APK source `7e905d6a9241848b4635a069a962c42382a9a200`, version **0.13.9 / code 24**,
on the existing `codex/character-persistence-continuation` branch.
[Release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.9)
is a published prerelease. [Dedicated CI 37233136368](https://github.com/Russianranger/coh-android/actions/runs/37233136368)
passed all three jobs: **742 checks / 46 suites / zero skips / 276 source pins**,
all three real PostgreSQL transaction fixtures, official SDK version and v2/v3
signature verification with the existing signer, and publication.

The public APK is **701,679,895 bytes**, **184,320 bytes** above 0.13.8;
SHA-256 `64644f8b82c7bde63304bc36009043dccacc171e5cae8df9d537cbadf4d60b9d`.
[Publication receipt](android-evidence/client-streaming-0.13.9-publication.json)
records an independent public download, matching release API and formal build
digests, all **71 payloads: 64 retained / 7 replaced / zero added**, all 276
qualification source pins, and all 5,878 original animation tracks. It checks
the exact immediate 0.13.8 Game/client DLLs, DEX/resources, server/cache lineage,
all 323 prior visual leaves and the six additions. Local SDK/signature
reverification was not performed; official CI checks bind to this identical
public APK SHA-256. The following documentation checkpoint is a descendant of
the APK source and does not imply another APK/native compilation.

The live repository was first confirmed at `af7e6a52926f842044b3115ae4729809df8997a2`;
0.13.8 was already published and has not been recreated. Read-only exact
candidate discovery is committed at `17f46d5e26fb04ef3411348c525343bc76013bdf`.
Continue the same branch and open draft PR #1; main remains
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`. No newer physical 0.13.8 result
was found. Preserve the accepted 0.13.7 device result and all prior milestones.

This wrapper preserves the exact public 0.13.8 APK Game/client ZIP, 20 DLLs,
corrected Android DEX/resources and 19 Java sources, DbServer/MapServer and server
packs, cache schemas, graphics and all animation tracks. It changes three guest
helpers, append-only visual payloads and two verification manifests only.
[Exact encounter evidence](android-evidence/client-streaming-0.13.9-assets.json)
selects six original NPC texture leaves (291,538 decoded bytes) from existing
first-encounter Atlas errors; no broad asset dump, user reimport or speculative asset replacement
is requested. All 323 previous visual leaf pins and compressed payload streams
remain intact; the complete supplement has 329 files / 39,521,237 decoded bytes.
Existing Hellion and selected vegetation repairs remain intact.

Complete current-console marker search avoids splitting every unrelated native
line while retaining every session/PID/duplicate/retry check on every call.
`client_console_identity_metrics` separates decoding/identity parsing from the
broader observer hook, whose old 83.249 seconds include other work and must not
be attributed wholly to this parser. The host benchmark uses the exact
1,334,723-byte / 23,631-line preserved console and alternating stock/candidate
rounds with UTF-8 decode in both paths: median 0.922698s stock
versus 0.147935s candidate for 156 final-console observations.
[Console benchmark](android-evidence/client-streaming-0.13.9-console-benchmark.json)
does not establish Thor savings.
Texture inventory computes shared canonical roots and relative prefixes once,
retaining strict resolution and full readonly metadata for each leaf, with a
final ancestor replacement check. Inventory tuples/hash and cache envelope are
unchanged. A reproducible 11,612-leaf Linux fixture has identical full tuples and
SHA-256 across all comparisons: median 1.152739s to
0.771422s (33.079% host reduction),
with every leaf still strictly resolved once. [Texture benchmark](android-evidence/client-streaming-0.13.9-texture-benchmark.json)
is synthetic preparation only. New report-only `preparation_phase_seconds` separates complete
inventory, original header reads and validation/publication. These fields are
not persisted in the texture-index marker and do not invalidate warm packs.
The six additions require one index refresh; prelaunch preparation and the
previous 37.460-second wait are separate from actual Game startup.

[Focused 0.13.9 instructions](COH-Atlas-Gameplay-0.13.9-testing.txt) request one
same-preset hero reopen, three timing observations, one far/near comparison,
nearby Hellion appearance and a short first-pass/retrace comparison in the same
session, then Abort, owned cleanup and the complete exported outer support ZIP.
Physical startup/streaming/visual success remains pending. Preserve BIN phase
instrumentation; do not bypass freshness or change native decoder/cache formats
without new device timing. Repeated `Reading Car_*.txt` log lines are not proof
of repeated disk reads: stock seqLoad logs before its in-memory cache lookup.
The complete new outer `coh-atlas-gameplay-YYYYMMDD-HHMMSS.zip`, including its
unchanged nested `guest-report.zip`, is the next required physical evidence;
export after Abort and owned cleanup. Include the three timings and far/near
screenshots. An intentional cancellation from Abort is expected. The baseline
pass is the existing hero reaching Atlas with prior assets intact, clean owned
worker shutdown, no package-validation error and no material startup regression.
Accept an improvement only from observed timing/visual results. A crash, failed
Atlas entry, missing previously working assets, cleanup failure or repeatable
material regression is a failure; export that attempt without clearing data.
Broader NPC/world/FX coverage, `GEO_Collar_MAGIC`, unresolved material aliases
and distant white-object causes remain open. Software llvmpipe remains active.
Do not repeat accepted character/task/save/combat/storage gates or claim a
hardware graphics or complete combat milestone from this wrapper.

**0.13.8 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.8/COH-Atlas-Gameplay-0.13.8.apk)
from APK source `17751a759240181f962d5b5ded962cf13b364e24` on the existing
`codex/character-persistence-continuation` branch and open draft PR #1.
`main` remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`.
[Dedicated CI 37206208480](https://github.com/Russianranger/coh-android/actions/runs/37206208480)
passed all three jobs, **708 checks / 43 suites / zero skips / 261 source pins**,
all three real PostgreSQL transaction fixtures, official SDK version and v2/v3
signature checks with the existing signer, and publication.

The public APK is **701,495,575 bytes**, **1,363,968 bytes** above 0.13.7;
SHA-256 `5cd4235aa0772b219b9d2efb21bd37435a3676eea5cc36f1b31d39e1c7320076`.
[Publication receipt](android-evidence/client-loading-0.13.8-publication.json)
records an independent public download and checks every one of the **71 payloads**:
**61 retained / 10 replaced / zero added**. It verifies the actual new Game PE,
20 unchanged client DLLs, retained DbServer/MapServer, all 5,878 animation tracks,
323 visual leaves including all 290 old leaves unchanged, the new DEX, 17
unchanged authored Java sources, and setup memory protections. Local SDK
reverification was not performed; official CI checks bind to this identical
public APK SHA-256.

The native Game was built and qualified on Win32 at
`f42ebb46675213809018b4f9825d13eb1cd6e952`, successful Windows job
[111443757374](https://github.com/Russianranger/coh-android/actions/runs/37204837499/job/111443757374).
Five-round copy benchmarks and stock secure-CRT equivalence, explicit-length,
null/OOM and enabled profiling checks passed under `/O2 /Oy- /MT /TC`.
The original run later failed receipt aggregation, after 697 host checks passed,
because `test_acceptance` was missing from the suite registry. The corrected
publication run registers that suite and guards check composition; it reuses
the exact four-file native artifact **11304751532**, retains its original
commit/run identity, and does not claim a second native compilation. The audit
binds the original ZIP to its GitHub API digest and all three immutable native
source files. Game SHA-256 is
`ec1a6c01b07d7c189bde743a7255c860b8dd96879225b4ffa50fd42eabbb721b`.
The initial pre-build Windows staging failure was fixed by exact Git reverse
application instead of newline-altering reverse patching; no failed build was
published.

Install over the existing app and run **Set up runtime once**, preserving
imports, THORHERO, database and completed tasks. Follow the
[focused timing/visual instructions](COH-Atlas-Gameplay-0.13.8-testing.txt):
one reopen with the same preset, separate server/client/login-to-world timing,
far/near vegetation and nearby Hellion appearance, then Abort, owned cleanup
and export. The first added-texture inventory rebuild is expected and must be
timed separately from Game startup. No repeated task/save, creation, storage,
combat, reinstall, reimport or second boot is required. **Physical 0.13.8
startup savings and visual correctness remain pending.** Software llvmpipe and
broader missing assets remain open.

**0.13.7 device improvement accepted and preserved (October 4, 2026 UTC).**
The [current device receipt](android-evidence/client-visual-0.13.7-device-result.json)
pins the supplied `coh-atlas-gameplay-20261004-121800.zip` and six screenshots.
The user accepts server startup at approximately **6 minutes**, actual client
startup **4m24s**, and login-to-world **1m27s**, including about 30 seconds of
waiting/input. Instrumented client readiness is **263.921s**, down **182.021s**
from 0.13.6; the guest client stage is **264.424s**. Request-to-owned-Atlas is
**316.277s**, PostgreSQL **0.388s**, DbServer **41.163s**, and Atlas **232.803s**.
The <=300-second server goal remains open. Login-to-character protocol timing
is **67.939s**, using different boundaries from the user's visual measurement.

Many models and the HUD tray textures are visibly restored. The first visual
installation adds 290 files in **3.446s**; animation binding/verification takes
**13.974s** with **zero duplicate animation payload bytes**. The new texture
index has **11,612 hits / zero ordinary reads**; regeneration takes **38.941s**,
with **37.460s** of serial waiting. The complete Atlas-ready-to-launcher gap is
**59.068s**. Sequencer loading falls to **53.764s** from 95.325s; powers remain
approximately **54.048s**, FX info **29.694s**, grouplibs **19.433s** and the
map metadata/client NPC interval **23.649s**. Warm generated particle/behavior/
cape caches also improve. Do not attribute the entire client improvement to
animation mounting or claim these phase boundaries isolate pure decoding.

The guest succeeds, ordinary save/logout preserves character ID 1, powers,
costume and SQL/native position, login count increases 3 to 4, and owned cleanup
leaves zero workers. **The raw Android report is false because its retained Java
validator expects 12 stages while this build correctly emits 14.** All 56 guest
payload pins and the session match. Preserve the raw flag and fix the exact
contract; do not treat it as a gameplay or PostgreSQL regression. The next pass
requires the complete visual/animation APK pins and their two passed stages,
while retaining session, import, capture, save and cleanup checks.

Distant white vegetation/objects remain and can change appearance when approached.
The exact material/fallback dependency chain is being repaired without forcing
high-detail LOD or changing rendering. The invisible hostile is independently
identified as **Blood Brother Chopper / Hellions_Axe_Thug**, whose stock costume
variants are `Thug_Hellion_01` through `_06`. Native logs contain five hostile
power activations and three hits; HP changes from 102.50 to 98.24. Accept this
limited aggro/incoming-damage observation; full combat remains unqualified.
The current console still reports 391 missing GEO files and 1,422 texture errors;
this next bounded repair cannot promise every NPC/world asset is complete.

The published 0.13.8 pass expands the existing visual supplement to **323 files**,
preserving all old 290 leaf bytes and adding **8 THUG GEO files / 25 textures**,
**2,646,051 decoded bytes**. All 19 requested hostile model names are present in
stock geometry tables. The preserved Atlas bushes' `X_P_BushLODs` uses the
previously absent `Praet_BushLODs_d` primary and `Praet_BushLODs_fb` fallback;
both are now supplied alongside selected oak/evergreen material dependencies.
Stock LOD distances and renderer remain unchanged. The first updated texture
inventory rebuilds the header index; this preparation is separate from client
startup. The manifest retains unresolved original collar/legacy-texture gaps.

A separate, Game-only native layer retains the previous startup producer and
cache schema history. This layer replaces known-length string allocation
copies with `memcpy` after stock `strlen`, only under
`COH_CLIENT_KNOWN_STRING_COPY=1`; explicit-length copies keep stock secure CRT
behavior. `COH_CLIENT_BIN_PROFILE=1` distinguishes opening/CRC, source-freshness
checks and BIN decoding. CRC, date checks, parser tables, allocation/free policy,
DLLs and server executables are preserved. Two small-stack decoder prototypes
were slower in host measurements and were not selected. The new copy path passed
source-bound Win32 equivalence and representative benchmarks before APK
publication; device client savings remain unqualified. The guest recognizes the
exact immediate producer, upgrades only Game in place, and preserves generated
caches and absolute server links. Android DEX is recompiled solely for the two
acceptance Java changes; 17 other Java sources and setup memory guards are fixed.

Continue the same branch and draft PR #1. Preserve all accepted setup, storage,
NPC interaction, task acceptance/completion, character creation/reopen and save
milestones. The next physical check is client timing plus distant/close vegetation
and hostile visibility, followed by owned cleanup/export. No repeated task,
creation, reinstall, asset reimport or broad gameplay gate is requested.

**0.13.7 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.7/COH-Atlas-Gameplay-0.13.7.apk)
from source `0da09e771cb472f4ec897c39b90cef675d007edf`
(implementation `78218a5d2368af4020712dbc65900b40f1d2d4f1`).
[Dedicated CI 37198877717](https://github.com/Russianranger/coh-android/actions/runs/37198877717)
passed both Ubuntu jobs, **633 checks / 38 suites / zero skips / 236 source pins**,
all three real PostgreSQL transaction fixtures, official SDK v2/v3 signing,
version-only manifest verification and publication. No native or Java/DEX
recompile was performed. Broader draft-PR baseline checks remain separate.

Public APK is **700,131,607 bytes**, **23,998,809 bytes** above 0.13.6;
SHA-256 `ab21dc2e8a6ebecea0edf694187da83787f808a396d686e0d8312565f8373fc7`.
[Publication receipt](android-evidence/client-visual-0.13.7-publication.json)
records an independent public download, all **71 payloads** with the exact
**64 retained / 3 replaced / 4 added** boundary, unchanged 22-member client ZIP
and 20 DLLs, actual Game/DbServer source and PE receipts, exact memory DEX and
19 Java sources, retained MapServer/server extraction, all 5,878 animation
tracks, selected visual files/model tables and public checksum/instructions.
Local SDK reverification was not performed; official CI SDK checks are bound
to the identical public APK SHA-256. The first run assembled/signed an
unpublished APK, then refused publication on process-dependent JSON key order.
A serialization-only fix and independent-process regression passed; every
runtime payload outside the two verification manifests remains identical to
that first attempt. No extra physical test or user APK was requested.

Install over the existing app, preserve imports/profile/database/tasks, and run
**Set up runtime once**. [Focused instructions](COH-Atlas-Gameplay-0.13.7-testing.txt)
request one saved-hero reopen with the same preset, separate preparation/client
timings and Atlas/NPC/HUD screenshots, then Abort/owned cleanup/export. The first
new texture-header index may add preparation time. Physical client savings and visible restoration were pending at publication;
the subsequent partial improvements are accepted above. Remaining gaps stay open.
Continue the existing branch and draft PR #1; main remains
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`. Preserve all earlier accepted gates.

**Preserved 0.13.6 device baseline: server startup and client asset diagnosis (October 4, 2026 UTC).**
The user reports a substantial server-startup improvement: about **6 minutes**
to server start, **7m30s** for actual client startup to login, then about
**1m45s** to world entry including password input and hero selection. The
[0.13.6 device receipt](android-evidence/client-visual-0.13.6-device-result.json)
pins `coh-atlas-gameplay-20261004-104130.zip`, its current reports/consoles and
all four supplied screenshots. Three screenshots are current user visual
examples; `Screenshot_20261004-034450.png` is an older visual reference and
must not be represented as an independently authenticated 0.13.6 capture.

Runtime setup completed in **64.918s**. Request-to-owned-Atlas readiness is
**329.701s (5m29.701s)**, so the <=300-second target remains open. PostgreSQL
itself takes **0.491s**. The existing server-data cache is reused after verifying
one changed parent (`.`) and 50 child entries; checkout takes **6.420s**, with
**10.493s** total private-server preparation versus **421.648s** of prior
restaging. The broad DbServer stage falls from **452.302s to 40.328s**. Atlas
initialization takes **230.882s**, up from 195.016s in the preceding run; do not
claim that every native server phase became faster.

The actual client startup stage is **446.411s (7m26.411s)**; the launcher's
readiness observation is **445.942s**, versus 582.356s previously. The verified
texture index now has **11,367 hits, zero ordinary reads and zero miss samples**.
Texture-header loading falls from **137.859s to 7.550s**. This confirms the
0.13.6 path adapter and explains most of the observed client improvement.
The original headers and generated client caches are preserved through the
verified native-layer identity migration. Preparing the retained index after
Atlas readiness still takes **32.430s**, with **30.977s** of serial waiting
before the client launcher; this is a separate preparation opportunity.

Largest remaining console-measured client phases are sequencers **95.325s**,
powers **59.427s** (53.625s for dictionary/boost sets), grouplibs approximately
**54.725s**, map metadata/client NPCs approximately **33.184s**, FX info
**27.095s**, particles **23.115s**, FX behaviors **22.295s** and capes **22.152s**.
Grouplibs and map-metadata timings use adjacent log boundaries and can include
intervening work. Deferred registry polling works (88 deferred checks; 11
translated queries totaling 15.798s). Instrumented Android login-to-connection
is **78.703s**; its protocol boundaries differ from the user's 1m45s visual/input
observation. Do not equate either interval with pure world-loading time.

**Accept the ordinary-save regression fix on this device.** Existing THORHERO
reopened, ordinary Save/logout was delivered, the server observed the logout
timer and disconnect, and committed SQL/native position plus identity, powers,
costume and selected rows were verified. Character ID 1 remains intact; login
count increases 2 to 3, with one `ents` row, one `ents2` row, seven powers and
14 costume parts. No PostgreSQL 23505/PG_FIFO_FAILED appears in this current
owned DbServer console. Graceful PostgreSQL shutdown, Wine-prefix stop and
owned worker cleanup pass with zero remaining workers. Preserve the database
and accepted prior task/save/storage/gameplay progress; no repetition of those
completed physical gates is requested.

**Missing models/textures remain open and are now an active priority alongside
client startup.** The supplied screenshots show white world-surface patches
and blue/white HUD placeholders; the user also reports missing models. The
current console contains 3,345 FILEERROR records, 1,661 spaced `CUSTOM TEXTURE
ERROR` records, 391 missing `.geo` files and 114 missing root-geometry records.
Recorded examples include Ms Liberty texture names on `Wedding_MsLiberty_01`,
Atlas world dependencies and missing FX geometry. These references do not
identify the exact resource responsible for every screenshot or prove the
same costume as the invisible Atlas contact. The bounded diagnostic limit
worked, retaining validation and suppressed-event counters. Rendering still
uses llvmpipe/software with the performance preset; complete model/texture
appearance and hardware acceleration are unqualified.

Continue the existing `codex/character-persistence-continuation` branch and draft
PR #1. Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; this analysis
starts from `f865c9902eec22d20c9e985eff23ad11702961c8`. The current 0.13.7 pass
exposes the existing animation pack through the stock client loader and adds
selected missing Atlas NPC/world/HUD inputs after owned Atlas readiness. Game,
DbServer, MapServer, graphics libraries and the memory-protected Android DEX
retain their exact 0.13.6 bytes. Native parser/date-check bypasses are deferred
until freshness checks and decoding costs can be measured separately. The
animation helper validates pack and loose-file identities on each preparation;
count its verification overhead against any sequencer improvement. Added
textures require one full header-index refresh (prior cold build about 90s),
reported separately from actual Game startup. The selected visual closure is
bounded; `male_collar.geo/GEO_Collar_MAGIC` is absent from its donor and remains
explicitly unresolved. Do not claim full visual restoration or physical speedup
before the next device result. Five older geometry base-material names remain
absent from the donor (nine model edges): `BF_Boot_Clogs`, `BM_Eyes_Glasses_01a`,
`BM_Boot_Business_Shoe`, `BM_Chest_Bum_Flannel_01a` and `Emblem_Hero_Corp`.
Available live costume overrides are supplied; the original edges remain open.
The supplement also includes Ms Liberty's `FEM_GLOVE.geo`: the native Larm
suppression path masks its absence, so console BAD DATA alone was insufficient
to identify all missing costume parts. Exact source-requested model names are
checked against donor tables; no guessed model/material aliases are introduced.
The frozen supplement has **290 files: 45 geometry files and 245 textures**,
**36,583,648 decoded bytes**, archive **23,887,359 bytes** / SHA-256
`2cb25dbf8a5749c6e2cf9abc4a7dab305f5b2698d6c59e460d638b9756a40809`.
Original donor geometry tables contain 6,576 named models; 135 of 136 requested
model names match, including both Folded Gloves models. The selected ZIP and
each original file are checked by SHA-256, donor table MD5, cached headers,
native loader version/bounds and requested model/material edges. Its manifest
SHA-256 is `6b93b50a2b4d2bf6d2b16b5827517dec20f8b666c4fb853ccd58906659945c1b`.
Archive reconstruction authenticates selected HTTP ranges with stable metadata
and original per-file integrity; it does not claim full donor-archive hashes.
The animation mount references the retained 5,878-track pack and duplicates no
animation payload bytes. The installer adds missing private client files only,
with atomic/cancellable publication, owned readonly outputs and warm receipts.
[Focused 0.13.7 instructions](COH-Atlas-Gameplay-0.13.7-testing.txt)
request one timing/visual review, then Abort/owned cleanup/export; repeating
accepted task/save/storage gates or a second long boot is not requested.
Host/package qualification and publication are recorded above; the physical
client timing and visual gate remains pending. Preserve the accepted server reuse,
setup memory guard, imports, database, tasks and all earlier qualified gates.
Historical entries below retain their state at the time they were written;
this current section supersedes their outstanding 0.13.6 device-test requests.

**0.13.6 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.6/COH-Atlas-Gameplay-0.13.6.apk)
from source `7b48762de0748e443a2df60c6e4b59e22b365e35`
(implementation `ecddc3983beb8e6c298aaa63e6a068eb341f4e25`).
[Dedicated CI 37192124009](https://github.com/Russianranger/coh-android/actions/runs/37192124009)
passed both Win32 native builds, **542 checks / 34 suites / zero skips / 187 source
pins**, three real PostgreSQL transaction fixtures, official SDK v2/v3 signing,
version-only manifest verification and publication. Broader draft-PR baseline
checks are separate. The first CI attempt stopped before APK creation on a
Windows test-fixture CRLF patch input; a fixture-only fix and regression passed.

Public APK is **676,132,798 bytes**, only **12,288 bytes** larger than 0.13.5;
SHA-256 `6c3a11bcbe245c3938dbb9eb461fce40468097189dc115ab8819c496d26f5552`.
[Publication receipt](android-evidence/startup-bundle-0.13.6-publication.json)
records actual public download and checksum/instruction verification, all 67
payloads with the exact 55-retained/12-updated boundary, nested 22-file client
ZIP with 20 retained DLLs, native source/qualification receipts, actual retained
server archive extraction, 19 unchanged authored Java sources and the exact
memory-protection DEX/resources. CI SDK checks are bound to identical public
bytes; no separate local SDK rerun or device performance claim is made.

Install over the existing app, keep imports and private database/profile, and
**Set up runtime once** to activate the changed helper/native generation.
[Focused instructions](COH-Atlas-Gameplay-0.13.6-testing.txt) request one Reopen
saved THORHERO with the same graphics preset, readiness/login/connection timings,
one Save/logout for the newly observed regression, then one exported report.
No contact/task/combat/movement/storage/character-creation retest or second long
boot is requested. Preserve the accepted 0.13.5 setup result and earlier gates.
Actual 0.13.6 speedups and <=300-second readiness remain unqualified.
Main stays `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; PR #1 stays open draft.

**Current continuation: measured startup/cache/texture and save fixes (October 4, 2026 UTC).**
The user accepted smooth 0.13.5 runtime setup and supplied both reports
`coh-atlas-gameplay-20261004-082023.zip` and `coh-atlas-gameplay-20261004-084550.zip`.
[Device result](android-evidence/startup-bundle-0.13.5-device-result.json) records
53.918-second setup, no pressure waits, at least 9.515 GB reported available
memory, and the successful activation. This attempt is accepted; system-wide
LMK immunity is not claimed. Preserve the setup guard and prior physical gates.

The current startup result reaches the client window at 21m41.695s, login
observation at 22m10.946s, and the existing THORHERO Atlas connection at
23m35.398s. PostgreSQL itself takes 0.543s. The misleadingly broad local
DbServer stage takes 452.302s because an immutable-directory timestamp rejection
causes 421.648s of server-data staging (176,960 leaves / 9,524 directories).
Native DbServer console initialization then takes approximately 20s. Its exact
rejected directory is absent from the old report; do not invent that path.

Client startup takes 582.356s. Its index parses 11,367 texture records but gets
zero hits and performs all 11,367 ordinary reads; the header phase is about
137.859s. The source scanner's absolute-path callback versus relative index keys
is a supported inference, pending the new bounded path diagnostics. About
48.826s of translated registry queries and 27.63 MB of repetitive texture
diagnostics are additional measured opportunities. Atlas startup is 195.016s;
rendering remains llvmpipe, with hardware acceleration a separate open gate.

A new concrete save regression appears after the verified connection: a
Windows(1,17) INSERT precedes its cancelling DELETE, causing PostgreSQL 23505
and DbServer exit 3. Save was not acknowledged. Preserve the database and
accepted earlier saves/tasks; fix the production row-command emission rather
than deleting the conflicting row, ignoring SQL errors or clearing the profile.
Owned cleanup and graceful PostgreSQL shutdown passed in this report.

The authorized 0.13.6 pass addresses bounded server-cache changed-parent
validation, verified-root texture lookup and opt-in missing-texture aggregation,
registry query deferral, and the narrow cancelled-child INSERT regression.
Only Game and normal DbServer need native compilation; the retained MapServer,
renderer libraries, runtime archives, prepared caches, imports and 19 authored
Java memory-protection sources remain exact. Frozen prior native source layers
remain unchanged; new patches and receipts describe each supplement separately.
Dedicated CI qualification passed **542 checks / 34 suites / zero skips**, with
a **187-file source closure**, both native builds and all three real PostgreSQL
transaction fixtures. The public APK also passed independent payload verification.
[Targeted instructions](COH-Atlas-Gameplay-0.13.6-testing.txt) request one runtime
activation and one preserved-character timing/save session. Do not repeat
contact, task, combat, movement, storage or character-creation tests. Device
speedups and the <=300-second readiness target remain unqualified.

**0.13.5 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.5/COH-Atlas-Gameplay-0.13.5.apk)
from build source `31c8a1722f992e7a8334ef2256b4feaa9ca173be`
(application implementation `9e3b88a2d6109cb5711a3ba480924d0a89fe0c1c`).
[CI 37174737394](https://github.com/Russianranger/coh-android/actions/runs/37174737394)
passed qualification, official SDK compile/v2/v3 signing/version verification,
and wrapper publication: **467 checks / 29 suites / zero skips / 160 source pins**.
Public APK is **676,120,510 bytes**, only **12,288 bytes** larger than 0.13.4;
SHA-256 `b02cfa71498418a0fef0f5b3219a37207fcbc713fcece0c2dcc3a1019b5c3a13`.
[Publication receipt](android-evidence/setup-memory-0.13.5-publication.json)
records the actual public download and verification of all 67 retained payloads,
DEX/resources, server archive extraction, source pins and checksum/instructions.
CI official SDK checks are bound to these identical bytes; no local SDK rerun
or physical memory/LMK qualification is claimed. The first CI attempt stopped
before APK creation because checkout omitted the parent needed by the routing
check; both dedicated jobs now fetch two commits. Broader draft-PR baseline
checks are separate from this successful wrapper publication.

Install over the current app and do **Set up runtime once, then export its report**.
Do not uninstall, clear data, reimport assets, recreate THORHERO or repeat any
accepted gameplay/storage/recovery gate. Review this setup result before another
long Reopen. This wrapper retains the exact 0.13.4 runtime manifest/generation
identity and all runtime files; a completed generation is reused. Interrupted
staging must complete verification under the memory guard before activation.
[Setup-only instructions](COH-Atlas-Gameplay-0.13.5-testing.txt).
Main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`; PR #1 stays draft.

**Current continuation: runtime setup memory protection (October 4, 2026 UTC).**
The user reports that running 0.13.4 Set up runtime interrupted all apps. No new
log bundle accompanied this report: neither Android LMK nor a precise failing
phase is confirmed. [Recorded report](android-evidence/setup-memory-0.13.4-user-report.json).
Accepted storage recovery and manual task completion remain accepted; do not
reset the profile or repeat those gates to diagnose this setup failure.

The published wrapper, 0.13.5, adds setup memory headroom checks, bounded pauses and
safe refusal under persistent pressure, bounded I/O/synchronization, effective
Stop during extraction, and interruption checkpoints with own Android exit
history. It retains the exact 0.13.4 runtime manifest and all 67 runtime payloads;
no additional runtime generation is required solely by this wrapper update.
A completed 0.13.4 generation is reused, while an interrupted staging operation
must complete verification before activation. Do not uninstall, clear data,
reimport assets or recreate THORHERO. Request only setup and its report before
another long Reopen; no device safety/speedup or system-wide LMK immunity is
claimed. [Setup-only instructions](COH-Atlas-Gameplay-0.13.5-testing.txt).

Local qualification passed **467 checks / 29 suites / zero skips / 160 source
pins**, including production guard, real archive cancellation, installer reuse
and publication refusal, Service heap/ownership/recovery and all retained prior
guards. All 19 authored Java sources are receipted (six changes plus one setup
guard). Dedicated CI and independent public payload verification passed; no
native rebuild or physical setup qualification is claimed.

The setup controller checks at admission, bounded I/O (1 MiB aggregate reads and
writes) or 250 ms between cooperative checkpoints. It keeps 512 MiB–1 GiB above
Android's low-memory threshold, adds 64 MiB resume hysteresis, and checks Java
heap headroom. A single pressure wait is limited to 15 seconds, with a 60-second
operation total. Memory-service/clock failure refuses further setup I/O. Stream
buffers are 64 KiB; every regular output file is synced at close, active large
files at 8 MiB, and cumulative 8 MiB write windows are paced by 25 ms. These are
cooperative limits: blocked OS I/O is not forcibly preempted and polling cannot
guarantee prevention of a system process kill.

Stop, persistent pressure, unavailable memory telemetry and heap exhaustion
leave only owned unactivated staging for a later admitted retry; its ready
marker is removed. Cleanup streams no-follow entries with depth/entry limits.
No protected profile, SQL data, import or prior runtime generation is retired.
Setup phases and original app version are durably checkpointed with bounded
records; interruption recovery exports the last phase and at most four own
Android process-exit records. The setup reservation spans terminal evidence and
wake cleanup, including same-process Service replacement, before another
operation can start. Surface frame arrays/bitmap are released before setup.

**0.13.4 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.4/COH-Atlas-Gameplay-0.13.4.apk)
from source `6d16acf8330774e5fee4c0410c9cc56746d60b58`.
[CI 37171443387](https://github.com/Russianranger/coh-android/actions/runs/37171443387)
passed qualification and wrapper packaging, with no native build:
**374 checks / 25 suites / zero skips / 148 source pins**. APK is
**676,108,222 bytes**, the same size as 0.13.3; SHA-256
`5cfd2cd929467f1797d72a142cd39999c3d5dbceee65a02d4baf7bba287f2052`.
[Publication receipt](android-evidence/task-receipt-cleanup-0.13.4-publication.json)
records the actual public download, all 67 payload digests, 64 retained payloads,
corrected DEX/resources, exact server archive extraction, source pins and public
checksum/instructions. CI official SDK signature/version checks are bound to
identical public bytes; no separate local SDK rerun is claimed. The signer is
retained. One Java source/DEX, the reopen helper and its two manifests change;
all native payloads and the four prior startup improvements remain exact.

Install over the app, **Set up runtime once**, then **Reopen saved THORHERO** as
an explicit startup-only connection/timing check. Existing journal rows are
preserved and no task qualification is requested. Stop and export after
connection; a cancelled verdict without ordinary Save is timing evidence, not
an ordinary-save or gameplay pass. No reinstall, import or completed physical
gate repetition is required. [Testing instructions](COH-Atlas-Gameplay-0.13.4-testing.txt).
The prior generation remains available for rollback and reviewed storage cleanup.
Actual device startup improvement and the <=300-second target remain open.

The retained activity's static explanatory paragraphs still describe the old
task test. Follow the new startup-only status and 0.13.4 instructions; adapt that
static copy to the active mode on the next UI pass. Task controls are gated off
for the explicit startup-only mode. Do not replace/rebuild this qualified APK
solely for that legacy explanatory copy.

**Prior device result: 0.13.3 Reopen stopped on a stale task-helper receipt;
PostgreSQL login passed (October 4, 2026 UTC).**
[Failure receipt](android-evidence/startup-schedule-0.13.3-reopen-blocked.json)
pins `coh-atlas-gameplay-20261004-021301.zip`. The installed runtime and native
supplement match published 0.13.3. Persistent profile and client worktree were
reused, PostgreSQL durability/admin/fixture checks passed, and owned cleanup
plus graceful database shutdown passed. Wine, DbServer, Atlas and graphical
client never started; this result cannot qualify the startup speedup.

`ClientRuntime.removePreviousGuestOutput()` omitted the two fixed transient
outputs `character-task-contact.json` and `character-task-completion.json`.
The retained guest correctly refused a leftover receipt. The export does not
include that receipt's exact filename or previous session, so do not infer
either. Retire these session outputs under the existing prelaunch operation
lock and retain all current-session delivery/save/readiness guards.

The accepted manual-task run also recorded a task row, while the old one-task
diagnostic requires an empty journal. The approved next activity is startup
timing, so explicitly select ordinary saved-character Reopen, preserve existing
task rows and do not reopen the accepted task gate. The 0.13.4 correction is implemented with an explicit startup-only flag;
**374 checks / 25 suites / zero skips / 148 source pins** passed locally.
CI publication passed. Native startup optimizations and all earlier
physical acceptances remain retained. Changed reopen helper
requires one runtime setup; no reinstall, data clear, import or character
recreation is justified. [Continuation instructions](COH-Atlas-Gameplay-0.13.4-testing.txt).

**0.13.3 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.3/COH-Atlas-Gameplay-0.13.3.apk)
from startup source `dee916f80e9e336f374f31228535afdbe2c928ca`.
[CI run 37167835800](https://github.com/Russianranger/coh-android/actions/runs/37167835800)
passed Windows native build, qualification and retained-signer publication:
**331 tests / 23 suites / zero skips / 141 source pins**. Public APK is
**676,108,222 bytes**, only **807,084 bytes** larger than 0.13.2; SHA-256
`2626dcabcc9d69bfd1b9ad723e9748746df77e93d565a0fb1740eeff4b516709`.
[Publication receipt](android-evidence/startup-schedule-0.13.3-publication.json)
records the actual downloaded 67-payload audit, ZIP CRCs, retained DEX/resources,
server archive extraction and native/source pins. CI official SDK signature and
version checks are bound to these identical public bytes; no separate local SDK
rerun is claimed. The normal Win32 DbServer supplement is the only native rebuild.

Install over the existing app, **Set up runtime once**, then do one saved-hero
startup/connection timing session and export. Keep assets/profile; preserve all
accepted gameplay/storage/recovery gates. No new physical speedup is claimed.

Publication tooling follow-up: the frozen 0.13.3 manifest producer/checker uses
frozenset insertion order for its two new native keys. A new
`tools/android/interactive/audit_startup_schedule_public.py` companion preserves
the actual client manifest's order without changing values, allowed updates or
original derivative guards; four mutation/order checks and independent review
passed. The actual client hash matches its runtime pin. Sort added keys in both
producer/checker for the next release; do not rebuild or replace this APK solely
for this checker serialization issue.

**Current authorized priority (October 4, 2026 UTC): reduce server startup
further before the next gameplay milestone.** The user selected options **7
(avoid decoding unchanged world assets), 13 (skip the unused local Launcher
wait), 18 (overlap independent preparation) and 4 (move client texture indexing
after server readiness)**. Preserve the accepted manual task and all earlier
physical gates; do not restart the proposed progression sequence yet.

The published 0.13.3 uses a pinned world reuse receipt, a narrowly guarded
DbServer manual-Atlas launcher-wait bypass, and a single texture preparation
worker after actual Atlas readiness which overlaps only the independent PE32
runtime probe. Server and client heavy initialization remain serial, and the
worker joins before client launch or cleanup. Game, MapServer, renderer,
imported content, prepared definition/message caches and the animation pack
remain retained. This build has not yet established physical speedup.

[Prior warm-run baseline](android-evidence/startup-schedule-0.13.3-baseline.json)
pins the uploaded 0.13.2 reopen: Atlas readiness **11m22.726s** from guest start,
native connection **23m19.616s** from Android run start, DbServer **6m53.111s**,
Atlas **3m20.429s**, client startup **10m09.694s**, and warm texture preparation
**16.585s**. The previous 89.7-second texture observation was a cold preparation,
not a guarantee for every run. World reuse avoids repeatedly decoding 318.6 MB
of unpacked resources. The <=300-second Atlas-readiness target remains open.

The updated source-bound runtime requires **one Set up runtime** to activate
the changed helpers/DbServer. Keep the current installation, imported assets
and saved profile; do not reimport or recreate THORHERO. The prior generation
remains for rollback and can later be retired with reviewed storage cleanup.
Repeated setup of the same new manifest must reuse its installed generation.
[Focused startup instructions](COH-Atlas-Gameplay-0.13.3-testing.txt) request one
startup/connection timing session and its export, without repeated task,
movement, safe-ground, contact, storage or recovery qualification. Main remains
preserved; continue the same draft PR and branch.

**Latest physical acceptance (October 4, 2026 UTC): manual task acceptance and
completion passed on Thor in the installed 0.13.2. The user completed the task
through normal in-game play without the completion helper and explicitly asks
that this be accepted regardless of the diagnostic verdict.**
[Acceptance receipt](android-evidence/thor-0.13.2-manual-task-accepted-20261004.json)
pins `coh-atlas-gameplay-20261004-003136.zip` and preserves the original reports.
Close manual task acceptance/completion as successful; no repeat is required.
The user reports that this prevented use of the left-side helper controls.
Record that as a separate diagnostic UI follow-up, not a failed gameplay gate.

The native connection event confirms the previously saved THORHERO (character
1, COHLOCAL) reopened on Atlas with preserved identity. The wrapper's narrow
authored-task observer reported a task outside its finite simple-task contract;
its accepted/completed events and completion-command receipt were absent. The
run was cancelled and owned cleanup passed. These diagnostic facts do not
overturn the user's manual gameplay acceptance or establish a game regression.
The exact task identity, forced-command path, reward turn-in, combat and mission
maps are not newly qualified by this acceptance. No ordinary Save or task-specific
committed SQL proof was captured in this run. Carry task/progression persistence
into the next ordinary save/reopen checkpoint without repeating the accepted
manual task. Prior character save/persistence acceptance remains valid.

**Proposed next gameplay sequence, not a previously approved numbered plan:**

1. Remove the helper-control obstruction to normal play and ordinary Save;
   validate contact reward turn-in/next-task progression and its save/reopen.
2. Validate training, level/power progression and power-tray behavior.
3. Qualify authentic generated Atlas beacon provenance, structure, world CRC
   and native graph loading before claiming moving-NPC pathfinding/combat.
4. Validate basic combat and power effects, then instanced mission entry,
   objectives, exit/Atlas return and saved progression.
5. Validate ordinary graphical zone transfers and persistence across maps.
6. Complete missing costume assets (including Ms. Liberty), broader terrain,
   materials/minimap and collision coverage.
7. Complete offline-app reliability: backup/restore into a clean profile,
   airplane-mode play, repeated transfers and a sustained two-hour session.

Server startup remains the main performance priority: the <=300-second Atlas
readiness target is open. Retain shipped options 1, 2, 8, 3 and 9 and the accepted
startup improvement; the installed animation pack has no controlled physical
speedup measurement yet. Hardware renderer acceleration remains deferred;
audio, broader services and eventual native ARM64 conversion remain future
scope. Do not reopen accepted setup/import, graphical login/creation, ordinary
save/reopen, movement/camera/jump, indoor/outdoor traversal, contact dialogue,
storage or fresh-profile recovery milestones. No app changes, runtime refresh,
asset import or new APK accompany this documentation acceptance. Main remains
preserved and PR #1 remains draft on the existing continuation branch.

**Prior physical acceptance (October 3, 2026, 23:48–23:50 UTC): 0.13.2 fresh
character recovery and storage inventory passed on Thor. The user reports
“Everything worked including storage, still need to do the tasks.”**
[Accepted evidence](android-evidence/thor-0.13.2-storage-recovery-passed-20261003.json)
pins both uploaded files. Android and guest creation reports both passed with
no guest failures. THORHERO entered Atlas, ordinary logout/timer was observed,
the character was disconnected before read-only SQL proof, and committed rows
contain one character, seven power rows and fourteen costume parts. Three fresh
post-save Android captures passed; Finish and graceful PostgreSQL/Wine/owned
process cleanup completed, with no cleanup block. The profile is READY. Treat
the deleted installation recovery as complete; do not recreate the character.

Storage inventory completed without errors over **578,696 entries**, verified
the current runtime and allowed reviewed cleanup. Allocated app files total
**10,878,041,088 bytes (10.88 GB)**: current runtime 3.81 GB, protected character/
server/Wine/cache state 2.93 GB, and protected imports 3.45 GB. There are no older
runtime generations in this fresh installation. Only two recognized component
downloads and one older report are candidates, totaling **673,447,424 bytes
(673.4 MB)**. This upload is an inventory, not a cleanup-execution receipt:
the user accepts storage functionality, but deleted entries and actual freed
bytes are not measured. Do not call the former 62 GB installation explained or
its missing data reclaimed by this scan. No further scan/recovery repeat is
needed for the task gate. A setup reuse receipt was not included in these files;
keep quantitative repeated-setup growth unclaimed.

This first-profile run reached Atlas readiness at **15m36.196s** after guest
launch and the client startup gate at **25m46.194s**. Client data worktree reuse
took 0.153s; initial Wine setup took 64.872s, DbServer startup 479.574s, Atlas
startup 198.116s and client startup 607.049s. The 5,878-animation pack installed
and loose fallback inputs remained preserved. These are phase observations,
not a controlled option 9 speedup comparison. Preserve prior startup findings.

The next gate after this recovery receipt was the fixed authored-task path in
[0.13.0 task instructions](COH-Atlas-Gameplay-0.13.0-testing.txt). The October 4
manual acceptance above supersedes that request: do not repeat acceptance or
completion merely to satisfy helper-command receipts. The creator run had
`task_gate.required=false` and supplied no task proof; the newer user acceptance
supplies the manual gameplay verdict. Task persistence moves to the next
progression/save checkpoint. Combat, mission maps and contact reward turn-in
remain separate scope.

**Current recovery publication (October 3, 2026): 0.13.2 is published and
independently verified from `c0d10f8cd873449962f5a723d489b9ead18642d0`.
The user reported 62 GB app storage,
a storage scan crash after about two minutes, a subsequent gameplay crash, and
then uninstalled the app. Setup and import succeeded on the new installation;
the uploaded reopen run failed before PostgreSQL, Wine/server or client startup
because the saved character profile was absent.**
[Reviewed evidence](android-evidence/thor-0.13.1-reinstall-failure-20261003.json)
pins the upload. Its 289.23-second client worktree preparation completed before
the missing-profile refusal. No pre-uninstall crash trace or exit reason survives
in this bundle; do not call the earlier crash an established OOM or regression
of the accepted gameplay milestones. Diagnostic exports are not SQL backups.

The 0.13.2 Android recovery derivative is qualified on the existing
continuation, retaining all 65 runtime payloads, manifest bytes and signing key.
Storage traversal now streams descriptor-anchored entries; cleanup planning
uses a bounded on-disk postorder journal instead of retaining every node in
memory. Fixed inode/memory limits fail closed. Progress is persisted every five
seconds and on phase changes; cancellation retains ownership until the worker
finishes, and interruption diagnostics include the last checkpoint plus bounded
own-process Android exit reasons. An incomplete or interrupted scan cannot
authorize cleanup. Current state/import/cache protection is unchanged.

Same-manifest runtime setup already reuses its installed generation. The known
cumulative mechanism is retained full generations across changed manifests,
along with downloads and reports; the source alone does not attribute the
62 GB or prove a new full copy per setup of the same build. New setup receipts
distinguish reuse from installation and record bounded generation counts,
downloads, extraction/copy counters and filesystem available bytes. Filesystem
available-byte differences are not an allocated per-app inventory.

Missing-profile reopen is refused before expensive guest staging. The UI offers
explicit fresh THORHERO creation only when the entire profile is absent; an
existing, incomplete, linked or unreadable profile is protected. The guarded
native creation route uses ordinary logout/save. The task gate remains required
on subsequent reopen. Only this deleted installation needs fresh creation;
prior physical acceptance remains accepted. Install the update in place, keep
the successful setup/import, export the storage/setup receipts and fresh creator
save report, and stop before another long task run. See the
[0.13.2 instructions](COH-Atlas-Gameplay-0.13.2-testing.txt). Device recovery and
storage inventory are now accepted above; measured reclamation remains pending.
Main remains 04d62616 and PR #1
remains draft on `codex/character-persistence-continuation`.

[CI 37147463123](https://github.com/Russianranger/coh-android/actions/runs/37147463123)
passed qualification and APK/publication: **489 checks, 32 suites, zero skips,
209 source pins and all 18 Java sources compiled against Android 35.** Native
animation/task packaging and the historical 0.13.1 publication jobs were
correctly skipped. The public APK was downloaded separately and passed every
actual payload/DEX/resource digest and ZIP CRC, exact manifest conservation,
real server archive extraction, official retained v2/v3 signer, alignment,
ABI/version and version-only Android binary manifest comparison.
[Publication receipt](android-evidence/storage-recovery-0.13.2-publication.json).

[Download 0.13.2](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.2/COH-Atlas-Gameplay-0.13.2.apk).
Public APK: **675,301,138 bytes**, only 12,288 bytes larger than 0.13.1;
SHA-256 `28e3eda8dbc3982bc42d42dee6ab4f35e985d96af31bff4a2c691b806a207e1f`.
The user-reported 62 GB concerns installed data, not a multi-gigabyte APK.
The host stress scan/deletion covers 300,000 lazy entries and 1,000 hard-link
pairs under a 48 MiB heap. The repeated-setup fixture preserves five identical
setups' runtime bytes/inodes/mtime with zero extraction/copy/download work.
Neither fixture establishes Thor scan responsiveness, actual reclamation or
the cause of the deleted installation's crashes. Existing runtimes/imports and
accepted physical milestones must remain intact.

**Previous storage publication (October 3, 2026): 0.13.1 is published and independently
verified from `5252595717a1965a76251d4110725185bbcbbe20`. It adds idle-only storage
inspection and explicitly reviewed cleanup for the user-reported 57.44 GB app
usage. [Run 37129906760](https://github.com/Russianranger/coh-android/actions/runs/37129906760)
passed both jobs: 384 host checks across 28 suites, no skips and 201 source pins.
PR #1 remains draft on the same continuation; main remains 04d62616. Device
cleanup and actual recovered space remained unmeasured at publication. The
0.13.0 physical task/save test was then underway; the subsequent crashes and
uninstall are recorded in the current recovery findings above.**

[Download the storage update](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.1)
with [its instructions](COH-Atlas-Gameplay-0.13.1-testing.txt).
Public APK: 675,288,850 bytes, SHA-256
`7652106de29838389b012aee802ccb784c6fc956dffe66d566773e1eb40bd9d3`.
It adds only 20,480 bytes to the previous APK. All 65 runtime payloads and the
runtime/client manifest bytes are exactly 0.13.0, retaining the signer,
93 startup caches, 5,878 animation pack and all task/input/save behavior.
No runtime refresh, reimport, new native preload or repeated physical test is
required. [Publication receipt](android-evidence/storage-cleanup-0.13.1-publication.json).

Runtime setup creates a new `m2/runtime-<manifest SHA prefix>` for changed
manifests and previously retained older full Linux/Wine/PostgreSQL/asset trees.
Component downloads and completed support-report directories also accumulate.
These are candidates rather than a measured attribution of the 57.44 GB.
Storage and cleanup → Scan storage reports actual allocated blocks and apparent
file lengths. Review selected cleanup lists categories, paths and estimates;
Clean selected performs deletion only after a complete unchanged rescan and
verified current runtime. Unknown or unsafe identities disable or exclude
cleanup. Errors stop remaining deletion and report partial progress. The
separate JSON export preserves the latest gameplay report. Scan/cleanup/export
share idle operation ownership with gameplay/setup/import; fd-anchored deletion
and literal symlink digests guard path changes. Scans have entry/depth/time and
memory bounds; partial scans cannot authorize deletion.

All `client/state` (character/PostgreSQL/Wine, cache/worktree anchors, raw
evidence), all imported generations, current runtime, protected symlink targets,
latest report and newest three report directories remain protected. Cached
component removal can require a future download on a genuine runtime change.
No automatic pruning occurs. The device inventory and Android Settings figures
before/after cleanup will guide any later state/evidence retention work.
Independent downloaded-public-byte audit passes every payload/DEX/ZIP CRC,
actual server archive extraction, original animation envelope/header closure,
official v2/v3 signer, alignment/ABI/version and version-only binary manifest
changes. Original 0.13.0 publication and accepted gameplay progress remain below.

**Retained gameplay publication (October 3, 2026): 0.13.0 is published and independently
verified from `53c885896e9b4d838be0f36a1f09237f04c08a00`. It implements the newly
authorized option 9 and the task acceptance/command-completion/ordinary-save
gate. [Run 37125084672](https://github.com/Russianranger/coh-android/actions/runs/37125084672)
passed all three jobs. PR #1 remains draft on the same continuation branch;
main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`. New physical task/save and
Thor startup results are pending; all accepted milestones below remain valid.**

[Download 0.13.0](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.0)
with [the new testing instructions](COH-Atlas-Gameplay-0.13.0-testing.txt).
Public APK is 675,268,370 bytes, SHA-256
`18cffb361df26076c10f9c020548f384d10c21f8462ed06e77e9cae5c00de4d1`.
See [the publication receipt](android-evidence/task-gate-0.13.0-publication.json).

The server-private Pig v2 pack preserves all 5,878 retained animation files,
names, timestamps, cached native headers and bodies. Its 97,084,456 bytes have
SHA-256 `465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b`.
Original loose animations remain the fallback. Installation outside the stable
server data cache retains all accepted 93 definition/message bins and cache
identity. Native client/server, runtime, driver, world/avatar data and Wine
component timestamps are unchanged. No FEX upgrade or other startup option is
included in this pass.

Actual stock MapServer loose, cold-packed and warm-packed preloads completed
normally with exact cache/input conservation, packed animation content reads,
no loose animation reads in packed phases and traced Wine-prefix quiescence.
Native proof is reverified before build and publication. Traced host preload
intervals were 232.204s / 192.199s / 191.128s. These establish host consumption
and a host improvement; they do not predict Thor savings. Original inventory
byte preservation does not assert all tracks were selected during preload.

The new gate opens Matthew Habashy's ordinary dialogue through the fixed stock
`/contactdialog Contacts/Atlas_Park/Matthew_Habashy.contact` helper. The user
manually accepts **What Was Lost / Part One: Demons and Gangsters** (`Mission1`,
five Hellions), captures its accepted journal view, and invokes the fixed stock
`/completetask 0` helper once. Native task/arc logs, owned command receipts,
authored SQL attribute mappings, one active task and actual bounded reward
credit must agree before completion. Three fresh captures of each phase are
required before ordinary Save. The same completed task state and credited
XP/contact points must persist with preserved identity, class/origin/level,
powers and costume. The previous final-logout position correction is included.
Combat, missing-NPC clicking, reward turn-in and later story progression are
not required or claimed. Existing tasks are never cleared or replaced to make
this gate pass. Keep the current profile, imports and THORHERO; refresh runtime
once, perform this new gate, then Finish/export after Saved character verified.

Only the task profile's private logging enables stock entity level 2 for
Storyarc:Add; legacy reopen behavior remains unchanged. SQL remains read-only
game evidence. Host qualification passes **308 checks across 24 suites with no
skips and 190 source pins**. Independent actual public-byte verification passes
all 65 payloads, DEX/CRC, donor conservation, original animation/header closure,
real guest archive extraction, retained official v2/v3 signer, alignment,
ABI/version, version-only binary manifest changes and public release assets,
checksum and instructions. Public 0.12.1 remains unchanged. The accepted
physical checkpoint below remains authoritative and must not be repeated.

**Current physical checkpoint (October 3, 2026): The user accepts the 0.12.1
startup improvement and ordinary NPC contact/dialogue test. Sunstorm and Merit
Reward Informant opened readable dialogue and processed normal responses.
Ms. Liberty remains an incomplete female costume asset defect, not a reason to
repeat the accepted general contact test. The app's failed result came from a
stale position comparison during ordinary save. A narrow observer correction
and regression replay are included in the published 0.13.0 update; the published
0.12.1 APK remains unchanged. PR #1 stays draft and main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261003-110806.zip` binds the Thor session
`cb216f7fcefc4ad1b4e9f059b2128df8`. The six exported contact PNGs have verified
hashes and two completed, identity-bound capture batches. Native logs show
Sunstorm opening at 11:04:20 UTC and closing at 11:04:42, and Merit Reward
Informant opening its `MeritReward` script at 11:05:40, processing an information
response at 11:05:55 and closing at 11:06:07. The user's extra screenshot shows
its information page after the initial page. The Patriot exploration badge is
visible and user-attested; its persistence is not independently established.
Mission acceptance/completion, training, NPC pathing and combat remain separate.

| Measured endpoint | 0.12.1 from session start |
| --- | --- |
| DbServer ready | 10m45.471s |
| Atlas server ready | 14m35.812s |
| Client menu/main loop | 23m56.276s |
| Local login verified | 24m15.587s |
| THORHERO connected | 25m39.175s |

The accepted 0.11.6 server baseline was 21m50s; this run reaches Atlas about
7m14s earlier. The user's approximate 24-25-minute boot and 4-5-minute perceived
improvement are retained alongside the measured endpoints. All 93 shipped
server caches appear in native loader traces; 91 were seeded and two existing
bins retained. First-use server staging still costs 410.218s and client startup
556.981s. Wine's expected first-transition registration costs 65.423s. The new
server data cache was returned after owned cleanup with credentials removed,
so a later ordinary run can qualify reuse. No warm-start timing or five-minute
server-target pass is claimed; no extra startup-only physical run is required.

The false save rejection compared committed SQL against the 11:06:08 periodic
sample `(121.10, -768, -702.51)`. Ordinary logout expired and disconnected at
11:06:37; its final native position `(112.468750, -768, -660.765625)` agrees with
SQL `(112.461586, -768, -660.7662)` at 11:07:48, within 0.008 units. Independent
SQL-log analysis preserves the selected `ents`/`ents2` rows, seven powers and
fourteen costume parts except expected LoginCount 7 to 8. Original failed flags
are retained: no Saved-character-verified event or Finish occurred. Cleanup
passed. The fix prefers the final own-player, map-1, same-route/same-timestamp
ordinary-logout location while retaining fresh native producer, request/session,
protected-row, SQL, fall-floor and optional-recovery gates. A regression uses
real exported log lines and explicitly synthetic delivery time because the
private command receipt was not exported. It does not fabricate physical proof.

The optional contact observer also missed stock `BuildNumber` suffixes and the
two NPCs outside its original name list. It now recognizes bounded stock
suffixes and the pinned authored Sunstorm/information-NPC contracts. Merit script
responses use contact handle zero; those are deliberately unclaimed by this
ordinary-handle observer. Visible dialogue/progression remains user-assessed.

Ms. Liberty's live client log reports missing female pants, chest, head, boots,
hair, belt and shoulder geometry plus textures; the retained avatar supplement
covers default male assets. Supply/verify her complete matching costume
requirements in later asset work. Her specific interaction and complete NPC
rendering remain unverified. Missing animations are not claimed.

The observer correction passes **88 focused checks**, including exact native and
authored data contract pins, with no skips. The correction is now packaged in 0.13.0;
the installed/public 0.12.1 behavior is not changed.

See [the physical acceptance and diagnostic receipt](android-evidence/thor-0.12.1-contact-startup-accepted-20261003.json).
Preserve prior accepted camera/jump/outdoor/recovery and persistence milestones.
The next new gameplay gate is bounded task acceptance/completion/save,
using the corrected observer in the published 0.13.0 build; this does not require
replaying accepted contact dialogue. Current published 0.12.1 remains available.

The retained publication checkpoint follows:

**Current (October 3, 2026): 0.12.1 is published and independently verified. It
implements the authorized startup options 1, 2, 8 and 3: exact server/English
message caches, stable verified client/server data roots and cache identities,
and trusted Wine component timestamps. Native client/server, world/avatar,
client caches, driver and contact behavior remain retained. Physical Thor
startup timing, contact dialogue and ordinary Save without recovery remain
pending; no five-minute startup or device speedup is claimed. GPU work remains
deferred. PR #1 remains draft and main stays 04d62616.**

[Download 0.12.1](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.12.1/COH-Atlas-Gameplay-0.12.1.apk).
Published from `1fcabfa28f1f32a8c78de2cac496d6647fd376a9` in
[run 37116009802](https://github.com/Russianranger/coh-android/actions/runs/37116009802),
with all four jobs successful. The public APK is **625,055,087 bytes**, SHA-256
`fee8880a53916e4ff746d67c8a6ab22f3f0cf2ab7779198cef59035ef4d6bf29`,
version code 14, with the existing app ID and signer. Independent v2/v3 signature,
public payload/CRC, retained-byte and release checks pass. Focused qualification
passes **344 checks** and binds **199 source files**. See
[the publication receipt](android-evidence/startup-caches-0.12.1-publication.json)
and [the implementation scope](ANDROID_STARTUP_CACHE_REUSE.md).

The exact **29,825,263-byte** cache archive contains **90 Parse6 caches and three
English MessageStores**. Hosted native generation and consumption reached
preload, retained identifier files, exited normally and completed bounded Wine
waiting. Independent consumption evidence shows all 93 cache files read,
unchanged cache bytes, no scoped source-content reads and no cache writes.
An additional host-only Wine helper-lock observer inspected the stock `/tmp`
directory while this Ubuntu host used `/run/user/1001/wine`; that extra lock-path
claim is invalid. It does not invalidate the native exit, wait, identifier,
cache-hash or consumption evidence and is not embedded in the APK. A corrected,
consumption-only supplemental check of the exact public cache bytes passed in
[run 37117800033](https://github.com/Russianranger/coh-android/actions/runs/37117800033)
at `71e4568b5af32c394867e9f779f4d27ee898cf60`. Two independent audits verify
37 source pins, 96 evidence files, all 93 cache reads, unchanged identifiers,
cache bytes and normalized dates, and no scoped source reads or cache writes.
The actual traced `/run/user/1001/wine/server-801-9c3091` lock is unheld after
initialization and after normal owned native exit; bounded `wineserver -w` returns
zero with empty diagnostics. Corrected host qualification passes **365 checks**
and binds **202 source files**, separately from the original APK qualification.
This adds independent consumption quiescence evidence; it does not retroactively
observe the original generation lock or replace runtime timestamp proof.
Public APK/cache bytes and original qualification/build reports remain unchanged.

Install over the existing app, preserve imports and THORHERO, and refresh runtime
once. Follow the
[short 0.12.1 contact test](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.12.1/COH-Atlas-Gameplay-0.12.1-testing.txt)
with ordinary Save and verified Finish. Return to Safe Ground remains optional;
F remains Follow. The accepted 0.11.6 camera, jump, outdoor, persistence and
safe-ground tests must not be repeated solely to reconfirm them. The startup
target remains at most 300 seconds from session start through Atlas server
readiness, including required preparation; this build has no physical timing
result yet.

The published 0.12.0 checkpoint follows (its startup deferral is superseded above):

**Current: The physical 0.11.6 run passes existing-character reopen, ordinary save and cleanup. The user accepts the smoother client as adequate for testing. Server startup remains slow and optimization is deferred with a target of five minutes or less. The 0.12.0 stationary-contact candidate removes mandatory ground recovery, keeps its optional button, and records bounded contact views/native initiation evidence. The public APK, retained signer and exact payload/source closure are independently verified. PR #1 remains draft; main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261002-214857.zip` verifies THORHERO ID 1 /
COHLOCAL, seven power rows and fourteen costume rows, ordinary logout and
committed SQL save, verified Finish and clean owned-process shutdown. The
user reports smoother, tolerable client play; no sustained FPS benchmark or
complete terrain/materials acceptance is claimed. See [the accepted physical
checkpoint](android-evidence/thor-0.11.6-client-accepted-20261002.json).

Session start to DbServer readiness took **10m57s**; Atlas server readiness took
**21m50s**, followed by **9m46s** of client startup. First-use server data staging
cost 411.258s. These measurements support the user's unchanged-server-startup
assessment. Future server work should target **at most 300 seconds from session
start to Atlas server readiness**, including required preparation. This work is
explicitly deferred; GPU acceleration remains deferred as well.

The next playable checkpoint is ordinary stationary-contact interaction.
Ms. Liberty beside the Atlas statue and City Representative inside City Hall
are authored `PL_StandStill` contacts. The pinned client's cursor/A-left-click
path sends `CLIENTINP_TOUCH_NPC` to normal contact dialogue processing without
requiring a beacon graph. F is Follow, so no invented Interact binding or chat
command is introduced. Use the [short 0.12.0 checks](COH-Atlas-Gameplay-0.12.0-testing.txt)
to open a readable dialog, record its view, read an information response and
close it normally before Save/Finish. Task acceptance, training, moving NPC
pathing, combat and authentic generated beacon loading remain later milestones.

Movement and normal Save now become available after current native connection,
a bounded play/save budget and three fresh Android views. Return to safe ground
is optional; when requested it still pauses controls until the actual ordinary
`/stuck` receipt, stable native positions and fresh views are verified. Normal
save requires current native Atlas position matching committed SQL, identity,
powers/costume and selected-row preservation, normal logout/disconnection and
fresh saved-character views. A skipped recovery has explicitly false ground
claims. Optional recovery cannot extend the previously established deadline.

Capture contact dialog retains three fresh 800x600 PixelCopy views per manual
request, with at most three requests, current session/PID/character binding,
strict frame/time watermarks and a two-minute request limit. Optional owned
native `ContactInteract` initiation/response records are read once at export,
never in readiness polling. Those logs precede dialog generation and do not
prove that a visible dialog or mission/combat effect succeeded. The user supplies
that assessment. Native contact-state persistence is outside the protected
identity/power/costume selected rows; no database writes are made by observers.

Focused qualification passes **161 checks** and binds **84 source files**.
The candidate retains all native/container, renderer, world/avatar and prepared
cache bytes from the exact public 0.11.6 APK; five Java sources and three guest
helpers change, and one bounded contact-evidence helper is added. Actual guest
extraction of all three server archives remains required before signing and
publication. Device contact interaction and normal save without recovery remain
unverified until the next export. The accepted long camera/jump/ground tests
must not be repeated solely for this checkpoint.

Published [0.12.0](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.12.0)
from source commit `1791a3203ecf662191f2d6e3401cfa9ea4692004` in successful
[run 37071344940](https://github.com/Russianranger/coh-android/actions/runs/37071344940).
The public APK is **595203099 bytes**, SHA-256
`4a507d7d59b3af07be74de4bf47e39b8fd09ac86266a34c4fefd756fb442ee7c`,
version code 13, with the same app ID and signer. Independent verification passes
both v2/v3 signatures, the complete 570-chunk APK digest, all 63 ZIP CRCs,
56 payload hashes, 84 published source pins and the actual 161-check CI receipt.
Exactly 50 donor payloads remain unchanged; all three raw server archives and
their actual packaged guest extraction match public 0.11.6. The public notes,
checksum, asset metadata and release body also close to the build receipt. See
[the publication receipt](android-evidence/contact-interaction-0.12.0-publication.json).

The superseded 0.11.0 Atlas workflow also triggered on the modern UI edit and
rejected a changed historical workflow pin before compiling or publishing an APK.
It is now manual-only, matching the earlier superseded responsiveness workflow;
the dedicated 0.12.0 release workflow completed successfully. This routing change
does not alter the published APK. PR #1 remains draft and main remains unchanged.

The prior published checkpoint follows:

**Current: 0.11.6 repairs the immediate 0.11.5 reopen packaging failure and reduces Android runtime-extraction allocation pressure. The public APK and retained signer have been independently verified. Game/MapServer binaries and their existing performance changes are reused exactly; no new native build or physical performance gain is claimed. PR #1 remains draft; main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261002-203058.zip` failed in less than a
second at `persistent_server_profile`: `Server payload archive metadata differs`.
All 26 members of the published game tar had nonzero timestamps, contrary to the
unchanged guest extractor's canonical metadata contract. Reproducing the exact
public APK rejects the first file before any PostgreSQL, DbServer, MapServer,
Wine or client process starts. The failed operation did not open the persistent
character database. See [the failure evidence](android-evidence/thor-0.11.5-reopen-preflight-failed-20261002.json).

The writer now produces zero timestamps and preserves the strict extractor.
Before signing and again before publication, the actual guest consumer extracts
all three server archives; a JSON/hash-only check cannot substitute for this
proof. Focused qualification passed **118 tests** and binds **116 source files**.
The exact completed native build from run 37048610759 is reused and both actual
Game/MapServer executable bytes are compared against public 0.11.5. Historical
full native/runtime pipelines remain skipped for this bounded repair.

Android tar extraction now reuses one 64 KiB copy buffer per archive, replacing
one 1 MiB allocation per member. A 1,002-member extraction fixture with a 32 MiB
Java heap reduced measured collections from 125 to 1 with identical extracted
bytes. This verifies allocation pressure, not a device crash cause or speedup.
The attachment contained no refresh crash trace. Android 11+ reports now include
up to four own-app historical exit records at the next completed operation,
without trace streams; unavailable exit history cannot block the report.

[Download 0.11.6](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.6/COH-Atlas-Gameplay-0.11.6.apk).
Built from `6557a21dbd696c9ac8e9b9344a0e8d7553d5a345` in
[run 37063509202](https://github.com/Russianranger/coh-android/actions/runs/37063509202),
with both observer and APK jobs successful. The public download is
**595,194,816 bytes**, SHA-256
`c8a0b2801c6f4ea80ef6df17f7e66f0a90b0ad128ef86fbb39d94c6d54182895`.
Independent v2/v3 signatures and the full 570-chunk content digest, all 55
payload hashes, every ZIP entry CRC, binary app/version manifest and actual
packaged guest extraction pass. The retained native files and qualified source
closure match their expected bytes.

Install over the existing app, preserve imports and THORHERO, refresh runtime once,
then reopen. Use the [short 0.11.6 checks](COH-Atlas-Gameplay-0.11.6-testing.txt)
with ordinary Save/verified/Finish; the accepted long camera/jump tests need not
be repeated. First cold server and texture-index work still take time. Device
startup/FPS gains and saved exterior-position reopening remain unverified.
GPU acceleration and broader cross-session warm-server lifecycle work remain
pending. See [publication evidence](android-evidence/reopen-repair-0.11.6-publication.json).

The prior published checkpoint follows:

**Current: 0.11.5 is published and implements the user-authorized non-GPU performance recommendations. Native immediate ready/position events, a batched texture-header index with normal-loading fallback, transient minimum graphics, and one bounded pre-menu early-client retry are implemented. Native compilation, focused CI packaging and independent public APK verification passed; no device speedup is claimed. Broader warm-server reuse across completed sessions is still pending.**

The physical 0.11.4 export `coh-atlas-gameplay-20261002-172722.zip` showed no
noticeable improvement: interactive startup took 29m54.324s, versus about
29m28s in the accepted 0.11.3 run. Cold data preparation cost 401.760s; Atlas
startup took 639.458s and client startup 583.631s. Client texture headers alone
took 133.526s. Native ready and ground observations arrived through the old
60-second logger queue with measured delays of 62.346s and 71.260s. These
measurements motivated native work rather than another host-only derivative.

The new native event channel is session/PID/main-thread/SQL-identity bound and
flushed immediately. It retains completed MapServer ticks, two actual stable
positions 25–90 seconds apart, ordinary `/stuck`, fall checks and three fresh
Android views. Logout/save still uses its original normal countdown and SQL
proof. The indexed texture header/name/mip pack preserves full textures and
prepared Parse6 caches, validates import/executable/inventory identity, and
falls back to normal reads when unavailable or invalid. Repeated missing-file
diagnostics are deduplicated within load stages; validation is retained.

The default-on performance checkbox applies the existing minimum native
quality preset and 0.75 world render scale at the next launch. Saved graphics
preferences are captured before the overlay and restored before persistence;
unchecking it restores the normal profile. Rendering remains llvmpipe, with
800x600 UI and the existing 10 FPS cap. Actual loading/FPS improvements await
a short physical comparison using [0.11.5 notes](COH-Atlas-Gameplay-0.11.5-testing.txt).

Warm service reuse in this candidate is limited to one natural client early
exit before interactive menu/login, within the same active operation. It
requires proven client shutdown, unchanged SQL rows, live owned servers and
current MapServer ticks; retry gets a fresh attempt ID within the original
startup deadline. Finish/Stop still shut all owned services down. This is
not a fix for every later login-menu bounce or cold session start. GPU
acceleration remains deferred by the user.

[Published 0.11.5 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.5/COH-Atlas-Gameplay-0.11.5.apk)
was assembled from `bfa5a3da01789c634bdcab8e2d7134f71f54fe24` in
[APK run 37049707089](https://github.com/Russianranger/coh-android/actions/runs/37049707089).
Both observer and APK jobs passed. The separate
[native run 37048610759](https://github.com/Russianranger/coh-android/actions/runs/37048610759)
built Game and MapServer from `0ddd27dfaddf9ac53a6a65548c8199bced767fbe` after the
real Win32 flushed-event fixture and exact overlay staging passed. Received
Windows PG LF/CRLF provenance is validated without relabelling its source chain.
No full native gameplay/physical milestone is repeated. Focused qualification
passes **195 checks**, authenticates the exact 0.11.4 donor's 50 payloads and all
16 Java sources, and binds **120 source files**. The full local interactive suite
passes **434 tests** without skips.

The public APK is **595,194,816 bytes**, SHA-256
`5ba95d45bfbe0a2cda74bb632b80d1499058f5c8b40c48d9d422a9304cdb9941`.
Its complete download matches the build and release asset pins. Independent
v2/v3 signatures, the full signed content digest, ZIP CRC, binary app/version
manifest, all **55 payloads**, qualified source closure and native-container
comparison against the exact donor pass. Only Game, MapServer, the launcher,
six explicitly allowed guest helpers and their manifests change; four guest
helpers plus a native receipt are added. DbServer, DLLs, prepared caches, imported
world/avatar assets, Android native libraries, resources, app ID and signer remain
retained. Only Activity/Runtime Java sources change for graphics preference and
launch environment. See [the publication receipt](android-evidence/responsiveness-0.11.5-publication.json).

PR #1 remains draft and main is independently confirmed at
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`. Install over the existing app, refresh
runtime once, retain imports and THORHERO, and use the short comparison notes plus
ordinary Save/Finish. Physical speed gains and the saved exterior-position reopen
remain unverified. Broader persistent warm-server lifecycle work remains pending;
GPU acceleration is deferred by the user.

The prior published checkpoint follows:

**Current: 0.11.4 is published for the user's startup/readiness priority. The bounded derivative removes whole-data-tree log scans, reuses completed owned private server data on later starts, and buffers RFB input. Focused host qualification, CI packaging and independent public APK checks passed; physical timing and gameplay-FPS gains remain unverified. Physical 0.11.3 outdoor movement, usable presentation, phase deadlines and ordinary save/Finish/cleanup remain accepted. THORHERO, seven powers and fourteen costume parts are preserved; the saved exterior position awaits a subsequent reopen. PR #1 remains draft; main stays 04d62616.**

The accepted run spent about 29 minutes 28 seconds reaching the interactive menu.
Repeated readiness queries then walked roughly 177,000 private data files to find
logs, and server preparation rebuilt the entire private data tree each session.
The performance pass narrows current-session log reads to owned root logs and the
owned logs subtree. Poll cadence is measured from poll start; timing reports retain
launcher start, observer costs and the original ground-verification samples.
Current native identity, complete-record, stable-ground, SQL save and deadline
checks remain required.

Private data reuse is limited to the same source/import/runtime identities after
proven owned-process and Wine shutdown with credential configuration removed.
Session executables, configuration and logs are fresh. Interrupted or invalid
cache generations remain preserved and are bypassed with fresh preparation.
The first launch after the APK/runtime update still constructs the new cache;
later same-generation starts can retain generated private MapServer caches and
avoid recreating the imported leaves. Old unreceipted 0.11.3 trees are not adopted.

RFB input now uses a bounded 64 KiB buffer. The deterministic full 800x600 plus
incremental-frame fixture reduces underlying reads from 658 to 31 with identical
pixels, requests, sequence ownership and cancellation behavior. This measures
transport overhead, not game FPS. Native rendering still uses software llvmpipe;
the observed world rate was well below the existing 10 FPS launcher cap. Native
renderer, cap, display resolution, Surface capture and frame-proof paths remain
unchanged. Device improvement must be assessed from a short comparison run,
using [0.11.4 testing notes](COH-Atlas-Gameplay-0.11.4-testing.txt), rather than
replaying the accepted long movement/camera/jump milestone.

The focused derivative qualification passes 186 unittest methods plus 89 Java
budget scenarios and binds 85 source files. It authenticates the exact published
0.11.3 APK, its 49 payloads, all sixteen Java sources and the four immutable
lineage receipts. CI interactive discovery passes 393 executed tests, with one
existing Tesseract-dependent test skipped (394 methods). The
historical 0.11.3 transform test now uses byte/hash-pinned published helper fixtures
with its original positive and negative assertions; no test suite is filtered.
The required host cache fixture creates 4,002 links cold and zero warm, with 25
directory checks (0.824119 / 0.004263 seconds on this host). These are fixture
measurements, not Thor startup timings. Historical 0.11.2/0.11.3 publication
workflows remain manually dispatchable; the new derivative has its own exact
retained-donor workflow. Native/physical milestones are not repeated for this pass.

[Published 0.11.4 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.4/COH-Atlas-Gameplay-0.11.4.apk)
was built from `97c5ece986c9ba91825844e648d728ee310ed732` in
[run 37030944557](https://github.com/Russianranger/coh-android/actions/runs/37030944557).
Both observer and APK jobs passed. The public APK is 595,116,556 bytes, SHA-256
`8f5a398f15adc4d94ed1137817a7db696bafa3c03aa0e7a54638e5570bfb0fa3`.
Its complete download matches the build and GitHub release pins; ZIP CRC,
independent v2/v3 RSA signatures and the full 570-chunk content digest pass.
All 50 payloads match the build receipt. Six existing guest/verification payloads
change, one cache helper is added, and DEX is recompiled with only the exact
bounded RFB source wrapper changed. Other Java sources, resources, signer,
application ID, native runtime/client/server and world/avatar bytes are retained.
See [the publication receipt](android-evidence/startup-perf-0.11.4-publication.json).
The actual CI cache fixture records 4,002 to zero link creations and 25 directory
checks, taking 1.085236 / 0.005661 seconds on that host; it is not a device timing.
Generic push tooling runs 37030944503 and 37030944442 passed with all native,
cache-build and APK jobs skipped. No accepted native or physical gate repeated.

Next: use the short 0.11.4 readiness/frame-pace comparison and normal Save/Finish
to establish a completed data-cache generation. A later necessary reopen can
compare warm startup and the saved exterior position. Reports now distinguish
preparation, native readiness and observer costs. Native client/Atlas loading and
software-renderer FPS remain targets beyond the removed host overhead; no device
speedup is accepted until the new export is reviewed. Genuine beacon generation,
NPC pathing/combat and complete materials/minimap remain separate pending gates.

The physical 0.11.3 checkpoint follows:

The returned `coh-atlas-gameplay-20261002-145320.zip` independently confirms
normal `/quittologin` delivery at 14:50:24.531 UTC, native logout timer expiry
at 14:50:27, committed SQL verification at 14:52:01.321, guest receipt of Finish at
14:52:19.993 and complete cleanup at 14:53:14.783. The committed exterior
position is **(104.47185, 31.959229, -531.55786)**. ID 1 / COHLOCAL and all
selected rows remain identical except the expected LoginCount 4 to 5. The
canonical saved selected-row snapshot is
`648b7ca2368748f0bbd5020e7bcd99a6a1b9e040728ac8f73cb525ff323123e0`;
positions are verified by a separate SQL query and matching native records.
See [the physical outdoor movement/save receipt](android-evidence/thor-0.11.3-outdoor-movement-save-passed-20261002.json).

The initial interior is explained by the previous committed position
(133.92833, -768, -594.64825), which still matched the accepted interior save.
The previous outdoor run requested no new normal save. Native resume then chose
the authored nearby-door auxiliary exit (134.5, -768, -575); this is normal
door emergence, with no reset or persistence defect indicated. The prior
selected-row snapshot differs from this run's baseline only in LoginCount 3 to 4.
Do not claim that the new outdoor position has already survived another restart.

All 23 exported Android PNG hashes, sizes and dimensions match; connection,
ground and save each have three fresh sequences after their event watermarks.
They show City Hall, outdoor Atlas Plaza and the login screen after logout.
The user's new screenshots and report accept outdoor movement and usable
presentation. Prior camera/jump and tested-route no-clipping acceptance remains
retained. Flat white ground, purple/blue surfaces, UI placeholders and **Map
Unavailable** remain visible, so complete materials/minimap and broad collision
coverage are not accepted. Automated rendering/controller/input-effect flags
remain false; user acceptance is recorded separately. Runtime/identity manifests
match published 0.11.3, without claiming independent installed-APK byte attestation.

The delivered `/stuck` at 14:44:14.313 anchors movement/Save/proof deadlines at
14:50:14.313 / 14:51:14.313 / 14:54:14.313. Revision 2 shortened the connected
allowance; no renewal or expiry revival occurred. Android recorded input cutoff
558 ms after its deadline, and normal Save delivery arrived 49.782 seconds before
the Save cutoff. Finish and cleanup completed before final expiry. This run also
finished before the original menu deadline, so expired-phase behavior was not
exercised physically. A complete 60-second all-controls-neutral interval is not
proven: the last retained ordinary input preceded Save delivery by 44.728 seconds
and could have been a cursor/release event. Current stable native samples and
ordinary committed-save proof passed; retain the 60-second neutral test guidance.

Responsiveness remains a concrete next target. Guest start to interactive menu
took about 29 minutes 28 seconds: Wine refresh 64 seconds, private data/DbServer
7 minutes 16 seconds, Atlas 10 minutes 43 seconds and client startup 9 minutes
38 seconds. `/stuck` delivery to ground observation took 1 minute 55 seconds,
followed by 2.217 seconds for fresh Android frames. The final pre-save ground
samples at 14:49:45/14:50:15 are refreshed evidence and must not be attributed to
the initial 14:46:09 ground event. This run has no cold-login watchdog/auth failure
or disconnect before normal logout. Do not import the prior failure diagnosis
as a new failure, or blame all user waiting on disabled controls: native records
already show outdoor traversal before `/stuck` was requested.

The menu allowance remains 1200 seconds. A current validated native connection
receives a one-shot allowance up to 1200 seconds, capped at actual launcher start
plus 2040 seconds and overall-operation deadline minus 120 seconds. A current
ordinary `/stuck` receipt anchors movement/save/proof deadlines at 6/7/10 minutes.
The last minute before Save is reserved for neutral standing; the following
three minutes are reserved for the existing normal logout, SQL proof and Finish.
Caps can shorten the visible window. Duplicate events cannot renew it, expired
phases cannot revive it, and the Android shell binds the UTC deadlines to uptime.
Android independently caps event admission at its display announcement plus
35 minutes, providing one minute of headroom between announcement and launcher start;
the guest's actual emitted policy cap remains 34 minutes before the native
36-minute launcher lifetime. Menu/creation behavior and normal-save validators
are unchanged. Input cutoff releases held movement/camera inputs and preserves
a queued ordinary Save command. No automatic logout is requested.

[0.11.3 focused testing notes](COH-Atlas-Gameplay-0.11.3-testing.txt) request a
brief route to a safe outdoor spot, preferably more than 30 units from a door,
60 seconds standing still, normal Save before its cutoff, then verified Finish
and report export. A later reopen can assess the new outdoor saved coordinate.
The existing native cold-load timeout remains in place. The update does not
claim to fix the inferred cold-login watchdog or complete materials/collision.

[Beacon input preflight](android-evidence/atlas-beacon-input-preflight.json)
audits six supplied inventories and pins the loader's expected Atlas v8 graph
and v9 date-sidecar/CRC inputs. Zero generated graphs were found. Optional
supplied files can receive bounded prefix/hash/sidecar checks but always remain
unqualified until provenance, full structure, loaded-world CRC and native graph
loading are established. No fake graph, NPC readiness or combat acceptance is
claimed. [Published 0.11.3 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.3/COH-Atlas-Gameplay-0.11.3.apk)
was built from `97565b0c28ba27ef79e70d4c04dddb1a8383ec1f` in
[run 37015136168](https://github.com/Russianranger/coh-android/actions/runs/37015136168).
Its observer and APK jobs passed. The exact focused receipt passes 102 unittest
methods plus 89 Java protocol scenarios and binds 61 source files. The complete
Android source closure (16 sources) compiled; only Runtime, Service and Activity
changed and the budget class was added. APK size is 595,108,273 bytes and SHA-256
is `3c97d5c85092ec9aec88de405cea92a91c760db379cdbf66a244714687f35dfd`.
The public download matches this complete pin. Independent RSA/SHA-256 v2 and
v3 signature checks and the full 570-chunk APK content digest passed. [The publication review receipt](android-evidence/session-window-0.11.3-publication.json)
records the independent signing/content/payload review. The existing app ID,
signer, native libraries/client/server, world/avatar assets and unrelated Java
sources are retained. Four existing guest/verification payloads change, one new
budget module is added, and the Android DEX is recompiled. Resources are unchanged.

The previous full client/DbServer native gates did not repeat: push tooling runs
37015135666 and 37015135634 passed and their native runtime/APK/cache jobs were
skipped. The historical 0.11.0 gameplay publication workflow also triggered on
Activity and failed closed at its old donor-source boundary, as expected for this
new derivative; it did not boot a native runtime or replace an old release. The
new 0.11.3 workflow passed its own exact current-source and donor boundaries.

Next: use the archived startup/readiness timeline to reduce expensive preparation
and observation latency while preserving existing data, cache, normal-save and
native guards. Assess the newly saved exterior coordinate on a later necessary
reopen; do not repeat the accepted long physical/native gates solely to record
this checkpoint. Qualify a bounded genuine one-map graph generator, provenance,
full structure and loaded-world CRC before installing an Atlas beacon graph.
NPC pathing/powers/combat still follow genuine graph loading. Rendering/minimap
completeness is a separate gate; beacon data alone does not qualify it.

Previous physical evidence checkpoint follows:

**Previous physical checkpoint: 0.11.2 verifies the prior movement-save survived reopening, normal City Hall door emergence, traversal into outdoor Atlas, usable outdoor rendering and no clipping on the user's tested route. The earlier interior movement/camera/jump and normal-save gate remains accepted. The latest export is correctly failed because the 20-minute menu-based interaction budget expired without a requested outdoor save; cleanup passed. Next development should provide a bounded gameplay/save window after world readiness, trace cold-login loading timeouts and qualify genuine Atlas beacon inputs before NPC/powers/combat. Complete materials/collision and a new outdoor save/reopen remain pending. main stays 04d62616 and PR #1 stays draft.**

The returned `coh-atlas-gameplay-20261002-125646.zip` proves the entire SQL
baseline equals the previous accepted saved snapshot, SHA-256
`be69e921dfafb584ae0fd263693a6f43eb6f1577125dfa5b17b4852576071362`.
THORHERO ID 1 / COHLOCAL, LoginCount 3, seven powers, fourteen costume parts
and the committed position (133.92833, -768, -594.64825) survived the restart.
Initial native records repeat that position at their two-decimal precision.
The user reports the same initial nearby City Hall location, then successful
exit into outdoor Atlas with decent rendering and no observed clipping.
Native periodic records confirm stable outdoor ground near (132.82, 44.04,
-597.78). This accepts the observed route and usable exterior presentation,
while broad terrain/collision coverage and complete materials remain pending.
See [the outdoor observation and incomplete-save receipt](android-evidence/thor-0.11.2-outdoor-observed-save-incomplete-20261002.json).

Native resume intentionally moved the character to (132.5, -768, -576)
before `/stuck`: `resumeCharacter()` calls `prepEntForEntryIntoMap()` with
`EE_USE_EMERGE_LOCATION_IF_NEARBY`. It finds an emergence marker within
30 units and places the player at an authored auxiliary door exit; the
City Hall door transforms give the exact observed coordinate. This is normal
door behavior, not a persistence defect. A later exact outdoor coordinate
test should save more than 30 units from a doorway. The latest run did not
request another save, so no newly committed exterior position is claimed.

The first cold MapServer connection began at 12:36:07 UTC; world loading
continued through actor-spore initialization at 12:38:29 before the client
returned to login with **Lost connection to server** around 12:38:32.
`commLinkLooksDead()` uses a 120-second stale-link threshold during loading,
and `commCheck()` contains the matching return-to-login branch. The successful
retry took about 115 seconds. These facts support a cold-load watchdog
diagnosis, but the export contains no explicit 120-second alarm. The later
**Unknown auth code: -1** disconnect is not evidence of a MapServer crash.
Do not add an unqualified `-notimeout` bypass or reset the preserved profile.

The diagnostic's 1200-second interaction budget started at menu/input
readiness, 12:34:42 UTC. Connection observation arrived at 12:44:54 and
ground verification at 12:49:01, leaving only 5 minutes 41 seconds before
the 12:54:42 Android deadline. The guest emitted `interaction_timeout`
at 12:54:51, then correctly failed **Character save was not verified**.
No Save character / log out or Finish request was sent. The display-closure
error accompanies producer shutdown; cleanup completed with no remaining
owned workers or inspection failures. The prior successful normal save is
not invalidated by this unfinished new save.

All 20 retained Android PNG hashes match their files, with three fresh frames
after connection and ground verification. Those retained frames show the
interior/EXIT doorway. The guest final frame shows outdoor statue, plaza,
buildings and vegetation, with purple/overbright surfaces and a white sky
still visible. The user's physical observations support delivery to Thor;
no fresh retained outdoor Android PixelCopy proof is claimed. The attached
06:45 interior screenshot duplicates the previous run and is excluded from
new outdoor evidence.

Next implementation scope:

1. Give the reopened character a phase-aware, bounded gameplay/save budget
   after native connection/ground verification. Synchronize the Android
   countdown with the guest deadline and retain the overall runtime cap.
   Reserve time for the existing 60-second neutral wait and normal logout;
   keep recovery-receipt age, identity, stable-ground and SQL save checks.
2. Investigate the cold world-loading watchdog using the archived timings;
   preserve native timeout behavior until a bounded correction is qualified.
   Do not rerun the accepted physical route solely for this diagnosis.
3. Audit authentic generated Atlas beacon data or a bounded one-map generator.
   No generated `.bcn` is in the repository/shipped package; the authored
   beacon layer is placement data, not the combat graph. The generation chat
   commands are disabled in the native command table, so there is no supported
   manual `/beacongenerate` or `/beaconprocess` procedure for the current APK.
   The native loader expects `server/maps/City_Zones/City_01_01/City_01_01.txt.v8.bcn`
   and uses map CRC/date metadata. A genuine graph needs a separate verified
   server-only installer: the current world supplement accepts only geometry
   and textures. Prove graph loading and CRC compatibility before NPC/combat.

No APK was changed or published for this evidence checkpoint. The earlier
saved-position/outdoor procedure below is historical; no unchanged Thor boot
is requested. The previous interior acceptance and publication are preserved.

The returned `coh-atlas-gameplay-20261002-115211.zip` passed the composite
existing-character recovery and normal-save gate with zero failed input sends.
The user explicitly reports successful movement, camera and jump and adequate
interior rendering. The screenshots show the City Hall floor, walls, columns
and character and the **Atlas position verified** status with movement enabled.
This accepts the focused physical input/interior gate; the report's broad
automated gameplay/controller/rendering booleans remain false by design and
are not reclassified as automatic visual or gameplay proof.

Native evidence and committed SQL independently support the normal save.
The prior saved position was (123.5, -768, -579); the character moved about
18.80 horizontal units to (133.92833, -768, -594.64825). Two native observations
at 11:46:30 and 11:47:00 UTC agree at their two-decimal precision. The real
`/quittologin` receipt precedes **Logout timer expired** at 11:47:12 UTC,
followed by the committed-save proof at 11:49:07 UTC. LoginCount advanced
2 to 3; identity, selected entity fields, powers and costume remained intact.
Three fresh Android PixelCopy captures after each connection, ground event
and save match their exported PNG hashes and exceed the corresponding frame
watermarks. Guest and Android cleanup passed with no remaining owned workers.
See [the accepted physical receipt](android-evidence/thor-0.11.2-interior-movement-save-passed-20261002.json).

Use [the saved-position and outdoor procedure](COH-Atlas-Gameplay-0.11.2-saved-position-outdoor-testing.txt)
on the already installed 0.11.2 APK. Preserve the existing runtime and character.
Leave controls neutral for 60 seconds after gameplay appears and capture the
initial view **before** Return to safe ground. The current app's reopening
status verifies identity and native readiness, not coordinate restoration;
review the initial native records against baseline SQL separately. Then use
one ordinary recovery command to unlock movement, test a bounded City Hall
route and the ordinary exit into outdoor Atlas, and perform another normal
save. Complete the route and 60-second neutral settling within the existing
ten-minute recovery window. No new APK, character creation or hosted game
session is required for this gate.

The following preserves the 0.11.1 failure diagnosis and 0.11.2 publication
history. Its pending focused movement/save retry is now accepted above.

The returned `coh-atlas-gameplay-20261002-095609.zip` records native connection
and existing identity verification for THORHERO ID 1 / COHLOCAL. Baseline
SQL contains seven powers and fourteen costume parts. `/stuck` moved the
character from the -2000 synthetic floor to City Hall's authored interior
spawn, then the native logger repeated that exact position every 30 seconds.
The old verifier rejected negative elevations below -100 in both the live
and committed-save observers, so it never announced character_relocated.
Controls and save remained disabled until the recovery receipt expired;
the shared receipt reader's generic logout/save-window error is secondary.
The final report therefore fails the composite gate despite successful
physical reopening. No requested normal save was performed. Cleanup passed.
See [the physical failure receipt](android-evidence/thor-0.11.1-ground-verifier-failed-20261002.json).

The source correction changes only `local_character_server.py`: a shared
height predicate rejects Atlas's synthetic -2000 fall floor with one unit
of clearance, accepts genuine subterranean Atlas rooms, and keeps the
existing identity, owned log route, freshness, latest-pair stability and
SQL position matching. Two numerical observations do not prove all collision
geometry; that remains explicitly false in the evidence. Eight new regressions
replay unmodified physical native records and exercise save/identity/fallback
boundaries, alongside the fourteen existing observer regressions. The receipt
used for archived replay is labeled synthetic because the original private
delivery file was not exported. No new hosted game session is claimed.

The dedicated `android-ground-repair.yml` packages a 0.11.2 derivative of
the exact published 0.11.1 APK, retaining the PRoot avatar repair, DEX, resources,
world, native libraries, client/server binaries, application ID and signer.
Only the observer and its client/runtime verification manifests may differ;
Android package metadata advances to version code 8. No unchanged server
rebuild, character creation or hosted seed/reopen gate is requested.
[Publication run 36994687459](https://github.com/Russianranger/coh-android/actions/runs/36994687459)
passed both observer and APK jobs at `7e2f44b122417192ec1d9dd6d973b27b594e0a82`.
The public signed APK is 595,104,089 bytes, SHA-256
`1e8b9ffd09dcfa6967685e31b1ccbff1acf200b892614e6ec2f6092d533e8adb`.
Independent public-download review checked all payload pins and ZIP CRC,
unchanged DEX/resources and the exact three-member derivative boundary.
The complete build receipt and review are archived in the physical failure
receipt's corrective_publication section. Ten qualification source pins
match the packaged code commit; the 22 observer and 13 packaging tests passed.
[Download COH Atlas Gameplay 0.11.2](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.2/COH-Atlas-Gameplay-0.11.2.apk).

Commit `88c8b9a9` narrows the old retained-reopening fixture wildcard to its
original name-row image. Its routing-only run `36994935181` passed tooling
and skipped the unchanged runtime. The broad wildcard had queued old run
`36994687391`; it failed the retained 0.10.0 Java-source boundary before a
graphical session started. No accepted character seed/reopen session was
repeated. Preserve that failure receipt as a routing issue, not as evidence
against the separately successful 0.11.2 observer/package publication.
[The original focused physical procedure](COH-Atlas-Gameplay-0.11.2-testing.txt)
was the in-place update and one runtime refresh used for the now accepted
ground verification, brief movement, jump/camera and normal-save gate. Its
installation/refresh step should not be repeated for the next saved-position
and outdoor test. Sustained collision/outdoor scenery precedes map beaconing
or native NPC/powers/combat.

The following preserves the completed 0.11.1 publication and earlier history.
Its formerly pending physical reopening and focused interior input/save gate
are now accepted as described above; sustained outdoor rendering/collision
and NPC/powers/combat remain pending.

[Download COH Atlas Gameplay 0.11.1](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.1/COH-Atlas-Gameplay-0.11.1.apk)
as an in-place update, then Refresh runtime once and Reopen saved THORHERO.
Do not clear storage, reimport data or create a replacement character.
[Run `36944389469`](https://github.com/Russianranger/coh-android/actions/runs/36944389469)
at `34b763a5518e3fa3740c197c0e824c17da088536` passed all three jobs:
tooling (15 installer regressions, 12 package boundary tests and routing),
actual native ARM64 PRoot migration, and retained-signer packaging/publication.
The migration reproduced ELOOP, verified/repaired 21 old avatar files,
reused all 21 on repeat, removed hidden backing entries, preserved sentinel
state and passed six refused-invalid cases plus both interrupted-repair retries.

The public APK is 595,104,089 bytes with SHA-256
`f4e30c728046771cb91beece46fb54663b0fcd57a28b8e055f6fc8918dd3c899`.
It retains application ID `io.github.russianranger.cohclientinteractive` and
signer `92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`,
and advances to version code 7. Independent download review verified the
complete public APK digest and every payload pin against the signed build.
Only the avatar helper and its client/runtime verification manifests change;
Android package version metadata is updated. The DEX, resources, world,
native runtime, client and server remain byte-identical to published 0.11.0.
See [the complete reviewed qualification/publication receipt](android-evidence/avatar-repair-36944389469-reviewed.json)
and [the focused physical instructions](COH-Atlas-Gameplay-0.11.1-testing.txt).
The existing screen heading still says v0.11.0 because the controls are retained;
Android app version and exported reports identify the new 0.11.1 candidate.
No physical reopening, rendering, ground recovery or gameplay acceptance is
claimed by this hosted file-migration check.

The user's `coh-atlas-gameplay-20261001-233407.zip` contains a 0.11.0
`character_reopen` failure after about 2.5 seconds. Inputs, the reused private
worktree, persistent server profile and durable PostgreSQL startup passed.
The first avatar verification then failed with `Errno 40` at
`data/player_library/male_boot.geo`. Wine, DbServer, Atlas and the game client
never started; no rendering, ground recovery, movement or normal second save
was reached. The report records `before_character_id=1` but leaves
`existing_character_verified=false`; this attempt did not verify reopening.
PostgreSQL stopped
gracefully and Android verified cleanup. See
[the physical failure receipt](android-evidence/thor-0.11.0-reopen-failed-20261001.json).

The accepted older avatar installer used `os.link` under PRoot
`--link2symlink`. Its two hidden backing entries embed absolute paths. A later
wrapper-only directory rename preserves bytes but breaks those embedded paths;
strict `O_NOFOLLOW` then reports the observed `ELOOP`. The corrective helper
recognizes only the relocated old avatar publisher's exact link layout,
verifies the pinned payload, mode, timestamp and ownership, and atomically
materializes its logical leaf. Verified hidden backing entries are removed
before MapServer staging. Imported files, caches, worktree identity and the
saved database are untouched. Focused qualification must reproduce this with
the actual pinned ARM64 PRoot; source-equivalent unit tests alone do not close
that gate. The successful run above now closes that focused repair gate;
physical results remain pending.

The corrective checkpoint adds 15 avatar installer regression cases, including
the moved emulated-link layout, refused invalid chains and cleanup retry. The
new retained-donor packaging boundaries pass 12 tests; routing passes its
focused check. Independent extraction of the actual published 0.11.0 APK
verified all donor pins and exactly three revised payloads: the avatar helper,
client verification manifest and runtime verification manifest. The other 48
APK members, including the DEX, are retained. The bounded
`android-avatar-repair.yml` workflow must first reproduce the legacy failure,
repair and retry under native ARM64 PRoot, then package/sign/publish 0.11.1
(version code 7) using the retained key. No Wine/server/world rebuild or passed
two-session graphical requalification is requested. The workflow and corrective
publication now pass. Resume physical testing with
[the 0.11.1 instructions](COH-Atlas-Gameplay-0.11.1-testing.txt).

Focused ARM64 run `36943167422` built the matching PRoot successfully but
stopped the migration gate on a hidden `.l2s..avatar-pending-*.0001` file's
owner check; no corrective APK was built or published. Pinned PRoot's hidden
backing stat hook restores the physical host UID after guest UID mapping.
The narrow backing-file reader now accepts the mapped owner or the same real
UID from `/proc/self/status` as existing owned-process cleanup, since extension
order can reverse across fork. Ordinary payload reads
still require the mapped guest owner; only the exact recognized legacy backing
names may use the real-owner check. The fixture compares the same underlying
owner across this virtual stat difference and preserves detailed failure
tracebacks. The successful focused retry above fulfills that requirement;
the completed 0.10.0 graphical gate is not repeated.

Retry `36943898161` at `fa104426` passed the checked 21-file repair and exact
payload/metadata comparison, then caught physically remaining intermediate
links. PRoot's virtual `lstat` reports those broken intermediates as missing,
so `lexists` cannot determine their physical presence. Cleanup now unlinks only
the preflighted intermediates directly and handles actual ENOENT, then removes
their verified backing files. Orphan preflight likewise uses bounded readlink
instead of virtual lstat. The added regression reproduces this missing-stat
view. No APK was built or published by either failed focused attempt.

The retained-APK [run `36929550592`](https://github.com/Russianranger/coh-android/actions/runs/36929550592)
passed tooling and the full native ARM64 runtime on host-driver commit `f7c6c3a6`.
The APK is byte-identical to run `36920583713` / source `204615c6`; no client,
server, native library or APK was rebuilt for the host OCR correction.
Independent review checked all 355 artifact members, 195 source pins, both
raw SQL/report/observer contracts, native CLIENT_READY and normal logout lines,
27 proof PNGs, ten raw PPMs and graceful cleanup. The same THORHERO ID 1 retained
seven powers and fourteen costume parts; LoginCount incremented from 1 to 2.
Ordinary `/stuck` produced fresh stable native positions near `(106.45, 0.25,
-114.45)` over 30 seconds; the second normal save committed that Atlas position
with MapId/StaticMapId 1. Both sessions stopped all owned workers.
See [the reviewed gate receipt](android-evidence/atlas-world-reopen-reviewed.json).

The [0.11.0 release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.11.0)
is published from code commit `1649e807d2b2310170e775c53bafa24cd932638a`.
[Build/publication run `36937373454`](https://github.com/Russianranger/coh-android/actions/runs/36937373454)
passed its actual qualification gate, Java/D8/resource build, payload comparison,
package badging, retained-key signing and release upload verification. The APK
is 595,099,993 bytes with SHA-256
`e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924`.
All three public assets are present: APK, checksum and focused testing notes.
Independent packaging review confirmed exactly five world-bound payload changes
and two Java UI/input changes, unchanged native/client/server payloads and the
same application ID/signing certificate. The complete build receipt and release
pins are retained under `publication` in
[the material receipt](android-evidence/atlas-material-inputs-0.11.0.json).
Both legacy workflows passed tooling and skipped duplicate APK/runtime jobs.
PR #1 remains draft and main remains `04d62616`.

A separate continuation review downloaded the **public release APK itself**
and independently matched its complete digest to the signed build receipt.
Every packaged payload pin, shipped Java source pin and preserved backend source
pin matched. All 2,904 decoded world files passed their recorded hashes; all
2,877 original world files were preserved and exactly 27 texture files were
added. The public testing notes also match the build pin. No passed runtime or
controller test was re-run, and no new APK was built. See
[the public-download review](android-evidence/atlas-gameplay-publication-36937373454.json).
The new materials' appearance and physical walking/jump/collision remain pending
until the focused Thor test. After accepting that report, reopen the movement-saved
position and qualify sustained Atlas movement/collision before first power/combat
work; that is new gameplay coverage, not a repeat of the accepted creation gate.

The earlier publication completed packaging, while the physical report now
requires the avatar reuse correction above. Preserve the
accepted physical 0.9.0 behavior and the healthy hosted 0.10.0 reopening gate.
Do not re-run either gate merely for completeness. Resume with the corrective
candidate's single focused Thor report covering reopening, scenery, neutral movement stop, jump/camera,
ground contact and normal save. Fix the exact observed defect next; after
initial world/movement acceptance, advance collision completeness, map beaconing
and native NPC/gameplay behavior sequentially.

Earlier hosted frame inspection confirms the avatar, ground, stairs, statue and building
geometry in the reopened Atlas frame. Materials remain flat or poorly textured,
and native UI still reports an unbeaconed map. This proves visible geometry and
recovery, not complete graphics, NPC pathfinding or physical gameplay acceptance.

The sequential 0.11.0 milestone adds only 27 texture targets named in the
retained material/shader warnings, preserving all 2,877 existing world files.
The revised supplement is 2,904 files / 318,611,871 decoded bytes. Exact public
range reconstruction fetched 4,357,758 bytes and reproduced its pinned ZIP;
[the material receipt](android-evidence/atlas-material-inputs-0.11.0.json) records
all old-payload preservation and new source/header checks. The finite MapServer
staging cap accounts for exactly the extra 27 files / 8,955,931 payload bytes.

The new Android controls map the left stick to forward/back and strafe, X to
jump, and held on-screen movement buttons to the same keys. Movement becomes
available only after native ground verification and fresh Android views. Keys
share ownership with keyboard/touch, use stick hysteresis, and release on neutral,
focus/dialog/disconnect/save transitions. Existing right-stick cursor, A click,
text input, D-pad and shoulder mouse-look behavior are preserved. Saving checks
the latest stable position after walking; stand still for 60 seconds and request
Save within ten minutes of Return to safe ground.

The gameplay builder retains the exact qualified APK backend and signing key.
Only two Java UI/input files may differ, and only five APK world-bound payloads
may change: the supplement ZIP/manifest, six immutable helper pins and their two
verification manifests. New materials and the complete 0.11.0 APK remain
host/device-unvalidated. The original reopening and legacy DbServer workflows
route these bounded derivatives to the gameplay builder; unknown/backend changes
and manual dispatches still request full qualification. No repeat seed/reopen or
unchanged DbServer rebuild is needed for this milestone.

Install the new candidate as an in-place update from accepted 0.9.0, keep the
private database/Wine/imports and THORHERO, and Refresh runtime once. Accepted
0.9.0 has no world marker; its first missing-only world install narrowly refreshes
private Atlas/affected geometry caches. No marker migration or cache-archive
replacement is needed. The focused [0.11.0 Thor instructions](COH-Atlas-Gameplay-0.11.0-testing.txt)
cover only reopening, visible Atlas materials, a brief walk/jump/camera check,
then normal save and export. Do not repeat character customization.


The following resolved regression notes preserve the path to the passed gate.

Run `36920583713` at `204615c6` proves the narrow NULL MapId baseline fix.
Its seed session passed in 1,845.046 seconds. The second session preserved
identity, authentication, powers, costume and the exact Atlas SQL position,
started Atlas and the graphical client, logged in locally, and reached the
existing character roster. The retained frame clearly shows THORHERO and the
default costume, but wide-region OCR misread the name as THOAMERG and refused
selection. No reopened CLIENT_READY, ground recovery or second save was reached.
Both sessions cleaned up their owned workers normally. See
[the preserved OCR failure receipt](android-evidence/character-reopen-hosted-36920583713-ocr-failed.json).

The host correction crops the character name row and uses grayscale single-line
OCR, retaining exact THORHERO matching and clicking only recognized bounds.
Retained attempts 1, 10 and 21 each recognize THORHERO at 70% confidence.
The dedicated retained-APK workflow downloads the unchanged signed 0.10.0 APK
from run `36920583713`, verifies all donor pins, and records the separate host
driver commit/source inventory. It performs two real sessions with a fresh
PostgreSQL profile; the failed run did not archive a reusable database cluster.
It does not rebuild client, server or APK components. The original full-build
workflow routes bounded host-only pushes to this qualification, avoiding a
duplicate runtime and rebuild. At that point, reopening remained pending until the normal
second save, persistence comparison and cleanup passed. Run `36929550592` above
now satisfies this gate.

Run `36913457461` at `07eb3ecb` completed with a runtime failure. Its first
graphical session passed in 1,840.069 seconds, reached CLIENT_READY, displayed
Atlas ground/stairs/statue/building geometry, and committed rows 1/1/7/14.
Native position stayed around `(106.45, 0.25, -114.45)` rather than falling to
Y=-2000. World surfaces and the avatar remain poorly textured/lit; this is
visible geometry, not complete graphics or device gameplay acceptance.

The second session reused PostgreSQL/Wine and all world/avatar files. Its read-only position after
normal DbServer startup was `MapId=NULL`,
`StaticMapId=1`, `(106.454605, 0.251066, -114.45343)`. The pre-entry guard
incorrectly required the temporary live map to be 1 and stopped before launching
Atlas/client. The outer RFB error is a consequence of that guest refusal. Both
sessions shut down PostgreSQL/Wine gracefully with no surviving owned workers.
See [the preserved failed receipt](android-evidence/character-reopen-hosted-36913457461-failed.json).

Pinned native source explains the NULL: first creation assigns MapId in memory
but writes StaticMapId to SQL; ordinary MapServer saves omit the read-only map
fields. Reopening an existing character writes its active MapId assignment.

The now-proven narrow correction accepts NULL temporary MapId only in the existing
character baseline, while requiring persisted Atlas StaticMapId, exact ID and
finite coordinates. Post-save live-map verification stays strict. The fresh
corrected candidate still uses version 0.10.0/code 5: none of the failed 0.10.0
APKs has been delivered for a Thor test. Existing creation, imports, costume,
powers and runtime components remain unchanged.

The first two hosted attempts stopped before client launch while mirroring the
private MapServer data. The initial staging budget omitted the pinned world and
avatar supplements; adding their exact inventory exposed the deeper cause:
PRoot's `--link2symlink` emulates each newly published hard link with hidden
backing entries. The 2,877 world files therefore left 5,754 extra entries and
619,311,880 extra bytes of staging accounting. Run `36905387168` refused entry
180,006 against the corrected 180,005-file cap and stopped all owned workers,
PostgreSQL and Wine cleanly. Preserve both failed receipts; neither APK is a
qualified Thor candidate.

World/avatar payloads and the world marker now publish through Linux
`renameat2(RENAME_NOREPLACE)`, retaining permissions, timestamps and fsync while
avoiding the emulated hard-link backing files. Existing paths are refused before
the PRoot rename hook, and the kernel refuses concurrent replacement. Publication
fails closed if that operation is unavailable. The finite inventory budget still
includes both pinned supplements. These changes required a fresh signed APK and real ARM64 hosted
qualification before the one-session Thor test; the retained-APK gate above
now completes that qualification. Dependency downloads
are bounded and reuse SDK 35 when already present on the runner.


Run `36909118523` passed tooling and prepared caches but its bounded compiler
install timed out on a throttled Azure Ubuntu mirror before APK packaging.
The build now uses Ubuntu's canonical signed mirror and only the required
MinGW POSIX compiler variant, with an eight-minute overall step bound.

The next candidate defaults to reopening the existing COHLOCAL / THORHERO ID 1.
It compares a read-only pre-login baseline with the ordinary committed save,
preserves identity, powers and costume, and requires LoginCount to increment
once. Its pinned Atlas supplement adds missing geometry and referenced textures
to the private client/server trees. A one-time refresh removes only affected
private compiled map caches; the original import and accepted cache archive are
preserved. The large supplement ZIP is reconstructed from exact reviewed public
PIGG ranges rather than committed as a Git blob.

The [static world review](android-evidence/atlas-world-static-review-20261001.json)
verified exact reconstruction of the 203,438,405-byte ZIP, all 2,877 decoded
files (309,655,940 bytes), a complete first install and repeat reuse, and narrow
cache refresh. The 4,209,334-byte manifest records 488 geometry and 2,389 texture
files with no accepted-import/avatar overlap. These are static checks; runtime
appearance and recovery still require the candidate's hosted/device evidence.
The complete install replay also used the accepted import's original directory
case plan, preserving all 741 existing directory spellings and inodes. The
[Android compile](android-evidence/character-reopen-android-compile-20261001.json)
passed resource linking, all 15 Java sources and D8 bytecode generation using
the official checksum-verified SDK 35 platform and build tools.

After native connection and three fresh Android views, the app enables
**Return to safe ground**, delivering ordinary `/stuck`. It requires two fresh,
stable native positions at least 25 seconds apart, then three fresh Android
views before enabling ordinary save/logout. The committed safe position and
preserved selected rows are required before three fresh post-save captures
enable Finish. Stable native position is a bounded recovery check; actual Atlas
appearance needs visual inspection, and full collision/gameplay remain pending.

The hosted candidate creates a seed through the actual graphical client, saves,
fully stops the owned stack, then reopens and saves the same character through
a second real session with the same PostgreSQL/Wine profile. This hosted seed
does not change the accepted Thor test. The user's next test is only the
[one-session reopen flow](ANDROID_CHARACTER_REOPEN_TEST.md), with the existing
character and app storage preserved.

The user completed `coh-character-creation-20261001-162621.zip` on Android 13 / AYN
Thor and confirmed the default Male costume, visible character/UI, normal save
and return from the game. The [device review](android-evidence/character-creation-thor-20261001.json)
accepts this session without another boot. Native evidence verifies COHLOCAL,
THORHERO ID 1, current CLIENT_READY, requested `/quittologin`, the live logout
timer and committed rows (`ents=1`, `ents2=1`, `powers=7`, `costumeparts=14`).
All 17 Android PNG records and four SQL table hashes were checked; three fresh
post-save captures show the login screen. Cleanup completed with zero remaining
owned workers and zero inspection failures.

The original wrapper remains `client_incomplete`: its final window check accepts
only the login title, whereas the same PID 672 retains
`City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 672` after entering
Atlas. The corrective Android source accepts that exact map title with the owned
PID and valid mapped window dimensions. It preserves every import/asset,
SQL/logout, fresh capture and cleanup requirement. All 188 interactive tests
passed, including the actual retained title and rejection regressions. This fix
is for the next APK; the installed 0.9.0 report and uploaded evidence are unchanged.

The scene is still an empty flat backdrop with a visible avatar and HUD.
Native position records show THORHERO falling to Y=-2000 before ordinary logout,
and the logout location is map 1 `(106.453125, -2000, -114.453125)`. This is a real
world/collision issue, separate from the reporting bug; its complete cause is
not established. Keep the existing database and character. The next candidate
must reopen this exact saved character, resolve Atlas geometry/collision and
provide safe relocation of the retained character if required. No character
deletion, recreation or SQL synthesis, and no repeat creation-only device test.

The delivered signed APK is from source `bc4d750deab00f0fdbbd084b32b563aa3abdddce`,
[run 36862027713](https://github.com/Russianranger/coh-android/actions/runs/36862027713),
386,658,292 bytes, SHA-256
`001e1dc4db87f1184814a8f75a33953504d6ee06b238490a8c26c71c4ca7f963`.
Independent [package](android-evidence/character-package-review-36862027713.json)
and [hosted](android-evidence/character-hosted-36862027713.json) reviews passed.
The Male/Clear creator renders its full body and both hands. The owned client
reached CLIENT_READY on Atlas, submitted `/quittologin`, ran the live logout
timer and committed one ents row, one ents2 row, seven power rows and fourteen
costume-part rows. Three fresh host captures follow login, connection and save;
the final view returns to login. Cleanup completed with no remaining workers.

Atlas reaches its HUD and welcome, but the scenery is black without visible
ground or buildings; the in-world avatar is a dark silhouette. Missing Atlas
geometry is consistent with this result, but sole cause is not proved. This is
creation/connection/save qualification, not rendered Atlas or playable gameplay.
The [one-session Thor instructions](ANDROID_CHARACTER_CREATION_TEST.md) are now
historical reference: their creation/save session is accepted above.

The user confirmed local login and supplied `coh-local-login-20261001-010523.zip`.
Independent review matched the 0.8.1 APK and runtime identities, verified all
14 Android PNG and four guest image records, and reviewed the empty 0/12
character-selection screen. Three post-login Android captures, 272 successful
inputs, preserved database/profile/assets/caches and clean owned cleanup are
recorded in the [acceptance receipt](android-evidence/local-login-thor-20261001.json).
The session ended at its 180-second interaction limit. No repeat is requested.

The accepted creation candidate retains package `io.github.russianranger.cohclientinteractive`,
the accepted signing key and profile `android-local-login`. It adds the accepted
Atlas MapServer package because actual character data is sent during the map
handoff. The new target is graphical creation of **THORHERO**, a first connection
to map 1, ordinary logout and read-only verification of committed character,
power and costume records. The interaction window is 1,200 seconds. No existing
character is deleted or synthesized in SQL. A preexisting THORHERO stops this
creation-only candidate while preserving its data.

Thor 0.9.0 creation/save qualification is accepted by the device review above.
Exact-character reopen, Atlas scenery/collision asset closure, gameplay controls
and performance remain pending. Initial map entry completes creation/save; it
does not establish sustained gameplay or hardware acceleration. The following
0.9.0 attempt notes preserve historical checkpoints.

The first 0.9.0 [hosted attempt](android-evidence/character-hosted-36801130531-failed.json)
failed before client launch: Wine could not enumerate directory links in the
new server data tree. The correction uses real directories and the accepted
client's individual immutable file-link pattern. It also waits for the real
client's world-ready record and binds the completed logout command delivery to
fresh logout-timer and SQL evidence; the unmodified server does not log the
individual logout packet. Keep the failed candidate's receipt and clean cleanup
result. No device test of that APK is requested.

The second 0.9.0 [hosted attempt](android-evidence/character-hosted-36802634099-failed.json),
run 36802634099 at source `ae8054d6430c194e32344f47678e134395419046`,
started Atlas, verified local login and reached the creator's Register page for
THORHERO. Host OCR timed out after 20 seconds on the actual tutorial Yes/No
prompt. No character creation, character map entry or committed save is accepted.
PostgreSQL stopped gracefully, but the host killed PRoot before a final guest
report was exported, so full cleanup is unverified. The male avatar preview was
absent, with missing geometry and texture errors: base avatar geometry/textures
are outside the accepted import. Avatar assets remain separate work before
costume rendering or gameplay claims; this candidate keeps the existing assets
and targets registration, Atlas environment loading and ordinary logout/save.
No extra import or device test is requested for this failed candidate.

The subsequent [protocol-flow attempt](android-evidence/character-hosted-36805992804-failed.json),
run 36805992804 at source `335688677eb1fe67e31089b35b3f685bebaf04f6`,
started Atlas and verified login, declined the tutorial and selected Hero.
Its final frame shows the creation confirmation with the pointer covering Yes;
host OCR reported `Rendered Yes button not found`. The guest also failed its
inherited 2 MiB server-log bound during observation and evidence collection.
No character map connection or committed save was proved. This time the guest
report was retained and confirms graceful PostgreSQL shutdown, stopped Wine,
zero remaining owned workers or inspection failures, and preserved database;
the host needed no forced quit or kill. Keep this failed result separate from
qualification of the later avatar-supplement candidate.

The next retry parks the pointer outside each dialog before OCR and waits for a
fresh settled frame. Character mode now retains complete bounded server logs in
one archive with per-file hashes and redaction metadata; final cleanup replaces
live snapshots with closed logs. Its support-evidence budget is 256 MiB with a
260 MiB ZIP guard, while login-only defaults remain unchanged. Local validation
passed 168 interactive tests, 26 client/cache tests and the full Java compile.
Hosted creation, save and avatar rendering still require a passing runtime run.

The [13-file avatar attempt](android-evidence/character-hosted-36807202335-failed.json)
at source `80e776f30de896605b6db4101baa5ab16957a29a` hit the same confirmation
OCR and log-export failures, with full graceful cleanup. All 13 supplement files
installed correctly, but screenshots show a head and fragmented white torso,
without a complete body. Source review explains why: entering the costume screen
applies a random preset. This run selected Military, whose parts were absent.
The normal **Clear** control resets to deterministic tights, smooth gloves/boots
and Martial Arts hair, without a confirmation or another random choice. The next
candidate adds that explicit test step and its seven missing asset dependencies;
partial installation or a partial preview is not a visual qualification.

That candidate contained a pinned 20-file supplement for the Male body
and the costume selected by **Clear**. A bounded source audit recovered only
the missing entries from the original project's PIGG donors;
[entry integrity and format checks](android-evidence/character-avatar-source-review-20261001.json)
passed. The 1,722,790-byte ZIP adds 2,737,564 bytes to the private client worktree,
preserving the imported archive, client prerequisites, cache identity and saved
profile. Installation rechecks all files on reuse and refuses conflicting files
or links. The 13-to-20-file upgrade also preserves the original files' inodes,
bytes, modes and timestamps. Male rendering after reset and character saving still require hosted
qualification; other bodies and costume choices remain outside this small
supplement. The next Thor instructions explicitly use **Male → Costume → Clear**.

The [confirmation retry](android-evidence/character-hosted-36809680532-failed.json)
at source `b17457ec83aa705b1c265f8d511da08b5823c382` passed all three dialog OCR
steps and delivered the final Yes. DbServer then reported THORHERO assigned to
map 1, loaded and connected. The guest stopped during world loading because the
client changed its window title to include the map path; the inherited check
accepted only the menu title. The same owned client and display were still
running. No CLIENT_READY, rendered Atlas environment or ordinary logout/save is
accepted. Full bounded server logs were retained, PostgreSQL stopped gracefully,
and zero owned workers or inspection failures remained. The next candidate
recognizes the source's two PID-bound title forms and preserves rejection of
unrelated windows, while retaining the existing renderer and startup checks.

The [owned-window retry](android-evidence/character-hosted-36846149988-failed.json)
at source `e00f04970fa438864c08c339e5f6c65515b7ecdc` kept the map-title window
observed and delivered the same creation steps. Clear rendered textured tights,
boots and head/hair, but the forearms and hands were absent. The native launcher
then returned 67 at its inherited 1,200-second deadline from launch; the guest's
1,200-second interaction window starts after client readiness, reached at
419.223 seconds. This cutoff is not evidence that the game process crashed.
The last console stage was `AutoGroup..` during map loading. No CLIENT_READY,
rendered Atlas or ordinary logout/save is accepted. Guest cleanup completed
without forced host termination, remaining owned workers or inspection failures.
The next correction gives only character mode a 2,160-second launcher bound
(900 startup + 1,200 interaction + 60 completion grace), and adds the missing
smooth glove geometry using its source-pinned donor entry.

The corrected supplement contains 21 files in a 1,842,488-byte ZIP, adding
2,980,122 bytes to the private worktree. Its only new file is
`data/player_library/male_glove.geo`, containing the two Smooth forearm/hand
models used by Clear; the matching glove texture was already included.
The source entry MD5 and decoded GEO model names were checked, and all original
20 file bytes and provenance records remain unchanged. Installation tests cover
both 13-to-21 and 20-to-21 upgrades without replacing accepted files or changing
the import, worktree identity or caches. Visual completeness and the full
creation/save milestone still require the corrected hosted run.
The combined correction passed all 173 interactive and 27 client/cache tests.
Independent review checked the exact glove model names, previous file pins and
provenance, strict launcher modes and the production deadline regression.

Source review also found an existing native MapServer option for the costly
`AutoGroup..` stage: **`-donotautogroup`**. Production servers already default to
this setting; the development server used by character mode does not. The stock
world packet sends the setting to the client before map loading, so both sides
use the same load policy. The next candidate requests this option only for its
owned Atlas launch and records the policy in its report. Normal map parsing,
tracker activation, welding, collision setup, CLIENT_READY and ordinary
logout/committed-save gates remain. No binaries or imported assets are rebuilt
for this change. The development client also sets `iAmAnArtist` under this stock
policy; do not claim identical internal group topology or physical visual and
collision acceptance before runtime review. See the
[source review](android-evidence/character-atlas-autogroup-policy-source-review-20261001.json).
The [full-budget retry](android-evidence/character-hosted-36852214162-failed.json)
at `cdff43b4` exhausted its full twenty-minute interaction window while the client
remained at `AutoGroup..`. Both forearms and hands visibly rendered after Clear,
alongside the tights, boots and hair. The owned client was still alive; its
1,641.351-second launcher lifetime was below the new 2,160-second bound.
No CLIENT_READY or requested ordinary logout/save was obtained. A later server
logout-timer expiry followed no logout input and is consistent with the normal
connection timeout, so it is not accepted save evidence. Guest cleanup completed
with no remaining owned workers, inspection failures or forced host termination.
The production-policy candidate at `19879ed5`,
[run 36855035567](android-evidence/character-hosted-36855035567-failed.json),
failed before login because the external host driver opened Settings and never
dismissed its overlay. The tiny red-X click failed visibly before Escape was
sent; fresh frames continued but never matched the restored login panel. No
credentials were entered, creator opened or Atlas client policy exercised.
Its full interaction-bound failure therefore does not establish that the Atlas
policy failed. Cleanup again completed without remaining workers, inspection
failures or forced host termination.

The signed APK is already built and
[independently verified](android-evidence/character-package-review-36855035567.json):
386,658,292 bytes, SHA-256
`1da4719cf7af825092199c73067fb5fd3423fcaa8543a37d366ad1a0557ed681`.
The next qualification uses that immutable APK. The corrected character-only
host driver omits the previously accepted optional Settings probe, preserves
ordinary login actions, and requires the current login event plus three fresh
post-event captures within 180 seconds. The login-only driver remains unchanged.
Full map-ready, ordinary logout and committed-save acceptance remain pending.
The dedicated `android-character-qualification.yml` workflow checks the exact
donor run, successful APK job and artifact digest before reusing the APK and
its build receipt. It records the current external-driver commit separately
from APK source `19879ed5`; packaged Java/native/guest source closure remains
checked, and neither the APK nor prepared caches are rebuilt. This host-only
correction passed all 181 interactive and 27 client/cache tests, including
failed/forged donor rejection and login event/fresh-frame/deadline regressions.
All 174 interactive tests passed after the policy change, including an integrated
Atlas startup regression that rejects tick zero and NotReady, and requires
advancing completed ticks around the successful current-map protocol query.

The [immutable retry](android-evidence/character-hosted-36862027663-failed.json)
at driver `bc4d750d` reached an empty character list using **OHLOCAL**: the host
lost the initial C during typing. Exact COHLOCAL identity proof correctly failed
at the new 180-second login bound. No character or Atlas client policy was tested
in that retry. Its already-verified source-19879ed5 APK remains unchanged.
The parallel normal run at the same driver did enter COHLOCAL and passed the
full flow; its reviewed APK and scope are the current result above.

The subsequent host-only typing correction separates focus and Ctrl-release
from text by fresh frames, uses longer key settles and requires the entire
rendered account field to read COHLOCAL before submitting login. Replacements
are bounded to three attempts within the existing login deadline. All 186
interactive tests passed; the 27 client/cache checks remain unchanged and passed.
Actual OCR rejects the failed OHLOCAL frame and accepts a correct COHLOCAL frame.
This correction changes no packaged APK payload. It is a future host-driver
improvement, not the tested `bc4d750d` driver: the historical passed report lacks
the newer OCR receipt fields and must remain bound to its original validator.

**Historical hosted 0.8.1 qualification — the following device instruction is superseded by the accepted report above.**

**0.8.1 passed the hosted saved-Wine-profile refresh regression and graphical local login. It is ready for one Thor login session as an in-place update.**

Qualified source `1fb4c6057fda579da1913670889922ba8e53bbdc`,
[run 36785793934](https://github.com/Russianranger/coh-android/actions/runs/36785793934),
passed all 11 guest stages. The test first created a genuinely ready Wine profile
using the exact APK and real PE32 probe, stopped it cleanly, then made only its
stored registration timestamp stale. The login run performed exactly one real
registration pass (3/1/1) in 38.481 seconds, retained the prefix inode and sentinel,
matched the new timestamp, and renewed readiness after the real PE32 probe.
The seed's retained raw timestamp bytes confirm CRLF (`0d0a`) line endings.

Root screenshot review confirms **Server Used/Total: 0/12** with twelve empty
Create Character slots. Local authentication, the sent character list and SQL
account identity agree. Client startup took 439.248 seconds, followed by 48.585
seconds of observation. All 63 login-run child records closed with zero remaining
owned workers or inspection failures; PostgreSQL stopped gracefully and retained
its database. The separate prefix seed also cleaned up successfully.

The qualified `COH-Local-Login-0.8.1.apk` is 373,849,564 bytes, SHA-256
`2f9663f43c24b071714a7ea2f63a2f8abd624a49bca4b64298f58c7e56278a20`.
It retains the installed app identity and signing certificate, increments version
code to 3, and preserves the imported assets, client caches and Wine state.
All 86 interactive and 26 client/cache automated checks passed. See the
[hosted review](android-evidence/local-login-hosted-36785793934.json),
[package review](android-evidence/local-login-package-review-36785793934.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).
Physical Thor local login remains pending; no new Atlas, Settings, general input,
character creation, or restart/reopen device test is requested in this pass.

**Historical Thor 0.8.0 failure: Wine profile refresh was rejected before DbServer or the game launched. No repeat of 0.8.0 is requested.**

The supplied `coh-local-login-20260930-220534.zip` records a 76.956-second
operation. Imported assets and the generated client caches were successfully
reused through the wrapper-only migration. PostgreSQL initialized its persistent
profile and started successfully. Wine then exited initialization with code 0,
recording one complete registration pass (three registration processes, one
WoW64 process), but the reused-prefix validator expected no registration and
reported `Wine initialization registration evidence differs`. No client inputs
were sent. All 21 child records closed; PostgreSQL stopped gracefully, its
database remained intact, and no owned workers or inspection failures remained.
See the [device failure receipt](android-evidence/local-login-thor-review-20260930.json).

Source review explains the upgrade-specific mismatch: the Android extractor
recreates Wine files with extraction-time modification dates on a new runtime
generation. Wine compares the installed `wine.inf` modification time with the
decimal value inside the preserved prefix's `.update-timestamp`. Our marker
only compared the unchanged runtime archive identity. The device report did
not contain those timestamp values, so the timestamp mismatch is a source-based
explanation; the complete unexpected registration pass is directly recorded.
The correction reconciles this metadata before calling the existing strict
initializer, preserves the prefix, and requires the real PE32 runtime probe before
writing readiness. The hosted stale-timestamp regression seeds a real prefix
using the exact APK's Wine and PE32 probe, proves cleanup, changes only the
stored timestamp, and requires a real registration refresh before graphical
login. Prefix inode/sentinel and Wine input hashes must survive. This regression
passed in corrected run 36785793934, as recorded above.

The first corrective hosted run
[36784616495](https://github.com/Russianranger/coh-android/actions/runs/36784616495)
successfully seeded a real Wine profile and performed the required saved-profile
refresh. It then failed because the new timestamp reader accepted only LF line
endings. Pinned Wine writes this file through CRT text mode, which uses CRLF.
Corrected source `1fb4c6057fda579da1913670889922ba8e53bbdc` accepts complete decimal
timestamps ending in LF or CRLF, retains all registration/probe checks, and adds
raw timestamp-format evidence to the hosted seed receipt. Keep the
[failed hosted receipt](android-evidence/local-login-hosted-36784616495.json);
that candidate was not delivered for a device test. All 86 interactive and 26
client/cache automated tests pass; corrected hosted run 36785793934 passed.

**Historical 0.8.0 fresh-profile hosted qualification passed; the Thor result above supersedes its device-test recommendation.**

Accepted source `a80bc9c9df684779987dd6d1c146c66960db9458`, run
[36779011148](https://github.com/Russianranger/coh-android/actions/runs/36779011148),
passed all 11 guest stages and independent package review. Root visual review of
fresh post-response screenshots confirms **Server Used/Total: 0/12** and twelve
empty Create Character slots. The owned local DbServer authenticated `COHLOCAL`,
sent the character list, and matched SQL account ID `1353310574` with zero
characters. The graphical client became ready in 441.389 seconds; total hosted
execution took 671.270 seconds. Finish completed after 49.235 seconds of live
observation. All 63 child records closed, PostgreSQL stopped gracefully, the
database was retained, and no owned workers or inspection failures remained.
The same run also recovered the login screen after Settings X/Escape.

The accepted `COH-Local-Login-0.8.0.apk` is 373,845,468 bytes, SHA-256
`76723c1b2f52d351f48d3b46a15625414c3977fdb8230965d83ec939d2af88fd`.
It retains app ID `io.github.russianranger.cohclientinteractive` and the 0.7.0
signing key, increments version code to 2, and preserves imported assets, Wine
state and compatible prepared/generated caches. All 77 interactive and 26
client/cache automated checks passed. See the [hosted receipt](android-evidence/local-login-hosted-36779011148.json),
[package review](android-evidence/local-login-package-review-36779011148.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).

The scope is hosted graphical local login and an empty character list. Android
local login, account reopening after restart, character creation and world entry
are not yet accepted. This hosted run initialized a fresh persistent profile;
retaining its database at cleanup does not prove a subsequent reopen. Raw
automation reports intentionally leave visual-validation flags false; the
separate review receipt records the screenshot assessment.

Sequential targets:
1. Confirm this APK's local login and clean Finish on Thor in one session.
2. Create and save one graphical character against the persistent profile.
3. Restart and reopen that exact saved character, proving durable persistence.
4. Enter a local map with MapServer and verify initial world interaction.
5. Refine gameplay controls, performance, audio and hardware acceleration.

The first hosted attempt below remains a failed historical result.

Candidate source `8d8ebd35396e193f426df686167c87e3d2eeee7a`, run
[36775940197](https://github.com/Russianranger/coh-android/actions/runs/36775940197),
passed signed packaging and independent package review. PostgreSQL and the pinned
loopback DbServer started, and the graphical client reached its login screen in
438.599 seconds. Root screenshot review confirmed Settings X/Escape recovery,
`COHLOCAL`, masked password entry and the single `127.0.0.1` shard. The client
then displayed **Wrong game version** and the bounded interaction timed out.
All 67 owned child records closed; PostgreSQL stopped gracefully, its profile
was retained, and no owned workers or inspection failures remained. Preserve
that failed result: see the [runtime review](android-evidence/local-login-hosted-36775940197.json)
and [package review](android-evidence/local-login-package-review-36775940197.json).

Pinned source explains the malformed development version strings: its getter
expects `Ouroboros.exe`, ignores the failed timestamp lookup in these differently
named executable layouts, then formats uninitialized date fields. The accepted
headless TestClient already requests the supported development version exception.
The correction adds `--local-login` to the native launcher, which alone appends
`-noversioncheck 1`; ordinary startup and cache generation are unchanged. The
separate DbServer wire-protocol check and exact source/executable/data pins remain
enforced. Corrected run 36779011148 passed as recorded above.

The update keeps the installed app identity/signature, imported assets, Wine
prefix and compatible prepared/generated caches. The new persistent
`android-local-login` profile starts PostgreSQL/DbServer with no MapServer. Login
acceptance requires current owned-server authentication and a sent character-list
response, matching SQL account identity and fresh captures; actual empty-character
selection requires visual review. The [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md)
now identify the accepted APK receipt/hash. Do not repeat earlier
startup, menu input, Atlas, or synthetic display device tests.

**Physical Thor startup and basic menu input are accepted within their reviewed scope. The 0.7.0 device session failed its final-frame check during a graphics reload; cleanup passed.**

The supplied `coh-client-interaction-20260930-201926.zip` records 174 input
events with zero transport failures. The user confirmed touch and right-stick
pointer movement, A as left click, and text entry; retained Android captures
show `COHINPUT` in Account Name with Settings open. All 40 owned child records
closed, with zero remaining owned workers or inspection failures. Preserve
the original failed result: Finish captured an all-black guest desktop after
58.427 seconds of observation, reporting `Observed client desktop became blank`.
See the [device interaction review](android-evidence/client-interaction-thor-review-20260930.json).

The last Android capture shows loading artwork. The console continues through
shader compilation. Source review shows that the Settings red X invokes the
settings-close path, which reapplies graphics settings and can show loading
artwork while rebuilding rendering resources. This supports a graphics-reload
explanation; it does not prove eventual recovery or that B caused the blackout.
B maps to Escape; its separate visible effect remains unverified. Do not call
the complete session passed or suppress the blank-frame acceptance check.

No repeat device menu test is requested. Carry the confirmed input results
forward. The source correction now adds bounded final-frame settling within the existing
interaction deadline, retaining blank samples and checking the exact client
window/process, display and complete console evidence. Fresh nonblank output
is required before acceptance; permanent blank output, client exit, window loss
and deadline expiry still fail. At most three raw blank images are retained to
preserve the existing support archive limit. All 53 interactive automated tests
passed after this correction, including transient blank recovery, permanent
blank output, deadline, process/window loss and truncated console cases.
Hosted run 36775940197 now demonstrates the Settings-close/Escape sequence
returning to the login screen; corrected run 36779011148 also passed local-login
qualification. Install 0.8.0 over 0.7.0 and retain its imported/runtime state.

The supplied `coh-game-client-test-20260930-141120.zip` passed the exact shipped
Java cleanup and PixelCopy acceptance checks. Its pinned actual client reached
renderer, all-data completion, main loop and the exact-PID window. All three
Android screenshots show the Freedom login screen and first-launch graphics
prompt; they span 2.037 seconds after current-session readiness. The client
remained observable for 34.810 seconds, and all 38 child records closed with
zero remaining owned processes and zero inspection failures. Renderer startup
at about 5m56s explains the user's reported first visible boot; full readiness
was 10m20s after client launch and the entire first operation took 16m24s,
including private-data preparation and Wine initialization. See the
[physical client receipt](android-evidence/accepted-client-startup-thor-20260930.json).
No repeat startup, Atlas, synthetic presentation, Stop/rerun or screen-lock
acceptance test is requested.


The corrected interactive APK from source
`fdd0acc492485455ce0fc8b43eb4b406da529ba1`, run
[`36736910061`](https://github.com/Russianranger/coh-android/actions/runs/36736910061),
passed all seven guest stages and independent package/session checks. Root visual
review confirmed that Cancel dismissed the graphics prompt, `COHINPUT` appeared
in Account Name, and Settings opened. Startup took 362.627 seconds, followed by
33.543 seconds of live observation; all 27 child records closed, with zero
remaining processes or inspection failures. The APK is 370,560,140 bytes,
SHA-256 `8ada2e23cf8cf4986b4faacdff1839233ef6538cf4eb12602d2e11d1cb3d36ca`.
All 44 automated checks passed. See the
[hosted interaction receipt](android-evidence/client-interaction-hosted-36736910061.json),
[package review](android-evidence/client-interaction-package-review-36736910061.json)
and [one-session device instructions](ANDROID_CLIENT_INTERACTION_TEST.md).
The later physical review above accepts the user-confirmed basic menu inputs;
input counts alone do not establish a visible game response.

The **COH Client Interaction 0.7.0** milestone adds touch, text and basic
Thor controller menu input, then Finish and verified cleanup in one session.
It starts no server. The old 0.6.0 development signing key was not retained,
so its installed package cannot be updated while preserving private state.
The new package `io.github.russianranger.cohclientinteractive` installs beside
it and requires its own one-time runtime setup and asset import. The new
development signing identity is retained, backed up and pinned to certificate
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`;
future builds fail rather than silently generate another certificate.
The accepted old apps stay installed. Login, world entry, audio, hardware
acceleration, B/Escape behavior and recovery after a settings reload remain
separate unproven outcomes.


The first interactive hosted candidate, run `36732627939`, passed startup,
observation, Finish and cleanup, but failed visual input qualification: Settings
opened while the graphics prompt remained and `COHINPUT` was absent. That APK
was not delivered. Source review found that Cancel and account focus use stored
button-down coordinates, while Settings uses the current cursor position. CoH
polls the absolute pointer at the end of its input frame, so a combined pointer
warp and press can leave stored click coordinates stale. The correction sends
neutral pointer movement before a bounded settling interval and button-down;
the hosted check also waits for fresh frames before clicks and text entry.
No game binary, accepted startup gate or window-focus behavior is changed.


With basic physical menu input now accepted, the next smallest gate is graphical
loopback login to an empty character-selection screen using PostgreSQL/DbServer;
MapServer and world entry can follow later. Update the retained-signature 0.7
package so its imported generation, Wine prefix and prepared caches survive.
Start the server pair once for that client session and initialize a persistent
server profile once. The accepted Atlas diagnostic dropped its database and
deleted its run tree during cleanup; it preserved import data and evidence, not
a resumable `TEST50056` character. Reuse the accepted implementation and receipts,
not a nonexistent live database or another app's private files. Verify the actual
client protocol and local `-db` authentication path in a hosted session before
requesting this later device gate.


**Historical hosted qualification for the accepted 0.6.0 build follows.**

Exact APK source `5e4e8f2f0acc78e397a3ee8c1eb7df6f661953cb`, run
[`36719533060`](https://github.com/Russianranger/coh-android/actions/runs/36719533060),
passed all six guest stages. Startup reached the renderer, all-data completion,
main loop and exact-PID 800×600 window in 362.742 seconds, then remained live
for 33.433 seconds. Three fresh external frames span 2.566 seconds after
readiness, and final cleanup left zero owned processes or inspection failures.
Root visual review sees the Freedom login screen with its first-launch
Quality/Ultra graphics prompt. Interaction remains untested; leave that prompt
untouched for the physical run. The full 39,463,670-byte console is retained.
The exact APK is 370,539,567 bytes, SHA-256
`ca506e5c22369de04d80cb98b6a747bd818ef20c81245806b6d7271357f3377d`.
See the [hosted qualification receipt](android-evidence/client-startup-hosted-36719533060.json)
and [one-run device instructions](ANDROID_CLIENT_DEVICE_TEST.md). Hosted evidence
does not establish Android execution, PixelCopy, input, world entry, hardware
acceleration or playable performance for this actual-client build.

**Physical Thor presentation 0.5.0 passed and remains accepted.**
The supplied `coh-client-test-20260930-094646.zip` verifies all 120 current-session
PixelCopy frames over 62.758 seconds. The full operation took 128.592 seconds;
all five guest stages and six child records passed, and cleanup left zero
owned processes or inspection failures. Exact shipped Java acceptance and
runtime identities were independently replayed. See the [physical presentation
receipt](android-evidence/accepted-presentation-thor-20260930.json).

The separate **COH Game Client Test 0.6.0** packages the pinned actual
`CityOfHeroes.exe` and matching DLLs. Reuse the reviewed asset ZIP for one
private import, then attempt visible game loading/login without a server boot.
The one-run instructions are in [the client device test](ANDROID_CLIENT_DEVICE_TEST.md).
Earlier hosted attempts below are historical; their proposed next actions are
superseded by the exact-APK qualification above.

The initial actual-client hosted attempt [36700734062](https://github.com/Russianranger/coh-android/actions/runs/36700734062)
displayed the Freedom loading artwork but timed out before `game_mainLoop`;
cleanup was complete. Do not deliver that APK as qualified. Its later console
output was redirected away from the inherited pipe. See the
[first failed startup receipt](android-evidence/client-startup-hosted-36700734062.json).
The next diagnostic [36704251918](https://github.com/Russianranger/coh-android/actions/runs/36704251918)
confirmed owned-console capture and a correctly fitted 800×600 loading screen.
Renderer, texture headers, fonts, group libraries and LOD data completed; the
300-second diagnostic deadline expired during sequencer text parsing. Nine
private caches were generated and cleanup was complete. This establishes cold
data processing, not a rendering deadlock or complete startup. The next work
is to prepare compatible client caches off-device and qualify a normal startup.
See the [second failed startup receipt](android-evidence/client-startup-hosted-36704251918.json).
Native x86 cache generation then finished in 221 seconds with the game completion
marker, but correctly failed its output checks because three badge/pophelp
attributes were absent. The next candidate includes those exact accepted lookup
files for both cache generation and normal startup. See the
[cache generation receipt](android-evidence/client-cache-generation-36706745544.json).
The corrected candidate `a40250b0032bd05a333514920722ddffa4427730` produced
100 verified caches and a verified 0.6.0 APK in run `36707839624`. Its short
300-second hosted diagnostic consumed those caches without rebuilding them and
continued through powers, NPCs and items to FX loading when the diagnostic
deadline expired. Cleanup was complete. The next qualification uses this exact
APK and its existing normal 900-second startup budget, with all readiness,
observation and cleanup checks unchanged; do not rebuild or repeat phone tests.
See the [cached diagnostic receipt](android-evidence/client-startup-hosted-36707839624.json).
The full-budget run `36710174172` advanced through FX, villains, cape FX and
body parts, then hit the diagnostic 1 MiB console limit during NPC costume
missing-texture warnings. It did not exhaust the startup deadline, and cleanup
was complete. The next wrapper increases bounded observation capacity, preserves
all failure/readiness checks, and reuses the exact verified caches. See the
[observation-budget receipt](android-evidence/client-startup-hosted-36710174172.json).
Run `36711916066` then retained the complete 5.79 MB console capture but reached
the 900-second startup limit just after mission-maker data, at the start of
player geometry preload. NPC and costume checks consumed about 514 seconds;
the main loop was not reached and cleanup was complete. See the
[full-budget receipt](android-evidence/client-startup-hosted-36711916066.json).
The next wrapper reduces repeated parsing of the same diagnostic log and uses
the client's native-diagnostic-UI mode to preserve direct pipe logging. This
changes native prompts and the small initial splash, while retaining actual
game window creation, graphics, data loading and texture validation. It needs
fresh hosted qualification; no phone rerun is requested for failed candidates.
See the [console profile review](android-evidence/client-console-profile-20260930.md).
The profile worked in `36716064689`: the child attached to the real parent
console and preserved direct logging. The full warning stream exceeded the
10 MiB guest limit during NPC validation, about 321 seconds into startup;
the deadline was not reached and cleanup was complete. NPC warnings alone
are estimated to exceed 20 MiB. The hosted Raw-only RFB viewer also disconnected
on a desktop-size change; Android's existing viewer already handles that event.
The next candidate retains up to 128 MiB of complete raw output, streams the
bounded support archive into the Android export, and fixes the hosted viewer's
resize and post-readiness frame checks. It keeps the same startup deadline,
full data validation, and exact game/cache inputs. See the
[direct-output receipt](android-evidence/client-startup-hosted-36716064689.json).
Physical synthetic presentation is closed; do not request another pattern,
Atlas, Stop/rerun or screen-lock test. Actual client, menu, input, hardware
acceleration and gameplay claims remain separate.

**COH Atlas Test 0.4.4 also passed on the physical AYN Thor.**
The supplied `coh-atlas-test-20260930-003609.zip` verifies all 18 stages in
55 minutes 52.7 seconds: both protocol saves committed, `TEST50056` resumed in
the same cluster with 12,345 influence and login count 1 → 2, and all 102 child
captures closed. Restart and final owned cleanup had zero inspection failures
and zero remaining processes. The device exercised the EACCES exit recovery;
the separate ESRCH path was not exercised. The exact original report also passes
the Java acceptance/cleanup checks and Python capture/startup checks.
See the [physical acceptance receipt](android-evidence/accepted-atlas-test-thor-20260930.json).

The user explicitly asked to advance without manual Stop/rerun or another long
server boot. Manual Stop/rerun and screen-lock checks remain **skipped at user
request, unvalidated** for 0.4.4; they are not prerequisites for the next APK.
The 177 ms activity visibility gap does not prove sustained background operation.
Do not request another full Atlas test to close those checks.

Keep the accepted Atlas app and its private runtime installed. The separate
**COH Client Test 0.5.0** implements the next [presentation gate](NEXT_ANDROID_PRESENTATION_GATE.md):
a session-bound animated Wine/OpenGL fixture, app-private Unix RFB, an Android
SurfaceView, and actual PixelCopy frame verification. It starts no game server
or SQL service and imports no game data. The exact signed APK passed hosted qualification in
[run 36654262400](https://github.com/Russianranger/coh-android/actions/runs/36654262400):
the external private RFB viewer observed all 120 frames in 109.26 seconds, and
all six children and the socket cleaned up. The APK itself is from build
`36653423058`, source `6fdeef4494dd41f6137ee51d80ec4e39cf687b01`; only the
host viewer changed for qualification. See the [receipt](android-evidence/accepted-presentation-hosted-36654262400.json).

That physical [display test and export](ANDROID_PRESENTATION_DEVICE_TEST.md) has now passed,
as recorded above. Its installation instructions are retained as historical evidence.
A visible fixture does not establish actual CoH menus, world rendering, controls
or gameplay. Preserve the separate APK and do not repeat the accepted server test.

The 0.4.4 exact signed APK remains hosted-qualified in
[run 36638344040](https://github.com/Russianranger/coh-android/actions/runs/36638344040)
at `e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce`.
See the [hosted receipt](android-evidence/accepted-atlas-test-hosted-36638344040.json).

The earlier checkpoints below preserve their original successes and failures.
Their installation and retry directions are superseded by the physical pass and next-step direction above.

**Qualified MapServer diagnostic donor: run 36630872719.**
Run `36630872719` passed all six real Windows producer contracts and all eighteen
ARM64 game stages in 31 minutes 23.5 seconds. Independent review verified both
committed saves, exact-name resume, 122 closed children and zero ownership
inspection failures at restart and final cleanup. Raw records show 8,226 completed
ticks on the first launch and 2,425 on restart, with distinct file identities.
Only the separately identified MapServer changed; accepted supporting binaries
and their original source identities remain exact.

The successful run also captured a 114.233-second interval inside the first
`FolderCacheDoCallbacks` call, with one tick started and none completed. Existing
freshness checks rejected protocol-ready samples aged 23 and 85 seconds. This
does not prove the cause of earlier uninstrumented failures or repair the folder
work. The qualified 0.4.4 profile additionally requires a freshly validated
completed tick and the two-phase startup guard described above, preserving
startup deadlines, 20-second freshness and 30-second observation.

0.4.4 carries these diagnostics from donor commit
`003b07bcd98cb100c1505c15670c07d11a240c8f`, separately from its Android
wrapper and guest-adapter commit. Only the instrumented MapServer is replaced;
accepted supporting binaries and their original source identities remain exact.
See the [hosted diagnostic qualification](android-evidence/accepted-mapserver-progress-hosted-36630872719.json).

**0.4.3 remains unqualified after two hosted Atlas heartbeat failures.**
All 113 candidate checks and exact APK verification passed. Both runtime attempts
of the same signed APK in run `36621227369` passed nine stages, then failed
`Atlas lost current readiness during observation`, before character creation or
restart. DbServer kept dispatching and both services were alive at capture.
Both final cleanups completed with zero ownership inspection failures and zero
remaining owned processes. Neither attempt exercised the targeted restart race.

Identical 0.4.3 retries are stopped. The separately receipted MapServer diagnostic
above now exposes fresh late-startup and main-loop stages while preserving all
readiness, listener and cleanup checks. Buffered stdout and saved thread contexts
from these failures do not prove the blocked operation. Do not install 0.4.3 as
a qualified candidate. The 0.4.4 hosted pass does not establish the root cause or
repair of either earlier uninstrumented failure.
See the [attempt 1 review](android-evidence/atlas-test-review-36621227369-attempt1-failed.json),
[attempt 2 review](android-evidence/atlas-test-review-36621227369-attempt2-failed.json),
and [observer design](android-evidence/atlas-test-heartbeat-observer-plan-20260929.md).

**Thor 0.4.2 follow-up (2026-09-29, 18:57 UTC): cleanup is blocked again.**
The first 13 stages passed, including Atlas live-heartbeat observation and the
committed save of `TEST24402` with 12,345 influence. `game_restart` failed with
`Cannot verify Wine descendant ownership` after Wine stop/wait both returned 0.
Final cleanup subsequently found zero remaining owned processes and closed all
84 child records, but one earlier inspection failure remained latched. The app
correctly refused reuse. This run did not reach PostgreSQL restart, the new
restart startup budget or exact-name resume. No Stop or cancellation was recorded.

The report has zero permission-read retries and no permission observations. Its
message comes from the generic OS/parse-error path and omits the underlying
exception, errno and process identity. A reproduced proc-file exit race is a
candidate mechanism, not a proved explanation of this particular device run.
The narrow correction introduced in 0.4.3 and retained in 0.4.4 handles
ESRCH from status/stat as task disappearance.
Environment/namespace ESRCH requires a fresh exact-identity check and preserves
inspection of live workers behind a stopped leader. Live unreadable ownership
still fails; retries and diagnostic records are bounded. The original operation,
exception type, errno and process/thread IDs are retained without raw contents.
See the [owned-child reproduction](android-evidence/atlas-test-proc-exit-reproduction-20260929.json).
The accepted base runtime, identity/token signaling checks and Java cleanup
gates remain intact. Do not repeat 0.4.2. The current 0.4.4 procedure supersedes
that failed app's recovery and retry sequence: one full Thor test/export first,
with Stop/rerun and lifecycle checks held until report review.
See the [device failure review](android-evidence/atlas-test-thor-cleanup-failure-20260929-185717.json).

**Previous hosted checkpoint: COH Atlas Test 0.4.2 passed on attempt 2.**
The exact signed APK completed import and all 18 create/save/restart/resume stages
in 32 minutes 11 seconds, with both committed saves and complete owned cleanup.
All 100 candidate checks passed. That checkpoint qualified the bounded
DbServer startup correction; the subsequent failed Thor run is preserved above.
Attempt 1's separate Atlas heartbeat failure remains preserved. The unchanged
repeat passed, but does not establish a repair or root cause for that failure.
See [run 36599606621, attempt 2](https://github.com/Russianranger/coh-android/actions/runs/36599606621/attempts/2)
and the [acceptance receipt](android-evidence/accepted-atlas-test-hosted-36599606621.json).
That 0.4.2 candidate code was `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`.
Its installation instructions are superseded by the current 0.4.4 procedure;
the acceptance and subsequent device failure remain separate historical records.

Previous device checkpoint (2026-09-29, 16:32 UTC): **0.4.1 recovered the ownership
read race and passed 15 stages, then hit a separate DbServer startup deadline.**
The first committed save, owned service stop and PostgreSQL restart passed.
Both restart and final cleanup reported zero inspection failures and zero
remaining owned processes. Two denied worker-environment reads ended in verified
disappearance; the app was not cleanup-blocked. The report records a timeout,
not cancellation. Screen off/on events were recorded during the earlier startup,
but the full lifecycle/device milestone remains unaccepted.

At restart the retained 5,935-column schema was ready at 16:31:28; this started
the inherited 30-second dispatch deadline while DbServer was still initializing.
Its normal minimum 15-second launcher wait began at 16:31:50. The deadline fired
at 16:31:58.99, before that wait could finish. Pre-cleanup publication was valid
but still at SQL_KEEPALIVE_QUEUE with loop count zero. The test correctly refused
to call this ready. The 0.4.2 adapter correction uses one shared 600-second startup
budget across schema/listener readiness and positive-loop dispatch, retaining
the existing overall deadline, cancellation, health and readiness predicates.
Accepted base payloads and Java guards remain unchanged. See the
[failure receipt](android-evidence/atlas-test-thor-dispatch-failure-20260929.json).
The 0.4.2 APK built successfully and its 30 payloads and 12 Java source identities
match candidate commit `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`. All 100 candidate
checks passed. Hosted run `36599606621` attempt 1 passed nine stages, then failed
`atlas_ready_observation`: Atlas heartbeat ages reached 29 seconds while DbServer
dispatch continued. The first DbServer startup milestones passed in 42.468 and
57.217 seconds. Final cleanup completed with zero inspection failures and no
remaining owned processes. This is a separate failure, not accepted runtime
qualification. The [failed evidence](android-evidence/atlas-test-evidence-36599606621-attempt1-failed.zip)
and [partial review](android-evidence/atlas-test-review-36599606621-attempt1-failed.json)
are preserved. Atlas publishes readiness before its final startup work, and the
stdout tail can be buffered; these observations do not establish an SG permission
verification defect. The runtime-only retry of the exact same signed APK and
unchanged guards passed as attempt 2, as recorded above. That repeat does not
establish a repair of this separate failure.

The DbServer startup correction remains part of 0.4.4. Follow the current
0.4.4 procedure above for the next physical check; the older 0.4.2 installation
sequence is superseded.

For any repeated Atlas heartbeat failure, preserve the existing 20-second
freshness requirement and 30-second observation. `dbReadyForPlayers` precedes
late initialization; registration sets the initial age timestamps. Later stats
come from `dbComm` inside `svrTick`. Unbounded directory/callback draining later
in that tick is a plausible source of delay, not an established cause. The
[exact-PDB context review](android-evidence/atlas-test-context-review-36599606621-attempt1.json)
identifies folder/path/hash words but explicitly cannot prove current execution.
The separately qualified MapServer donor now supplies bounded, fresh
main-thread stage/tick publication around late startup, `dbComm` and folder
callbacks. The completed-tick guard is integrated in 0.4.4. Callbacks and the
original heartbeat requirements remain intact; earlier root causes remain unknown.

Previous hosted checkpoint (2026-09-29, 14:49 UTC): **COH Atlas Test 0.4.1 passed hosted
qualification** in [run 36579726816](https://github.com/Russianranger/coh-android/actions/runs/36579726816)
at `6b50467a1b96133acc92a378617ff961733f288c`. All 91 candidate checks, 65 import
checks and 142 of 143 existing game checks passed (one Windows-only skip).
The exact signed APK's import and all 18 stages passed in 1,968.534 seconds.
Independent review verified 25 capture files, both committed saves, same-cluster
restart, exact-name resume and all 122 closed process records. Restart and final
cleanup each had zero inspection failures and zero remaining owned processes.
The Java gate compatibility replay also passed while retaining the original
report's hosted identity. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36579726816.json).

The candidate-only scanner correction handles identity-verified worker exit
during ownership reads and bounded full-read retries; persistent live denial
still fails. It adds sanitized failure details without changing accepted base
payloads or Java acceptance guards. Hosted cleanup needed no permission retry;
the later Thor run above exercised that recovery successfully. Its new startup
failure supersedes the old 0.4.1 retry instructions. Keep the accepted
0.1.5/0.2.0/0.3.0 apps installed.
After the first pass is reviewed, complete Stop during active services and a
successful rerun with app switching and screen lock/unlock. Graphical client
work remains later. See the [device procedure](ANDROID_ATLAS_DEVICE_TEST.md).

Thor follow-up (2026-09-29, 13:50 UTC): **0.4.0 reached Atlas Park and committed
the first character save, then failed the restart ownership check.** The first
13 stages passed; `TEST-47452` (container 1) saved influence 12,345. Wine stop and
wait finished, but the process scanner reported `Cannot inspect same-UID Wine
ownership`. Final cleanup subsequently reported zero remaining owned processes
and closed all 86 child records; the cumulative inspection failure correctly
kept the Android guard blocked. The full restart/resume milestone is not accepted.
The failed PID/read is absent from this report; a worker-exit race in the scanner
is consistent with the captured zombie leaders and surviving Wine workers.
The isolated 0.4.1 correction is now hosted-qualified above, retaining strict live
ownership checks and adding bounded failure context. Do not repeat the remaining
device tests on 0.4.0. See the
[failure receipt](android-evidence/atlas-test-thor-restart-failure-20260929.json).
The user confirms following the force-stop instruction at the end, probably
after exporting the report. This was recovery after the recorded failure.

Previous hosted checkpoint (2026-09-29, 12:18 UTC): the separate
[COH Atlas Test 0.4.0 candidate](ANDROID_ATLAS_DEVICE_TEST.md) **passed hosted
qualification** in [run 36563104664](https://github.com/Russianranger/coh-android/actions/runs/36563104664)
at `4a8534b46ec024ca8f97bcbdc689f5fe23746a69`. The exact APK passed full import,
all 18 server stages, two committed saves, same-cluster restart, exact-name
resume and cleanup of all 122 captured process records. Import plus runtime
took 1,947.999 seconds. All 77 new contract tests and existing regression gates
passed (one existing Windows-only test skipped on Linux). The downloaded APK,
payloads and source identities match their receipts; the current report also
passed the scratch JVM validator compatibility check without being relabelled
as device evidence. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36563104664.json).
The next gate at that checkpoint was Thor success/Stop/success with lifecycle
checks. Later failed runs superseded that sequence: follow the current candidate's
full run/export and pause for review, as directed in the current checkpoint above.
The candidate combines content import with the accepted local server/runtime
package and the automatic Atlas Park create/save/restart/resume test. It uses a new
application ID, so its private content must be imported once; accepted 0.3.0 data
cannot be read across Android app sandboxes. The unchanged accepted executable
package is reassembled from run `36510836956`; current wrapper/guest provenance
is recorded separately. The new workflow is `android-atlas-game.yml`.

Latest device checkpoint (2026-09-29, 11:11 UTC): **COH Atlas Setup 0.3.0 passed
physical import/Stop/retry on Thor (Android 13 / SDK 33)**. Both full imports
verified 173,011 files / 2,977,730,517 bytes, taking 56.610 and 61.822 seconds.
The intervening cancelled import stopped during extraction after 4,552 files
and retained the first completed generation. Retry published a new complete
generation. All three raw contracts exactly match hosted-qualified build
`2f828ca3e626245ea9fd60055745980bc3f32001`. Original report ZIPs and their hashes
are preserved in the [device acceptance receipt](android-evidence/accepted-asset-import-thor-20260929.json).
No repeat of import/Stop/retry is required. The reports do not separately record
app switching, screen locking, a reopen, process death or Stop latency; carry
explicit lifecycle/resource checks into the next combined game-service candidate.
That combined server candidate is now hosted-qualified above; its physical
create/save/restart/resume and Stop/rerun checks are next. Graphical client
execution remains later work. Keep all existing diagnostics installed.

Earlier hosted import checkpoint (2026-09-29): **COH Atlas Setup 0.3.0 passed hosted
qualification** in [run 36556279364](https://github.com/Russianranger/coh-android/actions/runs/36556279364)
at `2f828ca3e626245ea9fd60055745980bc3f32001`. All 65 checks, the signed APK
build, full 173,011-file import, cancelled re-import and abandoned-stage recovery
passed. The complete inventory matches the accepted game data. The downloaded
APK and all four payloads were independently rehashed against the reports.
See the [acceptance receipt](android-evidence/accepted-asset-import-hosted-36556279364.json)
and [candidate/device instructions](ANDROID_ASSET_IMPORT.md).
Physical Thor import/Stop/retry is now accepted above. The subsequent 0.4.0
candidate failed its first restart check; the current candidate's retry instructions
above supersede its device test sequence. The 0.3.0
app imports content only; Android Atlas game services and graphical
gameplay remain unvalidated. Accepted listener and diagnostic evidence below
remains unchanged. The candidate uses a development/ephemeral signing certificate.

Continuation recovery (2026-09-29 UTC): recovered branch head `7aea5ee` and
confirmed its completed GitHub checks. Independently replayed the preserved
Thor and hosted loopback evidence: both 28-stage physical runs, clean Stop,
and the hosted 18-stage create/save/restart/resume sequence remain accepted.
The original uploaded ZIP downloads returned HTTP 502 during this recovery;
the replay used the receipt-bound reports and captures already in this repo,
not newly downloaded archives or fresh device execution.

**Previous hosted runtime milestone accepted:** the separate [MapServer/TestClient
listener profile](ANDROID_GAME_RUNTIME.md#mapserver-and-testclient-listener-candidate)
passed all four jobs in
[run 36510836956](https://github.com/Russianranger/coh-android/actions/runs/36510836956)
at `ac4c1f7978be444a893f65f5177641191861d42f`. Windows passed 17 native Winsock
contracts; all 18 ARM64 stages and final host validation passed in 1,873.269766
seconds. Both DbServer starts proved 14 local endpoints, both Atlas starts
proved UDP `127.0.0.1:7001`, and each TestClient session proved two loopback UDP
bindings. Character `TEST33790` / container 1 retained influence 12,345 and
selected SQL rows across both committed saves, same-cluster restart and
exact-name resume with creation disabled. LoginCount progressed 1 → 1 → 2.
All 122 process captures closed, with zero remaining owned processes or
inspection failures. The
[acceptance receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
binds the [raw report](android-evidence/game-listeners-arm64-36510836956.json)
and [preserved captures](android-evidence/game-listeners-evidence-36510836956.zip).

Verified file-picker import is implemented and accepted on Thor above. The
separate Android Atlas runtime/lifecycle integration was subsequently built and
hosted-qualified; the current candidate's physical retry is the next gate. The hosted
namespace remains mandatory;
the local binding policy does not establish device-wide network isolation.
Keep installed 0.1.5 and 0.2.0; no repeat of their passed diagnostics is needed,
and the listener milestone itself supplies no physical Atlas result.
Local verification: 162 checks ran (161 passed, one Windows-only observer
skipped), including 17 actual socket contracts and eight source-preparation
checks. Both complete creation/resume staging commands verified the immutable
5,995-file source snapshot and produced the expected separate receipts.
The three new game executables were also downloaded and independently checked
against their source receipts, byte hashes and PE metadata. Existing Wine,
DbServer console/launcher and orphaned Atlas door-point warnings match the
previous accepted run; no new failure diagnostics were found.

Previous device checkpoint (2026-09-28, 22:28 UTC): **COH Server Test 0.2.0 passed
on Thor**. The [receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two complete 28-stage real DbServer passes, a clean cancellation between
them, exact local listener coverage and complete owned cleanup. App switching
and screen locking are user-attested; peak memory is unmeasured. The subsequent
hosted Atlas loopback integration passed in `36493722153`, including both local
DbServer starts and both committed saves. MapServer/TestClient local bindings
subsequently passed hosted qualification in `36510836956`. Asset import has
since passed on Thor with 0.3.0; Android Atlas integration remains next.
Physical Atlas execution and rendering remain unvalidated.

Updated: 2026-09-29 (UTC). PostgreSQL controlled persistence, targeted stage1 inspection,
matching Windows packaging, base runtime assembly and data-only database schema
generation have passed their current checks. Normal fixture-OFF DbServer schema
initialization/export/reload and normal MapServer network save acknowledgements
have also passed against fresh PostgreSQL clusters.
The refreshed runtime and schema artifacts share repository commit
`775a0dd770adac045484805dbbb5f68054c7a354`. Ordinary asset-backed reference
comparison and Atlas Park protocol readiness have now passed. Fresh fake-auth
character creation, live currency change, protocol logout/save, database and
game-service restart, and exact-name short resume also passed in
[run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135).
The follow-on [sustained-session run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
also passed: exact-name resume, missing-name refusal without mutation, 66.953
seconds connected, restored live currency and a second protocol save.
The follow-on [Atlas transfer run 36297542986](https://github.com/Russianranger/coh-android/actions/runs/36297542986)
also passed: the same character moved map 1 → prestarted clone 101 → map 1,
preserved committed state at each arrival and completed the final protocol save.
The [primary M2 device diagnostic and headless client capability gate](THOR_DEVICE_ACCEPTANCE.md)
is now accepted on Thor with 0.1.5. The supplied combined report passed all twelve
stages, reused the database cluster and ready Wine prefix, and completed owned
cleanup with all 30 process input/output captures closed. The user also attests to
a preceding database-only pass; its separate archive was not supplied. Device
cleanup observed exited leaders with live owned workers, while the exact writer
of the earlier pipe was not inventoried. The subsequent 0.2.0 device gate now
proves Stop followed by a successful fresh rerun; app switching and screen
locking are user-attested, while peak memory remains unmeasured.
The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md)
also passed in run 36369485666: 21 persistence check groups across 14 fixture
invocations, then two fixture-OFF schema exports with 99 tables, 5,935 ordered
columns, 58,272 exact attribute IDs/names and a stable catalog on reload.
All 28 ARM64 stages passed, with all 111 process input/output captures closed and
zero remaining owned processes or inspection errors. The
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36369485666.json)
binds the reports and inputs. Physical Android DbServer execution has since
passed with 0.2.0; Android presentation and game rendering remain unvalidated. The separate
[hosted Atlas gate](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
passed its full workflow in run `36460005201`: all three jobs, all 18 guest
stages and the final host validator succeeded, including both protocol saves,
same-cluster restart and exact-name resume. The
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
binds independently verified reports and captures. The earlier `36454174481`
workflow failure and separate post-correction acceptance remain preserved,
alongside the first-save, restart-port and startup-timeout history below.
The follow-on diagnostic DbServer package passed all three jobs in run
`36425508780`. Windows verified enabled dispatch-record publication; the ARM64
fixture/schema gate used the observer disabled. Atlas run `36428915900` then
verified enabled ARM64 publication with this qualified donor and captured the
folder callback boundary during the intermittent timeout.
The current fixed-input successor is qualified in run `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`: all three jobs passed, including
default normal-schema startup and acknowledged fixed-input reload on ARM64.
This remains the default Atlas donor; preserve the earlier first-save and
dispatch evidence. The accepted device diagnostics are 0.1.5 and 0.2.0.
The separate opt-in loopback listener package passed all three hosted jobs in
[run 36460867428](https://github.com/Russianranger/coh-android/actions/runs/36460867428)
at `eed2ce1f5388195f65a07853919761a93657aca6`. Its
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36460867428.json)
records 28 ARM64 stages in 191.502348 seconds, all 13 required loopback binds
(12 TCP plus UDP 7000), and the optional asynchronous TCP 6992 bind. Windows
passed all eleven native loopback contracts and the existing persistence,
dispatch and fixed-input checks. Both schema exports and the catalog were
stable; all 111 captures closed with zero owned processes or inspection errors.
The first attempt `36460005041` failed before DbServer builds or runtime execution
because its Windows test fixture applied a CRLF patch to LF source files.
The correction normalizes only that fixture's patch input and adds a CRLF
regression; preserve the
[failure receipt](android-evidence/dbserver-qualification-failure-36460005041.json).
This qualifies the hosted listener prerequisite. Physical DbServer listener
execution and app integration subsequently passed with 0.2.0. The default Atlas
donor remains `36451873322`; its separate loopback profile uses `36460867428`.
The first attempt with the preceding diagnostic donor `36425508780`, run
`36427680960`, stopped before game execution
when the pinned talloc download timed out during the PRoot build. A bounded
download retry is now applied. The next run passed dependency preparation with
no retry line observed; the transport remedy supplies no startup-fix evidence.
The reviewed asset ZIP has been uploaded to a draft release and downloaded by
the hosted runner with its exact size/hash verified. That attempt then stopped
on Windows manifest line endings before game execution. The byte-preserving
checkout fix is applied and run 36176806895 completed successfully: all 56 fresh
template outputs matched, then Atlas Park remained ready for 62.235 seconds.
Earlier character attempts exposed harness status parsing and console capture
issues; the final corrected run completed all eight phases with no failures.

Continuation on 2026-09-26 recovered the completed 2026-09-25 run after this
handoff had retained an in-progress status. At recovery, GitHub showed no queued
or running workflow and the latest commit was `04d62616e2e1b41b10f35a04d4c798e43680d5ba`
(2026-09-25 19:05:39 UTC). The workflow finished at 19:16:38 UTC. These observations
do not reveal the internal status of the other Codex session.

## Earlier hosted DbServer-loopback checkpoint (2026-09-28)

[Run 36493722153](https://github.com/Russianranger/coh-android/actions/runs/36493722153)
at `708878f78a3361b595dcc03a0c4b14fb6cd2e6c3` **passed the separately identified
Atlas loopback DbServer profile**: all three jobs, all 18 guest stages and final
host validation. The [receipt](android-evidence/accepted-game-loopback-hosted-36493722153.json)
binds independent replay of the unchanged reports and captures. Runtime took
1,883.535869 seconds; first service readiness took about 17 minutes 32 seconds
and restart readiness about 3 minutes 13 seconds.

Both DbServer starts proved all 14 observed local endpoints, including optional
TCP 6992. Character `TEST-60538` / container 1 retained influence 12,345 and its
selected committed SQL rows through same-cluster restart and exact-name resume
with creation disabled. LoginCount progressed 1 → 1 → 2 across both protocol
saves. Both fixed-input acknowledgments and all four inventory checks passed.
All 122 process input/output captures closed, with complete cleanup and zero
remaining owned processes or inspection failures. Preserve the
[raw report](android-evidence/game-loopback-arm64-36493722153.json) and
[captured evidence](android-evidence/game-loopback-evidence-36493722153.zip).

The workflow explicitly selects loopback donor `36460867428`; default assembly
and the earlier accepted profile retain `36451873322`. This qualifies DbServer
binding within that earlier Atlas sequence. The subsequent `36510836956`
profile qualified MapServer and TestClient local bindings as well. The private
hosted network namespace remains mandatory; outgoing TCP and device-wide
isolation are outside the binding proof. Physical Atlas execution remains
unvalidated. Follow
the [remaining device preparation](ANDROID_GAME_RUNTIME.md#remaining-preparation-for-a-physical-atlas-candidate),
keeping accepted 0.1.5 and 0.2.0 installed.

### Earlier accepted default-profile workflow

[Run 36460005201](https://github.com/Russianranger/coh-android/actions/runs/36460005201)
at `cfc8ac477e449037213d5242f43480acf4f1cb85` **passed all three jobs and the
complete hosted Atlas gate**. The [raw report](android-evidence/game-arm64-36460005201.json)
records all 18 stages in 1,963.43549 seconds, `TEST48625` / container 1 /
account `CohAa82e8aaa56`, live influence 12,345, first protocol save, Wine and
same-cluster PostgreSQL restart, exact-name resume at slot 0 with creation
disabled and a processed server update, and the second protocol save.
LoginCount progressed 1 → 1 → 2; selected SQL retained one `ents` row, one
`ents2` row, seven powers and 13 costume parts. Atlas readiness was independently
observed for 31.421914 seconds with current heartbeats.

Both fixed-input acknowledgments and all four unchanged input checks passed
(62 files / 4,402,846 bytes). Schema, attribute IDs/names and the full catalog
stayed stable. All 123 process input/output captures closed; graceful PostgreSQL
and Wine cleanup left zero owned processes or inspection failures. Independent
full report, character/SQL capture and service-capture checks passed with the
exact tested validator modules. Preserve the
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json) and
[captured evidence](android-evidence/game-evidence-36460005201.zip).
Atlas donor `36451873322` at `53c6270dff8a0efcc6be09da756408504d8313bd` and
APK 0.1.5 remain unchanged. Physical Android game execution, presentation and
rendering remain unvalidated.

### Testing takeover verification (2026-09-28)

A fresh checkout at `d1907db` independently replayed the accepted `36460005201`
evidence. All 43 preserved archive members matched their recorded sizes and
hashes; the raw report was byte-exact. The exact tested validator modules passed
`validate_report`, `validate_capture_files` and `validate_service_captures`.
The [verification record](android-evidence/atlas-takeover-verification-20260928.json)
delimits the retained-evidence scope: no fresh runtime or device execution,
and no recomputation of the omitted full data inventory or executable payloads.
The current focused suites passed 103 tests with one Windows-only observer test
skipped locally; the accepted hosted Windows job covers that observer.

Live GitHub inspection confirmed the successful full Atlas run and zero queued
or running repository workflows. This does not reveal another agent's internal
session status. README and Thor next-work instructions now point to Android
integration and physical device qualification instead of repeating the accepted
hosted Atlas milestone. The 0.1.5 APK and Atlas donor are unchanged.

### Earlier acceptance after host validator correction

[Run 36454174481](https://github.com/Russianranger/coh-android/actions/runs/36454174481)
at `8944bd598990b33b63a750a64ae448403e4542cd` has an **accepted runtime sequence
after host revalidation; the original workflow conclusion remains failure**.
All 18 guest stages passed in 1,867.229988 seconds. The
[raw report](android-evidence/game-arm64-failed-36454174481.json) records
`TEST01443` / container 1 / account `CohA318dc5a821`, live influence 12,345,
first protocol save, Wine and same-cluster PostgreSQL restart, restarted Atlas
readiness, exact-name resume at slot 0 and the second protocol save. LoginCount
progressed 1 → 1 → 2; selected SQL retained one `ents` row, one `ents2` row,
eight powers and 14 costume parts. Atlas readiness was independently observed
for 31.564746 seconds.
Both DbServer fixed-input acknowledgments and all four unchanged input checks
passed (62 files / 4,402,846 bytes). All 122 input/output captures closed;
cleanup left zero owned processes or inspection failures.

The original host validator incorrectly required `child_exited: true`, which
the bridge does not serialize. The correction requires the existing exit code
to be a terminal DWORD and rejects `STILL_ACTIVE` (259). Both clients recorded
exit code 125 after forced termination following independently committed
protocol saves. Strict full report, character-capture and service-capture
validation passed against unchanged evidence. Preserve the separate
[acceptance receipt](android-evidence/accepted-game-hosted-36454174481.json),
[failure receipt](android-evidence/game-runtime-failure-36454174481.json) and
[captured evidence](android-evidence/game-evidence-36454174481.zip).
The actual C serializer, real guest stop validation and host consumer are
covered by a regression; the runtime, bridge producer and evidence bytes are
unchanged. The original Actions run remains failed. Keep donor `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`
and the accepted 0.1.5 APK unchanged. Physical Android game execution,
presentation and rendering remain unvalidated.

The separate sibling DbServer [run 36454174374](https://github.com/Russianranger/coh-android/actions/runs/36454174374)
failed attempt 1 with SIGSEGV (`-11`) after `PG_TEST_COMPLETE rebuild` and
teardown messages. Attempt 2 reused the byte-identical package and passed all
28 stages in 190.362494 seconds, with all 111 captures closed and complete
cleanup. The [failure](android-evidence/dbserver-runtime-failure-36454174374.json)
and [repeat](android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
receipts preserve both outcomes. The failure remains intermittent and
unexplained; the passing repeat does not establish a repair or replace the Atlas
donor.

### Earlier hosted ARM64 checkpoints

[Run 36416020268](https://github.com/Russianranger/coh-android/actions/runs/36416020268),
commit `324823be6ca9713bdc60446eb31596004ff6286a`, is an **overall failure with
new partial runtime evidence**. Atlas stayed independently ready for 31.519
seconds. Stock TestClient created `TEST02279` / ID 1, entered Atlas, changed live
influence to 12,345 and completed protocol logout with an independent committed
SQL snapshot (LoginCount 1) before forced cleanup. Wine and PostgreSQL shut down
cleanly; the same PostgreSQL cluster restarted. The next service-launch
preflight failed immediately with `[Errno 98] Address already in use`, before
replacement game services started. No exact-name resume or second-save proof
was obtained. Preserve the [raw report](android-evidence/game-arm64-failed-36416020268.json)
and [detailed evidence](ANDROID_GAME_RUNTIME.md#first-arm64-creation-and-protocol-save-restart-gate-failed).

The bounded fallback snapshot found no owned Wine processes or game-role SQL
sessions after the verified shutdown. Review confirmed that the TCP preflight
lacked the native `SO_REUSEADDR` behavior used by pinned Wine. An isolated Linux
experiment reproduced the bare-bind error with TIME_WAIT and passed with TCP
reuse while retaining rejection of live listeners and occupied UDP ports. The
hosted report has no socket table proving that state, but the behavior is
consistent with its failure. The narrow harness correction and tests were
applied for the subsequent run described below; restart validation was still required. The
prior startup timeout did not recur: one query returned after 78.833 seconds and
AutoCommands retrieval completed after 82.71 seconds. This does not establish
that intermittent startup delay as fixed. Do not repeat the successful first
save as if it were still unknown, or mark the full hosted gate accepted before
restart/resume/second-save pass. Keep the accepted 0.1.5 device diagnostic;
Android game presentation and gameplay remain unvalidated.

The subsequent [run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed a startup query in the first
service phase after 13 preceding readiness queries had completed. The failing
query reached 90.041 seconds, so it did not exercise the restart-port correction.
Preserve the prior first-save evidence above. The new
[failure receipt](android-evidence/game-runtime-failure-36420158506.json),
[raw report](android-evidence/game-arm64-failed-36420158506.json) and
[pre-cleanup snapshot](android-evidence/game-hang-36420158506/snapshot.json)
show live DbServer/Atlas/query processes and 65 idle SQL sessions. All Windows
capture APIs completed (three processes, 72 threads, 114 modules, zero errors),
but inspection of pinned Wine/FEX shows `GetThreadContext` supplies saved WOW64
context rather than current translated x86 execution state. Decoded DbServer
pointers lead to an already-completed startup path, so they do not identify the
live blocker or justify a main-loop change. Final cleanup passed with all 59 process
captures closed and zero remaining owned processes or inspection failures.
This run did not validate the full hosted restart/resume/second-save gate or
Android gameplay.

[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` qualified the separately receipted
DbServer package containing [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md):
all three jobs passed, including the Windows enabled-record contract. The ARM64
fixture and normal schema checks ran with the observer disabled. Preserve the
[new acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
alongside the original acceptance. The donor manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632` and the normal
executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

Atlas adopted donor `36425508780`, with separate fresh records required for
first startup and restart. Enabled publication on live ARM64 was subsequently
verified in run `36428915900` below. Bounded stage/sequence observations distinguish progress
through startup, dispatch, SQL keepalive and console handling without relying
on stale WOW64 contexts. A stopped marker identifies an operation and its nested
calls; it does not prove a deadlock or gameplay success. No startup blocker fix
has been established, and the accepted device APK remains 0.1.5.

[Run 36427680960](https://github.com/Russianranger/coh-android/actions/runs/36427680960)
at `82386fd48c2352a2ce65d5920f7857e8b92ec442` passed source, package and data
staging, then failed on a read timeout downloading pinned talloc for the PRoot
build. No game diagnostic ran, and no runtime report or dispatch sample exists.
The [infrastructure failure receipt](android-evidence/game-infrastructure-failure-36427680960.json)
preserves this result. It adds no evidence about the intermittent startup
stall. The isolated retry correction allows at most three transport attempts,
discards partial downloads and preserves the size/SHA-256 gates; Atlas tooling
now explicitly runs its regression tests. The next run passed dependency
preparation without an observed retry. This download remedy is not a game
startup fix; this attempt did not reach restart/resume/second-save.

[Run 36428915900](https://github.com/Russianranger/coh-android/actions/runs/36428915900)
at `f32ccd7c0f1aa950d1f87ceb81ab09b2dba4e2ac` failed a first-phase startup query
after 90.030 seconds, following 13 completed readiness queries. Enabled ARM64
source markers are now validated: the initial record had sequence 28 / loop 1
at `NM_MONITOR`; the same DbServer PID 412 / main thread 416 and mapped file
later held `FOLDER_CALLBACKS`, sequence 2,449,552 / loop 43,741. Identical before
and after records span 13:55:20.897–13:55:23.957 UTC. This localizes the observed
work to folder callbacks or nested calls. Separate non-atomic native snapshots
showed `read` and `fchdir` operations under PRoot, so a deadlock is not established.
The specific nested operation and throughput remain unknown.

The query, DbServer and Atlas were alive before cleanup, and the query remained
alive after the 3.061-second capture. All 65 SQL sessions were idle in
`ClientRead`, without active transactions; the foreground last query was `;`,
about 134.9 seconds old. Atlas ended at `Retrieving AutoCommands..`. Preserve the
[failure receipt](android-evidence/game-runtime-failure-36428915900.json),
[raw report](android-evidence/game-arm64-failed-36428915900.json) and
[snapshot](android-evidence/game-hang-36428915900/snapshot.json). Archive and all
eight service/hang capture hashes were independently verified. Final cleanup
passed with all 57 process input/output captures closed and zero remaining owned
processes or inspection failures. No new character or restart result was obtained.

The opt-in [fixed-input DbServer mode](../database/wine-dbserver/FIXED_INPUTS.md)
is now qualified in [run 36451873322](https://github.com/Russianranger/coh-android/actions/runs/36451873322)
at `53c6270dff8a0efcc6be09da756408504d8313bd`. It prevents watcher registration
before the first cache while preserving initial reads and lookup mode; it does
not establish a generic Wine notification fix. All 28 ARM64 stages passed in
192.280590 seconds, including 21 persistence groups across 14 fixture phases,
default normal-schema startup and acknowledged fixed-input reload. Both fresh
empty exports preserved 99 tables, 5,935 ordered columns, 58,272 exact attribute
IDs/names and the full catalog. All 111 process captures closed; cleanup left
zero owned processes or inspection errors. Preserve the
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36451873322.json).
The donor manifest SHA-256 is
`e4f8a66802f29643b13aec2228ada1549a80c22efa11de1549a9b145bb43e06b`;
normal executable SHA-256 is
`659e9072234f75ad02c8cac2636df93f5249ff1de385c1ed7d6c6fc0c04a453a`.

Earlier fixed-input qualification `36434692816` passed Windows/source checks,
but both ARM64 attempts failed before DbServer execution on talloc HTTP 503
after all three transport attempts. Successful qualification `36451873322`
recovered the identical archive from accepted runtime `36364550345`'s verified
corresponding-source bundle. Atlas uses the same source recovery; the build
recipe and source pins are unchanged.

The Atlas harness now enables this mode only for DbServer and requires its exact
startup acknowledgment on both launches. After private `servers.cfg` generation,
it binds all 62 accepted schema inputs plus the entire staged `data/server/db`
tree. Four unchanged snapshots are required: before first startup, after first
save, before restart and after second save. Run `36454174481` subsequently
completed this sequence; its unchanged evidence passed strict host revalidation
after correction of the bridge exit contract. Preserve the original failed
workflow, earlier first-create/save evidence and accepted 0.1.5 APK; Android
game execution and rendering remain unvalidated.

## Continuation validation checkpoint

The accepted character run is **36282414135**, tested commit
`86e512e85c8350714bc7b58668bf11443dc164f8`, completed 2026-09-27 00:40:07 UTC.
It verified `TEST20636` / container ID 1 with live influence 12,345, committed
protocol logout before forced cleanup, restart of the same PostgreSQL cluster
and game services, and exact-name short scene resume with creation disabled.
Selected identity/rows remained unchanged (1 parent, 1 `ents2`, 7 powers,
13 costume parts); `LoginCount` progressed 1 → 1 → 2. The resume exited
naturally with code 0 and both console observers finalized successfully.
The [report](postgresql-evidence/character-persistence-36282414135.json),
[complete artifact](postgresql-evidence/character-persistence-36282414135.zip) and
[acceptance/provenance record](postgresql-evidence/accepted-character-persistence-36282414135.json)
are preserved. Windows passed 67 tooling/map checks; Linux passed 62 with five
Windows-only skips. All four same-commit
[PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36282414187)
passed. The short resume does not establish sustained gameplay or Android execution.

### Accepted next milestone: sustained second session

The [sustained-session implementation](SUSTAINED_SESSION_VALIDATION.md) adds a
separately identified diagnostic TestClient with creation disabled and a normal
connected command loop. [Run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
passed all 12 phases at `4e8058c3ffe20acda61b55023202d409ed1d0df1`, completing
2026-09-27 05:08:11 UTC. `TEST-37762` / ID 1 resumed with live influence 12,345
and a processed server update confirming its identity. Ten samples covered
66.953 seconds connected on Atlas Park, with a maximum gap of 7.625 seconds.
The second live influence command produced 23,456 and committed through protocol
logout before forced cleanup. Missing-name refusal exited naturally with code 3
and left the entire character inventory and selected SQL unchanged.

`LoginCount` progressed 1 → 1 → 1 → 2 across first logout, restart, missing-name
probe and second logout. Selected identity/rows stayed identical except for the
intended influence change (1 parent, 1 `ents2`, 7 powers, 16 costume parts).
All three console observers finalized successfully. The [raw report](postgresql-evidence/character-session-36295176484.json),
[complete artifact](postgresql-evidence/character-session-36295176484.zip) and
[acceptance record](postgresql-evidence/accepted-character-session-36295176484.json)
are preserved. Windows passed 103 tooling checks; Linux passed 98 with five
Windows-only skips. The same-commit [stock regression](https://github.com/Russianranger/coh-android/actions/runs/36295176352)
and all four [PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36295176473)
passed. The accepted stock TestClient and server reference binaries remain
unchanged; the diagnostic client has separate source/build receipts.

The first hosted attempt
[36293644180](https://github.com/Russianranger/coh-android/actions/runs/36293644180)
passed stock creation/save/restart and missing-name refusal without mutation,
then rejected the positive selection because the character-list packet does not
populate its `db_id` field. The correction checks exact name/slot there and binds
the actual MapServer entity ID after the processed update to independent SQL.
The [failed evidence](postgresql-evidence/character-session-36293644180.json) is
preserved. The corrected retry above proves the sustained resume and second save;
the failed attempt remains identified as a failure.

### Accepted next milestone: Atlas instance transfer

The [Atlas instance transfer gate](MAP_TRANSFER_VALIDATION.md#accepted-hosted-validation-36297542986)
passed all 15 phases in run `36297542986`, tested commit
`5f2c561058a186de59d3f27301eea210bd4bb66d`; terminal success was recorded
2026-09-27 05:56:06 UTC. `TEST59440` / ID 1 stayed in the same client process
for map 1 → clone 101 → map 1. Fresh player updates carried transfer epochs 1
and 2 on ports 7002 and 7001, while independent character status confirmed
MapId/SmapId 101 then 1. Each arrival had current heartbeats, live influence
12,345 and unchanged committed selected state. Per-leg SQL reads establish that
state, not a fresh identical-write acknowledgement. The subsequent live change
to 23,456 and protocol logout supplied a fresh final-save proof before cleanup.
LoginCount stayed 2 across both transfers and final logout; no extra character
was created. All three console observers finalized successfully.

The [raw report](postgresql-evidence/character-transfer-36297542986.json),
[artifact](postgresql-evidence/character-transfer-36297542986.zip) and
[acceptance record](postgresql-evidence/accepted-character-transfer-36297542986.json)
are preserved. Windows passed all 119 tooling checks; Linux passed 114 with
five Windows-only skips. The same workflow passed the 12-phase sustained
regression using the same diagnostic bytes (62.532 seconds over 10 samples).
The stock-client and all four PostgreSQL regression jobs also passed at
`3848133e5e644f4c166cc9e7f3e027288d06c2fd`, with identical runtime code;
the retry changed only the test fixture and documentation.
The first transfer attempt stopped before the build on a Windows C-test fixture
portability error. The fixture now uses Winsock on Windows; client and server
code are unchanged by that correction. The [tooling failure record](postgresql-evidence/character-transfer-tooling-36297326622.json)
is preserved separately from the successful retry.

### Historical hosted M2 gate (0.1.0)

[Run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
passed all four jobs at source `0b61d7455f40f05709f912338cd5de8b1d72d750`,
completing 2026-09-27 17:29:16 UTC. All 80 tooling tests passed without skips.
The APK's exact guest assets passed eleven stages on Linux ARM64, including
real PE32 DLL/driver loading, all 65 stock ODBC connections, transactions,
rollback, UTF-16/binary values, column metadata, schema rebuild/reopen, graceful
same-cluster restart and a second Win32 verification of persisted data. All
three cleanup checks passed. The same-source [PostgreSQL regression run](https://github.com/Russianranger/coh-android/actions/runs/36336644454)
also passed all four jobs. Preserve the [acceptance receipt](android-evidence/accepted-hosted-36336644450.json)
and [raw guest report](android-evidence/runtime-smoke-report-36336644450.json).

`COH-Diagnostic-0.1.0.apk` is 13,309,477 bytes, SHA-256
`80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac`.
Download the `coh-diagnostic-apk` artifact from the accepted run. It contains
no game binaries or assets. The native Java app and owned PRoot session combine
pinned Bookworm/Wine 10/FEX inputs with PostgreSQL built from official pinned
source; its ephemeral CI signing certificate is not a stable update identity.

Physical Thor acceptance was pending at this checkpoint. The current
[device acceptance record](THOR_DEVICE_ACCEPTANCE.md) preserves the later 0.1.5
pass and remaining lifecycle checks. Hosted Linux execution alone does not prove
Android SELinux, foreground-service lifecycle, device shutdown, performance or
gameplay. Mission/new-zone transfers, automatic Launcher startup and combat remain
separate unfinished scope.

### Accepted hosted client prerequisite milestone (0.1.1)

Continuation on 2026-09-27 found the hosted M2 gate complete, with physical Thor
acceptance still pending. The branch had no unfinished result to recover from its
latest completed workflows; this does not expose another Codex session's internal
state. Work advanced to the independently permitted
[basic client capability probe](CLIENT_RUNTIME_PROBE.md).

Commit `c1097bdc0aab433fd3cb1560fd07175c6c3dc6b0` adds a separate **Run client probe**
operation to 0.1.1. It exercises a real PE32 WGL context, a textured quad with four
verified RGB readbacks, buffer swap, own-window keyboard/mouse messages and
DirectInput device creation. Audio enumeration and extension availability are
observations only. The original database-only operation remains available and
both modes require complete owned cleanup. The app now scrolls on short displays.

Local validation passed 93 tests with two environment-dependent skips; the actual
PE32 program also cross-compiled warning-free with `-Werror` and its Windows
imports were verified. Hosted workflow [36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245)
passed all five jobs at 20:59:41 UTC, including all 93 tooling tests without skips.
Database mode passed eleven stages; client mode passed twelve. The observed
renderer was llvmpipe/Mesa 22.3.6 OpenGL 4.3, all four RGB readbacks were exact,
and synthetic input plus DirectInput device creation passed. Both modes proved
graceful PostgreSQL restart and complete cleanup. DirectSound enumerated zero
devices, with no playback claim. All same-source PostgreSQL regressions passed.
The [acceptance record](android-evidence/accepted-client-probe-36349552245.json)
preserves report hashes, observed capabilities and the verified 13,477,490-byte
APK. Preserve it as the historical 0.1.1 result; the later
[Thor acceptance record](THOR_DEVICE_ACCEPTANCE.md) describes current device evidence.
A fixture result cannot establish CoH rendering, Cg shaders, physical controls,
audio playback, Android presentation or GPU acceleration. Thor reports were still
needed at this checkpoint; M3 minimal game-server/device execution remains unfinished.

### Historical Thor wineboot failure and hosted 0.1.2 result

The user supplied two Thor/Android13 reports from 0.1.1. Both passed native
PostgreSQL initialization, restricted fixture SQL and owned cleanup, but failed
at the 150-second wineboot wait before Windows ODBC or graphics. The second run
reused the same diagnostic database cluster. This is partial real-device database
evidence; complete M2/device acceptance remained pending at this checkpoint.

[The selected device evidence](android-evidence/thor-wineboot-failure-20260927.json)
records both failures. Their exit-code0 values were captured after forced cleanup
and do not establish the initializer's status before the timeout. A real subprocess
regression reproduced a false timeout when a successful initializer's background
service retains stdout. Commit `1afb0610095ebe3cb8aba591ea22d749613b7276` applies
[the narrow 0.1.2 fix](ANDROID_WINEBOOT_RETRY.md): wineboot alone may complete on
its own exit, with captured background output retained under owned cleanup. Live
initializer timeouts, nonzero exits, cancellation and output limits remain errors.
Receipts now record pre-signal state and require capture/writer shutdown too.

[Hosted run 36352420585](https://github.com/Russianranger/coh-android/actions/runs/36352420585)
passed all five jobs at this commit on 2026-09-27 21:44:41 UTC: all 99 tests
without skips, eleven database stages, twelve client stages and complete owned
cleanup. The [acceptance receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
preserves that historical build and reports. Hosted wineboot exited with output
capture still open; capture closed during cleanup. This proves the corrected
wait path was exercised, not that inherited output caused the Thor failures.
The subsequent Thor retry failed; the inherited-output correction alone did not
resolve device initialization.

### Historical 0.1.3 cold initialization qualification

[The 0.1.2 device report](android-evidence/thor-initializer-timeout-20260927.json)
records wineboot still running at 150.040 seconds before cleanup signals. Four
early native database stages passed; Windows ODBC and graphics were not reached.
PostgreSQL and prefix shutdown passed, but output capture remained open, so
complete cleanup was not proved.

Commit `49c1626c10636e46a38493047f34ab61a9a5d5ca` applies the
[0.1.3 initialization correction](ANDROID_WINE_INITIALIZATION.md): use `wineboot -i`
to avoid a forced second registration pass, invalidate only the timestamp of an
unready prefix, allow 600 seconds with progress every five seconds, and write a
readiness marker only after the real PE32 fixture passes. Successful warm runs
preserve the timestamp. Wine bootstrap errors, fixture failures and open captures
still fail the diagnostic; Stop and the overall fifteen-minute limit remain.
This addresses startup behavior without identifying the exact internal component
delayed on Thor.

[Hosted run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs on 2026-09-27 22:16:35 UTC at this source. All 109 tests passed
without skips. Fresh and repeat runs each passed eleven database stages or twelve
client stages, including all Windows fixtures and complete cleanup. Cold Wine
initialization took 39.911 seconds in database mode and 40.305 seconds in client
mode, with one registration pass each; both warm runs took 4.629 seconds with zero
registration passes. These timings describe the hosted environment. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36354266044)
also passed. The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds the verified APK, payload hashes and runtime evidence.

The subsequent device run passed initialization and all eleven functional stages;
its remaining cleanup failure is recorded below. Preserve the 0.1.3 artifact and
receipt as historical evidence.

### Historical 0.1.4 Wine helper cleanup qualification

[The 0.1.3 Thor report](android-evidence/thor-functional-pass-cleanup-failure-20260927.json)
completed initialization in 90.927 seconds with one registration pass, then passed
native PostgreSQL, real PE32 DLL loading, all 65 ODBC sessions, SQL/value/metadata
checks and durable same-cluster restart verification. The sole recorded failure
was `Owned process input/output capture did not close: wineboot`. The Wine prefix
lock and socket were inactive, and PostgreSQL shut down cleanly; that does not
prove every detached Unix helper exited. The remaining pipe writer is unidentified.
Client graphics were not requested.

Accepted source `83f132ddb8077c9d5175ae7cd039e0754b70074e` applies the
[0.1.4 cleanup correction](ANDROID_WINE_CLEANUP.md). Wine helpers carry an exact
per-run ownership token; bounded cleanup verifies the real UID and PID identity
before signaling. Output captures must actually reach EOF, and unrelated processes
must survive. The menu-helper override is corrected to `winemenubuilder.exe`;
its earlier launch does not prove it caused the retained pipe.

The initial [hosted attempt 36356073708](https://github.com/Russianranger/coh-android/actions/runs/36356073708)
stopped on ownership inspection of an unreadable, unrelated same-UID CI process.
The accepted correction safely excludes processes strictly older than diagnostic
startup, which cannot inherit the new child-only token; current or newer processes
still require inspection.

[Run 36356283176](https://github.com/Russianranger/coh-android/actions/runs/36356283176)
passed all five jobs on 2026-09-27 22:50:49 UTC. All 116 tests passed in 11.510 seconds
without skips. Database fresh/repeat runs passed all eleven stages; client
fresh/repeat runs passed all twelve. Every owned input/output capture closed,
ownership cleanup completed and no helpers remained. Cold initialization took
39.397 seconds in database mode and 37.973 seconds in client mode; warm runs took
4.276 and 4.126 seconds respectively. These are hosted timings.

Both detached-helper fixtures exercised one TERM and one KILL through two pidfd
signals, with zero remaining helpers or inspection failures. The unrelated
sentinel survived and the capture reached genuine EOF. All twelve embedded APK
assets and all six hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36356285898)
also passed. The [acceptance receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
preserves the build identity, payload hashes and reports.

The subsequent 0.1.4 Thor run again failed capture closure; the hosted receipt
and APK remain historical evidence.

### Hosted 0.1.5 Wine thread cleanup qualification

[The 0.1.4 device report](android-evidence/thor-capture-still-open-20260928.json)
passed all eleven functional stages and initialized Wine in 85.957 seconds. The
same wineboot capture failure remained after graceful PostgreSQL and Wine prefix
shutdown. Ownership scanning reported zero candidates, zero inspection failures
and completion, so its accounting did not explain the still-open pipe. Graphics
was not requested.

The [thread cleanup investigation](ANDROID_WINE_THREADS.md) reproduced a native
thread-group leader in `Z` state while a live worker retained the exact ownership
token and inherited output pipe. The old policy skipped that group, reported zero
candidates and left the capture open. Signaling the authenticated group allowed
genuine EOF. This confirms a real cleanup defect; the physical report has no
thread inventory and cannot identify its remaining writer.

Version 0.1.5 inspects surviving tasks of an exited leader and verifies UID,
thread-group ID, start time, PID namespace and the exact run token before group
signaling, preferring a group pidfd. A true zombie without live tasks needs no signal.
Unknown ownership, surviving owned tasks or missing output EOF must still fail.
Thread observations in reports exclude environment contents and ownership tokens.

Accepted source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4` includes the final
state-transition race and missing-task checks.
[Run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
passed all five jobs on 2026-09-28 01:12:14 UTC. All 125 tests passed in 15.591
seconds without skips. Fresh/repeat database runs passed eleven stages each;
client runs passed twelve each. Cold initialization took 39.343 seconds in
database mode and 39.747 seconds in client mode; warm runs took 4.176 and 4.277
seconds respectively. These timings describe the hosted environment.

The ordinary detached-helper and exited-leader/live-worker fixtures passed in
both modes under the pinned PRoot. Each thread fixture observed a zombie leader
with an authenticated worker holding the exact inherited pipe, which the old
policy would miss. Cleanup exercised one TERM and one KILL through two pidfd
signals and reached genuine EOF. An unrelated, TERM-sensitive sentinel running
the same executable survived. These are direct fixture observations, not evidence
of the identity of Thor's remaining writer.

All twelve APK payloads and all eight hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36364553676)
also passed. The [acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
preserves build identity, payload hashes and reports.

### Accepted primary M2 Thor diagnostic and headless client gate

The [device acceptance record](THOR_DEVICE_ACCEPTANCE.md) and
[selected evidence](android-evidence/accepted-thor-20260928.json) preserve the
supplied `coh-diagnostic-20260928-012426.zip` report. It identifies app 0.1.5 on
AYN Thor/Android 13 and runtime manifest
`fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203`, matching the
accepted hosted build. The `database_and_client` run completed at
2026-09-28 01:24:05.958172 UTC with all twelve stages passed, no failures and
complete owned cleanup.

This report proves a successful subsequent combined run: the existing database
cluster and ready Wine prefix were reused. The user says both operations passed, including
the preceding database-only run; the supplied archive directly documents only
the subsequent combined run. It verifies native PostgreSQL, real PE32 DLL and ODBC driver
loading, all 65 ODBC sessions, SQL/value/metadata fixtures and durable same-cluster
restart. Headless WGL rendering through llvmpipe/Mesa 22.3.6 returned all four
expected pixel colors; synthetic window input and DirectInput device creation
passed. This is a software renderer. DirectSound enumerated zero devices, with
no audio playback claim.

Device cleanup now observed three exited-leader groups and three authenticated
live-worker witnesses. It issued three TERM signals and one KILL signal through pidfds,
finished with zero remaining helpers or inspection failures, and closed input and
output for all 30 recorded processes. This observes the reproduced dead-leader/
live-worker condition on Thor and completes cleanup successfully. The report does
not inventory the exact earlier pipe writer, so that identity remains unknown.

**The primary M2 device diagnostic and headless client capability gate are
accepted.** Android surface presentation, hardware acceleration, physical input,
audible playback and CoH gameplay remain unvalidated. The subsequent 0.2.0
DbServer test passed two full runs with a clean Stop between them. App switching
and screen locking are user-attested; peak memory remains unmeasured. Keep both
accepted installations. The next device work is verified asset import and the
combined Atlas runtime with Android lifecycle handling. The
[first hosted M3 DbServer gate](ANDROID_DBSERVER.md) subsequently passed in
run 36369485666. The latest managed Atlas result above accepts hosted
MapServer/client local bindings; Android packaging, network integration and
app lifecycle checks remain before physical Atlas acceptance.

### Earlier attempts and corrections

The recovered evidence and new character harness are on
[`codex/character-persistence-continuation`](https://github.com/Russianranger/coh-android/pull/1)
in draft PR #1. Implementation commit: `3d61ca929dc825ba9424279553797b66498df418`.
[Hosted run 36269025801](https://github.com/Russianranger/coh-android/actions/runs/36269025801)
passed both tooling jobs: all 55 Windows checks, including three live named-pipe
checks; Linux passed 52 with those three platform checks skipped. The game
experiment failed with `Unknown character status flags`: a multiline whitespace
match consumed process output after a valid status line. Character ID 1 and its
name agreed between TestClient, stock `-find` and independent SQL, but no save or
restart pass was reached. The [full failed attempt](postgresql-evidence/character-persistence-36269025801.zip)
and [report](postgresql-evidence/character-persistence-36269025801.json) are preserved.
The status parser is corrected at `cc3c82a87e2c3eabe1478b13ea031e3923423b10`,
without relaxing identity or flag checks. The reproducing regression passed;
all 40 portable character checks passed, with three Windows transport checks
skipped locally. [Fresh retry 36270565732](https://github.com/Russianranger/coh-android/actions/runs/36270565732)
failed after the status fix worked: character ID 1/`TEST-43027` was connected on
Atlas Park, but TestClient's GUI entry allocated its own console and reopened
stdout/stderr to `CONOUT$`. The harness could not see the required creation
branch text. The [artifact](postgresql-evidence/character-persistence-36270565732.zip)
and [report](postgresql-evidence/character-persistence-36270565732.json) are preserved.
The attempted console preallocation fix was rejected by its Windows GUI
regression in [run 36280623154](https://github.com/Russianranger/coh-android/actions/runs/36280623154):
`AllocConsole` still succeeded, so the runtime job was skipped. The replacement
uses a bounded observer attached to the actual TestClient console before the
launcher version exchange, preserving the console across the short client exit.
[Run 36281372316](https://github.com/Russianranger/coh-android/actions/runs/36281372316)
then passed all 66 Windows tooling/map checks and reached real character creation,
live currency 12345, protocol logout and independently committed SQL. The first
saved snapshot contains one parent, one secondary row, seven powers and twelve
costume parts. It failed on observer cleanup before restart acceptance: forced
client-tree termination closed the console before its final snapshot. The
[artifact](postgresql-evidence/character-persistence-36281372316.zip) and
[report](postgresql-evidence/character-persistence-36281372316.json) are preserved.
The follow-up finalizes the observer after proven logout/save but before residual
client cleanup; exact resume acceptance remains required.
All four [PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36269025871)
also passed on the implementation commit.

The final cleanup-order correction in `86e512e8` completed the restart/resume
gate. Its accepted evidence and remaining scope are recorded above; earlier
failed attempts remain as diagnostic history.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
The actual Win32 DbServer now has an opt-in, asset-independent persistence test
entry. It exercises the original container parser, writer, SQL FIFO/worker pool,
reader and template updater with controlled templates and records. PostgreSQL
saves commit before completion; serialization/deadlock retries replay the whole
transaction. Permanent or uncertain failures stop without acknowledging the
failed command. Child/parent deletion is atomic.

All four jobs in the current [regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 21 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild, backup/restore and foreign-key removal against absent tables. The
narrow PostgreSQL guard fixes the fresh-database initialization failure without
changing the preserved source snapshot.

The earlier [20-group implementation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
at `0827ccc992daa7530d9f98d742122238197847df` and
[regression refresh 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
remain historical evidence. The separate normal fixture-OFF DbServer
[startup/export/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed using the accepted schema/runtime pair and a fresh disposable
PostgreSQL database. This exercises normal game-schema initialization in addition
to the controlled persistence fixtures; it does not create or save characters.

**Normal network acknowledgements passed:** [run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
verified creates, an update after restart, and a two-container request held behind
an actual PostgreSQL row lock. No ACK arrived during the 2.078-second observed
write block. After release both rows were committed; an injected COMMIT failure
then produced zero ACKs, preserved the previous row, and stopped DbServer with
exit 3. The normal reference package had fixture mode OFF. The report and all
redacted logs are [preserved](postgresql-evidence/network-ack-36125829311.json).
Batches are not atomic as a whole, and player-session completion is untested.

The latest test drivers distinguish the specific observed benign PostgreSQL
catalog notices from real errors. Both new normal-process gates passed at
`a0ae66d72648d33a7f70b3116d1e1800d9164184` using the accepted `775a0dd...` builds.

Migration 2 adds transactional table rebuilds preserving sequence high-water,
indexes and foreign keys, explicit ASCII case-insensitive name equality, and the
PostgreSQL auction timestamp filter. Stop DbServer, back up and run
`pg_local.py migrate` for an existing development cluster. See the
[persistence design and test scope](POSTGRESQL_PERSISTENCE.md),
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This database milestone does not establish
gameplay; the separate diagnostic APK's current acceptance is recorded above.

**Stage1 asset inspection complete:** `stage1a.pigg`, `stage1b.pigg` and
`stage1f.pigg` have been received. All **14,814 entries** passed archive integrity
and offline structural checks; 5,878 animations and 8,936 textures were staged
separately. All seven startup texture names and MALE/THUMBSUP are present.
Every base-animation reference resolves within `stage1a.pigg`. Preserve warnings
for 216 legacy hierarchy layouts and 193 DDS surplus-byte cases; runtime use
remains unvalidated. See [the stage1 assessment](STAGE1_ASSET_ASSESSMENT.md).
No repeat index run, repeat upload or custom `i26/geobin.pigg` upload is needed.

**Reference runtime refreshed:** [run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed with the exact source pin, PostgreSQL patch and fixture mode OFF at
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
Download `reference-win32-runtime` (artifact `10843979104`) from this run;
it supersedes [the earlier package 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663).
Client, MapServer, DbServer, TestClient, pig and Launcher are packaged with
required supplied DLLs and app-local x86 MSVC runtime libraries. The package
passed hash, PE and dependency checks. The verified base assembly contains
173,011 data files / 2,977,730,517 bytes, with no conflicting donor paths.
The preflight's earlier 173,008 count excluded three additional source-pinned DB
config files added by final assembly. See [current assembly evidence](reference-runtime-evidence/assembly-775.json)
and [reproduction/build instructions](REFERENCE_RUNTIME.md).

Local game execution is blocked by this environment's wineserver IPC restriction.
Use hosted Windows for further runtime validation. The separate data-only schema
patch remains isolated from the reference package and retains error/output
gates. Its incidental caches must not be reused as gameplay caches.

**Data-only schema generation refreshed:** [run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the current reference package. Bootstrap
took 31.468 seconds and strict reload 5.750 seconds, with zero queued errors and
identical bytes for all six attribute maps. All 51 required outputs plus five
dbidmaps are preserved in [the current accepted artifact](schema-generation-evidence/accepted-36088012666.zip).
Every one of these 56 generated payloads is byte-identical to the
[earlier accepted run 36072787971](schema-generation-evidence/accepted-36072787971.zip),
which remains historical evidence. Keep the accepted attribute-ID mappings with
any database initialized from them.

**Normal DbServer schema startup/reload passed:** the first hosted attempt
exposed a fresh-database FK-removal ordering bug. The narrow correction passed
its regression suite and is included in both current artifacts. With that pair,
[run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
completed fresh initialization/export in 13.219 seconds and a second pass in
5.718 seconds. Both exited successfully with no failure diagnostics and produced
fresh empty dumps. Both passes found 99 tables and 58,272 attribute rows
(56,411 general, 1,771 badge-stat and 90 pop-help IDs), with identical catalog
hashes and attribute mappings. Both catalogs contain the verified 5,935 columns,
119 indexes and 734 constraints.
The tested DbServer has persistence fixture mode OFF; its executable SHA-256 is
`fb62028b24bf3165bdcf09e80909d02df5391f89986b9e0454934909a67d93f8`.
See the [downloaded evidence](postgresql-evidence/generated-schema-36125829298.zip)
and [summary](postgresql-evidence/generated-schema-36125829298.json).
The later asset-backed comparison and Atlas Park gate below passed. Complete
serializer semantics, complete asset coverage and character gameplay remain
unvalidated.

**Normal templates and Atlas Park readiness passed:**
[run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
used the accepted reference/schema pair and all 16,721 reviewed binary assets.
Ordinary `MapServer -templates` freshly reproduced **56/56** accepted files
byte-for-byte in **25.89 seconds**. A separate fresh runtime, without comparison
caches, then started normal DbServer and Atlas Park against PostgreSQL. Independent
DbServer status queries confirmed the initial not-started state and subsequent
ready state with continuing updates for **62.235 seconds**. Both reports have
empty failure lists. Preserve the [comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json),
[comparison artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip),
[map report](postgresql-evidence/one-map-36176806895.json),
[map artifact](postgresql-evidence/postgresql-one-map-36176806895.zip) and
[accepted gate identities/hashes](reference-runtime-evidence/accepted-gates-36176806895.json).
The normal executable does not report queued startup error counts; these gates
do not establish complete assets, character login/persistence or gameplay.

## Completed

- All 5,995 source files verified; exact-commit upstream Windows build and nine
  utility/archive/codec tests passed, as previously audited.
- Imported the entire `Thunderspies/i24` tree at
  `d51533ec8e6a9cf726b9214968077a05fdcf19f3` under `upstream/i24`: 156,297 files,
  1,992,097,492 bytes, no exclusions. Local and hosted integrity/tree checks passed.
  Import commit: `1768775ab3608cdd852ec7119bbf0139a91248c6`.
- Added `content-lock.json`, data inventory and per-file manifest. The importer
  and verifier accept `--lock content-lock.json`; existing source defaults remain.
- Added the exact 72-archive upstream catalog and portable `content_assets.py`
  probe/fetch/record/verify tool. Receipt checks detect changed/missing bytes.
- Added `prepare_runtime.py`; full text-only staging passed. It keeps imports
  immutable, fixes `Game.exe` to `CityOfHeroes.exe` in staged launchers and uses
  source-pinned configs. It accepts extracted asset data and exact-pin build
  outputs separately; it does not execute programs or install SQL.

## External content result

The user's `small_i26_piggs.zip` has now been inspected: all **17 archives /
8,864 entries** passed size, decompression, MD5 and cached-header checks.
**549 compiled files use Parse7; the pinned source expects Parse6**, so these
caches cannot be reused unchanged. Staged **665 candidate binary assets**
(141 geometry, 445 textures, 79 audio files; 152,755,341 bytes) separately,
with runtime compatibility still unverified. No raw client binaries/assets were
published. The original ZIP plus the new portable inspector reproduce staging.
See [client content assessment](CLIENT_CONTENT_ASSESSMENT.md) and its
[per-archive hashes/counts](client-content-assessment.json). Eight inspector
regression tests passed in that initial pass.

The subsequent **`geomBC.pigg`** also passed: 1,232 entries, comprising 584
geometry files and 648 Parse6 caches. All geometry files use versions accepted
by the source and passed compressed-header/data-bounds checks; meshes/collision
and runtime loading are untested. Staged geometry separately under
`imports/base-geomBC-candidate-assets`. Cumulative result: **18 archives,
10,096 verified entries, 1,249 distinct candidate assets / 318,908,734 bytes**.
The inspector now records geometry header checks; eleven regression tests pass.
See [base geometry evidence](base-geometry-assessment.json).

The later `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg` batch also
passed: **2,774 additional entries**. Cumulative result is now **22 archives /
12,870 entries / 2,487 distinct candidate asset paths**, with two conflicting
custom/base geometry variants kept separately. All 46 fonts are staged, including
TTC collections; every one of the 16 startup font filenames is present. All
1,277 new geometry headers passed. `misc.pigg` mostly duplicates the pinned text.
At that earlier stage there were **zero skeletal .anim tracks** in the supplied
set and none of seven requested basic renderer texture names. The subsequent
stage1 uploads below supply those candidates; runtime startup remains untested. See [asset coverage history](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

The subsequent **`coh-asset-index.json`** has now been received from Thor and
preserved as [thor-asset-index.json](thor-asset-index.json). It reports 73 base
archives and 22 custom-folder archives, with 96,379 entries across those tables
(not deduplicated). Base `stage1a.pigg` lists 5,878 animation tracks, including
MALE/THUMBSUP; `stage1b.pigg` and `stage1f.pigg` list all seven startup texture
names. This locates candidates on the device; it does not add to the 22
payload-verified archives or establish source-format/runtime compatibility.
The indexer previously matched full-inspection counts/extensions for all 22
available archives; thirteen regression tests passed in that earlier pass.

The three selected **stage1 archives** then passed integrity and offline format
checks. Cumulative payload-inspected count: **25 archives / 27,684 entries**.
New staging contains 14,814 distinct paths within the batch and 654,699,284 bytes;
its overlaps with earlier custom assets have not been recomputed. The 20 new
format/staging tests passed. All animation base references resolve, including
the fallback, and all seven startup textures pass structural checks. Native
ARM64 needs explicit decoding of 32-bit animation records; the renderer must
handle the observed DDS formats. Runtime compatibility remains untested. See
[stage1 evidence](stage1-assets-assessment.json) and the
[reproducible checks](STAGE1_ASSET_ASSESSMENT.md#reproduce-without-windows).


[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The original fallback was an accessible compatible archive/mirror/magnet or
existing asset folder; the user has since supplied the targeted assets above.
No additional broad asset upload or Windows VM is required for this assessment. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation priority and remaining scope

The accepted device build is [COH Server Test 0.2.0](ANDROID_SERVER_DEVICE_TEST.md),
installed alongside 0.1.5 as `io.github.russianranger.cohdiagnostic.m3`.
It packages the exact accepted M2 payloads and qualified loopback DbServer donor
`36460867428`, with a device policy enabling loopback for every DbServer process
and fixed inputs for both normal schema launches. The original Atlas donor is
not changed. Each real test has disposable state and each operation an immutable
support ZIP. The candidate workflow builds the APK and runs its exact packaged
guest/bundles on hosted ARM64 with the device policy. All three jobs and all 28
runtime stages passed in
[run 36483331900](https://github.com/Russianranger/coh-android/actions/runs/36483331900)
at `f7dbba42ec29a1c054d856d71810146f5b53bac6`. Tooling passed 233 checks with eight
Windows-only skips. The APK is 16,668,615 bytes, SHA-256
`cb5cf453af1b81cbaa02917a6d7cb55ab8b8f2a910a46b0a85f4ae399883188b`.
The [candidate receipt](android-evidence/accepted-device-candidate-hosted-36483331900.json)
binds the build, independently checked APK payloads and hosted reports.
The [physical Thor receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two full passes in 325.763 and 338.326 seconds, surrounding a clean Stop
during active Wine setup. Both passes verified 14 local endpoints, all 21 fixture
groups, both schema passes and all 111 closed process captures. The stopped run
closed all 22 captures and correctly reported cancellation. All three ended with
zero owned processes and inspection failures. App switching and screen locking
are user-attested; peak memory is unmeasured. The subsequent hosted Atlas loopback
integration passed in `36493722153`, preserving the earlier accepted default.
MapServer/client local bindings then passed Windows and hosted ARM64
qualification in `36510836956`. Verified asset import and separate Android
Atlas runtime/lifecycle integration are next; none of these hosted results
establish physical Atlas acceptance.

**The primary M2 device diagnostic, hosted M3 DbServer and hosted Atlas
create/save/restart/resume/second-save sequence are accepted.** The Atlas
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
records the successful full workflow `36460005201`, including the final host
validator. Preserve the earlier `36454174481` workflow failure and its separate
post-correction acceptance.
The isolated Wine-compatible DbServer fixture
and normal schema startup/export/reload have passed; preserve their
[accepted evidence](android-evidence/accepted-dbserver-hosted-36369485666.json).
The current fixed-input DbServer successor is also
[qualified](android-evidence/accepted-dbserver-hosted-36451873322.json).
Keep default donor `36451873322` and retain both DbServer
activation acknowledgments and all four schema/configuration snapshots.
Enabled ARM64 dispatch publication was already verified in run `36428915900`.
The separate sibling DbServer failure remains unexplained despite the successful
byte-identical repeat; retain both receipts and the qualified donors.
The separate loopback listener package is
[hosted-qualified](android-evidence/accepted-dbserver-hosted-36460867428.json)
in run `36460867428` and accepted for the explicit Atlas loopback profile in
`36493722153`; the historical default donor is retained. Preserve its earlier
CRLF fixture-setup failure and correction. The 0.2.0 device results accept this
listener package and Stop/rerun handling on Thor. The separate
[hosted game listener receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
accepts both MapServer starts and both TestClient sessions with actual local
UDP bindings and the complete persistence sequence. Its opt-in donor profile
preserves the historical defaults and accepted device APKs.
Keep the existing 0.1.5 and 0.2.0 APKs and runtimes. See the
[concrete next steps](THOR_DEVICE_ACCEPTANCE.md#next-work).
Peak memory remains unmeasured. The following items preserve
completed reference gates; no repeated Windows-only milestone is needed.

1. Preserve the accepted results from corrected manual [asset run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895).
   It passed ordinary template comparison and Atlas Park readiness with schema
   run `36088012666`, reference run `36088012664`, asset `588984151` and
   `run_one_map=true`. No rerun is needed to establish those completed gates.
   Upload is complete: unpublished draft release
   `396839391` contains the accepted **615,541,018-byte** ZIP, SHA-256
   `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`.
   Ignore incomplete asset `588979946`. No repeat PIGG or ZIP upload is needed.
   The initial manual [run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
   failed during download before any game process, suspected to be the draft
   release's rejection of the read-only token. Its HTTP status was not logged.
   [Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
   scopes `contents: write` to the manual comparison job; global/tooling tokens
   stay read-only. It also adds safe numeric HTTP status and stage diagnostics;
   all 12 downloader tests and [tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
   passed. [Run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
   then successfully downloaded and verified the exact ZIP, confirming hosted
   draft access. It failed `Manifest must use canonical JSON` before game
   execution: Windows checkout changed the manifest's LF bytes to CRLF.
   [Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
   marks `assets/reference-inputs-*.json -text`; a temporary Git checkout with
   `core.autocrlf=true` reproduced the accepted canonical bytes, and
   [tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
   passed. The successful manual run used that fix. The release remains unpublished
   and raw assets are not uploaded as Actions artifacts. See the
   [concrete handoff](NEXT_SERVER_VALIDATION.md) and
   [transfer evidence](reference-runtime-evidence/asset-transfer-20260925.json).
   The matching reference package and coherent base assembly are ready. Preserve the accepted attribute-ID mappings; do not
   substitute the separate schema executable or its incidental caches for the
   reference runtime.
2. Preserve the accepted [character persistence result](CHARACTER_PERSISTENCE_VALIDATION.md#accepted-hosted-validation-36282414135).
   Fake-auth creation, live currency change, explicit logout, committed SQL,
   same-cluster/service restart and exact-name short resume have passed.
   The [sustained resume and second-save result](SUSTAINED_SESSION_VALIDATION.md#accepted-hosted-validation-36295176484)
   has also passed, including missing-name refusal without mutation. Preserve
   the separate diagnostic TestClient receipts alongside the stock reference.
   The [Atlas round trip](MAP_TRANSFER_VALIDATION.md) has also passed with
   independent destination identity, fresh player updates, current heartbeats,
   live currency and a final committed protocol save. New-zone assets, mission
   transfers and automatic Launcher startup remain unvalidated.
   Separate remaining server work includes player-session completion callbacks, game-level
   name uniqueness and auxiliary-service persistence. Generic-container network
   ACK ordering is now verified. Fake auth is only the minimal local diagnostic route; no SQL
   Server save migration has been attempted. Empty-database startup/export and
   controlled persistence fixtures do not establish these gameplay behaviors.
3. Generate further server/client caches with the bounded harness when the runtime
   has the required graphics. Resolve legacy animation hierarchy/DDS warnings
   through reference runtime use. Keep custom variants separate and request
   further archives only when runtime evidence identifies a concrete missing
   input. The older upstream v2i3 release is not the locked build; use the current
   reference artifact.
4. Keep the accepted 0.1.5 and [0.2.0 server](ANDROID_SERVER_DEVICE_TEST.md)
   installations. The real DbServer, Stop/rerun and requested background checks
   are complete within their documented evidence scope; do not request another
   run of these passed diagnostics. Peak memory remains unmeasured.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. The current APK status is recorded
in [ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md); gameplay remains unvalidated.
