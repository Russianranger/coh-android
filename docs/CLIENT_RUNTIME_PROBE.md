# Basic Win32 client capability probe

The current **0.1.5** diagnostic retains **Run client probe**, introduced in
0.1.1, alongside the database diagnostics. It includes the complete database,
restart and shutdown test plus a PE32 graphics/input fixture in the same private
Wine/FEX session. The [Wine thread cleanup retry](ANDROID_WINE_THREADS.md)
passed all five jobs in
[run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
at source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4` on 2026-09-28 01:12:14 UTC.
All 125 tests passed without skips. Fresh/repeat database and client runs, ordinary
detached-helper fixtures and exited-leader/live-worker fixtures passed with genuine
capture EOF and unrelated processes preserved. The
[acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
binds all twelve APK assets and eight reports. The subsequent
[physical Thor run](THOR_DEVICE_ACCEPTANCE.md) passed all twelve combined stages
and complete cleanup. Its exact RGB samples and synthetic input passed through
llvmpipe; it reused the cluster and ready Wine prefix in a 55.344-second run.

The [0.1.4 Thor report](android-evidence/thor-capture-still-open-20260928.json)
again passed all eleven functional database/Windows stages, including 65 ODBC
sessions and restart verification; initialization took 85.957 seconds. Its sole
failure was an open wineboot output capture after prefix shutdown. The ownership
scan found zero candidates. Graphics was not requested.

A native reproduction demonstrated an exited thread-group leader with a live
worker retaining the exact run token and output pipe, which the old scan ignored.
Version 0.1.5 authenticates surviving tasks using UID, thread-group ID, start time,
PID namespace and exact token before signaling the group, preferring its pidfd.
Genuine EOF and preservation of unrelated processes remain required. The 0.1.5 device
report confirms three owned live workers behind exited leaders were cleaned up;
the exact device pipe writer was not inventoried.

The historical [0.1.4 hosted receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
records all five jobs passing at source `83f132ddb8077c9d5175ae7cd039e0754b70074e`
on 2026-09-27 22:50:49 UTC: 116 tests without skips, fresh/repeat database and client
runs, and both ordinary detached-helper fixtures with complete capture closure.
That hosted qualification did not resolve the Thor failure.

The historical [0.1.3 hosted receipt](android-evidence/accepted-wine-initialization-36354263676.json)
records all five jobs passing at source `49c1626c10636e46a38493047f34ab61a9a5d5ca`
on 2026-09-27 22:16:35 UTC: 109 tests without skips, plus fresh and repeat runs
with eleven database or twelve client stages each and complete cleanup. The
[cold initialization fix](ANDROID_WINE_INITIALIZATION.md) remains in 0.1.5.

The earlier [0.1.2 hosted receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
remains historical: all five jobs, 99 tests without skips, eleven database stages,
twelve client stages and complete cleanup passed at 2026-09-27 21:44:41 UTC.
That inherited-output correction did not resolve the device failure. Historical
0.1.1 evidence is preserved below, and 0.1.0 remains documented in
[ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md).

This step follows the client prerequisites in the imported
`upstream/ouroboros/Game/CMakeLists.txt`: desktop OpenGL, DirectInput and
DirectSound. It does not load the actual CoH executable, game assets or Cg shaders.

## Exercised behavior

- Create a Win32 window and double-buffered WGL context on the private virtual
  display, and record the observed OpenGL vendor, renderer and version.
- Upload a four-color texture, draw it on a quad, read four independently checked
  RGB pixels, and swap the window buffers. A black or missing render fails.
- Dispatch keyboard and mouse messages to the fixture's own window, and create
  the DirectInput system keyboard and mouse devices. Physical gamepad, keyboard,
  touch and mouse input are not exercised.
- Record DirectSound device enumeration as an observation, without requiring an
  audio device or claiming audible playback.
- Release fixture resources, then complete the existing ODBC, durable database
  restart and owned process shutdown checks. A fixture failure, timeout, Stop
  request or failed cleanup cannot produce a pass.

Extension and WGL entry-point availability are recorded for later shader/pbuffer
work; they are not runtime proof of those features. Known software renderer names
are labeled software. Other renderer names remain unclassified. All reports
explicitly leave hardware acceleration, Android surface presentation, Cg shaders
and game rendering unvalidated.

## Device test

The current Thor already passed the combined diagnostic. Keep 0.1.5 installed;
no repeat setup or replacement APK is needed. Stop followed by a successful new
run, app reopening/background behavior and memory measurements remain. These
can accompany the next device candidate. Export any stopped report before a new
run overwrites it. The following setup steps are for a fresh installation.


Download [coh-diagnostic-apk](https://github.com/Russianranger/coh-android/actions/runs/36364550345/artifacts/10946846847) and install
`COH-Diagnostic-0.1.5.apk`. Choose
**Setup runtime**, then **Run diagnostics** and export the report. Cold Windows initialization may take several minutes; progress
should update every five seconds. If diagnostics fails, stop further checks and
share that single report for diagnosis. Only after it passes, choose **Run client
probe** and export its report separately. After a successful probe, reopen the app
and repeat it, and test **Stop** during another run. Switch away/return during an
operation to exercise the foreground service. Setup needs
at least 5 GiB free and downloads about 641 MiB; subsequent tests are local.

Each hosted build has an ephemeral signing certificate. If Android refuses an
update over an earlier build, export any previous reports before uninstalling **COH
Diagnostic**, then install the new candidate and repeat setup. This separate
diagnostic app contains no game saves.

## Validation

The workflow runs the database-only and client-probe modes in separate ARM64
workspaces. Version 0.1.5 requires a fresh run and a successful repeat in each
workspace, including correct cold/warm prefix readiness and complete cleanup.
Both ordinary detached-helper and exited-leader/live-worker checks must prove
output EOF while preserving unrelated same-UID processes. Reports bind the requested mode, hashed PE32 asset
and observed pixels/input to successful owned cleanup. Native C tests reject corrupted pixels,
handle driver-string JSON escaping and distinguish complete extension names.
Python tests reject missing, duplicate, contradictory and out-of-scope evidence,
as well as modified or non-PE32 probe payloads. APK verification checks version,
signature, package identity and exact packaged asset bytes.

[Run 36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245)
passed all five jobs on 2026-09-27 at 20:59:41 UTC. All 93 tooling tests passed
without skips; database-only mode passed eleven stages and client mode passed
twelve, with complete owned cleanup in both. The fixture observed Mesa 22.3.6
OpenGL 4.3 through **llvmpipe software rendering**. All four RGB readbacks exactly
matched red, green, blue and white. DirectInput keyboard/mouse creation and the
synthetic messages passed. DirectSound enumeration reported zero devices; audio
playback remains unvalidated. All same-source PostgreSQL regression jobs passed.

The [acceptance record](android-evidence/accepted-client-probe-36349552245.json)
binds the downloaded evidence and APK. This completes the hosted basic client
prerequisite milestone. The [0.1.5 device receipt](android-evidence/accepted-thor-20260928.json)
now accepts the corresponding physical diagnostic gate. M3 actual game-server
execution is next; client/shader compatibility and Android display integration
remain separate unfinished work.

## Historical build identity (0.1.1)

| Field | Value |
| --- | --- |
| Source | `c1097bdc0aab433fd3cb1560fd07175c6c3dc6b0` |
| Workflow | [36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245) |
| APK | `COH-Diagnostic-0.1.1.apk`, 13,477,490 bytes |
| APK SHA-256 | `8f7d7b0201d79d44084e257fff20cca175d7f77a91a449540aaeece4df161850` |
| Runtime manifest SHA-256 | `9aebda10d6c438a48b52353989df17cf5f80104ffa56d5149b01e29c6fd17218` |
| Signing certificate SHA-256 | `2c898bb2bdac6bf64d2f582f05662e3333e9b9576e074f8f17885743c8a118a6` |

The downloaded APK artifact digest and APK hash were checked. All twelve embedded
runtime inputs matched their recorded sizes and hashes. The verified build report
and runtime manifest are in `docs/android-evidence/` with this run ID.
