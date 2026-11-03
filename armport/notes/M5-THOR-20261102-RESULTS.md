# Thor results: King's Row regression report — 2026-11-02

Development is paused at the user's request. This records the supplied exports
and diagnosis only; no implementation, workflow dispatch or APK handoff is requested.

## Inputs and exact scope

| Export | Bytes | SHA-256 | Meaning |
|---|---:|---|---|
| coh-atlas-gameplay-20261103-010459.zip | 17,218,519 | d9420a3219737f309ed6737408e63aa5ecf134569a46de32e3e5cecfc3ca5205 | Reopen, Atlas → King's Row → Atlas, committed save, cleanup failure |
| coh-atlas-gameplay-20261103-010516.zip | 2,369,446 | de3c0c29a4927e79b8e9d99bf22ed2941c396c79bd38a43f924cc1e83a8448d6 | Setup complete; no gameplay session, zero decoded frames |

The filename dates are UTC; the gameplay occurred on November 2 in
America/Chicago. Both reports identify **0.13.44**. The gameplay session is
`d2ae95388c54479384dac85ef23bb073`, using the ARM64 client, standard graphics and
Turnip at 800×600. Guest identity names executable `2caf815f…db6e` and package
`bba31da1…52bf`, matching the .44 candidate. The second report's x86/software
defaults describe setup, not a second play test or a pre-port comparison.

**User result:** “Kings row is still functioning poorly, worse than before the
arm port.” Record this as an unresolved experience/acceptance failure. These
exports do not contain a matched pre-port gameplay run, so they cannot quantify
the regression or attribute it to a particular patch.

## Measured results

| Area | Result | Evidence |
|---|---|---|
| Tap → native connection observed | 604.299 s, about 10 min 4 s | android-client-report.json: character_connected_observed_uptime_ms minus started_uptime_ms |
| Client folder scan | 217.712 s; 212,496 files, 10,639 folders | guest/client-evidence/armport_stdio.txt:6 |
| King's Row cold preparation | 656.024 s | character-zoning.json: preparations[0].preparation_elapsed_ms |
| Python preparation / native-readiness phase | 304.188 s / 349.794 s | same preparation record; these are separate stages |
| Largest runtime preparation components | cold data mirror 231.218 s; beacon graph 57.096 s | map-startup-observation.json: maps["5"] |
| Transfer after preparation | 54.908 s | character-zoning.json: transfers[0].elapsed_ms |
| Request → observed King's Row arrival | 711.056 s, about 11 min 51 s | transfers[0].total_to_native_arrival_ms |
| Resident return to Atlas | preparation 8.444 s; transfer 50.413 s; total 59.130 s | preparations[1], transfers[1] |
| King's Row rendering after load | 19.95–29.94 FPS; 25.63 FPS weighted over 11 complete windows, 1,423 frames / 55.53 s | armport_stdio.txt:760–781 |
| Atlas rendering after return | 21.55–26.13 FPS; 24.59 weighted over six complete windows, 740 frames / 30.09 s | armport_stdio.txt:801–812 |
| Save after zoning | committed SQL, identity/powers/costume/enhancements preserved | latest-report.json: character_reopen; Android character_saved_event |
| Session result | actual interaction passed; overall cleanup_failed | guest stage actual_client_interaction; Android status/app_error |

Rendering summaries exclude the first partial window after each ready marker.
King's Row map.start → ready.sent took 27.131 s (lines 664/754); return Atlas
took 27.782 s (783/795). Those are client map-loading spans, not server ticks or
the complete transfer durations. The two loading-spanning FPS records were
1.39 FPS / 42.53 s and 0.49 FPS / 35 s. There were also 19 sub-5-FPS windows
before the King's Row client map load. Do not present a whole-session average,
which includes preparation/loading/menu periods, as King's Row gameplay FPS.

The renderer log identifies **Zink/Turnip on Adreno 740**, not the software
renderer. Raw conversion cost was 10,459 ms cumulative, maximum 2 ms per measured
conversion, over the entire receiver lifetime. This does not measure complete
presentation latency or prove the GPU/display path incapable of stalling.

## Why the experience can still be poor

**Established:** the client is ARM64, but both zones still use the retained
7,475,200-byte x86 MapServer, SHA-256
`fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363`.
The King's Row console identifies the WoW64 path. The port has not removed the
translated server/runtime work. Atlas remains resident when King's Row runs;
status queries show Atlas uptime of 16–17 minutes after the destination transfer.

**Leading hypothesis:** simulation/update delivery can stall independently of
the client's rendered frames. Around 25.6 rendered FPS during this short King's
Row visit does not establish smooth server-driven NPC/car movement. Concurrent
zone processes and shared Wine/PRoot overhead are plausible contributors; this
capture does not measure their simultaneous gameplay CPU or Wine requests.

**Additional evidence, limited to preparation:** 68 destination-process samples
span 343.878 s. Sampled task CPU counters increase by 115.41 CPU seconds; process
RSS rises from 207.80 to 1,768.07 MiB (peak 1,772.25 MiB). System-wide counters
increase by 17,747 swap-in pages, 289,318 swap-out pages and 18,104 major faults.
This supports possible memory/I/O contention during cold preparation. It does
not isolate COH as the cause, prove disk swapping (Android can use zram), or
measure post-arrival gameplay. RSS includes shared pages and is not PSS.

The preparation scheduler reports all three temporarily deprioritized threads
restored from nice +5 to 0, `restore_complete=true`. These samples end before
departure; there is no evidence of a permanently lowered destination priority.
Neither temperatures nor clock throttling are captured.

**Not established:** the exact cause of the user's worse-than-pre-port
experience. There is no server-metrics.jsonl, owned-processes.json or native
longest-tick/file-load telemetry here. A single completed-tick counter is not a
rate. Approximately 30-second stock native position observations are telemetry
cadence, not proof that the game updates only every 30 seconds. Sequencer
“Reading” lines precede cache lookup and do not count disk reads. Spawn-content
warnings exist, but their timing cost and relation to this regression are unknown.

## Save and cleanup are separate results

The ordinary save after returning to Atlas was committed at about 01:03:49 UTC.
The guest confirms preserved character identity, powers, costume and enhancements;
`forced_stop_before_save=false`. No unhandled client fault is recorded in the
captured console.

Cleanup remains a confirmed failure. `wine_process_cleanup` reports repeated
EACCES reading worker 18736 in group 18730 on three attempts, then
`persistent_live_permission_denied`; owned-process reaping is unproved.
The final failure is “Atlas data cache return lacks proved owned Wine cleanup.”
An additional observation reports “Cache inventory: Linked private cache
directory refused.” Wine-prefix shutdown and PostgreSQL graceful shutdown
succeeded. These later cleanup failures do not establish the cause of earlier
King's Row stutter or prove that leftover processes preceded this session.

## Handoff disposition

- M5 acceptance remains blocked by the user's King's Row result and cleanup.
- The .45/.46 changes were not exercised by these .44 exports. Separately,
  .46 at `8dc2a66d` passed build 40929292200, retained runtime 40945708189 and
  APK 40952408285; Claude comment 6508052528 says this is CI evidence, not review.
  There is no newer formal handoff approval or .46 device result on PR #8.
- Future diagnosis, only after the user resumes development, needs matched
  pre-port/ARM64 gameplay evidence and per-zone tick/CPU/pressure observations.
  Previous-zone retirement and synchronization changes remain experiments to
  qualify, not demonstrated solutions.
- This update changes documentation and summarized evidence only. No build,
  code fix, runtime change, merge or release was initiated.

The original ZIPs remain in the user's uploaded Library files
`libfile_a281fa85c9b48191a5e779facbb46dda` and
`libfile_2d0d30b01ee8819194a5df0e9a011cb5`. Do not commit raw private profiles,
process environments or full report archives. Summary: ../evidence/20261102-thor-results.json.
