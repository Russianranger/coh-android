# Thor test: COH Atlas Gameplay 0.13.63 (ARM64 client): Reopen any name

In 0.13.62, **Reopen saved character** stopped before the game opened:
"Station travel (Game's own zone travel off) follows only a character named
THORHERO. Turn Game's own zone travel back on to play Ralakar", although
Game's own zone travel was on (export 20261109-015537).

The app checks which zone travel a session uses, because station travel
works only for a character named THORHERO. It ran that check while it read
Ralakar's saved row, before the game's own travel was set up. At that moment
only the station route (installed with King's Row) looked active, so the app
refused any name except THORHERO. CI never showed this because its runtime
has no King's Row package. 0.13.63 runs the check once the session's travel
is known. With Game's own zone travel on, Reopen goes on to start Mercy
Island at Enter Game. The stopped attempt changed nothing in Ralakar's saved
rows.

Everything else is 0.13.62: [THOR-TEST-0.13.62.md](THOR-TEST-0.13.62.md):
any name the game accepts, one character per install, walking not locked, a
save after ordinary play in Mercy Island can be verified. Station travel (Game's
own zone travel unticked) still follows only a character named THORHERO, so
keep that option on. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.63".

CI at e679031ca: build 42550231650 (it runs the new reopen tests), zone-trip
runtime 42558801806 (its character named OTHERHERO) and trusted runtime
42563040886 passed; APK 42566326193 published it (sha256
`8d748cb7a4b75acd9b92b26c325ee2c721ff40dc0006e04fa500c9db9373b508`). The
default runtime was not repeated: the trusted runtime covers the same THORHERO
path. CI has no King's Row package, so it never showed this refusal; the unit
tests replay your session's order, and your Reopen of Ralakar is the first run
of the fix.

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.63 over 0.13.62. Your imported assets and the database profile
   (with Ralakar) stay.
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. **2 · Reopen saved character**. Before the game opens, the app should say
   that Ralakar is saved in Mercy Island and that Mercy Island starts when you
   press Enter Game. Log in with `COHLOCAL / offline`, select Ralakar, **Enter
   Game**. Note the time from Enter Game until you are in the world.
   - Walk with the stick right away. The movement buttons should work as soon
     as the world is on screen. (On the login and character screens the stick
     types W, A, S or D like a keyboard, so leave it alone there.)
   - Play normally for a while: defeat a few enemies (your pets count), so the
     save has experience to keep. Change zone if you like (a ferry or a door).
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**.
   - If Reopen stops before the game opens again, note the message and export
     the report.
4. **Reopen again**: you should arrive where you saved in step 3, with the
   experience kept. Save/log out, **Finish** and export.
5. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report (it holds
Android's reason).

## Report

The exports of steps 3-4 and the storage report, the Enter Game to world times,
whether walking worked at once, and anything odd. Fields I will read:
`character_profile_eligibility.character_name`, `character_reopen.name`,
`client_ready_evidence` (its `source` should be the zone's stock log),
`gameplay_progress` (the save of step 3), `character_zoning.initial_zone`,
`stock_travel.starts`, and the storage report's `android_process_exit_history`.
