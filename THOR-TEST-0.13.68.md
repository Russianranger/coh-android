# Thor test: COH Atlas Gameplay 0.13.68 (ARM64 client): your zone starts while the game starts

0.13.68 is 0.13.67 plus one change: on **Reopen saved character**, the zone
your character is saved in now starts while the game itself starts, instead of
after **Enter Game**. In your 0.13.66 session Mercy Island took 113 s to
prepare and 227 s to start, all of it after Enter Game, while the game's own
start and the login had taken longer than that. The two now run side by side,
so Enter Game should take you in after a short wait, or at once.

It is an option, **Start my saved zone while the game starts (Reopen)**, on by
default. The app starts only the zone the character is saved in, only one zone
server, and only with at least 3 GB of memory free; otherwise the zone starts
at Enter Game as in 0.13.67. A new character is not affected (its zone is not
known until it is created).

A second new option, **Keep a spare zone server loaded for travel (needs Fast
server start)**, is off by default and has not run on a phone: leave it off
for launches A to C. It is for the next step (a zone you travel to starting in
about a minute instead of four or five); launch D below tries it if you want.

If you skipped 0.13.67, everything in its sheet applies here too:
[THOR-TEST-0.13.67.md](THOR-TEST-0.13.67.md) (Mercy Island pathing fix, launch
work no longer repeated, 60 FPS cap from the first frame). **The first launch
on 0.13.67 or 0.13.68 still does the one-time work once**; the gain shows
from the second launch.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.68".

CI: CI_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.68 over 0.13.66 or 0.13.67. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Leave the options at their defaults (the new option is ticked).
3. **Launch A.** **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. Note roughly how long
   Enter Game takes to put you in Mercy Island.
   - Summon your pet, target an enemy some distance away and order the pet to
     attack: it should walk or run to it and fight.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**. Export the report.
4. **Launch B** (the one that should be shortest). Close the app from recents,
   open it and repeat step 3 exactly. Export the report.
5. Optional **Launch C**: tick **Fast server start (test server with trusted
   bins)**, repeat step 3, export the report, then untick it. This is the
   server CI runs; I want one phone time for it before making it the default.
6. Optional **Launch D** (the spare zone server): tick both **Fast server
   start (test server with trusted bins)** and **Keep a spare zone server
   loaded for travel**, repeat step 3, but before saving stay in Mercy Island
   for about four minutes, then take the ferry to Port Oakes (or any zone
   travel) and note how long the loading screen lasts. The first trip after
   installing may still take four or five minutes (the app learns the game
   server's options from the first zone request). Stay about four minutes,
   travel again (back, or onward) and note that loading screen too: this is
   the one a spare should shorten. Save, export, then untick both.
7. **Storage and cleanup**, **Scan storage**, export the storage report.

If Reopen stops before the game opens, or the app closes by itself: open it,
**Recover interrupted reports**, export the top report and a storage report,
then untick **Start my saved zone while the game starts (Reopen)** and try
once more. If an error box appears in the game, tap **Ignore** (not Stop
Program), note what it says and keep going.

## Report

The exports of launches A and B (and C and D if you ran them), the storage report,
whether the pet walked to the enemy, and roughly how long Enter Game took in
each launch. Fields I will read, besides those in the 0.13.67 sheet:

- `character_zoning.initial_zone.early_start`: `started`, `preparation_seconds`,
  `ready_seconds`, `ready_before_the_game_asked` (or `requested_after_seconds`),
  and `reason` when it did not start.
- `character_zoning.spare_zone` (launch D): each spare's `warm_seconds`,
  `outcome` and the trip's `ready_seconds`; `waiting_reason` when none started.
- `memory_trace` around the zone's start (free memory with one zone server
  loading beside the client), and the storage report's
  `android_process_exit_history`.
