# COH Atlas Gameplay 0.13.39: M5 Thor test (ARM64 client)

**Status:** candidate built and signed, waiting for review. Not yet installed
or played. M5 is not complete.

| Item | Value |
|---|---|
| APK | `COH-Atlas-Gameplay-0.13.39.apk`, versionCode 54, 80,907,096 bytes |
| APK sha256 | `d341a045a3fafa3e3acba1c3df046f9fece5a284ae9a4c47d714bcc7b6af620a` |
| Built by | run [40526906680](https://github.com/Russianranger/coh-android/actions/runs/40526906680) at `6e08aad1f`, artifact `coh-atlas-gameplay-0.13.39-apk` (12742874538, kept until 2026-11-26) |
| Signer / app ID | retained `92955353…c282`, `io.github.russianranger.cohclientinteractive` (same as 0.13.36 to 0.13.38) |
| ARM64 client | executable `ed70b6c3…d92a`, package `68c68f7a…c57d`, from build 40510032907 (patches to 0111, per-set anchor indices) |
| CI qualification | run 40519490566 at `6e08aad1f`: ARM64 creation then reopen through the app guest passed (retained 0.10 runtime; the full 0.13.39 runtime has not run in CI) |

## What changed from 0.13.38 (Thor report, session a354bb95)

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

1. Install 0.13.39 over 0.13.38. Do not uninstall or clear data.
2. Run **Set up / update runtime** once.

## Test

1. Choose **Client for next launch → ARM64 client (experimental)** and the
   **GPU** renderer.
2. **Reopen saved THORHERO** twice. For each, note the time from the tap
   until you can move. The first launch after the update may still be cold;
   the second shows the warm time (the target is under 5 minutes).
3. Note whether Atlas Park draws, the FPS, and whether the GPU fallback
   message appeared.
4. Move, open the map, try one power, then **Save/Logout**, **Finish** and
   export the diagnostic ZIP from *both* launches.

## If something fails

Export the ZIP, then switch back to x86. Do not recreate the character.
