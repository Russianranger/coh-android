# Thor test: COH Atlas Gameplay 0.13.54 (ARM64 client): save check, shared server memory

0.13.54 is 0.13.53 plus a corrected save check and one experiment, off by
default. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.54".

## What changed since 0.13.53

| Change | Default | Expected effect |
|---|---|---|
| Save check for ordinary play | always | A session where you train, pick a power, receive a Day Job or other automatic power, earn XP and influence, or have a temporary power expire now passes the reopen check. Both of your 0.13.53 sessions would have passed; the tests use their saved rows. A save that loses a power, a level, XP or slots still fails |
| `Shared server memory (experiment: zone servers share game data)` | off | The zone servers stop parsing and holding their own copy of the shared game data; the first one builds a shared copy and the next one maps it. If Wine cannot provide the shared mapping, each server falls back to private memory, as today. Expected (unproven): King's Row starts faster with Atlas running and the two servers use less memory together |
| Server memory counted once | always | `server-metrics.jsonl` rows gain `pss_kib` every 30 s (memory shared between processes counted once), next to `rss_kib` |

CI (runtimes CI_R0, CI_RT, CI_RS): CI_SUMMARY

## Steps

1. Install 0.13.54 over 0.13.53, then tap **Set up / update runtime** once.
2. **Session 1 (option off, as before):** reopen the hero, play a little (a
   power, some XP), take the monorail to King's Row and back. Save/logout,
   Finish, **export**. The save check should pass.
3. **Session 2 (option on):** tick `Shared server memory`. Reopen the hero,
   wait in Atlas until King's Row has been prepared (or take the monorail), go
   to King's Row and back. Note whether King's Row was ready sooner than in
   session 1, and anything odd (a server that does not start, missing NPCs,
   a crash). Save/logout, Finish, **export**.
4. Untick `Shared server memory` afterwards unless session 2 was clearly
   better.

## Report

Exports from both sessions and how King's Row's start felt with the option
on. Fields I will read: `shared_heap` in the guest report (the option and
each zone server's console decision: shared heap reserved, or the fallback
line), the MapServer startup phases (`sequencer_info`, `definitions`), and
`rss_kib`/`pss_kib` per server in `server-metrics.jsonl` (memory with both
zones loaded, 0.13.53: 6.3 GB total).
