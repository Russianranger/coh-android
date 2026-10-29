# COH Atlas Gameplay 0.13.45: CI-qualified candidate (ARM64 client)

**Approved for Thor handoff by Claude, review [5692088051](https://github.com/Russianranger/coh-android/pull/8#pullrequestreview-5692088051).** VersionCode 60, tested source
`0bf31c81b1b5a9f8427b4692c623702b30e7029e`. All three serialized CI stages passed.
0.13.44 below remains the last device-tested candidate. This documentation update
does not change the tested code. M5 acceptance and merge are not requested.

| Item | Exact evidence |
|---|---|
| Native build | [40776745390](https://github.com/Russianranger/coh-android/actions/runs/40776745390): all 8 jobs passed; Release/OptDebug reused clients with matching inputs |
| Runtime requalification | [40786315414](https://github.com/Russianranger/coh-android/actions/runs/40786315414): all 4 jobs passed; client/data inputs both 40776745390 |
| APK run | [40791416254](https://github.com/Russianranger/coh-android/actions/runs/40791416254), input `m4_run_id=40786315414` |
| Artifact | `coh-atlas-gameplay-0.13.45-apk`, ID 12860779714 |
| ZIP SHA-256 | `2e27321c4097a71e5d9a135642794973cefc0d6eed9f022c1eb27a6262493efb` |
| APK | `COH-Atlas-Gameplay-0.13.45.apk`, 80,919,462 bytes, version 0.13.45 / 60 |
| APK SHA-256 | `1ff2252876def6cfeb28d33490d8c2f5d5952c330698d6a719fb67a2197b3959` |
| ARM64 package SHA-256 | `caf54a9aea9e5fcb479ff651b25892e5a731f1300f44fa8e43401341bd21c0c8` |
| ARM64 executable SHA-256 | `2caf815fc2262399440af333512cec3d83bf69ce43fc3a6d44ba35b21f67db6e` (unchanged from 0.13.44) |
| Native patch tree | `992ed11b116a2db10179c8507ce61e3f37b27840` |

CI provenance notice: `package run 40786315414, client run 40776745390 at 0bf31c81b1b5a9f8427b4692c623702b30e7029e, armport/patches tree 992ed11b116a2db10179c8507ce61e3f37b27840 matches 0bf31c81b1b5a9f8427b4692c623702b30e7029e`.

The downloaded ZIP/APK hashes, APK v2/v3 signatures and complete content digest,
binary manifest, 377 inner file pins, 75 packaged runtime pins and 67 packaged
client pins were independently checked. The retained signer is
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
Raw runtime ZIPs, the donor APK and 19 external assets were not independently
downloaded. See [qualification evidence](evidence/0.13.45-qualification.json).
The interactive guest reported `passed=true`, `m4_complete=false`, elapsed
2214.441 seconds, and no error. This is retained 0.10 runtime qualification,
not execution of the full Android 0.13.45 runtime or device acceptance.

Changes: five-second cooperative `server-metrics.jsonl` tick-counter and CPU
samples (50 ms collection budget, 4 MiB cap, partial/unavailable markers); the Java
manual-session policy now matches the guest's emitted flags and still requires
completed interaction and Finish; cleanup retains the original Wine failure
alongside any cache-return failure. Native patches/runtime/server pins unchanged.
The “server side” explanation below is an inference; no measured King's Row tick
rate or Wine request count is available. Sequencer “Reading” lines are cache
lookups, not proven disk reads. See `notes/M5-ASTRA-ANALYSIS.md`.

Local validation: 292 tests pass with `python3 -m unittest discover -s armport/tests
-p 'test_*.py'` and a javac launcher for the installed Java compiler module.
Native longest-tick/file-load time and Wine request counts explicitly remain
unavailable in this candidate. No 0.13.45 Thor behaviour is established yet.

Reviewer reproduced a sampler liveness defect: a new-zone PID at a budget
boundary can be missed repeatedly. Local 292-test success depended on directory
order; Claude's run passed 291/292 and exposed that defect. A deterministic retry
fix is required before the next candidate. Missing King's Row telemetry must
remain unknown; it is not evidence that its server was idle or stopped. The
review also identified a costly whole-registry copy being corrected separately.

Install this approved diagnostics APK over the current app without clearing data.
Keep the same ARM64/GPU profile and saved character for both launches:

1. Launch the saved character, wait in Atlas for at least 30 seconds, then take
   the monorail to King's Row. Observe NPC/car movement there for at least 60
   seconds before returning to Atlas. Include combat and defeats; record any
   enhancement award rather than avoiding the known harness limitation.
2. Use Save/Logout and Finish, then export the report even if a harness check
   reports failure. Reopen the same character, repeat the route, save and Finish,
   and export again. These are cold/warm comparisons only if cache state supports
   that description; record which launch the export belongs to.
3. Each `guest-report.zip` must retain `client-evidence/server-metrics.jsonl`,
   `armport_stdio.txt`, `client-console.log`, stage logs, zoning consoles and
   ownership/cleanup receipts. Confirm telemetry schema and sample coverage
   before computing CPU/tick rates; retain partial/unavailable markers. Explicitly
   check whether a MapServer row with map_id 5 appears after zoning; report its
   absence without repeating a long test solely to obtain that row.

Enhancement additions and the underlying post-zoning cleanup failure remain
open. This candidate must report those failures accurately. The experimental
enhancement policy and native patch 0119 are not included in this APK.

---

## Last device-tested candidate: 0.13.44

**Status:** 0.13.44 approved for Thor handoff (Astra 5687848443) and played on
Thor 2026-10-28: combat, defeats, zoning and save work; game 12-30 FPS (mean
22.8). Open: NPCs and cars stutter in the second zone (server side), warm start
about 12 minutes. Next steps: `armport/M5-HANDOFF.md`. M5 is not complete.

| Item | Value |
|---|---|
| APK | `COH-Atlas-Gameplay-0.13.44.apk`, versionCode 59, 80,911,192 bytes |
| APK sha256 | `2cf80a03a0161fc42581147f0c75d8f22ea2ad93fc8884c9abab5c72388e5c1b` |
| Built by | run [40743596575](https://github.com/Russianranger/coh-android/actions/runs/40743596575) at `a5bd2bbe3`, artifact `coh-atlas-gameplay-0.13.44-apk` (12840043807) |
| Signer / app ID | retained `92955353…c282`, `io.github.russianranger.cohclientinteractive` (same as 0.13.36 to 0.13.43) |
| ARM64 client | executable `2caf815f…db6e`, package `bba31da1…52bf`, from build 40724321192 at `a5bd2bbe3` (patches to 0118; provenance: `armport/patches` tree `992ed11b` equals the APK head's) |
| CI qualification | build 40724321192: all 8 jobs passed, including the 0117 index check and the 0118 ragdoll check (upstream code fails both). Requalification 40736589404: ARM64 creation then reopen passed (2177 s). Retained 0.10 runtime; the full 0.13.44 runtime has not run in CI |

## 0.13.44 on Thor (exports 20261028-202049 zoning, -203539, -202106 setup)

| Check | Result |
|---|---|
| Combat, hit/miss lines | Works; no `Bad parameter` lines (0117) |
| Defeats, play afterwards | Works; no fault, client exit 0 on launch 2 (0118) |
| FPS | 12-30 in gameplay, mean 22.8 over 227 windows |
| Monorail Atlas → King's Row → Atlas | Works; client 18-23 s per zone |
| NPCs and cars in King's Row | Stutter; the player is smooth. Server side: wineserver 478 s and DbServer 428 s system time, two x86 MapServers at once |
| Warm start | About 12 min; Atlas MapServer 9.5 min on the critical path |
| Harness | False failures: enhancement additions after defeats, ARM64 evidence check in the app, post-zoning cleanup proof |

## What changed from 0.13.43 (Thor report, exports 20261028-160515/160528)

| 0.13.43 result | Cause found in the exported report | 0.13.44 change |
|---|---|---|
| FPS much better: game 15-27 FPS in Atlas (was 6-12) | Patch 0116 works: the render worker now mostly polls instead of sleeping (spin hits above sleeps) | Unchanged |
| Combat worked, but hit/miss texts showed `Bad parameter for: PlayerPowerHit:powerName` | Each message's parameter list was rebuilt by reading pointer-sized index elements as `int`, so powerName took the ToHit slot | Patch 0117: pointer-sized index reads, shared-heap copy and allocation |
| Crash after defeating an enemy | Page fault writing `0x38` in `mat3ToQuat`: without PhysX the ragdoll stand-in returns NULL, and the first ragdoll pose was written through it (`qCurrentRot` at 0x34) | Patch 0118: ARM64 reads and discards ragdoll packets (upstream `entGetRagdollIgnore`); creation checks for NULL. Server ragdoll poses are not shown on ARM64 (they never were without PhysX) |

## Earlier: what changed from 0.13.41 (Thor report, exports 20261027-235148/235205)

| 0.13.41 problem | Cause found in the exported report | 0.13.42/0.13.43 change |
|---|---|---|
| Crash when engaging an NPC in combat | `Bad parameter for: P1703759751:PowerName`, then a page fault reading `3FFC000000000000` (1.75 as a double): the combat message read its 8-byte argument slots 4 bytes apart, so PlayerSource came from the Damage slot | Patch 0115: 8-byte variadic slots on 64-bit Windows |
| FPS still very low | The game itself measured 6-12 FPS with a 30 cap; the app now shows what it receives. The render worker sleeps on an event whenever its queue drains, and each event call is a traced wineserver round trip under PRoot | Patch 0116: the worker polls its queue up to 2 ms before sleeping (event round trips about 23x fewer in the TSan stress test); `ARMPORT_WORKER_V1` logs sleeps, spin hits and client CPU every 5 s (counters atomic, timer per worker). Not yet measured on Thor |

## Earlier: what changed from 0.13.40 (Thor report: 30 FPS cap active, about 9.5 frames/s shown)

| 0.13.40 problem | Cause found in the exported report | 0.13.41 change |
|---|---|---|
| FPS still very low | The game's cap was 30, but the app showed about 9.5 frames/s: Raw RFB decoded per pixel and drawn with a software canvas and CPU scaling on the UI thread | Scaled draw on a hardware canvas (one canvas mode per Surface; recreated after a failure); Raw decoded in 64 KiB chunks through an int view (same pixels) |
| No way to tell game FPS from shown FPS | Not measured | Patch 0114 logs the game's frame rate every 5 s (`ARMPORT_FRAME_RATE_V1`); the report adds delivered frames per 5 s and decode times |
| Session ended after entering the new character | Logged in as another account and created a new hero; the strict same-session inventory check refused it. Not a client crash | Unchanged; reopen THORHERO on the usual account |

## Earlier: what changed from 0.13.39 (Thor report, sessions 577aff8c and 8f2ed736)

| 0.13.39 problem | Cause found in the exported report | 0.13.40 change |
|---|---|---|
| Very low FPS | Every client starts with `-maxfps 10`; only x86's qualified producer raises gameplay to 30 | Patch 0113 (the app's reviewed gameplay-performance hook): 30 FPS in gameplay when Turnip/Zink is selected, 10 on Software; menus stay 10 |
| Crash opening the graphics options | Page fault reading `FFFFFFFFFDF9D3DC` in `initializeShadowInfo`: shadow-volume/cape models rebased their vertex streams with int arithmetic | Patch 0112: pointer-width rebase |
| Session ended about 30 s after logout | The save was correct, but the strict reopen check refused an added `temporary_powers.brawl_tranq` | ARM64 accepts added temporary powers only, with every prior power preserved |
| ARM64 data stage 65 s with a valid cache | The merged-view case check followed links (173k stats) | That check now walks only the real (merged) directories |
| 110-145 s client folder scan | Measured by patch 0111: the whole-tree scan, not the change monitor | Not changed yet. After these fixes the x86 MapServer (about 6 min to ready) bounds the warm start |

## Earlier: what changed from 0.13.38 (Thor report, session a354bb95)

| 0.13.38 problem | Cause found in the exported report | 0.13.39 change |
|---|---|---|
| Crash entering Atlas after the MapServer connection | Page fault reading `FFFFFFFFA3E25370` at `smf_RenderTextAndWhitespace` (smf_render.c:219): SMF anchor pointers were kept in an int stack | Patch 0110: each attribute set keeps its anchor pointers; the int stack holds indices into it, so no anchor is truncated or recycled |
| ARM64 data stage 114 s | One stat per linked file (212k under PRoot) for the descendant check | The walk classifies by d_type; links must point directly at their file; a passed check (format 2) is reused while every source and link-target directory keeps its identity |
| 137 s before the first message store | Not yet measured: whole-tree folder cache scan plus recursive change monitor | Patch 0111 prints each folder-cache phase (`ARMPORT_FOLDER_CACHE_V1`) and skips the monitor for the immutable app worktree |

## Earlier: what changed from 0.13.37 (Thor report, 2026-10-27)

| 0.13.37 problem | Cause found in the exported report | 0.13.38 change |
|---|---|---|
| Startup took about 35 minutes | First (cold) run: fresh DB profile, Wine prefix and mirrors, plus a 7-minute copy of 8.5 GB of game data for ARM64 every launch | ARM64 now links the existing data (no copy). Warm reuse is kept |
| Client spent 99 s reading texture headers | Every texture file was opened at startup | Patch 0109: the app's texture-header index, built in the background and reused while the files are unchanged |
| Warm path sequential | ARM64 was excluded from the saved-world reopen, which starts the map while the client loads | ARM64 uses the same reopen and overlap as x86 |
| Kicked to login while loading Atlas, then a crash | The Release client renamed its window to the map name without the PID, so the harness decided the client had gone and shut down the session | The ARM64 client always shows the PID in its title (patch 0107); the MapServer also keeps a slow-loading client (`-notimeout`) |
| FPS the same as x86 | ARM64 always ran on the llvmpipe software renderer, with per-exception and per-file tracing | The renderer chosen in the app is honoured (GPU Turnip + Zink, with automatic fallback to Software); tracing is boundary-only (patch 0108) |

## Install (keep everything)

1. Install 0.13.44 over 0.13.43. Do not uninstall or clear data.
2. Run **Set up / update runtime** once.

## Test

1. Choose **Client for next launch → ARM64 client (experimental)** and the
   **GPU** renderer.
2. **Reopen saved THORHERO** twice. For each, note the time from the tap
   until you can move. The first launch after the update may still be cold;
   the second shows the warm time (the target is under 5 minutes).
3. Note the FPS in Atlas (it should be at least as smooth as 0.13.43), and
   open the graphics options once.
4. Move and open the map. Fight and defeat several NPCs with powers, reading
   the hit/miss lines in the combat chat (they should name your power, with no
   "Bad parameter" pop-up), and keep playing for a few minutes after the last
   defeat. On the second launch, also take the monorail to another zone once.
   Then **Save/Logout**, **Finish** and export the diagnostic ZIP from *both*
   launches.

## If something fails

Export the ZIP, then switch back to x86. Do not recreate the character.

## 0.13.46 development reservation — no APK available

Version/code 0.13.46/61 is reserved on the experimental server-metrics branch.
It adds an optional modern Win32 MapServer with 0119 timing and bounded native
console ingestion. The paired retained-progress executable runs in retained
0.10 CI; that does not execute the modern Thor executable. Exact same-head
build/runtime/package checks keep those scopes separate. Build, runtime and APK
run IDs, artifact/digests and reviewer approval are pending. Do not replace the
0.13.45 candidate instructions above with an assumed .46 qualification.

## Sampler review fix and launch history — qualification pending

The revised .46 development head fixes new-PID discovery at the sample deadline
and removes whole-registry copies. Tests force both target-first and costly-prefix
directory orders, including a callback with no remaining budget. Oversized cached
worker history is omitted explicitly while fresh ownership checks may still
supply process totals. No deadline is claimed to bound a blocking OS read.

Zoning exports add `launch_history` and unique generation console tails (at most
five, 256 KiB each). Resident returns keep the same generation; records refer to
owned launcher objects and are not native PID authentication or shutdown proof.
Retirement, restart/control paths and existing save/cleanup rules are unchanged.
This revision is not yet CI-qualified; no new APK is approved or available.
