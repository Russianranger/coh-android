# Validation record

Date: 2026-09-23. This record covers source preservation and assessment accuracy.

| Check | Result |
| --- | --- |
| Source snapshot byte count | 173,081,714 bytes across 5,995 tracked regular files |
| Per-file integrity | SHA-256, Git blob SHA-1, size and executable-bit checks passed for all files |
| Extra/missing imported files | None |
| Staged Git subtree | `f634e21e230009fa8edc91d15429cd4da69eee8c`, identical to the acquired upstream commit's root tree |
| Submodules/symlinks | None in the acquired snapshot |
| Source exclusions | None from the acquired tracked tree |
| Largest file | `3rdparty/cg/bin.x64/cg.dll`, 8,421,480 bytes |
| Documentation | Local links and referenced source paths checked; main constraints confirmed in imported code |
| Executable/game changes | None; imported source is byte-identical |

The verifier uses only Python's standard library:

```sh
python3 tools/verify_source.py
```

An independent Git check, after files are staged, is:

```sh
git write-tree
# Use the returned tree as TREE in the following command:
git rev-parse TREE:upstream/ouroboros
```

The result must equal the original tree in `upstream-lock.json`.

## Not performed at the initial import assessment

- No Windows/MSVC build performed by us. The exact-commit upstream build was later verified; see the 2026-09-24 addendum below.
- PostgreSQL was initially untested. Live PostgreSQL integration has since been added; see the database addendum below. No SQL Server data migration has been performed.
- No binary game-asset download, template/bin generation or source/data compatibility test. Companion text data was subsequently imported; see the addendum.
- No Wine/FEX, PhysX, graphics or gameplay execution.
- No Android APK build, emulator/device run, performance or thermal benchmark.

The source's CMake restrictions were read directly; they were not reported as a
failed build experiment. The original PostgreSQL defect was identified through source inspection.
It has since been patched and tested against running databases; see the database
addendum below.

The imported upstream workflows remain nested in the snapshot and are not enabled
as workflows in this destination. Successful source checks must not be represented
as a passing Android build.

## 2026-09-24 completeness addendum

Reran the source verifier successfully: all 5,995 files and 173,081,714 bytes
still match. Inspected successful upstream Windows run
[35934567567](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
for the exact source commit. Its server/client builds and nine utility, archive,
development-mode and codec tests passed. This was an upstream run, not a build
performed in this repository. Downloaded the v2i3 runtime ZIP, verified its
published SHA-256, and inspected its file list/build metadata without execution;
it uses a different source commit. See the
[completeness audit](LOCAL_SERVER_CLIENT_COMPLETENESS.md) for missing runtime
content/database setup and concrete companion-script gaps. No gameplay or Android
execution was performed.

## 2026-09-24 companion content import

[Import run 35940141238](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 156,297 companion files (1,992,097,492 bytes) passed
SHA-256/Git-blob/mode checks and the staged subtree matched
`4a9a4e893787b6367e916530235d8818dc32ea8f`. No exclusions or submodules. The original
source verifier also passed. Reproduce with:

```sh
python3 tools/verify_source.py
python3 tools/verify_source.py --lock content-lock.json
```

The hosted asset probe received HTTP 403 for all 72 catalogued HEAD requests;
local sample GET access also failed. A full text-only runtime staging run passed;
six adapted launchers and source-pinned configuration files were checked. Receipt
checks caught modified and missing files. These do not constitute archive
extraction, SQL startup, template/bin generation, gameplay or Android tests.
See [content acquisition](CONTENT_ACQUISITION.md).


## 2026-09-24 PostgreSQL development addendum

Implementation commit: `b3c87609dca03a13c47af3c042fcac4c2241b9ca`.
[Hosted validation run](https://github.com/Russianranger/coh-android/actions/runs/35948251357).
The original source and content imports remain unchanged. Verification was
corrected to use POSIX manifest paths on Windows; all source bytes still match.
The build stager copies the verified pin, applies the patch outside the imported
snapshot and records source/patch/overlay/patched-file hashes.

| Database / driver | Platform | Result |
| --- | --- | --- |
| PostgreSQL 16.15 / psqlODBC 16.00.0000 | Linux x86_64 | Passed |
| PostgreSQL 18.6 / psqlODBC 18.00.0004 | Linux x86_64 | Passed |
| PostgreSQL 17.11 / psqlODBC 18.00.0004 | Windows, x86 client / x64 server | Passed |
| Patched DbServer, OptDebug Win32 | MSVC hosted runner | Passed; x86 executable artifact verified |

The development build artifact contains `DbServer.exe` (1,651,712 bytes),
`CrashRpt.dll` and the build-input receipt. ZIP SHA-256 and executable PE machine
type were checked; it is Windows x86. See the [build receipt and file hashes](postgresql-evidence/win32-build.json).
It is a DbServer development build, not a complete server/client distribution.

The integration tests use actual PostgreSQL processes and the non-superuser game
role, with the same dialect header consumed by the patched DbServer. All three configurations pass:
65 simultaneous connections; deterministic per-table indexes and legacy cleanup;
foreign-key enforcement; SQLColumns metadata; integer/byte/float/timestamp and
UTF-16 values; chunked 32 KiB binary reads; large text and NULL; column alteration;
out-of-order ID reservations; rollback; deleted-highest-ID behavior; six parallel
writers; reconnect; clean restart; forced WAL recovery; logical backup/restore;
and refusal to overwrite a restored database. Credentials remain outside the
repository and uploaded artifacts. Migration metadata uses `coh_meta`, because
DbServer prunes unreferenced tables from `dbo`.

Windows cluster setup grants the invoking user an explicit private ACL, because
PostgreSQL drops administrator group privileges. File-backed subprocess output
avoids inherited daemon pipes hanging the launcher; this lifecycle path now
passes the same restart/recovery/restore checks as Linux.

The newer ODBC driver exposed a signed-byte error at value 255. The provider now
uses SQL_C_UTINYINT explicitly. PostgreSQL versions are tested independently;
this is not a claim that the entire game supports every version of either driver.

Raw redacted reports: [PostgreSQL 16](postgresql-evidence/postgresql-16-linux.json),
[PostgreSQL 18](postgresql-evidence/postgresql-18-linux.json), and
[Windows x86 ODBC / PostgreSQL 17](postgresql-evidence/postgresql-17-win32.json).

At that milestone, full DbServer boot with generated templates, the actual
container FIFO/retry pipeline, character gameplay/save/load, SQL Server data
migration, auxiliary services and Android execution remained unproven. The next
addendum records subsequent tests of the actual persistence pipeline.
The [database README](../database/postgresql/README.md) contains commands and
remaining gates. Archive indexing is deferred to the next session.

## 2026-09-24 actual DbServer persistence and compatibility

Tested implementation: `0827ccc992daa7530d9f98d742122238197847df`.
[Hosted validation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993).
This extends the earlier ODBC-only milestone with execution inside the actual
patched Win32 DbServer. The source snapshot is still verified before staging;
patches and overlays remain outside the immutable imports.

| Test | Environment | Result |
| --- | --- | --- |
| Extended ODBC and schema suite | PostgreSQL 16.15 / psqlODBC 16.00.0000, Linux x86_64 | Passed |
| Extended ODBC and schema suite | PostgreSQL 18.6 / psqlODBC 18.00.0004, Linux x86_64 | Passed |
| Extended ODBC and schema suite | PostgreSQL 17.11 / psqlODBC 18.00.0004, Windows x86 client | Passed |
| Real container/FIFO/template pipeline | Actual OptDebug Win32 DbServer / PostgreSQL 17.11 | Passed: 20 check groups / 14 process invocations |

The opt-in `-pgpersistencetest` entry links the original container parser/merger,
SQL generator, 64-worker queue, reader and template updater. Controlled templates
and records replace asset-generated game data. It does not mock those persistence
components or call the player-session completion callback.

The fixtures cover 512 child rows crossing statement-batch boundaries; sixteen
independent records; repeated same-record saves; queued read callbacks; an
8,202-byte UTF-8 value including accented text and an emoji; byte 255; and
case-insensitive ASCII name lookup through both SQL and the game cache.

Real PostgreSQL triggers inject serialization/deadlock failures late in saves,
and a deferred trigger fails during commit. Tests check complete-command replay,
rollback of all batches on permanent failure, the five-attempt limit, and no
successful completion of rejected commands. A rejected parent deletion restores
previously deleted children. A terminated database connection must stop the
process without replaying or acknowledging its in-flight write.

Lifecycle checks reopen saved records through the actual container reader after
a new process, clean PostgreSQL restart, forced WAL recovery and backup/restore.
The real template updater changes column order and adds a field while retaining
data, the reserved high-water value 9000, indexes and inbound foreign keys.
Failed type conversion and view-dependent replacement preserve the original
table identity. Migration 2 is idempotent; the upgrade helper refuses a newer
schema version. Schema functions are also tested independently on all three
database/ODBC configurations above.

Redacted reports: [actual DbServer](postgresql-evidence/persistence-v2/dbserver-persistence.json),
[PostgreSQL 16](postgresql-evidence/persistence-v2/postgresql-16-linux.json),
[PostgreSQL 18](postgresql-evidence/persistence-v2/postgresql-18-linux.json), and
[Windows ODBC](postgresql-evidence/persistence-v2/postgresql-17-win32.json).
All five downloaded artifact ZIP digests were checked. The Win32 PE machine type
is x86, and the downloadable executable's SHA-256 equals the hash recorded by
the actual persistence test. Patch and all 14 patched-source hashes match local
verified staging. The new diagnostic overlay has CRLF in the Windows checkout;
the [build receipt](postgresql-evidence/persistence-v2/win32-build.json) records
that exact conversion and both hashes. See [artifact provenance](postgresql-evidence/persistence-v2/artifact-provenance.json)
for per-file hashes. The diagnostic entry is enabled in that development artifact
and disabled in ordinary builds unless `COH_PG_PERSISTENCE_TESTS=ON` is requested.

These results do not establish character gameplay, network acknowledgement
delivery, MapServer transfers, production account/auction services, SQL Server
save migration, or Android/Wine execution. Trigger-raised retryable errors test
the real error path, not contention performance. Name equality is explicit ASCII
folding; full Unicode collation and game-level uniqueness remain separate gates.
See [persistence behavior and upgrade instructions](POSTGRESQL_PERSISTENCE.md).
