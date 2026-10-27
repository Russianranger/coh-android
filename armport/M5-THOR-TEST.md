# COH Atlas Gameplay 0.13.40: M5 Thor test (ARM64 client)

**Status:** candidate built and signed, waiting for review. Not yet installed
or played. M5 is not complete.

| Item | Value |
|---|---|
| APK | `COH-Atlas-Gameplay-0.13.40.apk`, versionCode 55, 80,907,096 bytes |
| APK sha256 | `29f102c4cc8ef66682d4ae749d2f991e92e28436fee618866836e94f0022cd74` |
| Built by | run [40560666702](https://github.com/Russianranger/coh-android/actions/runs/40560666702) at `2d3c8a6c5`, artifact `coh-atlas-gameplay-0.13.40-apk` (12760522009, kept until 2026-11-26) |
| Signer / app ID | retained `92955353…c282`, `io.github.russianranger.cohclientinteractive` (same as 0.13.36 to 0.13.39) |
| ARM64 client | executable `dfd967f6…18a8`, package `9599acc4…b60a`, from build 40543984620 at `eb976d7a1` (patches to 0113; provenance step: same `armport/patches` tree as the APK head) |
| CI qualification | build 40543984620: all 8 jobs passed. Run 40547544476 attempt 2: ARM64 creation then reopen passed (2196 s). Attempt 1 stopped when the creator's rendered "No" button was not found; no client fault. Retained 0.10 runtime; the full 0.13.40 runtime has not run in CI |

## What changed from 0.13.39 (Thor report, sessions 577aff8c and 8f2ed736)

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

1. Install 0.13.40 over 0.13.39. Do not uninstall or clear data.
2. Run **Set up / update runtime** once.

## Test

1. Choose **Client for next launch → ARM64 client (experimental)** and the
   **GPU** renderer.
2. **Reopen saved THORHERO** twice. For each, note the time from the tap
   until you can move. The first launch after the update may still be cold;
   the second shows the warm time (the target is under 5 minutes).
3. Note the FPS in Atlas (it should be clearly smoother than 0.13.39), and
   open the graphics options once.
4. Move, open the map, try one power, then **Save/Logout**, **Finish** and
   export the diagnostic ZIP from *both* launches.

## If something fails

Export the ZIP, then switch back to x86. Do not recreate the character.
