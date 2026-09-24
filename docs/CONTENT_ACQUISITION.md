# Missing content: acquisition and next steps

Updated 2026-09-24. Source baseline remains
`0b75ade0c801735e10c5798f641948a45cc50488`.

## Imported successfully

The entire companion [Thunderspies/i24 repository](https://github.com/Thunderspies/i24/tree/d51533ec8e6a9cf726b9214968077a05fdcf19f3)
is now preserved under [`upstream/i24`](../upstream/i24): **156,297 files,
1,992,097,492 bytes** (1.99 GB decimal / 1.86 GiB). This includes 156,287 data
files, eight upstream setup scripts, the README and ignore file. It supplies
powers/definitions, maps and object descriptions, contacts/missions/spawns,
effects, costumes, shaders, localization and server configuration data. It does
not supply the large geometry/texture/audio/font archives excluded by upstream.

| Identity | Value |
| --- | --- |
| Commit | `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |
| Original root tree | `4a9a4e893787b6367e916530235d8818dc32ea8f` |
| Destination import commit | `1768775ab3608cdd852ec7119bbf0139a91248c6` |
| Import scope | Entire tracked tree, no exclusions, byte/mode preserving |
| Missing files, symlinks, submodules | None |
| Case-insensitive path collisions | None |
| Largest file | `data/defs/invention/sets.recipe`, 6,626,071 bytes |
| Integrity records | [Lock](../content-lock.json), [inventory](data-inventory.json), [per-file manifest](data-manifest.json) |

Both local import and the [hosted import workflow](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
passed file hashes/counts/modes and an independent Git subtree identity check.
The original 5,995-file source snapshot also still passes. This proves preservation,
not that the exact source/data pair has passed gameplay tests.

## Acquisition map

| Missing item | Where to obtain it | Current result and course of action |
| --- | --- | --- |
| Companion text data | Pinned `Thunderspies/i24` repository above | Imported completely; no further user download needed for repository development. |
| Binary game assets | [Upstream fetch recipe](../upstream/i24/tools/fetch_data.ps1), using `https://dists.thunderspy.org/piggs/` | Cataloged all 72 archive URLs. All 72 hosted HEAD requests returned HTTP 403; local sample GET also returned 403. No complete binary assets imported. Obtain an accessible equivalent baseline or a copy of existing matching assets. |
| Alternate baseline archive | [OuroDev Magnet Links](https://wiki.ourodev.com/Magnet_Links) | Search indexing identifies full game/server base data and binning resources, including Issue 24 data with Volume 2 Issue 1.1 changes. Direct page access returned 403 here; no torrent hash, reachable seed set or complete archive was verified. Treat as a candidate, not a tested download. |
| Matching executables and runtime DLLs | Build our exact source pin on a hosted Windows runner | Preferred path. Existing [v2i3 release](https://github.com/Thunderspies/CityOfHeroes/releases/tag/v2i3) downloads successfully but is built from older commit `3724da475a470926b006dbf73e2e21fd0e7ec856`. Do not mix it into the locked runtime by default. |
| Stock reference database | [Microsoft LocalDB installation media](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/sql-server-express-localdb) | Install on the hosted Windows reference environment. An installer is not a portable Android database. |
| Stock SQL driver | [Microsoft ODBC downloads](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) | Match the source recipe's Driver 17 and 32-bit game processes. Keep acquisition in reference-build setup, outside the source/data import. |
| Android database | [PostgreSQL sources/packages](https://www.postgresql.org/download/) | Proposed native ARM64 backend; existing CoH PostgreSQL code needs repairs and integration tests before adoption. Downloading PostgreSQL alone does not complete this work. |
| Templates and binary data caches | Generate with this source's MapServer and client against staged content | Do not download another shard's generated bins/templates. Use `MapServer -templates`, then client/server `-createbins` as appropriate. |
| Additional build dependencies | Imported `cmake/dependencies` pins and bundled SDKs | Let the exact hosted build fetch its pinned CPM inputs, then package the resulting runtime DLLs. Avoid importing unrelated latest dependency versions. |

The [hosted availability report](asset-availability.json) records the time and
individual HTTP results. It is a reachability probe, not a content verification.
These failures do not prove that a browser or another network cannot retrieve the
files. No credentials were sent to the asset host; `odtoken` is not needed for the
public data import and must not be reused on a different service.

## Best route for the remaining binary assets

1. Prefer the **same Issue 24 asset set named by the pinned fetch recipe**. If the
   host supplies a working public mirror or corrected URL, compare names and
   checksums before changing the catalog. The current failures should be fixed
   with a valid download source, not by disabling certificate checks.
2. If you can access OuroDev from the Thor, open its **Magnet Links** page and
   locate the Issue 24/Volume 2 base-data or binning-data archive. The input needed
   for this project is the asset archive or its actual download/magnet link;
   a Windows VM is unnecessary. A previously downloaded compatible `piggs/`
   directory or extracted `data/` directory is also useful. These can be acquired
   on Android without a Windows PC. Their compatibility still needs validation.
3. Avoid substituting the current public Thunderspy/Homecoming client wholesale.
   The [Thunderspy live manifest](https://thunderspy.net/manifest/live.xml) is
   advertised by its [installation guide](https://thunderspy.net/guides), but it
   represents that live server's customized content. It is not established as
   this archived source/data baseline. Direct access also returned 403 here.
4. Keep binary archives in a separate downloadable/importable content package,
   outside Git and outside the APK. Record sizes and SHA-256 values, validate
   extraction and a working source/data pair, then freeze a versioned content
   manifest. The app can later import an archive/folder or fetch a known package.

The immediate missing input is therefore **an accessible baseline asset archive,
mirror URL, magnet link, or existing asset folder**. The code and text data no
longer require access to OuroDev. We have not invented a torrent identifier or
claimed a working mirror that could not be checked.

## Tools added for acquisition and staging

[`assets/catalog.json`](../assets/catalog.json) preserves all 72 exact filenames
and URLs from the pinned upstream script. Upstream publishes no archive hashes in
that recipe, so unknown hashes remain null rather than being presented as verified.

The following commands use Python's standard library and do not require Windows:

```sh
# Probe public endpoints; HTTP errors are recorded as report data.
python3 tools/content_assets.py probe --output out/asset-probe.json

# Download archives when the catalog's host is accessible.
python3 tools/content_assets.py fetch --directory imports/piggs

# Inventory an existing folder of the catalog's PIGGs, then detect later changes.
python3 tools/content_assets.py record --directory imports/piggs
python3 tools/content_assets.py verify --directory imports/piggs
```

`--name fonts.pigg` selects one archive; repeat `--name` for a subset. Fetches use
temporary `.part` files and reject truncated responses. Existing files are reused
only when they match their receipt. `record` intentionally establishes a new local
receipt; use `verify` to check it afterwards. A receipt detects missing/changed
bytes; it is not an upstream-authenticated checksum or a PIGG/gameplay validation.

[`tools/prepare_runtime.py`](../tools/prepare_runtime.py) creates a **new** runtime
directory. It verifies both snapshots, optionally copies previously extracted
assets, overlays the pinned text data, copies DB configs from our source pin,
and adapts six launch/template/bin scripts to `CityOfHeroes.exe`. It never runs
the upstream fetcher's Git reset or edits the imported snapshots.

```sh
# Text/configuration staging only; useful now, not a playable install.
python3 tools/prepare_runtime.py --output runtime/reference

# Later, after asset extraction and a matching hosted build:
python3 tools/prepare_runtime.py --output runtime/complete-candidate \
  --asset-data imports/extracted/data --binaries imports/pinned-build
```

The optional binary directory must contain the core executables and a
`build-info.txt` line exactly identifying `Commit: 0b75ade0c801735e10c5798f641948a45cc50488`.
The stager excludes preexisting generated bins from the external asset input.
It does not unpack PIGGs, install SQL, generate templates, prove DLL completeness,
or launch the game. Extraction should use the matching built `pig` tool, in the
catalog's case-insensitive alphabetical order, into a separate scratch data root.
The stager then reapplies authoritative text, without modifying a Git checkout.
Keep downloaded `texts.pigg` out of the active runtime `piggs/` developer directory.

Do not run `upstream/i24/tools/fetch_data.ps1` inside the vendored snapshot. That
upstream script is preserved unchanged for provenance and assumes a standalone
data checkout; its stash/reset behavior is inappropriate for this combined repo.

## Validation and next implementation milestone

- Complete imported tree verified locally and in GitHub Actions.
- Asset receipt checks detect altered and missing files.
- Full text runtime staging completed; all six launcher adaptations and all
  source-pinned DB configs checked. No binaries/assets were supplied to that test.
- Binary archive download/extraction, database initialization, generated bins,
  gameplay and Android execution remain untested.

Next: establish an accessible asset set and add a hosted Windows build/package
workflow for the pinned source. Use that environment for extraction, templates,
SQL reference setup and TestClient save/reload checks. Then pursue the PostgreSQL
and Thor runtime gates in the [Android proposal](ANDROID_PORT_PROPOSAL.md). None
of these steps requires the user to own or operate a Windows PC.
