# Thor diagnostic APK (M2)

Status: the diagnostic APK builds, signs and verifies successfully. Hosted guest
qualification is still in progress. Run `36334953501` established the first
ODBC connection and two SQL queries, then localized a pinned Wine ANSI metadata
wrapper bug. Its [failed report](android-evidence/runtime-smoke-report-36334953501.json)
and [attempt history](android-evidence/attempts-20260927.json) are preserved.
No hosted guest or on-device pass is claimed. The accepted
[Atlas transfer gate](MAP_TRANSFER_VALIDATION.md) remains unchanged.

This is a separate app, `io.github.russianranger.cohdiagnostic`, targeting the
AYN Thor (Android 13, ARM64). It exercises the platform needed by the future CoH
launcher. It contains no game binaries or game assets and cannot launch the game.

## What the diagnostic does

The app provides **Setup runtime**, **Run diagnostics**, **Stop**, and
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

The diagnostic compiles the existing ODBC fixture with three ANSI import aliases:
`SQLDriverConnectA`, `SQLExecDirectA` and `SQLColumnsA` use their
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
and traced failure above identify the cause. Import verification rejects both
ANSI version-query names and requires the working Unicode entry point. The
fixture's SQL assertions and acceptance markers are unchanged.

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

Hosted Linux success establishes the exercised guest path. It does not establish
Android SELinux/device behavior, activity/foreground-service lifecycle, graphics,
performance or gameplay. The first Thor report remains a required acceptance step.

The first APK uses an ephemeral CI signing certificate. It is a diagnostic
candidate, not a stable release/update channel. Preserve its APK and exported
report; do not assume a later candidate will install as an in-place update.

Source and license records are provided in the workflow artifacts and the
[third-party notices](../android/THIRD_PARTY_NOTICES.md). Immutable upstream game
snapshots and all previously accepted Windows reference inputs remain untouched.

## Thor acceptance steps once a verified APK is available

1. Install COH Diagnostic and choose **Setup runtime** with a reliable connection.
2. Choose **Run diagnostics**. Keep its notification active; wait for a passed or
   failed result. No game import is needed.
3. Choose **Export latest report** and attach the ZIP to this conversation.
4. After a successful run, repeat after closing/reopening the app. Also exercise
   Stop during a run and export that result, so ownership and shutdown can be
   checked on the device.

If the result is **Cleanup failed**, export the report first. Then use Android
**Settings → Apps → COH Diagnostic → Force stop** and reopen the app. Closing the
activity alone does not clear the process-wide cleanup block.

A passing M2 report qualifies the exercised database and compatibility runtime.
The next gameplay work is the minimal Android server and basic client-runtime
probe; full rendering, combat and mission behavior remain later gates.
