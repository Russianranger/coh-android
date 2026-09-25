# Matching reference runtime

Updated: 2026-09-25. The exact-pin Windows client/server package now builds in
this repository. It is a reference for the Android work, not an Android app or
a gameplay-validated server.

## Build and downloads

[Run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
This is the current package, including the PostgreSQL first-start foreign-key
removal guard and the pending-write drain before network save acknowledgements.
It supersedes run 36074139984; that run and its
[build receipt](reference-runtime-build.json) remain historical evidence.
The separate normal-schema and network acknowledgement runs described below
now validate their tested database paths using this package.
Download `reference-win32-runtime` and, for debugging, `reference-win32-symbols`
from that run. Actions artifacts are retained for 30 days; the workflow can
rebuild them. The runtime artifact contains an inner `coh-reference-win32.zip`,
hashes, PE dependency checks and a build receipt. Extract that inner ZIP into
its own directory before staging.

| Item | Value |
| --- | --- |
| Original source pin | `0b75ade0c801735e10c5798f641948a45cc50488` |
| Companion text pin | `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |
| Configuration | OptDebug / Win32 / MSVC hosted Windows |
| PostgreSQL persistence fixture | OFF in this runtime package |
| PostgreSQL patch SHA-256 | `03898e46aa0d8aa34b97234a296307e075c8859f438567450cfb4024f5a282ad` |
| Runtime artifact | `10843979104` / 14,556,607 bytes |
| Runtime artifact SHA-256 | `b5453b47a2cc4d4059f9f48a7bf4622272a447ea648040e587e5796c71a2c853` |
| Inner runtime ZIP SHA-256 | `dd551750de26765297a45310bba51817b36a942d23f97d4da7f0d1365f49d3aa` |

The package includes DbServer, MapServer, CityOfHeroes, TestClient, pig and
Launcher executables, supplied PhysX/Cg DLLs, CrashRpt and app-local x86 MSVC
runtime DLLs. All packaged executable/DLL files passed PE32/x86 and import
closure checks. The recovered package also passed local receipt, file-hash, PE
metadata and dependency checks against the current source patch. See
[the complete build receipt](reference-runtime-evidence/build-36088012664.json)
and [artifact verification record](reference-runtime-evidence/artifact-36088012664.json).
The pinned psqlODBC x86 driver is identified there but is not installed or
bundled; PostgreSQL setup remains separate.

## Reproducible assembly

`prepare_runtime.py` verifies both complete immutable imports before copying.
It accepts repeated binary-asset donors, rejects conflicting case-insensitive
paths and incomplete inspections, excludes donor text/generated caches, and
requires matching source/patch/overlay receipts for the runtime binaries. Only
explicitly reconstructed LF/CRLF variants of overlay C files are accepted;
source and patched-file hashes remain exact. It never patches the imported
snapshots. Use a new output directory:

```sh
python3 tools/prepare_runtime.py \
  --output out/reference-runtime-v2 \
  --asset-data out/recovered-base-assets \
  --asset-data /path/to/base-stage1-candidate-assets \
  --binaries out/reference-binaries-v2
```

The asset directories above are outputs of the existing PIGG inspector, not raw
archive folders. The selected base donors are fonts/player/geom/geomBC and
stage1a/stage1b/stage1f. Custom `i26` data and precompiled Parse7 caches are not
part of this assembly. Their original supplied archives remain the inputs for
reproducing extraction.

The earlier assembly using the run 36074139984 binaries completed with
**173,011 data files / 2,977,730,517 bytes**:
156,290 text/configuration files and 16,721 selected binary assets, with no
conflicting paths or duplicate donor files. The binary assets comprise 5,878
animations, 1,861 geometry files, 8,936 textures and 46 fonts. Three source DB
configuration files account for the increase over the 173,008-file preflight.
See [the assembly record](runtime-assembly-assessment.json). The stock staged
SQL settings still require the separately generated private PostgreSQL
configuration before DbServer can run; staging does not create credentials,
install a driver or start a database. That assembly record is historical:
workspace maintenance removed the original staged runtime. The current recovery
has now fully verified both immutable imports and successfully staged the run
36088012664 package with the restored, verified 16,721 binary assets. The current
[assembly record](reference-runtime-evidence/assembly-775.json) confirms 173,011
data files / 2,977,730,517 bytes and 29 verified build-package files. Ordinary
asset-backed generation has not yet executed. See
[the next validation steps](NEXT_SERVER_VALIDATION.md) for the prepared asset
bundle and hosted comparison workflow.

## Reference generation

On Windows with a staged runtime, the bounded harness can run:

```sh
python tools/generate_runtime_data.py \
  --runtime out/reference-runtime-v2 \
  --output out/reference-generation \
  --phase templates
```

`--phase server-bins`, `--phase client-bins` and `--phase all` are also available.
Under a compatible Linux environment a command prefix can be supplied using
`--runner-json '["wine"]'`; client binning additionally needs working graphics.
These commands are supported paths, not evidence that these runtime phases have
completed here.

The harness checks executable hashes, fresh outputs and process diagnostics.
Templates require all 23 templates, six attribute files and 22 HTML schemas.
Cache phases require completion markers and valid Parse6 outer envelopes;
server binning also requires newly written geometry/map bins. Stale files or a
zero exit without outputs cannot pass. The engine can queue nonfatal errors
before its ordinary early exits, so output checks do not establish complete
definition semantics or gameplay compatibility.

The local execution environment permits Wine version inspection but rejects
the wineserver socket with `Operation not permitted`; it also cannot execute
ELF32 programs. No game-generation process completed locally. Hosted Windows is
the supported execution route for the next checks, without requiring the user
to own a Windows PC.

## Separate data-only schema experiment

The schema workflow builds a separately identified MapServer using the normal
PostgreSQL patch plus `patches/schema-generation`. `-dbtemplatesonly` retains
the normal definition loaders and `containerWriteTemplates`, defers skeletal
track attachment, skips trick texture-animation binding, and omits Mission
Architect animation-selection metadata generation. Those binary-animation
operations do not supply database serializer definitions according to source
review. Ordinary `-templates` behavior is preserved.

The separate mode prints queued definition errors and fails if any are present.
The wrapper requires the exact source/patch receipt, the captured executable
hash, its completion marker and all freshly written schema outputs. Successful
output archives contain templates, HTML schemas and newly written dbidmaps;
incidental parser caches are excluded because this mode deliberately lacks
gameplay assets. Equality with an asset-complete reference `-templates` run
must still be tested. Never substitute this executable for the reference runtime.

The [first engine attempt](schema-generation-evidence/attempt-36070840517.json)
wrote all 51 required template/attribute/schema files and exited with zero queued
definition errors. Its strict log gate rejected six messages about absent old
attribute-ID files. Source review confirmed that the first generation reads these
optional prior mappings and subsequently writes new ones. A fresh initialization
therefore needs a bounded bootstrap followed by a clean ordinary second pass.
Only exact known missing-map reads can permit that second pass, and only when
the maps were absent before and freshly written afterward. Attribute bytes must
remain identical between passes; other failures continue to block acceptance.

The current [two-pass hosted run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the reference package above. Initialization
took 31.468 seconds; the strict reload took 5.750 seconds, with zero queued errors,
no failure diagnostics and identical bytes for all six attribute maps. The accepted
archive holds all 51 required files plus five newly written dbidmaps; incidental
parser caches are excluded.

The current artifact is preserved as
[accepted-36088012666.zip](schema-generation-evidence/accepted-36088012666.zip),
with its [hashes and verification summary](schema-generation-evidence/accepted-36088012666.json).
Its outer artifact SHA-256 is
`62da453ef5673238e11b4b418692117ea7692597a079119b3aaf72504a2502ae`;
the inner schema-output ZIP SHA-256 is
`a7bb94cd936198850f1a35ac58df925b3638caae29c02f47dca1cb3e21dbc132`.
The earlier [accepted run 36074139889](schema-generation-evidence/accepted-36074139889.json)
and [run 36072787971](schema-generation-evidence/accepted-36072787971.json)
remain historical evidence. All 56 current generated payloads are byte-identical
to run 36074139889; the ZIP hash differs because archive metadata changed.
The current build receipt includes the network acknowledgement source changes.
Extract the current `accepted-36088012666.zip` into a new directory. Its
`schema-evidence/` directory contains
`schema-generation-report.json` and the inner `schema-outputs.zip`; the sibling
bootstrap directory retains first-pass diagnostics. Keep these exact ID mappings
with any database initialized from them. This does not establish compatibility
with an existing shard database or the custom client.

Local verification checked the current reference package, schema source receipt
and every archived payload. The source-derived templates define 99 SQL tables,
5,935 columns and 58,272 attribute rows (56,411 general, 1,771 badge-stat and
90 pop-help IDs). The current normal DbServer run confirmed those counts;
separate network validation also passed with the same build, as described below.

## Normal DbServer database validation

Source inspection identified a bounded normal-DbServer path that can exercise
generated game schemas without starting a map or graphical client:

```text
DbServer.exe -exportdump C:\fresh-test-output\empty.dump
```

It invokes `dbInit(-1)`, performs template/attribute/table initialization, exports
the database and shuts down. The driver and its acceptance tests are
implemented in `database/postgresql/tests/run_generated_schema.py`. The accepted
artifact has passed local input checks. The first hosted database run stopped
with SQLSTATE 42P01 while removing foreign keys before their tables existed.
The PostgreSQL removal statement now guards both absent tables and absent
constraints, with ODBC and real DbServer FIFO regressions. The current runtime
and schema builds above both include that provider correction and have passed.
The current [normal database run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
passed at harness commit `a0ae66d72648d33a7f70b3116d1e1800d9164184` using reference/schema pair
36088012664/36088012666, both built from `775a0dd770adac045484805dbbb5f68054c7a354`.
Initial startup and export took 13.219 seconds; the second took 5.718 seconds.
Both exited zero and wrote fresh empty dumps. Actual catalogs contain 99 tables,
5,935 columns, 119 indexes and 734 constraints, with all 58,272 expected attribute
rows. The two catalogs and attribute mappings are byte-identical. See the
[current evidence summary](postgresql-evidence/generated-schema-36125829298.json)
and [complete redacted evidence](postgresql-evidence/generated-schema-36125829298.zip).

The earlier [run 36075137920](https://github.com/Russianranger/coh-android/actions/runs/36075137920)
used reference/schema pair 36074139984/36074139889 and remains
[historical evidence](postgresql-evidence/generated-schema-36075137920.json).
The first current-build checks were rejected when the log classifier treated
expected PostgreSQL catalog notices as failures. The corrected classifier accepts
only the observed catalog-maintenance notices, retains them in the report and
continues to reject SQL failures. The current run above passed with that correction.
The companion workflow runs only after successful schema generation on this
repository's main branch, or an explicit manual run selecting an artifact.
Use only a fresh disposable PostgreSQL cluster initialized and migrated with
`pg_local.py`, the fixture-OFF reference DbServer and the x86 Windows ODBC driver.
Replace staged SQL provider/name/login settings with the generated private
PostgreSQL configuration and remove the MSSQL `SqlInit` statement. Keep fake auth
enabled and the queue server disabled for this local diagnostic route.

Text-only staging retains the source DB/load-balance configs, `maps.db` and account
loyalty/product definitions read by this path. `weeklyTF.cfg` and `Doors.db` are
absent from the current pins; source callers tolerate missing content with
diagnostics, which must be recorded rather than concealed. No imported saves,
character dumps or backups are needed for a fresh database.

The driver requires a fresh empty dump, successful exit, the expected SQL table
and column names/order, matching attribute identifiers, preserved compatibility
migration metadata and no captured SQL failures. It repeats against the same
disposable database and compares the column/index/constraint catalog and
attribute mappings for stability. It does not independently model every field
type or constraint's semantics. The existing persistence test
driver uses controlled fixtures and cannot substitute for this normal startup
check. The long-running `DbServer Ready.` marker is not emitted by `-exportdump`.


Expected PostgreSQL notices are retained in the legacy SQL diagnostics: absent
tables/constraints during optional cleanup and already-existing indexes on reload.
These are success-with-info messages, not failed SQL execution. Other captured
warnings concern console setup, omitted auxiliary service launchers and initial
parser cache misses followed by text fallback.

## Normal network save acknowledgements

[Run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
passed using the same reference/schema pair. Ordinary DbServer and MapServer
`-dbquery` processes exercised the network protocol for SQL-backed generic
containers. The test created two records, updated a record after DbServer
restart, withheld the two-container acknowledgement while a real SQL row lock
blocked the second save, and checked both committed values immediately after
the reply. A deferred commit failure produced SQLSTATE `42501`, DbServer exit 3,
no acknowledgement and an unchanged prior row. See the
[network evidence summary](postgresql-evidence/network-ack-36125829311.json),
[complete redacted evidence](postgresql-evidence/network-ack-36125829311.zip) and
[persistence design](POSTGRESQL_PERSISTENCE.md).

This diagnostic does not load a map or graphical client and requires no binary
asset archives. It validates the generic container acknowledgement path; each
save still has its own transaction, so a multi-container request is not atomic.
The next gates are comparison with ordinary asset-backed `MapServer -templates`,
normal MapServer map startup and real character creation/save/logout/reload.
These results do not establish playable character sessions, map transfers,
auxiliary services, compatibility with the custom client or Android execution.
