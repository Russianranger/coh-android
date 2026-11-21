# Thor test: COH Atlas Gameplay 0.13.61 (ARM64 client): villain creation after the failed Mercy Island start

In 0.13.60 both **Resume first character creation** and **Reopen** stopped
before the game opened. The 0.13.60 sheet said the 0.13.59 villain had been
deleted; it had not. The game writes a new character to the database at Enter
Game, before its first zone starts. When Mercy Island failed, it kept that
half-made THORHERO: name and account only, with no class, powers, costume or
logins. Resume refused it as an existing character, and Reopen refused it as
one that had never logged in. 0.13.61:

- **Resume first character creation removes that unfinished THORHERO** (one
  that never entered the game), then you create THORHERO again. The report
  keeps a copy of what it removed. Any other character still stops the request
  and stays untouched.
- **Reopen explains it**: if THORHERO never entered the game, Reopen says so
  and points to Resume first character creation.
- If a new character's first zone fails again, the app says so and that Resume
  first character creation will create it again.

Everything else is 0.13.60: [THOR-TEST-0.13.60.md](THOR-TEST-0.13.60.md). Every
zone can start, Mercy Island included, from the shared server folder. CI cannot
start those zones, so your phone is the first to. Same limits: one character
per install, named THORHERO; at most two zone servers; NPCs outside Atlas Park
and King's Row stand still; missions are not served. Evidence:
[HANDOFF-X86.md](HANDOFF-X86.md), "0.13.61".

CI at bd27744ed: build 42499066512 (it now also runs the removal on a real
PostgreSQL database), zone-trip runtime 42506353321, default runtime
42510220143 and trusted runtime 42513450368 passed; APK 42516615576 published it
(sha256 `1718a7844d7c1eb8cd16e28afda774938c0b06fbbca186c3142329b7ce4bc88b`).
The first build, at a4799e843, stopped for an unrelated reason: lua.org timed
out the second download of the Lua library. The build now reuses the first
download. CI's sessions start from an empty database, so your Resume is the
first time the removal runs on a phone. In the zone-trip run Atlas Park was
again ready 136 s after Enter Game asked for it, and the trip to a second
Atlas Park took 172 s.

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.61 over 0.13.60. Your imported assets and the database profile
   stay.
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. Press **Resume first character creation** and confirm. Before the game
   opens, the app should say it is removing the unfinished THORHERO. Log in
   with `COHLOCAL / offline` and create THORHERO as a **villain** (skip the
   tutorial), then **Enter Game**.
   - The app should say it is starting **Mercy Island**. This first time it
     prepares the server files that every zone except Atlas Park and King's
     Row shares (about 5 minutes on your phone in 0.13.59; kept for later
     sessions), then starts the zone. The game screen stays still meanwhile
     (the game waits up to 15 minutes). Note the time from Enter Game until
     you are in Mercy Island.
   - Release the controls for the 60-second wait, **Save character / log
     out**, wait for **Saved character verified**, then **Finish and save
     report**.
   - If Mercy Island fails to start again, note the message, **Finish** and
     export the report (it now says why), and send it before trying again.
4. **2 · Reopen saved THORHERO**: the app says THORHERO is saved in Mercy
   Island. Log in, **Enter Game**: you should arrive in Mercy Island, faster
   than in step 3. Take a zone exit (a ferry, tunnel or door) to another
   zone, stay at least 2 minutes, then **Save character / log out there**,
   **Finish and save report**.
5. **Reopen again**: Enter Game should take you straight to the zone you saved
   in in step 4. Note the time. Save/log out, **Finish** and export.
6. **Storage and cleanup**, **Scan storage**, export the storage report.

If Resume first character creation still stops before the game opens, note
its message and export the report: it lists what it found. If an error box
appears, tap **Ignore** (not Stop Program), note what it says and keep going.
If the app closes by itself, open it, **Recover interrupted reports**, export
the top report, then also export a storage report (it holds Android's reason).

## Report

The exports of steps 3-5 and the storage report, the Enter Game to zone times,
and anything odd (where THORHERO appeared, NPCs, collisions). Fields I will
read: `character_profile_eligibility.unentered_character` (step 3),
`character_zoning.initial_zone` (`attempts`, `request_to_ready_ms`),
`stock_travel.starts`, `zone_tree_preparation` (its `phase_seconds`), the
zoning events, and the storage report's `android_process_exit_history`.
