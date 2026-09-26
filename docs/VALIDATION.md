# Validation record

Date: 2026-09-23. This record covers source preservation and assessment accuracy.

Latest milestone, recovered 2026-09-26: [ordinary template comparison and Atlas
Park readiness](#2026-09-26-continuation-completed-reference-comparison-and-atlas-park)
passed in the completed 2026-09-25 hosted run. Character persistence awaits
hosted execution of its new harness.
Earlier sections remain historical records; they do not describe the newest
build status.

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


## 2026-09-24 matching runtime assembly

[Reference build 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663)
passed at `7524c9d894bd49bc83d64c3dbfac0f8d24e57eba`. It compiled and packaged
DbServer, MapServer, CityOfHeroes, TestClient, pig and Launcher with PostgreSQL
fixture mode OFF. The package's eight tests, PE32/x86 checks, import closure and
artifact uploads passed. Runtime/symbol artifacts have separate hashes.

The downloaded runtime ZIP digest matched GitHub's artifact digest, the inner
ZIP matched SHA256SUMS, and every packaged payload hash passed the stager.
Source/patch/patched-source receipts match; the two PostgreSQL overlay hashes
match the exact, explicitly reconstructed Windows CRLF versions of the repository
C sources. Unrecognized content changes remain rejected.

Both original snapshots passed full integrity verification again. Assembly of
pinned text/configs, fonts/player/geom/geomBC and stage1a/b/f completed with
173,011 data files / 2,977,730,517 bytes and 29 verified package files.
There are 16,721 binary asset files / 985,644,857 bytes, no conflicting paths and
no duplicate donor paths. Three source-pinned DB configs explain the increase
from the 173,008-file preflight. No imported snapshot or raw asset was published
or modified by staging. Existing imported snapshots remain preserved; raw binary
assets remain outside Git.

Local tool suites passed 53 tests: packaging 8, staging 14, reference-generation
harness 11, schema-source staging 8 and schema-runner 12. Synthetic subprocess
checks establish failure/freshness/receipt behavior, not game execution.
Actual local generation is blocked by the environment's wineserver socket
restriction. The separately patched hosted data-only schema experiment has its
own workflow and receipts; it cannot establish asset-complete runtime or
serializer equivalence by itself. See [runtime instructions](REFERENCE_RUNTIME.md)
and [assembly evidence](runtime-assembly-assessment.json).


## 2026-09-24 compatibility regression refresh

All four jobs in [run 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
passed at `7ee6e8233458cc50a0304e5c6d9023ec8e12ed62`: PostgreSQL 16 and 18
on Linux, x86 Windows ODBC, and the actual DbServer persistence fixture.
The database patch is unchanged. This refresh does not replace the separate
normal DbServer startup/reload check using generated game templates.


## 2026-09-24 generated game schemas

[Run 36072787971](https://github.com/Russianranger/coh-android/actions/runs/36072787971)
passed at `adaadac67581bfe6a7798229bb17428a9b3e5732`. A separately identified
MapServer first initialized the six absent attribute maps, then ran a clean
strict second pass. Both processes exited zero, the second had zero queued errors
and no failure diagnostics, and all six attribute maps were byte-identical.
All 51 required templates/attributes/HTML schemas plus five dbidmaps are archived;
incidental parser caches are excluded. Asset-complete serializer equivalence and
gameplay remain untested.

The downloaded artifact's SHA-256 and every eligible file hash were verified.
The actual archive also passed the normal DbServer driver's acceptance check
against verified text and the fixture-OFF reference package. Expected database:
99 tables, 5,935 columns and 58,272 attribute rows. These are preflight expectations,
not SQL execution results. Exact evidence is preserved in
[the artifact](schema-generation-evidence/accepted-36072787971.zip) and
[its summary](schema-generation-evidence/accepted-36072787971.json).
Local focused tests passed: 18 schema-runner, 12 generation-harness and nine
schema-source tests. The hosted staging/generation check step also passed.


## 2026-09-25 fresh-database startup correction and rebuilds

The first normal DbServer check, [run 36073664472](https://github.com/Russianranger/coh-android/actions/runs/36073664472),
failed with SQLSTATE 42P01: startup removes optional foreign keys before their
tables exist. `DROP CONSTRAINT IF EXISTS` alone does not guard an absent table.
The PostgreSQL statement now also uses `ALTER TABLE IF EXISTS`. The original
failure remains in [its evidence record](postgresql-evidence/generated-schema-attempt-36073664472.json).

[Regression run 36074139842](https://github.com/Russianranger/coh-android/actions/runs/36074139842)
passed all four jobs: Linux PostgreSQL 16/18, Windows x86 ODBC, and the actual
Win32 DbServer persistence fixture. The latter passed 21 check groups across
14 process invocations, including removal through the real FIFO before table
creation and removal of an absent constraint. The ODBC regression also verifies
that an existing foreign key enforces its relationship before removal.
See [the DbServer report](postgresql-evidence/fk-cold-start/dbserver-persistence.json).

The updated [reference package 36074139984](https://github.com/Russianranger/coh-android/actions/runs/36074139984)
and [data-only schema run 36074139889](https://github.com/Russianranger/coh-android/actions/runs/36074139889)
both passed at `0f37414d1b42498e65738c78995e160fceb29ca8`. The normal package keeps
persistence fixture mode OFF. Schema initialization took 32.062 seconds and its
strict second pass took 5.907 seconds. All six attribute maps were stable, the
strict pass had zero queued errors and no failure diagnostics, and all 56
archived payloads are byte-identical to the earlier accepted schema run.
Their new receipts bind them to the corrected PostgreSQL overlay. Downloaded
artifact, inner archive and payload hashes passed verification. The current
[accepted schema artifact](schema-generation-evidence/accepted-36074139889.zip)
and [summary](schema-generation-evidence/accepted-36074139889.json) are preserved.


## 2026-09-25 normal DbServer generated-schema startup and reload

[Run 36075137920](https://github.com/Russianranger/coh-android/actions/runs/36075137920)
passed at workflow commit `21757aa5284851bd23d4e100b8fd96a0d0d7304d`, using the
matching reference and schema builds at `0f37414d1b42498e65738c78995e160fceb29ca8`.
The fixture-OFF DbServer performed its normal `dbInit(-1)` through `-exportdump`
on a fresh migrated PostgreSQL cluster, then repeated against that database.
Initial startup/export took 11.718 seconds; reload/export took 5.578 seconds.
Both exited zero within bounds, with fresh empty dumps and no failure diagnostics.

Independent downloaded-evidence verification confirmed all 99 tables and 5,935
ordered columns against the accepted generated templates. All 58,272 attribute
IDs and names match their generated files. The two snapshots contain 119 indexes
and 734 constraints (99 primary keys and 635 foreign keys); their catalog and
attribute JSON files are byte-identical. Compatibility migration metadata stayed
unchanged. All recorded input and log hashes match. This checks catalog stability
and names/order, not an independent model of every column type or constraint.

The legacy `SQLERROR:` log label also carries success-with-info diagnostics.
Every such entry in this run is an expected PostgreSQL NOTICE for optional
absent-object cleanup or existing indexes. No unexpected SQL execution error was
found. Console setup, omitted auxiliary launchers and initial parser cache misses
with text fallback remain visible in the redacted logs.

The full [redacted evidence archive](postgresql-evidence/generated-schema-36075137920.zip)
and [summary with original report](postgresql-evidence/generated-schema-36075137920.json)
are preserved in Git. This completes the generated-schema database initialization
and reload gate. It does not test character creation/save/reload with those
templates, network acknowledgements, map transfer, auxiliary services, an
asset-complete serializer comparison, the custom client or Android execution.

## 2026-09-25 network acknowledgement and current build validation

The current [reference build 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
and [strict schema run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at `775a0dd770adac045484805dbbb5f68054c7a354`. Their receipts include the
PostgreSQL network ACK correction. All 56 schema payloads remain byte-identical
to the previous accepted schema. The current package and reviewed assets were
assembled again after workspace recovery: 173,011 data files / 2,977,730,517 bytes
and 29 build files; [assembly record](reference-runtime-evidence/assembly-775.json).

[Normal schema run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
passed with the current fixture-OFF reference package. Fresh initialization took
13.219 seconds and reload 5.718 seconds. Both exited zero and produced empty
dumps, identical 99-table/5,935-column catalogs, 119 indexes, 734 constraints and
58,272 matching attribute rows. [Summary](postgresql-evidence/generated-schema-36125829298.json)
and [full redacted evidence](postgresql-evidence/generated-schema-36125829298.zip)
are retained.

[Network run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
passed at workflow commit `a0ae66d72648d33a7f70b3116d1e1800d9164184` using the
same accepted schema/reference pair. Normal MapServer `-dbquery` created two
MiningAccumulator containers and modified one after a DbServer restart. Actual
received ACK packet fields matched the request, and independent SQL reads
confirmed committed values. A two-container batch was blocked by a real SQL
row lock for 2.078 seconds without any received ACK. After release, one two-ID
ACK batch arrived and both updated values were visible. A deferred constraint
trigger failed COMMIT with SQLSTATE `42501`: the client received zero ACKs,
DbServer exited 3, the expected fatal-worker diagnostic appeared, and the prior
committed row remained unchanged. The report has no failures.
[Summary/report](postgresql-evidence/network-ack-36125829311.json) and
[full redacted evidence](postgresql-evidence/network-ack-36125829311.zip) are retained.

The first current-package attempts stopped on benign PostgreSQL NOTICE messages
carried under the legacy `SQLERROR:` label. The drivers now recognize only the
specific observed missing-object/existing-index notices and retain them in the
reports; real errors and unknown notices still fail. All 44 driver tests passed.
At this earlier checkpoint, the asset packaging/comparison/map-tooling workflow
passed 57 tests, but its actual template-comparison job was skipped because the
reviewed ZIP had not reached the hosted runner. The asset ZIP was restored from saved parts and its
615,541,018 bytes and SHA-256 verified before re-extraction.

This establishes normal generic-container network ACK ordering, including
failure behavior. It does not establish batch atomicity, throughput under load,
character session persistence, asset-complete templates, Atlas Park gameplay,
the customized client, or Android execution. Atlas Park readiness was then
unexecuted; the subsequent completed gates are recorded below.

## 2026-09-26 continuation: completed reference comparison and Atlas Park

Continuation recovered [run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895),
which had completed successfully on **2026-09-25 at 19:16:38 UTC**. The prior
handoff at commit `04d62616e2e1b41b10f35a04d4c798e43680d5ba` still described
comparison as in progress and Atlas Park as pending. There were no queued or
running GitHub workflows at recovery. These observations establish repository
activity only; the other Codex session's internal state is not available.

The run used workflow commit `fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687`, the
reference package from run `36088012664`, schemas from run `36088012666` and
reviewed release asset `588984151`. Both reference and schema packages share
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.

The earlier manual attempts remain historical: run `36174562963` stopped at
download; run `36175960917` verified the exact asset ZIP but failed canonical
manifest checking after Windows line-ending conversion. Commit `fe98dd5` fixed
checkout byte preservation; the accepted run then passed extraction of all
16,721 reviewed binary assets and full runtime staging.

Ordinary `MapServer -templates` freshly rewrote **56/56** required outputs in
**25.89 seconds**; every payload matched the accepted data-only output bytes,
with no differences, timeout or reported failure. Preserve the
[comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json)
and [complete recovered artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip).

A separate fresh runtime started normal DbServer and Atlas Park against
disposable PostgreSQL, reusing only the verified generated outputs and accepted
identifier mappings. Comparison caches were not carried forward. Independent
DbServer status queries observed the initial not-started state followed by
registered ready status and continuing updates for **62.235 seconds**, exceeding
the requested 60 seconds. The map report contains no failures. Preserve the
[map report](postgresql-evidence/one-map-36176806895.json),
[complete recovered artifact](postgresql-evidence/postgresql-one-map-36176806895.zip)
and [shared identities/archive hashes](reference-runtime-evidence/accepted-gates-36176806895.json).

This establishes equality of the 56 generated files for the reviewed inputs
and a bounded Atlas Park readiness observation. Normal executables do not
report their queued startup error count; complete asset coverage, complete
serializer semantics, character sessions and gameplay remain unvalidated.
The next gate is the new character persistence harness, awaiting hosted
execution. No character persistence or Android pass is claimed.
