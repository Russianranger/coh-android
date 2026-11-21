# Thor test: COH Atlas Gameplay 0.13.75 (ARM64 client): faster zone server start, second round

0.13.75 continues from 0.13.74 with what CI measured there. It contains
everything in 0.13.74, so if you have not tested 0.13.74 yet, test this one
instead; the steps are the same with two more options.

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
- **New, on by default: "Reuse prepared collision meshes (faster zone start,
  needs Fast server)".** A zone server prepared ("cooked") every collision
  mesh of its zone at every start: 10 s on the phone, 17 s in CI. The Fast
  server now keeps them in one file and reads them back. The first start of
  each zone after this update still prepares them, so the saving shows from
  the second start of a zone (launch B below).
- **New, on by default: "Find files in any letter case in one step (needs
  Lighter system-call monitor)".** The game asks for files in a different
  letter case than they are stored in, and Wine then walks the path folder
  by folder. The system-call monitor now finds the stored name itself, for
  Wine's programs only.
- In CI the second start of a zone server fell from 56.5 s to 27.3 s with
  the first two, and the first start of a new game folder from 300 s to
  214 s with the third. What they save on the phone is not measured yet:
  launches A to C below measure it.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.75".

CI at b270ff434: build 44424804176 passed; stock-travel runtime 44436543449
(`early_zone=true`, `proot_ioctl_filter=true`, sampler; one trip; the
letter-case option in both of its sessions); trusted runtime 44441077783
created and reopened a character (its interactive job took 1762 s); APK
44445389436 published 0.13.75 (sha256
`47b40206e4e139661442f5b919d06ba1feec2fb90c2962dc2ddda1530f0fcc63`). Trusted
runtime 44441077783, against 0.13.74's 44398992652 (reopen session, Atlas
Park): the zone server reached its main loop in 26.26 s (50.83) and was ready
27.3 s after its spawn (56.5); `definitions_done` 13.01 s (21.99) with
`ARMPORT_OBJECT_LIBRARY_BIN_V1 status=trusted` in both sessions;
`group_load_done` 9.90 s (25.54). Cooked meshes: the creation session cooked
2,265 meshes in 16.45 s and wrote 2,014 records, 12,815,870 bytes; the reopen
session read all 2,265 (`hits` 2265, `misses` 0, `refused` 0, `bad_records` 0,
`create_ms` 50). The Windows build compiled both changes in both server
variants. Runtime 44436543449 (stock server, so only the letter-case option),
against 0.13.74's 44392083121: the first zone start, which builds its caches,
213.7 s (299.9); later zone starts 101.2 and 95.8 s (106.2 and 100.8); PRoot
served 11.48 million stops in the 943 s creation session and 4.41 million in
the 775 s reopen session (14.18 and 4.86 million); MapServer's `newfstatat`
stops 1,540,303 in creation and 1,793,380 in reopen (3,430,953 and 2,027,296);
`casefold_replaced` 426,349 and 127,173. These are CI times; the phone's zone
start was 1.6 times CI's in 0.13.73.

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
   - Reuse prepared collision meshes (faster zone start, needs Fast server)
   - Find files in any letter case in one step (needs Lighter system-call monitor)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

   The last four in the Checked list are new since 0.13.73 and should
   already be ticked; tell me if they were not.
3. **Launch A** (the defaults; this one fills the collision mesh file).
   **2 · Reopen saved character**, log in with `COHLOCAL / offline`, select
   Ralakar, **Enter Game**. Then:
   - Note roughly how long it took from the tap to standing in the world.
   - Watch characters for a minute: enemies and citizens walking, your own
     run, jump and a few attacks on an enemy. Anything that slides without
     moving its legs, stands frozen in a pose, or an attack with no motion is
     what I need to hear about (animations load on first use).
   - Walk into a wall, up some stairs and off a ledge: you should collide,
     climb and land as always.
   - Travel to Port Oakes (the ferry) and note roughly how long the loading
     screen stayed. Fight something there, then travel back to Mercy Island.
   - **Save character / log out**, **Finish and save report**, export.
4. **Launch B** (the defaults again; nothing to change). This is the one
   that measures everything together. Reopen, note the time from the tap to
   the world, check walls, stairs and a ledge once more, travel to Port
   Oakes and note the loading time, save, export.
5. **Launch C** (the letter-case option off). Untick **Find files in any
   letter case in one step**, Reopen, enter the world, travel to Port Oakes
   once, save, export, and tick it again.
6. Optional **Launch D** (animations at start, as in 0.13.73). Untick **Load
   zone server animations when first used**, Reopen, enter the world, save,
   export, and tick it again.

If the game does not start at all: untick **Find files in any letter case
in one step** and try once more; if it still fails, untick **Reuse prepared
collision meshes**; then **Remember folder locations in the Wine server**;
then **Load zone server animations when first used**; then **Fast
server**. Either way, open the app, **Recover
interrupted reports** and export the top report so I can see which one it
was. If an error box appears in the game, tap **Ignore** (not Stop Program),
note what it says and keep going. If a zone looks wrong (missing buildings
or objects), tell me which zone: that would be the object library list. If
you fall through the ground or pass through a wall, untick **Reuse prepared
collision meshes** and tell me where it happened.

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
- `physx_cache` (`applied`, `bytes_before_start`) and the zone server's
  console line `ARMPORT_PHYSX_COOKED_V1` (`hits`, `misses`, `cook_ms`,
  `create_ms`, `added_bytes`): launch A cooks and writes, launch B reads.
- `proot_stop_counts`: the first line's `casefold_replaced`,
  `casefold_absent` and `casefold_listed` (zero in launch C); wineserver's
  `readlinkat` row (call 78; 1.0 million stops per zone start in 0.13.73)
  and MapServer's `newfstatat` row (79; 0.7 million).
- `character_zoning.stock_travel.starts`: `ready_seconds` for Port Oakes
  (149.5 s in 0.13.73).
- The client's `ARMPORT_FRAME_RATE_V1` lines (60 expected, as in 0.13.73).
