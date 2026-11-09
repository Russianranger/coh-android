# Thor test: COH Atlas Gameplay 0.13.65 (ARM64 client): pets in Mercy Island

In 0.13.63 (export 20261109-154935) Ralakar's pet followed him but did not walk
to the enemy he ordered it to attack; it attacked only enemies already near it.
Mercy Island's map server said "Beacon file not loaded for map:
maps/City_Zones/V_City_01_01/V_City_01_01.txt".

Pets and NPCs plan their way with the zone's navigation graph (the game's
"beacons"). Atlas Park and King's Row have graphs. Every other zone starts from
one shared world on the phone, which had none, so nothing there could plan a
path. 0.13.65 carries Mercy Island's graph. The game's own map server generated
it on a Windows build machine from exactly that shared world (GRAPH_SUMMARY).
When Mercy Island starts, the app first checks the graph against the world on
your phone and then installs it; this check reads every collision file once,
so the first Mercy Island start of a session may take up to about a minute
longer. If the graph and the world differ, the app skips the graph, records
why, and Mercy Island starts as in 0.13.64 (pets still follow but do not walk
to a target).

Other zones (except Atlas Park and King's Row) still have no graph. Everything
else is 0.13.64: [THOR-TEST-0.13.64.md](THOR-TEST-0.13.64.md). Evidence:
[HANDOFF-X86.md](HANDOFF-X86.md), "0.13.65".

CI: CI_SUMMARY

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.65 over 0.13.64 (or 0.13.63). Your imported assets and the
   database profile (with Ralakar) stay.
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. **2 · Reopen saved character**. Log in with `COHLOCAL / offline`, select
   Ralakar, **Enter Game**.
   - Summon your pet. Pick an enemy some distance away (not next to you),
     target it and order the pet to attack. The pet should walk or run to it
     and fight.
   - Attack an enemy from range: it should come toward you around obstacles.
   - Play normally for a while: defeat a few enemies, so the save has
     experience to keep. Turning the camera quickly is still welcome.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**.
4. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report (it holds
Android's reason).

## Report

The export of step 3 and the storage report, whether the pet walked to the
enemy, and anything odd. Fields I will read: the guest report's
`zone_tree_preparation.beacon_graph` (map 71: `installed_verified_graph`, or
`not_installed` with its `error`), its `phase_seconds.zone_beacon_graphs`, the
Mercy Island map server log (no "Beacon file not loaded"), `app_error`,
`presentation_timing.rfb_update_rectangles_max`, `gameplay_progress` (the save
of step 3) and the storage report's `android_process_exit_history`.
