# Uploaded client content assessment

Assessed 2026-09-24. Input: `small_i26_piggs.zip`, 17 PIGG archives,
191,014,597 ZIP bytes. Exact archive sizes, SHA-256 hashes and counts are in
[client-content-assessment.json](client-content-assessment.json).

Follow-up: `geomBC.pigg` has also been received and verified; see the
[base geometry result](#base-geometry-follow-up) below and
[base-geometry-assessment.json](base-geometry-assessment.json).

The subsequent fonts/player/misc/geom batch is covered in the
[current base asset assessment](BASE_ASSET_COVERAGE.md). Current totals are
22 archives / 12,870 verified entries / 2,487 distinct candidate asset paths.
That report supersedes the next-upload suggestions in this earlier assessment.

## Result

All **8,864 entries** passed bounds, decompression, uncompressed-size and MD5
checks. Cached asset headers also matched the corresponding file payloads.
The 17 archives use PIGG version 2, supported by the imported archive reader.
This establishes internal consistency, not trusted provenance or gameplay
compatibility. No supplied executable was run.

There is a concrete compiled-data mismatch: **549 files use `Parse7`**, while
the selected source defines `PARSE_SIG` as **`Parse6`**. Powers, classes,
origins, costumes, effects, particles and some map/object caches are affected.
The loader compares the signature even when schema-CRC checks are disabled in
production mode. These files cannot be loaded unchanged through this parser.
Do not edit the signature bytes to bypass the check: that does not convert the
serialized data or reconcile gameplay definitions/protocols.

The signature numbers describe serialization formats, not City of Heroes issue
numbers. They do not identify an exact SCoRE branch or release.

| Content | Count | Treatment |
| --- | ---: | --- |
| Generated bins and bounds | 6,668 | Retain for inspection; regenerate for the selected source/data pair. |
| Geometry files (`.geo`) | 141 | Extracted into separate candidate staging; engine compatibility untested. |
| Textures (`.texture`) | 445 | Extracted into separate candidate staging; rendering untested. |
| Audio (`.ogg`) | 79 | Extracted into separate candidate staging; playback untested. |
| Other content, primarily text | 1,531 | Compared with the pinned text snapshot; no automatic overlay. |

The **665 candidate binary assets total 152,755,341 bytes** (about 145.7 MiB).
Their extracted SHA-256 values were checked against the verified archive
inventory. They are staged locally under `imports/client-i26-candidate-assets`,
outside the active runtime and immutable snapshots. Raw assets and uploaded
executables are not published in Git. Reproduce staging from the uploaded ZIP
using the tool below; the Git report preserves the input/archive hashes.

This is a partial asset donor, not a complete baseline or a ready server.
Substantial new/custom content appears in the geometry and texture paths. Of
the 141 geometry paths, 84 have same-stem text paths in the baseline; this is
only a path match, not proof that their contents agree.

## Compiled and text content findings

- Recognized serialized headers: 6,112 `Parse6` and 549 `Parse7`. Seven generated
  cache files do not use this `CrypticS` header. A `Parse6` match alone does not
  establish matching schema CRCs, definitions, asset references or protocol.
- `bin.pigg` contains server-relevant caches, including contacts, tasks, spawn
  definitions, scripts and `npcs_server.bin`. The inspected set contains no
  `server/` tree, raw `defs/` or `scripts/` tree, database backup, or server
  executable. These caches do not establish a complete custom-server package.
- Among the text/other files, 1 is byte-identical to the baseline, 56 have no
  matching baseline path, and 1,474 differ in bytes. **1,439 of those differences
  disappear after normalizing line endings**. The remaining 35 differ beyond
  line endings; this is not a count of semantic gameplay changes.
- One concrete change is an added material swap in
  `scenes/cityscene_atlas_park.txt`. Preserve our baseline text while evaluating
  these customizations separately.
- The `Parse6` dependency lists collectively mention 1,230 unique paths absent
  from the text snapshot. These are path references, not recoverable source
  files or a definitive list of missing runtime requirements. `Parse7`
  dependency sections were not decoded.

## Earlier client evidence

The uploaded shortcut launches:

```text
Production_Client.exe -auth 127.0.0.1 -patchdir i26
```

Its working directory is `C:\cityofheroes`. Thus `i26` is an explicitly selected
patch directory; its name does not establish Issue 26. The user describes this
as an earlier customized client from the individual who later ran Cake/New Dawn.
That history is user-provided, not independently authenticated.

Both supplied clients are PE32 Windows x86 executables with `SCORE` in their
version metadata. Those resources do not identify the exact source revision.
`-auth 127.0.0.1` expects local authentication service connectivity; the shortcut
does not start the server. Our initial baseline uses the documented fake-auth
DBServer/MapServer setup and a client built from the same selected source.

The screenshots show loose `data/bin` empty and `texture_library` containing
`MAPS`, `P_MAPS` and `V_MAPS`. The archive inspection now confirms that substantial
compiled data exists inside the PIGGs despite the empty loose bin directory.

## Next content and implementation steps

1. Continue inspecting base assets from **`piggs/`**. `geomBC.pigg` is now verified
   and staged separately. The next useful batch is `player.pigg`, `misc.pigg`,
   and `fonts.pigg` if present; `geom.pigg` remains a priority for further base
   geometry. Their names are upload priorities, not a verified inventory of
   their contents. A full base-folder file/size inventory will let us
   choose subsequent batches without repeated screenshots.
2. Keep this custom `i26` patch set separate from the base set. Extract verified
   candidate assets into isolated staging, retaining hashes and provenance.
   Additional `geobin`/`bin` packages have lower priority because their caches
   must be regenerated for the baseline.
3. Build the exact pinned source, including client/server and utilities, on a
   hosted Windows runner. Stage compatible base assets with the already-imported
   Issue 24 text data. Generate bins and database templates with those builds.
   The user does not need a Windows PC.
4. Validate character creation, map entry and character save/reload on that
   reference environment before treating the pair as compatible. Continue the
   Android database/runtime work from the existing proposal.

Recreating this customized shard exactly would additionally require its matching
server source/definitions or a known-compatible server package. That is a
separate compatibility target; it is not required to pursue our selected baseline.

## Base geometry follow-up

The supplied `geomBC.pigg` is 167,716,173 bytes and contains **1,232 entries**:
584 `.geo` files and 648 generated `.bin` files. Every archive entry passed
decompression, length, MD5 and cached-header checks. All 648 serialized caches
have `Parse6` signatures; this is not enough to establish matching schemas or
content, so regenerate caches for the selected baseline.

All **584 geometry files** also passed the geometry header checks derived from
`Common/seq/anim.c:geoLoadStubs`: supported format version, header decompression,
declared header length and data-block bounds. Versions are 452 version-8 files,
91 legacy files, 38 version-7 files, one version-5 file and two version-4 files.
These geometry version numbers are separate from `Parse6`/`Parse7` cache tags.
Meshes, collision grids, model records, texture dependencies and runtime loading
have not been validated. In particular, this does not prove that Atlas Park or
any other map is complete or playable.

Geometry files total **166,153,393 bytes** and are staged under
`imports/base-geomBC-candidate-assets`, separately from the custom patch donor.
There are no duplicate geometry paths with the earlier 665 candidate assets.
217 geometry paths have same-stem baseline text paths; path matches are only
an indicator and do not measure runtime coverage.

Across both uploads, **18 archives / 10,096 entries** have been verified, with
**1,249 distinct candidate binary assets / 318,908,734 bytes** staged. The upload
and per-archive hashes plus the inspector reproduce these results without
Windows. Raw assets remain outside Git and are not yet an active runtime.

The inspector now records `.geo` header checks automatically. Eleven regression
tests pass, including versioned/legacy geometry bounds and unsupported geometry
versions. The original eight archive tests are retained.

## Reproducible inspection without Windows

After extracting the ZIP into `imports/client-i26-piggs`, run from the repository
root in a Linux/Termux shell:

```sh
python3 tools/inspect_piggs.py imports/client-i26-piggs/*.pigg \
  --baseline-manifest docs/data-manifest.json \
  --output out/client-i26-inventory.json \
  --stage-assets imports/client-i26-candidate-assets

python3 -m unittest discover -s tools -p 'test_inspect_piggs.py' -v
```

Both output paths must be new. The tool validates every entry and inventories
paths, hashes, types and serialized headers. It supports PIGG v2 with the
16-byte archive/48-byte entry layout, not HOGG or arbitrary future variants.
It imposes archive/entry/total size limits, rejects unsafe paths and case
collisions, and only stages an allowlist of binary asset extensions. Staged
paths are lowercased for the baseline's file naming convention. Duplicate
candidate paths across archives are rejected instead of choosing an overlay.
For `.geo` files, it additionally records source-supported versions and checks
compressed header lengths/data bounds. Unsupported geometry versions are reported
without claiming runtime compatibility; archive integrity remains a separate test.

An interrupted/failed staging directory retains `.inspection-incomplete` and
must not be used. Successful staging still does not establish runtime
compatibility. Eight regression tests passed, covering corruption, truncation,
path traversal, case collisions, inflation limits, cached-header mismatches,
unsupported versions and selective staging.

Primary format evidence is in the preserved source:

- [PIGG layout](../upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h)
- [PIGG reader and checksum validation](../upstream/ouroboros/libs/UtilitiesLib/src/utils/piglib.c)
- [Data pools](../upstream/ouroboros/libs/UtilitiesLib/src/components/datapool.c)
- [Expected parser signature](../upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h)
- [Serialized signature/CRC checks](../upstream/ouroboros/libs/UtilitiesLib/src/utils/serialize.c)
- [Bin reader and parse-table CRC](../upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c)
- [Geometry header reader and supported versions](../upstream/ouroboros/Common/seq/anim.c)

No Android APK, server runtime or gameplay validation was produced by this
inspection. Both imported source/data snapshots remain unchanged.
