# Uninstalled raw public bounds supplier and native import

`source_public_bounds.inc` adds a read-only bounded raw-prefix supplier, not a
hook, source mutation, installed capture or cache permission. It requires the
actual original GroupBounds and GroupDef declarations. Compile-time assertions
require sizeof(GroupBounds)==60, F32/int widths4 and exact named prefix offsets
for min/max/mid/visibility/radius/LOD/shadow/recursive_count in BOTH types. A
runtime byte-order check refuses big endian. These compile checks do not claim
that the host fixture is the actual Win32 producer ABI or capture generation.
Raw bitfield and padding bytes are copied directly from the actual def->min;
none are reconstructed, zeroed or canonicalized.

COHRBW01 has a96-byte little-endian header with version1/header96/total bytes,
original catalog generation, layout-contract1/raw-prefix60, exact48-byte COHCAT
header, file/slot/public counts and reserved0. Each file preserves original file
order and has24 bytes: index, original file.idx, observed bounds token, slotcount,
NUL filename bytes, reserved0, followed by filename. Each original slot has32
bytes: slot, original ID (MAX for hole), allocated, active, actual groupIsPublic,
NUL active-name bytes (zero for inactive/hole), raw bytes60 iff public, reserved0;
then name and exact raw prefix. All decisions including nonpublic entries remain
represented. File0 stays represented, but its token cannot be claimed recomputed:
the original writer returns immediately for file.idx0. Source preflight completes
before output; all callback bytes remain provisional until entire call succeeds.
Two passes detect count/size changes, but do not replace the exclusive stable
owner-thread prerequisite. Output is capped32MiB, slots65536/files1024.

`coh_public_bounds_create` retains the actual CatalogOwner, copies SHA-verified
input and validates embedded catalog header, every exact file/slot identity,
active name/public-selection decision and observed checksum token. It preserves
holes/tombstones, all public raw bits and original order. The native owner is
immutable/refcounted; getters borrow spans until last release. Constructor errors
leave prior owner/output/report unchanged, free partial allocations and retain no
new catalog reference. All named input/old/new/catalog/index/stack reservations
are admitted before allocation, bounded by32MiB per owner/96MiB aggregate.
Caller additionally charges other provider/digest/slack payloads in retained_bytes.

Current-byte token comparison independently follows the original raw prefix plus
non-NUL public-name Adler32 order/digest byte order; file0 refuses, token mismatch
refuses and zero is never replaced or normalized. A successful byte comparison is
NOT proof that the original cached token's computation generation is the current
source state. Raw SHA/run/catalog labels do not authenticate that chain. Native
ABI/source/cache/world flags stay0. Layout/build/source/run and same-boundary
original owner+quiet+eligibility+packet/receive evidence remain independently
required. No14346 authentic raw rows have been captured by these fixtures.

The host fixture executes unchanged original groupInLib/groupIsPrivate/
groupIsPublic and objectLibraryWriteBoundsFileIfDifferent. It compares emitted
raw spans directly against test-owned original-type member-prefix objects,
including high padding bits, and supplies eight cases including mixed-case/prefix library names, grp/private
names, tombstones/holes, matching/changed/zero observed tokens. Host layout assertions and source fixtures do not substitute
for an actual original Win32 build or runtime. This supplier is NOT yet inserted
into the private boundary helper or any source role; future combined capture
requires separate reviewed staging/ownership/sink integration. No capture/run is
performed or authorized by this preparation.
