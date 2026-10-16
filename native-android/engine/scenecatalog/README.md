# Original saved-definition catalog adapter

This module supplies the concrete `CohSgImportFn` implementation missing from
`engine/scenegraph`. It decodes a bounded sidecar exported from an already loaded
original MapServer `GroupInfo`. It neither loads a live server catalog itself
nor grants world, actor, render, asset, authentication or READY authority.

`sendGroupFile` deliberately omits saved definitions in unmodified libraries.
A received GROUPS body with 508 files and zero definition records therefore
cannot reconstruct its definitions from that body alone. Original
`receiveGroupFile` uses an existing file or checksum-matched `.bounds`, falling
back to `groupLoadFull`. Bounds files contain public names and raw `GroupBounds`,
not complete definition slots or topology. Original `groupLoadInternal` combines
`.rootnames` and text (or geobin), loads imports, creates/moves future slots,
renames definitions and skips degenerates. The existing offline subset parser
cannot promise the running server's file IDs/order/checksums.

## Producer boundary

Include `source_export.inc` after the unchanged original `groupnetsend.c` in the
same translation unit, where its static `sendDef` remains visible. The ordinary
packet subsystem must already be initialized. Call:

```c
int coh_source_catalog_export(CohSourceCatalogOutputFn output, void *context,
    unsigned int asset_generation, CohSourceCatalogExportReport *report);
```

The callback is `int output(void *, const unsigned char *, unsigned int)` and
must copy/consume each borrowed span, returning exactly 1. Return value 0 from
the exporter means complete success. Any failure can leave partial callback
output; the embedding owner must stage and atomically publish only after full
success. The exporter has no filesystem/network/link operations. It does not
change GroupDef, GroupFile, DefTracker, force_reload or normal network payloads.
It calls the original `sendDef`, bypassing saved-definition filtering, and the
original `groupInfoCrcDefs`, `groupInfoCrcRefs` and `groupInfoRefCount`.

The caller must serialize a stable world snapshot and packet/property writing
through the entire call, including callbacks: original property serialization
uses process globals. Two passes measure then emit. The producer rejects
observed changed counts/CRC/size; this is no replacement for exclusive ownership.
Source generation is an explicit caller-owned binding, not authentication.
The producer admits at most 65,536 total root tracker slots, including inactive
slots, before any tracker/CRC traversal. Active roots have a separate 65,536
cap. The final CRC recheck rejects a changed tracker-slot count before traversal. The
original packet allocator may grow before the 4 MiB per-record admission check;
this exporter does not claim a hard allocation bound on upstream allocation.

## Envelope

All scalar fields below are unsigned little-endian 32-bit. No transport header,
zlib stream, runtime executable, pointer or account data occurs in the envelope.
Names include a terminal NUL, have 1–255 visible ASCII characters, and are never
used as filesystem paths by this module.

| Header offset | Field |
|---|---|
| 0 | Eight-byte magic `COHCAT01` |
| 8, 12, 16 | Version 1, header size 48, exact total bytes |
| 20, 24, 28 | Asset generation, file count, nonnull definition count |
| 32, 36, 40 | Original definitions CRC, references CRC, active root count |
| 44 | Reserved zero |

Files follow in original index order 0..N−1, preserving the server's actual slot
identity even though network GROUPS sends files in order 1..N−1,0. Each file has
five scalars: index, bounds checksum, original slot count, nonnull record count,
filename byte count; then the filename. Each nonnull slot follows in increasing
ID order with four scalars: original slot ID, wire bit count, wire byte count,
alignment 1; then the **complete unmodified original `sendDef` record**, including
its id+1 prefix. Byte alignment means bit count equals eight times byte count.
Allocated tombstones remain records; null slots are omitted. File slot counts
retain holes. All optional render/property metadata remains owned verbatim.

## Native ownership and integration

`coh_scenecatalog_preflight` allocates nothing. It checks the envelope's complete
bounds, original file/slot order, duplicate file names, generation, record
lengths/IDs, source definition-name CRC (including `NAMELESS` tombstones and null
omissions) and counts children. Its successful result is **preflight only**; the
full record decoder has not run. Numeric diagnostics retain stage, byte offset,
file/slot, files/slots/definitions/children, source CRCs/roots, minimum array
ownership, wire bytes, and whether current graph count limits are exceeded.

`coh_scenecatalog_load` first preflights, then allocates exactly counted arrays
and uses the shared `coh_scenegraph_definition_read` implementation for complete
records and exact cursor exhaustion. Candidate strings, child/swap arrays and
metadata are deeply owned. Failed decode/allocation/budget/generation/checksum
leaves the prior catalog unchanged; successful replacement frees it only after
publication. `coh_scenecatalog_file` lends immutable definitions synchronously,
checking full filename, checksum and generation. The scene graph deep-copies
these records before returning. The owner serializes catalog/graph use; this is
not concurrent publication or RCU.

`coh_scenecatalog_match` checks a complete new-world GROUPS inspection against
catalog file count, original definitions/references CRCs and active root count.
Full graph application still independently binds names/checksums, file-zero map
path, resolves children/assets, checks cycles/transforms and recomputes both
GROUPS CRCs. It is the required graph gate. An initial snapshot match alone does
not check every file identity or authorize rendering. Incremental roots may
legitimately differ from the exported root snapshot and require the graph gate.

Limits: 32 MiB borrowed input, 32 MiB ownership per catalog (64 MiB prior plus
candidate), 1,024 files, 65,536 aggregate slots/non-null definitions, 262,144
aggregate child edges, 4 MiB per record. The shared decoder additionally admits
at most 16,384 children in a single definition. These are admission policies,
not original engine maxima. Existing graph caps of 4,096 definitions/16,384 total
children remain unchanged and can reject a successfully prepared catalog.

CRCs cover names and the first child's name for roots. They do not authenticate
transforms, geometry, metadata, the producer or asset bytes. The integration
owner must bind independently verified source/provenance and actual imported
asset generation/pins, provide qualified asset callbacks, and own deployment.
No supplied source fixture constitutes an authenticated server capture.

## Qualification and remaining deployment

```sh
python3 native-android/engine/scenecatalog/check.py --source-root . --sanitize \
  --output native-android/engine/scenecatalog/evidence/qualification.json
```

The check executes hash-pinned original producers from
`replication/groups-source-pins.json` without function-body edits. It preserves
`catalog_fixtures.h` with `--fixtures-output`; `--ndk` plus `--android-output`
builds arm64-v8a and x86_64 standalone binaries and records both source and
fixture hashes. Build receipts do not claim Android execution.

Fixtures cover packed/aligned and modern/legacy original GROUPS, saved omitted
libraries, rich optional fields/matrices/properties/swaps, tombstones/null holes,
empty worlds, callback output failure and changed snapshot rejection, including an excessive
root-slot count with an inaccessible tracker pointer (rejected before output),
and the same count mutation during output (rejected before final CRC traversal). Separate
original `sendDef` calls are byte-compared with exported small-fixture records.
Native controls cover envelope mutations, CRC/identity/generation mismatches,
all envelope truncations, every logical bit truncation of a rich shared-decoder
record, exact ownership past input disposal, asset failure, every small candidate
allocation failure, source-only large counts and the unchanged graph limit.

The source-produced stress fixture has 508 files, 12,192 allocated records,
36,567 child edges and 33 roots; corresponding GROUPS omits every saved record.
On 64-bit host it owns 26,276,931 bytes; replacing it peaks at 52,553,862 bytes.
A five-child variant exceeds the unchanged 32 MiB ownership budget and rejects
while retaining the prior catalog. These are synthetic count/memory fixtures,
not recovered Atlas definitions. ASan and UBSan execute the native decoder;
legacy original producers execute unsanitized at O0 as in the existing oracle.

**Deployment remains open:** a catalog must be exported from the actual loaded
MapServer, verified and delivered to the client with matching imported asset
provenance. The authentic 508-file/33-root Thor GROUPS alone contains none of
these saved definitions. This module cannot manufacture that missing catalog.
A larger dynamically sized graph and qualified geometry/material/entity state
remain subsequent work. No accepted renderer/support/audio path is changed.
