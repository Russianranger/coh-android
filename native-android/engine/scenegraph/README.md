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

`CohSgImportFn` is implemented by `coh_scenecatalog_file`. Qualification imports
source-produced synthetic catalogs through this real decoder; no matching live
Atlas catalog has been captured. Each catalog must match its exact original
filename, bounds checksum, asset generation and all original definition slots.
It includes allocated tombstones and excludes null slots. The catalog may not
infer definitions merely from wire references. The bounds checksum is checked
against the importer receipt; this module does not recompute it from original
`.geo`/bounds bytes.

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

The resolver admits at most 1,024 files, 65,536 definitions, 65,536 sparse root
records, 262,144 child edges and depth 128, subject to a stricter 32 MiB candidate
allocation limit. Definitions and roots grow dynamically; known catalog counts
can reserve exact capacity once. Original file/slot identity, root identity and
case-folded names use separately owned indexes with at most half occupancy.
Every insertion/lookup admits at most 256 probes; pathological collision chains
reject transactionally instead of allowing quadratic scans. In-place heapsort
restores original checksum order in O(n log n) time without libc temporary
allocations. DFS scratch is dynamically bounded and freed before publication.
All preparation remains off the render thread. Immutable index lookups allocate
nothing and invoke no callbacks.

Use `coh_scenegraph_apply_bounded` for catalog integration. Set
`CohSgBudget.external_bytes` to the catalog report's `owned_bytes`, any retained
catalog envelope, all retained asset generations/views and external callback
scratch/reservations. The API adds GROUPS input bytes, old graph ownership and a
64 KiB internal stack reserve, then admits every candidate allocation including
simultaneously live growth arrays/indexes and DFS scratch under a caller-selected
limit of at most 96 MiB. Callbacks must not retain allocations beyond their
reservation. Graph output is immutable and must be serialized during publication;
old graph is freed only on complete success. Reserve definitions from the exact
catalog count (plus any qualified new slots), and roots from its source root
count; hints never replace count/identity/checksum validation. Without hints,
geometric array growth may correctly refuse a large graph whose final size
alone fits. The legacy `coh_scenegraph_apply` wrapper reserves zero external
bytes and is compatibility-only, not a complete working-set admission contract.

Memory receipts count allocation payload and reserved external/scratch bytes,
not allocator metadata, GPU allocation or whole-process RSS. Account these
separately in the caller's process budget. Host GCC `-O2 -fstack-usage` measures
96 bytes per recursive visit, at most 129 frames including a rejected depth,
and 1,904 bytes for the apply frame; the 64 KiB internal reserve exceeds that
measured path. Android compiler frames require their own qualification. Caller
and arbitrary importer callback stack usage belong to the external reservation.
Shrinking/reordering file tables or changing same-index identities during an
incremental update requires a new-world update and rejects before cloning. No
imported strings become filesystem paths.

## Dynamic stress qualification

The source-produced stress fixture has 508 files, 12,192 allocated definitions,
36,567 child links and 33 roots. These are synthetic original-source inputs, not
a captured Atlas world. The fixture generator independently invokes unchanged
original `sendDef` for **all 12,192 records** and compares exact bytes, then runs
the actual catalog importer and graph resolver against the original GROUPS footer.
Every file/slot/name/root index, all child resolutions, tombstones, CRCs and
owned lifetime after catalog release are checked. Full replacement retains the
old graph until success. Budget underflow/overflow, a limit one byte below the
observed peak, invalid hints and representative large allocation failures leave
the published object and reader unchanged. Existing small-world tests exhaust
every candidate and clone allocation failure and retain incremental coverage.

On 64-bit host builds the stress graph owns **26,806,591 bytes**. Candidate heap
peak is **26,843,167 bytes**. The complete replacement reservation (catalog,
retained envelope, old graph, candidate peak, GROUPS input, internal stack)
peaks at **81,706,049 bytes**, below 96 MiB. These are deterministic ownership
measurements, not process RSS or Android latency measurements. No authentic
world, imported material semantics or render authorization is inferred.

## Qualification

`check.py` reuses the accepted hash-pinned original producer oracle (16 source
files, 41 functions). Eight additional trusted-input cases exercise an actual
original-produced baseline before an incremental deletion and 1,023-byte property
values. Original function bodies stay unchanged. The receipt hashes both the
extension and generated fixture header. All 52 original graph fixtures run in packed/aligned
and modern/legacy-command variants; 44 resolve, four base headers are unsupported,
and four deliberately cyclic/depth-exceeding source graphs reject.

The native harness additionally verifies exact geometry/texture/swap identities,
original source matrix outputs, forward/saved definitions, CRCs, incremental
deletions, malformed/truncated inputs, missing/canceled catalog/asset loads,
wrong generations/checksums, duplicate identities, imported nonfinite matrices,
prefix identity mismatch, wrapped per-allocation failure rollback, ownership
past input/catalog lifetime, noncommuting composition, aliasing and finite
overflow. The same original fixtures and large stress controls compile into the single
standalone executable used for release, ASan, UBSan and Android qualification.
Local release/ASan/UBSan run **124,804 checks per mode**, including 34 exhaustive
small allocation failure points and 18 large rollback/budget controls. LSan cannot enumerate `/proc` threads in this host's
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
claim Android emulator execution or physical Thor acceptance. This continuation
host has no CMake/CTest or Android NDK executable, so the direct compiler driver
is qualified locally; CMake and Android builds/execution remain hosted gates. Existing Combined
0.1.7 bytes remain unchanged; the new module is not linked into that APK.

## Original definition metadata boundary

`coh_scene_metadata.h` adds allocation-free, transactional inspection of a
validated graph's **complete retained original definition body**. It returns a
caller-owned value with scene/asset generation, original file/slot identity,
raw LOD/fade/collision/tracker flags, light/fog/tint colors, cubemap settings,
sound fields, volume/beacon values, texture names, alpha, geometry identity,
swap count, gameplay hiding and a bounded property span. It verifies exact
record consumption, finite scalars, identity and explicit geometry/texture/swap
agreement; output stays unchanged on failure. Missing original wire records
reject instead of inferring metadata from an offline catalog.

Properties remain borrowed views over the immutable graph's owned wire bytes.
`coh_scenegraph_property_begin` and `coh_scenegraph_property_next` copy one
bounded property into caller-owned storage (64-byte name, at most 4,095 value
bytes plus terminator). Cursor and output commit together. These APIs retain
wire order and duplicates and do not claim original stash-table insertion or
replacement semantics. Retain the graph until property iteration completes.
All metadata/property preparation belongs off the render thread; account for
caller output/workspace in external memory reservations. No per-definition
allocation or graph-layout expansion was added, so stress ownership is unchanged.

The parser preserves `receiveDef`'s **raw wire conventions before client fixups**:
absent values are zero, light then fog then tint writes overwrite the same
color buffer in source order, tint writes only RGB and preserves alpha bytes,
`has_alpha` remains distinct from an alpha value of zero, and empty sound-script
names remain empty. It does not guess the meaning of a zero LOD distance or
convert byte colors into renderer-ready lighting.

`unresolved_requirements` deliberately records remaining adapter obligations.
Every live definition requires bounds/LOD qualification; geometry also requires
original model/trick qualification. Textures, composite swaps, properties
(including `TexWordLayout`/parameters), type-dependent FX, lighting, fog,
cubemaps, sound, volumes, beacons and visibility each retain explicit obligations
when present. A successful metadata read does not clear any of these obligations,
validate asset bytes, pin a loader generation or authorize rendering. Those steps
still require exact original loader/material/bounds behavior on the captured
asset generation. In particular, `setClientFlags`, `getGeo`, `groupSetTrickFlags`,
`groupSetDrawInfo`, `groupSetBounds` and `groupSetVisBounds` are not executed here.

Fourteen packed/aligned fixtures execute **unchanged original `sendDef`**, then
independently read the source `GroupDef` fields to compare 50 scalar fields,
seven strings and eight color bytes. They cover all transmitted metadata
branches, default/empty cases, ambient-only/light-only data, zero optional
values, empty sound-script names and a `TexWordLayout` property. The original
`receiveDef` source is hash-pinned and audited, **not executed by this oracle**.
The metadata controls add 34,710 checks, including 33,623 every-bit truncations,
property end/rollback, generation/identity refusal, and the existing 1,023-byte
property fixture. Release, ASan and UBSan each pass **159,514 total checks**;
see `evidence/metadata-qualification.json`. Android execution remains a separate
hosted gate. Host GCC `-O2 -fstack-usage` reports 7,024 bytes for metadata decoding
and 4,272 bytes for property iteration, with no recursion or allocation.


## Byte rollback test portability

The follow-up `evidence/metadata-rollback-qualification.json` retains release,
ASan, UBSan and a test-only reader-padding control. Each passes 193,219 checks,
including the same 33,623 metadata bit truncations; higher check count separates
status and byte-preservation assertions and adds explicit invalid-input rollback.
Every byte rollback comparison now snapshots object representation with `memcpy`
immediately before the rejected operation. It does not compare padding across
successful struct assignments or successful decodes.

The original Android qualification at `140ee62d` stopped at the combined metadata
identity/status-and-bytes assertion. A controlled host reproduction changes only
padding in otherwise identical valid readers: the original test rejects the
correct `COH_STATE` result because it compares against bytes from a previous
successful decode. The revised test passes this control without production code
changes. See `evidence/metadata-rollback-control.json`; this identifies a real
test defect but does not independently establish the original emulator's status
or changed byte offsets. Corrected Android execution remains a separate gate.
