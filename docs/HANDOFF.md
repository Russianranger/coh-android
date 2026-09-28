# City of Heroes Android handoff

Updated: 2026-09-28 (UTC). PostgreSQL controlled persistence, targeted stage1 inspection,
matching Windows packaging, base runtime assembly and data-only database schema
generation have passed their current checks. Normal fixture-OFF DbServer schema
initialization/export/reload and normal MapServer network save acknowledgements
have also passed against fresh PostgreSQL clusters.
The refreshed runtime and schema artifacts share repository commit
`775a0dd770adac045484805dbbb5f68054c7a354`. Ordinary asset-backed reference
comparison and Atlas Park protocol readiness have now passed. Fresh fake-auth
character creation, live currency change, protocol logout/save, database and
game-service restart, and exact-name short resume also passed in
[run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135).
The follow-on [sustained-session run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
also passed: exact-name resume, missing-name refusal without mutation, 66.953
seconds connected, restored live currency and a second protocol save.
The follow-on [Atlas transfer run 36297542986](https://github.com/Russianranger/coh-android/actions/runs/36297542986)
also passed: the same character moved map 1 → prestarted clone 101 → map 1,
preserved committed state at each arrival and completed the final protocol save.
The [primary M2 device diagnostic and headless client capability gate](THOR_DEVICE_ACCEPTANCE.md)
is now accepted on Thor with 0.1.5. The supplied combined report passed all twelve
stages, reused the database cluster and ready Wine prefix, and completed owned
cleanup with all 30 process input/output captures closed. The user also attests to
a preceding database-only pass; its separate archive was not supplied. Device
cleanup observed exited leaders with live owned workers, while the exact writer
of the earlier pipe was not inventoried. The next device gate is Stop followed by
a successful rerun; suspend/resume and memory checks remain pending and can
accompany the next candidate. The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md)
also passed in run 36369485666: 21 persistence check groups across 14 fixture
invocations, then two fixture-OFF schema exports with 99 tables, 5,935 ordered
columns, 58,272 exact attribute IDs/names and a stable catalog on reload.
All 28 ARM64 stages passed, with all 111 process input/output captures closed and
zero remaining owned processes or inspection errors. The
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36369485666.json)
binds the reports and inputs. Physical Android DbServer execution, Android
presentation and game rendering remain unvalidated. Managed Atlas MapServer and
diagnostic TestClient execution are now implemented in the separate
[hosted Atlas gate](ANDROID_GAME_RUNTIME.md). One ARM64 run passed the first
character creation, live currency change and committed protocol save, then
failed at the service restart port check. The latest game execution reproduced the
startup timeout and captured stationary `FOLDER_CALLBACKS` source markers;
native snapshots show continued operations, not a proven deadlock. Resume remains unproved.
The follow-on diagnostic DbServer package passed all three jobs in run
`36425508780`. Windows verified enabled dispatch-record publication; the ARM64
fixture/schema gate used the observer disabled. Atlas run `36428915900` then
verified enabled ARM64 publication with this qualified donor and captured the
folder callback boundary during the intermittent timeout.
The first attempt with that donor, run `36427680960`, stopped before game execution
when the pinned talloc download timed out during the PRoot build. A bounded
download retry is now applied. The next run passed dependency preparation with
no retry line observed; the transport remedy supplies no startup-fix evidence.
The reviewed asset ZIP has been uploaded to a draft release and downloaded by
the hosted runner with its exact size/hash verified. That attempt then stopped
on Windows manifest line endings before game execution. The byte-preserving
checkout fix is applied and run 36176806895 completed successfully: all 56 fresh
template outputs matched, then Atlas Park remained ready for 62.235 seconds.
Earlier character attempts exposed harness status parsing and console capture
issues; the final corrected run completed all eight phases with no failures.

Continuation on 2026-09-26 recovered the completed 2026-09-25 run after this
handoff had retained an in-progress status. At recovery, GitHub showed no queued
or running workflow and the latest commit was `04d62616e2e1b41b10f35a04d4c798e43680d5ba`
(2026-09-25 19:05:39 UTC). The workflow finished at 19:16:38 UTC. These observations
do not reveal the internal status of the other Codex session.

## Latest hosted ARM64 game checkpoint (2026-09-28)

[Run 36416020268](https://github.com/Russianranger/coh-android/actions/runs/36416020268),
commit `324823be6ca9713bdc60446eb31596004ff6286a`, is an **overall failure with
new partial runtime evidence**. Atlas stayed independently ready for 31.519
seconds. Stock TestClient created `TEST02279` / ID 1, entered Atlas, changed live
influence to 12,345 and completed protocol logout with an independent committed
SQL snapshot (LoginCount 1) before forced cleanup. Wine and PostgreSQL shut down
cleanly; the same PostgreSQL cluster restarted. The next service-launch
preflight failed immediately with `[Errno 98] Address already in use`, before
replacement game services started. No exact-name resume or second-save proof
was obtained. Preserve the [raw report](android-evidence/game-arm64-failed-36416020268.json)
and [detailed evidence](ANDROID_GAME_RUNTIME.md#first-arm64-creation-and-protocol-save-restart-gate-failed).

The bounded fallback snapshot found no owned Wine processes or game-role SQL
sessions after the verified shutdown. Review confirmed that the TCP preflight
lacked the native `SO_REUSEADDR` behavior used by pinned Wine. An isolated Linux
experiment reproduced the bare-bind error with TIME_WAIT and passed with TCP
reuse while retaining rejection of live listeners and occupied UDP ports. The
hosted report has no socket table proving that state, but the behavior is
consistent with its failure. The narrow harness correction and tests were
applied for the subsequent run described below; restart validation remains required. The
prior startup timeout did not recur: one query returned after 78.833 seconds and
AutoCommands retrieval completed after 82.71 seconds. This does not establish
that intermittent startup delay as fixed. Do not repeat the successful first
save as if it were still unknown, or mark the full hosted gate accepted before
restart/resume/second-save pass. Keep the accepted 0.1.5 device diagnostic;
Android game presentation and gameplay remain unvalidated.

The subsequent [run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed a startup query in the first
service phase after 13 preceding readiness queries had completed. The failing
query reached 90.041 seconds, so it did not exercise the restart-port correction.
Preserve the prior first-save evidence above. The new
[failure receipt](android-evidence/game-runtime-failure-36420158506.json),
[raw report](android-evidence/game-arm64-failed-36420158506.json) and
[pre-cleanup snapshot](android-evidence/game-hang-36420158506/snapshot.json)
show live DbServer/Atlas/query processes and 65 idle SQL sessions. All Windows
capture APIs completed (three processes, 72 threads, 114 modules, zero errors),
but inspection of pinned Wine/FEX shows `GetThreadContext` supplies saved WOW64
context rather than current translated x86 execution state. Decoded DbServer
pointers lead to an already-completed startup path, so they do not identify the
live blocker or justify a main-loop change. Final cleanup passed with all 59 process
captures closed and zero remaining owned processes or inspection failures.
The full hosted restart/resume/second-save gate and Android gameplay remain
unvalidated.

[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` qualified the separately receipted
DbServer package containing [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md):
all three jobs passed, including the Windows enabled-record contract. The ARM64
fixture and normal schema checks ran with the observer disabled. Preserve the
[new acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
alongside the original acceptance. The donor manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632` and the normal
executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

Atlas adopted donor `36425508780`, with separate fresh records required for
first startup and restart. Enabled publication on live ARM64 was subsequently
verified in run `36428915900` below. Bounded stage/sequence observations distinguish progress
through startup, dispatch, SQL keepalive and console handling without relying
on stale WOW64 contexts. A stopped marker identifies an operation and its nested
calls; it does not prove a deadlock or gameplay success. No startup blocker fix
has been established, and the accepted device APK remains 0.1.5.

[Run 36427680960](https://github.com/Russianranger/coh-android/actions/runs/36427680960)
at `82386fd48c2352a2ce65d5920f7857e8b92ec442` passed source, package and data
staging, then failed on a read timeout downloading pinned talloc for the PRoot
build. No game diagnostic ran, and no runtime report or dispatch sample exists.
The [infrastructure failure receipt](android-evidence/game-infrastructure-failure-36427680960.json)
preserves this result. It adds no evidence about the intermittent startup
stall. The isolated retry correction allows at most three transport attempts,
discards partial downloads and preserves the size/SHA-256 gates; Atlas tooling
now explicitly runs its regression tests. The next run passed dependency
preparation without an observed retry. This download remedy is not a game
startup fix; full restart/resume/second-save remain pending.

[Run 36428915900](https://github.com/Russianranger/coh-android/actions/runs/36428915900)
at `f32ccd7c0f1aa950d1f87ceb81ab09b2dba4e2ac` failed a first-phase startup query
after 90.030 seconds, following 13 completed readiness queries. Enabled ARM64
source markers are now validated: the initial record had sequence 28 / loop 1
at `NM_MONITOR`; the same DbServer PID 412 / main thread 416 and mapped file
later held `FOLDER_CALLBACKS`, sequence 2,449,552 / loop 43,741. Identical before
and after records span 13:55:20.897–13:55:23.957 UTC. This localizes the observed
work to folder callbacks or nested calls. Separate non-atomic native snapshots
showed `read` and `fchdir` operations under PRoot, so a deadlock is not established.
The specific nested operation and throughput remain unknown.

The query, DbServer and Atlas were alive before cleanup, and the query remained
alive after the 3.061-second capture. All 65 SQL sessions were idle in
`ClientRead`, without active transactions; the foreground last query was `;`,
about 134.9 seconds old. Atlas ended at `Retrieving AutoCommands..`. Preserve the
[failure receipt](android-evidence/game-runtime-failure-36428915900.json),
[raw report](android-evidence/game-arm64-failed-36428915900.json) and
[snapshot](android-evidence/game-hang-36428915900/snapshot.json). Archive and all
eight service/hang capture hashes were independently verified. Final cleanup
passed with all 57 process input/output captures closed and zero remaining owned
processes or inspection failures. No new character or restart result was obtained.

Next, qualify the opt-in [fixed-input DbServer mode](../database/wine-dbserver/FIXED_INPUTS.md).
It prevents watcher registration before the first cache and preserves initial
reads/lookup mode; merely disabling callbacks would leave notifications queued
in Wine. The two existing normal schema launches cover default startup and
acknowledged fixed-input reload. After qualification, adopt the new donor in
Atlas with unchanged-input checks over schema and DbServer configuration files,
then complete both saves and exact-name resume. Keep the earlier successful
first-create/save evidence and the accepted 0.1.5 APK. The full hosted gate and
Android gameplay remain unvalidated.

## Continuation validation checkpoint

The accepted character run is **36282414135**, tested commit
`86e512e85c8350714bc7b58668bf11443dc164f8`, completed 2026-09-27 00:40:07 UTC.
It verified `TEST20636` / container ID 1 with live influence 12,345, committed
protocol logout before forced cleanup, restart of the same PostgreSQL cluster
and game services, and exact-name short scene resume with creation disabled.
Selected identity/rows remained unchanged (1 parent, 1 `ents2`, 7 powers,
13 costume parts); `LoginCount` progressed 1 → 1 → 2. The resume exited
naturally with code 0 and both console observers finalized successfully.
The [report](postgresql-evidence/character-persistence-36282414135.json),
[complete artifact](postgresql-evidence/character-persistence-36282414135.zip) and
[acceptance/provenance record](postgresql-evidence/accepted-character-persistence-36282414135.json)
are preserved. Windows passed 67 tooling/map checks; Linux passed 62 with five
Windows-only skips. All four same-commit
[PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36282414187)
passed. The short resume does not establish sustained gameplay or Android execution.

### Accepted next milestone: sustained second session

The [sustained-session implementation](SUSTAINED_SESSION_VALIDATION.md) adds a
separately identified diagnostic TestClient with creation disabled and a normal
connected command loop. [Run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
passed all 12 phases at `4e8058c3ffe20acda61b55023202d409ed1d0df1`, completing
2026-09-27 05:08:11 UTC. `TEST-37762` / ID 1 resumed with live influence 12,345
and a processed server update confirming its identity. Ten samples covered
66.953 seconds connected on Atlas Park, with a maximum gap of 7.625 seconds.
The second live influence command produced 23,456 and committed through protocol
logout before forced cleanup. Missing-name refusal exited naturally with code 3
and left the entire character inventory and selected SQL unchanged.

`LoginCount` progressed 1 → 1 → 1 → 2 across first logout, restart, missing-name
probe and second logout. Selected identity/rows stayed identical except for the
intended influence change (1 parent, 1 `ents2`, 7 powers, 16 costume parts).
All three console observers finalized successfully. The [raw report](postgresql-evidence/character-session-36295176484.json),
[complete artifact](postgresql-evidence/character-session-36295176484.zip) and
[acceptance record](postgresql-evidence/accepted-character-session-36295176484.json)
are preserved. Windows passed 103 tooling checks; Linux passed 98 with five
Windows-only skips. The same-commit [stock regression](https://github.com/Russianranger/coh-android/actions/runs/36295176352)
and all four [PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36295176473)
passed. The accepted stock TestClient and server reference binaries remain
unchanged; the diagnostic client has separate source/build receipts.

The first hosted attempt
[36293644180](https://github.com/Russianranger/coh-android/actions/runs/36293644180)
passed stock creation/save/restart and missing-name refusal without mutation,
then rejected the positive selection because the character-list packet does not
populate its `db_id` field. The correction checks exact name/slot there and binds
the actual MapServer entity ID after the processed update to independent SQL.
The [failed evidence](postgresql-evidence/character-session-36293644180.json) is
preserved. The corrected retry above proves the sustained resume and second save;
the failed attempt remains identified as a failure.

### Accepted next milestone: Atlas instance transfer

The [Atlas instance transfer gate](MAP_TRANSFER_VALIDATION.md#accepted-hosted-validation-36297542986)
passed all 15 phases in run `36297542986`, tested commit
`5f2c561058a186de59d3f27301eea210bd4bb66d`; terminal success was recorded
2026-09-27 05:56:06 UTC. `TEST59440` / ID 1 stayed in the same client process
for map 1 → clone 101 → map 1. Fresh player updates carried transfer epochs 1
and 2 on ports 7002 and 7001, while independent character status confirmed
MapId/SmapId 101 then 1. Each arrival had current heartbeats, live influence
12,345 and unchanged committed selected state. Per-leg SQL reads establish that
state, not a fresh identical-write acknowledgement. The subsequent live change
to 23,456 and protocol logout supplied a fresh final-save proof before cleanup.
LoginCount stayed 2 across both transfers and final logout; no extra character
was created. All three console observers finalized successfully.

The [raw report](postgresql-evidence/character-transfer-36297542986.json),
[artifact](postgresql-evidence/character-transfer-36297542986.zip) and
[acceptance record](postgresql-evidence/accepted-character-transfer-36297542986.json)
are preserved. Windows passed all 119 tooling checks; Linux passed 114 with
five Windows-only skips. The same workflow passed the 12-phase sustained
regression using the same diagnostic bytes (62.532 seconds over 10 samples).
The stock-client and all four PostgreSQL regression jobs also passed at
`3848133e5e644f4c166cc9e7f3e027288d06c2fd`, with identical runtime code;
the retry changed only the test fixture and documentation.
The first transfer attempt stopped before the build on a Windows C-test fixture
portability error. The fixture now uses Winsock on Windows; client and server
code are unchanged by that correction. The [tooling failure record](postgresql-evidence/character-transfer-tooling-36297326622.json)
is preserved separately from the successful retry.

### Historical hosted M2 gate (0.1.0)

[Run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
passed all four jobs at source `0b61d7455f40f05709f912338cd5de8b1d72d750`,
completing 2026-09-27 17:29:16 UTC. All 80 tooling tests passed without skips.
The APK's exact guest assets passed eleven stages on Linux ARM64, including
real PE32 DLL/driver loading, all 65 stock ODBC connections, transactions,
rollback, UTF-16/binary values, column metadata, schema rebuild/reopen, graceful
same-cluster restart and a second Win32 verification of persisted data. All
three cleanup checks passed. The same-source [PostgreSQL regression run](https://github.com/Russianranger/coh-android/actions/runs/36336644454)
also passed all four jobs. Preserve the [acceptance receipt](android-evidence/accepted-hosted-36336644450.json)
and [raw guest report](android-evidence/runtime-smoke-report-36336644450.json).

`COH-Diagnostic-0.1.0.apk` is 13,309,477 bytes, SHA-256
`80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac`.
Download the `coh-diagnostic-apk` artifact from the accepted run. It contains
no game binaries or assets. The native Java app and owned PRoot session combine
pinned Bookworm/Wine 10/FEX inputs with PostgreSQL built from official pinned
source; its ephemeral CI signing certificate is not a stable update identity.

Physical Thor acceptance was pending at this checkpoint. The current
[device acceptance record](THOR_DEVICE_ACCEPTANCE.md) preserves the later 0.1.5
pass and remaining lifecycle checks. Hosted Linux execution alone does not prove
Android SELinux, foreground-service lifecycle, device shutdown, performance or
gameplay. Mission/new-zone transfers, automatic Launcher startup and combat remain
separate unfinished scope.

### Accepted hosted client prerequisite milestone (0.1.1)

Continuation on 2026-09-27 found the hosted M2 gate complete, with physical Thor
acceptance still pending. The branch had no unfinished result to recover from its
latest completed workflows; this does not expose another Codex session's internal
state. Work advanced to the independently permitted
[basic client capability probe](CLIENT_RUNTIME_PROBE.md).

Commit `c1097bdc0aab433fd3cb1560fd07175c6c3dc6b0` adds a separate **Run client probe**
operation to 0.1.1. It exercises a real PE32 WGL context, a textured quad with four
verified RGB readbacks, buffer swap, own-window keyboard/mouse messages and
DirectInput device creation. Audio enumeration and extension availability are
observations only. The original database-only operation remains available and
both modes require complete owned cleanup. The app now scrolls on short displays.

Local validation passed 93 tests with two environment-dependent skips; the actual
PE32 program also cross-compiled warning-free with `-Werror` and its Windows
imports were verified. Hosted workflow [36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245)
passed all five jobs at 20:59:41 UTC, including all 93 tooling tests without skips.
Database mode passed eleven stages; client mode passed twelve. The observed
renderer was llvmpipe/Mesa 22.3.6 OpenGL 4.3, all four RGB readbacks were exact,
and synthetic input plus DirectInput device creation passed. Both modes proved
graceful PostgreSQL restart and complete cleanup. DirectSound enumerated zero
devices, with no playback claim. All same-source PostgreSQL regressions passed.
The [acceptance record](android-evidence/accepted-client-probe-36349552245.json)
preserves report hashes, observed capabilities and the verified 13,477,490-byte
APK. Preserve it as the historical 0.1.1 result; the later
[Thor acceptance record](THOR_DEVICE_ACCEPTANCE.md) describes current device evidence.
A fixture result cannot establish CoH rendering, Cg shaders, physical controls,
audio playback, Android presentation or GPU acceleration. Thor reports were still
needed at this checkpoint; M3 minimal game-server/device execution remains unfinished.

### Historical Thor wineboot failure and hosted 0.1.2 result

The user supplied two Thor/Android13 reports from 0.1.1. Both passed native
PostgreSQL initialization, restricted fixture SQL and owned cleanup, but failed
at the 150-second wineboot wait before Windows ODBC or graphics. The second run
reused the same diagnostic database cluster. This is partial real-device database
evidence; complete M2/device acceptance remained pending at this checkpoint.

[The selected device evidence](android-evidence/thor-wineboot-failure-20260927.json)
records both failures. Their exit-code0 values were captured after forced cleanup
and do not establish the initializer's status before the timeout. A real subprocess
regression reproduced a false timeout when a successful initializer's background
service retains stdout. Commit `1afb0610095ebe3cb8aba591ea22d749613b7276` applies
[the narrow 0.1.2 fix](ANDROID_WINEBOOT_RETRY.md): wineboot alone may complete on
its own exit, with captured background output retained under owned cleanup. Live
initializer timeouts, nonzero exits, cancellation and output limits remain errors.
Receipts now record pre-signal state and require capture/writer shutdown too.

[Hosted run 36352420585](https://github.com/Russianranger/coh-android/actions/runs/36352420585)
passed all five jobs at this commit on 2026-09-27 21:44:41 UTC: all 99 tests
without skips, eleven database stages, twelve client stages and complete owned
cleanup. The [acceptance receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
preserves that historical build and reports. Hosted wineboot exited with output
capture still open; capture closed during cleanup. This proves the corrected
wait path was exercised, not that inherited output caused the Thor failures.
The subsequent Thor retry failed; the inherited-output correction alone did not
resolve device initialization.

### Historical 0.1.3 cold initialization qualification

[The 0.1.2 device report](android-evidence/thor-initializer-timeout-20260927.json)
records wineboot still running at 150.040 seconds before cleanup signals. Four
early native database stages passed; Windows ODBC and graphics were not reached.
PostgreSQL and prefix shutdown passed, but output capture remained open, so
complete cleanup was not proved.

Commit `49c1626c10636e46a38493047f34ab61a9a5d5ca` applies the
[0.1.3 initialization correction](ANDROID_WINE_INITIALIZATION.md): use `wineboot -i`
to avoid a forced second registration pass, invalidate only the timestamp of an
unready prefix, allow 600 seconds with progress every five seconds, and write a
readiness marker only after the real PE32 fixture passes. Successful warm runs
preserve the timestamp. Wine bootstrap errors, fixture failures and open captures
still fail the diagnostic; Stop and the overall fifteen-minute limit remain.
This addresses startup behavior without identifying the exact internal component
delayed on Thor.

[Hosted run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs on 2026-09-27 22:16:35 UTC at this source. All 109 tests passed
without skips. Fresh and repeat runs each passed eleven database stages or twelve
client stages, including all Windows fixtures and complete cleanup. Cold Wine
initialization took 39.911 seconds in database mode and 40.305 seconds in client
mode, with one registration pass each; both warm runs took 4.629 seconds with zero
registration passes. These timings describe the hosted environment. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36354266044)
also passed. The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds the verified APK, payload hashes and runtime evidence.

The subsequent device run passed initialization and all eleven functional stages;
its remaining cleanup failure is recorded below. Preserve the 0.1.3 artifact and
receipt as historical evidence.

### Historical 0.1.4 Wine helper cleanup qualification

[The 0.1.3 Thor report](android-evidence/thor-functional-pass-cleanup-failure-20260927.json)
completed initialization in 90.927 seconds with one registration pass, then passed
native PostgreSQL, real PE32 DLL loading, all 65 ODBC sessions, SQL/value/metadata
checks and durable same-cluster restart verification. The sole recorded failure
was `Owned process input/output capture did not close: wineboot`. The Wine prefix
lock and socket were inactive, and PostgreSQL shut down cleanly; that does not
prove every detached Unix helper exited. The remaining pipe writer is unidentified.
Client graphics were not requested.

Accepted source `83f132ddb8077c9d5175ae7cd039e0754b70074e` applies the
[0.1.4 cleanup correction](ANDROID_WINE_CLEANUP.md). Wine helpers carry an exact
per-run ownership token; bounded cleanup verifies the real UID and PID identity
before signaling. Output captures must actually reach EOF, and unrelated processes
must survive. The menu-helper override is corrected to `winemenubuilder.exe`;
its earlier launch does not prove it caused the retained pipe.

The initial [hosted attempt 36356073708](https://github.com/Russianranger/coh-android/actions/runs/36356073708)
stopped on ownership inspection of an unreadable, unrelated same-UID CI process.
The accepted correction safely excludes processes strictly older than diagnostic
startup, which cannot inherit the new child-only token; current or newer processes
still require inspection.

[Run 36356283176](https://github.com/Russianranger/coh-android/actions/runs/36356283176)
passed all five jobs on 2026-09-27 22:50:49 UTC. All 116 tests passed in 11.510 seconds
without skips. Database fresh/repeat runs passed all eleven stages; client
fresh/repeat runs passed all twelve. Every owned input/output capture closed,
ownership cleanup completed and no helpers remained. Cold initialization took
39.397 seconds in database mode and 37.973 seconds in client mode; warm runs took
4.276 and 4.126 seconds respectively. These are hosted timings.

Both detached-helper fixtures exercised one TERM and one KILL through two pidfd
signals, with zero remaining helpers or inspection failures. The unrelated
sentinel survived and the capture reached genuine EOF. All twelve embedded APK
assets and all six hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36356285898)
also passed. The [acceptance receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
preserves the build identity, payload hashes and reports.

The subsequent 0.1.4 Thor run again failed capture closure; the hosted receipt
and APK remain historical evidence.

### Hosted 0.1.5 Wine thread cleanup qualification

[The 0.1.4 device report](android-evidence/thor-capture-still-open-20260928.json)
passed all eleven functional stages and initialized Wine in 85.957 seconds. The
same wineboot capture failure remained after graceful PostgreSQL and Wine prefix
shutdown. Ownership scanning reported zero candidates, zero inspection failures
and completion, so its accounting did not explain the still-open pipe. Graphics
was not requested.

The [thread cleanup investigation](ANDROID_WINE_THREADS.md) reproduced a native
thread-group leader in `Z` state while a live worker retained the exact ownership
token and inherited output pipe. The old policy skipped that group, reported zero
candidates and left the capture open. Signaling the authenticated group allowed
genuine EOF. This confirms a real cleanup defect; the physical report has no
thread inventory and cannot identify its remaining writer.

Version 0.1.5 inspects surviving tasks of an exited leader and verifies UID,
thread-group ID, start time, PID namespace and the exact run token before group
signaling, preferring a group pidfd. A true zombie without live tasks needs no signal.
Unknown ownership, surviving owned tasks or missing output EOF must still fail.
Thread observations in reports exclude environment contents and ownership tokens.

Accepted source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4` includes the final
state-transition race and missing-task checks.
[Run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
passed all five jobs on 2026-09-28 01:12:14 UTC. All 125 tests passed in 15.591
seconds without skips. Fresh/repeat database runs passed eleven stages each;
client runs passed twelve each. Cold initialization took 39.343 seconds in
database mode and 39.747 seconds in client mode; warm runs took 4.176 and 4.277
seconds respectively. These timings describe the hosted environment.

The ordinary detached-helper and exited-leader/live-worker fixtures passed in
both modes under the pinned PRoot. Each thread fixture observed a zombie leader
with an authenticated worker holding the exact inherited pipe, which the old
policy would miss. Cleanup exercised one TERM and one KILL through two pidfd
signals and reached genuine EOF. An unrelated, TERM-sensitive sentinel running
the same executable survived. These are direct fixture observations, not evidence
of the identity of Thor's remaining writer.

All twelve APK payloads and all eight hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36364553676)
also passed. The [acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
preserves build identity, payload hashes and reports.

### Accepted primary M2 Thor diagnostic and headless client gate

The [device acceptance record](THOR_DEVICE_ACCEPTANCE.md) and
[selected evidence](android-evidence/accepted-thor-20260928.json) preserve the
supplied `coh-diagnostic-20260928-012426.zip` report. It identifies app 0.1.5 on
AYN Thor/Android 13 and runtime manifest
`fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203`, matching the
accepted hosted build. The `database_and_client` run completed at
2026-09-28 01:24:05.958172 UTC with all twelve stages passed, no failures and
complete owned cleanup.

This report proves a successful subsequent combined run: the existing database
cluster and ready Wine prefix were reused. The user says both operations passed, including
the preceding database-only run; the supplied archive directly documents only
the subsequent combined run. It verifies native PostgreSQL, real PE32 DLL and ODBC driver
loading, all 65 ODBC sessions, SQL/value/metadata fixtures and durable same-cluster
restart. Headless WGL rendering through llvmpipe/Mesa 22.3.6 returned all four
expected pixel colors; synthetic window input and DirectInput device creation
passed. This is a software renderer. DirectSound enumerated zero devices, with
no audio playback claim.

Device cleanup now observed three exited-leader groups and three authenticated
live-worker witnesses. It issued three TERM signals and one KILL signal through pidfds,
finished with zero remaining helpers or inspection failures, and closed input and
output for all 30 recorded processes. This observes the reproduced dead-leader/
live-worker condition on Thor and completes cleanup successfully. The report does
not inventory the exact earlier pipe writer, so that identity remains unknown.

**The primary M2 device diagnostic and headless client capability gate are
accepted.** Android surface presentation, hardware acceleration, physical input,
audible playback and CoH gameplay remain unvalidated. The current next device
gate is **Stop followed by a successful diagnostic rerun**, exporting both reports.
Use the existing 0.1.5 APK; no new build is needed. Suspend/resume and memory
behavior still need evidence and can accompany the next candidate. The
[first hosted M3 DbServer gate](ANDROID_DBSERVER.md) subsequently passed in
run 36369485666. Managed Atlas MapServer and diagnostic TestClient execution are
next; Android listener binding and app lifecycle integration remain before the
device candidate.

### Earlier attempts and corrections

The recovered evidence and new character harness are on
[`codex/character-persistence-continuation`](https://github.com/Russianranger/coh-android/pull/1)
in draft PR #1. Implementation commit: `3d61ca929dc825ba9424279553797b66498df418`.
[Hosted run 36269025801](https://github.com/Russianranger/coh-android/actions/runs/36269025801)
passed both tooling jobs: all 55 Windows checks, including three live named-pipe
checks; Linux passed 52 with those three platform checks skipped. The game
experiment failed with `Unknown character status flags`: a multiline whitespace
match consumed process output after a valid status line. Character ID 1 and its
name agreed between TestClient, stock `-find` and independent SQL, but no save or
restart pass was reached. The [full failed attempt](postgresql-evidence/character-persistence-36269025801.zip)
and [report](postgresql-evidence/character-persistence-36269025801.json) are preserved.
The status parser is corrected at `cc3c82a87e2c3eabe1478b13ea031e3923423b10`,
without relaxing identity or flag checks. The reproducing regression passed;
all 40 portable character checks passed, with three Windows transport checks
skipped locally. [Fresh retry 36270565732](https://github.com/Russianranger/coh-android/actions/runs/36270565732)
failed after the status fix worked: character ID 1/`TEST-43027` was connected on
Atlas Park, but TestClient's GUI entry allocated its own console and reopened
stdout/stderr to `CONOUT$`. The harness could not see the required creation
branch text. The [artifact](postgresql-evidence/character-persistence-36270565732.zip)
and [report](postgresql-evidence/character-persistence-36270565732.json) are preserved.
The attempted console preallocation fix was rejected by its Windows GUI
regression in [run 36280623154](https://github.com/Russianranger/coh-android/actions/runs/36280623154):
`AllocConsole` still succeeded, so the runtime job was skipped. The replacement
uses a bounded observer attached to the actual TestClient console before the
launcher version exchange, preserving the console across the short client exit.
[Run 36281372316](https://github.com/Russianranger/coh-android/actions/runs/36281372316)
then passed all 66 Windows tooling/map checks and reached real character creation,
live currency 12345, protocol logout and independently committed SQL. The first
saved snapshot contains one parent, one secondary row, seven powers and twelve
costume parts. It failed on observer cleanup before restart acceptance: forced
client-tree termination closed the console before its final snapshot. The
[artifact](postgresql-evidence/character-persistence-36281372316.zip) and
[report](postgresql-evidence/character-persistence-36281372316.json) are preserved.
The follow-up finalizes the observer after proven logout/save but before residual
client cleanup; exact resume acceptance remains required.
All four [PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36269025871)
also passed on the implementation commit.

The final cleanup-order correction in `86e512e8` completed the restart/resume
gate. Its accepted evidence and remaining scope are recorded above; earlier
failed attempts remain as diagnostic history.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
The actual Win32 DbServer now has an opt-in, asset-independent persistence test
entry. It exercises the original container parser, writer, SQL FIFO/worker pool,
reader and template updater with controlled templates and records. PostgreSQL
saves commit before completion; serialization/deadlock retries replay the whole
transaction. Permanent or uncertain failures stop without acknowledging the
failed command. Child/parent deletion is atomic.

All four jobs in the current [regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 21 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild, backup/restore and foreign-key removal against absent tables. The
narrow PostgreSQL guard fixes the fresh-database initialization failure without
changing the preserved source snapshot.

The earlier [20-group implementation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
at `0827ccc992daa7530d9f98d742122238197847df` and
[regression refresh 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
remain historical evidence. The separate normal fixture-OFF DbServer
[startup/export/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed using the accepted schema/runtime pair and a fresh disposable
PostgreSQL database. This exercises normal game-schema initialization in addition
to the controlled persistence fixtures; it does not create or save characters.

**Normal network acknowledgements passed:** [run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
verified creates, an update after restart, and a two-container request held behind
an actual PostgreSQL row lock. No ACK arrived during the 2.078-second observed
write block. After release both rows were committed; an injected COMMIT failure
then produced zero ACKs, preserved the previous row, and stopped DbServer with
exit 3. The normal reference package had fixture mode OFF. The report and all
redacted logs are [preserved](postgresql-evidence/network-ack-36125829311.json).
Batches are not atomic as a whole, and player-session completion is untested.

The latest test drivers distinguish the specific observed benign PostgreSQL
catalog notices from real errors. Both new normal-process gates passed at
`a0ae66d72648d33a7f70b3116d1e1800d9164184` using the accepted `775a0dd...` builds.

Migration 2 adds transactional table rebuilds preserving sequence high-water,
indexes and foreign keys, explicit ASCII case-insensitive name equality, and the
PostgreSQL auction timestamp filter. Stop DbServer, back up and run
`pg_local.py migrate` for an existing development cluster. See the
[persistence design and test scope](POSTGRESQL_PERSISTENCE.md),
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This database milestone does not establish
gameplay; the separate diagnostic APK's current acceptance is recorded above.

**Stage1 asset inspection complete:** `stage1a.pigg`, `stage1b.pigg` and
`stage1f.pigg` have been received. All **14,814 entries** passed archive integrity
and offline structural checks; 5,878 animations and 8,936 textures were staged
separately. All seven startup texture names and MALE/THUMBSUP are present.
Every base-animation reference resolves within `stage1a.pigg`. Preserve warnings
for 216 legacy hierarchy layouts and 193 DDS surplus-byte cases; runtime use
remains unvalidated. See [the stage1 assessment](STAGE1_ASSET_ASSESSMENT.md).
No repeat index run, repeat upload or custom `i26/geobin.pigg` upload is needed.

**Reference runtime refreshed:** [run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed with the exact source pin, PostgreSQL patch and fixture mode OFF at
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
Download `reference-win32-runtime` (artifact `10843979104`) from this run;
it supersedes [the earlier package 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663).
Client, MapServer, DbServer, TestClient, pig and Launcher are packaged with
required supplied DLLs and app-local x86 MSVC runtime libraries. The package
passed hash, PE and dependency checks. The verified base assembly contains
173,011 data files / 2,977,730,517 bytes, with no conflicting donor paths.
The preflight's earlier 173,008 count excluded three additional source-pinned DB
config files added by final assembly. See [current assembly evidence](reference-runtime-evidence/assembly-775.json)
and [reproduction/build instructions](REFERENCE_RUNTIME.md).

Local game execution is blocked by this environment's wineserver IPC restriction.
Use hosted Windows for further runtime validation. The separate data-only schema
patch remains isolated from the reference package and retains error/output
gates. Its incidental caches must not be reused as gameplay caches.

**Data-only schema generation refreshed:** [run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the current reference package. Bootstrap
took 31.468 seconds and strict reload 5.750 seconds, with zero queued errors and
identical bytes for all six attribute maps. All 51 required outputs plus five
dbidmaps are preserved in [the current accepted artifact](schema-generation-evidence/accepted-36088012666.zip).
Every one of these 56 generated payloads is byte-identical to the
[earlier accepted run 36072787971](schema-generation-evidence/accepted-36072787971.zip),
which remains historical evidence. Keep the accepted attribute-ID mappings with
any database initialized from them.

**Normal DbServer schema startup/reload passed:** the first hosted attempt
exposed a fresh-database FK-removal ordering bug. The narrow correction passed
its regression suite and is included in both current artifacts. With that pair,
[run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
completed fresh initialization/export in 13.219 seconds and a second pass in
5.718 seconds. Both exited successfully with no failure diagnostics and produced
fresh empty dumps. Both passes found 99 tables and 58,272 attribute rows
(56,411 general, 1,771 badge-stat and 90 pop-help IDs), with identical catalog
hashes and attribute mappings. Both catalogs contain the verified 5,935 columns,
119 indexes and 734 constraints.
The tested DbServer has persistence fixture mode OFF; its executable SHA-256 is
`fb62028b24bf3165bdcf09e80909d02df5391f89986b9e0454934909a67d93f8`.
See the [downloaded evidence](postgresql-evidence/generated-schema-36125829298.zip)
and [summary](postgresql-evidence/generated-schema-36125829298.json).
The later asset-backed comparison and Atlas Park gate below passed. Complete
serializer semantics, complete asset coverage and character gameplay remain
unvalidated.

**Normal templates and Atlas Park readiness passed:**
[run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
used the accepted reference/schema pair and all 16,721 reviewed binary assets.
Ordinary `MapServer -templates` freshly reproduced **56/56** accepted files
byte-for-byte in **25.89 seconds**. A separate fresh runtime, without comparison
caches, then started normal DbServer and Atlas Park against PostgreSQL. Independent
DbServer status queries confirmed the initial not-started state and subsequent
ready state with continuing updates for **62.235 seconds**. Both reports have
empty failure lists. Preserve the [comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json),
[comparison artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip),
[map report](postgresql-evidence/one-map-36176806895.json),
[map artifact](postgresql-evidence/postgresql-one-map-36176806895.zip) and
[accepted gate identities/hashes](reference-runtime-evidence/accepted-gates-36176806895.json).
The normal executable does not report queued startup error counts; these gates
do not establish complete assets, character login/persistence or gameplay.

## Completed

- All 5,995 source files verified; exact-commit upstream Windows build and nine
  utility/archive/codec tests passed, as previously audited.
- Imported the entire `Thunderspies/i24` tree at
  `d51533ec8e6a9cf726b9214968077a05fdcf19f3` under `upstream/i24`: 156,297 files,
  1,992,097,492 bytes, no exclusions. Local and hosted integrity/tree checks passed.
  Import commit: `1768775ab3608cdd852ec7119bbf0139a91248c6`.
- Added `content-lock.json`, data inventory and per-file manifest. The importer
  and verifier accept `--lock content-lock.json`; existing source defaults remain.
- Added the exact 72-archive upstream catalog and portable `content_assets.py`
  probe/fetch/record/verify tool. Receipt checks detect changed/missing bytes.
- Added `prepare_runtime.py`; full text-only staging passed. It keeps imports
  immutable, fixes `Game.exe` to `CityOfHeroes.exe` in staged launchers and uses
  source-pinned configs. It accepts extracted asset data and exact-pin build
  outputs separately; it does not execute programs or install SQL.

## External content result

The user's `small_i26_piggs.zip` has now been inspected: all **17 archives /
8,864 entries** passed size, decompression, MD5 and cached-header checks.
**549 compiled files use Parse7; the pinned source expects Parse6**, so these
caches cannot be reused unchanged. Staged **665 candidate binary assets**
(141 geometry, 445 textures, 79 audio files; 152,755,341 bytes) separately,
with runtime compatibility still unverified. No raw client binaries/assets were
published. The original ZIP plus the new portable inspector reproduce staging.
See [client content assessment](CLIENT_CONTENT_ASSESSMENT.md) and its
[per-archive hashes/counts](client-content-assessment.json). Eight inspector
regression tests passed in that initial pass.

The subsequent **`geomBC.pigg`** also passed: 1,232 entries, comprising 584
geometry files and 648 Parse6 caches. All geometry files use versions accepted
by the source and passed compressed-header/data-bounds checks; meshes/collision
and runtime loading are untested. Staged geometry separately under
`imports/base-geomBC-candidate-assets`. Cumulative result: **18 archives,
10,096 verified entries, 1,249 distinct candidate assets / 318,908,734 bytes**.
The inspector now records geometry header checks; eleven regression tests pass.
See [base geometry evidence](base-geometry-assessment.json).

The later `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg` batch also
passed: **2,774 additional entries**. Cumulative result is now **22 archives /
12,870 entries / 2,487 distinct candidate asset paths**, with two conflicting
custom/base geometry variants kept separately. All 46 fonts are staged, including
TTC collections; every one of the 16 startup font filenames is present. All
1,277 new geometry headers passed. `misc.pigg` mostly duplicates the pinned text.
At that earlier stage there were **zero skeletal .anim tracks** in the supplied
set and none of seven requested basic renderer texture names. The subsequent
stage1 uploads below supply those candidates; runtime startup remains untested. See [asset coverage history](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

The subsequent **`coh-asset-index.json`** has now been received from Thor and
preserved as [thor-asset-index.json](thor-asset-index.json). It reports 73 base
archives and 22 custom-folder archives, with 96,379 entries across those tables
(not deduplicated). Base `stage1a.pigg` lists 5,878 animation tracks, including
MALE/THUMBSUP; `stage1b.pigg` and `stage1f.pigg` list all seven startup texture
names. This locates candidates on the device; it does not add to the 22
payload-verified archives or establish source-format/runtime compatibility.
The indexer previously matched full-inspection counts/extensions for all 22
available archives; thirteen regression tests passed in that earlier pass.

The three selected **stage1 archives** then passed integrity and offline format
checks. Cumulative payload-inspected count: **25 archives / 27,684 entries**.
New staging contains 14,814 distinct paths within the batch and 654,699,284 bytes;
its overlaps with earlier custom assets have not been recomputed. The 20 new
format/staging tests passed. All animation base references resolve, including
the fallback, and all seven startup textures pass structural checks. Native
ARM64 needs explicit decoding of 32-bit animation records; the renderer must
handle the observed DDS formats. Runtime compatibility remains untested. See
[stage1 evidence](stage1-assets-assessment.json) and the
[reproducible checks](STAGE1_ASSET_ASSESSMENT.md#reproduce-without-windows).


[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The original fallback was an accessible compatible archive/mirror/magnet or
existing asset folder; the user has since supplied the targeted assets above.
No additional broad asset upload or Windows VM is required for this assessment. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation priority and remaining scope

**The primary M2 device diagnostic and first hosted M3 DbServer gate are accepted.**
Continue M3 with managed Atlas MapServer and diagnostic TestClient execution in
the same ARM64 Wine/FEX runtime. The isolated Wine-compatible DbServer fixture
and normal schema startup/export/reload have passed; preserve their
[accepted evidence](android-evidence/accepted-dbserver-hosted-36369485666.json).
The diagnostic DbServer successor is also [qualified](android-evidence/accepted-dbserver-hosted-36425508780.json).
Use donor `36425508780` for the next Atlas run; verify enabled ARM64 dispatch
publication and finish restart/resume/second-save before accepting that hosted gate.
Android listener binding and app lifecycle integration remain before the next
device candidate. Keep the existing 0.1.5 APK and runtime. See the
[concrete next steps](THOR_DEVICE_ACCEPTANCE.md#next-work).
Stop followed by a successful rerun, suspend/resume and memory measurements remain
device checks and can accompany the next candidate. The following items preserve
completed reference gates; no repeated Windows-only milestone is needed.

1. Preserve the accepted results from corrected manual [asset run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895).
   It passed ordinary template comparison and Atlas Park readiness with schema
   run `36088012666`, reference run `36088012664`, asset `588984151` and
   `run_one_map=true`. No rerun is needed to establish those completed gates.
   Upload is complete: unpublished draft release
   `396839391` contains the accepted **615,541,018-byte** ZIP, SHA-256
   `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`.
   Ignore incomplete asset `588979946`. No repeat PIGG or ZIP upload is needed.
   The initial manual [run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
   failed during download before any game process, suspected to be the draft
   release's rejection of the read-only token. Its HTTP status was not logged.
   [Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
   scopes `contents: write` to the manual comparison job; global/tooling tokens
   stay read-only. It also adds safe numeric HTTP status and stage diagnostics;
   all 12 downloader tests and [tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
   passed. [Run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
   then successfully downloaded and verified the exact ZIP, confirming hosted
   draft access. It failed `Manifest must use canonical JSON` before game
   execution: Windows checkout changed the manifest's LF bytes to CRLF.
   [Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
   marks `assets/reference-inputs-*.json -text`; a temporary Git checkout with
   `core.autocrlf=true` reproduced the accepted canonical bytes, and
   [tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
   passed. The successful manual run used that fix. The release remains unpublished
   and raw assets are not uploaded as Actions artifacts. See the
   [concrete handoff](NEXT_SERVER_VALIDATION.md) and
   [transfer evidence](reference-runtime-evidence/asset-transfer-20260925.json).
   The matching reference package and coherent base assembly are ready. Preserve the accepted attribute-ID mappings; do not
   substitute the separate schema executable or its incidental caches for the
   reference runtime.
2. Preserve the accepted [character persistence result](CHARACTER_PERSISTENCE_VALIDATION.md#accepted-hosted-validation-36282414135).
   Fake-auth creation, live currency change, explicit logout, committed SQL,
   same-cluster/service restart and exact-name short resume have passed.
   The [sustained resume and second-save result](SUSTAINED_SESSION_VALIDATION.md#accepted-hosted-validation-36295176484)
   has also passed, including missing-name refusal without mutation. Preserve
   the separate diagnostic TestClient receipts alongside the stock reference.
   The [Atlas round trip](MAP_TRANSFER_VALIDATION.md) has also passed with
   independent destination identity, fresh player updates, current heartbeats,
   live currency and a final committed protocol save. New-zone assets, mission
   transfers and automatic Launcher startup remain unvalidated.
   Separate remaining server work includes player-session completion callbacks, game-level
   name uniqueness and auxiliary-service persistence. Generic-container network
   ACK ordering is now verified. Fake auth is only the minimal local diagnostic route; no SQL
   Server save migration has been attempted. Empty-database startup/export and
   controlled persistence fixtures do not establish these gameplay behaviors.
3. Generate further server/client caches with the bounded harness when the runtime
   has the required graphics. Resolve legacy animation hierarchy/DDS warnings
   through reference runtime use. Keep custom variants separate and request
   further archives only when runtime evidence identifies a concrete missing
   input. The older upstream v2i3 release is not the locked build; use the current
   reference artifact.
4. Keep the accepted 0.1.5 APK. Start a diagnostic, choose Stop, wait for its
   terminal result and export the report; then rerun diagnostics and export that
   result. The combined run with reused state and full cleanup pass above remain accepted.
   Suspend/resume and memory behavior are pending device measurements. These
   checks can accompany the next M3 candidate; implementation need not wait for
   another run of the already-passed diagnostic.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. The current APK status is recorded
in [ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md); gameplay remains unvalidated.
