# Rank 4 owned PhysX stream prerequisite — nonshipping

This continuation adds an isolated byte-stream prerequisite under
`database/map-startup-physics/qualification/`. It does **not** replace
`NwSharedStream`, change MapServer/Game, build native binaries, alter an APK or
asset pack, or claim reduced startup time. Published 0.13.32 remains the device
baseline. Cooked-mesh caching and Atlas/Kings Row collision parity remain
unimplemented and unqualified.

The stock `Common/NovodeX/NwSharedStream.cpp` uses process-global storage,
unchecked read extents, and a shared capacity/read cursor. The stock callers in
`NwWrapper.cpp` include triangle cook/export, serialized triangle load, immediate
cook/load, and convex cook/load. Replacing a class name alone would leave caller
ownership, failed SDK returns, cooking lifetime, and export copying unresolved.

## Implemented prerequisite

- `owned_bounded_stream.h` is an independent, C++03-compatible owned core with an
  explicit per-stream capacity cap, separate capacity/used/read cursor, and a
  scoped release using a paired allocator. Copy construction and assignment are
  inaccessible; each instance owns its allocation. No global scratch storage or
  borrowed input ownership exists.
- `nx_owned_bounded_stream.h` derives from the **actual unchanged vendor**
  `NxStream.h`, with vendor `NxSimpleTypes.h`/`Nx.h` types and signed wrappers.
  Fixture compilation binds to the checked-in PhysX SDK headers, not a substitute
  interface or recreated SDK types. Header version is 2.8.4; executing the runtime
  DLLs with those headers remains a separate gate.
- Allocation/growth failure leaves data, used extent, and capacity intact, sets a
  sticky error, and never frees the original buffer prematurely. Growth copies
  only initialized bytes. It does not initialize unused capacity. Primitive and
  bulk transfers preserve the current host's native byte representation, as the
  stock `memcpy` stream does. No endian/geometry/cooking transformations occur.
- The loaded constructor accepts a signed byte count and rejects negative sizes,
  null positive-length input, and inputs above the cap before dereferencing input.
  Read/write bounds use subtraction before arithmetic. Zero-length buffers accept
  null only in the appropriate mode. Invalid allocator pairs are rejected.
- `beginRead()` is a single write-to-read transition. A cooking failure cannot be
  revived; a read stream cannot be rewound or switched back to writing. The first
  error survives all subsequent operations.
- Failed bulk reads preserve destination and cursor. They do not zero-fill an
  SDK-provided length, which could amplify malformed-input work or overwrite a
  short destination. Failed scalar reads return initialized zero and preserve the
  error. Scalars are **not** a substitute for caller validity checks.
- Self append accounts for allocation relocation and permits only initialized
  source bytes. One-past-capacity pointers and uninitialized tails are rejected.

The cap bounds each retained allocation, **not total RSS**. Atomic growth briefly
holds old and replacement buffers: their combined capacity can reach less than
or equal to twice the cap, excluding allocator bookkeeping, caller input, SDK
mesh/cooking allocations, and other streams. Loaded streams own a copy of input.
No RAM savings are measured. A production cap needs measured per-mesh lengths and
an aggregate budget; this prerequisite deliberately does not choose one.

The allocator contract requires nonthrowing allocation/release callbacks with
correct alignment, a fresh disjoint allocation, and a null return on allocation
failure. Caller buffers must supply the claimed accessible extent; a raw pointer
API cannot verify arbitrary external memory. Different streams can coexist;
concurrent access to one stream requires caller synchronization.

## Mandatory SDK caller behavior before integration

`NxStream` has no read/write error return. Every real producer must reject failed
cooking **or** an invalid stream before exporting bytes or calling `beginRead()`.
Every real mesh consumer must check read mode, valid source identity/length, and
stream validity **before** `createTriangleMesh` / `createConvexMesh`, then check
validity **after** the SDK returns and reject a null mesh. A nonnull SDK mesh
returned after stream failure must be released through the correct SDK mesh
release API before returning failure. Never create a shape or increment mesh
counts for a rejected mesh.

Post-return checking cannot make an SDK decoder safe against arbitrary corrupt
input: the SDK may assert, hang, or fail before returning after receiving a scalar
zero or an unchanged bulk destination. A future cache therefore needs bounded
authenticated envelopes, exact expected bytes, and a prevalidated format/source
contract **before** invoking SDK code. The host mock consumer tests the caller
pattern only; it is not PhysX mesh execution or adversarial SDK qualification.

Cook/export paths must also check `streamOutput`/`streamSize`, bounded conversion
to legacy `int`, export-allocation failure, and output ownership. All
`NxInitCooking`/`NxCloseCooking` calls need an audited lifetime pair. The vendor
header states that initialization resets cooking parameters and uses a limited
saved-state stack; snapshots must come after successful initialization and
parameter setup. These caller changes are not made in this pass.

## Exact identity required for a future cooked-mesh cache

No cache key/reader/writer is implemented here. Before a cache can replace stock
cooking, its immutable certificate must bind all inputs below. A filename, map
ID, SDK version string, geometry count, or timestamp alone is insufficient.

| Identity | Required bound inputs |
| --- | --- |
| Effective geometry source | Effective provider/generation certificate and exact donor/member hashes; loader/transformation source pins; mesh kind; byte order and scalar widths; exact vertex/index bytes consumed; counts, point/triangle strides, index width, winding, descriptor flags; any scale/coordinate transformations before cooking |
| Triangle descriptor | All effective `NxTriangleMeshDesc`/`NxSimpleTriangleMesh` fields including optional material-index presence/bytes/stride, height-field axis/extent, convex-edge threshold, and PMap absence or exact content; encode individual values, never hash padded pointers/struct memory |
| Convex descriptor | All effective `NxConvexMeshDesc` fields, generated-hull flags and inflation/normal/index settings, exact points/triangles and their counts/strides; triangle and convex identities stay distinct |
| Cooking configuration | Successful initialization contract; observed `NxGetCookingParams()` target platform, exact `skinWidth` float bits, `hintCollisionSpeed`; `NxPlatformMismatch()` result; all caller parameter/flag branches and their source hashes |
| Producer and consumer | SDK numeric version plus exact cooking/loader/SDK DLL and linked-library hashes, PE architecture/ABI, build/source receipt, serializer/stream schema, target platform/endian, and generated cooked-byte length/hash; actual loaded modules must match the receipt |
| Scene/shape parity | Preserve local/global transforms, collision groups/flags, material mapping, shape skin width, actor density/response, and scene parameters. They may sit in a separately bound shape recipe, but changing them cannot be accepted as cooking-cache parity |

Materialization should be private, bounded, atomic, and scoped to the verified
generation. A malformed/mismatched cache must be rejected before SDK decoding,
with a measured stock-cooking fallback only after owned cleanup. This prerequisite
provides no fallback, durable cache, certificate, or global SDK synchronization.

## Qualification performed here

Command:

```sh
python tools/test_map_startup_bounded_stream.py --evidence database/map-startup-physics/qualification/host-prerequisite-evidence.json
```

Result: **25 tests, zero failures/errors/skips**, on the 64-bit Linux host with
GCC 13.3.0, C++03, and the real vendor headers. Ten fixture groups run normally
and with ASAN/UBSAN instrumentation; five compile-rejection tests cover core and
adapter copy/assignment plus absence of an unbounded default constructor.
Coverage includes independent ownership, every primitive and bulk byte parity,
signed wrappers, short inputs, overflowing lengths, exact/zero caps, both initial
and growth allocator failures, null/negative sizes, mode separation, sticky
errors, self append, one-past-buffer input, bounded growth, unchanged failed bulk
destinations, and before/after/null-mesh checks in a clearly labeled mock consumer.

LeakSanitizer cannot inspect this managed host's `/proc/<pid>/task` and initially
failed at process exit with its ptrace limitation. ASAN/UBSAN then passed with
**LeakSanitizer disabled**, explicitly recorded in the evidence. Paired allocator
fixtures account for every owned allocation/release and reject double release;
this does not claim a process-wide leak scan. On a compatible host, require the
additional scan with `--leak-sanitizer`; a requested scan failure is not silently
downgraded.

The retained evidence includes source/header hashes and marks SDK cooking, SDK
mesh creation, Win32/Wine, collision, Thor, and shipping integration **false**;
startup seconds and RAM savings are null.

## Gates remaining before deployment

1. Independently review the core/adapter and audit every stock triangle/convex
   caller, cooking lifetime, failure cleanup, ownership/export contract, and
   exact caps. Add genuine SDK error cases; host mock checks cannot close them.
2. Compile the adapter with the actual Win32 MapServer toolchain and real linked
   PhysX 2.8.4 components. Execute producer and consumer under the retained Wine
   runtime, compare stock/new cooked output bytes where deterministic, and record
   exact loaded module hashes, descriptor/configuration values, malformed input
   rejection, allocator pressure, and object release counts.
3. Build a separate generation-bound cache/certificate only after stream/caller
   safety qualification. Verify all current triangle and convex cache inputs,
   invalidation after donor/cooking/source changes, corruption rejection, atomic
   publication, interruption/cleanup, and bounded fallback. This is additional
   work, not part of the 25 host tests.
4. Qualify Atlas and actual Map 5/Kings Row collision parity: deterministic mesh
   inventory and geometry, raycasts/sweeps, ground/stairs/walls/doors, contact and
   spawn placement, movement/combat, monorail arrival and return, repeated
   save/reopen, and no falling-through/clipping change. Preserve graphics and
   current GPU/controller/persistence behavior.
5. Measure on the physical AYN Thor using the .32 baseline: individual stream
   change first, then cache change, then combined certificate optimization. Retain
   fresh/warm preparation time, actual native-ready and usable-world timings,
   per-stage/mesh counters, failures, FPS, temperature, peak and settled RAM.
   Require repeatable startup improvement without collision, saved-character,
   cleanup, stability, or RAM regressions before any APK release. No sub-30-second
   claim follows from this host prerequisite.
