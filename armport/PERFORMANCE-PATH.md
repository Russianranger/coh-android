# Performance path: start, zoning, FPS and cold MapServer start

Written 2026-11-02 by Claude (reviewer) at the user's request, after reading
`main`, `COH-ArmPort`, every active `armport/*` branch (newest:
`armport/mapserver-startup-60s` and `armport/mapserver-modern-runtime-qualification`,
2026-11-01), `native-android`, and the `codex/*` app line, plus the latest
Thor exports (0.13.44, 2026-10-28). Numbers come from those exports unless a run
is named; estimates are marked as estimates.

## Direction (decided by the user, 2026-11-02)

- **The x86 track is primary again. ArmPort (the ARM64 client) is shelved and
  stays secondary**: no further ARM64-specific investment. The ARM64 option can
  remain in the app as experimental.
- **Keep ragdoll physics.** The servers stay x86 Win32 with PhysX, as in the
  x86 version. A native ARM64 MapServer is off the table.
- **Servers may stay running, with an idle/stasis mode or shutdown** that cuts
  resource use while idle. The goals should still be met from a **cold start**;
  resident servers are an addition, not a substitute.
- **The default branch stays `main`.** Workflows keep being dispatched through
  Astra's branch coordinator or by the reviewer on request.

What this changes in practice:
- Almost nothing on the server side. The DbServer and MapServers are x86 in
  both lanes, so every server, data and runtime figure below applies as is.
- The client figures below come from the ARM64 client lane. **The x86 client's
  gameplay FPS has never been measured on the Thor** (every x86-era report has
  `native_fps_measurement: false`). The x86 client runs through FEX, so its FPS
  needs its own baseline before any FPS work.
- The x86 client source is not behind. Its native patch series (`patches/`,
  tree `ffcb910e1`) is byte-identical in the 0.13.36 release, the `codex/*`
  branches, `COH-ArmPort` and Astra's newest branch. It already has
  render-worker wake coalescing (`client-render-queue`) and a texture-header
  index (`client-texture-index`), the x86 counterparts of ArmPort 0116 and
  0109.
- The lines differ in the app and guest runtime only:
  - The `codex/*` branches (PRs #1 and #2) hold ~1,900 lines of unreleased
    0.13.37 app/guest work on top of release commit `3570430ce`.
  - Astra's line holds the newer startup instrumentation, ODBC reuse, server
    metrics, zoning and display-path work.
  - Continuing on Astra's line with the x86 lane as the target, and reviewing
    the 0.13.37 work for merge, loses nothing.

## Goals

| # | Goal | Today on Thor (0.13.44) | Gap |
|---|---|---|---|
| 1 | Server and client start under 5 min | Client window ready 8.9 min after the tap with a warm server-data cache, 10.9 min on a cache miss; in the world at ~12 min either way | ~2x |
| 2 | Zoning under 30 s | ~29 s when the destination MapServer is already running; ~9.7 min (563 s server + 18 s client) when it is cold | met only for resident servers |
| 3 | Steady 30 FPS or higher | ARM64 client: 12-30 FPS in gameplay, mean 22.8; 226 of 227 five-second gameplay windows under 30. x86 client: never measured | needs headroom, not just the cap |
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

Launch 1, from `armport/app/mapserver_phases.py` over the Thor consoles
(stamp to map ready): Atlas 332 s, King's Row 258 s.

| Phase | Atlas | King's Row | What runs (source reading) |
|---|---|---|---|
| `sequencers` → folder caching (untimed) | 94 s | 89 s | sequencer tree scan + `sequencers.bin` decode + 5,120 animation attachments (certificate hashing only 1.2 s) |
| Story arcs | 54 s | 30 s | `Scripts.loc` tree scan (35 s / 17 s gap) and `maps` scan (13 s / 8 s) |
| Map load | 48 s | 30 s | `scenes`/geometry for the zone |
| FX info | 42 s | 33 s | `fx` tree scan + `fxinfo.bin` decode |
| Group libraries | 25 s | 24 s | `object_library`, 3,224 files |
| PhysX objects | 19 s | 7 s | 2,311 objects |

The servers run in `FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC` (no
`./piggs/texts.pigg`). In that mode the first use of each top-level folder scans
its whole tree from disk (`FolderCacheRequestTree`, the `[DEBUG] \tfx`-style
lines), and `ParserIsPersistNewer` then date-checks every source file against
each `.bin`. Every scanned entry is a Wine directory read plus `stat` through
PRoot path translation. Production mode skips the date check, but it also bans
loose `scenes`, `ent_types`, `object_library` and `geobin` (they must come from
piggs) and ignores `.bin` CRC differences, so forcing it with a marker file
alone would break map loading. The two candidates are piggs for the immutable
data (the shipped configuration the code expects) or a narrow native switch
that trusts a CRC-matching prepared `.bin` without the tree scan.

The narrow switch is `patches/mapserver-trusted-bins/0001-trusted-prepared-bins.patch`
(PR #11). It is applied only by the instrumented-MapServer producer
(`server-metrics-*` jobs, next to 0119) and is off unless the guest sets
`ARMPORT_TRUSTED_BINS=1`. CI requests it with `armport-app-runtime`
`trusted_bins=true`, which needs that build's servers (`server_run_id` at the
same commit). Each trusted `.bin` is logged as `ARMPORT_TRUSTED_BINS_V1`. The
metrics proof now reports `parser_or_definition_sources_changed: true` for such
a build. It accepts that only for this reviewed, default-off switch.

### Zoning, 0.13.44 launch 1

| Transfer | Server side | Client load | Total |
|---|---|---|---|
| Atlas → King's Row (cold) | 563 s: Python prep 291 s (data mirror 218 s, beacon graph 57 s) + native start 271 s | 17.8 s | ~9.7 min |
| King's Row → Atlas (Atlas still running) | 7.6 s | 21.7 s | ~29 s |

### PRoot fast mode A/B, CI (2026-11-03)

Runs 41588867344 (off) and 41584980465 (on): same branch and build inputs,
shipping MapServers, ARM64 runner. Both passed.

| | Off | On |
|---|---|---|
| `getppid` probe | 27.1 µs | 0.31 µs |
| Creation: Atlas spawn → ready | 489 s | 360 s |
| Reopen: Atlas spawn → ready | 183 s | 124 s |
| Reopen: request → client in world | 524 s | 397 s |
| Whole job | 2179 s | 1818 s |

On the fresh data mirror (creation), the MapServer re-parses source text that
the reused cache (reopen) loads from `.bin`: spawn definitions 154 s vs 2 s,
story arcs 85 s vs 17 s, definitions 67 s vs 3 s (fast mode off).

### Trusted prepared bins A/B, CI (2026-11-03)

Build 41593619489 (instrumented MapServers with the switch), fast mode on in
both runs; only `trusted_bins` differs. Both passed creation and reopen.

| | Off (41610459604) | On (41605600310) |
|---|---|---|
| Creation: Atlas spawn → ready | 381 s | 353 s |
| Reopen: Atlas spawn → ready | 130 s | 94 s |
| Reopen: request → client in world | 409 s | 367 s |
| Reopen: story arcs | 17.0 s | 2.1 s |
| Creation: spawn definitions | 116 s | 115 s |

On the fresh mirror only 38 bins reached the trusted path; spawn definitions,
story arcs and definitions are parsed from text either way, so those `.bin`
files are missing or rejected there. Combined with fast mode, the reopen Atlas
start went from 183 s (41588867344, neither) to 94 s.

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
   - Lead (2026-11-02, source reading only): `FolderCacheAddFolder` skips the
     upfront scan in `FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC` and resolves files
     on demand (`FolderCacheQuery`); `FolderCacheChooseMode` picks it only when
     `./piggs/texts.pigg` is absent. The logged `phase=scan` shows the clients
     ran a full scan instead. Dev mode also lowers client priority
     (`game_beforeParseArgs`) and changes `fileScanAllDataDirs`, so measure
     before relying on it. Round-1 cache recovery (PR #11) covers the stranding.
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
| Native ARM64 MapServer | 4 2 1 | Would remove FEX from the servers | Large | PhysX 2.8.4 has no ARM64 build | **Shelved by the user's decision** (keep ragdoll physics; x86 track) |
| FEX tuning for the x86 servers and client (TSO, SMC and block settings per process) | 1 2 3 4 | Unknown; FEX runs entirely on defaults today | Small to try | Correctness: memory-ordering settings must stay safe for multithreaded processes | Untried. A/B per setting in CI, server first |
| Idle/stasis for resident servers (lower tick rate when empty, or freeze and thaw) | 2 | Keeps resident zoning (~29 s) while idle servers use little CPU and battery | Medium | DbServer heartbeats and timeouts must tolerate a frozen map; thaw must be quick | Design and measure; the user wants this as an addition to cold-start goals |
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
- Get an x86 client FPS baseline on the Thor: per-window game FPS (the x86
  equivalent of ArmPort's `ARMPORT_FRAME_RATE_V1`, as an x86 `patches/` change)
  next to the existing `COH_CLIENT_RENDER_QUEUE_V1` timing, with time inside
  SwapBuffers split from the rest of the frame.

Exit: a phase table for the MapServer with FEX/Wine/PRoot shares understood,
a seccomp yes/no, and the x86 client's FPS and frame-time split.

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

### Shared read-only server tree: design (2026-11-03, source reading)

The engine already searches layered data folders, so the shared tree needs no
native change. `fileLoadDataDirs` → `findAutoDataDir` → `searchForDataDir(cwd)`
accepts a folder that has both `data/` and `tools/`. `addAppropriateDataDirs`
then adds `localdata/` (searched first) and `serverdata/` (second) when they
exist, and makes `data/` the main folder: it is searched last, and
`fileLocateWrite` writes there. `start_game` already runs each MapServer with
its runtime as the working directory.

Per MapServer runtime:
- `data/` (private, writable): `bin`, `geobin`, `server` (with `servers.cfg`
  and the schema), `.dbidmap` files and any writable input. This is the small
  part to copy or check out.
- `serverdata/`: one shared tree per data identity. It holds every immutable
  input except those private roots, and it is never moved or returned.
- `localdata/`: a per-map overlay, for example King's Row's 52 collision
  leaves.
- `tools/`: an empty folder that turns the layered search on.

Rules and work:
- A private root must not also exist in a folder searched earlier. Otherwise a
  rewritten `.bin` in `data/bin` is shadowed by the shared copy.
- The guest proofs that read `runtime/data/<input>` (beacon and collision
  inputs, cache verification) must resolve through the same three-folder order.
- `serverdata` as a directory link is a deliberate exception to "no directory
  links". It needs its own immutability proof (owned, read-only, fingerprinted
  by identity).
- Expected effect: no 104-230 s mirror on a miss, King's Row's 218 s first
  mirror goes, and nothing large is left to strand. Confirm first with a
  CI-only probe: a runtime where `tools/` exists and `serverdata/` holds one
  moved definition folder, checked by the console's
  `Using game data dir` line and a normal map start.

### Phase 3: close the cold-start gap on the x86 track

With Phases 0-2 measured, the remaining gap to a 60 s cold start is known.
The levers left on the x86 track, in order:
1. FEX tuning per process, starting with the MapServer.
2. Removing remaining per-start work found in the 0119 phase timing (for
   example cooked physics, definition parsing that can be cached by data
   identity).
3. If file syscalls still dominate: the bionic runtime (Wine + FEX without
   PRoot).

Alongside, ship resident servers with an idle/stasis mode for zoning and
restarts, without relying on them for the goals.

Exit target: cold MapServer ≤ 60 s, which also makes cold zoning about
60 s + ~20 s client load. Resident zoning stays the 30 s path.

## Process changes that would speed all of this up

- **A performance experiment lane.** A CI job that runs only the server stack
  (and optionally the client) with one toggle and posts timings in ~30-40 min.
  A developer APK flavour with runtime toggles (seccomp, FPS cap, pre-start)
  that is device-tested for numbers, not qualified for saves. Keep the full
  qualification for candidates handed to the user as playable.
- **Dispatch.** The default branch stays `main` (user decision), so the
  workflows can't be started from the GitHub UI. Astra's branch coordinator
  and reviewer dispatch on request remain the route.
- **Consolidate branches.**
  - `main` stopped on 2026-09-25 and shares no history with `COH-ArmPort`.
  - The 26 `codex/*` app-line branches were last active between 2026-09-28 and
    2026-10-14 (`codex/cloud-foundation-20261029` is tooling). They are
    historical except the unreleased 0.13.37 app/guest work in PRs #1 and #2,
    which should be reviewed for merge into the x86 track. `native-android` is
    frozen.
  - Live work forks at `0bf31c81b` (0.13.45 code). `armport/m5-thor` adds 2
    documentation commits. `armport/server-metrics` → `armport/sampler-review-fix`
    (0.13.46) → `armport/mapserver-startup-60s` is one line, and
    `armport/mapserver-modern-runtime-qualification` is a sibling of the last
    one from `e563fe566` (4 and 13 commits of their own).
  - Merge order: m5-thor's docs into that line, then the two MapServer
    branches, then `COH-ArmPort`. Older review and replay branches can be
    archived.

## What I would not do now

- Further ARM64-client work (shelved), or an ARM64 MapServer (ragdoll physics
  must stay).
- Resume `native-android` for these goals.
- Rebuild the runtime on bionic before the seccomp result is in.
