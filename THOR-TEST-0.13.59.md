# Thor test: COH Atlas Gameplay 0.13.59 (ARM64 client): only the character's own zone

0.13.58 started Atlas Park's zone server at the start of every session, even for
a hero saved in King's Row (the hero still went to King's Row at Enter Game).
You asked for the game to load whatever zone the character is in, and never
Atlas Park unless the character is there, including for villains and
Praetorians. 0.13.59:

- **No zone starts before you enter the game.** Startup prepares only the
  database server and the game. When you press **Enter Game**, the game itself
  asks for the zone THORHERO is in, and only that zone starts. A request for
  any other zone before THORHERO has entered its own is refused (nothing is
  moved; the game shows that the map failed).
- **A new THORHERO can be a hero, villain or Praetorian.** After the character
  creator, the game starts that character's starting zone: Atlas Park for a
  hero, Mercy Island for a villain, Nova Praetoria for a Praetorian, or that
  side's tutorial zone. Atlas Park starts only for a hero who starts there.
- While the zone starts, the game screen stays still for a few minutes (the
  game waits up to 15 minutes). The app's status line says which zone is
  starting, then when it is ready.
- **Save is no longer cancelled by its own Enter key.** The game cancels a
  logout on any key press during its 30-second countdown ("Press any key to
  abort"); under Wine the Enter that sent `/quittologin` reached that check one
  frame late, so at a low frame rate (often right after a zone has started)
  THORHERO stayed in the zone and was not saved. The ARM64 client now ignores
  keys pressed before the logout was asked for. Leave the movement controls
  and keys alone during the countdown: a new key press still cancels it.

Everything else is 0.13.58: [THOR-TEST-0.13.58.md](THOR-TEST-0.13.58.md)
(storage cleanup, Android exit reasons in the storage report). Still the same
limits: one character per install, named THORHERO; at most two zone servers;
NPCs outside Atlas Park and King's Row stand still; missions are not served.
Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.59".

CI at 825bae059: build 42419983392, trusted runtime 42426938668, zone-trip
runtime 42413409889 and default runtime 42416994465 passed; APK 42429765739
published it (sha256 `aa704cdf8767a9ccc159d3497d9d2e3fc3766a7f63d030569a9fc7781c316ec9`).
In the zone-trip run (CI's hero is a hero in Atlas Park) the reopen started
no zone before Enter Game: Atlas Park was ready 136 s after Enter Game asked
for it, then the game's own trip to a second Atlas Park (172 s) and the save
passed. The Enter key race did not happen in these runs, so the Save fix is
proven by the build's native check only (patched client keeps the logout, the
original cancels it).

## Steps (fresh install)

1. Keep the four asset ZIPs on the phone (`COH-Assets-1.0.0-Base.zip`,
   `-Reference.zip`, `-Zones.zip`, `-Audio.zip` from the
   [coh-assets-v1.0.0](https://github.com/Russianranger/coh-android/releases/tag/coh-assets-v1.0.0)
   release). Uninstall COH Atlas Gameplay, then install 0.13.59.
2. **Import asset pack part** once for each of the four ZIPs, then **Set up /
   update runtime**. Note how long each part takes.
3. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
4. **Create fresh THORHERO**: log in with `COHLOCAL / offline` and create
   THORHERO on the side you want to test. This install keeps that one
   character:
   - **Villain** (skip the tutorial): the game should start **Mercy Island**,
     not Atlas Park. This is the main check of the new start.
   - **Hero** (skip the tutorial): the game starts Atlas Park; then step 5's
     King's Row trip.
   - **Praetorian**: Nova Praetoria (its collision data is incomplete; note
     anything odd).

   After Enter Game, note the time until you are in the zone and what the
   app's status line said. Release the controls for the 60-second wait,
   **Save character / log out**, wait for **Saved character verified**, then
   **Finish and save report**.
5. **2 · Reopen saved THORHERO**: the app says THORHERO is saved in that zone
   and that it starts at Enter Game. Log in, press **Enter Game**: you should
   arrive in the same zone. Take a zone exit (a door, tunnel, ferry or the
   monorail) to another zone, stay at least 2 minutes, then **Save character /
   log out there**, **Finish and save report**.
6. **Reopen again** (the main test): Enter Game should take you straight to
   the zone you saved in in step 5, with no other zone started first. Note the
   time from Enter Game to that zone. Save/log out anywhere, **Finish** and
   export.
7. **Storage and cleanup**, **Scan storage**, export the storage report.

If Enter Game ends with an error message, note it, wait a minute and press
Enter Game again. If an error box appears, tap **Ignore** (not Stop Program),
note what it says and keep going. If the app closes by itself, open it,
**Recover interrupted reports**, export the top report, then also export a
storage report (it holds Android's reason).

## Report

The exports of steps 4-6 and the storage report, the import/setup times, which
side THORHERO is, the Enter Game to zone times, and anything odd. Fields I will
read: `character_zoning.initial_zone` (`attempts`, `refused_requests`,
`request_to_ready_ms`), `stock_travel.starts` (`initial_login`), the zoning
events, the client's `ARMPORT_LOGOUT_KEY_V1` lines (the kept logouts), and the
storage report's `android_process_exit_history`.
