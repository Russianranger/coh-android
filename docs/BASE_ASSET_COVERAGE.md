# Base asset coverage and next upload

## Thor index received: next three uploads

The subsequent device index has been assessed. It reports **95 archives, with
no indexing errors**. Upload these files from `cityofheroes/piggs/` next:

| Archive | Size | Located contents |
| --- | ---: | --- |
| `stage1a.pigg` | 58.5 MiB | 5,878 animation tracks, including MALE/THUMBSUP |
| `stage1b.pigg` | 137.4 MiB | `white`, `grey`, `black`, `invisible` textures |
| `stage1f.pigg` | 118.8 MiB | `dummy_bump`, `dummy_dynamic_cubemap_face0`, `buildingLightPattern` textures |

See [the complete index assessment](THOR_ASSET_INDEX.md). These are filename-table
findings; payload integrity and runtime compatibility remain unverified. The
assessment below records the earlier 22 payload-inspected archives. Its index
command remains useful for future scans, but no repeat scan is needed now.
PostgreSQL persistence has since passed its hosted tests; see
[the current database handoff](HANDOFF.md#current-database-work).

Assessed 2026-09-24 against the unchanged source and Issue 24 text snapshots.
The new input is `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg`.
Sizes, SHA-256 hashes and detailed counts are in
[base-assets-assessment.json](base-assets-assessment.json).

## New verified content

All **2,774 entries** in the four new archives passed PIGG bounds,
decompression, size, MD5 and cached-header checks. Files were inspected without
running any user-supplied executable.

| Archive | Contents | Result |
| --- | --- | --- |
| `fonts.pigg` | 43 TTF-named fonts and 3 TTC font collections | All 46 staged. Every one of the 16 unique font filenames requested by `loadFonts()` is present. |
| `player.pigg` | 709 character/costume geometry files | All geometry versions are supported by the source and compressed-header/data-bounds checks passed. This archive contains no skeletal animation tracks. |
| `misc.pigg` | 694 scene, shader and other text files | 692 match existing baseline files after line-ending normalization; two have no baseline path. Keep the baseline text authoritative. |
| `geom.pigg` | 568 geometry files and 757 Parse6 caches | All geometry header checks passed. Keep caches separate and regenerate them for our baseline. |

The font inspector now includes `.ttc` alongside `.ttf` and `.otf` in its
candidate asset allowlist. Font container signatures were recognizable (42
TrueType, one OpenType and three collections); font rendering has not been tested.
The startup filename coverage does not prove every UI/localization font use.

Geometry checks cover 1,277 files in this batch. They establish version support,
compressed-header integrity and declared data bounds, not complete mesh decoding,
collision validity, dependency completeness or successful map loading.

## Cumulative result and overlay conflicts

Across the **22 inspected archives**, **12,870 file entries** passed integrity
checks. There are **2,487 distinct candidate asset paths**:

- 1,917 geometry files
- 445 textures
- 79 Ogg audio files
- 43 TTF-named fonts and 3 TTC collections

There are 85 repeated candidate paths: 83 repeat identical bytes, while two
have different base and custom-patch variants:

- `object_library/v_cov/bases/details/functional/base_telemed_aux/base_telemed_aux.geo`
- `object_library/v_cov/bases/details/functional/base_teleporter_arc_aux/base_teleporter_arc_aux.geo`

Both differing custom versions came from `i26/geobin_obj.pigg`; their base
versions came from `piggs/geom.pigg`. They are preserved in separate staging
directories. No automatic combined runtime has been created. The first baseline
test should use a coherent base set with the pinned text, and evaluate custom
overrides separately. A first-seen or last-seen choice across arbitrary uploaded
batches would obscure this distinction.

Counting different byte variants separately gives 2,489 candidate files totaling
472,691,118 bytes. This is not the size of a validated playable installation.
The previous Parse7 mismatch remains in the custom patch caches; these new base
archives do not remove that mismatch.

Raw assets are staged locally under `imports/base-fonts-complete-candidate-assets`,
`imports/base-player-candidate-assets` and `imports/base-geom-candidate-assets`.
Their SHA-256 hashes match the verified archive inventories. No raw asset payloads
were added to Git; the uploads, hashes and tools reproduce this staging.

## Concrete remaining startup gaps

These findings concern the **uploaded archives**, not every file on the user's
Thor. The missing files may already be inside archives that have not been uploaded.

1. **Skeletal animation tracks:** there are zero `.anim` files in all 22 archives.
   The engine constructs paths under `player_library/animations/` and returns an
   error when a requested track is missing. Its fallback `MALE/THUMBSUP` is also
   unavailable in the uploaded set. `bin/sequencers.bin` describes animation
   sequencing; it does not replace the track files themselves.
2. **Basic renderer textures:** none of the uploaded texture basenames matches
   `white`, `grey`, `invisible`, `black`, `dummy_bump`,
   `dummy_dynamic_cubemap_face0`, or `buildingLightPattern`, which the startup
   texture loader requests. It explicitly asserts several of these in developer
   builds. Core UI/world/character texture coverage remains incomplete.
3. **Runtime preparation:** bins and database templates still need generation
   from the chosen source/text/asset pair. Matching reference executables,
   database integration with gameplay and an actual character-create/map-entry/save-reload test
   remain undone. PostgreSQL's controlled persistence tests have since passed.

The source references supporting these checks are:

- [Startup font names](../upstream/ouroboros/Game/src/UI/sprite/sprite_font.c), `loadFonts()`
- [Animation file lookup](../upstream/ouroboros/Common/seq/animtrack.c), `animGetAnimTrack()`
- [Missing-animation fallback](../upstream/ouroboros/Common/seq/seqload.c), `seqAttachAnAnim()`
- [Startup textures](../upstream/ouroboros/Game/src/render/tex.c), assignments to `white_tex`, `grey_tex` and other defaults
- [Geometry loader](../upstream/ouroboros/Common/seq/anim.c), `geoLoadStubs()`

## Index command for future scans

Use [tools/index_piggs.py](../tools/index_piggs.py), a standalone Python 3 script.
It recursively reads PIGG filename tables and produces a small JSON report of
file-type counts, animation samples, basic-texture locations and archive sizes.
It reads no file payloads, extracts nothing and modifies no game files. It needs
no Windows PC, extra Python packages or access credentials.

On the Thor, save the script in Downloads. In Termux with Python 3 and access to
the client folder, the user's client root is:

```sh
python3 ~/storage/downloads/index_piggs.py \
  --directory "/storage/emulated/0/Download/cityofheroes" \
  --output ~/storage/downloads/coh-asset-index.json
```

Scan the client root so the report covers both `piggs/` and `i26/`. The current
`coh-asset-index.json` has already been received and assessed; the next uploads
are the three archives at the top of this document. Future scans can identify
new candidates after changes to the installation.
On another Linux/Python environment, use its accessible client/output paths.
The output must be new; choose another filename for subsequent scans.

The indexer supports PIGG v2 with the 16-byte archive/48-byte entry layout.
Unsupported formats and unreadable files are reported as errors. This quick
index **does not verify integrity or compatibility**. Full inspection is still
required after a selected archive is uploaded. Its counts/extensions agreed
with full inspection for all 22 available archives. Thirteen regression tests
passed, including index-only limitations and bad-table rejection.

## Implementation sequence

The index is now complete. The next content action is the three targeted archive
uploads listed above, followed by payload and source-format inspection. A hosted
build of the exact pinned source can be prepared independently; it need not wait
for every cosmetic/audio archive. The gameplay
test itself needs the missing startup assets, matching generated data and SQL
runtime. Keep hosted reference validation before Android runtime integration.

No APK or successful server/client startup is claimed by this assessment.
