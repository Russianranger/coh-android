# Thor test: COH Atlas Gameplay 0.13.83 (ARM64 client): a menu with tabs, options in categories, a first look at missions

0.13.83 comes from the Thor test of 0.13.82 (2026-11-24) and the owner's
requests of the same day.

## What the 0.13.82 test showed

Exports 20261124-181441 (A, recommended options) and -182926 (B, with "Keep
the zone you just left loaded").

| Trip | Launch | Server was | By the game's own clock |
|---|---|---|---|
| Mercy Island to Port Oakes | A | warm spare | 24.8 s |
| Port Oakes to Mercy Island | A | spare, loaded 17 s before | 30.9 s |
| Mercy Island to Port Oakes | B | warm spare | 25.9 s |
| Port Oakes back to Mercy Island | B | still running (the option) | 10.0 s |
| Mercy Island to Cap au Diable | B | warm spare | 21.2 s |
| Cap au Diable back to Mercy Island | B | still running (the option) | 9.4 s |

- **Citizens have names** and "null" is gone (owner's observation; it was the
  chat line of a rescued citizen).
- **The FPS buttons** came alive 9.4 s (A) and 11.3 s (B) after the hero was
  in the world; 73-74 s in 0.13.81. All 30 and 38 "the hero is in the zone"
  records came from the zone servers' own lines, none from the late log.
  Nothing was typed into the chat.
- **The third zone server** made the way back 9-10 s. Lowest free memory:
  3.5 GB with it, 4.9 GB without (the spare is not started below 3 GB), and
  more was pushed to swap. The owner's verdict: close to the device's limit,
  so it is now in its own **Optional** category.
- **Launch A was marked failed** although it saved correctly: the hero gained
  two enhancements in play and an old check could not look them up. Fixed.

## What is new

- **Three tabs.** *Play*: the commands of a session, in the order they are
  used. *Options*: the launch options. *Setup*: runtime, asset import,
  controller, storage and test tools. The state lines ("Connecting", what is
  loading) stay above the tabs. During a game the menu opens on Play.
- **Four option categories** on the Options tab: Recommended, Optional, Test,
  Experimental. "Restore recommended options" sets Recommended, Test and
  Experimental and leaves Optional as you set it. If anything differs from
  the recommended settings, an amber line says so above the tabs as well.
- **FPS buttons sooner again.** The app acts on the zone server's line within
  half a second instead of at its next look, which came every 15 s. The same
  for arrivals after a trip, so the next spare starts sooner.
- **Enhancements gained, slotted or sold in play** are recorded and no longer
  decide whether a launch passed.
- **Missions: a first look, nothing playable yet.** A mission map is not
  started yet (the game is told the map failed and you stay where you are).
  The report now keeps which mission map the game asked for. Launch B below
  collects what I need to plan the work.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.83 over the installed version.
2. Open the **Setup** tab, tap **Set up / update runtime** and wait for
   **Runtime ready**. It should still show **Navigation maps 1.0.0 ·
   verified; reusable with this APK**.
3. Open the **Options** tab and tap **Restore recommended options**; the
   line above the options should turn green. The options then are:

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

   Unchecked - Test (0): nothing is under test in this version.

   Unchecked - Experimental (5):
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)

4. **Launch A: the menu and the FPS buttons.** On the **Play** tab tap
   **Reopen saved character**, log in, Enter Game. Then:
   - As soon as the world appears, open the menu and note roughly how many
     seconds until **Show FPS** can be tapped.
   - Use the menu as you normally would for a few minutes: is anything you
     use often in the wrong place, hard to find, or missing from Play?
   - Travel once to a zone you know and note the loading time.
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B: missions, to see how far the game gets.** Reopen, Enter Game.
   Then, as far as each step works:
   - Do you have a contact (the Contacts window, or a contact standing in
     the zone)? Talk to one and ask for a mission. Does the dialog open, and
     does a mission appear in your mission list?
   - Does the mission show a location, and does the map or compass point at
     a door? Go to the door and click it. I expect "the map could not be
     started" or a loading screen that returns you; note what you see.
   - If you have no contact or no mission is offered, note that and stop;
     that is a result too.
   - **Save character / log out**, **Finish and save report**, export.

If the game does not start at all: on the Options tab tap **Restore
recommended options** and try once more. If it still fails, untick **Finish
zone loading while the game loads the zone**; then **Keep a spare zone server
loaded for travel**; then **Faster number emulation in zone servers**; then
**Fast server** once, and tell me which launch worked. Either way, on the
Setup tab tap **Recover interrupted reports** and export the top report. If
an error box appears in the game, tap **Ignore** (not Stop Program), note
what it says and keep going.

If a trip fails (the game says the map could not be started, or the loading
screen returns you to where you were), travel again: the second try starts
the zone the ordinary way. Tell me which trip it was.

## Report

The exports of each launch, the times you noted, and what you saw. Fields I
will read:

- `character_observer_metrics.native_ready_to_observation_ms` (7,174 and
  8,945 in 0.13.82; expected under 3,000) and `character_zoning.ready_peeks`.
- `character_zoning.transfers[].character_status.resume_utc_ms` against
  `arrival_observed_utc_ms` (up to 9.7 s apart in 0.13.82).
- `enhancement_preservation.status` (`verified` or `changed_in_play`).
- For launch B: `character_reopen.external_maps.supervisor.requests` (a mission request has
  `is_static` 0, its `map_name` and `mission_info`), the zone server's
  console and the DbServer's console around the door click, and the hero's
  saved task rows.

Details: `HANDOFF-X86.md`, section "0.13.83 (98)".

CI (build 45466729870 at `de54a1b54`, every runtime run with the x87 option):
zone change 45485919306 passed. Default options 45492202751: zone server
start 365.1 s for a new character, 23.9 s reopened (0.13.82: 371.1, 23.9).
Spare run 45497903372 with late loading and the third zone server: both
arrivals read from the zone servers' console (5 records, none from the log
file) and recorded 19.5 s and 10.8 s after the typed command (0.13.82: 27.1
and 24.1 s), the effect of acting on the line within half a second. CI
cannot see the menu: it was compiled and its layout checked by tests, never
run on Android before this release. APK run 45503102987: 93,618,442 bytes,
sha256 `c0e9843e...cb3437dc`, signer unchanged, its 51 guest files equal the
commit.
