# Thor test: COH Atlas Gameplay 0.13.56 (ARM64 client): zone travel fix

0.13.56 fixes the 0.13.55 monorail crash: the first zone the database server
had to start stopped it on an error box (`weeklyTFcfg.c`, `currentWeek`).
Every zone start reads a weekly task force file the game data does not have;
the app now supplies an empty one. Everything else is 0.13.55: test sheet
[THOR-TEST-0.13.55.md](THOR-TEST-0.13.55.md). Evidence:
[HANDOFF-X86.md](HANDOFF-X86.md), "0.13.56".

CI: CI_SUMMARY

## Steps

1. Install 0.13.56 over 0.13.55, then tap **Set up / update runtime** once.
2. Reopen the hero in Atlas Park with `Game's own zone travel` ticked.
3. Take the monorail to King's Row: the loading screen should appear right
   after you pick the stop and stay until King's Row is ready (about 3–4
   minutes the first time). Note the time.
4. In King's Row, walk through the tunnel to Skyway City (or take the monorail
   to Steel Canyon): loading screen again, then the new zone (NPCs will not
   move there). Note the time.
5. Return to Atlas Park by monorail. Save/logout, Finish, **export**.

If an error box like 0.13.55's appears, tap **Ignore** (not Stop Program),
note what it says (file, line, expression) and keep going; export at the end.

## Report

The export, the loading-screen times, and anything odd: a loading screen that
never ends (wait at least 6 minutes, then export), "map failed" messages, an
error box. Fields I will read: `character_zoning.stock_travel` (starts, stops,
arrivals), the supervisor's requests and decisions,
`external_maps.weekly_tf_config`, and the DbServer console.
