# Thor test: COH Atlas Gameplay 0.13.60 (ARM64 client): villains start in Mercy Island

In 0.13.59 your new villain asked for the right zone: at Enter Game the game
requested Mercy Island and nothing else started. Mercy Island then failed with
"Map failed to start". Every zone other than Atlas Park and King's Row runs
from one shared server folder (0.13.57). One of that folder's setup steps (the
server's effects catalog) still accepted only the Atlas Park and King's Row
folders, so after about 5 minutes of preparing server files it refused, and the
game reported the map as failed. Nova Praetoria, the tutorials and every other
zone would have failed the same way. 0.13.60:

- **The shared zones folder is accepted**, so Mercy Island and every other zone
  can start.
- **A first zone that cannot start is recorded with its reason** in the
  report (`character_zoning.initial_zone.attempts`), and a second Enter Game in
  the same session repeats that reason instead of a confusing one.

Everything else is 0.13.59: [THOR-TEST-0.13.59.md](THOR-TEST-0.13.59.md) (no
zone before Enter Game, then only the character's own; Save is not cancelled by
its own Enter key). Same limits: one character per install, named THORHERO; at
most two zone servers; NPCs outside Atlas Park and King's Row stand still;
missions are not served. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.60".

CI at 81b6cdfc0: build 42442419621 (it now also runs the zone start, zone
travel and trip tests), zone-trip runtime 42448320432, default runtime
42451345001 and trusted runtime 42453750449 passed; APK 42456241853 published it
(sha256 `3f2761d824bbef9b83450bd80a794bd51fd5b74317c6e16eaebdbf555fca0b67`).
CI's hero starts in Atlas Park and CI's copy of the game has no all-zones
pack, so CI cannot start Mercy Island or any other zone from the shared
folder: your test is the first start of one. In the zone-trip run Atlas
Park was again ready 136 s after Enter Game asked for it, and the trip to a
second Atlas Park took 172 s.

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.60 over 0.13.59. Your imported assets and the database profile
   stay. The villain from 0.13.59 was not kept: the game deletes a new
   character whose first zone could not start. (Correction, 0.13.61: it was
   kept as an unfinished character, so Resume and Reopen both stopped; see
   [THOR-TEST-0.13.61.md](THOR-TEST-0.13.61.md).)
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. Press **Resume first character creation**. Log in with `COHLOCAL / offline` and create
   THORHERO as a **villain** (skip the tutorial), then **Enter Game**.
   - The app should say it is starting **Mercy Island**. This first time it
     first prepares the server files that every zone except Atlas Park and
     King's Row shares (about 5 minutes on your phone last time; kept for later
     sessions), then starts the zone. The game screen stays still meanwhile
     (the game waits up to 15 minutes). Note the time from Enter Game until
     you are in Mercy Island.
   - Release the controls for the 60-second wait, **Save character / log
     out**, wait for **Saved character verified**, then **Finish and save
     report**.
   - If the app instead says a character already exists, use **2 · Reopen
     saved THORHERO** and note what it says.
4. **2 · Reopen saved THORHERO**: the app says THORHERO is saved in Mercy
   Island. Log in, **Enter Game**: you should arrive in Mercy Island, faster
   than in step 3. Take a zone exit (a ferry, tunnel or door) to another
   zone, stay at least 2 minutes, then **Save character / log out there**,
   **Finish and save report**.
5. **Reopen again**: Enter Game should take you straight to the zone you saved
   in in step 4. Note the time. Save/log out, **Finish** and export.
6. **Storage and cleanup**, **Scan storage**, export the storage report.

If Enter Game ends with an error message, note it, export the report and send
it; the report now says why the zone could not start. If an error box appears,
tap **Ignore** (not Stop Program), note what it says and keep going. If the app
closes by itself, open it, **Recover interrupted reports**, export the top
report, then also export a storage report (it holds Android's reason).

## Report

The exports of steps 3-5 and the storage report, the Enter Game to zone times,
and anything odd (where THORHERO appeared, NPCs, collisions). Fields I will
read: `character_zoning.initial_zone` (`attempts`, `request_to_ready_ms`),
`stock_travel.starts`, `zone_tree_preparation` (its `phase_seconds`), the
zoning events, and the storage report's `android_process_exit_history`.
