# Thor test: COH Atlas Gameplay 0.13.54 (ARM64 client): save check, shared server memory

0.13.54 is 0.13.53 plus a corrected save check and one experiment, off by
default. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.54".

## What changed since 0.13.53

| Change | Default | Expected effect |
|---|---|---|
| Save check for ordinary play | always | A session where you train, pick a power, receive a Day Job or other automatic power, earn XP and influence, or have a temporary power expire now passes the reopen check. Both of your 0.13.53 sessions would have passed; the tests use their saved rows. A save that loses a power, a level, XP or slots still fails |
| `Shared server memory (experiment: zone servers share game data)` | off | **Leave it off.** In CI the shared copy is created (1024 MB reserved, Atlas ready 12-15 s later than without it), but both CI sessions with it on went wrong after login: once the logout never reached the server, once the client stalled for 267 s and the new-character welcome dialog came back 30 times. Without it, the same checks passed at both builds. Kept in the app for later study only |
| Server memory counted once | always | `server-metrics.jsonl` rows gain `pss_kib` every 30 s (memory shared between processes counted once), next to `rss_kib` |

CI at a66b533f6: build 41937339905; default runtime 41948749075 and test-server
runtime 41952941661 passed character creation and reopen; shared server memory
runtime 41956900853 failed reopen (above; 41931773800 at the previous head
failed creation logout); APK 41960891294. The on-demand zone DbServer (your
device's DbServer plus the map-request hook, still off in this APK) passed
creation and reopen in CI for the first time (41961253764).

## Steps

1. Install 0.13.54 over 0.13.53, then tap **Set up / update runtime** once.
2. Leave `Shared server memory` unticked.
3. Reopen the hero, play a little (train or pick a power, earn some XP), take
   the monorail to King's Row and back. Save/logout, Finish, **export**.
   The save check should now pass.

## Report

The export, and whether the reopen check passed. Fields I will read: the
reopen save check (`gameplay_progress`), and `rss_kib`/`pss_kib` per server in
`server-metrics.jsonl` (memory shared between processes counted once; with
both zones loaded, 0.13.53 RSS: 6.3 GB total). PSS tells how much of that is
really private to each server, which decides whether a pre-loaded spare zone
server fits within 16 GB.
