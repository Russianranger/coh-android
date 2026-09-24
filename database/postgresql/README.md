# PostgreSQL development backend

PostgreSQL is the selected database alternative for the Thor port. LocalDB is a
Windows SQL Server component; PostgreSQL can run natively on ARM64 Android.
The first implementation below repairs the existing DbServer provider. It is a
development backend, not yet a validated complete game server.

## Implemented

- Immutable source remains at the original pin. `tools/prepare_pg_source.py`
  verifies every source file, copies to a new directory, applies the patch and
  records input hashes. Never build by editing `upstream`.
- Correct, schema-qualified PostgreSQL index removal; deterministic per-table
  index names; legacy index cleanup; table-scoped foreign-key checks.
- Serialized, monotonic container ID reservations across asynchronous writes.
  Startup reads the sequence high-water mark and existing rows without rewinding.
  Exactly **one DbServer writer per shard** remains required.
- PostgreSQL ODBC metadata normalization for smallint/int, Unicode varchar,
  timestamp, text and bytea, including explicit unsigned byte conversion for
  psqlODBC 18. Windows-specific IDENTITY_INSERT is excluded from
  PostgreSQL table rebuilds. Connection strings are withheld from error logs.
- A private loopback cluster with SCRAM passwords, a non-superuser game role,
  durable writes enabled, generated ODBC/DbServer settings and backup/restore.
  Migration metadata lives outside dbo so DbServer’s table cleanup preserves it.
- A real ODBC integration probe uses the same SQL dialect header as DbServer.
  CI also compiles the patched Win32 DbServer and runs a Win32 probe using a
  hash-pinned 32-bit psqlODBC installer from PostgreSQL’s official server.

## Host / Termux development commands

Requires Python 3, Git and PostgreSQL tools. Run PostgreSQL as a normal user in
private internal storage. Never place its data directory on shared storage or
an SD card. `--bin` must contain initdb, pg_ctl, psql, pg_dump and pg_restore.
These commands need no Windows PC. Termux use is a development route, not the
final application packaging solution; its on-device execution is still untested.

```sh
python3 database/postgresql/pg_local.py init --root "$HOME/coh-pg" --bin /usr/lib/postgresql/16/bin
python3 database/postgresql/pg_local.py status --root "$HOME/coh-pg"
python3 database/postgresql/pg_local.py backup --root "$HOME/coh-pg" --file "$HOME/coh-game.backup"
python3 database/postgresql/pg_local.py stop --root "$HOME/coh-pg"
python3 database/postgresql/pg_local.py start --root "$HOME/coh-pg"
python3 database/postgresql/pg_local.py restore --root "$HOME/coh-pg" --file "$HOME/coh-game.backup" --database coh_restored
```

On Termux, use its PostgreSQL installation’s `--bin "$PREFIX/bin"`. Default port
is 15432; choose `--port` on init if occupied. Init refuses an existing root.
Restore refuses an existing database; it does not replace the active database.
Keep the entire private cluster directory out of Git and public artifacts.
Do not upload its credentials, connection strings, saves or SQL dumps.

For DbServer, replace the existing SqlDbProvider/SqlDbName/SqlLogin/SqlInit lines
in the **staged runtime** servers.cfg with the generated `dbserver-postgresql.cfg`
settings. Retain the other source-pinned server settings. That file contains a
password. The database and migration must exist before DbServer starts.
The Unicode ODBC driver name must match the installed driver: for a 32-bit
Windows DbServer, install the **32-bit Windows psqlODBC** driver inside the same
Windows/Wine environment. An Android/Linux ODBC library cannot be loaded by it.
Do not assume merely selecting PostgreSQL makes other game services compatible.

## Reproduce the validation

```sh
python3 tools/prepare_pg_source.py --output out/pg-source
cmake -S database/postgresql/tests -B out/pg-probe
cmake --build out/pg-probe
python3 database/postgresql/tests/run_integration.py --bin /usr/lib/postgresql/16/bin --probe out/pg-probe/odbc_probe --root /tmp/coh-pg-test --report out/postgresql-integration.json
```

The probe refuses destructive fixture setup unless connected to `coh_test_*`.
It uses the non-superuser game role. Tests cover all 65 stock connections, DDL, ODBC values, sequence
ordering, rollback, six parallel connections, reopen, clean restart, forced WAL
recovery, backup/restore and refusal to overwrite an existing restored database.
CI uploads only the redacted report and built executables/receipt, never cluster
files. PostgreSQL **16.15 with psqlODBC 16.00.0000**, and **18.6 with
psqlODBC 18.00.0004**, pass the full Linux suite. The same suite passes with
**32-bit Windows psqlODBC 18.00.0004 against PostgreSQL 17.11**. The patched
Win32 DbServer also compiles successfully. Download
`postgresql-win32-development-build` from that run’s artifacts for the executable,
CrashRpt.dll and build receipt; the driver probe is in
`postgresql-win32-test-evidence`. These are development artifacts, not a complete
game install. See the
[validation record](../../docs/VALIDATION.md) and
[hosted run](https://github.com/Russianranger/coh-android/actions/runs/35948251357).

## Remaining gates

- Start the actual patched DbServer with generated templates, then create,
  save, reload and transfer a character with MapServer and client. Missing game
  assets still block the full reference path; the database probe is independent.
- Exercise DbServer’s actual asynchronous transaction/retry machinery, schema
  whole-container rollback/retry, ID preservation across table rebuilds,
  case-insensitive name rules and remaining hard-coded SQL
  (for example the auction activity DATEADD/GETDATE filter). Integer ISNULL
  predicates in base lookups and character import have been changed to COALESCE.
- Port or replace SQL Server-specific AccountServer/other auxiliary services;
  the minimal fake-auth diagnostic path does not require a production account
  service. This work does not migrate existing SQL Server databases.
- Validate Win32 ODBC under Wine/translation against ARM64 PostgreSQL on Thor;
  package PostgreSQL under the APK’s own UID and paths, then benchmark memory,
  lifecycle and crash recovery. The stock DbServer opens 65 SQL connections;
  this initial cluster permits 80 and needs on-device pool/memory tuning.

## Sources

- [PostgreSQL sequence semantics](https://www.postgresql.org/docs/18/functions-sequence.html): sequence changes may survive rollback; gaps are expected. A crash may lose an uncommitted reservation.
- [psqlODBC connection options](https://odbc.postgresql.org/docs/config-opt.html).
- [Termux PostgreSQL build recipe](https://github.com/termux/termux-packages/blob/master/packages/postgresql/build.sh): demonstrates Android support, including platform patches; it is not directly relocatable into another APK.
- [SQL Server Express LocalDB](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/sql-server-express-localdb?view=sql-server-ver17).
