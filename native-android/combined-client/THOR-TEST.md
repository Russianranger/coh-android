# AYN Thor — combined server and native client test

This is a new, separate app named **CoH Native Combined**
(`org.coh.nativecombined`). Keep the conventional launcher, accepted native
0.1.0/0.2.0/0.3.0 apps and all existing assets and reports. Do not uninstall or
clear their storage. Gates 22–24 remain accepted within their documented scope.

## Current update: 0.1.2

Install `CoH-Native-Combined-0.1.2-arm64.apk` **over the existing Combined app**.
The package and signing identity are unchanged. Keep its data; do not uninstall,
clear storage, repeat the imports or repeat runtime setup. Both prior reports
confirm the imports and runtime setup are already complete.

For this retry:

1. Stop the server in the conventional COH launcher. Close other memory-heavy
   apps before starting this disposable server test.
2. Install the update, open **CoH Native Combined**, then tap **Start server**.
   The first start verifies and protects the existing immutable inputs in place.
   This repair preserves their bytes, runtime identity and private test profile.
   Subsequent starts reuse the protection receipt with bounded metadata checks.
3. Watch the stage and elapsed time. If an interrupted ownership warning appears,
   export the report, force-stop this test app, reopen it and tap **Recover
   interrupted server**, then **Start server**. Recovery preserves the database.
4. If readiness succeeds, tap **Launch native client**, then **Connect local
   server**. Follow the character and Map handoff checks below.
5. Export the combined launcher's **report ZIP** after success or failure. If
   Android closes the app, reopen it and export before another retry. Reports
   now include memory samples, available OS process-exit reasons and up to four
   preceding attempts. A native preview JSON alone lacks server startup evidence.

The recorded 0.1.1 attempt failed after 46.026 seconds before starting DbServer.
The exact retained donor guard rejected a writable hardlinked FX payload; the
pinned bytes are correct. The fix verifies those bytes and removes write bits
from immutable inputs without weakening the original donor guard. The user also
reported a preceding Android low-memory kill; its exact cause was not retained
in that ZIP. Cold geometry admission now finishes in a reaped process before
PostgreSQL and Wine start, reducing overlapping allocations. Startup admission
and cooperative runtime memory monitoring are additional safeguards, not a
promise that Android cannot kill the app. Successful ARM64 server boot still
requires the Thor retry.

The previous qualified 0.1.1 package remains available:
11,242,291 bytes, SHA256
`278363e57b04148a4e5653026105873b164cab557fece651feb0d20ffad9f4ec`,
[0.1.1 package artifact](https://github.com/Russianranger/coh-android/actions/runs/38790024223/artifacts/12000096595).

The original 0.1.0 APK and evidence remain preserved:
11,493,783 bytes, SHA256
`4ae4ef25c6ea60bfdcac000f4ff9016ae202aa42e3414024a40c99dcf66b97ee`,
[original package artifact](https://github.com/Russianranger/coh-android/actions/runs/38763514350/artifacts/11987440686).
The following preparation section is for a **new installation**, not this update.

## Prepare the existing files

1. Stop the server in the conventional COH launcher first. Both apps use local
   ports 7000/7001/7003; run one server owner at a time.
2. Install the combined ARM64 APK. Allow its foreground-service notification.
3. Tap **Import launcher APK** and choose your existing
   `COH-Atlas-Gameplay-0.13.36.apk`. You are selecting the file, not installing it.
   It must be 42,076,692 bytes with SHA256
   `14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f`.
   A different APK is refused. The established donor is also available from the
   [0.13.36 release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.36).
4. Tap **Import game asset part** and select all four existing **CoH Assets
   1.0.0** ZIP parts. Multi-selection is supported; alternatively import them one
   at a time. Wait for the accepted input status after each operation. Keep the
   original ZIPs. An incomplete or wrong part must not enable server readiness.
5. If you already have the pinned Linux ARM64 and Wine/FEX runtime `.tar.gz` / `.tgz`
   archives, import each with **Import runtime archive (optional)**. Otherwise
   setup downloads approximately 672 MB. Arbitrary runtime archives are refused.
6. Leave **Import character backup** unused for the first disposable test.
   The app creates a separate test profile and uses the original headless helper
   to create and validate one real saved test character. Existing launcher
   accounts and characters are untouched. Optional restoration accepts a logical
   PostgreSQL PGDMP backup, at most 512 MiB, into this isolated profile; it does not
   import a raw `pgdata` directory. The supported restored profile has one
   `COHLOCAL` character with container ID 1 on Atlas or Kings Row; arbitrary
   account/profile migration is outside this initial test.
7. After imports, have at least **5 GiB free in internal storage**, then tap
   **Set up runtime**. Keep the app foreground for initial setup. Imported game
   data and the new runtime take additional space; the APK does not share the
   old launcher's private copies.

## Start server, then open native client manually

1. Tap **Start server**. Wait for **Server ready**. The first boot may take
   several minutes while initializing the isolated profile, original binaries
   and disposable character. Do not run the conventional client simultaneously.
2. Tap **Launch native client**. The offline Atlas preview should render the
   accepted character, floor and benches. This preview is not a received server
   world.
3. Tap **Connect local server**. Record the displayed state and diagnostic
   counters. A real character list should arrive from the local DbServer.
4. Choose the existing test character. Record the DB-to-Map handoff and MapServer
   state. The currently implemented endpoint is **SCENE_INCOMPLETE** once the
   bounded initial packets require further scene/entity decoding. This does not
   mean live-world rendering or authenticated AuthServer login has passed.
5. If connection or startup fails, preserve the displayed state and use
   **Export report**. Do not clear app storage or reimport everything first.

## Native preview and lifecycle checks

* Use View distance at reset: Near selects six instances; Far selects eleven.
  Verify floor/bench rendering and the character, then forward/backward/lateral
  movement, bench collision/sliding and directional animation.
* Use **Recreate**. Geometry, materials and character should return after Surface
  replacement, with decoded asset reuse preserved.
* Hold movement, press Home, release the control and return. The preview must not
  retain held movement. The native network owner suspends when backgrounded;
  reconnect explicitly only while the server is still ready.
* Reset the actor and export the native JSON report using its document picker.
  This does not reset the server character.
* Return to the combined launcher and **Export report** to save the ZIP containing
  launcher, guest-server (if produced) and native diagnostics. Attach that ZIP
  with the device/Android version and the observed failure or handoff state.

## Stop and interrupted recovery

1. Return to the combined launcher and tap **Stop server / current operation**.
   Wait for **Server stopped; test profile preserved**. Check that ready becomes
   false immediately and the native client cannot reuse an old endpoint lease.
2. Start again and confirm the same saved test character remains available.
3. Only if an interruption leaves an ownership warning: export the report,
   Android-force-stop **CoH Native Combined**, reopen it and tap **Recover
   interrupted server**. Recovery refuses if an owned child is still visible.
   It clears stale ownership/readiness metadata, not database files.
4. Stop the test server before returning to the conventional launcher.

## Acceptance record

Record import/setup result, server readiness, character-list/selection result,
MapServer state, stop/restart, native preview/lifecycle results and exported
reports separately. Host tests, ARM64 build and x86_64 Android framework checks
must not be recorded as physical Thor server interoperability. Real encrypted
AuthServer login, complete initial entity/scene decoding and server-authoritative
spawn/render remain pending milestones.
