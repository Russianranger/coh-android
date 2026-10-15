# AYN Thor — combined server and native client test

This is a new, separate app named **CoH Native Combined**
(`org.coh.nativecombined`). Keep the conventional launcher, accepted native
0.1.0/0.2.0/0.3.0 apps and all existing assets and reports. Do not uninstall or
clear their storage. Gates 22–24 remain accepted within their documented scope.

## Current update: 0.1.5 Return to launcher

Install `CoH-Native-Combined-0.1.5-arm64.apk` **over Combined**. Keep the existing
imports, runtime, saved test profile, accepted native apps and conventional
launcher. Do not uninstall, clear storage or repeat setup.

Your exact 0.1.4 report confirms a real server boot, character list/selection,
initial Map connection acceptance and shortcut-catalog admission. Scene reception
then fails with `COH_LIMIT` before a scene prefix reaches the parser. The visible
scene remains the offline preview. This navigation update does not change that
protocol bound or claim a completed live world.

1. Start the server from the launcher, then open the native client manually.
2. Tap **Return to launcher** at the top of the native controls. It must return
   to the existing launcher so server status, **Stop server** and ZIP export are
   available. Returning closes the client; it does not stop the server.
3. Launch the native client again. Its preview must render, and connecting again
   must require the explicit **Connect local server** button. Try returning while
   the character list is visible and after the current scene-transfer failure.
4. Export the launcher ZIP after the test or first failure, before another retry.
   Stop the server through the launcher when finished. Keep the saved character.

## Previous qualified 0.1.4 interrupted-start recovery

Historical handoff; use the current 0.1.5 procedure above. The new physical report
records successful startup and a clean manual stop. It does not test a separate
force-stop/recover/restart cycle or identify the earlier Android memory-kill cause.

Current ARM64 delivery: **11,527,815 bytes**, SHA256
`18b06672a11af3a50bd2ece77ce41bc2fecec7f8ebe6037408245119ca21ad2c`.
[Download package artifact](https://github.com/Russianranger/coh-android/actions/runs/38811852104/artifacts/12007874953).
The [successful workflow](https://github.com/Russianranger/coh-android/actions/runs/38811852104)
passes twelve host suites, both ABI builds/package audits, 76 current/donor
runtime executions without skips, and **26 Android13 framework checks**. All
native ELF payloads and accepted scene assets retain the exact qualified 0.1.3
bytes. Source: `294041ddff3b5f80ae4dbf25073b01e037ecc7ee`. Actual 0.1.4 Thor
server restart and native handoff are the next physical tests, not yet accepted.

Install `CoH-Native-Combined-0.1.4-arm64.apk` **over Combined**. Do not uninstall,
clear storage, reimport assets, repeat setup or remove the saved test profile.
The 0.1.3 report failed before Wine/client startup because a pre-existing private
display endpoint remained after interruption. The next session now uses a fresh,
short session-derived endpoint. It never deletes or takes over an old endpoint.
The real Android backing pathname is checked against the Unix-socket size limit.

The report separately records an Android low-memory exit around 5.4 seconds into
a preceding startup. The allocating process/cause was not retained. The last
samples still showed over 8 GB system headroom and over 245 MB Java headroom;
those measurements cannot guarantee against an OS kill. Original streamed asset
verification, memory admission and cleanup checks remain enabled. New stage
boundaries preserve bounded guest RSS/peak observations for the next diagnosis;
unknown cgroup metrics are explicitly null, not assumed zero.

For this retry:

1. Stop any running test server and install over Combined. Keep the conventional
   launcher closed. Existing runtime, immutable inputs and saved character stay.
2. If an interrupted-owner warning appears, use **Recover interrupted server**
   after reopening the app with no owned server still running. If recovery refuses
   live children, export first, Android-force-stop only Combined, reopen and
   recover. Do not delete files or change Android memory-killer settings.
3. Tap **Start server**. It must no longer fail merely because an older session's
   display endpoint exists. Record the stages and wait for server readiness.
4. Once ready, launch the native client manually, Connect, select the existing
   character and record its resulting protocol state. The expected implemented
   boundary is still `SCENE_INCOMPLETE`; the visible scene is an offline preview.
5. Return to the launcher, stop the server normally, and start once more. Confirm
   the same character persists. If this passes, an optional interruption check is
   to force-stop only Combined while its server is ready, reopen, recover and
   start again. Never clear app data or run two server owners simultaneously.
6. Export the combined **report ZIP** after success or the first failure, before
   another retry. It includes the current installed APK hash and sampled guest
   resources. Retained native reports from older app versions are clearly named
   `previous-app-native-client-report.json`; they are not new test results.
7. If Android kills the app again, reopen and export before recovery/retry. The
   earlier attempt and OS exit record are needed even when no final guest report
   could be written. This update repairs restart isolation; it does not claim to
   have identified or eliminated the separate low-memory exit.

The [0.1.3 failure record](evidence/20261015/startup-repair-0.1.4/thor-failure-sanitized.md)
explains the current failure and the stale 0.1.2 client report. The qualified
0.1.3 APK, accepted scene and all earlier evidence remain available below.

## Previous qualified 0.1.3 connection repair

Historical handoff; use the current 0.1.4 procedure above.

Install `CoH-Native-Combined-0.1.3-arm64.apk` **over the existing Combined app**.

Current ARM64 delivery: **11,521,251 bytes**, SHA256
`8b60102521c23d42e2706331d266602d5c7429b3b42799e053361f47331b90c5`.
[Download package artifact](https://github.com/Russianranger/coh-android/actions/runs/38804511398/artifacts/12005078271).
The [successful workflow](https://github.com/Russianranger/coh-android/actions/runs/38804511398)
passed eleven host suites, both ABI builds/lint and **24 Android13 framework
checks**, including the real app's landscape character picker against an
explicitly scripted UDP peer. Runtime/driver source:
`1ca6afc1b375d1e3a59ed13be562d9f9d1d0b81e`. Actual 0.1.3 Thor Map acceptance
remains the purpose of this retry.

The package and signing identity are unchanged. Keep its data; do not uninstall,
clear storage, repeat imports or repeat runtime setup. Your 0.1.2 report confirms
that the server reached readiness after 9 minutes 16 seconds, and the native
client received a real character list, selected a character and requested the
DB-to-Map handoff. Map connection acceptance and live-world rendering were not
established.

This update bounds the scrolling controls and the actual Surface dimensions so
showing the character picker cannot collapse the accepted camera viewport. It
also separates the accessible command-name list from the smaller shortcut schema
limit: the source server can send over 900 command names. Reports retain the
terminal protocol stage, status and numeric transport counters after cleanup and
Home/return. The old report's `COH_LIMIT` is consistent with that parser defect;
without its packet body, the exact failed packet cannot be identified.

For this retry:

1. Stop any existing server owner first. Install the update over Combined and
   open it. Keep the conventional launcher closed during the disposable test.
2. Tap **Start server** and wait for **Server ready**. Existing inputs, runtime
   and saved disposable character are reused. Do not repeat setup. First-boot
   timing is not a guarantee of warm-start timing; record the displayed stages.
3. Tap **Launch native client**, then **Connect local server**. When the
   character list appears, the scene must keep rendering. Controls scroll within
   the upper part of the screen; scroll there to reach other buttons if needed.
4. Select the same existing test character. Record the resulting state. The
   expected implemented boundary is **SCENE_INCOMPLETE** when the server's
   initial scene/entity packets require further decoding. The visible scene
   remains the accepted offline preview, not server-authoritative world state.
5. Before exporting, check **Recreate**, then Home/return and explicit reconnect.
   Backgrounding suspends the network owner; it does not silently reconnect.
6. Export the native JSON and the combined launcher's **report ZIP**, whether
   the handoff succeeds or fails. Export before another retry if Android closes
   the app. The ZIP preserves up to four preceding attempts and available numeric
   OS exit reasons. A preview JSON alone lacks the complete server evidence.
7. Stop the server through the launcher, then start once more and verify the
   saved character is retained. Stop/restart cleanup remains a separate check.

The new report also records the earlier Android low-memory exit; the latest
force-stops have different OS reasons. No allocation site was retained for the
old kill. The successful 0.1.2 server snapshot had no measured pressure stop and
at least 6.05 GB available system memory across 701 samples. This does not
establish the peak memory use between samples or guarantee against OS kills.
The old 0.1.1 FX failure is explicitly previous-session evidence in the ZIP.

Keep the qualified 0.1.2 APK available:
11,519,003 bytes, SHA256
`1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449`,
[0.1.2 package artifact](https://github.com/Russianranger/coh-android/actions/runs/38795244645/artifacts/12002281757).
Its [exact-package Android13 continuation](https://github.com/Russianranger/coh-android/actions/runs/38797308843)
passed all 18 framework checks. The Thor report now adds actual server boot and
DB list/selection/handoff evidence, within the limits described above.

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
