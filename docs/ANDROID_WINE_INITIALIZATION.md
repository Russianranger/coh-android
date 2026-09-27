# Thor cold Wine initialization retry (0.1.3)

The [0.1.2 Thor report](android-evidence/thor-initializer-timeout-20260927.json)
establishes that the initializer was still running at 150.040 seconds, before
any cleanup signal. The inherited-output correction did not resolve that device
failure. Four early native database stages passed; Windows ODBC and graphics were
not reached. PostgreSQL and Wine prefix shutdown passed, but an output capture
remained open, so complete cleanup was not proved.

## Startup correction

The pinned Wine 10 [loader](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/env.c)
automatically starts `wineboot --init` and allows up to five minutes for its boot
event. The old diagnostic started `wineboot -u`, whose
[forced update](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/programs/wineboot/wineboot.c)
can repeat prefix registration after automatic initialization. Wine also writes
its update timestamp before that registration completes. An interrupted prefix
therefore cannot be considered ready merely because that timestamp exists.

The same runtime's LSB Thor evidence measured 181.401 seconds between the first
and second initialization starts, longer than CoH's entire 150-second budget.
This supports correcting both the duplicate update and the startup allowance;
it does not identify the exact internal component delayed in this CoH report.

Version 0.1.3 initializes an unready owned prefix with `wineboot -i`, after
removing only its update timestamp. It allows up to ten minutes for initialization,
shows elapsed progress every five seconds, and retains the fifteen-minute total
diagnostic limit and Stop handling. Wine's internal bootstrap timeout is an
error even if its process exits zero. Initialization traces record the registration
passes for review.

A private readiness marker is written only after the actual PE32 DLL fixture
passes and is tied to the pinned runtime inputs. A successful repeat run retains
the timestamp and avoids forcing another registration pass. Failed or interrupted
initialization receives a fresh registration attempt. All later Windows ODBC,
restart, client-fixture and cleanup checks remain required; open output captures
continue to prevent a cleanup pass.

## Validation and device retry

Hosted qualification must pass fresh and repeat runs in both database and client
modes before the APK is accepted. Physical Thor success remains pending.

1. Install `COH-Diagnostic-0.1.3.apk`. These test builds use different signing
   keys, so export any reports and uninstall only **COH Diagnostic** before
   installing. This separate app contains no game saves.
2. Choose **Setup runtime**, then **Run diagnostics**. Cold Windows setup may
   take several minutes; elapsed progress should keep updating. Export the report
   whether it passes or fails. If it fails, send that one report and stop there.
3. After a pass, run **Run client probe** and export its report. Reopen and repeat
   the diagnostic, then exercise **Stop** during another run and export the result.

Neither hosted checks nor prefix initialization establish game rendering,
hardware acceleration, physical controls, audible playback or CoH gameplay.
