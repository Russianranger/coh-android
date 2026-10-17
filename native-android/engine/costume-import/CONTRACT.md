# Costume dictionary export/import boundary

Implemented: an additive bounded serialized import around the existing read-only
`coh_ent_costume_dictionary_load` interface. Full hash storage slots, holes,
present empty strings, original case, original slot capacities, and palette KEYS
are preserved. Import commits the dictionary pointer and receipt together. The
result owns copies and survives destruction of input bytes. Neither capture
origin nor actor authority is certified by this API.

## Format COHCDI1 (export contract, not original network grammar)

All numbers are unsigned little-endian. No padding/trailing bytes are admitted.

| Offset | Field |
| --- | --- |
| 0 | Eight bytes `COHCDI1\0` |
| 8 | Ten U32: version=1, generation, body parts, body types, ordinary max_size, extra max_size, palette max_size, ordinary valid count, extra valid count, palette valid count |
| 48 | Four 32-byte IDs: source schema, asset inventory, runtime profile, capture run |
| 176 | Exactly ordinary max_size slot records, then exactly extra max_size slot records |
| variable | Exactly palette max_size palette records |

A string record is U16 length then that many bytes; length65535 is a hole and
has no bytes. Length0 is a PRESENT empty key. Maximum string length259 excludes
NUL; embedded NUL is refused. A palette record is U8 presence then U32 key.
Presence is0/1; absent key must be0, present key must be nonzero. Original deleted
slots export as holes, not as deleted key/value internals. Max sizes must be
powers of two in2..65536. Body types must be the pinned source table count9;
body parts1..29 must also match independently admitted expected metadata.

Caller supplies independently verified payload SHA256, source schema ID,
inventory/profile/run IDs, generation and counts. All metadata must match the
file; SHA256 covers every byte including headers and holes. The source ID is
SHA256 of sorted `path + NUL + LF-normalized-file-SHA256 + LF` entries from
source-pins.json, not a Git commit or asset identifier. Source ID must also equal
the compiled ID. Exact source revision, compiler/profile, files/bins inventory,
run receipt and their trustworthy association remain an external admission
responsibility. Supplying a hash of arbitrary fixture data cannot establish
original runtime origin. No expected identity may be derived from the same
untrusted file and then treated as independent evidence.

## Named memory and lifetime

Before digest invocation or allocation, import charges the entire input, pins,
provider, declared provider context, pointer output, receipt, 16KiB native stack,
exact temporary full-slot arrays, caller retained bytes, provider transient
reservation, and the immutable loader's FULL existing4MiB maximum allocation.
Budget must not exceed8MiB. The full loader reservation is conservative; the
receipt also records actual immutable allocation size. This permits refusal of
otherwise syntactically valid large inputs under aggregate budget and does not
raise any existing cap. Temporary storage is one calloc, always freed; final
storage uses the existing single immutable allocation. No callback occurs on
budget refusal. Input/provider/context/output ranges must not overlap, including
pointer overflow. All inputs remain immutable through both parsing passes and
SHA callback. Provider must reserve all transient scratch and must neither
retain input nor allocate hidden storage. Its implementation and external
library stack/sanitizer coverage are separately qualified; native frame sums do
not claim closure over that dependency. Tests use low-level host OpenSSL
SHA256_Init/Update/Final, record the actual linked library hash, and explicitly
do not qualify OpenSSL's own stack or sanitize its implementation.

## Original source audit and required authentic data

`costume_initHashTable` creates ordinary strings with initial size4096, extras256,
palette128. These are INITIAL capacities, not capture values. Tables may resize;
`stashTableResize` reinserts old storage entries. `stashFindKeyByIndexInternal`
reads `pStorage[index]` and refuses empty/deleted slots, and packet width uses
`log2i(stashGetMaxSize(table))`. A dense list or sorted list is incompatible.
The source oracle executes unchanged whole original slot getters, packet width/log2i, original body-type table/count and palette
word function against synthetic slot storage, including holes/deleted slots,
present empty keys and indexed integer color keys. Original insertion/hashing,
resize, full costume builder, asset parser, packet producer/consumer and original
layout ABI are NOT executed by this new oracle. Their full sources/functions are
pinned for audit; existing costume wire tests remain independent qualifications.

Actual dictionary inputs required, all from ONE matching source/profile/runtime:

- Full ordinary `costume_HashTable` slots0..max_size-1 including holes and exact
  key bytes, valid count and max_size.
- Full `costume_HashTableExtraInfo` slots, with the same metadata.
- Full `costume_PaletteTable` slots with validity and actual INT KEYS, not the
  arbitrary0xabcdef01 values used by `addPaletteToTables`.
- `GetBodyPartCount()` after `bpReadBodyPartFiles`: source loads
  `Defs\\UI/*.bp`, `BodyParts.bin`, shared name `SM_BodyParts.bin`. Capture actual
  parsed ordered body-part identity/count, not an offline preview's part count.
  ParseBoneNames refuses counts >=MAX_BODYPARTS (=MAX_COSTUME_PARTS=30);
  this import therefore refuses30 despite the existing generic loader's <=30
  storage ceiling. This is a source admission restriction, not a raised cap.
- `getBodyTypeCount()` and ordered `g_BodyTypeInfos` (pinned source has9 entries).
- Exact loaded costume/supergroup palette bin and source/cache identities,
  runtime profile, source revision/build/ABI, generation and capture/run receipt.

Server/TEST_CLIENT `loadCostumes` uses shared ParserLoadFilesShared:
`Menu/Costume/Localized/costume.ctm` / `costume.bin`,
`Menu/Costume/ColorPalettes/supergroupColors.ctm` / `supergroupColors.bin`, and
`Menu/Costume/TailorCost.ctm` / `tailorcost.bin`. The tailor bin is part of load
context, not inserted into these dictionaries. Preprocess and fillExtraData
callbacks affect loaded structures. The ordinary CLIENT path additionally loads
supergroupEmblems.bin and has editnpc path overrides and reload callbacks; it
must not be assumed identical to a server generation without equality evidence.

Builder first inserts global super palette, then visits body/origin/region/bone/
geometry/texture arrays in REVERSE order; origin skin then body palettes are
inserted in their own forward color order. Texture1/2 names are truncated IN
PLACE at their first dot before insertion. Extra keys include body-set, region
and bone-set names. Ordinary keys include geometry, truncated texture names,
FX and masks. Reward/tagged/GeoData tables are separate. Palette colors are
`r + (g<<8) + (b<<16) + 0xff000000`; source float-to-int conversion and actual
palette inputs must match. Initialization reuses some existing tables, while
client reload explicitly destroys/rebuilds ordinary/extra/reward/palette tables;
capture must record when tables were initialized/reloaded. Reconstructing from
raw bins requires exact parser, insertion, resize, cache and ABI qualification;
exporting actual initialized slots avoids guessing those identities.

No authentic complete costume dictionary payload has been admitted here.
Existing scene/runtime captures are not evidence that these costume globals or
loaded costume/body-part inputs were captured. No new server capture was run.
The next data operation is to inspect preserved artifact inventories for these
exact exports/bins and receipts, then design an isolated source export if absent.
A successful import alone does not close appearance GEO/material/rig resources,
very-rare entity tails, selected-player identity/position, remaining enclosing
framing/dictionaries, authentication, ACK or renderer publication.
