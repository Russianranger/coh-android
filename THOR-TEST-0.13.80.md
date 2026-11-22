# Thor test: COH Atlas Gameplay 0.13.80 (ARM64 client): navigation maps prepared ahead of a trip

0.13.80 comes from your three 0.13.79 launches (2026-11-21).

**What those launches showed**

- All three passed; the frame rate was 60 at the cap in the world.
- Trips, from the request to the game's connection:

  | Trip | Time | What happened |
  |---|---|---|
  | Mercy Island to Port Oakes (20:21 export) | 30.7 s | through the spare; the navigation map check had been done ahead |
  | Port Oakes to Cap au Diable (20:21 export) | 67.7 s | first visit: 37 s to install that zone's navigation map before the spare could take the trip |
  | Cap au Diable to Mercy Island (20:21 export) | 25.6 s | through the spare |
  | Mercy Island to Port Oakes (20:30 export, new option off) | 49.4 s | 16.5 s re-installing Port Oakes' navigation map |

- Installing Cap au Diable's navigation map made the app check Mercy Island's
  and Port Oakes' in full again in the next launch (11 s at the start, 15 s
  before the trip). That, not the unticked option, made the 20:30 trip slow.
- "Faster number emulation in zone servers" made no measurable difference to
  an ordinary zone start on the Thor. It shortened the one-time preparation of
  collision meshes after the update (2.1 s for Mercy Island; 9.7 s in 0.13.78).
- The game's own zone load is 7-8 s, of which 5.5-6.8 s is loading the zone's
  group files.
- The 17:43 export took 7.5 minutes to connect: about 4.5 minutes at the login
  screen and a one-time 67 s texture index after the update. The start itself
  was not slower.

**What changed in 0.13.80**

- **Navigation maps are prepared before you travel.** While a loaded spare
  waits, the app prepares the navigation map of every zone, the zones nearest
  to yours first: Mercy Island's neighbours within the first minutes, all 64
  within about half an hour of play. It stops at once when you travel or save
  and continues later. After that no trip waits for a navigation map.
- **Preparing one is much shorter.** The app checked the same 8,700 shared
  files three times for every zone (35 s). It now checks them once, keeps the
  result, and afterwards only reads their folders: about 10 s for a zone that
  is new, about 4 s for one that only needs checking again.
- **A new zone no longer disturbs the others.** Each zone's saved check listed
  a folder that every other zone's install writes into. It no longer does.

The first launch after this update checks each known zone's navigation map
once more (about 15 s at the start for Mercy Island). That is expected and
happens once.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "Thor test of 0.13.79 and what
0.13.80 does about it".

CI: CI80_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.80 over 0.13.79. The app should still show **Navigation
   maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**.
3. Tap **Restore recommended options**; the line above the options should
   turn green. The options then are:

   Checked:
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

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

4. **Launch A.** **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. Then:
   - **Stay in Mercy Island for four minutes** (play as usual; check that
     the frame rate stays smooth, and that enemies and pets move normally).
     The spare loads, then the app prepares navigation maps.
   - Travel to Port Oakes and note how long the loading screen stayed.
   - **Stay in Port Oakes for four minutes.**
   - Travel to **a zone you have not visited with this app yet**, for
     example Sharkhead Isle or Nerva Archipelago, and note the loading time.
     This is the trip that took 68 s to Cap au Diable.
   - Check there that enemies react and move (their navigation map is new).
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B.** Change no options. Reopen (the character is now in the new
   zone), stay four minutes, travel to Port Oakes or Mercy Island, note the
   loading time, save, finish the report and export. This is the launch
   that had to check the other zones again in 0.13.79.

If the game does not start at all: tap **Restore recommended options** and
try once more. If it still fails, untick **Keep a spare zone server loaded
for travel** and try again; then **Faster number emulation in zone
servers**; then **Fast server** once, and tell me which launch worked.
Either way, open the app, **Recover interrupted reports** and export the top
report. If an error box appears in the game, tap **Ignore** (not Stop
Program), note what it says and keep going.

If a trip fails (the game says the map could not be started, or the loading
screen returns you to where you were), travel again: the second try starts
the zone the ordinary way. Tell me which trip it was.

## Report

The exports of both launches, the loading times you noted, and whether the
frame rate dipped while you stood in a zone (the app prepares navigation
maps then). Fields I will read:

- `spare_zone.graphs_checked_ahead`, `graphs_ahead_done` and
  `graphs_ahead_stopped`: which zones were prepared, how long each took, and
  how often a trip or a save stopped the work.
- `launch_receipts.zone_graph_*`: `reused` in launch B for every zone
  prepared in launch A.
- `stock_travel.starts`: the time between a request and its launch (0 s
  expected for a prepared zone).
- The client's `ARMPORT_FRAME_RATE_V1` lines while the work ahead ran.
