# Thor test: COH Atlas Gameplay 0.13.87 (ARM64 client): several heroes in one account

0.13.87 is 0.13.86 plus the last item of your request of 2026-11-25: **one
account holds several heroes, chosen or made in the game's own character
list, with no "Switch hero slot" step.** 0.13.86 has not been on the Thor, so
this sheet covers both versions; you can skip 0.13.86 and install this one.

## What is new in 0.13.87

- **Play** opens the game's own character list. Pick any saved hero and
  Enter Game, or click an empty slot and make a new hero.
- The zone of the hero you played last is prepared while the game starts. If
  you enter with another hero, that hero's own zone is started then, so its
  first load takes longer. A new hero starts in its own starting zone. No hero
  is moved to another zone.
- A hero made from the character list is saved and checked like a first hero,
  and the account's other heroes are checked to still be there under the same
  IDs and names.
- If making a hero is interrupted before its first zone starts, that
  unfinished hero (it has no class or costume, and the game cannot enter it)
  is removed at the next **Play**. The report keeps a copy of its rows.
- Your two saved games from 0.13.85 stay separate and both keep working:
  Setup tab, **Swap to the other saved game** (the old "Switch hero slot").
  Each of them can now hold several heroes. They are not merged.

Two things this version does not support. Neither loses anything, but both
stop the session:

- **Do not delete a hero in the character list.**
- **One hero per launch.** To change hero: Save character / log out, Finish,
  then Play again.

## From 0.13.86 (also untested on the Thor)

- Zones keep their navigation data with "Start mission maps" ticked.
- The Primalist has an archetype icon.
- The first launch with the Primalist or "Unlock all content" prepares about
  10,700 files instead of 128,765, and keeps the other setting's data.
- A launch is no longer marked failed after slotting an enhancement and then
  travelling.
- The two status lines use plain words; Setup tab, **Show test details and
  tools** brings back the check wording, counters, log and test buttons.
- **Show FPS** and 10 / 30 / 60 FPS are at the top of the Options tab.
  "Reopen saved character" is **Play**; "Finish and save report" is **Finish**.
- Free memory is recorded every 30 seconds and kept if Android stops the app.

## What CI showed, and what it could not

CI plays the app's part with a script on a GitHub runner (no Thor, no Android,
no zone asset pack).

- **Several heroes** (run 45821035737, and 45798191917 before the build):
  one account, four launches in a row. A first hero is created and saved; it
  is reopened and changes zone; then a launch clicks an empty slot of the
  character list, makes a second hero (HEROTWO) and saves it; the last launch
  expects HEROTWO (played last) and enters with the first hero instead. All
  four saves were proved; the first hero's identity row (ID, name, account)
  was unchanged by the second hero's launch, and in the last launch its
  powers and costume were the same after the save as before login.
- The other runs are the usual ones and passed: fast server 45830386270
  (zone server 372.7 s new, 24.0 s reopened), spare zone server 45836206662
  (157.6 s / 23.5 s, trip 9.7 s), and the same with "Unlock all content" and
  "Primalist archetype" 45841519885 (188.1 s / 23.0 s, trip 9.5 s; a Primalist
  is created and reopened).
- **Not shown in CI:**
  - The app's own check of a hero made in the character list. CI's script
    reads the guest's proof; the Android code that accepts it is unit-tested
    only. Launch B is its first real run.
  - A chosen hero saved in a different zone than the one prepared (both CI
    heroes were in Atlas Park). Launch C does this if the second hero is in
    another zone.
  - A villain or Praetorian second hero, and more than two heroes.
  - Everything from 0.13.86 that needs the Thor: navigation data with
    mission maps, the menu wording, the FPS buttons on Options, the icon on
    the device's screen.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.87 over the installed version.
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
   saved game (Setup, **Swap to the other saved game**).

4. **Launch A: the Primalist, the menu and the icon.** Options: tick
   **Primalist archetype** and **Unlock all content** (as in your last
   launch). **Play** tab: tap **Play**, log in. The character list shows the
   Primalist and empty slots. Select the Primalist, Enter Game. Note:
   - Do the two lines above the tabs read plainly ("Game ready", "Logged in",
     "In the game")?
   - **Options** tab: do **Show FPS** and the 10 / 30 / 60 buttons work once
     the hero is in the game?
   - Does the Primalist show its icon?
   - **Save character / log out**, wait for "Saved", **Finish**. The status
     should end at "Session finished".
5. **Launch B: make a second hero in the same account.** Same options.
   **Play**, log in, click an **empty slot**, make any hero you like (a
   villain is the most useful test: it starts on Mercy Island, which CI did
   not try) and enter the game. Note:
   - Does the new hero reach its starting zone? How long did that take?
   - Play a few minutes, **Save character / log out**, wait for "Saved",
     **Finish**. Does it end at "Session finished"?
6. **Launch C: back to the first hero.** **Play**, log in. The list should
   show both heroes. Select the **Primalist** (the new hero was played last,
   so its zone is the one prepared), Enter Game. Note:
   - Does the Primalist arrive in the zone it was saved in, as you left it?
   - Save, **Finish**.
7. **Launch D: navigation data with mission maps, with Ralakar.** Setup tab:
   **Swap to the other saved game**. Options: **Restore recommended
   options**, then tick **Start mission maps** only. **Play**, select
   Ralakar. This launch prepares the shared zone data once more (a few
   minutes). Then:
   - In Atlas Park and after one trip to another zone: do enemies and pets
     move again? (This is the fault you saw in 0.13.85.)
   - If you have a mission at hand, enter it and leave it again.
   - Save in a zone (not inside the mission), **Finish**.
8. **Launch E: the same again**, to see the second start: **Play** with the
   same options. The zone server should start as fast as before 0.13.85
   (about 55-95 s on the Thor), not in six minutes.
9. **Options** tab: **Restore recommended options** when done.

If a launch stops: export its report (Play tab, **Reports / export**; Setup,
**Recover interrupted reports** if needed) and tell me what you did last. If
the game does not start with a test option ticked: untick it, **Restore
recommended options**, try once more.

## Report

The exports and what you saw. Fields I will read:

- Launch B and C: `character_reopen.heroes` (count, the hero expected, the
  hero chosen, `choice`), `created_in_session`, `character_zoning`
  `initial_zone` (`zone_choice`, `launch_expected_map_id`),
  `profile_eligibility` (`hero_count`, `unfinished_characters`), and the
  app's own acceptance of the session (`accepted`, the status at Finish).
- Launch D and E: `zone_tree_preparation`, each zone's `beacon_graph`
  record (installed, not refused), `map_startup_observation`.
- Launch A: `private_map_data.shared_trees`,
  `server_preparation_phase_seconds`, the zone server's start time.
- `android_thermal_samples.samples[*].system_memory_available_bytes` and
  `system_memory_low`, and `android_process_exit_history` if the app is
  stopped again.

One leftover wording: if you use **Swap to the other saved game** while the
other saved game is empty, the message still calls the button "Switch hero
slot". It is the same button; fixed for the next version.

Details: `HANDOFF-X86.md`, sections "0.13.87 (102)" and "0.13.86 (101)".

CI: build 45807264231; several heroes 45821035737; fast server 45830386270;
spare 45836206662; spare with both test options 45841519885; APK 45847002904
(93,950,466 bytes, sha256
`dab3e731d3c39b6eef7cf23a875ab3cb782e67f41f57c3d5b47d1126a5c22628`, signer
unchanged; downloaded and hashed; 53 guest files equal the commit; the
several-heroes code and the new button text are in the file).
