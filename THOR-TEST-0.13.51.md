# Thor test: COH Atlas Gameplay 0.13.51 (ARM64 client)

Follows the 0.13.50 test (exports 20261103-215454 and -220758). Evidence:
[HANDOFF-X86.md](HANDOFF-X86.md), "Thor test of 0.13.50" and "0.13.51".

## What changed since 0.13.50

| Change | Default | Expected effect |
|---|---|---|
| Prepared Atlas and King's Row data is reused again | always | 0.13.50's second start rebuilt Atlas's data (cold copy 84 s and beacons 75 s instead of 9 s and 25 s). Expect Atlas ready in about 5 minutes and a faster second King's Row trip |
| 10 FPS while waiting at the monorail | always (ARM64 client) | While the next zone is prepared (input is held), the client draws at 10 FPS instead of 30-60, then returns to 60 when the zone is ready. Less heat, more CPU for the loading zone |
| Thermal samples | always | Android thermal status, thermal headroom and battery temperature every 30 s in the export |
| Server tick timing | always | Every 30 s, 4 s of tick timing for the zone you are in, plus which CPU cores the servers ran on. This is to find the King's Row NPC jumping |

The client's preparation was not moved earlier: with the data reused again, the
client and Atlas should finish within about 15 s of each other, so it would save
little (details in the handoff).

## Steps

1. Install 0.13.51 over 0.13.50, then tap **Set up / update runtime** once and
   wait for it to finish. No asset re-import is needed.
2. Options: same as 0.13.50 (`ARM64 client`, `Fast mode`, 60 FPS, `Share server
   data`, `Skip server-only folders` ticked; `Start King's Row in the background`
   and `Lower the waiting zone server's priority` unticked).
3. **Session 1 (direct trip).** Reopen the hero and note the time from tap to the
   login screen. The prepared data from 0.13.50 should be reused, so this should
   not be a slow first start; tell me if it is. Take the monorail to King's Row.
   While waiting at the station the game should drop to 10 FPS. **Stay in King's
   Row for at least 3 minutes** and note whether NPCs, cars and the train still
   jump, and whether it gets better after the first minute or two. Return to
   Atlas, save/logout, Finish and **export**.
4. **Session 2 (background start).** Tick `Start King's Row in the background`.
   Reopen, play in Atlas for about 8 minutes (King's Row loads meanwhile), then
   take the monorail. The trip should take about a minute. Again stay at least
   3 minutes and compare the NPCs with session 1. Note the device temperature in
   Atlas while King's Row loads. Save/logout, Finish and **export**.

## Report

- Times: tap to login screen, monorail trip, NPC behaviour over time, and the
  highest temperature you saw (and when).
- Keep both exports. Fields I will read: `android_thermal_samples`,
  `character_zoning.tick_probe` (gaps over 67 ms), `character_zoning.wine_priorities`
  (`last_cpu`, `cpu_max_khz`), `character_zoning.station_fps_cap` and the client
  log's `ARMPORT_FPS_CAP_V1` lines.
