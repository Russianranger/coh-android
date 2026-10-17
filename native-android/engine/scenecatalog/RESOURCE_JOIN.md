# Exact source owner, graph and resource observation association

`coh_resource_join` closes the source-only association gate deliberately left
open by the disposable resource capture driver. It does not resolve or admit
GEO bytes, materials, actors, client semantics or a live world.

The adapter checks immutable metadata from the actual opaque owners. Graph
catalog/snapshot/source/run hashes must equal the retained snapshot's binding.
The graph's borrowed byte addresses and extents must also equal the actual
catalog and snapshot owner spans. A new snapshot catalog-span getter prevents
two equal binding labels on distinct copied owners from hiding a second retained
catalog allocation or breaking lifetime accounting.

The original complete streaming catalog validator visits every file/slot in
original order. For each allocated record, the adapter checks the catalog owner's
indexed identity and exact raw wire span against the graph node. Every active
record consumes exactly one resource observation, matching regular file, slot,
original ID, canonical definition name, model-present flag and the complete
original geometry/model name byte for byte. Tombstones and holes consume no
resource rows and stay distinct. All external pre_alloc owners are then matched
in their captured ordinal order. Their graph node slot stores original ID, which
may be zero for every future; that value is never used as the external ordinal.
The original bounded sendDef decoder independently reads each future's ID/name/
geometry and compares it with both captured ownership and the resource row.
Missing, extra, reordered or changed rows fail the entire candidate.

The adapter copies and hashes the complete bounded COHRES stream and computes
per-record hashes only after owner matching. It exposes immutable ordered source
descriptors for the resource index. `coh_resource_join_match_index` uses copied
binding metadata and raw ordinal record views from a retained resource index to
prove that every joined observation was copied unchanged under the same source,
run, manifest and component generation. No supplied caller row identity can
replace these comparisons. The manifest/source/run receipt chain itself still
requires independent artifact admission before calling this adapter.

Catalog and snapshot references are retained through retirement. The graph is
borrowed and must remain alive/immutable through the join, including replacement
budget checks which inspect a prior graph. The adapter's queries use copied
mapping indexes, never source graph traversal or I/O. Before retiring the last
join, keep a separate original source-owner lease until graph retirement so its
borrowed inputs cannot disappear first. Resource-index input descriptors borrow
the join; the index copies them during preparation and owns its own source bytes.

The named aggregate budget charges input resources, candidate/old joins, unique
retained catalog/snapshot owners, unique graph pools, one streaming decoded
record, the original 64 KiB streaming reserve and a separate 128 KiB adapter/
future-decoder reserve. Caller buffers, loader/material/GPU resources, external
index owners and digest scratch belong in `retained_bytes`. Source owner bytes
are charged once even when the graph borrows them. Counters are payload/reserve
accounting, not allocator metadata or process RSS.

`check_resource_join.py` pins the retained successful catalog/root artifact and
runs release/ASan/UBSan. It constructs explicitly synthetic in-memory resource
observations only to test exact real catalog association: all 40,225 regular
owners plus seven future ordinals and 9,611 geometry references. No GEO path or
asset is inferred or admitted. The original small zero-model source fixture
also proves positive retained-index equality, generation refusal and duplicate
binding labels on distinct catalog owners. Checks cover late missing/changed
future records, names/IDs/geometry mutations, checksum mismatch, all four own
allocation failures plus decode failures, cancellation, exact budgets, old/new
rollback and source/graph retirement order.

The conservative full fixture reserves an entire 32 MiB test generation buffer;
its named old/new peak is not a production allocation requirement. The real
capture diagnostic instead reads exact file sizes and frees original catalog/
sidecar input buffers after immutable import. `inspect_resource_join.py` requires
an independently trusted binding SHA, reuses the source capture driver's final
post-cleanup binding validation, then compiles and executes the host CLI in all
three modes. It hashes every capture and native/helper dependency before/after.
No fixture slab, resource index, GEO decoder or renderer is enabled in this path.

For an actual newly captured resource triple, construct a fresh source/run owner
family from that capture's own source/inventory/run pins. Byte-identical catalog
content does not permit attaching new run labels to an old immutable owner. Keep
prior families intact and charge them as retained state while preparing the new
one. After native association, actual GEO manifest/path identities and sorted
runtime model-row versus raw disk-row semantics still require their own separate
admission before a resource index can be joined to rendering.
