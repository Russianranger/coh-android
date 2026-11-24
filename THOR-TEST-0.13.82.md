# Thor test: COH Atlas Gameplay 0.13.82 (ARM64 client): citizen names, FPS buttons at once, a third zone server

0.13.82 comes from the Thor test of 0.13.81 (2026-11-23) and two things the
owner has seen since the start of the project.

## What the 0.13.81 test showed

Exports 20261124-043617 (A, defaults), -044655 (B, prepared zone object
files) and -045740 (C, both options). Every launch passed.

| Trip | Launch | Server was | Door to arrival |
|---|---|---|---|
| Mercy Island to Port Oakes | A | spare, loaded 16 s before | 39.8 s |
| Port Oakes to Cap au Diable | A | not running | 50.4 s |
| Cap au Diable to Mercy Island | A | not running | 42.8 s |
| Mercy Island to Port Oakes | B | warm spare | 20.0 s |
| Mercy Island to Port Oakes | C | spare, loaded 21 s before | 29.0 s |
| Port Oakes to Mercy Island | C | warm spare, late steps deferred | about 17 s by the game's clock (see below) |

- **Finishing the zone load late works.** In launch C a warm spare had its
  zone ready 10.9 s after it was given it; in launch B, without the option,
  18.0 s. The late steps (navigation 3.9 s, physics 0.3 s) ran while the game
  was still loading. That option is now on by default.
- **The app learned where you were much too late.** It read "the hero is in
  the zone" from the game's log file, which is written 60-90 s after the
  event. Launch A and C: 73 and 74 s after you were in the world. Launch C's
  last trip: the game finished loading about 17 s after the door, the app
  recorded the arrival at 61 s. Everything that waits for that record was
  late: the FPS buttons, Save / log out, and the next spare zone server
  (which is why the spare was not warm for the first trips of A and C, and
  absent for A's second and third).
- **Prepared zone object files** saved 1-2 s of the game's zone load
  (object files 2.5-4.0 s for 4.1-5.1 s) and cost about 5 s on the first
  visit to each zone. It stays experimental and off.
- **A trip's request** was taken within a second of the game logging the
  move (2.3-3.3 s in 0.13.79).

## What is new

- **Citizens have names.** The zone server read no names at all: the lists
  of first names end their lines the Unix way in this game's data and the
  server looked only for the Windows way. Needs **Fast server** (default).
  I could not find the exact place that printed "null" for a nameless
  citizen, so if you still see it anywhere, tell me where (over the head,
  in the target window, in chat).
- **The FPS buttons and Save / log out come alive within seconds** of
  entering the world. A zone server now says on its own console when your
  character has loaded in, and the app reads that instead of waiting for
  the log file.
- **No 3 s pause when they come alive.** The app was typing `/maxfps 60`
  into the game's chat and holding your input back meanwhile. The game has
  started the world at 60 since 0.13.67; nothing is typed now.
- **The spare zone server starts sooner** after you enter the world and
  after each trip (it waited for the same late record).
- **"Finish zone loading while the game loads the zone"** is recommended and
  on by default.
- **New option, off by default: "Keep the zone you just left loaded".** The
  owner's decision: a toggle. With it, the current zone, the zone you just
  left and the spare run together, so the way back is a trip to a running
  zone. About 1.2 GB more memory. It needs the spare zone server; a spare
  still does not start below 3 GB of free memory.

What CI could and could not show:

- **Shown.** The name lists are read (a native test reads 0 names from a
  Unix file with the old code and all of them with the new). Every arrival
  in CI's travel run was read from the zone server's console (5 records,
  none from the log file): the trip back was recorded 24 s after CI typed
  the command, where 0.13.81 recorded it at 79 s. With the option on, the
  zone that was left stayed loaded, and the trip back to it began loading
  2.5 s after the request.
- **Not shown.** CI cannot see names over heads, the FPS buttons or the
  pause. Its run ended before a second spare was started, so three zone
  servers running together (launch B) is covered by unit tests only.
- **A defect CI caught.** The first build of this version ended the zone
  server when the character entered the world (my new console line was
  flushed the wrong way). Fixed and rebuilt before anything was published;
  a check now covers every server patch for the same mistake.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.82 over the installed version. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**.
3. Tap **Restore recommended options**; the line above the options should
   turn green. The options then are:

   Checked (19):
   - Use performance graphics
   - Fast mode (PRoot seccomp, experimental)
   - Share server data between zones (faster zone preparation)
   - Skip server-only folders in the client's file scan (faster client start)
   - Reuse the client's saved file list while the data is unchanged (faster client start)
   - Game audio (sound and music through Android)
   - Game's own zone travel (doors, tunnels, monorail; any zone)
   - Start my saved zone while the game starts (Reopen)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Fast server (untick for the 0.13.36 server)
   - Raise the frame cap to 60 FPS in the world
   - Lighter system-call monitor (untick for the 0.13.36 one)
   - Do not monitor ordinary socket traffic (needs Lighter system-call monitor)
   - Find files in any letter case in one step (needs Lighter system-call monitor)
   - Load zone server animations when first used (faster zone start)
   - Remember folder locations in the Wine server (faster file opening)
   - Reuse prepared collision meshes (faster zone start, needs Fast server)
   - Faster number emulation in zone servers (64-bit x87; faster zone start and travel)
   - Finish zone loading while the game loads the zone (needs Fast server)

   Unchecked (6):
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)
   - Keep the zone you just left loaded (about 1.2 GB more memory; needs the spare zone server)

4. **Launch A: recommended options.** Reopen, Enter Game. Then:
   - As soon as the world appears, watch the **Show FPS** button: note
     roughly how many seconds until it can be tapped, and whether anything
     pauses when it does. Tap it.
   - Look at citizens: do they have names over their heads? Target a few.
     Any "null"?
   - Wait one minute (the spare loads), then travel to a zone you know. Note
     the loading time. Do pedestrians, enemies and pets move there?
   - Wait one minute, travel again (any zone). Note the time.
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B: the third zone server.** Tick **Keep the zone you just left
   loaded** (the line above the options turns amber and names it; that is
   expected). Reopen, Enter Game. Then:
   - Wait one minute, travel to a zone you know, note the time.
   - Wait one minute, travel **back** to the zone you came from, note the
     time: this is the trip the option is for.
   - Wait one minute, travel to a third zone, note the time (through the
     spare), then back again.
   - Does the game stay smooth with three zone servers running?
   - **Save character / log out**, **Finish and save report**, export.
6. Tap **Restore recommended options** afterwards, unless you want to keep
   the third zone server on.

If characters in the world stand still, walk through walls, or a pet does
not follow: untick **Finish zone loading while the game loads the zone**,
tell me, and carry on.

If the game does not start at all: tap **Restore recommended options** and
try once more. If it still fails, untick **Finish zone loading while the
game loads the zone**; then **Keep a spare zone server loaded for travel**;
then **Faster number emulation in zone servers**; then **Fast server** once,
and tell me which launch worked. Either way, open the app, **Recover
interrupted reports** and export the top report. If an error box appears in
the game, tap **Ignore** (not Stop Program), note what it says and keep going.

If a trip fails (the game says the map could not be started, or the loading
screen returns you to where you were), travel again: the second try starts
the zone the ordinary way. Tell me which trip it was.

## Report

The exports of each launch, the times you noted, and what you saw. Fields I
will read:

- `character_observer_metrics.native_ready_to_observation_ms` (73,000 and
  74,000 in 0.13.81; expected under 6,000) and
  `client_ready_evidence.log_route` (`owned_zone_server_console`).
- `character_zoning.ready_records` (how often the console line was used)
  and `stock_travel.arrival_source`.
- `stock_travel.keep_previous_zone` (requested, applied, kept) and
  `stock_travel.evictions`.
- `spare_zone.starts` (when each spare was launched and whether it was warm
  at the request) and the trip times in `stock_travel.starts`.
- The game's new lines: `ARMPORT_GROUP_LOAD_V1 ... read_ms= write_ms=
  geoload= geoload_ms=` (where the rest of its group-file time goes) and
  `ArmPort zone: ... xfer.*` (its side of a trip, step by step).
- Each zone server's `ARMPORT_DEFERRED_LOAD_V1` and `ARMPORT_CLIENT_READY_V1`
  lines.

Details: `HANDOFF-X86.md`, section "0.13.82 (97)".

CI (build 45356454107 at `4953444f6`, every runtime run with the x87 option):
default options 45371360117: zone server start 371.1 s for a new character,
23.9 s reopened (0.13.81: 358.8, 23.4). Spare run 45377119759 with late
loading and the third zone server: 5 arrival records from the console, none
from the log file; trip: zone ready 10.7 s after the request, the game began
loading 11.9 s after its wait began and loaded for 7.9 s; trip back to the
zone still running: loading began after 2.5 s; arrivals recorded 27.1 s and
24.1 s after the typed command (0.13.81: 78.8 s for the second). Zone-change
run 45347675663 (the build before the server fix, same game client): of a
5.8-6.4 s object-file load, 1.6-2.0 s is reading files and 0.5-0.7 s
loading geometry; between leaving one zone server and connecting to the
next the game spends 0.2 s. APK run 45382486718: 93,614,346 bytes, sha256
`625c6cbc...b76eff8a`, signer unchanged, its 51 guest files equal the commit.
