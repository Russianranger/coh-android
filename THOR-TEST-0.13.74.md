# Thor test: COH Atlas Gameplay 0.13.74 (ARM64 client): faster zone server start

0.13.74 comes from your 0.13.73 launches A, B and C (2026-11-18).

**What those launches showed**

- What you saw is what the reports say. With "Do not monitor ordinary socket
  traffic" ticked the game held 60 frames a second, the cap, in both
  directions (60-62 with performance graphics, 52-61 without). Unticked it
  ran 28-31 one way and 48-52 the other. The socket monitoring was the
  frame-rate limit; the graphics effects cost a few frames.
- In the world about 3 min 35 s after the tap (goal: under 5 minutes).
- The zone map check is skipped now (1.5 s instead of 12-15 s) from the
  second launch.
- Travel back to a zone that is still running: 16 s.
- Not at the goal yet: a zone server takes about 150 s to start (goal: 60 s),
  so a trip to a zone that is not running takes about 3 minutes. Of the 150 s
  65 s went to loading every animation of every creature in the game, and a
  quarter of everything the system-call monitor served in a launch was Wine's
  server looking up, folder by folder, where each opened file really is.

**What changed**

- **New, on by default: "Load zone server animations when first used (faster
  zone start)".** The zone server loads an animation when a character first
  uses it. This is one of the game's own developer switches; the server
  program is unchanged.
- **New, on by default: "Remember folder locations in the Wine server
  (faster file opening)".** A small library inside Wine's server remembers
  folders it has already looked up.
- What the two save on the phone is not measured yet: launches A and B below
  measure it.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.74 and the Thor test of 0.13.73".

CI: CI_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.74 over what you have. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**. Nothing
   needs importing again. Then set the options exactly like this.

   Checked:
   - Use performance graphics
   - Fast mode (PRoot seccomp, experimental)
   - Share server data between zones (faster zone preparation)
   - Skip server-only folders in the client's file scan (faster client start)
   - Reuse the client's saved file list while the data is unchanged (faster client start)
   - Game audio (sound and music through Android)
   - Game's own zone travel (doors, tunnels, monorail; any zone)
   - Start my saved zone while the game starts (Reopen)
   - Fast server (untick for the 0.13.36 server)
   - Raise the frame cap to 60 FPS in the world
   - Lighter system-call monitor (untick for the 0.13.36 one)
   - Do not monitor ordinary socket traffic (needs Lighter system-call monitor)
   - Load zone server animations when first used (faster zone start)
   - Remember folder locations in the Wine server (faster file opening)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

   The last two in the Checked list are new and should already be ticked;
   tell me if they were not.
3. **Launch A** (the defaults). **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. Then:
   - Note roughly how long it took from the tap to standing in the world.
   - Watch characters for a minute: enemies and citizens walking, your own
     run, jump and a few attacks on an enemy. Anything that slides without
     moving its legs, stands frozen in a pose, or an attack with no motion is
     what I need to hear about (animations now load on first use).
   - Travel to Port Oakes (the ferry) and note roughly how long the loading
     screen stayed. Fight something there, then travel back to Mercy Island.
   - **Save character / log out**, **Finish and save report**, export.
4. **Launch B** (animations at start, as in 0.13.73). Untick **Load zone
   server animations when first used**, Reopen, enter the world, travel to
   Port Oakes once (no need to come back), save, export, and tick the option
   again.
5. Optional **Launch C** (the Wine server option off as well). Untick both
   new options, Reopen, enter the world, save, export, and tick both again.

If the game does not start at all: untick **Remember folder locations in the
Wine server** and try once more; if it still fails, untick **Load zone
server animations when first used**; then **Do not monitor ordinary socket
traffic**; then **Lighter system-call monitor**; then **Fast server**.
Either way, open the app, **Recover interrupted reports** and export the top
report so I can see which one it was. If an error box appears in the game,
tap **Ignore** (not Stop Program), note what it says and keep going.

## Report

The exports of the launches you ran, the times you noted, and anything odd
about animations. Fields I will read:

- `server_quick_start` (under `character_zoning`): `requested` and
  `commands`.
- `wineserver_path_cache`: `installed`, `reason`, and `counters` (`calls`,
  `fast`, `folders`, `passed`).
- The zone server's `ARMPORT_SERVER_STARTUP_V1` phase lines:
  `sequencer_info_done` (65 s in 0.13.73), `definitions_done`,
  `group_load_done`, and `process_spawn_to_map_ready_seconds` (150 s).
- `proot_stop_counts`: wineserver's `readlinkat` row (call 78; 1.0 million
  stops per zone start in 0.13.73) and MapServer's `newfstatat` row (79).
- `character_zoning.stock_travel.starts`: `ready_seconds` for Port Oakes
  (149.5 s in 0.13.73).
- The client's `ARMPORT_FRAME_RATE_V1` lines (60 expected, as in 0.13.73).
