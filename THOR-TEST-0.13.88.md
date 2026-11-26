# Thor test: COH Atlas Gameplay 0.13.88 (ARM64 client): fixes from the 0.13.87 test

0.13.88 answers your test of 0.13.87 (four exports, 2026-11-26). **0.13.87
cannot open your saved game now that it holds a Primalist; 0.13.88 can.**
Nothing in the saved game was changed by the failed starts.

## What changed (from your report and the exports)

- **A saved game with a Primalist opens again.** The two failed starts
  (exports 160736 and 160749) stopped after 5 seconds with "Character
  attribute is absent from the accepted mapping: ents.class". The app checked
  every saved hero before it had learned the Primalist's class name. "Start
  mission maps" was not the cause; any launch would have failed. The fault has
  been in every version since 0.13.85; no Primalist had been reopened before.
- **A hero made in the character list ends the session properly.** Your new
  hero "Prima" (export 160620) was created, saved and proved, and then the app
  reported the session as failed, because it judged a new hero by the rule for
  a reopened one. It now ends at "Session finished".
- **Show FPS and 10 / 30 / 60 FPS work for a hero made in the character
  list.** They were tied to a step only a reopened hero goes through.
- **The Primalist's icon shows in the creator's archetype list.** Its
  definition named the picture in a way only the in-game windows could look
  up. The large picture beside the list stays empty: no such art exists for
  the Primalist.
- Each report now names the saved hero's archetype (`class_name`).

One thing to expect: the first launch after this update prepares the two
changed data folders again (about 10,700 files) and its zone server rebuilds
two compiled files, so that one start is a minute or two longer.

## What CI showed, and what only the Thor can show

Shown on the CI machine (it plays the app's part with a script; the Android
app itself does not run there):

- **A Primalist was created, saved and reopened** (run 45889160018; the
  report names `class_primalist` in both sessions). This is the first time;
  the 0.13.87 sheet was wrong to say CI had done it: that hero was a Blaster
  with the Primalist option on.
- **The Primalist's bar shows its paw icon** in the creator's archetype list
  of that run (I looked at the frame).
- A second hero made in the character list, then the first hero chosen at
  the next start (45897435657).
- The zone server was ready in 23 to 24 s for a reopened hero in three of
  the four runs, and a trip to another zone took 9 s with the spare zone.

Only the Thor can show (the app's own code, checked by unit tests and by
replaying your export 160620 through it):

- that the app ends a created hero's session at "Session finished";
- that the FPS buttons are enabled for a hero made in the character list;
- that your saved game (Ralakar and Prima) opens;
- navigation with "Start mission maps" ticked.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.88 over the installed version.
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

   Your saved game holds Ralakar and Prima (the Primalist). Because it holds a
   Primalist, the archetype stays on in it whatever the **Primalist archetype**
   box says. The other saved game (the one with only a Primalist) is not used
   in this test.

4. **Launch A: open the saved game, with Prima.** Options: tick **Unlock all
   content** and **Primalist archetype** (as in your last launches). **Play**
   tab: tap **Play**, log in. The list should show Ralakar and Prima. Select
   **Prima**, Enter Game. Note:
   - Does the launch start at all? (This is the fault that stopped you.)
   - **Options** tab: do **Show FPS** and 10 / 30 / 60 work?
   - **Save character / log out**, wait for "Saved", **Finish**. The status
     should end at "Session finished".
5. **Launch B: the other hero.** **Play**, log in, select **Ralakar** (Prima
   was played last, so her zone is the one prepared), Enter Game. Note:
   - Does Ralakar arrive in the zone he was saved in? How long did it take?
   - Save, **Finish**.
6. **Launch C: a third hero, to see the creator.** **Play**, log in, click an
   **empty slot**. In the creator, pick the **Melee** or **Support** play
   style and look at the archetype list: does the Primalist show its icon?
   Then make any hero you like (a villain is the most useful: it starts on
   Mercy Island, which CI did not try) and enter the game. Note:
   - Do **Show FPS** and 10 / 30 / 60 work for the new hero?
   - Play a few minutes, save, **Finish**. Does it end at "Session finished"?
7. **Launch D: navigation data with mission maps, with Ralakar.** Options:
   **Restore recommended options**, then tick **Start mission maps** only.
   **Play**, select Ralakar. This launch prepares the shared zone data once
   more (a few minutes). Then:
   - In Atlas Park and after one trip to another zone: do enemies and pets
     move again? (The fault you saw in 0.13.85; fixed in 0.13.86, never yet
     seen on the Thor.)
   - If you have a mission at hand, enter it and leave it again.
   - Save in a zone (not inside the mission), **Finish**.
8. **Launch E: the same again**, to see the second start: **Play** with the
   same options. The zone server should start as fast as before 0.13.85
   (about 55-95 s on the Thor), not in six minutes.
9. **Options** tab: **Restore recommended options** when done.

Still not supported: deleting a hero in the character list, and two heroes in
one launch (save, **Finish**, then **Play** again). Neither loses anything,
but both stop the session.

If a launch stops: export its report (Play tab, **Reports / export**; Setup,
**Recover interrupted reports** if needed) and tell me what you did last.

## Report

The exports and what you saw. Fields I will read:

- Launch A: `character_profile_eligibility` (`eligible`, `hero_count`,
  `primalist_class_number`), `character_reopen.class_name`, the app's result
  (`passed`, `status`).
- Launch B: `character_reopen.heroes` (expected and chosen hero, `choice`),
  `character_zoning` `initial_zone` (`zone_choice`).
- Launch C: `character_reopen.created_in_session`, `class_name`, the app's
  result (`passed`, `qualification_gates.guest_acceptance`).
- Launch D and E: `zone_tree_preparation`, each zone's `beacon_graph` record
  (installed, not refused), `map_startup_observation`.
- `android_thermal_samples.samples[*].system_memory_available_bytes`, and
  `android_process_exit_history` if the app is stopped.

Details: `HANDOFF-X86.md`, section "0.13.88 (103)".

CI at `f48a8a244`: build 45879536548; Primalist created, saved and reopened
45889160018; fast server 45893114240; several heroes 45897435657; spare
45903889193; APK 45907324995 (93,950,466 bytes, sha256
`73b5f7e753dcb6ca68d4e04717fa920bbef902fb5d6bea948064f4d0b27a1af0`, signer
unchanged; downloaded and hashed; 53 guest files equal the commit; the
compiled class list in the file names the icon the way the creator looks it
up; the app's new rule for a created hero is in the file).
