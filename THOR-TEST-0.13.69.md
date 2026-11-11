# Thor test: COH Atlas Gameplay 0.13.69 (ARM64 client): the early zone start, now actually running

0.13.68 was meant to start your character's zone while the game itself
starts. It did not: the call sat in a launch sequence the ARM64 client does
not use, and the CI run passed without noticing. 0.13.69 puts the call in the
right place, and CI now fails if the option is on and no early start was
decided. If you installed 0.13.68, nothing is lost; it behaved as 0.13.67.

What should be different from your 0.13.67 launch (export 20261111-035325):

- **Reopen saved character**: Mercy Island starts once the game's files are
  checked, not after **Enter Game**. Enter Game should take you in after a
  short wait, or at once. Option **Start my saved zone while the game starts
  (Reopen)**, on by default.
- **The one-time work is done.** The install checks, the client's file list,
  the texture list and the zone's server data were recorded by your 0.13.67
  launch, so this launch should skip them. One more check joins them (the
  animation files, 13.6 s per launch until now); it runs once more and is
  skipped from the second launch.

Your 0.13.67 launch also showed where the time goes: the Linux layer's one
helper thread, which every file lookup of every process waits for. The zone
server used about 92 s of CPU in its 232 s start. **Fast server start** removes
many of those lookups, so launch B below is the measurement I most need.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.69".

CI: CI_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.69 over 0.13.67 or 0.13.68. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Leave the options at their defaults.
3. **Launch A.** **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. Note roughly how long
   Enter Game takes to put you in Mercy Island.
   - Stand where you arrive for about a minute, then play as you like (the pet
     should still walk to enemies).
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**. Export the report.
4. **Launch B** (fast server). Close the app from recents, open it, tick
   **Fast server start (test server with trusted bins)** and repeat step 3.
   Export the report, then untick it. This is the server CI runs; one phone
   time for it decides whether it becomes the default. If the game does not
   reach Mercy Island with it, export the report, untick it and carry on.
5. Optional **Launch C** (frame rate experiment): tick **Draw on the game's
   own thread (frame rate experiment)**, repeat step 3 and stand in the same
   spot as in launch A for a minute. Export, then untick it. In 0.13.67 four
   threads of the game each used about 30% of a core and none was at its
   limit; this removes one hand-off between them. It may help, do nothing, or
   lower the frame rate; the export tells.
6. Optional **Launch D** (the spare zone server, not yet run on a phone): tick
   both **Fast server start (test server with trusted bins)** and **Keep a
   spare zone server loaded for travel**, repeat step 3, but stay in Mercy
   Island about four minutes before travelling (the ferry to Port Oakes, or
   any zone travel) and note how long the loading screen lasts. Stay about
   four minutes, travel again and note that loading screen too. Save, export,
   then untick both.
7. **Storage and cleanup**, **Scan storage**, export the storage report.

If Reopen stops before the game opens, or the app closes by itself: open it,
**Recover interrupted reports**, export the top report and a storage report,
then untick **Start my saved zone while the game starts (Reopen)** and try
once more. If an error box appears in the game, tap **Ignore** (not Stop
Program), note what it says and keep going.

## Report

The exports of the launches you ran, the storage report, and roughly how long
Enter Game took in each. Fields I will read:

- `character_zoning.initial_zone.early_start`: `started`, `preparation_seconds`,
  `ready_seconds`, `ready_before_the_game_asked` (or `requested_after_seconds`),
  and `reason` when it did not start.
- `launch_receipts` (each step `reused`), the client's `ARMPORT_FOLDER_CACHE_V1`
  lines (`index result=hit`), `texture_header_index.reused`,
  `server_data_cache.reused`.
- `wine_priorities.loading_samples` (which core the zone server loads on and
  how much CPU it used) and the context switches in `busiest_threads`.
- `armport_gl_threads` and the client's `ARMPORT_FRAME_RATE_V1` lines
  (launch C against launch A).
- `character_zoning.spare_zone` (launch D).
- `memory_trace` while the zone server loads beside the client.
