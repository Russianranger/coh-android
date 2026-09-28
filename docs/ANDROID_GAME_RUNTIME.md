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

The completed job log shows the last successful map status query at 04:15:50 UTC.
The next query printed only its startup timestamp at 04:16:52, before its normal
command-line and error-log initialization output. Atlas continued through
encounter groups, script markers and door animation points, ending at
`Retrieving AutoCommands..`. Captured PostgreSQL sessions were idle with no
active transactions. This does not establish a SQL lock or an AutoCommands
root cause; inspect the query's early startup path and the full service captures.

The expanded evidence artifact was uploaded, but local extraction and independent
verification were blocked when the workspace disconnected. See the
[job-log failure receipt](android-evidence/game-runtime-failure-36375412599.json)
for its GitHub-reported identity. Download and verify this artifact before
changing runtime source or accepting cleanup. The create/save/restart/resume
milestone remains unqualified.
