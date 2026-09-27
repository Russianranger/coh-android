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
after prefix shutdown. It must preserve unrelated processes and prove that all
owned output captures close. The diagnostic does not turn an open capture into
a successful cleanup result merely by closing its reader.

The disabled menu-helper entry is also corrected to `winemenubuilder.exe`.
Wine's pinned load-order implementation strips `.dll`, but not `.exe`, from
module names; the old unsuffixed entry did not suppress the executable, and the
Thor trace shows it launched. The report does not prove that helper was the
remaining pipe writer.

Hosted qualification must exercise detached helpers retaining stdout as well
as the full cold and repeat database/client diagnostics before delivery.

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
