# Thor test: COH Atlas Gameplay 0.13.66 (ARM64 client): navigation maps for every zone

Pets and NPCs plan their way with each zone's navigation map (the game's
"beacons"). 0.13.65 had maps for Atlas Park, King's Row and Mercy Island only.
0.13.66 takes them from a separate navigation map pack that covers every zone
(64 zones: every static zone except Atlas Park and King's Row, which keep
their own maps). You import it once, like the asset pack, and it stays
imported across later APK updates while its version stays the same.

The app checks the pack against hashes this APK carries. Each zone's map is
installed when that zone first starts in a session, after the app checks it
against your phone's zone world; the first zone of a session may take up to
about a minute longer, later zones only a few seconds. A map that does not
match is skipped and recorded, and that zone starts without pathing (as
before). Without the pack, every zone other than Atlas Park and King's Row
starts without pathing, Mercy Island included (its map moved into the pack).

Everything else is 0.13.65: [THOR-TEST-0.13.65.md](THOR-TEST-0.13.65.md).
Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.66".

CI: CI_SUMMARY

## Steps (update in place: no uninstall; the asset pack stays imported)

1. On the phone, download `COH-Navigation-Maps-1.0.0.zip` (1.44 GB, one file)
   from https://github.com/Russianranger/coh-android/releases/tag/coh-navigation-maps-v1.0.0
   and keep it in Downloads.
2. Install 0.13.66 over 0.13.65. Your imported assets and the database profile
   (with Ralakar) stay.
3. Open the app. Below the asset line it shows **Navigation maps 1.0.0 ·
   import maps part(s)**. Tap **Import asset or map pack part** and pick the
   downloaded zip. Wait for **Navigation maps 1.0.0 verified**; the line then
   reads **Navigation maps 1.0.0 · verified; reusable with this APK**. The
   import needs about 3.4 GB of free storage while it runs; afterwards the maps
   take 1.44 GB and you can delete the zip from Downloads.
4. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
5. **2 · Reopen saved character**. Log in with `COHLOCAL / offline`, select
   Ralakar, **Enter Game**.
   - Summon your pet. Pick an enemy some distance away, target it and order
     the pet to attack: it should walk or run to it and fight.
   - Attack an enemy from range: it should come toward you around obstacles.
   - If you can, travel to another zone with the game's own travel (for
     example the ferry to Port Oakes) and try the pet there too.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**.
6. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report (it holds
Android's reason).

## Report

The export of step 5 and the storage report, whether the pet walked to the
enemy (and in which zones), and anything odd. Fields I will read: the app
report's `navigation_map_pack` (`bound`), the guest report's
`zone_tree_preparation.beacon_graph` (one entry per zone you entered: `status`
`installed_verified_graph`, `origin` `navigation_map_pack`, `elapsed_seconds`),
the map server logs (no "Beacon file not loaded"), `app_error` and the storage
report's `android_process_exit_history`.
