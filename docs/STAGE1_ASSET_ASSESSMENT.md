# Stage1 animation and texture assessment

Assessed 2026-09-24 against the unchanged source pin
`0b75ade0c801735e10c5798f641948a45cc50488` and Issue 24 text pin
`d51533ec8e6a9cf726b9214968077a05fdcf19f3`.

All three requested archives have been received. **14,814 entries passed archive
integrity and offline structural checks.** The uploaded set now contains the
MALE/THUMBSUP fallback animation and all seven previously missing startup
textures. No repeat index run, repeat upload or custom `i26/geobin.pigg` upload
is needed for these checks.

| Archive | Archive size | Verified entries | Content |
| --- | ---: | ---: | --- |
| `stage1a.pigg` | 58.5 MiB | 5,878 | Animation tracks |
| `stage1b.pigg` | 137.4 MiB | 7,033 | Textures, including four startup defaults |
| `stage1f.pigg` | 118.8 MiB | 1,903 | Textures, including three startup defaults |

Archive SHA-256 hashes, exact sizes, structural counts and individual startup
asset hashes are in [stage1-assets-assessment.json](stage1-assets-assessment.json).
Counts, extensions and sizes agree with the Thor index.

## Integrity and staging

Every entry passed table/path/bounds checks, decompression and uncompressed-size
checks, archive MD5 comparison and cached-header comparison where present.
All 14,814 candidate assets were staged separately under
`imports/base-stage1-candidate-assets` and their SHA-256 hashes were rechecked
against the inspection inventory. This batch contains 654,699,284 unpacked bytes
(624.4 MiB), with no duplicate paths within the batch.

The cumulative integrity-inspected count is **25 archives / 27,684 entries**.
That is not a count of unique assets or a complete installation: overlap against
earlier custom textures has not been recomputed. Keep base and custom data
separate. Raw payloads were not added to Git; the uploaded archives and commands
below reproduce staging and detailed inventories.

## Animation findings

All 5,878 tracks passed bounded checks for the 596-byte Win32 header, 20-byte
bone records, key-data offsets/counts/flags, relevant numeric predicates and
reachable hierarchy links. The checks cover 207,137 bone tracks, 11,894,088
rotation keys and 2,083,384 position keys. They do not decode or interpolate
compressed quaternions.

All internal track names match their archive paths case-insensitively. Every
base-animation reference resolves within this archive, with 385 terminal base
skeletons and no missing references or nonterminal cycles. The fallback chain
is `male/thumbsup` to `male/skel_ready2`, whose hierarchy is present. This does
not prove that every animation requested by gameplay definitions is included.

**216 tracks use older, shorter hierarchy arrays** of 70, 75, 85, 96 or 97 slots;
the current source declares 100. Their reachable links fit the stored arrays,
so they are reported as legacy-layout warnings. Higher-index engine accesses
and actual loading remain untested.

The format is a native 32-bit struct dump with file-relative offsets, without
a magic/version field. The source fixes pointer fields in place. A native
ARM64 port must decode the disk layout explicitly into native structures;
casting these records to 64-bit pointer-bearing structs is not viable. Preserve
the x86 reference path while establishing asset/runtime compatibility.

Source: [animtrack.h](../upstream/ouroboros/Common/seq/animtrack.h),
[animtrack.c](../upstream/ouroboros/Common/seq/animtrack.c),
[animtrackanimate.c](../upstream/ouroboros/Common/seq/animtrackanimate.c),
and [animation exporter](../upstream/ouroboros/Utilities/GetAnimation2/src/outputanim.c).

## Texture findings

All 8,936 textures have TX2 containers wrapping DDS data in formats recognized
by the pinned loader: 2,097 DXT1, 2,736 DXT5, 4,077 ARGB8888 and 26 RGB888.
Container sizes, names, DDS headers and mip bounds passed. All 4,884 cached mip
payloads matched their embedded DDS suffixes. Logical dimensions fit the
source's 1024-pixel limit; 1,238 use expected power-of-two padding.

**193 DDS payloads contain bytes beyond the advertised mip footprints.** These
bytes are retained and reported, not interpreted or silently stripped. No pixels
were decoded and no texture was uploaded to a graphics API.

| Startup texture | Dimensions | Format |
| --- | --- | --- |
| `black`, `white` | 8 × 8 | DXT1 |
| `grey` | 8 × 8 | ARGB8888 |
| `invisible` | 64 × 64 | DXT5 |
| `buildingLightPattern` | 128 × 128 | DXT1 |
| `dummy_bump` | 8 × 8 | DXT5 |
| `dummy_dynamic_cubemap_face0` | 4 × 4 | DXT1 |

The source uploads compressed textures through desktop OpenGL S3TC formats.
The Android renderer must verify the chosen graphics path's support or provide
decoding/transcoding. This inspection does not establish that capability.

Source: [texture structures](../upstream/ouroboros/Game/src/render/tex.h),
[texture loader and startup defaults](../upstream/ouroboros/Game/src/render/tex.c),
and [texture exporter](../upstream/ouroboros/Utilities/GetTex/src/gettex.c).

## Reproduce without Windows

From the repository root, with all three archives in an accessible directory,
replace `/path/to/piggs` below. Output paths must be new:

```sh
python3 tools/inspect_piggs.py \
  /path/to/piggs/stage1a.pigg \
  /path/to/piggs/stage1b.pigg \
  /path/to/piggs/stage1f.pigg \
  --output imports/stage1-inspection.json \
  --stage-assets imports/base-stage1-candidate-assets

python3 tools/inspect_asset_formats.py \
  --inventory imports/stage1-inspection.json \
  --assets imports/base-stage1-candidate-assets \
  --output imports/stage1-formats.json

python3 -m unittest discover -s tools -p 'test_*format*.py'
```

The 20 new format/staging tests passed, including truncated payloads, invalid
offsets, hierarchy cycles, altered cached mips, changed staged bytes and path
escapes. Keep the format checker and its animation/texture modules together.
These commands are for reproduction; the current uploads have already been
inspected and the user does not need to rerun them.

## Next implementation work

1. Assemble matching client, MapServer, TestClient and required DLLs alongside
   the tested PostgreSQL DbServer. Combine the verified base donors with the
   pinned text; compare duplicate paths before adding any custom overlays.
2. Generate source-matching caches and database templates. Do not reuse the
   earlier custom Parse7 caches with the Parse6 source loader.
3. Exercise reference startup, character creation, map entry, save/reload and
   map transfer. Use concrete missing-file/runtime errors to select any further
   asset uploads, rather than requesting the remaining installation wholesale.
4. Integrate and measure the Android runtime, accounting for animation disk
   layout, filename case handling and compressed texture support.

The PostgreSQL controlled persistence milestone remains complete. Full gameplay,
rendering and Thor execution remain unvalidated; no working APK is claimed.
