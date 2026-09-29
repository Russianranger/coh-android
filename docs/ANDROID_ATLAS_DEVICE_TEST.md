# Atlas Park server test on Android

**Thor follow-up:** 0.4.1 passed 15 stages, including the first committed save,
clean service shutdown and PostgreSQL restart. The ownership correction recovered
a denied worker read; final cleanup was complete and the app was not blocked.
It then hit a separate 30-second DbServer readiness deadline while the normal
launcher wait was still running. No Stop/cancellation was recorded. See the
[failure receipt](android-evidence/atlas-test-thor-dispatch-failure-20260929.json).
The older [0.4.0 cleanup failure](android-evidence/atlas-test-thor-restart-failure-20260929.json)
and subsequent user force-stop remain preserved separately.

The next M3 device candidate is **COH Atlas Test 0.4.2**, application ID
`io.github.russianranger.cohatlastest`. It combines the accepted content importer
with the qualified PostgreSQL/Wine/FEX runtime, DbServer, Atlas Park MapServer,
and creation/resume TestClients. It runs an automatic character persistence test.
It does not supply a graphical game client or human controls.

The 0.4.2 correction is being qualified. It gives schema/listener readiness and
positive main-loop dispatch one shared 600-second DbServer startup budget.
The overall 90-minute guest deadline and all readiness requirements remain.
The 0.4.1 identity-checked worker-exit recovery and bounded denied-read diagnostics
remain in place. Live unreadable ownership, changed identities and unresolved
cleanup still fail. The accepted base runtime and game binaries are unchanged.

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
The failed 0.4.1 Atlas Test used an ephemeral CI signing key which is no longer
available. Uninstall only **COH Atlas Test 0.4.1** before installing 0.4.2;
its private runtime/import will need preparing again. Keep the earlier accepted
diagnostic and setup apps installed.
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
| MapServer, creation/resume TestClients and bridge | Run `36510836956` |
| Generated schema | Run `36088012666`; 99 tables |
| Complete base data | 173,011 files / 2,977,730,517 bytes |
| Full data inventory SHA-256 | `b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4` |

The executable package remains the byte-bound accepted package from commit
`ac4c1f7978be444a893f65f5177641191861d42f`. Its receipt SHA-256 is
`ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a`.
The new APK separately records its current Android wrapper and guest adapter
commit. It must not relabel the older executables as newly compiled.

Setup downloads the hash-pinned runtime archives over HTTPS. No root, Termux,
Windows PC, GitHub token or manual server commands are needed on the device.
The game services and TestClients use their accepted loopback-only binding
profiles. These bindings are not a claim of device-wide network isolation;
hosted qualification retains its mandatory private network namespace.

## Device procedure after hosted qualification

1. After uninstalling only the failed 0.4.1 Atlas Test, install
   `COH-Atlas-Test-0.4.2.apk`.
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
6. After that pass is accepted, start another test, use **Stop** while game
   services are active, wait for cleanup and export that report. Then run a fresh
   successful test and export its report. Switch apps and lock/unlock the screen
   during this final run. The service records bounded lifecycle observations.

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

The preceding 0.4.1 APK was 355,105,590 bytes, SHA-256
`781dfb978b07e2d129c1b65b50913cee669df78e24058ee5f780aa4157502734`.
The Java acceptance gate was also replayed against this fresh hosted report:
the untouched host report was rejected as Android evidence, its cleanup was
accepted unchanged, and a scratch copy passed after changing only the requested
platform field. This is validator compatibility evidence, not Android execution.

After device create/save/restart/resume and Stop/rerun pass, the next milestones
are the graphical client on an Android surface, accelerated rendering, physical
controls/audio, then performance and packaging for normal play.
