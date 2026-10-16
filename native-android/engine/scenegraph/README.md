# Owned GROUPS topology preparation

This additive module prepares a bounded, owned topology snapshot after the
accepted `coh_rep_groups` structural inspector. It does **not** modify Combined,
the accepted inspector, network/session interfaces, support-client work, or any
renderer. It sends no READY, RECEIVED_CHARACTER or other packets. A successful
snapshot is not authority to render a live world or an offline preview as the
selected character.

Implemented behavior:

- Original implicit server file order `1..N-1,0`, full path and bounds-checksum
  identity, new-world prefix/file-zero identity agreement, file index stability.
- Mandatory generation-specific imported file catalogs. Saved definitions that
  `sendGroupFile` deliberately omits must come from that catalog. A missing file,
  definition or explicit asset identity rejects the whole candidate.
- Owned definition IDs, allocated tombstones, child references, sparse root IDs,
  raw and packed original matrices, geometry and texture names, texture swaps,
  and an exact owned wire span for every transmitted definition's metadata.
- Definition/root names resolve after the entire update, including forward
  references and case-insensitive ASCII basename lookup. Ambiguous names, empty
  or unsupported identities, missing dependencies, cycles and excessive depth
  reject transactionally. Non-ASCII names are explicitly unsupported.
- Source `groupInfoCrcDefs`, `groupInfoCrcRefs` and active-root-count equivalence,
  including original Crypto++ digest byte order, allocated `NAMELESS` tombstones,
  first-child contribution, and omission of null original slots.
- Incremental file/definition/root changes and deletions on an owned cloned
  candidate. A failed import, decode, allocation, resolver, asset identity or
  checksum leaves both prior graph and reader cursor unchanged. New-world
  replacement uses the same transaction. Publication requires sequential graph
  generations; incremental updates require the same asset generation.
- Original packed YPR/scale/position reconstruction and original column-basis
  matrix composition, with finite-result and aliasing checks.

## Exact limitations and integration boundary

`CohSgImportFn` is an interface for a future qualified importer, **not an existing
live imported-asset adapter**. The tests supply synthetic trusted catalogs. Each
catalog must match its exact original filename, bounds checksum, asset generation
and all original definition slots. It includes allocated tombstones and excludes
null slots. The catalog may not infer definitions merely from wire references.
The bounds checksum is checked against the importer receipt; this module does
not recompute it from original `.geo`/bounds bytes.

The existing support module `engine/offline-world/tools/prepare_zones.py` reuses
original source-map parsing, but its pinned i24 offline subset does not establish
the same file IDs, slot order, bounds checksums or complete current imported
Ouroboros definitions. Reuse its parser/asset-loader ownership machinery where
qualified; do not relabel its partial manifests as these catalogs.

The two footer CRCs cover names (and first-child name for root CRC), **not**
transforms, geometry bytes, material semantics or complete packet integrity.
Explicit model/texture/swap strings are retained and checked through
`CohSgAssetFn`; dynamic TexWord properties, inherited tricks, LOD, sound, lighting
and all complete render material semantics still need an adapter. Their exact
wire metadata stays owned rather than silently discarded. Neither the callback
nor these CRCs is proof of complete geometry/material admission.

The next integration work is to prepare exact imported catalogs and asset
receipts off the render thread, retain actual loader generation/pins, interpret
remaining semantic metadata and produce immutable qualified renderer/collision
pages. The client still requires separately validated complete entity/character
state and server-authoritative position. No renderer-facing live-ready flag is
exposed here.

Call `coh_scenegraph_apply` synchronously on the scene owner thread immediately
after the normalized GROUPS command; pass the existing reader representation and
bounded inflated payload. The input is borrowed during the call. All retained
fields are copied. Callbacks must not mutate the old graph or publish side
effects; they may return cancellation or missing dependency errors. The owner
must serialize readers while swapping snapshots: this function frees the old
snapshot on success and is not an RCU/multithreaded publication primitive.

The resolver admits 1,024 files, 4,096 definition slots, 4,096 sparse root records,
16,384 total child edges and depth 128. Each snapshot is capped at 32 MiB including
all allocations; the prior and candidate snapshots coexist during preparation,
so combined worst-case graph ownership is 64 MiB. Work is finite under these
limits; name resolution currently uses bounded linear lookup and should stay
off the render thread. Shrinking/reordering file tables and same-index identity
changes within incremental updates require a new-world update and are rejected.
No imported strings become filesystem paths here.

## Qualification

`check.py` reuses the accepted hash-pinned original producer oracle (16 source
files, 41 functions). Eight additional trusted-input cases exercise an actual
original-produced baseline before an incremental deletion and 1,023-byte property
values. Original function bodies stay unchanged. The receipt hashes both the
extension and generated fixture header. All 52 fixtures run in packed/aligned
and modern/legacy-command variants; 44 resolve, four base headers are unsupported,
and four deliberately cyclic/depth-exceeding source graphs reject.

The native harness additionally verifies exact geometry/texture/swap identities,
original source matrix outputs, forward/saved definitions, CRCs, incremental
deletions, malformed/truncated inputs, missing/canceled catalog/asset loads,
wrong generations/checksums, duplicate identities, imported nonfinite matrices,
prefix identity mismatch, wrapped per-allocation failure rollback, ownership
past input/catalog lifetime, noncommuting composition, aliasing and finite
overflow. It runs identically under release, ASan and UBSan and as Android
standalone executables. LSan cannot enumerate `/proc` threads in this host's
ptrace environment; leak checks use wrapped allocation ownership counters and
failure injection at every candidate/clone allocation instead.

```sh
python native-android/engine/scenegraph/check.py --source-root . --sanitize \
  --output /tmp/scenegraph-host.json \
  --ndk /path/to/android-ndk-r28c --android-output /tmp/scenegraph-android
cmake -S native-android/engine/scenegraph -B /tmp/scenegraph-cmake \
  -DCOH_SCENEGRAPH_TESTS=ON -DCOH_SCENEGRAPH_SOURCE_ROOT="$PWD"
cmake --build /tmp/scenegraph-cmake
ctest --test-dir /tmp/scenegraph-cmake --output-on-failure
```

Android receipts distinguish builds from execution. The local receipts do not
claim Android emulator execution or physical Thor acceptance. Existing Combined
0.1.7 bytes remain unchanged; the new module is not linked into that APK.
