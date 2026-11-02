# Thor startup capture

This procedure does not establish that the one-minute target passed. Use only the exact source commit, APK SHA-256, workflow and independently authenticated server-package rollback in the final handoff. Version 0.13.47/versionCode 62 is reserved; no APK is available at this checkpoint. The earlier `e563` pipeline failed staging and is not an installable candidate.

## Install and hold conditions fixed

1. Finish the current session with **Save character / log out**, wait for **Saved character verified · tap Finish now**, then **Finish and save report**. Wait for completion and export the report, including cleanup status.
2. Install the qualified candidate over the existing app, preserving app data, character and imported assets. Run **Set up / update runtime** once. Record setup/update/cache-generation time and storage separately; it is not a process-cold result.
3. Retain the ARM64 client, renderer, graphics settings/resolution, controls, assets and character. Record fan/performance mode, charging state and battery level, and hold them consistent. Test gameplay offline after setup.

The normal UI does not restore an identical disposable save snapshot between repetitions. Keep the character, costume, powers and progress fixed during timed launches; ordinary save/login metadata will still advance. Exact identical-save-snapshot comparisons remain unestablished through this UI. Do not edit SQL, recreate THORHERO or restore an unverified copy.

## Collect every attempt

Use **2 · Reopen saved THORHERO**, then normal **COHLOCAL / offline** login and select the existing character. The initial map follows its committed saved destination. **Start test** and **Stop test** mark manual observations; they do not start the startup clock.

For each attempt record an ID (`A1`, `K1`), saved destination, reboot/update/cache state, previous completed cleanup, fan/power conditions and errors. Export failed and slow attempts too. Record movement, collision, NPC/combat and responsiveness observations separately; missing observations remain unmeasured.

| Condition | Minimum for a claim | Required state |
| --- | --- | --- |
| Process-cold Atlas with installed assets | Five attempts | Previous owned maps, DbServer and PostgreSQL stopped; persistent caches retained |
| Process-cold King's Row with installed assets | Five attempts | Same stopped-session state; character saved there |
| Post-reboot launch | Separate check | Reboot following verified normal save/cleanup; record cache state |
| Cold destination while another zone runs | Five per claimed destination | Real monorail; destination absent, dependencies running |
| Resident-map return | Report separately | Destination server remained alive; never count as cold |
| First setup/cache generation | Separate cost/storage report | No reused-cache result presented as first initialization |

Perform five Atlas reopens, each followed by ordinary save/Finish and completed cleanup. Then use the real monorail to King's Row, save there, and perform five King's Row reopens. Keep timed launches free of combat/reward changes. Use a separate correctness session for movement, collision, NPCs, combat/rewards, save/reopen, both monorail directions and saved destination. Repeating cold zoning requires stopped sessions between repetitions; a same-session return is normally resident.

A retained-cache launch can be process-cold when its server is stopped. Initial guest dependency state `not_observed` does not certify stopped PostgreSQL/DbServer: check previous cleanup and current ownership/startup evidence. Do not count an uncleared failed session as a fresh cold start.

## Finish and export

1. Release controls; choose **Save character / log out**, wait for **Saved character verified · tap Finish now**, then **Finish and save report**. Wait until the operation is no longer busy.
2. Choose **Reports / export**, select the attempt in **Retained reports · newest first** (UTC timestamps), and save the complete ZIP with its ID and notes. Retain every original ZIP.
3. For stalls/failures, preserve the error and report. Use **Abort operation** only when needed, wait for cleanup, then export. Use **Recover interrupted reports** after interruptions. Do not routinely force-stop, clear storage or delete the character. Missing startup/cleanup evidence stays missing.

Programmed success labels do not certify usable movement, rendering, combat or one-minute physical performance.

## Clock and resource scopes

| Field | Meaning |
| --- | --- |
| `android_startup_timing.service_receipt_to_map_ready_seconds` | **Primary for normal initial launch:** Android `elapsedRealtime` at the first `onStartCommand` entry, before action validation/preparation, to receipt of the guest's existing owned completed-native-tick plus fresh DbServer endpoint/readiness observation. Includes Android preparation, guest/runtime preparation and event-delivery delay. |
| `ui_action_to_map_ready_seconds` | Optional app action-handler timestamp to that same Android receipt; includes service scheduling. This is not a physical finger timestamp. |
| `ui_action_to_client_world_ready_seconds` | Optional same app action to accepted native client-world-ready observation, including manual login/selection. Does not prove a movable character. |
| `service_receipt_to_client_world_ready_seconds` | Same Android service receipt through client-world-ready observation; movement remains unmeasured. |
| Guest `request_to_map_ready_seconds` | Narrower diagnostic: starts when the guest supervisor receives its request. Excludes earlier Android preparation. Use this boundary separately for guest cold-destination requests; never substitute it for the initial Android primary. |
| Guest `process_spawn_to_map_ready_seconds` | Launcher spawn request to the existing owned readiness observation. |
| Guest `runtime_database_route_seconds` | Contiguous private-profile/PostgreSQL → Wine/intervening setup → ODBC/private DbServer preparation → DbServer ready/schema snapshot; not exclusive CPU time. |
| Guest `dependency_start_seconds` | Declared ODBC/private-runtime/DbServer subinterval; earlier PostgreSQL/Wine preparation is excluded. Read its stored scope. |
| Guest `request_to_client_world_ready_seconds` | Guest request to native client-world-ready observation; excludes earlier Android work and does not prove movement. |
| `ARMPORT_SERVER_STARTUP_V1` | Separate Windows QPC clock from native main entry through named phases. Excludes work before main. |

Android timing points use one `elapsedRealtime` clock, including system suspend. Unobserved endpoints stay null. The initial Android map event accepts only this session's initial, nonresident map 1 or 5; zoning/resident returns retain their separate guest rows. Never subtract guest monotonic, Android elapsedRealtime/uptime, UTC or native QPC points from one another or add overlapping intervals. A video/stopwatch may provide a separately labelled physical tap-to-visibly-movable observation.

`owned_launch_memory_at_first_native_ready` records only the exact owned Linux launch leader's `VmHWM` (lifetime peak through the status read) and current `VmRSS` at its first sampled ready observation. It excludes other Wine/FEX workers, DbServer, client and PSS. It is not aggregate MapServer peak memory. Unavailable `/proc` observations remain unavailable; historical Android exit PSS/RSS and setup memory are not substitutes.

Optional `android_startup_timing.thermal_observations` contains two sparse snapshots, at service receipt and map-ready receipt: Android thermal **severity** and raw battery temperature in deci-degrees Celsius. Severity is not temperature; battery temperature is not CPU temperature. Missing sensors stay null/unavailable. These snapshots do not establish a continuous trace, CPU temperature or absence of throttling.

The outer ZIP contains `android-client-report.json` and usually `guest-output/latest-report.json` plus `guest-report.zip`. Interrupted carriers may instead retain `android-recovery-checkpoint.json`; recovery attribution remains explicitly unverified. Guest timing rows are under `character_reopen.map_startup_timing` (or `character_creation`). Owned memory is under that character object's `map_startup_observation[map_id]` (also aliased at the guest root). Nested `client-evidence/map-startup-observation.json` retains `maps[map_id]`. Full native rows are in nested `client-evidence/character-atlas-console.txt` and non-active `character-zoning-map-1-console.txt` / `character-zoning-map-5-console.txt`; use native map ID/PID because the retained “atlas” filename can contain King's Row. These rows are not in `server-metrics.jsonl`.

After transferring exports, extract observations offline from the repository root:

```sh
python3 armport/scripts/summarize_thor_startup.py A1.zip A2.zip K1.zip --output thor-startup-observations.json
```

The extractor retains raw Android clocks, failed/pending/resident guest rows, scoped memory/thermal observations, recovery status, duplicate-session warnings and separate native phases. It promotes the primary interval only for consistent, attributed Android reports; recovery clocks remain visible without a success/attribution claim. It makes no acceptance verdict or qualifying-run count. Every claimed run must be at most 60 seconds under declared conditions and pass correctness requirements; retain slower attempts and failures.

## Restore the server package

After verified save/Finish cleanup, install the separately authenticated rollback APK identified in the final handoff, then run **Set up / update runtime**. It must restore the predecessor modern game package/MapServer, not merely change client architecture. Preserve app data/imports; never uninstall or clear storage. APK installation alone does not activate the restored runtime. Verify the restored server-package identity in its report and perform ordinary save/reopen. A same-versionCode update can install over the candidate when the final rollback has matching identity/signing; no rollback APK is available at this checkpoint.
