# City of Heroes Android handoff

Updated: 2026-09-24. Active work switched to PostgreSQL development at the user’s request.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
Live PostgreSQL 16.15 and 18.6 tests pass, including 65 ODBC connections, schema
changes, bound values, asynchronous-style concurrent writers, rollback, clean
restart, forced WAL recovery and backup/restore. The actual Win32 DbServer has compiled successfully, and the complete probe
also passes with 32-bit Windows psqlODBC 18.00.0004 against PostgreSQL 17.11. See
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This is a database development milestone,
not yet a gameplay-validated server or Android APK.

**Deferred until tomorrow / the next session:** resume the Thor archive index and
missing animation/basic-texture investigation. No more asset uploads or index
work are needed from the user during this database session.

## Completed

- All 5,995 source files verified; exact-commit upstream Windows build and nine
  utility/archive/codec tests passed, as previously audited.
- Imported the entire `Thunderspies/i24` tree at
  `d51533ec8e6a9cf726b9214968077a05fdcf19f3` under `upstream/i24`: 156,297 files,
  1,992,097,492 bytes, no exclusions. Local and hosted integrity/tree checks passed.
  Import commit: `1768775ab3608cdd852ec7119bbf0139a91248c6`.
- Added `content-lock.json`, data inventory and per-file manifest. The importer
  and verifier accept `--lock content-lock.json`; existing source defaults remain.
- Added the exact 72-archive upstream catalog and portable `content_assets.py`
  probe/fetch/record/verify tool. Receipt checks detect changed/missing bytes.
- Added `prepare_runtime.py`; full text-only staging passed. It keeps imports
  immutable, fixes `Game.exe` to `CityOfHeroes.exe` in staged launchers and uses
  source-pinned configs. It accepts extracted asset data and exact-pin build
  outputs separately; it does not execute programs or install SQL.

## External content result

The user's `small_i26_piggs.zip` has now been inspected: all **17 archives /
8,864 entries** passed size, decompression, MD5 and cached-header checks.
**549 compiled files use Parse7; the pinned source expects Parse6**, so these
caches cannot be reused unchanged. Staged **665 candidate binary assets**
(141 geometry, 445 textures, 79 audio files; 152,755,341 bytes) separately,
with runtime compatibility still unverified. No raw client binaries/assets were
published. The original ZIP plus the new portable inspector reproduce staging.
See [client content assessment](CLIENT_CONTENT_ASSESSMENT.md) and its
[per-archive hashes/counts](client-content-assessment.json). Eight inspector
regression tests passed in that initial pass.

The subsequent **`geomBC.pigg`** also passed: 1,232 entries, comprising 584
geometry files and 648 Parse6 caches. All geometry files use versions accepted
by the source and passed compressed-header/data-bounds checks; meshes/collision
and runtime loading are untested. Staged geometry separately under
`imports/base-geomBC-candidate-assets`. Cumulative result: **18 archives,
10,096 verified entries, 1,249 distinct candidate assets / 318,908,734 bytes**.
The inspector now records geometry header checks; eleven regression tests pass.
See [base geometry evidence](base-geometry-assessment.json).

The later `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg` batch also
passed: **2,774 additional entries**. Cumulative result is now **22 archives /
12,870 entries / 2,487 distinct candidate asset paths**, with two conflicting
custom/base geometry variants kept separately. All 46 fonts are staged, including
TTC collections; every one of the 16 startup font filenames is present. All
1,277 new geometry headers passed. `misc.pigg` mostly duplicates the pinned text.
There are still **zero skeletal .anim tracks** in the supplied set and none of
seven requested basic renderer texture names. This prevents calling the content
startup-ready. See [current coverage and next-upload instructions](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

Tomorrow’s deferred input is **`coh-asset-index.json`**, generated on the Thor with the
new standalone `tools/index_piggs.py` against the whole client root. This reads
only archive tables and identifies which remaining archives contain animations
and base textures. It is not an integrity verifier. Counts/extensions matched
full inspection for all 22 available archives; thirteen regression tests pass.

[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The needed input is an accessible compatible archive/mirror/magnet or existing
asset folder. No Windows VM is required. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation steps

1. Use the PostgreSQL development backend as the active database path. Validate
   the actual DbServer container/FIFO save pipeline with generated templates,
   then character creation, save/reload and map transfer. Resolve the remaining
   auction SQL filter, name collation rules and retry/rebuild behavior. Account
   and auxiliary service persistence is a separate gate; fake auth is only the
   minimal local diagnostic route.
2. Tomorrow, resume `coh-asset-index.json` from Thor to locate animations and
   basic textures. Inspect and stage candidate assets separately; retain all
   archive integrity and source-format checks already established.
3. Package exact-pin client, MapServer, TestClient and required DLLs alongside
   the patched DbServer. The older upstream v2i3 release is not a locked build.
   Stage data/assets separately and generate source-matching templates and bins.
4. Bring up native ARM64 PostgreSQL plus Win32 psqlODBC under the selected
   Android runtime, then package under the APK’s own UID. Measure the stock
   65-connection pool, memory, suspension/restart and save durability on Thor.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. No APK or gameplay validation exists.
