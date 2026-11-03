# x86 client: next Thor device baseline

This is the device-test target after the `x86-track` integration. It is a test
sheet for Claude's next reviewed build, **not an APK handoff or evidence that the
integration head has run on the device**. See [HANDOFF-X86.md](HANDOFF-X86.md) and
[issue #10](https://github.com/Russianranger/coh-android/issues/10).

The user selected the x86 track on 2026-11-02. The app defaults to `x86 client`;
explicitly select it because an existing installation can retain an earlier
ARM64 preference. `ARM64 client (experimental)` remains available and shelved.
The x86 Win32 servers retain PhysX/ragdolls. Do not use historical ARM64
FPS figures as an x86 gameplay baseline. Sources: `ClientActivity.java`'s
architecture selector, `ClientRuntime.clientArchitecture(Context)`, and
[armport/PERFORMANCE-PATH.md](armport/PERFORMANCE-PATH.md).

## Setup and retained state

1. Use Claude's subsequently reviewed in-place update, retaining app data,
   the usual account, saved hero, database, imported Assets 1.0.0 and Wine prefix.
   Record versionName/versionCode, source SHA, runtime/build IDs, renderer,
   resolution and cache state in each export. No new package is supplied here.
2. Select `x86 client`; retain the same renderer, resolution, graphics and
   display cap across comparisons. Do not combine a client-lane change with
   unrelated settings changes. Do not lower resolution for this baseline.
3. After setup, conduct gameplay locally with networking disabled. Record any
   setup/update network requirement separately from offline gameplay.

## Cold-start and zoning capture

1. Start with no live owned game/server session after normal proved cleanup.
   Record whether the server-data cache is present or stranded. A warm data
   cache and a resident server are different states. Preserve failed runs;
   never claim a cold run from a resident server or delete state to hide failure.
2. Reopen the same saved character, enter Atlas, then take the monorail to
   King's Row promptly. Record tap/service receipt → server ready, tap → usable
   world, destination request → ready/arrival, and observed ability to move.
   Native readiness does not prove a movable player. See the existing
   [startup capture guide](armport/THOR-STARTUP-CAPTURE.md) for clock boundaries.
3. Observe NPC/car movement, combat, defeats, ragdolls, enhancement awards and
   controls. Return to Atlas; label that transfer resident if Atlas stayed live.
   Record memory/swap observations and thermal data only when present, retaining
   unavailable/partial markers. System-wide counters do not identify a culprit.
4. Save/logout, Finish and export even on failure. Reopen the same hero and
   verify identity, location, powers, costume and enhancements persisted. Preserve
   committed-save success separately from a later cleanup failure.
5. Keep outer reports, guest reports, stage/zoning consoles, server metrics,
   ownership/cleanup receipts and cache-return errors. Confirm x86 was actually
   launched. Do not substitute ARM64 `ARMPORT_FRAME_RATE_V1` numbers for missing
   x86 game FPS; report x86 gameplay FPS as **unmeasured** unless captured directly.

For a performance claim, Claude needs matched runs and repeated cold starts;
the existing guide asks for five Atlas and five King's Row runs. This handoff
does not request that the user repeat tests now. The known .44 reference is an
ARM64-client run with x86 servers: King's Row cold preparation 656.024 s,
request→arrival 711.056 s; see
[the dated evidence](armport/notes/M5-THOR-20261102-RESULTS.md).

## Failure rules

Keep the exact failure and report. In particular, `persistent_live_permission_denied`
and `Atlas data cache return lacks proved owned Wine cleanup` remain open; do
not weaken ownership proof or recycle that cache as though cleanup succeeded.
The integration's namespace/disappearing-task port is not evidence that the
Thor EACCES defect is fixed. No ≤60-second cold-start, FPS, thermal or memory
improvement is measured at this integration head.

## Performance options (0.13.48 candidate, branch `x86/perf-round2`)

`Fast mode (PRoot seccomp, experimental)` is now **on** by default. In CI
(41584980465 vs 41588867344) it made MapServer startup 26-32% faster with no
failures. Uncheck it to get the old compatible mode back. The guest report's
`proot_mode` records the mode and the cost of a test system call.
`Start King's Row in the background (zoning)` (off by default) prepares and
launches King's Row about 20 s after Atlas is live, but only with at least
3 GiB of memory available (else `skipped_low_memory`). The phases are recorded
in `character_zoning.background_prestart`. A trip during native loading is
labelled `prestarted_loading`.
`Lower the waiting zone server's priority (zoning, experimental)` (off by
default) weights a resident MapServer's threads +10 nice while the player is in
the other zone (also a background-started King's Row once it ticks), and
restores them before a trip back. Periods and restore results are in
`character_zoning.idle_resident_maps`. Compare NPC/car smoothness with it on
and off.
`Fast server data loading (trusted bins)` (on by default) only acts when the
APK carries the instrumented MapServer. It skips the data-folder scans and date
checks for CRC-matching prepared `.bin` files; `trusted_bins` records whether it
was used. In CI (41605600310 on vs 41610459604 off, same servers) the reopen
Atlas start fell from 130 s to 94 s; a new character's first start barely moved.
`Raise the frame cap to 60 FPS in the world` (on by default) sends the
sidebar's `/maxfps 60` once, quietly, when a reopened character's world views
are captured; the report records `gameplay_60fps_requested` and the lifecycle
line `gameplay_60fps_auto`. The native launch cap stays 30/10 until a client
rebuild. A higher client frame rate takes CPU from the MapServers: if NPCs or
cars stutter, uncheck it, or tap `30 FPS`, and note which setting was used.
A cache left behind by a cleanup that could not prove it finished is reused in
a later session only when no same-uid process outside that guest is alive
(`stranded_generation_recovered`). The earlier session's failed cleanup is
still reported as failed.
