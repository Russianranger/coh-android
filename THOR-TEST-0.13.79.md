# Thor test: COH Atlas Gameplay 0.13.79 (ARM64 client): the spare zone server by default, and faster number emulation in zone servers

0.13.79 comes from your 0.13.78 launches A and B (2026-11-20).

**What those launches showed** (goal in brackets)

- Start to playing (5 minutes): the game connected to Mercy Island 2 min 7 s
  after the launch began in B and 2 min 49 s in A, the first launch after
  the update.
- Frame rate (30): 60 at the cap in the world in both launches, also while a
  spare zone server loaded. Every recommended option was on.
- Zone server start (1 minute): 44 s by the server's own clock in B; 51-58 s
  in A, which prepared the collision meshes once for the new server.
- Travel (30 s): through the spare 34 s (to Port Oakes) and 28 s (back to
  Mercy Island); without it, in A, 66 s to Port Oakes and 11 s back to the
  still-running Mercy Island.
- The spare loaded in 35 s and 30 s; 6.4 GB of memory stayed available with
  it running.
- Of the 34 s trip: 2.3 s went to a navigation map check before the spare
  could take the trip, 20 s to the zone server loading Port Oakes, and 11 s
  to the game loading the zone.

**What changed in 0.13.79**

- **"Keep a spare zone server loaded for travel" is a recommended option, on
  by default.** If it is unticked on your Thor, the options line names it
  and **Restore recommended options** ticks it. With it on, the game keeps
  the zone you are in and the spare; the zone you left closes about two
  minutes after you arrive somewhere else.
- **New option, on by default: "Faster number emulation in zone servers".**
  The zone servers are x86 programs run by an emulator. Until now it did
  their x87 arithmetic at 80 bits in software; now it uses 64 bits, close
  to what Windows itself gives 32-bit programs. In CI the part of a zone
  start that a trip through the spare also has to do fell from 8.3 s to
  7.2 s, and a new game folder's first zone start from 392 s to 358 s. It
  applies to zone servers only. Untick it if a zone fails to start or
  characters move wrongly.
- **The navigation map check is done before the trip.** While a loaded spare
  waits, the app checks the navigation maps of zones you have visited
  before. A trip to one of them then does not wait for the check.
- **The game's log keeps the stages of its own zone load**, so this test
  shows where the game's 11 s goes. It changes nothing in the game.

I also measured a second emulator setting (not emulating x86 store ordering
for the zone server's own code). It made the definitions part of a start 7%
faster in CI, but the server's background log queue relies on that ordering,
so it is not in the app.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "Thor test of 0.13.78 and what
0.13.79 does about it".

CI (all at `3c9812a41`, with the new emulation option on): build
44885921669; default server with travel 44894164205 (passed; zone starts
198.3 s, then 85.9 s and 86.4 s, against 208.8 / 95.8 / 101.0 s for 0.13.78);
Fast server 44897019107 (passed; reopen zone server at its main loop after
20.1 s against 21.5 s, group load 7.3 s against 8.3 s); spare zone server
44899910978 (passed: the spare loaded in 20.1 s, the trip's zone was ready
10.1 s after the game asked and the game was in the new zone after 10.6 s,
against 15.1 s and 16.1 s for 0.13.78; no travel command had to be typed
again). CI's destination has no prepared collision meshes yet, and preparing
them is where the option helps most, so expect a smaller gain on the Thor.
The navigation map check ahead of a trip did not run in CI (its spare uses
the Atlas Park tree, which has no such check); launch A is its first run.
APK 44902543863: 93,581,578 bytes, sha256
`3af3a9ccf1d92f275856f5eaf62e55f77ea5f2673925e12d0003daed664a812d`, signer
unchanged.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.79 over 0.13.78. The app should still show **Navigation
   maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**. Nothing
   needs importing again.
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

4. **Launch A** (the recommended options). **2 · Reopen saved character**,
   log in with `COHLOCAL / offline`, select Ralakar, **Enter Game**. Then:
   - Note roughly how long it took from the tap to standing in the world,
     and the frame rate standing still and running.
   - **Stay in Mercy Island for two minutes** (play as usual; fight
     something, and check that enemies and pets move normally). The spare
     loads during this time.
   - Travel to Port Oakes (the ferry) and note how long the loading screen
     stayed.
   - **Stay in Port Oakes for four minutes.** Mercy Island's server closes
     and a new spare loads.
   - Travel back to Mercy Island and note the loading time.
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B** (the comparison). Untick **Faster number emulation in zone
   servers**; the status line turns amber and names it, which is expected.
   Reopen and enter the world, stay in Mercy Island for two minutes, travel
   to Port Oakes, note the loading time, then save, finish the report and
   export. Afterwards tap **Restore recommended options**.

If the game does not start at all: tap **Restore recommended options** and
try once more. If it still fails, untick **Faster number emulation in zone
servers** and try again; then **Keep a spare zone server loaded for
travel**; then **Fast server** once (that also turns off the server start
changes), and tell me which launch worked. Either way, open the app,
**Recover interrupted reports** and export the top report. If an error box
appears in the game, tap **Ignore** (not Stop Program), note what it says
and keep going.

If a trip fails (the game says the map could not be started, or the loading
screen returns you to where you were), travel again: the second try starts
the zone the ordinary way. Tell me which trip it was.

## Report

The exports of both launches, the times and frame rates you noted, and
whether anything moved or fought wrongly. Fields I will read:

- `options_off_recommended`: empty in launch A, `server-x87-64bit` in B.
- `server_emulation`: `FEX_X87REDUCEDPRECISION` set in A, nothing set in B.
- `spare_zone.starts` and `spare_zone.graphs_checked_ahead`.
- The zone servers' `group_load_done` after a hand-over, A against B.
- The client's zone stages between `map.start` and `ready.sent`.
- The client's `ARMPORT_FRAME_RATE_V1` lines (60 expected in the world).
