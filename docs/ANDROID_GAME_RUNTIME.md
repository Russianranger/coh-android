# Hosted Atlas character persistence on ARM64

This follows the accepted [Wine DbServer milestone](ANDROID_DBSERVER.md). The
new hosted gate is implemented; complete ARM64 qualification is pending. The
best completed run passed Atlas readiness, fresh character creation, live
currency change and a committed protocol save, then stopped at the restart port
check. The latest diagnostic reproduced the earlier startup query timeout and
captured the live failure state. Exact-name resume and the second save remain
unproved on ARM64. No accepted Thor 0.1.5 APK changes or Android game execution
claims follow from these hosted results.

The workflow `.github/workflows/android-game.yml` creates a separately
identified composite runtime from these immutable inputs:

| Component | Accepted run | Role |
|---|---:|---|
| ARM64 Wine/FEX/PostgreSQL inputs | 36364550345 | Accepted M2 runtime |
| Normal Wine-compatible DbServer | 36425508780 | Fixture disabled; qualified opt-in dispatch observer |
| MapServer and creation TestClient | 36088012664 | Stock reference binaries |
| Resume TestClient | 36297542986 | Exact name, creation disabled |
| Generated database schema | 36088012666 | Accepted 99-table schema |

The new PE32 `TestClientBridge.exe` starts one unchanged TestClient, verifies
its Windows process identity against the launcher pipe and console, observes
its output, and forwards ordinary launcher commands. It does not implement
character creation, mutation, logout, SQL persistence, or game networking.
Its receipt binds the current repository commit, source hashes, build flags,
executable bytes and imports. The composite package records every donor and
explicitly selects the Wine donor's normal CrashRpt dependency.

The next Atlas run adopts the qualified diagnostic DbServer donor
`36425508780`, repository commit `41f3aff596826e22e2774375e11590de895ca33d`.
Its manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632` and normal
executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.
The earlier Atlas attempts below used donor `36369485666`; their first-save and
failure evidence remains unchanged.

The full reviewed data inventory contains 173,011 files / 2,977,730,517 bytes.
The preparer verifies the externally pinned asset receipt plus immutable text
inputs. The guest uses a private copy, overlays the accepted generated schema,
and creates caches and disposable credentials only there.

The intended acceptance sequence is:

1. Start the private PostgreSQL database, normal DbServer and Atlas MapServer
   inside a mandatory network namespace with only loopback enabled.
2. Observe independent DbServer-confirmed Atlas readiness for at least 30 seconds.
3. Create a fresh fake-auth character through the stock TestClient and enter Atlas.
4. Set influence to 12,345 through the normal command protocol and observe the
   live server response for the same character/account.
5. Request protocol logout, then verify independent committed SQL and disconnected
   character state before any forced cleanup. `QuitNow` alone is not a save proof.
6. Restart the same cluster and services, compare committed selected rows, and
   resume that exact character with creation disabled and a processed server update.
7. Complete a second protocol logout/save and verify preserved rows, influence,
   and LoginCount 1 → 1 → 2. Close every owned process and input/output capture.

This gate does not yet cover the longer Windows sustained-session/transfer
checks, Android listener binding or app lifecycle integration, an Android game
surface, accelerated rendering, or a human-operated client. Those remain
separate milestones. Keep the accepted device diagnostic installed while this
hosted runtime is being qualified.

## First real attempt

[Run 36372777933](https://github.com/Russianranger/coh-android/actions/runs/36372777933)
passed all 48 tooling checks, the PE32 bridge build/native contracts, package
verification and full data staging. The guest copied and verified its private
data in 296.868 seconds. DbServer became ready, but a 25-second Atlas status
query timed out during cold map loading. All 101 process captures closed;
PostgreSQL and Wine stopped cleanly, with zero remaining owned processes or
inspection errors. See the [failure receipt](android-evidence/game-runtime-failure-36372777933.json).

All 103 geometry-warning lines retained from that attempt also occur verbatim
in the accepted Windows reference logs. The exact data inventory matches; no
source patch or preload-skipping flag is justified by these warnings. The retry
adds live stage progress, bounded full service captures, less frequent cold
startup queries and longer startup-only deadlines. Save/resume and current
heartbeat checks remain unchanged; the overall guest deadline stays 3,600 seconds.

## Extended-query retry

[Run 36375412599](https://github.com/Russianranger/coh-android/actions/runs/36375412599)
at `52e11f87b0298c9195f276e4586fe9f53ce07635` passed all 60 tooling checks
and the Windows bridge build. Thor, PostgreSQL backend, Windows character
persistence and Atlas transfer regression workflows also passed at that head.
The ARM64 runtime again failed `game-query-first-ready timed out`, now after
90 seconds. Increasing this allowance alone did not resolve the failure.

The expanded Atlas capture proves successful connection and registration with
DbServer, followed by completed geometry, encounter, script and door loading.
Its final output is `Retrieving AutoCommands..`. That source path waits
synchronously for a DbServer container reply. The DbServer request handler can
enumerate AutoCommands through foreground ODBC on its dispatch thread.
Captured PostgreSQL sessions were idle with no active transactions, so no
active database-side SQL query or lock was observed. The precise blocked
client operation remains unknown.

The killed status query printed only its startup timestamp. This does not
localize it to early initialization: that timestamp is written to stderr,
while the command line and initialized-error-log message use stdout, which
`-nogui` leaves buffered. Killing the process can discard that output.

The local execution workspace disconnected, so the fixed evidence archive
was inspected on a separate read-only hosted job. [Inspection 36377967143](https://github.com/Russianranger/coh-android/actions/runs/36377967143)
verified the complete archive SHA-256 and all four service-capture hashes,
recovered the exact raw report, and exposed registration and final wait markers.
Both full service stdout files were closed without overflow or truncation.
The report proves graceful PostgreSQL stop, stopped Wine prefix, all 58 process
input/output captures closed, zero remaining owned processes, and zero ownership
inspection errors. The [failure receipt](android-evidence/game-runtime-failure-36375412599.json)
and [raw report](android-evidence/game-arm64-failed-36375412599.json) preserve
these facts. Character execution did not begin.

The next bounded diagnostic must capture simultaneous owned DbServer, Atlas
and status-query thread stacks, socket state, and exact last PostgreSQL query
text before cleanup. In particular, distinguish whether DbServer dispatched
the AutoCommands request and reached its foreground
`SELECT dbo.AutoCommands.ContainerId FROM dbo.AutoCommands ORDER BY containerid`.
No further deadline increase or runtime source change is justified yet.
The create/save/restart/resume milestone remains unqualified.

## Recovery diagnostic (2026-09-28)

The continuation workspace and branch were recovered at `18522cada`. No active
hosted build remained. The next run now captures failure state **before** stopping
the failed query or cleaning up the game services. It records the private
database's exact last query text, wait events and timestamps; token-owned Linux
process/task state and socket inodes; and a separate PE32 observer's Windows x86
contexts, stack words and module addresses. Unavailable or truncated observations
are explicitly reported. These observations are not symbolized stack traces.

The observer has its own source/PE32 receipt and is staged separately from the
accepted game package. Snapshot collection is time/size bounded, occurs only on
failure and preserves the existing cleanup path. The game source and accepted
runtime donors are unchanged. The startup timeout has not been extended again.

Source inspection narrows interpretation: the status-query process waits for the
initial DbServer handshake before its command's timeout applies. That status
handler and map registration are memory/network operations. DbServer's main loop
also performs synchronous foreground SQL keepalive before network dispatch.
The failed query began before Atlas reached AutoCommands, so the final printed
Atlas message does not establish which DbServer operation blocked. Capture and
inspect the simultaneous state before selecting a runtime correction.

A separate latest Thor tooling run failed its synthetic process-exit assertion.
The test helper now uses kernel pidfds to distinguish exited, unreaped children
from live processes even when `/proc` exposes another PID namespace. A real child
regression covers that distinction; this is a test correction, not a change to
the accepted app's lifecycle behavior.

## First ARM64 creation and protocol save; restart gate failed

[Run 36416020268](https://github.com/Russianranger/coh-android/actions/runs/36416020268)
at `324823be6ca9713bdc60446eb31596004ff6286a` completed with an overall failure
on 2026-09-28. Its [unaltered guest report](android-evidence/game-arm64-failed-36416020268.json)
records independently confirmed Atlas readiness for 31.519 seconds, fresh
`TEST02279` / container 1 creation and Atlas entry, live influence 12,345, then
protocol logout and committed SQL before forced cleanup. LoginCount was 1;
selected SQL held one `ents` row, one `ents2` row, seven powers and 17 costume
parts. The first session's bridge proof completed before its subsequent stop.

Wine shutdown, owned-process cleanup and graceful PostgreSQL stop passed. The
same cluster restarted successfully. `game_services_restart` then failed
immediately with `[Errno 98] Address already in use`, before a replacement
DbServer or Atlas process was launched. The failure snapshot found zero owned
Wine processes and zero game-role database sessions; the Windows observer found
no game targets. Final cleanup also passed, with zero remaining owned processes
and zero ownership inspection failures. No owned socket table remained to
identify the rejecting port or state directly. Review confirmed a preflight
mismatch: the pinned Wine TCP socket implementation enables native
`SO_REUSEADDR`, while the Python TCP preflight did not. An isolated Linux
experiment reproduced the same bare-bind error with TCP TIME_WAIT, then passed
with TCP address reuse while still rejecting active wildcard/loopback listeners
and occupied UDP ports. That matches the hosted failure but is not a captured
TIME_WAIT observation from the hosted run. The narrow TCP preflight correction
and regression tests were applied for the next run; full restart/resume validation is still
required. No upstream game-source change is needed for this harness mismatch.

This run's cold startup query returned after 78.833 seconds and Atlas completed
AutoCommands retrieval in 82.71 seconds. The prior 90-second failure did not
recur; it is not established as fixed. No deadline was increased for this run.
Exact-name resume, post-restart row comparison and a second protocol save remain
pending, so the hosted create/save/restart/resume gate is still unqualified.
Android gameplay, rendering and app integration remain separate gates.

The `wine-game-arm64-evidence` artifact (ID `10968627172`, 8,792,105 bytes)
was downloaded and its archive SHA-256 verified as
`d046ac6c71d6ed54df3c8672236d54b1bd9f55dbdb0dcc91d85940512bb6e810`.
All 16 files listed by the report's character, service and hang capture inventories
matched their byte counts and SHA-256 values. Both full service stdout captures
closed without overflow or truncation.

## Startup timeout reproduced with pre-cleanup evidence

[Run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed the first startup status
query after 90.041 seconds. It did not reach character creation or exercise the
restart preflight correction. The prior run's first creation and committed save
remain valid partial evidence; this rerun does not complete the hosted gate.

The new [snapshot](android-evidence/game-hang-36420158506/snapshot.json) was taken
before query termination and service cleanup. DbServer, Atlas and the query
were alive, and the query remained alive after the 2.945-second observation.
PostgreSQL had 65 idle sessions waiting for client input, with no active
transactions. The foreground session's exact last query was `;`, completed
about 140 seconds earlier; the 64 workers' last queries were `COMMIT`. Atlas
again ended at AutoCommands retrieval. No active database-side SQL or lock wait
was observed.

The separate [Windows capture](android-evidence/game-hang-36420158506/windows-contexts.jsonl)
completed its APIs for three processes, 72 threads and 114 modules with zero
reported errors, no truncation and no forced probe termination. Inspection of
the pinned Wine/FEX `GetThreadContext` path shows that it supplies saved WOW64
context, not the current translated x86 execution state. Preliminary
DbServer address decoding points to `NMAddLinkList` /
`clientCommLoginInitStartListening`, a startup path whose work had already
completed before DbServer readiness and subsequent successful status queries.
Those pointers therefore do not identify the live blocking operation, and no
main-loop correction is justified by this capture.

Linux inspection recorded 13 owned processes and 120 tasks. Kernel stack reads
were denied for all of them; these denials are preserved explicitly. Socket
tables were read without truncation, but the 512-descriptor cap limits inode
coverage. Final PostgreSQL/Wine cleanup passed, all 59 process input/output
captures closed, and no owned processes or ownership inspection failures
remained. The [failure receipt](android-evidence/game-runtime-failure-36420158506.json)
and [raw report](android-evidence/game-arm64-failed-36420158506.json) bind the
verified archive and all eight captured files. Its 8,736,139-byte artifact has
SHA-256 `811106aac6577990fd376f772ed411e80b579f39ac284e5883263969ec938487`.

The next diagnostic uses [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md)
in a separately receipted DbServer build. They publish bounded main-thread
progress around startup, dispatch, SQL keepalive and console handling. Advancing
samples show progress; a stopped stage identifies an operation and its nested
calls, not a specific instruction or proof of deadlock. Markers remain inactive
unless explicitly enabled and do not change the intended game behavior.

[DbServer qualification run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
passed all three jobs. The [acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
binds the new donor package. Windows passed the enabled-record contract; the
ARM64 persistence fixture and normal schema gates passed with the observer
disabled. Atlas now adopts this qualified package for the next diagnostic,
requiring a fresh valid record at DbServer readiness and a distinct record after
restart. Enabled ARM64 publication is still pending. This is an evidence-gathering
step, not a demonstrated startup fix or gameplay result. The complete hosted
restart/resume/second-save gate and physical Android execution remain pending.
