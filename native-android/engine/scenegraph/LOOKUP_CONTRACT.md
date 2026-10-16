# Immutable library and model lookup index

`coh_scene_lookup` is an additive name-table preparation boundary. It maps an
original definition model name through exact loaded-library file/row and GEO
model slots supplied by the caller. It neither discovers those associations
from filenames nor authenticates an input manifest. No actual loaded-library
manifest was available for this qualification. Capturing saved definitions does
not supply the separate model/library/trick/material mapping.

Every successful result keeps `unresolved=31`: provenance, GEO payload/model
validation, tricks, materials and original bounds remain obligations. A caller
claim of verified input does not clear those bits. No scenegraph asset callback,
bridge, renderer, actor, JNI, ACK or APK is activated by this index.

## Source behavior

The host oracle extracts and executes thirteen unchanged original functions:
`groupGetPublicName`, `groupNameIdx`, `objectLibraryFileCount`,
`objectLibraryEntryFromIdx`, `objectLibraryEntryFromObj`, `groupModelFind`,
`modelFind`, the five model comparison/search/sort helpers, and `changeFileExt_s`.
The complete source files and extracted bodies are hash-pinned. The oracle uses
explicit synthetic library rows, GEO headers, model ownership, a case-insensitive
ASCII Stash fixture and a `geoLoad` fixture. Real StashTable storage, archive I/O,
GEO decoding, graphics initialization, source asset loading and tricks are not
executed. Historical functions run on bounded trusted inputs at `-O0`; ASan and
UBSan qualify the new native implementation, not historical pointer operations.

The supported name domain is nonempty printable ASCII, at most 998 bytes.
Non-ASCII names refuse admission because locale-dependent original comparison
has not been qualified. The source rules are preserved in this order:

1. Strip the directory using `/`, as `groupModelFind` does. Backslash remains a
   model-name character at this boundary.
2. For the library query only, if the resulting name ends in `&`, remove its
   final underscore suffix. Then remove the first `__` trick suffix.
3. Find the exact case-insensitive library key and retain its original row and
   file slot. The supplied GEO path must match original extension replacement,
   including dot/directory behavior; paths are not resolved against a filesystem.
4. Search that file's model table using the **original model query**, cutting
   only its first `__` suffix. The clone suffix remains part of this key. Compare
   the full base length as well as case-insensitive bytes. Return the complete
   original model name, including its original trick suffix.

Equivalent library keys, equivalent model bases within one GEO and duplicate
case-insensitive GEO paths are rejected, even when the original implementation
could choose an arbitrary first row. Numeric slots remain exact and can contain
holes; ordered input rows reject duplicate slots. Missing models never fall
back to another file or to a prefix match.

## Ownership, publication and memory

The caller supplies source/inventory/manifest digest identities, map and asset
generations, exact file/library/model rows, and expected payload digests. These
are externally established assertions. A nonzero digest is not proof that any
bytes were hashed. `coh_sg_lookup_asset_matches` compares a subsequently acquired
asset identity with the recorded identity; it neither hashes payload bytes nor
clears unresolved flags. Actual source inventory verification and immutable asset
pins remain external responsibilities.

Build performs bounded preflight and one zeroed allocation containing copied
rows, strings and bounded indexes. It borrows no input after return. File lookup
uses binary search; library/model lookups use indexed case-folded keys with at
most 256 probes. Duplicate/ambiguous or excessive-collision inputs fail closed.
All preparation belongs off the render thread. Lookup performs no allocation,
I/O or callbacks, and returns copied names/identifiers that survive retirement.

Native limits are 8,192 files, 65,536 library rows, 262,144 model rows, 16 MiB
owned allocation payload and 96 MiB aggregate reservation. These are admission
ceilings, not measured real-world requirements. The reservation includes input
arrays and referenced strings, the old and candidate indexes, an 8 KiB internal
stack allowance, and caller-declared retained bytes. Input allocation slack,
other retired indexes, graph/catalog generations, decoded assets, GPU resources,
external evidence and scratch must be declared by the caller. Allocator metadata
and process RSS are not measured. Count/string bounds prevent 32-bit overflow;
budget subtraction happens before allocation. Current GCC host `-O2` reports
480-byte build and 2,560-byte lookup frames; the reserve is conservative and is
not a measurement of Android/libc internals.

Output/control objects and borrowed input must be disjoint, as explicitly
required by the public API. The index is opaque. Build failures leave output and
memory reports unchanged and release all candidate allocations. Fresh builds
start at generation one; replacement requires the exact next generation and
retains the complete prior binding. Serialized publication compares that full
binding, preventing a candidate prepared for one owner from replacing another
owner with the same numeric generation. Publication returns the old allocation
without freeing it. The caller must acknowledge every borrower before retirement.
Cancellation discards the independently prepared candidate. No concurrent atomic
mailbox or resource-pin mechanism is implied.

## Qualification and integration

`check_lookup.py --sanitize --output PATH` independently executes 526 original
lookup cases and nine original extension cases. Native controls cover 32,768
library/model rows, duplicates, clone/trick/case semantics, cross-owner binding,
missing rows, malformed names, digest/generation mismatch, 2,000 deterministic
random malformed names, a 257-collision refusal, exact budget admission, old and
candidate coexistence, allocator failure, deep-copy lifetime, publication,
retirement and cancellation. Allocation wrappers require no live allocations.

The existing `check.py` graph qualification includes these tests in the same
`coh_scenegraph_test` executable for host release, ASan, UBSan, the reader-padding
control and optional Android builds. `lookup_fixtures.h` travels beside
`scenegraph_fixtures.h`; host and ABI receipts bind its exact bytes through the
top-level `lookup_fixtures_sha256`. Android execution and physical acceptance
remain separate coordinator evidence. Shared CI/JNI integration is unchanged.

Use the opaque index additively. Do not replace existing graph asset callbacks
with name-table success or admit rendering from this result. Rollback consists
of retaining the previous index and discarding the candidate. Further compact
graph/catalog ownership work will use actual captured sizes; this checkpoint
does not increase the existing graph/catalog memory caps.
