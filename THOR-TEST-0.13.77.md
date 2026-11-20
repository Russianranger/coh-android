# Thor test: COH Atlas Gameplay 0.13.77 (ARM64 client): options check, a shorter zone server start, and the spare zone server for travel

0.13.77 is 0.13.76 (from your 0.13.75 launches A to D, 2026-11-19) plus two
zone server changes made while 0.13.76 was in CI. If you have not tested
0.13.76, test this one instead: the steps are the same.

**What those launches showed**

- **One option was off in all four launches: "Do not monitor ordinary socket
  traffic".** Launch C of the 0.13.73 test unticked it and it stayed
  unticked. In your 30-minute launch, 18.5 million of the 26.9 million
  system-call monitor stops were the display server sending frames, which is
  what the option removes. Frame rate was 45-60 early in a launch and 23-34
  in the long one; with the option ticked you measured 60 in 0.13.73.
- Zone server start (0.13.73: about 150 s; goal: 60 s): Mercy Island 76 s
  and Port Oakes 55 s in launch B; 64 s and 64 s in launch C. Mercy Island's
  figure includes about 14 s of Wine starting its first program.
- Collision meshes: launch A prepared them (9.3 s and 5.2 s) and wrote a
  10.9 MB file; from launch B every mesh was read back (1,868 and 2,486,
  none missed, none refused). The object library list was trusted in every
  start.
- Animations on first use save 28-36 s per start (launch D against B), and
  you saw no animation problems.
- The letter-case option made no measurable difference on a warm start
  (launch C). It stays on: it cut the first start of a new game folder in
  CI.
- Travel: a trip to a zone that was not running took about 71 s to connect
  (about 3 minutes in 0.13.73); the trip back took about 10 s. Goal: 30 s.
- Start: the game connected to the zone 126 s after the launch began in B
  and 117 s in C (0.13.73: 206-210 s). (The report's "connected" time is about 70 s later than
  that, because it comes from a server log that is written late; I read the
  client's own log instead.)

**What changed (0.13.76 and 0.13.77)**

- **The options list starts with a status line and a button.** The line says
  "Options: all at the recommended settings." in green, or names every
  option that differs, in amber. **Restore recommended options** sets them
  all back. The report now carries the same list
  (`options_off_recommended`).
- **The spare zone server can now take a trip.** "Keep a spare zone server
  loaded for travel (needs Fast server)" keeps one extra zone server that
  has loaded everything zones share (37 s of a 62 s start in launch B) and
  waits.
  A trip then only loads the destination's own map. Until now a spare was
  refused whenever the trip's start options differed from its own by the
  game's "-transient" option, which these servers do not act on. It is
  still off by default: launch B below is its first run on a phone.
  With it on, the game keeps the zone you are in and the spare, so the zone
  you left closes about two minutes after you arrive somewhere else.

- **0.13.77: a zone server reads less at its start.** With Fast server on it
  no longer reads the `Defs` and `Menu` folders ahead (nothing lists them
  once the prepared data is trusted) and loads its message files without
  listing their source folders. In your launch B that work was 10 s of the
  54 s Port Oakes start and about 13 s of Mercy Island's 62 s. There is no
  new option; it follows **Fast server**.
- **0.13.77: the zone server reports where "loading map" spends its time**
  (12 s of that Port Oakes start), one line per map load. It changes nothing
  in the game; it tells me what to shorten next for trips through the spare.
- In CI the spare's first hand-over worked (0.13.76): the spare had loaded in
  25 s, and the trip's zone was ready 15 s after the game asked for it. A
  cold start of the same server takes 27-32 s there. On the Thor I expect
  about 30-35 s to ready; launch B measures it.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.76 and the Thor test of
0.13.75" and "For 0.13.77".

CI (all at `3e78d005e`): build 44683537682 (the Windows compiler's first
build of both changes); default server with travel 44693667939 (passed; zone
starts 233.0 s, then 106.7 s and 101.0 s); Fast server 44698417683 (passed;
reopen zone start 23.6 s from spawn to ready against 32.4 s in 0.13.76,
22.5 s to the main loop against 26.5 s; `Defs` and `Menu` not read ahead,
4 message files read without their folder listing); spare zone server
44703232069 (passed: the spare loaded in 19.9 s against 25.0 s, the trip's
zone was ready 15.2 s after the game asked and the game was in the new zone
at 15.8 s; the monitor served 1.84 million stops in that session against
2.13 million); APK 44708151316 (93,581,578 bytes, sha256
`dd8beb337ca77f3ce254125ea23be903dcaf9fa0b616613ab89e017f2271d042`, signer
unchanged).

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.77 over what you have (0.13.75 or 0.13.76). The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**. Nothing
   needs importing again.
3. Look at the new line above the options. It should name "Do not monitor
   ordinary socket traffic" as unticked (unless you ticked it since). Tap
   **Restore recommended options**; the line should turn green. The options
   then are:

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
   - Find files in any letter case in one step (needs Lighter system-call monitor)
   - Load zone server animations when first used (faster zone start)
   - Remember folder locations in the Wine server (faster file opening)
   - Reuse prepared collision meshes (faster zone start, needs Fast server)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

4. **Launch A** (the recommended options). **2 · Reopen saved character**,
   log in with `COHLOCAL / offline`, select Ralakar, **Enter Game**. Then:
   - Note roughly how long it took from the tap to standing in the world.
   - With the FPS display on, note the frame rate standing still and while
     running around for a minute.
   - Travel to Port Oakes (the ferry) and note roughly how long the loading
     screen stayed. Travel back to Mercy Island.
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B** (the spare zone server). Tick **Keep a spare zone server
   loaded for travel**; the status line turns amber and names it, which is
   expected. Reopen and enter the world. Then:
   - **Stay in Mercy Island for four minutes** (play as usual). The spare
     loads during this time.
   - Travel to Port Oakes and note how long the loading screen stayed.
   - **Stay in Port Oakes for five minutes.** Mercy Island's server closes
     and a new spare loads.
   - Travel back to Mercy Island and note the loading time. This trip also
     uses a spare, so it is slower than launch A's trip back.
   - Save, finish the report, export, then untick the option again (or tap
     **Restore recommended options**).

If the game does not start at all: tap **Restore recommended options** and
try once more. If it still fails, untick **Fast server** once (that also
turns off the new start changes) and tell me whether that launch worked;
then, with Fast server ticked again, untick **Find files in any letter case
in one step**; then **Reuse prepared collision meshes**; then **Remember folder
locations in the Wine server**; then **Load zone server animations when
first used**. Either way, open the app, **Recover
interrupted reports** and export the top report. If an error box appears in
the game, tap **Ignore** (not Stop Program), note what it says and keep
going.

In launch B, if a trip fails (the game says the map could not be started, or
the loading screen returns you to where you were), travel again: the second
try starts the zone the ordinary way. Tell me which trip it was.

## Report

The exports of both launches, the times and frame rates you noted. Fields I
will read:

- `options_off_recommended`: empty in launch A, `spare-zone-server` in B.
- `armport_proot_ioctl.socket_stops` (false expected) and
  `proot_stop_counts`: the rows for calls 206, 207 and 212 near zero.
- The client's `ARMPORT_FRAME_RATE_V1` lines (60 expected in the world).
- `armport_client_timeline.connections`: when the client connected to each
  zone server.
- `character_zoning.spare_zone` (launch B): each spare's `warm_seconds`,
  `outcome` (`assigned` expected twice), `map_id`,
  `loaded_seconds_before_request`, and any `refused_request`;
  `available_memory_mib_when_warm`.
- `character_zoning.stock_travel.starts`: `ready_seconds` for Port Oakes
  (55-66 s in 0.13.75; about 10 s less expected in launch A) and its `spare`
  record in launch B.
- The zone consoles: `ARMPORT_START_TREES_V1 status=not_read_ahead`, the
  `ARMPORT_MESSAGE_BIN_V1 status=trusted` lines, `Caching relevant folders`
  (7.8-13.2 s in 0.13.75) and the `ARMPORT_MAP_LOAD_V1` line.
- `character_zoning.memory_trace`: available memory with the zone, the
  spare and the client running.
- The zone servers' `ARMPORT_SPARE_V1` console lines and
  `ARMPORT_SERVER_STARTUP_V1` phases.
