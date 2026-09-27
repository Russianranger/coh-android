# Basic Win32 client capability probe

The 0.1.1 diagnostic APK adds **Run client probe** alongside the existing
database diagnostics. It includes the complete database/restart/shutdown test and
one additional PE32 fixture in the same private Wine/FEX session. Physical Thor
acceptance remains pending. The accepted 0.1.0 database-only candidate and its
evidence remain documented in [ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md).

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

Install `COH-Diagnostic-0.1.1.apk`, choose **Setup runtime**, then **Run diagnostics**
and export the report. Choose **Run client probe** and export its report separately.
Reopen the app and repeat the probe, and test **Stop** during another run. Switch
away/return during an operation to exercise the foreground service. Setup needs
at least 5 GiB free and downloads about 641 MiB; subsequent tests are local.

Each hosted build has an ephemeral signing certificate. If Android refuses an
update over 0.1.0, export any previous reports before uninstalling **COH
Diagnostic**, then install the new candidate and repeat setup. This separate
diagnostic app contains no game saves.

## Validation

The workflow runs the database-only and client-probe modes in separate fresh
ARM64 workspaces. Reports bind the requested mode, hashed PE32 asset and observed
pixels/input to successful owned cleanup. Native C tests reject corrupted pixels,
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

## Build identity

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
