# Basic Win32 client capability probe

The current **0.1.3** diagnostic retry retains **Run client probe**, introduced in
0.1.1, alongside the database diagnostics. It includes the complete database,
restart and shutdown test plus a PE32 graphics/input fixture in the same private
Wine/FEX session. The [cold initialization retry](ANDROID_WINE_INITIALIZATION.md)
passed all five hosted jobs in
[run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
at source `49c1626c10636e46a38493047f34ab61a9a5d5ca` on 2026-09-27 22:16:35 UTC.
All 109 tests passed without skips. Both fresh and repeat runs passed eleven
database stages and twelve client stages each, with complete cleanup. See the
[acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json).
Physical 0.1.3 acceptance remains pending.

The [0.1.2 Thor report](android-evidence/thor-initializer-timeout-20260927.json)
confirmed the initializer was still running at 150.040 seconds after four early
database stages; graphics was not reached. An open capture also prevented complete
cleanup. Version 0.1.3 removes forced duplicate registration, invalidates the
timestamp of an unready prefix, allows up to 600 seconds with five-second
progress, and marks readiness only after the PE32 fixture passes.

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

Download [coh-diagnostic-apk](https://github.com/Russianranger/coh-android/actions/runs/36354263676/artifacts/10942919938) and install
`COH-Diagnostic-0.1.3.apk`. Choose **Setup runtime**, then **Run diagnostics** and
export the report. Cold Windows initialization may take several minutes; progress
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
workspaces. Version 0.1.3 requires a fresh run and a successful repeat in each
workspace, including correct cold/warm prefix readiness and complete cleanup.
Reports bind the requested mode, hashed PE32 asset and observed pixels/input to successful owned cleanup. Native C tests reject corrupted pixels,
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
prerequisite milestone. Physical Thor M2 acceptance remains pending. The next
work is actual client/shader compatibility and Android display integration, plus
the minimal-server device gate.

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
