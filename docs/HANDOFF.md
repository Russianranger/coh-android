# City of Heroes Android handoff

Updated: 2026-09-24. PostgreSQL controlled persistence and targeted stage1 archive inspection are complete. Matching runtime assembly and cache/template generation are next.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
The actual Win32 DbServer now has an opt-in, asset-independent persistence test
entry. It exercises the original container parser, writer, SQL FIFO/worker pool,
reader and template updater with controlled templates and records. PostgreSQL
saves commit before completion; serialization/deadlock retries replay the whole
transaction. Permanent or uncertain failures stop without acknowledging the
failed command. Child/parent deletion is atomic.

All four jobs in [run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
passed at implementation commit `0827ccc992daa7530d9f98d742122238197847df`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 20 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild and backup/restore. Download `postgresql-win32-development-build` from
that run; its executable hash matches the executable recorded by the test.

Migration 2 adds transactional table rebuilds preserving sequence high-water,
indexes and foreign keys, explicit ASCII case-insensitive name equality, and the
PostgreSQL auction timestamp filter. Stop DbServer, back up and run
`pg_local.py migrate` for an existing development cluster. See the
[persistence design and test scope](POSTGRESQL_PERSISTENCE.md),
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This is a database development milestone,
not yet a gameplay-validated server or Android APK.

**Stage1 asset inspection complete:** `stage1a.pigg`, `stage1b.pigg` and
`stage1f.pigg` have been received. All **14,814 entries** passed archive integrity
and offline structural checks; 5,878 animations and 8,936 textures were staged
separately. All seven startup texture names and MALE/THUMBSUP are present.
Every base-animation reference resolves within `stage1a.pigg`. Preserve warnings
for 216 legacy hierarchy layouts and 193 DDS surplus-byte cases; runtime use
remains unvalidated. See [the stage1 assessment](STAGE1_ASSET_ASSESSMENT.md).
No repeat index run, repeat upload or custom `i26/geobin.pigg` upload is needed.

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
At that earlier stage there were **zero skeletal .anim tracks** in the supplied
set and none of seven requested basic renderer texture names. The subsequent
stage1 uploads below supply those candidates; runtime startup remains untested. See [asset coverage history](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

The subsequent **`coh-asset-index.json`** has now been received from Thor and
preserved as [thor-asset-index.json](thor-asset-index.json). It reports 73 base
archives and 22 custom-folder archives, with 96,379 entries across those tables
(not deduplicated). Base `stage1a.pigg` lists 5,878 animation tracks, including
MALE/THUMBSUP; `stage1b.pigg` and `stage1f.pigg` list all seven startup texture
names. This locates candidates on the device; it does not add to the 22
payload-verified archives or establish source-format/runtime compatibility.
The indexer previously matched full-inspection counts/extensions for all 22
available archives; thirteen regression tests passed in that earlier pass.

The three selected **stage1 archives** then passed integrity and offline format
checks. Cumulative payload-inspected count: **25 archives / 27,684 entries**.
New staging contains 14,814 distinct paths within the batch and 654,699,284 bytes;
its overlaps with earlier custom assets have not been recomputed. The 20 new
format/staging tests passed. All animation base references resolve, including
the fallback, and all seven startup textures pass structural checks. Native
ARM64 needs explicit decoding of 32-bit animation records; the renderer must
handle the observed DDS formats. Runtime compatibility remains untested. See
[stage1 evidence](stage1-assets-assessment.json) and the
[reproducible checks](STAGE1_ASSET_ASSESSMENT.md#reproduce-without-windows).


[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The original fallback was an accessible compatible archive/mirror/magnet or
existing asset folder; the user has since supplied the targeted assets above.
No additional broad asset upload or Windows VM is required for this assessment. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation steps

1. Use the PostgreSQL development backend as the active database path. The
   controlled DbServer persistence fixtures are implemented; next validate
   generated game templates, character creation, network save acknowledgements,
   save/reload and map transfer. Game-level name uniqueness and auxiliary service
   persistence remain separate gates. Fake auth is only the minimal local
   diagnostic route; no SQL Server save migration has been attempted.
2. Assemble a coherent base asset set from the verified donors, keeping custom
   variants separate. Stage1 archive integrity and offline format checks are
   complete. Resolve legacy hierarchy/DDS warnings through reference runtime
   tests and compare duplicate paths before allowing any overlay.
3. Package exact-pin client, MapServer, TestClient and required DLLs alongside
   the patched DbServer. The older upstream v2i3 release is not a locked build.
   Stage data/assets separately and generate source-matching templates and bins.
   Do not request further archives until dependency/runtime evidence identifies
   a concrete missing input.
4. Bring up native ARM64 PostgreSQL plus Win32 psqlODBC under the selected
   Android runtime, then package under the APK’s own UID. Measure the stock
   65-connection pool, memory, suspension/restart and save durability on Thor.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. No APK or gameplay validation exists.
