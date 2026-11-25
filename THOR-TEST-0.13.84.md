# Thor test: COH Atlas Gameplay 0.13.84 (ARM64 client): the tabbed menu, and mission maps as a test option

0.13.84 adds mission maps to 0.13.83, which was published a few hours
earlier (2026-11-24) and has not been on the Thor. This sheet covers both;
if you have not installed 0.13.83, skip it.

## What is new since 0.13.82

From 0.13.83 (from your 0.13.82 test and requests):

- **Three tabs.** *Play*: the commands of a session, in the order they are
  used. *Options*: the launch options. *Setup*: runtime, asset import,
  controller, storage and test tools. The state lines stay above the tabs.
- **Four option categories**: Recommended, Optional, Test, Experimental.
  "Restore recommended options" sets Recommended, Test and Experimental and
  leaves Optional as you set it.
- **FPS buttons sooner again** (9-11 s in 0.13.82): the app acts on the zone
  server's line within half a second.
- **Enhancements gained in play** no longer mark a launch failed.

New in 0.13.84:

- **Test option "Start mission maps"**, off by default. With it, a mission
  door starts the mission's map the way a trip starts a zone. The zone you
  came from stays loaded for the way out. Without it a mission is refused as
  before ("the map could not be started").
- **A hero whose session ended inside a mission can be reopened.** Before,
  the app refused such a hero's saved position. The hero reopens in the zone
  the mission was entered from.
- **Longer sessions**: up to 128 zone or mission starts and 48 spare zone
  servers per session (32 and 12 before).

What CI showed about missions, and what it could not:

- **Shown in CI, with the fast server and the spare server as on the Thor**
  (run 45544977220): a debug command gave the hero a level 1 office
  mission; the game asked for the mission's map; the warm spare server took
  it and had it ready 2.1 s later; the game loaded it in 1.2 s and the hero
  was inside 5.6 s after the command. The hero left through the mission's
  exit command, was back in the zone 10.4 s later, and the save was
  verified. On the 0.13.36 server without a spare (run 45503799391) a
  mission map of the same set took 67.7 s to start.
- **Not shown in CI:** CI has no zone asset pack, so the mission ran from
  the Atlas Park data, not from the shared zone data the Thor uses (which
  gets 123 more files with this option). A mission taken from a contact and
  entered by its door, enemies, objectives and completion were not
  exercised. The checkbox and the app's side were compiled and unit-tested,
  not run on Android. A second mission in one session and saving inside a
  mission were not run.
- **Known gaps:** mission maps have no navigation maps yet, so pets and
  enemies inside a mission may stand still or move in straight lines. The
  game knows a zone's mission doors only once that zone has been started,
  so a contact may place a mission only in zones you have already visited.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.84 over the installed version.
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

   Unchecked - Test (1), ticked only for launch B below:
   - Start mission maps (test; needs the game's own zone travel and the imported zone assets)

   Unchecked - Experimental (5):
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)

4. **Launch A: the menu and the FPS buttons** (recommended options, mission
   maps off). On the **Play** tab tap **Reopen saved character**, log in,
   Enter Game. Then:
   - As soon as the world appears, open the menu and note roughly how many
     seconds until **Show FPS** can be tapped.
   - Use the menu as you normally would for a few minutes: is anything you
     use often in the wrong place, hard to find, or missing from Play?
   - Travel once to a zone you know and note the loading time.
   - **Save character / log out**, **Finish and save report**, export.
5. **Launch B: a mission.** On the Options tab tick **Start mission maps**
   (the line above the options turns amber and names it; that is expected).
   Reopen, Enter Game. The zone start in this launch takes a few minutes
   longer once: the shared zone data is prepared again with the mission
   files. Then, as far as each step works:
   - Talk to a contact and take a mission whose door is in the zone you are
     in. Does a mission appear in your list, and does the map point at a door?
   - Wait one minute after entering the world (the spare loads), then click
     the mission door. Note the loading time and what you see: does the
     mission map appear, are there enemies, do they fight, do they move?
   - Play as far as it goes: defeat enemies, click an objective, try to
     complete the mission. Note anything that does not respond.
   - Leave by the mission's exit (or the Exit button when the mission is
     complete). Note the loading time back to the zone.
   - **Leave the mission before you save.** Then **Save character / log
     out**, **Finish and save report**, export.
6. On the Options tab tap **Restore recommended options** afterwards.

If the mission door says the map could not be started, or the loading screen
returns you to the zone: try the door once more, then carry on in the zone
and export as usual; the report says why.

If you are stuck inside a mission (no exit, loading never ends): open the
menu, **Save character / log out** if it responds, otherwise **Finish and
save report**; on the Setup tab tap **Recover interrupted reports** and
export. The hero is kept and reopens in the zone the mission was entered
from. That launch will be reported as failed; that is expected.

If the game does not start at all: untick **Start mission maps**, tap
**Restore recommended options** and try once more; then the fallback order
of the earlier sheets (**Finish zone loading while the game loads the
zone**, **Keep a spare zone server loaded for travel**, **Faster number
emulation in zone servers**, **Fast server**). If an error box appears in
the game, tap **Ignore** (not Stop Program), note what it says and keep going.

## Report

The exports of each launch, the times you noted, and what you saw. Fields I
will read:

- `character_observer_metrics.native_ready_to_observation_ms` (7,174 and
  8,945 in 0.13.82; expected under 3,000) and `character_zoning.ready_peeks`.
- `character_zoning.stock_travel.mission_maps`: `starts` (map, mission info,
  the zone it was entered from, when the hero arrived), `refused` (why),
  `ended`, `arrivals`, `returns`.
- `character_reopen.external_maps.supervisor.requests` (a mission request
  has `is_static` 0) and `stock_travel.starts` (whether the spare took it,
  how long until the mission's server was ready).
- `zone_tree_preparation` (`mission_collision_files` 123 and how long the
  one-time preparation took).
- The mission server's console (missing files, "Beacon file not loaded") and
  the game's `ARMPORT_GROUP_LOAD_V1` line for the mission map.
- `enhancement_preservation.status` (`verified` or `changed_in_play`).

Details: `HANDOFF-X86.md`, section "0.13.84 (99)".

CI: build 45521275964 at `ec0c2c48c`; zone change 45532798713; trusted 45537091983 (zone server 370.8 s new, 23.9 s reopened); spare 45541284416 (arrivals 19.4 s and 10.7 s after the command); mission with the fast server and spare 45544977220; APK APK84_RUN.
