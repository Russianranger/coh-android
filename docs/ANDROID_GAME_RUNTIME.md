# Hosted Atlas character persistence on ARM64

This follows the accepted [Wine DbServer milestone](ANDROID_DBSERVER.md).
Run `36424870915` completed all 18 ARM64 guest stages: Atlas readiness,
fresh creation, live influence 12345, committed protocol logout, same-cluster
service restart, exact-name resume and a second committed save. All 128 process
captures closed and owned cleanup passed. Its original workflow remains red
because the host validator required a `child_exited` field that the format-1
bridge never emits. The corrected validator checks the real verified uint32
exit code, excluding `STILL_ACTIVE` (259), and passes against the unchanged,
hash-verified report and every exported capture. Independent
[CI revalidation 36430794421](https://github.com/Russianranger/coh-android/actions/runs/36430794421)
passed at `73b1aeef8dfaa901d45763f7e4361054db777632`; the hosted runtime
evidence is accepted with that correction. See the
[acceptance receipt](android-evidence/accepted-game-hosted-36424870915.json) and
[recovery checkpoint](ATLAS_RECOVERY_20260928.md).
Startup reliability remains under investigation; this successful attempt had
one readiness query take 86.757 seconds within the existing 90-second limit.
The accepted Thor 0.1.5 diagnostic APK remains the device baseline.

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

Subsequent recovery runs captured socket state and exact last PostgreSQL query
text before cleanup. A separate native observer also returned thread contexts,
but comparison against the exact Wine binaries found inconsistent registers
and stack memory: these can be cached FEX/WOW64 contexts, not current execution.
See [the recovery evidence](ATLAS_RECOVERY_20260928.md). The useful next diagnostic
is direct DbServer main-thread dispatch progress, including foreground SQL,
network monitoring and console operations. It must distinguish whether the
AutoCommands request reaches its foreground enumeration query. No further
deadline increase or functional runtime patch is supported by the evidence.
The complete guest restart/resume sequence subsequently passed in run
`36424870915`; its corrected host evidence validation is tracked above.
