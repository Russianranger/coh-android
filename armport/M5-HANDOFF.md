# COH-ArmPort M5 handoff: from a playable ARM64 client to an optimized client/server

Written 2026-10-28 at the end of the M5 Thor iteration (PR #8, branch
`armport/m5-thor`, head after this file). All scheduled checks were cancelled
at the user's request. The historical measurements below describe that handoff.

## Latest device result and pause — 2026-11-02

**Development is paused at the user's request.** Record and diagnose only;
do not treat this handoff update as authorization to resume implementation,
dispatch CI, hand off an APK or request acceptance.

The user reports: **“Kings row is still functioning poorly, worse than before
the arm port.”** This remains an M5 experience/acceptance failure. The supplied
exports are `coh-atlas-gameplay-20261103-010459.zip` (gameplay) and
`-010516.zip` (setup only). Both identify **0.13.44**; this is not a test of
the .45/.46 changes and is not an ARM64-versus-x86 gameplay comparison.

Measured in this session:

- Tap to connected: **604.299 s**; client folder scan **217.712 s**.
- Atlas → King's Row: **656.024 s cold preparation**, **54.908 s transfer**,
  **711.056 s request to observed arrival** (about 11 min 51 s).
- Once loaded, eleven complete King's Row render windows cover 55.53 s:
  **19.95–29.94 FPS**, **25.63 FPS weighted**. This does not measure NPC/update
  smoothness or establish the server tick rate.
- Both maps still use the retained **x86 MapServer** under the translated runtime;
  Atlas remains resident. Preparation records large destination RSS growth and
  system-wide swapping; contention is plausible but not proven as the cause of
  post-arrival stutter.
- Save after returning to Atlas committed with character state preserved.
  Overall session failed at owned cleanup: repeated worker-environment EACCES,
  with cache return blocked. A linked private-cache observation also failed.
- No server tick/file-duration samples, gameplay CPU deltas, thermal data or
  matched pre-port run establish the precise regression cause.

Detailed evidence, caveats and source locations:
[2026-11-02 Thor results](notes/M5-THOR-20261102-RESULTS.md) and
[evidence summary](evidence/20261102-thor-results.json).
Do not turn the earlier “server-side” hypothesis into a confirmed diagnosis.

## Published candidate state — read-only reconciliation

0.13.45/code 60 at `0bf31c81b` passed build 40776745390, retained-runtime
requalification 40786315414 and APK 40791416254. Claude review 5692088051
approves artifact 12860779714 for handoff. There is no .45 device result here.

The P2/P3 sampler fixes, launch-history groundwork and Windows packaging fixes
are published separately on `armport/sampler-review-fix` at
`8dc2a66d72477b3c62227e572538b13f0e4f912b`. Its **0.13.46/code 61** chain
completed successfully: build **40929292200**, retained runtime **40945708189**,
APK **40952408285**. Claude comment **6508052528** reports artifact
**12931682996** and explicitly says these are CI results, not review approval.
The Thor server variant was built/source-checked; retained CI executes a
different server lineage. There is no .46 Thor validation or newer formal
handoff approval on PR #8. Do not hand off that APK on the basis of CI alone.

Build 40805020119 at `dd9d755bd` is historical: nine jobs passed, then its
Windows host import of fcntl failed before MSVC. The corrected chain above
supersedes that failure; do not retain “running” as its state.

Separate startup research branches exist (`armport/mapserver-startup-60s` and
`armport/mapserver-modern-runtime-qualification`). The supplied reports do not
test them. This session made no implementation changes or CI requests.

## Lead audit correction (2026-10-28)

The historical measurements below are retained as the previous lead's report;
raw Thor exports were not independently recovered in this checkout. The source
and all PR reviews/comments were audited in PR comment 6480628043, mirrored in
`notes/M5-ASTRA-ANALYSIS.md`. Apply these corrections to the next steps:

- `seqGetSeq` prints “Reading” before its hash lookup; these counts do not prove
  repeated file loads. Startup already calls `seqPreloadSeqInfos`. Instrument
  actual load paths before adding another preload.
- The Java validator already supports ARM64. The confirmed false rejection is
  a manual session emitting `bounded_live_observation=false` while the caller
  demanded true. Correct the policy while retaining session and Finish checks.
- DbServer's 64 SQL workers block on semaphores. 67 threads do not establish 64 polling
  workers. CPU totals do not measure Wine request counts or identify a hot thread.
- Smooth player prediction plus remote stutter supports a server/update-path
  hypothesis; longest tick, file-load duration and request counts are not measured.
- 0.13.45 first adds bounded host tick-counter/CPU observations and honest cleanup
  errors. A separate native timing producer/package follows; no esync change yet.

## Historical device snapshot — 2026-10-28

**0.13.44 on the AYN Thor is playable on the ARM64 client.** The user's exports
of 2026-10-28 (`coh-atlas-gameplay-20261028-202049` with zoning,
`-203539` with the second launch, `-202106` setup only) show:

| Area | Result on Thor | Evidence |
|---|---|---|
| Login, reopen THORHERO, Atlas Park | Works | both reopen exports |
| Frame rate | Game 12-30 FPS in gameplay, mean 22.8 over 227 five-second windows (cap 30); was 6-12 before patch 0116 | `ARMPORT_FRAME_RATE_V1` in `armport_stdio.txt` |
| Combat, hit/miss messages | Works; no `Bad parameter` lines | 0 matches in both exports (patch 0117) |
| Defeating enemies, play afterwards | Works; no crash | no `Unhandled` fault; client exit 0 on the second launch (patch 0118) |
| Zoning (monorail Atlas → King's Row → Atlas) | Works; client side about 18-23 s per zone load | `character-zoning.json` status `arrived`, epochs 1 and 2 |
| Save/logout | Works on the second launch (committed save observed) | `-203539` |
| **NPCs and cars in King's Row** | **Stutter forward; the player is unaffected** | user report; see below |
| Warm startup | About 12 minutes from tap to connected (target was under 5) | stage times below |

Candidate: `COH-Atlas-Gameplay-0.13.44.apk`, sha256 `2cf80a03…5c1b`, artifact
12840043807 (APK run 40743596575, build 40724321192, requalification
40736589404), approved for handoff by Astra (review 5687848443). Code reviews:
Astra approved 0115-0118 (5686257096). M5 completion and merging PR #8 are not
yet approved. Releasing anything needs the user's approval.

## What 0.13.38-0.13.44 fixed (all 64-bit or ARM64-runtime defects)

| Patch | Defect on Thor | Fix |
|---|---|---|
| 0107-0109 | Kicked to login during Atlas load; 99 s texture-header reads; software renderer only | PID window title, quiet trace, texture-header index, GPU (Turnip/Zink) option |
| 0110 | Crash entering Atlas (SMF anchor pointers kept in an int stack) | per-set anchor pointers, int indices |
| 0111 | Unmeasured startup | folder-cache phase timing; change monitor skipped for fixed data |
| 0112 | Crash opening graphics options (`initializeShadowInfo`) | VBO rebase in `intptr_t` |
| 0113 | 10 FPS gameplay cap | 30 FPS with the GPU profile |
| 0114 | No game-side FPS evidence | `ARMPORT_FRAME_RATE_V1`, CRT-isolated |
| 0115 | Combat crash reading `3FFC000000000000` | 8-byte variadic slots in `msGetTypeDefPointers` |
| 0116 | Game rendered 6-12 FPS: render worker paid wineserver round trips per command | poll up to 2 ms before sleeping; atomic counters; `ARMPORT_WORKER_V1` |
| 0117 | `Bad parameter … powerName` | pointer-sized message definition indices |
| 0118 | Crash writing `0x38` in `mat3ToQuat` after a defeat | ARM64 reads and discards ragdoll packets (no PhysX); NULL-checked creation |

App/Java side (shared app, reviewed files only): hardware-canvas drawing with
one canvas mode per Surface, chunked Raw RFB decode, delivered-frame and decode
timing (`presentation_timing`). Harness: OCR creator transition checks and the
ARM64 observer validator.

## Findings from the last exports

### NPC and car stutter in the second zone — cause unmeasured

The previous lead inferred server/update-path stutter from smooth predicted
player movement and jerky remote entities. The 2026-11-02 user report confirms
poor King's Row experience, but neither report establishes the exact cause.

Both maps run x86 MapServers under the translated Wine/PRoot stack, and Atlas
remains resident after transfer. This is a plausible source of contention.
The prior 478 s wineserver and 428 s DbServer system-time figures were cumulative
capture totals, not request counts or identified hot-thread measurements.
Not every Wine wait necessarily sends a wineserver request. DbServer's 64 SQL
workers normally block; thread count alone does not prove polling.

Sequencer “Reading” output precedes the cache lookup and does not prove a disk
load. Startup already preloads sequencer definitions. Measure actual file work
before attributing stutter to those messages or adding another preload.

The new export shows roughly 25.6 rendered FPS over a short loaded King's Row
interval, while the user still reports poor play. This supports investigating
simulation/update timing separately from rendered frames. Native longest-tick
and file-load time, gameplay CPU and a matched pre-port baseline remain missing.
See the dated results note for preparation-only memory/pressure observations.

### Startup (about 12 minutes warm)

Second launch (`-203539`), from tap at 20:21:32:

| Stage | Time | Notes |
|---|---|---|
| Wine, ODBC, DbServer | 20:21:41-20:22:30 | about 1 min |
| **Atlas MapServer** | 20:22:31-20:32:05 | **9.5 min**; "Server ready (took 287 s)" inside it |
| Client data stages | 20:27:09-20:28:12 | started 4.5 min late; launch 1 started them at once (19:41) |
| Client startup | 20:28:28-20:32:18 | includes the folder scan: 212,496 files, 142 s (156 s on launch 1) |
| Connected | 20:33:17 | waits for the MapServer |

The x86 MapServer under FEX is the critical path. The client already overlaps
with it, so the folder scan only matters once the server is faster.

### Harness false failures (the game was fine)

- `-202049`: "saved enhancements changed": defeats awarded enhancements, and the
  strict same-session inventory check refuses any change (as it did for
  temporary powers before 0.13.40). Also "Owned cleanup failed: Atlas data cache
  return lacks proved owned Wine cleanup" after zoning.
- `-203539`: guest passed and the save committed, but the app reported
  "current-session client evidence did not match this APK". The Java check
  expects the x86 client's evidence and does not know the ARM64 lane.

## Historical future-work plan — paused; apply audit corrections first

### 1. Measure the servers (small, do first)

- Add a MapServer tick log equivalent to `ARMPORT_FRAME_RATE_V1`: ticks per
  5 s, the longest tick, and time spent in file loads, keyed by map id. The
  MapServer is the app's x86 build; add it through the same patch series and
  build the i686 server from it, or as an app-side producer if the server
  binaries must stay pinned. Check with the reviewers which one is acceptable.
- Log per-process CPU deltas per window for client, DbServer and each MapServer
  using periodic `/proc` samples. Wine request counts require separate protocol
  instrumentation; CPU counters do not supply them.
- Repeat the King's Row test with Atlas stopped after the transfer, to separate
  "two MapServers" from "wineserver contention" from "on-demand loads".

### 2. Cut server-side cost without changing architecture

- **Stop or idle the previous zone's MapServer** once the transfer is
  confirmed, keeping reopen overlap only for the zone being entered. This is
  a hypothesis to test for second-zone stutter, not an established cause.
  Preserve character save, process ownership and safe restart requirements.
- **Measure actual post-ready definition loads** before changing preload.
  Startup already calls `seqPreloadSeqInfos`; “Reading” messages do not prove
  disk I/O. Any additional preload requires evidence of a missed load path.
- **Investigate the historical DbServer system-time totals**:
  measure per-thread CPU and wait paths first. The 64 SQL workers normally
  block; neither the thread count nor cumulative CPU proves polling.
- **Wine synchronization:** esync (wine-staging; eventfd and shared memory,
  available on Android kernels) would remove most wineserver round trips for
  all four processes at once. ntsync needs `/dev/ntsync`, which Android does
  not provide. Changing the Wine build changes the pinned runtime
  (`android/runtime-lock.json`) and needs a new runtime qualification.

### 3. Native ARM64 servers (the main structural win)

The user deferred this until the client ran; it now runs. Building DbServer
and MapServer for ARM64 Windows with the same toolchain and patch series as
the client removes FEX from the servers entirely: startup (9.5 min critical
path) and NPC update rate both depend on it. Expect the same class of 64-bit
defects the client had (pointer truncation, varargs, ints holding pointers,
packed indices). Reuse the client workflow: patchwork patches, CI
positive/negative checks extracted from real source, symbolized device faults.
Start with the server's message store and anything that shares code with
0110/0112/0115/0117, since those fixes apply directly.

### 4. Startup after the server is faster

- Persist the client folder cache for the fixed data tree (142-156 s scan of
  212k linked files under PRoot) and reuse it while the tree identity is
  unchanged, like the texture-header index (0109) and the link validation
  receipt.
- Restore the launch-1 ordering so client data stages always start alongside
  the MapServer (launch 2 started them 4.5 minutes late).
- Keep the servers warm between sessions when the app stays open.

### 5. Harness and app fixes before M5 acceptance

- Accept server-awarded enhancement additions in the ARM64 strict inventory
  check, as for `temporary_powers`: added items only, every prior item kept.
- Teach the app's current-session evidence check about the ARM64 lane.
- Make post-zoning Wine cleanup prove ownership for every MapServer started.

### 6. M5 acceptance and merge

Run the documented Thor test on the candidate that contains steps 1, 2 and 5:
two launches, combat with several defeats, play after the last defeat, one
monorail zone change, save/reopen, with both exports. Then request M5
acceptance and merge approval for PR #8 from Sol/Astra and the user. The x86
client stays the default; the ARM64 client stays "experimental" until the
servers are fixed.

## Working rules that applied (keep them)

- Never edit `upstream/`; native changes are patches made with
  `armport/scripts/patchwork.py` (init, commit, export).
- At most two compiler processes; ARM64 and i686 builds run sequentially. No
  competing CI: build → `armport-app-runtime` requalification
  (`client_run_id`/`data_run_id` = the build) → `armport-thor-apk`
  (`m4_run_id` = the requalification), one at a time.
- `STATUS.md` stays at most 40 lines with run/command evidence.
- Hand an APK to the user only after reviewer approval; read every review and
  issue comment on PR #8, including ones posted before your request.
- No protected-branch changes, history rewrites, secret or signing misuse;
  releases need the user's approval.
- Inspect actual Actions logs/artifacts when accessible; distinguish annotations
  from independently downloaded evidence. Use `armport-symbolize.yml` (`run_id`,
  exe `sha256`, `addresses`) for device fault addresses (image base 0x140000000).
- Thor exports: `guest-report.zip` → `client-evidence/armport_stdio.txt`
  (FPS, worker and folder-cache lines, zone markers), `client-console.log`
  (faults, exit), `character-zoning*.json`/`-console.txt`,
  `owned-processes.json` (per-process CPU).
