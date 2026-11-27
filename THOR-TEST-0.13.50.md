# Thor test: COH Atlas Gameplay 0.13.50 (ARM64 client)

The ARM64 client is the main client from 0.13.50 (user decision, 2026-11-03).
`x86 client (fallback)` stays selectable in case an ARM64-only game-breaking
bug needs a reversion. Evidence for each change: [HANDOFF-X86.md](HANDOFF-X86.md)
and [armport/PERFORMANCE-PATH.md](armport/PERFORMANCE-PATH.md). Qualifying CI
runtime 41704290931 (passed; no bin rebuilds on reopen, story arcs 470/957/3528).
King's Row zoning is not exercised in CI, so the trip is the main thing to test.

## What changed since 0.13.49

| Change | Default | Expected effect |
|---|---|---|
| ARM64 client is the default client | ARM64 | Same FPS as the 0.13.49 test (mean 45-48 in world) |
| Share server data between zones | on | Atlas and King's Row read one read-only copy of 15 data folders (128,765 files). CI: the private copy took 31 s instead of 99.5-106 s, so King's Row's first preparation (360 s+ on 0.13.49) should fit the 420 s limit |
| Skip server-only folders in the client's file scan | on | The client's upfront scan leaves out `scripts.loc` and `server/`. CI: client start 81.7 → 71.8 s; the Thor scan is about 3x slower than CI's, so expect roughly 20-30 s less to the login screen |
| Client asset checks | always | Unchanged supplements are checked once, not twice: about 40 s less |
| Stale-cache recovery fix | always | A cache left by an unproved cleanup is reused instead of rebuilt (the 6 min first start of 0.13.49) |

## Steps

1. Install 0.13.50 over 0.13.49 (in-place update; keeps the hero, database and
   imported assets). Tap **Set up / update runtime** once and wait for it to
   finish (about 2.5 minutes on 0.13.49): the new APK carries a new runtime, and
   Reopen refuses to start until it is installed. No asset re-import is needed.
   Then open the options and check: `ARM64 client`, `Fast mode`,
   `Raise the frame cap to 60 FPS`, `Share server data between zones` and
   `Skip server-only folders` are ticked. Leave `Start King's Row in the
   background` and `Lower the waiting zone server's priority` unticked, so a
   direct trip is tested.
2. **First start (one-time rebuild).** Reopen the hero. The first start after
   the update rebuilds the server data and builds the shared copy, so it is
   slow (about 10-12 minutes to Atlas). Log in as soon as the login screen
   appears. Play briefly, then take the monorail to King's Row. The first trip
   prepares King's Row from scratch: expect several minutes on the monorail
   screen. Walk around King's Row, take the monorail back to Atlas, then
   save/logout, Finish and **export**.
3. **Second start (the one to measure).** Reopen the same hero. Note the time
   from tap to the login screen and log in promptly. Take the monorail to
   King's Row again (it should reuse the King's Row data and be faster), then
   back. Save/logout, Finish and **export**.
4. Report anything that looks different from 0.13.49 in the world: missing
   NPCs, contacts or missions (the client scan now skips `scripts.loc` and
   `server/`, which the client source never reads), story arc or contact text,
   costumes, powers and ragdolls.

## If something fails

- King's Row trip fails again: export, then retry once with `Start King's Row
  in the background` ticked and wait about 10 minutes in Atlas before the trip.
- Client problems that look data-related: untick `Skip server-only folders`
  and retry. Server problems: untick `Share server data between zones`.
- Keep every export, including failed ones. Report fields that answer the open
  questions: `character_zoning` (trip phases), `shared_server_data` in the
  guest report, the client log's `ARMPORT_FOLDER_CACHE_V1 phase=scan/skip`
  lines, and `character_zoning.wine_priorities`.
