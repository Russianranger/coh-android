# Thor test: COH Atlas Gameplay 0.13.75 (ARM64 client): faster zone server start, second round

0.13.75 continues from 0.13.74 with what CI measured there. It contains
everything in 0.13.74, so if you have not tested 0.13.74 yet, test this one
instead; the steps are the same plus one option.

**Where things stand (your 0.13.73 launches, 2026-11-18)**

- 60 frames a second at the cap with "Do not monitor ordinary socket
  traffic" ticked; in the world about 3 min 35 s after the tap; back to a
  running zone in 16 s. Those three goals are met.
- Not met: a zone server takes about 150 s to start (goal: 60 s), so a trip
  to a zone that is not running takes about 3 minutes.

**What 0.13.74 changed (not yet measured on the phone)**

- "Load zone server animations when first used (faster zone start)" and
  "Remember folder locations in the Wine server (faster file opening)", both
  on by default. In CI a zone server start fell from 95.5 s to 56.5 s.

**What 0.13.75 adds**

- **"Fast server" skips the object library date check.** At every start a
  zone server compared the dates of all 3,224 object library files with its
  prepared list (18 s of the phone's 148 s start in 0.13.73). The Fast
  server now reads the prepared list directly, as it already does for its
  other prepared data. The list is still rebuilt when it is missing or made
  for another server.
- **New, on by default: "Find files in any letter case in one step (needs
  Lighter system-call monitor)".** The game asks for files in a different
  letter case than they are stored in, and Wine then walks the path folder
  by folder. The system-call monitor now finds the stored name itself, for
  Wine's programs only.
- What these save on the phone is not measured yet: launches A, B and C
  below measure it.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.75".

CI: CI_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.75 over what you have (over 0.13.73 or 0.13.74). The app should still show
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
   - Find files in any letter case in one step (needs Lighter system-call monitor)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

   The last three in the Checked list are new since 0.13.73 and should
   already be ticked; tell me if they were not.
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
5. **Launch C** (the letter-case option off). Untick **Find files in any
   letter case in one step**, Reopen, enter the world, travel to Port Oakes
   once, save, export, and tick it again.

If the game does not start at all: untick **Find files in any letter case
in one step** and try once more; if it still fails, untick **Remember folder
locations in the Wine server**; then **Load zone server animations when
first used**; then **Fast server**. Either way, open the app, **Recover
interrupted reports** and export the top report so I can see which one it
was. If an error box appears in the game, tap **Ignore** (not Stop Program),
note what it says and keep going. If a zone looks wrong (missing buildings
or objects), tell me which zone: that would be the object library list.

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
- The zone server's console line `ARMPORT_OBJECT_LIBRARY_BIN_V1
  status=trusted` and the time between its `object_library` and `Loaded
  grouplibs` lines (18 s in 0.13.73).
- `proot_stop_counts`: the first line's `casefold_replaced`,
  `casefold_absent` and `casefold_listed` (zero in launch C); wineserver's
  `readlinkat` row (call 78; 1.0 million stops per zone start in 0.13.73)
  and MapServer's `newfstatat` row (79; 0.7 million).
- `character_zoning.stock_travel.starts`: `ready_seconds` for Port Oakes
  (149.5 s in 0.13.73).
- The client's `ARMPORT_FRAME_RATE_V1` lines (60 expected, as in 0.13.73).
