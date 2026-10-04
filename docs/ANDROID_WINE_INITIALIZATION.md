# Thor cold Wine initialization retry (0.1.3)

Historical 0.1.3 qualification. The subsequent Thor run passed all eleven
functional database/Windows stages and exposed a final output-capture cleanup
failure. See the [0.1.4 cleanup retry](ANDROID_WINE_CLEANUP.md) for the current
build and device steps.

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

[Run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs at source `49c1626c10636e46a38493047f34ab61a9a5d5ca`,
finishing 2026-09-27 at 22:16:35 UTC. All 109 tooling tests passed without skips.
Both modes passed fresh and repeat execution: eleven database stages or twelve
client stages on each run, including every cleanup check. The
[same-source PostgreSQL regression](https://github.com/Russianranger/coh-android/actions/runs/36354266044)
also passed.

| Hosted initialization | Database mode | Client mode |
| --- | --- | --- |
| Cold duration | 39.911 seconds | 40.305 seconds |
| Cold registration | One pass: two host and one WoW64 registration processes | One pass: two host and one WoW64 registration processes |
| Repeat duration | 4.629 seconds | 4.629 seconds |
| Repeat registration | None; same prefix and database reused | None; same prefix and database reused |

These are hosted timings, not a Thor speed guarantee. The client fixture used
llvmpipe software rendering and passed the four exact pixel checks and synthetic
input on both runs. Physical Thor success remains pending.

The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds all four raw reports, archive hashes, and the verified APK and its twelve
embedded payloads. Download the **coh-diagnostic-apk**
[artifact](https://github.com/Russianranger/coh-android/actions/runs/36354263676/artifacts/10942919938)
and extract `COH-Diagnostic-0.1.3.apk`.

| Identity | Accepted value |
| --- | --- |
| APK size | 13,477,490 bytes |
| APK SHA-256 | `208b2251421a515b2416834d7c6ec1a0d322fa5fdd7903e5e8547df18f7fd879` |
| Runtime manifest SHA-256 | `4348030259b192a5711395704949c153e2f1e0fc0f337e70a05b55ad33300aa1` |
| Signing certificate SHA-256 | `54d55d36bc729460a5f09a6344642806d0c8c1cf4c46c1c2383bc41addd5ed1a` |
| Package / version | `io.github.russianranger.cohdiagnostic` / `0.1.3` (4) |
| Android / ABI | Minimum API 26, target API 35 / `arm64-v8a` |

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
