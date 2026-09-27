# Basic Win32 client capability probe

The 0.1.1 diagnostic candidate adds **Run client probe** alongside the existing
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

The implementation alone is not an accepted runtime result. Hosted results are
recorded after the workflow completes. A passing hosted fixture remains a basic
client prerequisite check; the next work is actual client/shader compatibility
and Android display integration, plus the pending minimal-server device gate.
