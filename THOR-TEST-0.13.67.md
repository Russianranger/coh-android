# Thor test: COH Atlas Gameplay 0.13.67 (ARM64 client): shorter launches, Mercy Island pathing

Two things change. First, 0.13.66 refused Mercy Island's navigation map on the
phone, so your pet did not walk to its target and NPCs stood still; 0.13.67
fixes the check that refused it. Second, the launch no longer repeats work
whose inputs have not changed. Your 0.13.66 session took 12 min 43 s from the
tap to the world; these were the repeated parts (export 20261110-213045):

| Repeated work in 0.13.66 | Cost | 0.13.67 |
|---|---|---|
| Re-checking installed files that had not changed | 93 s every launch | skipped while the folders are unchanged |
| Client's file scan (160,114 files) | 134 s after every APK update | the saved list survives an update |
| Copying the zone's server data | 75 s every zone start | handed back at the end of a session, reused next time |
| Navigation map check | 21 s, then the map was refused | the map installs; its 8,711 input files are hashed once (launch A), later only listed |
| Waiting for the texture list, then for the GPU check | 20 s + 31 s | both run at the same time |

**The first launch on 0.13.67 does all of this once more** (it records what it
checked), and launch A also hashes Mercy Island's map inputs for the first
time (565 MB; not timed on a phone yet), so launch A may be no shorter than
0.13.66. The gain shows from the second launch. Not changed yet: the zone
server's own start (227 s in your session); that is the next release.

With **Raise the frame cap to 60 FPS in the world** on, the world now starts
at the 60 cap (0.13.66 switched about 75 s after the world appeared).

Limit of the skipped re-check: it reads each folder's listing, not each file.
A file added, removed, renamed or replaced is seen and the step runs in full
again; a file rewritten in place is not (installed files are read-only, and
every step runs in full again after 30 days or with a new APK's assets).

Everything else is 0.13.66: [THOR-TEST-0.13.66.md](THOR-TEST-0.13.66.md).
Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.67".

CI: CI_EVIDENCE_PLACEHOLDER (the chain is running; filled when 0.13.67 is published).

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.67 over 0.13.66. The app should still show **Navigation maps
   1.0.0 · verified; reusable with this APK**.
2. Leave the options at their defaults.
3. **Launch A.** **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**.
   - Summon your pet, target an enemy some distance away and order the pet to
     attack: it should walk or run to it and fight.
   - Attack an enemy from range: it should come toward you.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**. Export the report.
4. **Launch B** (the one that should be shorter). Close the app from recents,
   open it and repeat step 3 exactly. Export the report.
5. Optional **Launch C**: tick **Fast server start (test server with trusted
   bins)**, repeat step 3, export the report, then untick it. This is the
   server CI runs; I want one phone time for it before making it the default.
6. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report.

## Report

The exports of launches A and B (and C if you ran it), the storage report,
whether the pet walked to the enemy, and roughly how long each launch felt
from the tap to the world. Fields I will read:

- `zone_tree_preparation.beacon_graph["71"]`: `status`
  `installed_verified_graph` with `input_files_hashed` 8,711 in A and 0 in B
  (or `reused_verified_graph` in B), and its `elapsed_seconds`.
- `launch_receipts`: `ran_in_full` / `no_receipt` in A, `reused` in B (a
  `reason` there names the folder that changed).
- The client's folder index line: a miss in A, a hit in B.
- The zone data cache: returned at the end of A, reused in B
  (`return_refused` or a refusal with `foreign` rows otherwise).
- `wine_priorities` samples: `busiest_threads`, `cpus_allowed`, `cgroup`
  (does the fastest core run the game), and `memory_trace`.
- `state_inventory` and the storage report (leftover state from old sessions).
