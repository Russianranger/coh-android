# Thor test: COH Atlas Gameplay 0.13.90 (ARM64 client): finding what closed the app

0.13.90 answers your test of 0.13.89 (2026-11-27, exports 190208, 190231,
190853 and 190904). Prima opened, played and saved: the 0.13.89 fix works on
your phone. Entering with Ralakar closed the app to the home screen.
**0.13.90 does not fix that close. It makes the app record why it was
closed**, so that one more attempt gives the cause. Nothing in the saved game
was changed.

## What your exports showed

- **Prima (190231): passed.** The tree that 0.13.88's failed start had left
  open was closed again, the two Primalist folders were made again (10,715
  links in 104 s), the other 13 folders were reused. The zone server took
  135 s, Prima was in Atlas Park 421 s after Play, and the save was verified.
- **Ralakar (190853, 190904): the app's process ended** between 19:07:40 and
  19:07:59 UTC, about 2¼ minutes after Play and within 20 seconds of the
  character list appearing. At that moment Atlas Park (Prima's zone, because
  she was played last) was loaded and ready. Ralakar is saved on Mercy
  Island, so Enter Game makes the game start Mercy Island beside it. The game
  side reported no failure, and 8 GB of memory was free at 19:07:35.
- **The cause is not in those exports.** A recovered export held neither
  Android's reason for ending the app nor a crash trace. Two candidates
  remain: Android ending the app for memory (the close you saw at the
  character list on 0.13.85 was that, with 11 GB free at setup), or a crash
  in the app's own code.
- **This case had never run before.** A saved hero chosen from another zone
  than the prepared one exists in unit tests only; CI's two heroes are both
  in Atlas Park.

## What changed

- **A recovered export explains the close.** It now carries Android's exit
  record (low memory, crash, not responding, signal) with Android's own
  description, the app's crash trace if its own code crashed, and the log up
  to the moment the app ended.
- **Every export holds Android's last 16 exit records** (4 before). The
  record of the close on 0.13.89 is on your phone now; the first export from
  0.13.90 will include it, whatever that launch does.
- **Memory is recorded while it happens.** The game side's free memory, swap
  and memory pressure go into the log every ten seconds, and Android's own
  memory warnings go into the launch record.
- **The launch record shows how far it came**: the login, the hero you chose
  and the start of its zone are saved as they happen.

## What CI showed, and what only the Thor can show

Shown on the CI machine (it plays the app's part with a script; the Android
app itself does not run there):

- The game side of this version starts, creates a hero, reopens it and saves
  as before (runtime run 46079013570, passed; zone server 361.0 s for a new
  hero, 23.7 s reopened). The new memory line is sent by the same code path,
  so sending it does not disturb a session.
- The published file was downloaded and checked: it holds the new evidence
  code and the game-side files of this commit.

Not shown in CI, tested only by small programs that run the app's own code
with stand-ins for Android:

- **Everything on the app's side**: reading Android's 16 exit records, the
  crash record, the memory warnings, the log that survives, the recovered
  export with its two new files. None of it has run on a device.
- The memory line itself is not printed in the CI log I can read; a unit
  test shows its form.

Only the Thor can show:

- **why the app closed** when Ralakar was chosen, and whether it closes again;
- that a recovered export on your phone really holds the record and the log.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.90 over the installed version (0.13.89).
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

4. **Launch A: Ralakar, exactly as on 0.13.89.** Options: tick **Unlock all
   content** and **Primalist archetype** (as in your last launches). **Play**
   tab: tap **Play**, log in, select **Ralakar**, Enter Game. Prima was
   played last, so Atlas Park is the prepared zone again.
   - **If the app closes:** open it again. **Setup** tab: **Recover
     interrupted reports**. **Play** tab: **Reports / export**, and export
     what was recovered. That export holds the cause. Then go to launch B.
   - **If Ralakar arrives on Mercy Island:** note how long it took from Enter
     Game, play a minute, **Save character / log out**, wait for "Saved",
     **Finish**, export. Skip launch B.
5. **Launch B (only if A closed): Mercy Island alone.** Options: untick
   **Start my saved zone while the game starts (Reopen)**; leave the rest.
   **Play**, log in, select **Ralakar**, Enter Game. No zone starts before
   Enter Game now, so Mercy Island starts by itself (the screen can stay
   still for a few minutes).
   - If he arrives: save, **Finish**, export. Ralakar is then the hero played
     last, so you can tick the option again and his zone is the prepared one.
   - If the app closes again: recover and export as in launch A.
6. **Options** tab: **Restore recommended options** when done.

If you already made the launch I asked for on 0.13.89 (the option unticked,
Ralakar selected), send that export too; it counts as launch B.

The launches left over from the 0.13.89 sheet (a third hero and the
Primalist's icon in the creator; **Start mission maps** with Ralakar) wait
until Ralakar can enter. They are unchanged in 0.13.90.

Still not supported: deleting a hero in the character list, and two heroes in
one launch (save, **Finish**, then **Play** again). Neither loses anything,
but both stop the session.

## Report

The exports and what you saw. Fields I will read:

- Any export: `android_process_exit_history` (16 records; the one at
  2026-11-27 about 19:07:45 UTC is the close on 0.13.89: `reason`,
  `status`, `importance`, `description`).
- A recovered export: `android-interruption.json` (`exit_history.records`
  with `reason_name`, `last_crash`, a trace for "not responding" or a native
  crash), `operation.log` (its last lines; `guest_memory_sample` every 10 s),
  `android-recovery-checkpoint.json` (`lifecycle`: `local_login_observed`,
  `session_hero`, `initial_zone_starting`, `trim_memory`).
- Launch A or B when Ralakar arrives: `character_reopen.heroes` (expected and
  chosen hero), `character_zoning` `initial_zone` (`zone_choice`,
  `chosen_zone_map_id`, `left_loaded_zone_map_id`), the app's result
  (`passed`, `status`).

Details: `HANDOFF-X86.md`, section "0.13.90 (105)".

CI at `1b4ade867`: build 46069408779; runtime 46079013570; APK 46082470173
(93,958,658 bytes, sha256
`fd3774d3dd1c215421e2b93866e2b940430ded5bcacb38a3640f8826c361031d`, signer
unchanged; downloaded and hashed; 53 guest files equal the commit; the dex
holds `ClientCrash`, `android-interruption.json`, `trim_memory`).
