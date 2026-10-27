# COH Atlas Gameplay 0.13.41: M5 Thor test (ARM64 client)

**Status:** candidate built and signed, waiting for review. Not yet installed
or played. M5 is not complete.

| Item | Value |
|---|---|
| APK | `COH-Atlas-Gameplay-0.13.41.apk`, versionCode 56, 80,911,192 bytes |
| APK sha256 | `d8757237d7f47e8aa60b727b4d6d1c2b5e5f36b09f12bf2ffd6eab1b32df98d7` |
| Built by | run [40597604226](https://github.com/Russianranger/coh-android/actions/runs/40597604226) at `d3f88f700`, artifact `coh-atlas-gameplay-0.13.41-apk` (12777057685) |
| Signer / app ID | retained `92955353…c282`, `io.github.russianranger.cohclientinteractive` (same as 0.13.36 to 0.13.40) |
| ARM64 client | executable `61fd1f85…53c2`, package `c5d4429f…bbc7`, from build 40573892264 at `4e387bca5` (patches to 0114; provenance step: `armport/patches` tree `61e62110` equals the APK head's) |
| CI qualification | build 40573892264: all 8 jobs passed. Requalification 40591557473: ARM64 creation then reopen passed (2256 s) with the creator transition checks. Earlier attempts 40576183475 (creator stayed on Powers) and 40587090046 (validator predated the checks) had no client fault. Retained 0.10 runtime; the full 0.13.41 runtime has not run in CI |

## What changed from 0.13.40 (Thor report: 30 FPS cap active, about 9.5 frames/s shown)

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

1. Install 0.13.41 over 0.13.40. Do not uninstall or clear data.
2. Run **Set up / update runtime** once.

## Test

1. Choose **Client for next launch → ARM64 client (experimental)** and the
   **GPU** renderer.
2. **Reopen saved THORHERO** twice. For each, note the time from the tap
   until you can move. The first launch after the update may still be cold;
   the second shows the warm time (the target is under 5 minutes).
3. Note the FPS in Atlas (it should be clearly smoother than 0.13.40), and
   open the graphics options once.
4. Move, open the map, try one power, then **Save/Logout**, **Finish** and
   export the diagnostic ZIP from *both* launches.

## If something fails

Export the ZIP, then switch back to x86. Do not recreate the character.
