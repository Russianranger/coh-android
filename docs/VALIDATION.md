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

Not yet proven: full DbServer boot with generated templates, the actual container
FIFO/retry pipeline, character gameplay/save/load, SQL Server data migration,
auxiliary service database compatibility, or Android execution/packaging. The
standalone ODBC probe validates the database boundary, not those higher layers.
The [database README](../database/postgresql/README.md) contains commands and
remaining gates. Archive indexing is deferred to the next session.
