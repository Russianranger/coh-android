# COH-ArmPort M5 handoff: from a playable ARM64 client to an optimized client/server

Written 2026-10-28 at the end of the M5 Thor iteration (PR #8, branch
`armport/m5-thor`, head after this file). All scheduled checks were cancelled
at the user's request; nothing is running or waiting in CI.

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

## Where things stand

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

### NPC and car stutter in the second zone (server-side)

The player moves smoothly because the client predicts its own movement; NPCs
and cars move only as fast as the King's Row MapServer sends updates. The
evidence points at the servers, not the client (client 12-30 FPS throughout):

- **One wineserver serves everything** (client, DbServer, two MapServers), and
  PRoot traps every syscall on both sides. At capture, `wineserver` had 478 s
  of system time and `DbServer.exe` (67 threads) 428 s, more than the client's
  317 s. Wine 10 here has no esync/fsync/ntsync, so every wait, event and
  mutex is a wineserver request.
- **Two x86 MapServers ran under FEX at the same time.** Atlas stays up after
  the player leaves (by design: the reopen overlap). King's Row used 233 s of
  CPU in its first ~15 minutes, much of it the 259 s startup.
- **Both MapServers load sequencer definitions on demand while playing**:
  repeated `Reading player.txt`, `Car_Compact.txt`, `zombie.txt`, `BF.txt` as
  NPCs and cars appear. That is 4,035 reads after ready in King's Row and 2,476 in
  Atlas (`character-*-console.txt`). Under FEX and PRoot each read can stall a
  server's main loop. Because Atlas also does it without visible stutter, this
  alone does not explain the second zone. The difference is that King's Row ran
  while Atlas was still up, and King's Row has more traffic (cars) to read.
- **Not measured:** the King's Row server tick rate. The only tick counts are
  14 at King's Row ready and 46,749 for Atlas at 20:13:44 (roughly 30 ticks/s
  averaged since its start, assuming about 6 minutes of startup). A per-window
  tick log is the first thing to add.

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

## Next steps, in order

### 1. Measure the servers (small, do first)

- Add a MapServer tick log equivalent to `ARMPORT_FRAME_RATE_V1`: ticks per
  5 s, the longest tick, and time spent in file loads, keyed by map id. The
  MapServer is the app's x86 build; add it through the same patch series and
  build the i686 server from it, or as an app-side producer if the server
  binaries must stay pinned. Check with the reviewers which one is acceptable.
- Log per-process CPU and wineserver request counts per window for client,
  DbServer and each MapServer (a periodic `/proc` sample from the guest
  runner is enough).
- Repeat the King's Row test with Atlas stopped after the transfer, to separate
  "two MapServers" from "wineserver contention" from "on-demand loads".

### 2. Cut server-side cost without changing architecture

- **Stop or idle the previous zone's MapServer** once the transfer is
  confirmed, keeping reopen overlap only for the zone being entered. This is
  the most likely cause of the second-zone-only stutter, and the cheapest to
  test.
- **Preload sequencer and entity definitions for every supported zone** at
  MapServer start (or ship them in the server-animation/server-cache packs that
  already exist for Atlas), so nothing is read from disk while playing.
- **Find why DbServer burns 428 s of system time** with 67 threads at idle:
  probably polling waits that each cost a wineserver round trip. Treat it like
  0116: find the waits, bound polling or lengthen timeouts.
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
- From the cloud session, Actions logs and artifacts cannot be downloaded (the
  proxy blocks the storage host). Use check-run annotations, and
  `armport-symbolize.yml` (`run_id`, exe `sha256`, `addresses`) for device
  fault addresses (image base 0x140000000).
- Thor exports: `guest-report.zip` → `client-evidence/armport_stdio.txt`
  (FPS, worker and folder-cache lines, zone markers), `client-console.log`
  (faults, exit), `character-zoning*.json`/`-console.txt`,
  `owned-processes.json` (per-process CPU).
