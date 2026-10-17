# Independent SQL readiness failure and transport experiment

Run `38993564320` admitted the exact corrected Win32 AuthServer and both existing
native probes, then refused the mandatory independent x86 ODBC precondition.
**No AuthServer or account probe started.** Artifact `12086206965` is preserved
with its complete hashes under `../evidence/sql-readiness-preauth-38993564320/`.
Its 8,066-byte ZIP SHA256 is
`1781e58ffdb870428f0b97284c73f7b2d97312300a8f9528f4e3404c9e93d35d`.

The actual observation opened zero of one attempted x86 connections and reported
SQLSTATE `08S01`/native 233 twice, then `08001`/native 0. The owned SQL process
6804 retained its original start identity before and after cleanup. AuthServer,
firewall, private-file and source cleanup flags passed; schema DROP failed,
although LocalDB stop/delete succeeded. Aggregate SQL cleanup remains false.
This result does not test the corrected receive path or encrypted login.

## Source comparison and limits

Accepted SQL/ODBC run `38948147656` used the same pinned original source,
ODBC17 x86 driver, LocalDB `17.0.4025.3`, 256-MiB SQL memory configuration and
connection keywords: `Database=cohauth;Trusted_Connection=Yes;Encrypt=No` with a
single-backslash `(localdb)` instance name. Current generated profile and x86
observer have the same endpoint spelling. No escaping mismatch was found.

The accepted native fixture and original AuthServer call `SQLDriverConnectA`;
the new observer uses managed `System.Data.Odbc.OdbcConnection`. The failed DROP
also came from sqlcmd/ODBC17, so a managed-only explanation is not established.
Neither PID presence nor the error numbers prove a working SQL listener. The
256-MiB setting was already used in accepted SQL tests, so it is a hypothesis to
measure, not an established cause. No authentication or encryption guard should
be disabled to get past this prerequisite.

Microsoft documents the actual LocalDB named pipe returned by instance info and
the ability to connect using that pipe:
https://learn.microsoft.com/sql/database-engine/configure-windows/sql-server-express-localdb
Microsoft also distinguishes the buffer/cache memory limit from total process
usage and describes memory-limit tuning:
https://learn.microsoft.com/sql/database-engine/configure-windows/server-memory-server-configuration-options
These sources motivate the diagnostic comparisons; they do not establish this
run's failure cause.

## Implemented readiness-only experiment

`sql_readiness_diagnostic.py` creates one fresh uniquely owned LocalDB instance;
it never starts AuthServer, DbServer, MapServer or an account login probe. It
retains the exact current ODBC17 x86 driver and LocalDB version admission. It
runs the same three-connection/read-only process-ID observer in x86 and x64
PowerShell against both the named instance and its exact owned local named pipe.
Only pointer size, endpoint and database vary; driver/security/query policies
are unchanged. Direct-pipe queries must return the expected owned SQL PID.

The four phases are default memory/master, configured memory/master, original
schema/cohauth, and original public fixture seed/cohauth. Each phase records SQL
PID/start identity, working set/private bytes/CPU ticks/thread count before and
after the observations. Only the owned error.log is read; a bounded parser emits
error number/severity/state tuples and fixed ready/termination/memory flags.
Raw SQL logs, instance-info/user strings, credentials and exception text are
never exported. Endpoint values are hashed; only fixed transport names escape.

Each observer has a 50-second child bound. The worst-case 16-observation experiment
can take about 14 minutes plus bounded setup/cleanup, so allow a 25-minute job.
A run with 256 MiB reproduces the prior memory policy. Only if those actual
measurements implicate pressure should a separately labeled 1024-MiB run be used
to change that single experimental variable. Both are disposable host SQL
settings; neither changes native AuthServer transport or account policy.

```powershell
python native-android/engine/auth-interop/deployment/sql_readiness_diagnostic.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-sql-readiness-only" --memory-limit-mb 256
```

Use the same fresh Windows hosted runner and LF checkout contract as the existing
candidate service workflow. No compiled artifact download or OpenSSL build is
required. Upload only `coh-sql-readiness-only/`. The `passed` flag means that the
bounded diagnostic and cleanup completed; `connectivity_qualified` stays false.
Interpret actual per-phase health evidence before proposing a service guard or
profile change. Do not restart AuthServer until its required x86 path is closed.

Nine host suites validate exact owned-pipe restrictions, unchanged security/query
policy across all variants, numeric UTF8/UTF16 log redaction, x86/x64 output
admission and explicit memory/no-service guards. Actual Windows diagnosis remains
pending a coordinator-owned readiness-only workflow. No SQL or auth success is
inferred from local tests.

All SQL/LocalDB console commands now use a redacting runner: stdout/stderr are
discarded, including schema DROP/instance stop/delete cleanup. Fixed version/PID
queries use a monitored private temporary file (8-KiB output bound), emit only
the admitted scalar, and close/delete the raw capture before returning. Failure
and timeout receipts retain numeric return codes and symbolic flags only. The
final source-status inspection is guarded; its failure marks source admission
false and still writes the complete failure receipt.

An overall 20-minute experiment budget caps SQL command and observer timeouts by
remaining time; the 25-minute job reserves its last five minutes for the existing
bounded cleanup and receipt. New children are refused after budget expiry. Host
controls additionally test private console suppression/invalid-output refusal,
DROP failure followed by stop/delete, overall budget refusal and preserved
receipts when final source-status observation raises. No raw SQL console file
is stored in the uploaded output directory.
