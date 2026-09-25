# Matching reference runtime

Updated: 2026-09-25. The exact-pin Windows client/server package now builds in
this repository. It is a reference for the Android work, not an Android app or
a gameplay-validated server.

## Build and downloads

[Run 36074139984](https://github.com/Russianranger/coh-android/actions/runs/36074139984)
passed at repository commit `0f37414d1b42498e65738c78995e160fceb29ca8`.
This is the current package, including the PostgreSQL first-start foreign-key
removal guard; it supersedes the earlier run 36069123663.
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
| Runtime artifact | `10839214575` / 14,555,555 bytes |
| Runtime artifact SHA-256 | `4d0afbef6b2e84b973d5e6081b7453d92448c3d71dbaf05e4680a4e231b83b93` |
| Inner runtime ZIP SHA-256 | `52a771bbd149c4daa1a4f15f786db9e4b070d706692629ae72ed00b2a32513e1` |

The package includes DbServer, MapServer, CityOfHeroes, TestClient, pig and
Launcher executables, supplied PhysX/Cg DLLs, CrashRpt and app-local x86 MSVC
runtime DLLs. All packaged executable/DLL files passed PE32/x86 and import
closure checks. See [the complete build receipt](reference-runtime-build.json).
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

This assembly completed with **173,011 data files / 2,977,730,517 bytes**:
156,290 text/configuration files and 16,721 selected binary assets, with no
conflicting paths or duplicate donor files. The binary assets comprise 5,878
animations, 1,861 geometry files, 8,936 textures and 46 fonts. Three source DB
configuration files account for the increase over the 173,008-file preflight.
See [the assembly record](runtime-assembly-assessment.json). The stock staged
SQL settings still require the separately generated private PostgreSQL
configuration before DbServer can run; staging does not create credentials,
install a driver or start a database.

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

The current [two-pass hosted run 36074139889](https://github.com/Russianranger/coh-android/actions/runs/36074139889)
passed at the same repository commit as the reference package above. Initialization
took 32.062 seconds; the strict reload took 5.907 seconds, with zero queued errors,
no failure diagnostics and identical bytes for all six attribute maps. The accepted
archive holds all 51 required files plus five newly written dbidmaps; incidental
parser caches are excluded.

The current artifact is preserved as
[accepted-36074139889.zip](schema-generation-evidence/accepted-36074139889.zip),
with its [hashes and preflight summary](schema-generation-evidence/accepted-36074139889.json).
Its outer artifact SHA-256 is
`ad4efacf2dc403e87240ef29935fa60d8f69529f8897709cef5bbb2e8050ecd4`;
the inner schema-output ZIP SHA-256 is
`83fe51b6f8f0533a71c278c869826b357e5c718c8eaee22185a394fbbbfdcbce`.
The earlier [accepted run 36072787971](schema-generation-evidence/accepted-36072787971.json)
remains historical evidence; every one of its 56 generated payloads is unchanged
in the current run, whose build receipt includes the updated PostgreSQL overlay.
Extract the current `accepted-36074139889.zip` into a new directory. Its
`schema-evidence/` directory contains
`schema-generation-report.json` and the inner `schema-outputs.zip`; the sibling
bootstrap directory retains first-pass diagnostics. Keep these exact ID mappings
with any database initialized from them. This does not establish compatibility
with an existing shard database or the custom client.

The database driver's local acceptance check passed against the actual archive
and verified reference package. It derives 99 SQL tables, 5,935 columns and
58,272 attribute rows (56,411 general, 1,771 badge-stat and 90 pop-help IDs).
Normal DbServer execution has now confirmed those counts, as described below.

## Normal DbServer database validation

Source inspection identified a bounded normal-DbServer path that can exercise
generated game schemas without starting a map or graphical client:

```text
DbServer.exe -exportdump C:\fresh-test-output\empty.dump
```

It invokes `dbInit(-1)`, performs template/attribute/table initialization, exports
the database and shuts down. The driver and its 11 acceptance tests are now
implemented in `database/postgresql/tests/run_generated_schema.py`. The accepted
artifact has passed local input checks. The first hosted database run stopped
with SQLSTATE 42P01 while removing foreign keys before their tables existed.
The PostgreSQL removal statement now guards both absent tables and absent
constraints, with ODBC and real DbServer FIFO regressions. The current runtime
and schema builds above both include this updated provider overlay and have
passed. The [normal database run 36075137920](https://github.com/Russianranger/coh-android/actions/runs/36075137920)
passed with that pair on a fresh disposable PostgreSQL database. Initial startup
and export took 11.718 seconds; the second took 5.578 seconds. Both exited zero
and wrote fresh empty dumps. Actual catalogs contain 99 tables, 5,935 columns,
119 indexes and 734 constraints, with all 58,272 expected attribute rows. The two
catalogs and attribute mappings are byte-identical. See the
[evidence summary](postgresql-evidence/generated-schema-36075137920.json) and
[complete redacted evidence](postgresql-evidence/generated-schema-36075137920.zip).
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

The next gates are comparison with asset-complete `MapServer -templates`, normal
MapServer startup and real character creation/save/reload. These results do not
establish a playable server, network save acknowledgements, auxiliary services,
compatibility with the custom client, or Android execution.
