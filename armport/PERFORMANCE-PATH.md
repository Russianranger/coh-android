# Performance path: start, zoning, FPS and cold MapServer start

Written 2026-11-02 by Claude (reviewer) at the user's request, after reading
`main`, `COH-ArmPort`, every active `armport/*` branch (newest:
`armport/mapserver-startup-60s` and `armport/mapserver-modern-runtime-qualification`,
2026-11-01), `native-android`, and the `codex/*` app line, plus the latest
Thor exports (0.13.44, 2026-10-28). Numbers come from those exports unless a run
is named; estimates are marked as estimates.

## Goals

| # | Goal | Today on Thor (0.13.44) | Gap |
|---|---|---|---|
| 1 | Server and client start under 5 min | Client window ready 8.9 min after the tap with a warm server-data cache, 10.9 min on a cache miss; in the world at ~12 min either way | ~2x |
| 2 | Zoning under 30 s | ~29 s when the destination MapServer is already running; ~9.7 min (563 s server + 18 s client) when it is cold | met only for resident servers |
| 3 | Steady 30 FPS or higher | 12-30 FPS in gameplay, mean 22.8; 226 of 227 five-second gameplay windows under 30 | needs headroom, not just the cap |
| 4 | Any MapServer cold start under 1 min | Atlas 287-339 s native start (plus 26-276 s preparation); King's Row 271 s native (plus 291 s preparation) | ~5x on native start alone |

Definition used below: "start" is tap to the client window being ready to log
in (machine time; the user's typing is excluded); zoning is request to "can
move" in the new zone.

## Where the time goes (measured)

### Startup, 0.13.44 launch 1 (cache hit) and launch 2 (cache miss)

| Stage | Launch 1 | Launch 2 | Notes |
|---|---|---|---|
| Guest start → DbServer ready (Wine, ODBC, PostgreSQL) | 1 min 39 s | 58 s | ODBC MSI repeated each launch (Astra's 95a09d11d skips it) |
| Atlas preparation (Python) | 26 s | 276 s | launch 2: `cold_server_data_mirror` 230 s; beacon graph 15-37 s |
| Atlas MapServer native start | 339 s | 296 s | x86 under FEX + Wine + PRoot; "Server ready (took 287 s)" internally |
| Client start (parallel) | 218 s | 213 s | folder scan of 212,496 loose files: 156 s / 142 s |
| Login to world | ~40 s | ~40 s | includes the client zone load (18-23 s) |

The MapServer is the critical path. Its own 287 s on launch 2 breaks down
(console timestamps) as: sequencers/defs 90 s, folder-cache callbacks 33 s,
fx 32 s, group libraries (3,224 files) 31 s, scripts 21 s, PhysX object
creation 22 s, maps 9 s; the remaining ~49 s is spread over smaller steps.
It is data loading through FEX + Wine + PRoot, not simulation.

### Zoning, 0.13.44 launch 1

| Transfer | Server side | Client load | Total |
|---|---|---|---|
| Atlas → King's Row (cold) | 563 s: Python prep 291 s (data mirror 218 s, beacon graph 57 s) + native start 271 s | 17.8 s | ~9.7 min |
| King's Row → Atlas (Atlas still running) | 7.6 s | 21.7 s | ~29 s |

### Frame rate, 0.13.44

- Game-measured FPS 12-30, mean 22.8, capped at 30 (patch 0113). With a cap of
  30 any slow frame drops below 30, so "steady 30" needs a higher cap and
  frames well under 33 ms.
- The display keeps up with the game (delivered 22.4 frames/s vs game ~23), so
  the limit is how fast the game produces frames.
- The client is not CPU-bound: about 0.5 cores user + 0.2 cores kernel while
  rendering. Frames wait rather than compute.
- In CI (software rendering, no device display path) the same client renders
  44-54 FPS on the login screen with its 120 FPS menu cap (build 40929292200,
  client-run). That is a menu, not gameplay, but it shows the client code is
  not limited to ~20 FPS.
- Each frame: Turnip renders → Zink's software WSI (`MESA_VK_WSI_DEBUG=sw`)
  copies it to the CPU → X11 socket to Xtigervnc → Raw RFB encode → second
  socket → Java decode → SurfaceView. Two full-frame copies through two sockets.

### Memory, 0.13.44 zoning session

Each MapServer peaks at 1.8-1.9 GB while loading. Idle Atlas sat at 0.8 GB
resident; King's Row with the player 1.9 GB. Client 1.4 GB (peak 2.5 GB),
DbServer 0.4 GB. The Thor has 16 GB, about 10 GB available at setup. Two or
three resident MapServers fit; every zone at once does not.

## Root causes, ranked by how much they cost

The costs of 2-4 are measured. The size of 1 is inferred from the evidence
below and is the first thing to measure (Phase 0).

1. **PRoot runs with seccomp acceleration disabled (`PROOT_NO_SECCOMP=1`)** in
   every app runtime and in CI (`host_smoke.py`). PRoot then stops on *every*
   system call via ptrace, including futex waits, pipe reads and writes, clock
   reads, mmap and getdents. With seccomp on, only path-based calls stop. Wine
   is built on pipe and futex traffic with wineserver, and the display path is
   socket writes. At capture, wineserver had 478 s and DbServer 428 s of
   system time. The 0.13.41→0.13.43 FPS gain (6-12 → 15-27) from fewer
   render-thread wakeups (patch 0116) is consistent with syscall cost
   dominating. No reason for the setting is recorded; it dates from the first PostgreSQL diagnostic
   (2026-09-27) and was copied forward. The 0.13.32 notes list "a whole-owned
   PRoot seccomp trial" as untried. The pinned PRoot is Termux's fork, which
   Termux normally runs with seccomp on.
2. **Data is 212,496 loose files, and each server gets its own copy.**
   - Both client and server scan the whole loose tree (`ARMPORT_FOLDER_CACHE_V1`
     reports `piggs count=0`). The client scan alone is 142-156 s.
   - Each MapServer session builds a private data tree (`cold_server_data_mirror`,
     218-230 s).
   - The cache meant to avoid that *moves* the only copy into the session and
     gives it back only after a perfect cleanup
     (`character_server_data_cache.py` `checkout`/`release`). Launch 1's
     post-zoning cleanup failed that proof, so launch 2 paid the full mirror
     again: about 4 minutes lost to one imperfect shutdown.
   - The engine already reads `.pigg` archives: the server animation pack is
     one.
3. **x86 MapServer under FEX doing file-heavy start-up**, every session, plus
   per-session Python preparation (beacon graphs 15-57 s, ODBC setup; the x86
   app line also paid a ~70 s Wine GPU probe each launch).
   FEX's share is probably the smaller part. The x86 client under FEX started
   in ~263 s (0.13.35, user-observed) against ~215 s for the native ARM64
   client: a different version, so this is only indicative, but CPU emulation
   was not the bulk.
4. **The display path copies every frame through the CPU and two sockets**, and
   the game cap is 30.
5. **Iteration cost.** One candidate takes ~2.5 h of serial CI (build 1 h 45 min,
   requalification 44 min, APK 2 min) before review and a device test. That
   sits on 188 workflows, 529 test files and 487 evidence records. The
   qualification protects saves and identity well, but performance work needs
   many fast measure-change cycles, and today every experiment pays the full
   release path. Workflows also can't be run from the GitHub UI because they
   aren't on the default branch (`main`), which is why Astra built a
   branch-level coordinator.

## Options evaluated

| Option | Goals | Expected effect | Effort | Risk | Confidence / how to confirm |
|---|---|---|---|---|---|
| Turn on PRoot seccomp | 1 2 3 4 | Large on Wine IPC, sockets, futex; moderate on file scans (path calls still stop) | Small (env change + guards) | Medium: any syscall PRoot then doesn't see must not need translation; `--sysvipc` must keep working | Unmeasured. A/B in CI `server-run` first (same PRoot, ARM64 kernel), then Thor |
| Server-data layout: shared read-only tree + small private overlay; no move/return cache | 1 2 4 | Removes 218-230 s mirror on every miss; preparation ~0 | Medium | Low: private writable roots are known (`bin`, `geobin`, `server`) | High for the mirror cost (measured) |
| Pack data into `.pigg` archives (or persist the folder-cache index) | 1 2 4 | Collapses the 212k-file scans for client and server | Medium-large | Medium: lookup order, private bin updates, case handling | High for the client scan (142-156 s measured); server share to be measured with patch 0119 phases |
| Cache per-session Python work (beacon graphs, probes) by data identity | 1 2 | 15-57 s per map, ~70 s GPU probe on the x86 line | Small | Low | Measured |
| Keep destination MapServers resident; pre-start the next zone once the current one is ready | 2 | Zoning becomes the measured ~29 s case | Small-medium | Memory (0.8-1.9 GB per server) and CPU contention during play | Measured for the resident case; needs a memory cap and low-priority start |
| Keep the server stack running between sessions (foreground service) | 1 | Second and later starts near client-only time | Medium | Battery, Android process limits, save safety | Design work; doesn't help the cold-start goal |
| Cooked PhysX mesh cache | 4 | Part of the 22 s PhysX phase | Medium | Cache correctness | Measure with 0119 phases first |
| Native ARM64 MapServer (Windows ARM64 under Wine, like the client) | 4 2 1 | Removes FEX from server start-up and simulation | Large | PhysX 2.8.4 has no ARM64 build. Options: run without server physics (ragdolls only, which the ARM64 client already discards) or migrate physics. The client's 64-bit defect classes all apply | Gain unknown until 1-3 are done and measured; decide then |
| Raise FPS cap to 60 (GPU profile) | 3 | Lets the average rise above 30 so dips stay above 30 | Trivial | Thermal/battery | Only useful once frames take well under 33 ms |
| Zero-copy display: X server with DRI3/Present on AHardwareBuffer, drop `MESA_VK_WSI_DEBUG=sw` | 3 | Removes CPU readback and both frame copies | Large | Integration and licence (Termux:X11, the proven open-source example, is GPL-3.0) | Measure SwapBuffers share first; seccomp may already recover much of the socket cost |
| Drop PRoot entirely (Wine + FEX built for Android bionic) | all | Removes the remaining path-call cost | Very large | Whole runtime rebuild | Only if seccomp + data layout leave a large gap |
| Resume the native Android client (`native-android`) | 3 | Native renderer | Very large | Frozen since 2026-10-21 at 0.1.19: placeholder boxes, 640x360, no gameplay parity | Not a path to these goals in reasonable time |

## Recommended path

Order matters. The cheap, broad fixes come first because they change what the
expensive options are worth. Each phase ends with a Thor measurement against
the goals.

### Phase 0: measure what is already built (days)

- Run Astra's existing instrumentation on the Thor: `ARMPORT_SERVER_STARTUP_V1`
  phases (native patch 0119), supervisor timing, server metrics. Five Atlas
  and five King's Row cold starts, per `armport/THOR-STARTUP-CAPTURE.md`
  (on the mapserver-startup branches).
- CI A/B, one variable: `server-run` with and without `PROOT_NO_SECCOMP`,
  recording MapServer "Server ready (took …)", the client folder-scan time and
  client FPS.
- Add a frame-time split to `ARMPORT_FRAME_RATE_V1`: time inside SwapBuffers
  versus the rest.

Exit: a phase table for the MapServer with FEX/Wine/PRoot shares understood,
and a seccomp yes/no.

### Phase 1: broad, low-risk wins (1-2 weeks)

1. PRoot seccomp on, if the A/B is clean (app and CI).
2. Replace the move/return data cache with a shared read-only data tree plus a
   private overlay per server. No mirror, nothing to strand.
3. Cache beacon graphs and probe results by data identity. Keep Astra's ODBC
   reuse.
4. Pre-start the next supported zone at low priority once the current zone is
   ready, with a memory cap; keep zones resident. Fix the post-zoning cleanup
   proof that currently fails.
5. Raise the GPU-profile cap to 60 behind a setting.

Exit targets: start ≤ 6 min warm; resident zoning ≤ 30 s every time;
cache-miss starts gone.

### Phase 2: data layout and frame path (2-4 weeks)

1. Pack client and server data into `.pigg` archives, or persist the
   folder-cache index keyed by data identity. Measure both scans before and
   after.
2. Cooked-physics cache if Phase 0 shows the PhysX phase matters.
3. If FPS is still under target after seccomp and the cap change: a zero-copy
   display path.
4. Keep the server stack alive between sessions while the app is open.

Exit targets: start ≤ 5 min; cold MapServer ≤ 2 min; FPS ≥ 30 in 95% of
gameplay windows.

### Phase 3: decide on the native ARM64 MapServer

With Phases 0-2 measured, the remaining gap to a 60 s cold start is known.
If it is mostly CPU time in parsing and simulation under FEX, port the
MapServer to ARM64 Windows with the client's toolchain and patch process. Make
the physics decision explicitly: run without server ragdoll physics to match
what the ARM64 client shows, or migrate. If the gap is still mostly file
syscalls, consider the bionic runtime instead.

Exit target: cold MapServer ≤ 60 s, which also makes cold zoning about
60 s + ~20 s client load. Resident zoning stays the 30 s path.

## Process changes that would speed all of this up

- **A performance experiment lane.** A CI job that runs only the server stack
  (and optionally the client) with one toggle and posts timings in ~30-40 min.
  A developer APK flavour with runtime toggles (seccomp, FPS cap, pre-start)
  that is device-tested for numbers, not qualified for saves. Keep the full
  qualification for candidates handed to the user as playable.
- **Make the workflows dispatchable from the UI.** Either set the default
  branch to `COH-ArmPort` or put the workflow files on `main`. This is a
  repository setting for the user to decide.
- **Consolidate branches.**
  - `main` stopped on 2026-09-25 and shares no history with `COH-ArmPort`.
  - The 26 `codex/*` app-line branches were last active between 2026-09-28 and
    2026-10-14 (`codex/cloud-foundation-20261029` is tooling). `native-android`
    is frozen. All of these are historical.
  - Live work forks at `0bf31c81b` (0.13.45 code). `armport/m5-thor` adds 2
    documentation commits. `armport/server-metrics` → `armport/sampler-review-fix`
    (0.13.46) → `armport/mapserver-startup-60s` is one line, and
    `armport/mapserver-modern-runtime-qualification` is a sibling of the last
    one from `e563fe566` (4 and 13 commits of their own).
  - Merge order: m5-thor's docs into that line, then the two MapServer
    branches, then `COH-ArmPort`. Older review and replay branches can be
    archived.

## What I would not do now

- Start the ARM64 MapServer port before Phase 0-1 numbers exist. Its gain is
  unknown and probably smaller than PRoot and data-layout costs, and it carries
  a physics decision.
- Resume `native-android` for these goals.
- Rebuild the runtime on bionic before the seccomp result is in.

## Open questions for the user

1. Is running the server without ragdoll physics acceptable for an ARM64 server
   (the ARM64 client already doesn't show ragdolls)?
2. Should the server stack stay running while the app is open (faster
   restarts, more battery use)?
3. Default branch: switch to `COH-ArmPort`, or copy the workflows to `main`?
