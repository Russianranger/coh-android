# Thor wineboot retry (0.1.2)

The two 0.1.1 Thor reports stopped at `wineboot timed out` after 150 seconds,
before Windows ODBC or graphics probes. Native ARM64 PostgreSQL initialization,
authenticated SQL, migration and owned shutdown passed; the second attempt
reused the same cluster. [Selected device evidence](android-evidence/thor-wineboot-failure-20260927.json)
preserves the results without publishing the original support archives.

The old harness waited for both the initializer process to exit and all inherited
output handles to close. A real subprocess regression reproduces an exit-0
initializer whose background service retains stdout: the old harness falsely
times out and forcibly stops the service. The device reports recorded exit status
after forced cleanup, so they do not establish this exact cause on Thor.

Version 0.1.2 allows **wineboot only** to complete on its direct process exit,
with a bounded 200 ms output drain. Its output reader and process group stay owned
until Wine prefix shutdown; output remains bounded. Nonzero exit and the original
150-second limit for a still-running initializer remain enforced. Windows driver
loading, real ODBC operations and optional graphics still have to pass afterwards.
Other commands still require process exit and output EOF.

The report records exit status and open-output state before any forced signal,
plus completion timing. Final cleanup refreshes late output and requires reader
and writer completion as well as exited direct processes. This distinguishes a
retained output handle from a genuinely stuck initializer on the next device run.

Six subprocess regressions cover retained output, strict default EOF handling,
nonzero exit, a genuinely stuck initializer, cancellation and late output overflow.
The local suite passed 99 tests with two environment-dependent skips. Hosted
APK and both runtime modes must pass before this retry is accepted.

## Thor retry

1. Install `COH-Diagnostic-0.1.2.apk`. CI candidates have different signing
   certificates: if an update is refused, export previous reports, uninstall only
   **COH Diagnostic**, then install 0.1.2. This separate app has no game save data.
2. Choose **Setup runtime**, then **Run diagnostics**. Export that report whether
   it passes or fails. If it fails, that single report is the next useful input.
3. After a pass, choose **Run client probe** and export its report. Then repeat
   after reopening and exercise **Stop** during another run.

Full physical-device acceptance remains pending. The 0.1.1 reports establish the
early database stages on Thor, not Windows fixture success, rendering, performance
or gameplay. Prior hosted 0.1.0/0.1.1 acceptance receipts remain unchanged.
