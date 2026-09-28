# Hosted Atlas character persistence on ARM64

This follows the accepted [Wine DbServer milestone](ANDROID_DBSERVER.md). The
new hosted gate is implemented; real ARM64 qualification is pending. The first
real attempt reached DbServer readiness and progressed into Atlas loading, then
failed a startup status-query deadline. A retry with a 90-second startup query
also failed. Its final Atlas output reached AutoCommands retrieval; character
execution had not started. It does
not change the accepted Thor 0.1.5 APK or claim Android game execution.

The workflow `.github/workflows/android-game.yml` creates a separately
identified composite runtime from these immutable inputs:

| Component | Accepted run | Role |
|---|---:|---|
| ARM64 Wine/FEX/PostgreSQL inputs | 36364550345 | Accepted M2 runtime |
| Normal Wine-compatible DbServer | 36369485666 | Fixture disabled |
| MapServer and creation TestClient | 36088012664 | Stock reference binaries |
| Resume TestClient | 36297542986 | Exact name, creation disabled |
| Generated database schema | 36088012666 | Accepted 99-table schema |

The new PE32 `TestClientBridge.exe` starts one unchanged TestClient, verifies
its Windows process identity against the launcher pipe and console, observes
its output, and forwards ordinary launcher commands. It does not implement
character creation, mutation, logout, SQL persistence, or game networking.
Its receipt binds the current repository commit, source hashes, build flags,
executable bytes and imports. The composite package records every donor and
explicitly selects the previously accepted Wine normal CrashRpt dependency.

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
