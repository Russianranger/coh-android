# Native Combined Client

One separately installed Android app imports the existing local-server inputs,
starts an owned headless local server, and lets the user open the native client
manually. The package is `org.coh.nativecombined`; the conventional launcher and
accepted native Session Client remain installed with their private data intact.

Follow [THOR-TEST.md](THOR-TEST.md) for the consolidated device test.

## Scope

* The server uses the existing ARM64 PostgreSQL and Wine/FEX DbServer/MapServer
  runtime. No graphical Windows game client is launched.
* The native client uses native C/C++ transport and GLES rendering. Its initial
  scene is the accepted Session Client 0.3.0 preview, with its original assets.
* The explicit loopback development session can request an existing character
  list, select a character, and follow the real DB-to-Map handoff. It uses the
  local server's `UseFakeAuth` policy, not a fabricated authenticated receipt.
* Full scene/entity decoding and server-position rendering are incomplete.
  `SCENE_INCOMPLETE` is the current bounded endpoint, not a live-world success.
* Real AuthServer authentication and actual guest-server/device interoperability
  remain separate qualification requirements. Deterministic socket peers do not
  prove a real server session.

## External inputs

The APK embeds small PRoot cores, reviewed helper scripts, manifests, native
libraries and the accepted preview fixtures. It excludes rootfs, Wine/FEX,
PostgreSQL binaries, PE server/client files and the four game asset archives.

`tools/prepare.py` pins the previously published 0.13.36 donor APK and qualified
0.3.0 scene APK. Runtime imports accept only exact manifest members/hashes;
unrelated or malformed archives cannot replace an accepted generation. The
0.13.36 donor helper closure is preserved unchanged. New server orchestration is
separate in `runtime/server_runtime.py`.

The app imports through Android's document picker, copies accepted inputs into
its own storage, and publishes completed generations atomically. It never reads
another app's private storage. Setup requires ARM64 and at least 5 GiB of free
internal space after imports. Missing pinned Linux and Wine archives are
downloaded during setup; existing matching archives can be imported instead.
This initial test stores its own runtime and profile, so it needs additional disk
space even when the old launcher already has those files.

## Ownership and reports

A foreground service owns imports, setup and the server process. Readiness
requires a live owner plus a current, matching guest heartbeat; the native client
receives only the current loopback development policy. Stop, stale readiness,
backgrounding the client, changed session/generation and process exit revoke the
native connection. Stop requests cooperative guest cleanup, then uses one bounded
120-second deadline with 15/5-second termination stages. An incomplete ownership
marker blocks reuse until explicit interrupted-server recovery. Recovery never
deletes database data.

Reports contain bounded diagnostics, state transitions and numeric native packet
counters. Export omits account identifiers, configuration, profile dumps,
passwords and authentication keys. Guest readiness is not equivalent to native
protocol success. Native packet receipt is not equivalent to complete scene
replication.

## Building and qualification

The workflow `.github/workflows/native-combined-client.yml` prepares exact inputs,
reuses the pinned public crypto artifact, runs host/sanitizer contracts, builds
ARM64 and an x86_64 emulator package, lints and audits both, then runs the Android
13 framework driver. A clean source receipt and exact APK hashes bind the driver
to its package. The emulator tests actual document import/refusal, preview GLES,
Near/Far selection, Surface recreation, Home/return, missing-policy refusal and
report export; scripted native UDP tests are labelled separately. It cannot run
the ARM64 Wine/FEX server on the x86_64 emulator.

## First Thor startup failure

The exported `COH-NativeCombined-1792088413287.zip` records a failed 0.1.0
server attempt lasting 825.923 seconds, ending in `local_dbserver_startup`.
PostgreSQL, Wine registration and both ODBC checks completed. No DbServer,
MapServer or TestClient process was recorded. Cleanup completed and the private
profile was preserved. The original generic failure code cannot identify the
exact failing preparation helper or prove a port conflict. Keep this evidence
under `evidence/20261015/startup-failure-0.1.0/`.

The 0.1.1 update removes duplicated ODBC work and adds session-bound failure
codes, bounded stage history and elapsed times. Completed child execution times
must be distinguished from their age at cleanup; the 0.1.0 report overwrote
those execution times. A stopped run's displayed timer now freezes, and old
guest evidence is labelled as a previous session in exports. These diagnostic
improvements do not establish successful Thor server startup or a live native
world session. Install updates over this separate test app to preserve its
verified imports and private profile.

Local preparation and checks:

```sh
python3 native-android/combined-client/tools/prepare.py --donor-apk /path/COH-Atlas-Gameplay-0.13.36.apk --scene-apk /path/CoH-Native-Session-Client-0.3.0-arm64.apk
python3 native-android/combined-client/tools/host_check.py --donor-apk /path/COH-Atlas-Gameplay-0.13.36.apk --ndk /path/android-ndk-r28c --output /tmp/combined-host
python3 native-android/combined-client/gradle.py -PprobeAbis=arm64-v8a -PcohCryptoRoot=/path/crypto-build :app:assembleDebug :app:lintDebug
```

The public test signing identity is for development packages. Generated inputs,
APK outputs, SDKs and caches are excluded from source control.

## Second Thor startup failure and memory interruption

The 0.1.1 report in `evidence/20261015/startup-failure-0.1.1/` identifies
`server_fx_catalog._regular`: an exact pinned FX payload was writable with two
hardlinks. The unchanged donor permits a shared source only when read-only.
0.1.2 seals verified immutable imports before publication and repairs an existing
ready generation on Start without changing its identity or saved profile. A
one-time streamed pin check precedes permission changes; a completed receipt
allows later bounded owner/type/size/mode checks. The original FX guard remains
unchanged. The regression uses the actual donor payload and original guard.

The user also observed an earlier Android low-memory kill. Its allocation site
is not recoverable from the supplied ZIP. Cold original geometry admission now
runs in a short-lived owned Python process before PostgreSQL/Wine startup; its
exact original manifest and geometry checks remain intact. The parent reaps the
child and verifies the retained warm receipt before continuing. Android memory
admission, cooperative runtime pressure stops and bounded numeric telemetry
supplement that allocation-lifetime change. These cannot guarantee prevention
of Android process kills. OS exit records and four preceding attempts are
included in report exports, without account identifiers or raw traces. Neither
this repair nor emulator preview tests establish successful Thor guest startup.
