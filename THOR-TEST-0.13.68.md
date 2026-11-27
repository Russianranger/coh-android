# Thor test: COH Atlas Gameplay 0.13.68 (ARM64 client): your zone starts while the game starts

> **Superseded: please test 0.13.69 instead.** After publishing I found that
> 0.13.68's early zone start never runs with the ARM64 client (its call sat in
> the x86 client's launch sequence; the CI run passed without a record of it).
> 0.13.68 behaves as 0.13.67. The steps below still work, but launch A will
> not show the change this sheet describes. Evidence: HANDOFF-X86.md,
> "0.13.68", "Defect found after publishing".

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
except in launch D. It is for the next step (a zone you travel to starting in
about a minute instead of four or five); launch D below tries it if you want.

Your 0.13.67 launch (export 20261111-035325) did the one-time work and
recorded it, so the first launch on 0.13.68 should already skip it (the
install checks, the client's file list, the texture list, the zone's server
data): the client program in 0.13.68 is the same build as in 0.13.67.

That launch also showed where the time goes: the Linux layer's one helper
thread, which every file lookup of every process waits for. The zone server
used about 92 s of CPU in its 232 s start. **Fast server start** removes many
of those lookups, so launch B below is the measurement I most need.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.68".

CI at 42728face: build 42945013269 passed; stock-travel runtime 42955090151
(`early_zone=true`, two trips; no early start was decided, see below); trusted
runtime 42959924053 created and reopened a character (its interactive job took
1873 s); APK 42963857636 published 0.13.68 (sha256
`75272fe931a6e8d6912cf6679f92dd7d136babebee8b2404e1d541c869e6f08a`). The
stock-travel run held no `early_start` record: the ARM64 launch never reached
the call (fixed in aad238554 for 0.13.69, where CI requires the record). Atlas
Park's MapServer, spawn to ready: 139.3 s stock, 98.7 s with trusted bins.

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
4. **Launch B** (fast server). Close the app from recents, open it, tick
   **Fast server start (test server with trusted bins)** and repeat step 3.
   Export the report, then untick it. This is the server CI runs; one phone
   time for it decides whether it becomes the default. If the game does not
   reach Mercy Island with it, export the report, untick it and carry on.
5. Optional **Launch C**: repeat step 3 exactly with the options at their
   defaults (a second plain launch, for comparison with A).
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
each launch. For the frame rate it helps to stand in the same spot for a
minute in each launch (where you arrive is fine) before moving on. Fields I will read, besides those in the 0.13.67 sheet:

- `character_zoning.initial_zone.early_start`: `started`, `preparation_seconds`,
  `ready_seconds`, `ready_before_the_game_asked` (or `requested_after_seconds`),
  and `reason` when it did not start.
- `character_zoning.spare_zone` (launch D): each spare's `warm_seconds`,
  `outcome` and the trip's `ready_seconds`; `waiting_reason` when none started.
- `memory_trace` around the zone's start (free memory with one zone server
  loading beside the client), and the storage report's
  `android_process_exit_history`.
