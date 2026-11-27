# Thor test: COH Atlas Gameplay 0.13.86 (ARM64 client): fixes from the 0.13.85 test, plain menu

0.13.86 answers the Thor test of 0.13.85 (seven exports, 2026-11-25). One
request is not in it yet: several heroes in one account, chosen in the game's
own character list. That work is under way for 0.13.87 (see the end).

## What changed (from your report and the seven exports)

- **Zones keep their navigation data with "Start mission maps" ticked.** In
  0.13.85 the zone data made for that option was refused by every zone's
  navigation map check (the check did not expect the 503 mission collision
  files), so zones started without their map; in export 030959 a zone server
  then took 376 s to start. Fixed. **CI cannot show this** (it has no zone
  asset pack); launch B below checks it.
- **The Primalist has an archetype icon** (a paw on a green badge, drawn for
  this build; the icon in the files you sent is not used).
- **The first launch with the Primalist or "Unlock all content" prepares
  less.** Your Primalist launch (export 035051) spent 335 s remaking the
  shared server data: 128,765 files, and it removed the data of the other
  setting, so switching back would have cost the same again. Now only the two
  folders the content changes are made again (about 10,700 files) and both
  settings' data are kept. The rest of that launch (creator about 3.5 min,
  zone data mirror 68 s, navigation map 47 s, zone server 126 s with two
  compiled files rebuilt once) is unchanged.
- **A launch is no longer marked failed after slotting an enhancement and
  then travelling** (export 014613).
- **The menu speaks plainly.** The two lines above the tabs say "Game ready",
  "In the game", "Saved", "Session finished" and so on. What a session checks
  is still written to its report. Setup tab, **Show test details and tools**
  brings back the check wording, the counters, the log and the test buttons.
- **Show FPS and 10 / 30 / 60 FPS are at the top of the Options tab.**
  "Reopen saved character" is now **Play**; "Finish and save report" is
  **Finish**; "Resume first character creation" moved to Setup.
- **The stop while you took a screenshot at the character list** (exports
  011040 and 011056) was Android stopping the app for low memory (its own
  record: reason 3, low memory, with the app in the foreground). Nothing was
  lost. The app had no memory figures from that moment; it now records the
  device's free memory every 30 seconds and keeps the figures across a stop.
- Not chased: the launch with "Unlock all content" on Ralakar (export 031914)
  played and saved, and failed only in the closing step (a known,
  intermittent fault while stopping Wine). Say so if it happens again.

## What CI showed, and what it could not

Four runs at the release commit (`fafe21a12`), all passed: a hero is created,
changes zone where the run has zones, saves, and is reopened.

- Both test options with the fast server and the spare (run 45766784376): the
  shared server data was made as two parts, the 2 folders the content changes
  (10,715 files) and the 13 it does not (118,050 files); the reopened session
  took both again in 0.01 s. Zone server 167.9 s new, 23.9 s reopened; the
  trip's zone ready 9.5 s after the request.
- Recommended options: zone change on the 0.13.36 server 45770545583; fast
  server 45774932914 (372.1 s new, 23.9 s reopened); fast server with the spare
  45779358365 (172.9 s new, 23.3 s reopened, trip zone ready 9.5 s).

Not shown by CI, so the Thor decides:

- Navigation data with "Start mission maps" (CI has no zone asset pack). Unit
  tests only.
- The 13 unchanged folders taken from the data 0.13.85 already made on your
  device (CI starts empty each time). Unit tests only.
- The Primalist's icon on screen (CI clicks a Blaster), and a Primalist
  created or played.
- The new menu wording, the Options-tab FPS buttons and the memory samples:
  the Java is compiled and unit-tested, never run on Android here.
- An enhancement slotted before a trip (unit tests only).

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.86 over the installed version.
2. **Setup** tab: tap **Set up / update runtime**, wait for **Runtime ready**.
3. **Options** tab: tap **Restore recommended options**. The options then are:

   Checked - Recommended (19):
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

   Your choice - Optional (1):
   - Keep the zone you just left loaded (about 1.2 GB more memory; needs the spare zone server)

   Unchecked - Test (3), each ticked only for the launch that names it:
   - Start mission maps (test; needs the game's own zone travel and the imported zone assets)
   - Unlock all content (test; store, veteran and pack rewards, locked power sets and archetypes; needs Fast server)
   - Primalist archetype (test; adds its name to the saved game once and stays on; older app versions will not open that saved game; needs Fast server)

   Unchecked - Experimental (5):
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)

   Your saved game right now holds the Primalist; Ralakar is in the other
   slot (Setup, **Switch hero slot**). The launches below say which hero.

4. **Launch A: the menu, with the Primalist** (the saved game as it is).
   Options: tick **Primalist archetype** and **Unlock all content** (as in
   your last launch). **Play** tab: tap **Play**, log in, Enter Game. Note:
   - Do the two lines above the tabs read plainly ("Game ready", "Logged in",
     "In the game")? Anything that still reads like a test?
   - **Options** tab: do **Show FPS** and the 10 / 30 / 60 buttons work from
     there once the hero is in the game?
   - Does the Primalist show its icon (character list, the team or info
     window, the power trays' archetype line)?
   - How long from Enter Game to the world, compared with the last time?
   - **Save character / log out**, wait for "Saved", **Finish**. The status
     should end at "Session finished".
5. **Launch B: navigation data with mission maps, with Ralakar.** Setup tab:
   **Switch hero slot**. Options: **Restore recommended options**, then tick
   **Start mission maps** only. **Play**. This launch prepares the shared zone
   data once more (a few minutes). Then:
   - In Atlas Park and after one trip to another zone: do enemies and pets
     move as before 0.13.85? (This is the fault you saw.)
   - If you have a mission at hand, enter it and leave it again.
   - Save in a zone (not inside the mission), **Finish**.
6. **Launch C: the same again**, to see the second start: **Play** with the
   same options. The zone server should start as fast as before 0.13.85
   (about 55-95 s on the Thor), not in six minutes.
7. Optional, **launch D: Ralakar with "Unlock all content"** (the launch that
   failed only while closing in 0.13.85): tick it, **Play**, a few minutes,
   save, **Finish**. Does it end at "Session finished" this time?
8. **Options** tab: **Restore recommended options** when done. Use
   **Switch hero slot** to go back to the Primalist whenever you like.

Do not create a second hero from the game's character list yet: this version
would stop the session and refuse that saved game afterwards. (0.13.87 is
about exactly that.)

If the game does not start with a test option ticked: untick it, **Restore
recommended options**, try once more, and export the failed launch's report
(Setup, **Recover interrupted reports** if needed).

## Report

The exports (Play tab, **Reports / export**) and what you saw. Fields I will read:

- Launch B and C: `zone_tree_preparation` and each zone's
  `beacon_graph` / `navigation` record (installed, not refused; no "no
  qualified native profile"), and `map_startup_observation` (zone server
  start seconds).
- Launch A: `private_map_data.shared_trees` (which folders were made again,
  which were reused), `server_preparation_phase_seconds`, the zone server's
  start time, `primalist`, `single_player_content`.
- `android_thermal_samples.samples[*].system_memory_available_bytes` and
  `system_memory_low` (every 30 s), and `android_process_exit_history` if the
  app is stopped again.
- `character_reopen.enhancement_preservation` and `stock_arrival` if you slot
  an enhancement and travel.

## Next: several heroes in one account (0.13.87)

You asked for several heroes per account without "Switch hero slot". That is
written and unit-tested, and is being proved in CI now: **Play** opens the
game's own character list; you choose any saved hero or make a new one in an
empty slot; the zone of the hero you played last is prepared first. It changes
the part of the app that proves every save, on the device side too, so it gets
its own version rather than riding along untested. Your two saved games (the
Primalist's and Ralakar's) will both keep working; they stay separate.

Details: `HANDOFF-X86.md`, section "0.13.86 (101)".

CI: build 45757162842; probe 45766784376; zone change 45770545583; fast server
45774932914; spare 45779358365; APK 45784045022 (93,942,274 bytes, sha256
`733014e9b563d2638c9990a74985d70f7e230b73b736626ff98b68bc41625c1e`, signer
unchanged; downloaded and hashed; 53 guest files equal the commit; the icon,
the new menu texts and the memory field are in the file).
