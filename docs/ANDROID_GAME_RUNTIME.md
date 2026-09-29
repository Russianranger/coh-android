# Hosted Atlas character persistence on ARM64

This follows the accepted [Wine DbServer milestone](ANDROID_DBSERVER.md).
**The loopback DbServer Atlas integration passed in run `36493722153`.** All
three jobs and all 18 runtime stages passed with both DbServer starts bound to
loopback, both committed saves, same-cluster restart and exact-name resume.
See the [combined acceptance](android-evidence/accepted-game-loopback-hosted-36493722153.json)
and [results below](#accepted-loopback-dbserver-integration).

The earlier full hosted ARM64 Atlas workflow passed in run `36460005201`. All three
jobs succeeded at `cfc8ac477e449037213d5242f43480acf4f1cb85`, including the
18-stage create/save/restart/exact-name-resume/second-save sequence and final
host validation. The [acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
binds the independently verified reports and captures. The earlier
`36454174481` workflow failure and its separate post-correction acceptance
remain preserved below. The accepted Atlas default remains donor `36451873322`.
The separate [0.2.0 DbServer test passed on Thor](ANDROID_SERVER_DEVICE_TEST.md#accepted-thor-results);
physical Android game execution, presentation and rendering
remain unvalidated.

The workflow `.github/workflows/android-game.yml` now prepares the separate
**MapServer and TestClient listener candidate** described below. Its new game
donors require fresh Windows and ARM64 qualification. The accepted DbServer-only
loopback result above is preserved. Assembly retains `accepted` as the default
for both the DbServer and game-listener profiles. The existing profiles use
these immutable inputs:

| Component | Accepted run | Role |
|---|---:|---|
| ARM64 Wine/FEX/PostgreSQL inputs | 36364550345 | Accepted M2 runtime |
| Loopback-profile DbServer | 36460867428 | Fixture disabled; qualified local bindings, dispatch observer and fixed-input mode |
| Default-profile DbServer | 36451873322 | Earlier accepted Atlas donor, retained for reproducibility |
| MapServer and creation TestClient | 36088012664 | Stock reference binaries |
| Resume TestClient | 36297542986 | Exact name, creation disabled |
| Generated database schema | 36088012666 | Accepted 99-table schema |

The PE32 `TestClientBridge.exe` starts one receipted TestClient, verifies
its Windows process identity against the launcher pipe and console, observes
its output, and forwards ordinary launcher commands. It does not implement
character creation, mutation, logout, SQL persistence, or game networking.
Its receipt binds the current repository commit, source hashes, build flags,
executable bytes and imports. The composite package records every donor and
explicitly selects the Wine donor's normal CrashRpt dependency.

The retained default Atlas profile uses the qualified fixed-input DbServer donor
`36451873322`, repository commit `53c6270dff8a0efcc6be09da756408504d8313bd`.
Its manifest SHA-256 is
`e4f8a66802f29643b13aec2228ada1549a80c22efa11de1549a9b145bb43e06b` and normal
executable SHA-256 is
`659e9072234f75ad02c8cac2636df93f5249ff1de385c1ed7d6c6fc0c04a453a`.
Its [acceptance receipt](android-evidence/accepted-dbserver-hosted-36451873322.json)
records successful Windows and ARM64 qualification, including default normal
schema startup and acknowledged fixed-input reload. The accepted hosted Atlas
sequence in `36460005201` uses this donor. Runs `36427680960` and `36428915900` used
the preceding diagnostic donor `36425508780`.
The Atlas attempts through `36420158506` used donor `36369485666`; their
first-save and failure evidence remains unchanged.

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
separate milestones. Keep the accepted 0.1.5 and 0.2.0 device diagnostics installed.
DbServer local listeners and Stop/rerun are now verified on Thor; MapServer/client
listener preparation and the combined Android game runtime remain separate work.

## Accepted loopback DbServer integration

After [0.2.0 passed on Thor](ANDROID_SERVER_DEVICE_TEST.md#accepted-thor-results),
the workflow now explicitly selects `--dbserver-profile loopback` for assembly
and validation. This accepted profile uses the exact qualified donor `36460867428`
(`eed2ce1f5388195f65a07853919761a93657aca6`). The default assembly profile and
accepted historical result retain donor `36451873322`; a profile manifest
cannot silently substitute either donor or downgrade the requested policy.

Both DbServer starts enable loopback binding, alongside the existing fixed-input
mode. Listener proof is required after main-thread dispatch initialization and
before Atlas starts: the same 13 required endpoints and optional crash-map TCP
6992 apply to the managed `-start 0`, fake-auth, no-queue, embedded-log setup.
The host independently reparses each complete DbServer stdout capture and checks
it against the phase receipt and pinned source-derived endpoint contract.
Missing, duplicate, substituted or wildcard endpoints fail qualification.

This is a separately identified **hosted-only** integration gate. The mandatory
private network namespace remains in place. The DbServer flag is cleared from
MapServer and client environments: the stock MapServer still binds wildcard
UDP 7001, and TestClient sends through implicitly bound UDP sockets. Their
listener policy and Android lifecycle integration must be addressed before a
physical Atlas candidate.

[Run 36493722153](https://github.com/Russianranger/coh-android/actions/runs/36493722153)
at `708878f78a3361b595dcc03a0c4b14fb6cd2e6c3` passed all three jobs and all
18 stages in 1,883.535869 seconds. Both DbServer starts recorded all 14 local
endpoints (13 required plus optional TCP 6992), and independent replay checked
both full stdout captures against the pinned source contract. Character
`TEST-60538` / container 1 resumed with creation disabled; influence 12,345 and
selected SQL rows survived restart. LoginCount progressed 1 → 1 → 2 through
the two independently committed protocol saves. All 122 process captures closed
with complete cleanup and zero owned processes or inspection failures.

First service readiness took about 17 minutes 32 seconds; restart readiness
took about 3 minutes 13 seconds. Both fixed-input acknowledgments and all four
inventory checks passed. The [receipt](android-evidence/accepted-game-loopback-hosted-36493722153.json)
binds the [raw report](android-evidence/game-loopback-arm64-36493722153.json) and
[preserved captures](android-evidence/game-loopback-evidence-36493722153.zip).
Independent replay used the exact tested validators, unchanged reports and
captures, and complete data/schema inventories. Executable payload checks were
performed by CI; this downloaded evidence contains their receipts, not all
executable bytes. The earlier accepted profile and evidence remain unchanged.

### MapServer and TestClient listener candidate

The next gate adds `COH_GAME_LOOPBACK_ONLY=1` to separately built MapServer,
creation TestClient and resume TestClient donors. The overlay changes staged
source only. Without the environment flag, the normal binding behavior remains;
invalid values refuse startup. The policy covers explicit IPv4 listeners and
the test clients' UDP sockets, including sockets which formerly bound implicitly
on their first send. It does not restrict outgoing TCP destinations or replace
the hosted network namespace.

`tools/prepare_game_loopback_source.py` stages `creation` and `resume` variants.
The resume variant retains the existing exact-name, creation-disabled behavior.
`tools/android/game/package_loopback_game.py` records the three executables,
both source receipts, fixture-OFF build configurations, symbols and dependency
closure against the accepted reference. Assembly requires explicit
`--game-listener-profile loopback --loopback-game PATH`; the donor, bridge and
composite must identify the same repository commit. The accepted reference,
resume donor and 0.1.5/0.2.0 APKs are retained.

The workflow runs native Windows socket contracts before building and then
qualifies the new composite through the full ARM64 sequence. Acceptance requires
actual socket address/type/port records from both MapServer starts and both
test clients, tied to owned service and client captures, along with the existing
character identity, SQL save, restart, resume and cleanup checks. A startup
acknowledgment alone is insufficient. This source preparation is not an Android
Atlas acceptance; the physical candidate still needs the steps below.

### Remaining preparation for a physical Atlas candidate

With the combined hosted gate accepted:

1. Complete the new MapServer and creation/resume TestClient listener
   qualification above. Cover MapServer's explicit UDP 7001 listener and
   TestClient's implicitly bound UDP sockets with native Windows contracts and
   the hosted persistence sequence. Preserve failure evidence if a gate fails.
2. Package the reviewed game assets plus authoritative repository text with
   exact inventories. The reviewed asset ZIP is 615,541,018 bytes; the combined
   tree is 173,011 files / 2,977,730,517 bytes. Prefer verified file-picker import
   of the existing ZIP. Its draft-release download currently requires CI
   credentials, which must not be embedded in the Android app. No new broad
   asset upload or public asset publication is required by this plan.
3. Add a separately identified Android Atlas test, retaining accepted 0.2.0.
   Use fresh owned state, foreground-service Stop handling, bounded startup
   deadlines and streamed support exports containing the game, service and hang
   captures. Determine storage and timeout limits from the actual packaged data
   and measured device timings, rather than inheriting the 30-minute DbServer
   limit unchanged.
4. Qualify the exact APK payloads on hosted ARM64, then collect a physical Atlas
   create/save/restart/resume pass, Stop with game services active, and fresh
   successful rerun with background checks. Keep rendering and human controls
   as separate milestones.

## Accepted full hosted workflow

[Run 36460005201](https://github.com/Russianranger/coh-android/actions/runs/36460005201)
at `cfc8ac477e449037213d5242f43480acf4f1cb85` passed all three jobs on
2026-09-28. Its [raw guest report](android-evidence/game-arm64-36460005201.json)
passed all 18 stages in 1,963.43549 seconds, from 17:48:08.291869 to
18:20:51.727359 UTC. Stock TestClient created `TEST48625` / container 1 / account
`CohAa82e8aaa56`, entered Atlas, observed live influence 12,345 and completed
the first independently committed protocol save before forced cleanup. Wine
and the same PostgreSQL cluster restarted without reseeding or restoration.
The resume client selected the same character at slot 0 with creation disabled
and a processed server update, then completed the second protocol save.
LoginCount progressed 1 → 1 → 2; selected SQL retained one `ents` row, one
`ents2` row, seven powers and 13 costume parts.

First service readiness took 1,118.015542 seconds and restart readiness took
194.370597 seconds. Independent Atlas readiness with current heartbeats was
observed for 31.421914 seconds. Both DbServer launches emitted the exact
fixed-input acknowledgment; all four input checks preserved 62 files /
4,402,846 bytes. The 99-table schema, 5,935 ordered columns, 58,272 attribute
IDs/names and full catalog remained stable. All 123 process input/output
captures closed; PostgreSQL stopped gracefully, the Wine prefix stopped, and
cleanup left zero owned processes or inspection failures.

The corrected bridge exit consumer ran in CI. Independent validation repeated
the full report, character/SQL capture and service-capture checks using the
exact tested validator modules, with unchanged report and capture bytes.
The [acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
and [captured evidence](android-evidence/game-evidence-36460005201.zip) preserve
this successful full workflow. The earlier failed workflow and its separate
post-correction acceptance remain historical evidence; the sibling DbServer
SIGSEGV remains unexplained. No generic Wine notification repair is established.

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

The next bounded diagnostic was required to capture simultaneous owned DbServer, Atlas
and status-query thread stacks, socket state, and exact last PostgreSQL query
text before cleanup. In particular, distinguish whether DbServer dispatched
the AutoCommands request and reached its foreground
`SELECT dbo.AutoCommands.ContainerId FROM dbo.AutoCommands ORDER BY containerid`.
No further deadline increase or runtime source change was justified by this
capture. The create/save/restart/resume milestone was unqualified at this checkpoint.

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
and regression tests were applied for the next run; full restart/resume validation
was still required. No upstream game-source change was needed for this harness mismatch.

This run's cold startup query returned after 78.833 seconds and Atlas completed
AutoCommands retrieval in 82.71 seconds. The prior 90-second failure did not
recur; it is not established as fixed. No deadline was increased for this run.
This attempt did not reach exact-name resume, post-restart row comparison or a
second protocol save, so it did not qualify the hosted gate.
Android gameplay, rendering and app integration remain separate gates.

The `wine-game-arm64-evidence` artifact (ID `10968627172`, 8,792,105 bytes)
was downloaded and its archive SHA-256 verified as
`d046ac6c71d6ed54df3c8672236d54b1bd9f55dbdb0dcc91d85940512bb6e810`.
All 16 files listed by the report's character, service and hang capture inventories
matched their byte counts and SHA-256 values. Both full service stdout captures
closed without overflow or truncation.

## Startup timeout reproduced with pre-cleanup evidence

[Run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed a startup query in the first
service phase after 13 preceding readiness queries had completed. The failing
query reached 90.041 seconds. It did not reach character creation or exercise the
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

The follow-on diagnostic uses [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md)
in a separately receipted DbServer build. They publish bounded main-thread
progress around startup, dispatch, SQL keepalive and console handling. Advancing
samples show progress; a stopped stage identifies an operation and its nested
calls, not a specific instruction or proof of deadlock. Markers remain inactive
unless explicitly enabled and do not change the intended game behavior.

[DbServer qualification run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
passed all three jobs. The [acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
binds the new donor package. Windows passed the enabled-record contract; the
ARM64 persistence fixture and normal schema gates passed with the observer
disabled. Atlas adopted this qualified package for the subsequent diagnostic,
requiring a fresh valid record at DbServer readiness and a distinct record after
restart. Enabled ARM64 publication was subsequently verified in `36428915900`
below. This is an evidence-gathering step, not a demonstrated startup fix or
gameplay result. At this checkpoint, the complete hosted
restart/resume/second-save gate and physical Android execution were pending.

## Diagnostic attempt stopped before game execution

[Run 36427680960](https://github.com/Russianranger/coh-android/actions/runs/36427680960)
at `82386fd48c2352a2ce65d5920f7857e8b92ec442` passed source, package and data
staging, then failed while building PRoot: the pinned talloc source download hit
a read timeout. The guest game diagnostic never ran, so this attempt produced
no runtime report or dispatch samples. It neither reproduced nor resolved the
intermittent DbServer startup stall. The
[infrastructure failure receipt](android-evidence/game-infrastructure-failure-36427680960.json)
preserves the failed build evidence.

The isolated download correction now permits at most three attempts for
transport failures, deletes partial bytes before retrying, and retains the
original size bound and required SHA-256. Hash mismatches and permanent HTTP
errors remain failures. Atlas tooling explicitly runs the retry regression
tests. The next run used the same qualified donor and passed this preparation
step; its log contains no observed download retry. The transport remedy does
not establish a game startup fix.

## Enabled ARM64 dispatch evidence localizes folder work

[Run 36428915900](https://github.com/Russianranger/coh-android/actions/runs/36428915900)
at `f32ccd7c0f1aa950d1f87ceb81ab09b2dba4e2ac` failed a startup query in the first
service phase after 13 preceding readiness queries completed. The query timed
out after 90.030 seconds. Eight setup stages passed, but Atlas readiness,
character creation and the restart correction were not reached in this run.
The earlier first creation and committed save remain valid partial evidence.

The [raw report](android-evidence/game-arm64-failed-36428915900.json) validates
enabled ARM64 source publication: at 13:40:22 UTC, DbServer PID 412 / main thread
416 published `NM_MONITOR`, sequence 28, loop 1. The
[pre-cleanup snapshot](android-evidence/game-hang-36428915900/snapshot.json)
then read the same mapped file at 13:55:20.897 and 13:55:23.957 UTC. Both reads
contained `FOLDER_CALLBACKS` (stage 30), sequence 2,449,552 and loop 43,741,
with identical raw-record hashes. This places the main thread in folder
callbacks or nested work during the observation. It does not identify the
specific nested call or prove a deadlock.

Separate, non-atomic native process/task samples showed `read` and `fchdir`
operations under PRoot. These indicate continuing native activity but do not
measure its throughput or identify the particular folder request. Kernel
stacks were permission-denied, and the descriptor cap omitted DbServer's file
descriptors. Saved WOW64 contexts remain unsuitable as live translated stacks.
DbServer, Atlas and the timed-out query were alive before cleanup; the query
was still alive after the 3.061-second capture. All 65 PostgreSQL sessions were
idle in `ClientRead`, with no active transactions. The foreground last query
was `;`, about 134.9 seconds old; the 64 workers' last queries were `COMMIT`.
Atlas's full stdout ended at `Retrieving AutoCommands..`.

Final PostgreSQL/Wine cleanup passed, all 57 process input/output captures
closed, and zero owned processes or inspection failures remained. The
[verified receipt](android-evidence/game-runtime-failure-36428915900.json)
binds the raw report, all three preserved hang files and all eight service/hang
capture hashes. The 8,738,855-byte archive has SHA-256
`bc51de6db5afa732bfd92ca57ffa9d68c12c16013aacaea66736317be110d0ce`.

The scoped response is the qualified opt-in [fixed-input DbServer mode](../database/wine-dbserver/FIXED_INPUTS.md),
which prevents watcher registration from startup while preserving initial reads
and lookup mode. Disabling callbacks alone would leave Wine accumulating
undrained notification records. Run `36451873322` qualified its package; Atlas
now requires a complete startup acknowledgment from each owned DbServer launch,
with the mode enabled only for DbServer. After private `servers.cfg` generation,
the harness binds the union of all 62 accepted schema inputs and the entire
staged `data/server/db` tree, including optional configuration files and empty
directories. Four snapshots must remain unchanged: before first startup, after
first save, before restart and after second save. The checks reject changed
bytes, replaced files/directories and inventory additions/deletions. Default
dynamic behavior remains available outside this controlled mode.

Both ARM64 attempts in earlier fixed-input qualification `36434692816` failed
before DbServer execution on talloc HTTP 503. The successful qualification used
the exact talloc source from accepted runtime `36364550345`'s authenticated
corresponding-source bundle. Atlas now uses that same recovery path and preserves
its extraction receipt; the PRoot compiler recipe and source pins are unchanged.

The subsequent run below exercised both game sessions with this mode; its
unchanged evidence passed strict revalidation after a host contract correction.
This does not establish a generic Wine notification repair. The accepted device
diagnostics are 0.1.5 and 0.2.0; Android game execution and presentation remain unvalidated.

## Hosted sequence accepted after host validator correction

[Run 36454174481](https://github.com/Russianranger/coh-android/actions/runs/36454174481)
at `8944bd598990b33b63a750a64ae448403e4542cd` has an **accepted runtime sequence
after host revalidation; the original workflow conclusion remains failure**. Its
[raw guest report](android-evidence/game-arm64-failed-36454174481.json) records
all 18 stages passed in 1,867.229988 seconds, from 16:57:11.550333 to
17:28:18.780321 UTC on 2026-09-28. Stock TestClient created `TEST01443` /
container 1 / account `CohA318dc5a821`, entered Atlas, observed live influence
12,345 and committed the first protocol save before forced cleanup. Wine and
the same PostgreSQL cluster restarted, Atlas became ready again, and the resume client selected
the same character at slot 0 with creation disabled and a processed server
update before the second protocol save. LoginCount progressed 1 → 1 → 2;
selected SQL retained one `ents` row, one `ents2` row, eight powers and 14 costume
parts. Atlas readiness was independently observed for 31.564746 seconds.

Both DbServer launches emitted the exact fixed-input acknowledgment. All four
input checks preserved 62 files / 4,402,846 bytes. All 122 process records closed
their input/output captures; PostgreSQL stopped gracefully, the Wine prefix
stopped, and cleanup left zero owned processes or inspection failures.
Independent character-capture and service-capture validation passed.

The original host validator rejected the first session because it required
`child_exited: true`, which the bridge does not serialize. The correction checks
the existing `child_exit_code` as a terminal DWORD and rejects `STILL_ACTIVE`
(259), while retaining identity, capture, pipe and save checks. Both clients
were forcibly stopped after their independently committed protocol saves and
recorded terminal exit code 125. The corrected full report, character-capture
and service-capture validators passed against the unchanged raw evidence.
A regression compiles the actual C result serializer and checks its output
through the real guest stop validation and host consumer. The runtime, bridge
producer and evidence bytes are unchanged; only the host exit check was corrected.
The [acceptance receipt](android-evidence/accepted-game-hosted-36454174481.json)
binds the correction and revalidation separately from the original
[failure receipt](android-evidence/game-runtime-failure-36454174481.json) and
[captured evidence](android-evidence/game-evidence-36454174481.zip).
The original Actions run remains failed. The prior startup failures remain
historical evidence, and this result does not establish a generic Wine
notification repair.

The separate sibling DbServer run `36454174374` failed attempt 1 with SIGSEGV
(`-11`) after `PG_TEST_COMPLETE rebuild` and teardown messages. Its byte-identical
package passed all 28 stages on attempt 2. The
[failure](android-evidence/dbserver-runtime-failure-36454174374.json) and
[repeat](android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
receipts retain the intermittent, unexplained failure; the repeat does not
establish a repair. Atlas donor `36451873322` remains unchanged.

The separate loopback listener package passed hosted qualification in
[run 36460867428](android-evidence/accepted-dbserver-hosted-36460867428.json).
It preserves Atlas's default donor `36451873322`. The subsequent separate 0.2.0
test qualifies physical DbServer execution on Thor and retains the accepted
0.1.5 installation. Physical Atlas execution remains unvalidated.
