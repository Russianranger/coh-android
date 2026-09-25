# City of Heroes Android handoff

Updated: 2026-09-25. PostgreSQL controlled persistence, targeted stage1 inspection,
matching Windows packaging, base runtime assembly and data-only database schema
generation have passed their current checks. Normal fixture-OFF DbServer schema
initialization/export/reload and normal MapServer network save acknowledgements
have also passed against fresh PostgreSQL clusters.
The refreshed runtime and schema artifacts share repository commit
`775a0dd770adac045484805dbbb5f68054c7a354`. Game-level persistence, asset-complete
reference comparison and Android execution remain validation gates.
The reviewed asset ZIP has been uploaded to a draft release and downloaded by
the hosted runner with its exact size/hash verified. That attempt then stopped
on Windows manifest line endings before game execution. The byte-preserving
checkout fix is applied and full hosted staging passed in run 36176806895.
The normal template comparison is in progress; Atlas Park readiness is pending.

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

All four jobs in the current [regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 21 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild, backup/restore and foreign-key removal against absent tables. The
narrow PostgreSQL guard fixes the fresh-database initialization failure without
changing the preserved source snapshot.

The earlier [20-group implementation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
at `0827ccc992daa7530d9f98d742122238197847df` and
[regression refresh 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
remain historical evidence. The separate normal fixture-OFF DbServer
[startup/export/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed using the accepted schema/runtime pair and a fresh disposable
PostgreSQL database. This exercises normal game-schema initialization in addition
to the controlled persistence fixtures; it does not create or save characters.

**Normal network acknowledgements passed:** [run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
verified creates, an update after restart, and a two-container request held behind
an actual PostgreSQL row lock. No ACK arrived during the 2.078-second observed
write block. After release both rows were committed; an injected COMMIT failure
then produced zero ACKs, preserved the previous row, and stopped DbServer with
exit 3. The normal reference package had fixture mode OFF. The report and all
redacted logs are [preserved](postgresql-evidence/network-ack-36125829311.json).
Batches are not atomic as a whole, and player-session completion is untested.

The latest test drivers distinguish the specific observed benign PostgreSQL
catalog notices from real errors. Both new normal-process gates passed at
`a0ae66d72648d33a7f70b3116d1e1800d9164184` using the accepted `775a0dd...` builds.

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

**Reference runtime refreshed:** [run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed with the exact source pin, PostgreSQL patch and fixture mode OFF at
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
Download `reference-win32-runtime` (artifact `10843979104`) from this run;
it supersedes [the earlier package 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663).
Client, MapServer, DbServer, TestClient, pig and Launcher are packaged with
required supplied DLLs and app-local x86 MSVC runtime libraries. The package
passed hash, PE and dependency checks. The verified base assembly contains
173,011 data files / 2,977,730,517 bytes, with no conflicting donor paths.
The preflight's earlier 173,008 count excluded three additional source-pinned DB
config files added by final assembly. See [current assembly evidence](reference-runtime-evidence/assembly-775.json)
and [reproduction/build instructions](REFERENCE_RUNTIME.md).

Local game execution is blocked by this environment's wineserver IPC restriction.
Use hosted Windows for further runtime validation. The separate data-only schema
patch remains isolated from the reference package and retains error/output
gates. Its incidental caches must not be reused as gameplay caches.

**Data-only schema generation refreshed:** [run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the current reference package. Bootstrap
took 31.468 seconds and strict reload 5.750 seconds, with zero queued errors and
identical bytes for all six attribute maps. All 51 required outputs plus five
dbidmaps are preserved in [the current accepted artifact](schema-generation-evidence/accepted-36088012666.zip).
Every one of these 56 generated payloads is byte-identical to the
[earlier accepted run 36072787971](schema-generation-evidence/accepted-36072787971.zip),
which remains historical evidence. Keep the accepted attribute-ID mappings with
any database initialized from them.

**Normal DbServer schema startup/reload passed:** the first hosted attempt
exposed a fresh-database FK-removal ordering bug. The narrow correction passed
its regression suite and is included in both current artifacts. With that pair,
[run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
completed fresh initialization/export in 13.219 seconds and a second pass in
5.718 seconds. Both exited successfully with no failure diagnostics and produced
fresh empty dumps. Both passes found 99 tables and 58,272 attribute rows
(56,411 general, 1,771 badge-stat and 90 pop-help IDs), with identical catalog
hashes and attribute mappings. Both catalogs contain the verified 5,935 columns,
119 indexes and 734 constraints.
The tested DbServer has persistence fixture mode OFF; its executable SHA-256 is
`fb62028b24bf3165bdcf09e80909d02df5391f89986b9e0454934909a67d93f8`.
See the [downloaded evidence](postgresql-evidence/generated-schema-36125829298.zip)
and [summary](postgresql-evidence/generated-schema-36125829298.json).
Equality with an asset-complete `MapServer -templates` reference, complete
serializer semantics, map loading and gameplay remain unvalidated.

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

1. Follow the corrected manual [asset run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895),
   currently comparing templates after successful full staging, with schema run `36088012666`, reference run
   `36088012664`, asset `588984151` and `run_one_map=true` to compare ordinary
   `MapServer -templates`. Upload is complete: unpublished draft release
   `396839391` contains the accepted **615,541,018-byte** ZIP, SHA-256
   `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`.
   Ignore incomplete asset `588979946`. No repeat PIGG or ZIP upload is needed.
   The initial manual [run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
   failed during download before any game process, suspected to be the draft
   release's rejection of the read-only token. Its HTTP status was not logged.
   [Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
   scopes `contents: write` to the manual comparison job; global/tooling tokens
   stay read-only. It also adds safe numeric HTTP status and stage diagnostics;
   all 12 downloader tests and [tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
   passed. [Run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
   then successfully downloaded and verified the exact ZIP, confirming hosted
   draft access. It failed `Manifest must use canonical JSON` before game
   execution: Windows checkout changed the manifest's LF bytes to CRLF.
   [Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
   marks `assets/reference-inputs-*.json -text`; a temporary Git checkout with
   `core.autocrlf=true` reproduced the accepted canonical bytes, and
   [tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
   passed. The current manual run uses that fix. The release remains unpublished
   and raw assets are not uploaded as Actions artifacts. See the
   [concrete handoff](NEXT_SERVER_VALIDATION.md) and
   [transfer evidence](reference-runtime-evidence/asset-transfer-20260925.json).
   The matching reference package and coherent base assembly are ready. Preserve the accepted attribute-ID mappings; do not
   substitute the separate schema executable or its incidental caches for the
   reference runtime.
2. After comparison succeeds, the prepared one-map driver stages a fresh copy
   and checks Atlas Park through independent DbServer status queries for a
   60-second readiness window. This has not run yet. Generate further server/client
   caches with the bounded harness when the runtime has the required graphics. Resolve legacy animation hierarchy/DDS warnings through reference
   runtime use. Keep custom variants separate and request further archives only
   when runtime evidence identifies a concrete missing input. The older upstream
   v2i3 release is not the locked build; use the current reference artifact.
3. Implement the [character persistence validation design](CHARACTER_PERSISTENCE_VALIDATION.md)
   after the map gate: fake-auth creation, a normal-protocol currency change,
   explicit logout, committed SQL verification, service restart and exact-name
   resume. This is design-only, not an implemented or executed test. Stock
   no-fallback resume is a short scene probe; a sustained second session needs
   the separately proposed TestClient option and a new reference build.
   Follow with map transfer, player-session completion callbacks, game-level
   name uniqueness and auxiliary-service persistence. Generic-container network
   ACK ordering is now verified. Fake auth is only the minimal local diagnostic route; no SQL
   Server save migration has been attempted. Empty-database startup/export and
   controlled persistence fixtures do not establish these gameplay behaviors.
4. Bring up native ARM64 PostgreSQL plus Win32 psqlODBC under the selected
   Android runtime, then package under the APK’s own UID. Measure the stock
   65-connection pool, memory, suspension/restart and save durability on Thor.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. No APK or gameplay validation exists.
