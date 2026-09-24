# City of Heroes Android handoff

Updated: 2026-09-24 after inspection of 17 custom client archives and base geomBC.pigg.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

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
See [base geometry evidence](base-geometry-assessment.json). Next useful batch:
base `player.pigg`, `misc.pigg`, `fonts.pigg`; `geom.pigg` remains a priority for
additional geometry. A filename/size inventory can guide further batches.

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

1. Complete base-asset acquisition and compatibility checks; the inspected custom
   patch set and geomBC are partial donors. Use `inspect_piggs.py` to verify additional
   PIGGs and isolate candidate assets, then test them against the selected source.
   `content_assets.py record` establishes observed hashes, not upstream-authenticated
   integrity. PIGG structure/extraction and source compatibility remain separate gates.
2. Add a hosted Windows reference build/package workflow for the exact source pin.
   Retain TestClient and all required service executables/DLLs, not only the minimum
   three executables. Record `build-info.txt` with the full source commit. The
   downloadable upstream v2i3 release is older and is not a drop-in locked build.
3. Extract assets in catalog order into a separate directory; use the runtime
   stager to overlay the immutable text data and source configs. Generate templates
   and bins, initialize SQL Server/32-bit ODBC on the hosted reference environment,
   and test character creation, map connection and save/reload across restarts.
4. Continue PostgreSQL repairs, Android runtime/client probes and normal map/mission
   transfers per the [proposal](ANDROID_PORT_PROPOSAL.md).

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. No APK or gameplay validation exists.
