# Thor test: COH Atlas Gameplay 0.13.89 (ARM64 client): the zone starts again after the update

0.13.89 answers your test of 0.13.88 (launch A, 2026-11-26 evening, exports
035125 and 035141): "Map failed to start" when you entered with Prima.
**0.13.88 fails that way on every launch on your phone; 0.13.89 does not.**
Nothing in the saved game was changed.

## What changed

- **The zone starts again.** 0.13.88 changed one of the Primalist's files
  (the icon fix). Your phone held the shared server data made with the old
  file by 0.13.85 to 0.13.87, one tree of 128,765 file links. 0.13.88 wanted
  that tree replaced, refused to delete the Primalist's own files in it
  ("Shared server data tree holds a regular file: ...menumessages.ms") and
  stopped preparing Atlas Park after 64 seconds. The game then reported "Map
  failed to start", twice. The saved game opened correctly this time: that
  part of 0.13.88 worked.
- **The old data is kept where it is still right.** The Primalist touches 2
  of the 15 shared folders. 0.13.89 keeps the old tree for the other 13 and
  makes only those 2 again (about 10,700 links, not 128,765).
- **The state the failed start left behind is repaired.** That start had
  already opened some of the old tree's folders for writing. 0.13.89 checks
  that the tree still holds exactly what was counted when it was made, and
  closes it again.
- **A failed preparation names its cause.** The status line said only
  "Earlier Atlas preparation did not complete"; it now carries the first
  failure.
- Everything from 0.13.88 is in it (a saved Primalist opens; a hero made in
  the character list ends at "Session finished" with working FPS buttons;
  the Primalist's icon in the creator). None of that was reached in your
  test, so the launches below are the same as on the 0.13.88 sheet.

**Expect a long first launch.** The Primalist's definitions changed, so the
zone server of the first launch compiles them once more and its private data
is laid out again. In CI that start took the zone server 168 s against 24 s
for a normal one; on the Thor the comparable start in 0.13.85 took about six
minutes. The game waits on its loading screen after Enter Game until the zone
is ready; do not stop it. The second launch is back to normal.

## What CI showed, and what only the Thor can show

Shown on the CI machine (it plays the app's part with a script; the Android
app itself does not run there):

- **An update that changes the Primalist's files, over kept data** (run
  45962174259, a new kind of run made for this fault). A Primalist was made
  and saved with 0.13.87's files; the next start used 0.13.89's files on the
  same data. The old tree of the two Primalist folders was removed with the
  Primalist's own files in it (the step 0.13.88 refused), the two folders
  were made again (10,715 links in 13 s), the other 13 folders (118,050
  links) were reused, the Primalist was reopened and travelled to another
  zone in 10 s.
- That start's zone server took 168 s, against 23 to 24 s for a normal
  reopen: this is the one long start described above.
- A second hero made in the character list, then the first hero chosen at
  the next start (45971549887); the fast server and the spare zone server as
  before (45966947122, 45979451178).

Not shown anywhere but in unit tests on the real staging code:

- **Your phone's exact state**: one tree holding all 15 folders, with some
  folders left open for writing by 0.13.88's failed start. CI's kept data had
  the folders in two trees, and nothing left open. Three of the unit tests
  fail on 0.13.88's code with the message from your export.

Only the Thor can show (unchanged from the 0.13.88 sheet, since your test
stopped before any of it):

- that the app ends a created hero's session at "Session finished";
- that the FPS buttons are enabled for a hero made in the character list;
- the Primalist's icon in the creator;
- navigation with "Start mission maps" ticked.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.89 over the installed version (0.13.88).
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
   - Does Prima arrive in Atlas Park? (This is the fault that stopped you.)
     How long did it take from Enter Game? This is the long first launch.
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

- Launch A: `shared_server_data` (`shared_trees`: the two content folders
  made, the old tree reused for the rest; `removed.opened_trees_sealed_again`),
  the zone server's start time, `character_profile_eligibility` (`eligible`, `hero_count`,
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

Details: `HANDOFF-X86.md`, section "0.13.89 (104)".

CI at `ba4f0bc5d`: build 45951872879; update run (Primalist made with the
0.13.87 content, reopened with this one's) 45962174259; fast server
45966947122; several heroes 45971549887; spare 45979451178; APK 45984057354
(93,954,562 bytes, sha256
`6be15dfb2dd28d48bc104222b0d98d314a94f5384ea4f132dbe7b4e915298e50`, signer
unchanged; downloaded and hashed; 53 guest files equal the commit; the
content archive in the file carries this version's identity `2215c556…`).
