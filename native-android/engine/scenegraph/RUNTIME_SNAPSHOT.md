# Original runtime snapshot diagnostic

`runtime_snapshot.c` consumes a retained `COHCAT01` catalog and a `COHRTS01`
sidecar produced at the same owner-thread startup boundary. It returns numeric
diagnostics and copied external-object identities. It never returns a graph,
borrowed source pointer, asset permit, received GROUPS, actor, or world-entry
claim. The accepted compact importer and application code remain unchanged.

The sidecar supplies data absent from the original catalog: every root slot,
including empty slots; original root transforms and their unchanged `sendMat4`
encoding; and separately observed `group_info.pre_alloc` objects referenced by
the regular catalog or roots. Future objects are not added to the original file
or definition-slot arrays. Their numeric source IDs can all be zero. The source
observer deduplicates actual pointers, requires canonical lookup to return each
same pointer, rejects ambiguous names, and verifies regular file/slot ownership
or exact `group_info.pre_alloc` ownership before emitting a record. The native
diagnostic independently rejects duplicate names, ordinary/future shadowing,
unreferenced extra records, and inconsistent root identities.

The only supported referenced targets are active named definitions. An absent
root slot is supported; a present root pointing to an inactive definition is
refused. This is deliberate: original `sendDef` omits inactive names/children,
whereas `groupInfoCrcRefs` can still incorporate an inactive root's first child.
Unreferenced inactive catalog slots and holes retain their original identities.

## Version 1 format

All integers and IEEE754 float bit patterns use explicit little-endian bytes.
No ABI structs, bitfield layouts, pointers, implicit padding or trailing bytes
are accepted. Names contain printable ASCII and a final NUL; names are limited
to256 bytes including the NUL. Object names have no directory separators. A
library path is an independent source lookup observation, not an asset permit.

The80-byte header starts with `COHRTS01`. Its u32 fields at offsets8..60 are:
version1, header bytes80, total bytes, asset generation, catalog bytes, file
count, allocated slot count, allocated definition count, regular child count,
root slot count, active root count, external object count, definition CRC and
reference CRC. Bytes64..79 are zero. The header counts/CRCs must exactly match
the retained catalog, except root slots and external objects which the catalog
does not contain. Limits:16MiB sidecar,65,536 root slots,64 external objects,
4MiB individual external `sendDef`,262,144 total regular+external child links.

Each root has a32-byte header: source root slot, present, kind, file index,
definition slot or external ordinal, name bytes, matrix wire bits, matrix wire
bytes. Roots appear once in ascending slot order. Absent roots have present0,
kind0, file/slot `UINT32_MAX` and zero lengths. Kind1 identifies a regular
file/slot; kind2 uses file `UINT32_MAX` and a separate external ordinal. Present
roots append name,48 bytes of raw source matrix and original byte-aligned
`sendMat4` bytes. Matrix bodies are bounded to256 bytes, consumed completely and
finite. Translation must equal the original source values; basis elements allow
2e-6 relative tolerance for original/native trigonometry, with absolute floor
2e-6. The raw matrix is retained in the authenticated sidecar even when this
numerical comparison permits a small compiler difference.

Each external record has a36-byte header: ordinal, original ID, ownership bits,
model-present, name bytes, wire bits, wire bytes, bounds-lookup-found, library
path bytes. Ownership bits0..3 mean definition pre_alloc, file pre_alloc, file
equals global pre_alloc, and original name lookup returns the same pointer;
all four must be set and no other bit is accepted. Record bodies are live bounds,
scratch lookup bounds, name, optional path and unchanged aligned `sendDef`.
The scratch lookup never targets a live definition. Each60-byte bounds block is
13 F32 values (min/max/mid, vis_dist/radius/lod_scale/shadow_dist), recursive_count,
and26 flags in original `GroupBoundsMembers` declaration order. A lookup miss
requires zero scratch bounds. Live bounds and successful lookup bounds remain
separate observations; matching names do not justify changing live bounds.

## Admission and accounting

The caller supplies independently trusted SHA256 pins for both byte spans and
nonzero source/run identity digests, then a SHA256 callback. The parser verifies
the byte pins; it does not establish the external source/run provenance. The
coordinator must verify the source identity, run identity, exact exporter PE,
runtime inventory, cleanup receipt and same-boundary export before interpreting
the result as an original-runtime snapshot. A matching checksum alone is never
sufficient. The original catalog is preserved; any fresh comparison witness is
stored separately and cannot silently replace it.

Two complete streaming catalog walks construct a compact diagnostic index with
original file/slot order. Future records use a separate ordinal space. Original
definition CRC is verified over the complete catalog; original reference CRC
is recomputed in root-slot order from canonical root name and first child's
canonical name. CRCs omit transforms and most metadata, hence the independent
byte pins and matrix checks. DFS starts only at observed roots and validates
cycle/depth bounds on that closure. Unreachable corpus cycles may remain;
`complete_source_name_closure` is not whole-corpus cycle validity. All missing
name references must nevertheless resolve to captured source records.

One bounded pool holds file/slot/name/edge indexes. Accounting includes both
input spans, the pool, one decoded record, output report,128KiB diagnostic stack,
64KiB streaming stack and caller retained bytes. The standalone host harness
reserves another256KiB for its report copies, SHA provider and test control
scratch. These are named ownership reservations, not allocator metadata or
process RSS. Allocation failure, cancellation, malformed input, excess depth,
checksum disagreement or incomplete ownership leaves output byte-for-byte
unchanged and releases all candidate allocations.

## Qualification and use

`tests/runtime_matrix_bridge.c` includes the unchanged qualified scenegraph
implementation and exposes its private matrix reader only to this standalone
binary. It is compiled instead of a second scenegraph object. No decoder grammar
is copied and no production API or application build is changed.

Run `check_runtime_snapshot.py --source-root REPO --output receipt.json
--sanitize`. It executes Worker A's original-source producer fixtures and the
native release/ASan/UBSan suites, binds all source/fixture/binary hashes, checks
negative inputs, exact budget boundaries, cancellation and every allocation
failure, and confirms cleanup. Legacy original bit-packing is a trusted O0
producer; the native diagnostic is separately sanitized. Host OpenSSL supplies
SHA256. This host-only diagnostic does not require an APK or Android rebuild.

To audit a preserved real pair after server cleanup, additionally pass
`--catalog`, `--snapshot`, `--catalog-sha256`, `--snapshot-sha256`,
`--source-sha256`, `--run-sha256`, and `--asset-generation`. The command accepts
all actual-capture arguments together or none. Exact hashes are checked before
and after execution. Source/root/future fixture success cannot establish which
of the authentic seven catalog references is reachable: that answer requires
the separately admitted actual sidecar. Assets, matching live GROUPS generation,
complete character updates and renderer publication remain independent gates.
