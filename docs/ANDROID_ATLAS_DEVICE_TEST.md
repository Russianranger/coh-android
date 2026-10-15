# Atlas Park server test on Android

**COH Atlas Test 0.4.4 passed hosted qualification; one full Thor test/export is next.**
The exact signed APK in [run 36638344040](https://github.com/Russianranger/coh-android/actions/runs/36638344040)
at `e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce` passed full import and all 18
create/save/restart/resume stages in 33 minutes 10.8 seconds. Both protocol saves
committed, the exact character resumed in the same database cluster, and restart
and final owned cleanup completed with zero inspection failures and zero remaining
owned processes. Independent review verified the preserved raw evidence and
replayed Java acceptance compatibility without relabelling the host as Android.
See the [0.4.4 acceptance receipt](android-evidence/accepted-atlas-test-hosted-36638344040.json).

All 149 candidate checks and 65 import checks passed. Of 179 game checks, 172
passed and seven Windows-only checks were skipped; the qualified MapServer donor
separately passed all six real native producer checks. The exact APK's 31 payloads,
14 Java source identities and six guest helpers match their receipts.

The selected `dispatch_progress_v1` profile requires a fresh coherent observation
with a positive completed-tick count before each startup protocol query, then a coherent
same-identity after-read, on both first launch and restart. Missing or invalid
observations cannot reuse cached success. The existing 20-second protocol
freshness, 30-second observation, shared 600-second DbServer startup budget,
overall deadline and cancellation remain intact. The narrow 0.4.3 ownership
correction is retained; live unreadable ownership still fails. Java acceptance
now checks the selected profile and raw startup evidence, retaining cleanup gates.

This qualifies hosted execution only. Complete physical Thor 0.4.4 acceptance,
Stop/rerun, lifecycle checks and graphical gameplay remain pending. Because the
CI signing certificate changed, uninstall only the failed **COH Atlas Test 0.4.2**,
then install **COH-Atlas-Test-0.4.4.apk**, prepare its private runtime and import the
complete reviewed ZIP. Keep accepted **0.1.5, 0.2.0 and 0.3.0** installed. Run one
full Thor test and export its report, even on failure. Hold Stop/rerun and lifecycle
checks until that report's restart/resume and cleanup evidence is reviewed.

The earlier checkpoints below preserve their original successes and failures.
Their installation and retry directions are superseded by the 0.4.4 procedure above.

**Qualified MapServer diagnostic donor: run 36630872719.**
Run `36630872719` passed all six real Windows producer contracts and all eighteen
ARM64 game stages in 31 minutes 23.5 seconds. Independent review verified both
committed saves, exact-name resume, 122 closed children and zero ownership
inspection failures at restart and final cleanup. Raw records show 8,226 completed
ticks on the first launch and 2,425 on restart, with distinct file identities.
Only the separately identified MapServer changed; accepted supporting binaries
and their original source identities remain exact.

The successful run also captured a 114.233-second interval inside the first
`FolderCacheDoCallbacks` call, with one tick started and none completed. Existing
freshness checks rejected protocol-ready samples aged 23 and 85 seconds. This
does not prove the cause of earlier uninstrumented failures or repair the folder
work. The qualified 0.4.4 profile additionally requires a freshly validated
completed tick and the two-phase startup guard described above, preserving
startup deadlines, 20-second freshness and 30-second observation.

0.4.4 carries these diagnostics from donor commit
`003b07bcd98cb100c1505c15670c07d11a240c8f`, separately from its Android
wrapper and guest-adapter commit. Only the instrumented MapServer is replaced;
accepted supporting binaries and their original source identities remain exact.
See the [hosted diagnostic qualification](android-evidence/accepted-mapserver-progress-hosted-36630872719.json).

**0.4.3 remains unqualified after two hosted Atlas heartbeat failures.**
All 113 candidate checks and exact APK verification passed. Both runtime attempts
of the same signed APK in run `36621227369` passed nine stages, then failed
`Atlas lost current readiness during observation`, before character creation or
restart. DbServer kept dispatching and both services were alive at capture.
Both final cleanups completed with zero ownership inspection failures and zero
remaining owned processes. Neither attempt exercised the targeted restart race.

Identical 0.4.3 retries are stopped. The separately receipted MapServer diagnostic
above now exposes fresh late-startup and main-loop stages while preserving all
readiness, listener and cleanup checks. Buffered stdout and saved thread contexts
from these failures do not prove the blocked operation. Do not install 0.4.3 as
a qualified candidate. The 0.4.4 hosted pass does not establish the root cause or
repair of either earlier uninstrumented failure.
See the [attempt 1 review](android-evidence/atlas-test-review-36621227369-attempt1-failed.json),
[attempt 2 review](android-evidence/atlas-test-review-36621227369-attempt2-failed.json),
and [observer design](android-evidence/atlas-test-heartbeat-observer-plan-20260929.md).

**Thor 0.4.2 follow-up (2026-09-29, 18:57 UTC): cleanup is blocked again.**
The first 13 stages passed, including Atlas live-heartbeat observation and the
committed save of `TEST24402` with 12,345 influence. `game_restart` failed with
`Cannot verify Wine descendant ownership` after Wine stop/wait both returned 0.
Final cleanup subsequently found zero remaining owned processes and closed all
84 child records, but one earlier inspection failure remained latched. The app
correctly refused reuse. This run did not reach PostgreSQL restart, the new
restart startup budget or exact-name resume. No Stop or cancellation was recorded.

The report has zero permission-read retries and no permission observations. Its
message comes from the generic OS/parse-error path and omits the underlying
exception, errno and process identity. A reproduced proc-file exit race is a
candidate mechanism, not a proved explanation of this particular device run.
The narrow correction introduced in 0.4.3 and retained in 0.4.4 handles
ESRCH from status/stat as task disappearance.
Environment/namespace ESRCH requires a fresh exact-identity check and preserves
inspection of live workers behind a stopped leader. Live unreadable ownership
still fails; retries and diagnostic records are bounded. The original operation,
exception type, errno and process/thread IDs are retained without raw contents.
See the [owned-child reproduction](android-evidence/atlas-test-proc-exit-reproduction-20260929.json).
The accepted base runtime, identity/token signaling checks and Java cleanup
gates remain intact. Do not repeat 0.4.2. The current 0.4.4 procedure supersedes
that failed app's recovery and retry sequence: one full Thor test/export first,
with Stop/rerun and lifecycle checks held until report review.
See the [device failure review](android-evidence/atlas-test-thor-cleanup-failure-20260929-185717.json).

**Thor follow-up:** 0.4.1 passed 15 stages, including the first committed save,
clean service shutdown and PostgreSQL restart. The ownership correction recovered
a denied worker read; final cleanup was complete and the app was not blocked.
It then hit a separate 30-second DbServer readiness deadline while the normal
launcher wait was still running. No Stop/cancellation was recorded. See the
[failure receipt](android-evidence/atlas-test-thor-dispatch-failure-20260929.json).
The older [0.4.0 cleanup failure](android-evidence/atlas-test-thor-restart-failure-20260929.json)
and subsequent user force-stop remain preserved separately.

The hosted-qualified M3 device candidate is **COH Atlas Test 0.4.4**, application ID
`io.github.russianranger.cohatlastest`. It combines the accepted content importer
with the qualified PostgreSQL/Wine/FEX runtime, DbServer, Atlas Park MapServer,
and creation/resume TestClients. It runs an automatic character persistence test.
It does not supply a graphical game client or human controls.

**Previous hosted checkpoint: COH Atlas Test 0.4.2 passed on attempt 2.**
The exact signed APK completed import and all 18 create/save/restart/resume stages
in 32 minutes 11 seconds, with both committed saves and complete owned cleanup.
All 100 candidate checks passed. That checkpoint qualified the bounded
DbServer startup correction; the subsequent failed Thor run is preserved above.
Attempt 1's separate Atlas heartbeat failure remains preserved. The unchanged
repeat passed, but does not establish a repair or root cause for that failure.
See the [0.4.2 historical acceptance receipt](android-evidence/accepted-atlas-test-hosted-36599606621.json)
and [failed first-attempt review](android-evidence/atlas-test-independent-failure-review-36599606621-attempt1.json).

The correction gives schema/listener readiness and
positive main-loop dispatch one shared 600-second DbServer startup budget.
The overall 90-minute guest deadline and all readiness requirements remain.
The 0.4.1 identity-checked worker-exit recovery and bounded denied-read diagnostics
remain in place. Live unreadable ownership, changed identities and unresolved
cleanup still fail. In 0.4.4 the accepted base runtime and supporting game
binaries remain unchanged; MapServer is replaced by the qualified instrumented donor.

The preceding 0.4.1 hosted qualification passed in
[run 36579726816](https://github.com/Russianranger/coh-android/actions/runs/36579726816)
at `6b50467a1b96133acc92a378617ff961733f288c`. The exact signed APK's full import
and 18-stage server test passed in 32 minutes 49 seconds, including 31 minutes
52 seconds of guest execution. Both committed saves, same-cluster restart,
exact-name resume, all captures and owned cleanup passed. The downloaded APK,
all 30 packaged payloads and all 12 compiled source identities were checked
against the build receipt. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36579726816.json)
and [raw evidence](android-evidence/atlas-test-evidence-36579726816.zip).
All 91 candidate contract tests passed. Independent review verified 25 capture
files and all 122 closed process records. Restart and final cleanup had zero
inspection failures and zero remaining owned processes. The host did not need
permission-read retries; the subsequent failed Thor run exercised that recovery
but did not complete restart/resume.
The preceding [0.4.0 hosted baseline](android-evidence/accepted-atlas-test-hosted-36563104664.json)
remains preserved. Complete physical Android Atlas acceptance is pending the
new candidate's device reports.
The [0.3.0 content import/Stop/retry](ANDROID_ASSET_IMPORT.md#accepted-thor-importstopretry)
and [0.2.0 DbServer tests](ANDROID_SERVER_DEVICE_TEST.md#accepted-thor-results)
remain accepted; they do not need repeating in those apps.

## Separate installation and inputs

Keep 0.1.5, 0.2.0 and 0.3.0 installed. The new app has a separate private data
directory. Android does not allow it to read the setup app's imported files, and
the earlier CI signing certificate is not available for an in-place update.
The failed 0.4.2 Atlas Test used a different ephemeral CI signing key.
Uninstall only **COH Atlas Test 0.4.2**, then install the exact qualified
**COH-Atlas-Test-0.4.4.apk**. Prepare its private runtime and import again.
Keep the earlier accepted diagnostic and setup apps installed.
Import the same complete `coh-reference-assets.zip` once into this candidate.
This is preparation for the new app, not a repeat acceptance test of 0.3.0.

The new APK includes the reviewed repository text and exact inventories. It
selects the existing 615,541,018-byte asset ZIP through Android Files. Both the
importer and guest runtime check the pinned content. The game uses a new writable
copy for each test, keeping the imported base separate from generated schema,
caches, credentials and disposable test characters.

| Component | Accepted input |
|---|---|
| ARM64 runtime and Android PRoot | Run `36364550345` |
| Loopback DbServer | Run `36460867428` |
| Instrumented MapServer | Qualified run `36630872719`, commit `003b07bcd98cb100c1505c15670c07d11a240c8f` |
| Supporting game binaries, creation/resume TestClients and bridge | Unchanged accepted run `36510836956` |
| Generated schema | Run `36088012666`; 99 tables |
| Complete base data | 173,011 files / 2,977,730,517 bytes |
| Full data inventory SHA-256 | `b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4` |

The selected package comes from qualified MapServer donor run `36630872719`,
commit `003b07bcd98cb100c1505c15670c07d11a240c8f`, with manifest SHA-256
`ef1e5b1aa7cad69f2e25d286cc579531c86417d3f7f1a5de86843a350f4024cd`.
Only MapServer is replaced by the separately qualified instrumented binary.
Supporting executables retain accepted commit
`ac4c1f7978be444a893f65f5177641191861d42f` and original package receipt SHA-256
`ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a`.
The 0.4.4 Android wrapper and guest adapter separately identify commit
`e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce`. These source identities are distinct.

Setup downloads the hash-pinned runtime archives over HTTPS. No root, Termux,
Windows PC, GitHub token or manual server commands are needed on the device.
The game services and TestClients use their accepted loopback-only binding
profiles. These bindings are not a claim of device-wide network isolation;
hosted qualification retains its mandatory private network namespace.

## Device procedure after hosted qualification

1. Uninstall only the failed **COH Atlas Test 0.4.2**, then install
   `COH-Atlas-Test-0.4.4.apk`. Keep accepted 0.1.5, 0.2.0 and 0.3.0 installed.
2. Choose **Set up runtime** with Internet access. Have at least 8 GiB free
   internal storage before setup; this is a working-space check, not the final
   installed size.
3. Choose **Import game assets** and select the complete reviewed ZIP. Have
   at least 5 GiB free before import. Successful import reports 173,011 verified
   files. Do not select split ZIP parts or individual PIGGs.
4. Have at least 6 GiB free **after setup and import**, then choose **Run Atlas
   test**. The test creates its own disposable writable game copy and database.
   The overall guest deadline is 90 minutes. The failed 0.4.1 Thor run took about
   50 minutes 19 seconds through its first save and attempted restart, including
   about 24 minutes 10 seconds for initial server startup. A complete Thor run's
   timing is still unknown; allow the active stage to finish.
5. Export and submit this first complete attempt for review, even if it fails.
   Pause here until its restart/resume and cleanup evidence has been checked.

Stop/rerun and lifecycle checks are held until the first report is reviewed
and its complete restart/resume and cleanup pass is accepted. The later sequence
is Stop during active services, cleanup/export, then a fresh successful run/export
with app switching and screen lock/unlock. The service records bounded lifecycle
observations; do not start that sequence before review.

The automatic test has 18 stages. It creates and enters Atlas Park with a
fake-auth test character, changes influence to 12,345, requests an ordinary
protocol logout/save, verifies committed SQL, restarts the same database and
game services, resumes the exact character with creation disabled, and commits
a second save. Required local listener evidence and complete owned cleanup are
part of acceptance. Finishing the launch alone is insufficient.

Each test starts with fresh owned state. It is a diagnostic of save/restart/resume
within one test, not yet a player-facing persistent world. Keep the original
imported content intact; game files generated during the test are disposable.

## Evidence and qualification

The foreground service owns one operation at a time. Import, setup and server
execution cannot overlap. Stop remains available in the app and notification;
an interrupted operation does not restart automatically. Late Stop cannot turn
an already published completed result into a cancellation.

The support ZIP records the current attempt and includes the bounded runtime
report, game and service captures, input identities, lifecycle observations and
resource measurements where available. A failed/stopped attempt cannot display
an earlier successful attempt as its latest report. Guest platform flags alone
do not establish Android execution; the Android wrapper validates the required
persistence, listener and cleanup evidence before reporting a device pass.

`.github/workflows/android-atlas-game.yml` verifies the new contracts, rebuilds
the composite from its accepted donor artifacts, and builds the APK with SDK 35.
It then extracts that exact signed APK, exercises its importer with the complete
reviewed ZIP and rehashes all resulting data. On ARM64 it runs the same guest
adapter with the qualified binaries and checks all stages and preserved captures
in a private loopback namespace. This establishes hosted qualification only.

The candidate retains a development/ephemeral CI signing certificate. It does
not establish a stable release update identity. A later candidate may need a
separate installation or reinstall and re-import.

The qualified 0.4.4 APK is **355,130,247 bytes**, SHA-256
`e502b80d91c92164021684d2ea311e9e9d5c99c1b9ac178c67619844f3c5d547`.
Its 31 payloads, 14 Java source identities and six guest helpers were verified
against the exact candidate commit and APK build receipt. The original host
report is retained as hosted evidence: Java rejects it as Android execution,
accepts its cleanup unchanged, and accepts a scratch copy after changing only
the requested platform field. This establishes validator compatibility only.
See the [exact APK review](android-evidence/atlas-test-apk-verification-36638344040.json)
and [Java compatibility receipt](android-evidence/atlas-test-java-gate-compatibility-36638344040.json).

The preceding 0.4.2 APK was 355,109,686 bytes, SHA-256
`1889ca4f005a6a4a9341daaba4eb7e4ec87e9564ab98f88ddbdbe1db729edf07`. Its 30 payloads and 12 Java source identities
matched that candidate code and its build receipt. Independent review replayed
that checkpoint's hosted evidence and the then-current Java acceptance gate.

The preceding 0.4.1 APK was 355,105,590 bytes, SHA-256
`781dfb978b07e2d129c1b65b50913cee669df78e24058ee5f780aa4157502734`.
The Java acceptance gate was also replayed against this fresh hosted report:
the untouched host report was rejected as Android evidence, its cleanup was
accepted unchanged, and a scratch copy passed after changing only the requested
platform field. This is validator compatibility evidence, not Android execution.

After device create/save/restart/resume and Stop/rerun pass, the next milestones
are the graphical client on an Android surface, accelerated rendering, physical
controls/audio, then performance and packaging for normal play.
