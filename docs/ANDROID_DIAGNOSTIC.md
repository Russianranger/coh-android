# Thor diagnostic APK (M2)

Status: **0.1.3 passed hosted acceptance and is ready for a Thor retry**.
[Run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs at source `49c1626c10636e46a38493047f34ab61a9a5d5ca` on
2026-09-27 22:16:35 UTC. All 109 tests passed without skips. Fresh and repeat runs
passed eleven database stages and twelve client stages each, with complete
cleanup. The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds the verified APK, packaged payloads and runtime evidence.

**M2 physical-device acceptance remains pending.** The
[0.1.2 Thor report](android-evidence/thor-initializer-timeout-20260927.json) confirms
wineboot was still running at 150.040 seconds. Four early native database stages
passed, but Windows ODBC and graphics were not reached. Output capture remained
open after prefix shutdown, so complete cleanup was not proved. The accepted
[Atlas transfer gate](MAP_TRANSFER_VALIDATION.md) retains its Windows scope.

This is a separate app, `io.github.russianranger.cohdiagnostic`, targeting the
AYN Thor (Android 13, ARM64). It exercises the platform needed by the future CoH
launcher. It contains no game binaries or game assets and cannot launch the game.

## Current retry APK

Download [coh-diagnostic-apk](https://github.com/Russianranger/coh-android/actions/runs/36354263676/artifacts/10942919938) and install
`COH-Diagnostic-0.1.3.apk`. The [cold initialization correction](ANDROID_WINE_INITIALIZATION.md)
uses `wineboot -i` for one registration pass, removes the timestamp from an unready
prefix, allows up to 600 seconds, and reports progress every five seconds. It
marks the prefix ready only after the PE32 fixture passes. Both fresh and repeat
hosted runs completed the database, client and cleanup checks. Cold initialization
took 39.911 seconds in database mode and 40.305 seconds in client mode, with one
registration pass each. Both warm runs took 4.629 seconds with no registration
passes. These hosted times do not predict Thor timing.

## Historical 0.1.2 result

[Run 36352420585](https://github.com/Russianranger/coh-android/actions/runs/36352420585)
passed all five jobs at source `1afb0610095ebe3cb8aba591ea22d749613b7276` on
2026-09-27 21:44:41 UTC: 99 tests without skips, eleven database stages, twelve
client-probe stages and complete cleanup. Its
[acceptance receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
preserves the build and reports. The [inherited-output wait fix](ANDROID_WINEBOOT_RETRY.md)
was exercised successfully on hosted Linux, but did not resolve the Thor failure.

This page preserves the original 0.1.0 evidence below. The 0.1.1 receipt remains
in [the client-probe record](CLIENT_RUNTIME_PROBE.md#historical-build-identity-011).

## Original accepted APK (0.1.0)

The original hosted gate passed all four jobs, 80 tooling tests and eleven guest
stages at 2026-09-27 17:29:16 UTC. Its
[acceptance receipt](android-evidence/accepted-hosted-36336644450.json) is historical.

Download the **coh-diagnostic-apk** artifact from
[run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
and extract `COH-Diagnostic-0.1.0.apk`. These are the original accepted bytes; the certificate belongs to this CI build.

| Identity | Accepted value |
| --- | --- |
| Source commit | `0b61d7455f40f05709f912338cd5de8b1d72d750` |
| APK size | 13,309,477 bytes |
| APK SHA-256 | `80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac` |
| Runtime manifest SHA-256 | `ace8964c905d4affbf9c28ee26e5922b6e4fc3fef3b0c88b7df5d8a806aaa14f` |
| Signing certificate SHA-256 | `a6172785398fd703e7122fd51e292e09dcfb70cac0100541af4cc5911f39fbd4` |
| Package / version | `io.github.russianranger.cohdiagnostic` / `0.1.0` (1) |
| Android / ABI | Minimum API 26, target API 35 / `arm64-v8a` |

The [APK build report](android-evidence/apk-build-36336644450.json) records verified
signature, package, ABI and payload bytes. The signing certificate is ephemeral;
this candidate does not establish a stable release/update channel.

## What the diagnostic does

The app provides **Setup runtime**, **Run diagnostics**, **Run client probe**, **Stop**, and
**Export latest report**. A foreground service owns each operation and shows progress
while the activity is closed or rotated. Stop requests a graceful guest cleanup
before terminating only the owned PRoot wrapper as a bounded fallback.

Setup verifies two pinned downloads (353,710,639 and 318,095,727 bytes), safely
unpacks them into a new private generation, and combines them with the packaged
PostgreSQL overlay and diagnostic assets. Keep at least **5 GiB free**. The
downloads total about **641 MiB**; installation uses more space while unpacking.
No separate Termux app, root access, or Windows PC is required. Network access is
needed for initial setup; the diagnostic uses only private state and loopback.

The database runs natively on the ARM64 CPU using Linux/glibc inside app-owned
PRoot. This is not a Bionic PostgreSQL port. Wine 10 and FEX WoW64 supply Win32
execution. One long-lived PRoot process provides the shared SysV memory namespace;
the guest sees UID 1000 while Android continues to enforce the app's real UID.
PRoot and its loader are executable APK libraries, rather than writable downloaded
Android executables. The pinned base, Wine and source archives are in
[`runtime-lock.json`](../android/runtime-lock.json).

The guest requires:

1. Verified inputs, ARM64 PostgreSQL/Wine executables and PE32 diagnostic binaries.
2. A private owned PostgreSQL cluster, loopback listening, authenticated identity
   and a restricted fixture role.
3. A real Win32 executable loading a fixture DLL and the Windows ODBC manager.
4. The existing x86 psqlODBC test, including 65 connections, transactions,
   rollback, Unicode/binary values, schema operations and reconnect.
5. Graceful PostgreSQL shutdown, restart of the same cluster and verification of
   the committed fixture through Win32 ODBC.
6. Prefix-scoped Wine shutdown, graceful final database shutdown and reaping of
   owned processes. A failed cleanup cannot count as a pass.

The diagnostic compiles the existing ODBC fixture with two ANSI import aliases:
`SQLDriverConnectA` and `SQLExecDirectA` use their
equivalent unsuffixed ANSI exports. The pinned Wine 10 export table stubs those
`A` names. Its implemented ANSI functions load the registered Windows
psqlODBC DLL; no Unix ODBC substitute is used. Build-time inspection verifies the
actual PE imports and records them in the runtime manifest. The fixture's SQL,
65-connection test, Unicode checks and acceptance markers remain unchanged.
See the [pinned export source](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/odbc32.spec)
and the [failed runtime evidence](android-evidence/runtime-smoke-report-36331879591.json).

The version query uses `SQLGetInfoW` with the actual manager handle and validates
its bounded UTF-16 result before emitting the same version header. The pinned
Wine ANSI fallback incorrectly calls its public Unicode wrapper with a
driver-private handle; this hung after successful connection and SQL queries.
The [exact source line](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/proxyodbc.c#L2975)
and the [traced failure](android-evidence/runtime-smoke-report-36334953501.json)
identify the cause. Import verification rejects both
ANSI version-query names and requires the working Unicode entry point. The
fixture's SQL assertions and acceptance markers are unchanged.

The column-metadata query uses `SQLColumnsW` with the same `dbo`/`pgprobe`
names and NULL catalog/column filters. Wine's [ANSI fallback](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/odbc32/proxyodbc.c#L1113)
rejects those valid NULL filters before invoking the driver. The Unicode call
preserves them; all ten-column and canonical-type checks remain required. The
[earlier failing report](android-evidence/runtime-smoke-report-36335852159.json)
is retained alongside the successful retry.

The x86 MSI is installed through the verified PE32 `syswow64/msiexec.exe`.
Wine's ODBC installer writes the process's registry view, so the installer must
match the 32-bit probe. A separate Win32 preflight reads the actual HKLM32
registration, loads its driver DLL with dependency search enabled, and checks
the driver's exports. The connection uses that observed registered name. A
registry or DLL failure is reported with its Win32 error before an ODBC call.

Passwords remain in private state, are removed from emitted diagnostics, and are
not part of the exported ZIP. Export contains the bounded report, recent log and
build manifest; it does not export a populated database or game save files.

## Validation and build

The [Thor diagnostic workflow](../.github/workflows/android-diagnostic.yml) first
runs focused archive, ownership, cancellation and packaging tests. It then:

- Builds PostgreSQL from a hash-pinned official source in a digest-pinned ARM64
  Bookworm builder, verifies the resulting ELF/dependency closure and performs a
  native Linux transaction/restart smoke test.
- Builds the patched Android PRoot and compiles the actual Win32 probes, then
  compiles, signs and verifies the APK with JDK 17 and Android SDK 35.
- Builds the equivalent native ARM64 Linux PRoot and runs the APK's exact guest
  assets against the pinned base/Wine archives, using the same Java extractor.

The accepted [raw guest report](android-evidence/runtime-smoke-report-36336644450.json)
contains eleven passed stages, no failures and complete owned cleanup. The real
32-bit Windows psqlODBC driver reported `18.00.0004`; all eight ODBC check groups
passed, including 65 simultaneous connections, rollback, bound UTF-16/binary
values, column metadata, schema rebuild and reconnect. A graceful restart of the
same PostgreSQL cluster was followed by a fresh Win32 verification of committed
data. Final PostgreSQL shutdown, prefix-scoped Wine shutdown and owned-process
reaping all passed. The [same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36336644454)
also passed all four jobs. Earlier failures remain in the
[attempt history](android-evidence/attempts-20260927.json).

Hosted Linux success establishes this exercised guest path. It does not establish
Android SELinux/device behavior, activity/foreground-service lifecycle, graphics,
performance or gameplay. A passing Thor retry remains a required acceptance step.
Preserve the accepted APK and exported report; do not assume a later candidate
with another signing certificate will install as an in-place update.

Source and license records are provided in the workflow artifacts and the
[third-party notices](../android/THIRD_PARTY_NOTICES.md). Immutable upstream game
snapshots and all previously accepted Windows reference inputs remain untouched.

## Thor acceptance steps

1. Install the accepted `COH-Diagnostic-0.1.3.apk` above. If Android
   reports a signing conflict, export old reports before uninstalling **COH Diagnostic**.
   Open **COH Diagnostic**
   and choose **Setup runtime** with a reliable connection and at least 5 GiB free.
   Wait for setup to finish; no game import is needed.
2. Choose **Run diagnostics**. Keep its foreground notification active and wait
   for a passed or failed result. Cold Windows initialization may take several
   minutes, with elapsed progress every five seconds and a ten-minute limit.
   Rotate or switch away and return to check that the operation persists.
3. Choose **Export latest report**, save the ZIP using Android's document picker,
   and attach it to this conversation. If diagnostics failed, stop further checks
   and share that single report for diagnosis.
4. Only after diagnostics passes, choose **Run client probe** and export its report.
   After a successful probe, close/reopen the app, repeat it and export the result.
5. Start another diagnostic run, choose **Stop**, wait for its terminal result,
   then export that report. A Stop request alone does not prove owned cleanup.

If the result is **Cleanup failed**, export the report first. Then use Android
**Settings → Apps → COH Diagnostic → Force stop** and reopen the app. Closing the
activity alone does not clear the process-wide cleanup block.

A passing Thor report plus repeat-run and Stop evidence qualifies the exercised
device database and compatibility runtime. It does not qualify game execution.
The next gameplay work is the minimal Android server and actual client/shader
compatibility; full rendering, combat and mission behavior remain later gates.
