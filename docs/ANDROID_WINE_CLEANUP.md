# Thor Wine helper cleanup retry (0.1.4)

The [0.1.3 Thor report](android-evidence/thor-functional-pass-cleanup-failure-20260927.json)
passed all eleven functional stages. Cold Wine initialization completed in 90.927
seconds with one registration pass. Native PostgreSQL, real PE32 DLL loading,
Windows ODBC with all 65 connections, SQL/value/metadata checks, and durable
same-cluster restart verification passed on the physical device.

The sole failure was `Owned process input/output capture did not close: wineboot`.
The Wine prefix lock and socket were inactive, and PostgreSQL shut down cleanly,
but an inherited output pipe remained open. Those server checks do not identify
or establish the exit of every detached Unix helper. Complete M2 device acceptance
therefore remains pending; the earlier initializer timeout has been resolved in
this run.

## Targeted repair

Version 0.1.4 adds exact per-run ownership for Wine helpers and bounded cleanup
after prefix shutdown. Wine alone receives a random run token. Cleanup checks
that exact token, real Android UID and process identity, preferring pidfds for
signaling and rechecking start times. It allows at most six seconds for the
owner scan and TERM/KILL cleanup within the existing shutdown budget. Processes
older than the diagnostic cannot inherit its fresh child-only token and are
excluded before reading private environment data. Possible descendants with
unreadable ownership still fail explicitly. All owned output captures must close. The diagnostic does not turn an open capture into
a successful cleanup result merely by closing its reader.

The disabled menu-helper entry is also corrected to `winemenubuilder.exe`.
Wine's pinned [load-order implementation](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/loadorder.c)
strips `.dll`, but not `.exe`, from
module names; the old unsuffixed entry did not suppress the executable, and the
Thor trace shows it launched. The report does not prove that helper was the
remaining pipe writer.

## Accepted hosted qualification

[Run 36356283176](https://github.com/Russianranger/coh-android/actions/runs/36356283176)
passed all five jobs at source `83f132ddb8077c9d5175ae7cd039e0754b70074e`,
finishing on 2026-09-27 at 22:50:49 UTC. All 116 tooling tests passed without
skips. Both modes passed fresh and repeated diagnostics: eleven database stages
or twelve client stages, with every owned input/output capture closed and no
remaining token-owned Wine process. The same-source
[PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36356285898)
also passed.

Each ARM64 PRoot job separately exercised a detached helper retaining stdout and
ignoring TERM. Exact ownership cleanup sent TERM then KILL through pidfds,
observed genuine EOF, and preserved an unrelated process with the same UID and
Wine prefix but a different token. Both receipts recorded zero inspection
failures and zero remaining owned processes. This regression exercises the
failure mechanism; the original Thor report did not identify its pipe writer.

| Mode | Cold Wine initialization | Repeated initialization | Registration passes |
| --- | ---: | ---: | --- |
| Database | 39.397 s | 4.276 s | 1 cold, 0 repeat |
| Client | 37.973 s | 4.126 s | 1 cold, 0 repeat |

These are hosted timings. Client evidence covers headless llvmpipe rendering,
four exact RGB readbacks and synthetic input, with physical capabilities still
explicitly unvalidated. Downloaded archive hashes, all twelve APK payloads and
all six hosted reports were verified. The
[acceptance receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
binds the jobs, package, payload inventory and reports.

Download [coh-diagnostic-apk](https://github.com/Russianranger/coh-android/actions/runs/36356283176/artifacts/10943554283):
`COH-Diagnostic-0.1.4.apk`, version code 5, 13,481,586 bytes, SHA-256
`49e4480e0c6d0d951ab49bbf5402d66488a50a165e23c750af591ae9e0513097`.
Runtime manifest SHA-256:
`18c57d8fa3bf464468609f6380b30c034f791857b3ed45930b378f226cd43a07`.
Version 0.1.4 has not yet been run on the physical Thor.

## Device retry

1. Export any reports, uninstall only the old **COH Diagnostic**, and install
   `COH-Diagnostic-0.1.4.apk`. Test builds use different signing certificates;
   this separate app contains no game saves.
2. Choose **Setup runtime**, then **Run diagnostics** and export its report.
   If it fails, stop further checks and send that report.
3. After a pass, run **Run client probe**, export its report, then check repeat
   operation and **Stop** in another run.

The verified database/Windows fixture work does not establish CoH gameplay,
Android presentation, hardware acceleration, physical controls or audible audio.
