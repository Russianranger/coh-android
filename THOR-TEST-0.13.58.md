# Thor test: COH Atlas Gameplay 0.13.58 (ARM64 client): fresh install, Atlas Park first

In 0.13.57 THORHERO was saved in King's Row (the 0.13.56 stop left the hero
there). Reopen started King's Row's zone server itself while the game started:
King's Row was ready at 20:56:10, the game launched a second earlier, and as its
first screen appeared Android closed the whole app with no message (recovered
export 20261106-210545). Your setup export 20261106-220022 has Android's
reason: **low memory** (the low-memory killer ended the app while it was on
screen, 20:58:39 UTC), with King's Row starting at the same time as the game.

0.13.58:

- **Every session starts Atlas Park first**, the start every working session
  has used. A hero saved in another zone is sent there by the game itself when
  you press **Enter Game**: the database server asks for that zone and it
  starts the way a monorail trip does. The screen can stay still for a few
  minutes while it loads (the game now waits up to 15 minutes there instead of
  90 seconds). The old King's Row startup is no longer used with the game's own
  zone travel.
- **Storage cleanup works again.** A folder the runtime creates
  (`assets/pgsql`) had no permissions, so every storage scan stopped there and
  disabled all cleanup; each update left another 3.5 GB runtime behind (14 of
  them on your Thor). The app now creates that folder itself and repairs it
  before a scan. The storage report also records Android's last reasons for
  closing the app.

Everything else is 0.13.57: [THOR-TEST-0.13.57.md](THOR-TEST-0.13.57.md).
Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.58".

CI: build 42300265349, zone-trip runtime 42312362966, default runtime
42316982535 and trusted runtime 42322788540 passed at 919e23760; APK
42329179898 published it. The zone-trip run took the game's own trip (second
Atlas Park ready 167 s after the DbServer asked for it, back to Atlas, save
passed). The default and trusted runs each
passed on a re-run of their failed job: the first tries stopped at a
character-creator screen check and at a logout that was not saved within 2
minutes, parts 0.13.58 did not change. CI's hero starts in Atlas Park, so the
King's Row start at Enter Game is tested only by you (step 6).

## Steps (fresh install)

1. Keep the four asset ZIPs on the phone (`COH-Assets-1.0.0-Base.zip`,
   `-Reference.zip`, `-Zones.zip`, `-Audio.zip` from the
   [coh-assets-v1.0.0](https://github.com/Russianranger/coh-android/releases/tag/coh-assets-v1.0.0)
   release). Uninstall COH Atlas Gameplay (this deletes the hero, the imported
   assets and the old runtimes), then install 0.13.58.
2. **Import asset pack part** once for each of the four ZIPs, in any order,
   then **Set up / update runtime** (the first time it also downloads about
   670 MB of database and Windows runtime). Note how long each part takes.
3. Leave the options at their fresh-install defaults; **Game's own zone
   travel** is on.
4. **Create fresh THORHERO**: log in with `COHLOCAL / offline`, create THORHERO
   as a Primal Earth hero and skip the tutorial. Release the controls for the
   60-second wait, **Save character / log out**, wait for **Saved character
   verified**, then **Finish and save report**.
5. **2 · Reopen saved THORHERO**: Atlas Park. Take the monorail to King's Row
   (3-4 minutes of loading screen), stay at least 2 minutes, then **Save
   character / log out there, in King's Row**, wait for **Saved character
   verified**, **Finish and save report**.
6. **Reopen again** (the main test): the app says THORHERO is saved in King's
   Row and Atlas Park starts now. Log in and press **Enter Game**: the screen
   can stay still for several minutes, then you are in King's Row. Note the
   time from Enter Game to King's Row. Play a little (back to Atlas Park by
   monorail, or another zone), save/log out anywhere, **Finish** and export.
7. **Storage and cleanup**, **Scan storage**: cleanup should be offered now
   (there is only one runtime after a fresh install). Export the storage report.

If Enter Game ends with an error message instead, note it, wait a minute and
press Enter Game again. If an error box appears, tap **Ignore** (not Stop
Program), note what it says and keep going; export at the end. If the app closes by itself, open it,
**Recover interrupted reports**, export the top report, then also export a
storage report (step 7): it now holds Android's reason.

## Report

The exports of steps 4-6 and the storage report, the import/setup times, the
Enter Game to King's Row time, and anything odd. Fields I will read:
`character_zoning.saved_startup.dynamic_start`, `stock_travel.starts`
(`initial_login`), the zoning events, and the storage report's
`runtime_mount_points_repaired` and `android_process_exit_history`.
