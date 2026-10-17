# Retiring prepared GEO dependencies

`coh_source_sealed_create` is a separate immutable SOURCE owner. It consumes an
actual source-mesh batch only after every copy, pointer rebase, cancellation and
reference operation succeeds. It retains the actual Selection, which retains
its actual join/catalog/snapshot. The graph still requires its external lease.
There is no Body, resource-index or loader pointer/span stored in the new owner.

Per selected mesh it copies the canonical vertex array, all indices and partition
descriptors, exact source COHRES record and complete decompressed GEO header.
Every ResourceView string, native model name, material name and canonical asset
path is rebased into its own allocation. Native Model/header metadata, original
rows, partition order, source min/max/flags, full body SHA, source-record SHA,
resource-stream SHA and source/run/manifest/counter values remain unchanged.
New narrow batch-dependency access derives the actual retained Selection handle;
no identity/generation label or witness-success JSON is accepted from a caller.

The complete header preserves GRID/reduction descriptors and all file-model
metadata. Full GEO payload streams are deliberately not retained or exposed by
this prepared-geometry owner: GRID/reduction payload operations require a later
separately validated reacquire of the exact body. Neither an empty fake payload
nor a stale BodyLease is returned. The original391 disk bodies remain intact.
Effective materials, UV scales, lighting, LOD selection, actors, live generation
and world publication remain unqualified; all corresponding readiness flags are
false. Geometry is still the same canonical unscaled SOURCE base data.

The factory preflights old batch, old mesh/Body/index/shared-source ownership,
whole live loader reservations, new copies,16KiB own preparation frames and ALL
caller-retained peaks before any external callback or allocation. Owned cap32MiB
and aggregate cap96MiB are unchanged. Candidate allocation, any cancellation or
late Selection-retain failure frees only the candidate and preserves batch,
output and report. Success retains Selection before freeing the old batch.

External loaders are caller-owned. **Consuming a batch alone does not release a
loader reservation from a global budget.** Other loader pins, cached blobs,
provider contexts and configured capacity remain until the caller actually
retires them. The new report keeps inherited_loader_reservations as a transition
charge and reports only its own dependency counts as zero. The caller must
include every still-live external loader/owner in later retained_bytes.

The actual CityHall/Plaza test uses two separate Body/index owners,21 partitions
and the real historical TexOpt/Trick cache owners throughout preparation.

| Phase / actual named ownership | Bytes |
| --- | ---: |
| Old batch + live GEO reservation + new sealed copy + other owners + frames |93,228,133|
| New copied geometry/records/headers/paths owner |2,376,823|
| Retained actual shared source owners |37,128,632|
| New owner + source dependencies after actual GEO destruction |39,505,455|
| Conservative previous dictionary/caller allowance still charged |17,633,248|
| **Post-GEO-retirement comparison aggregate** |**57,138,703**|
| **Remaining below96MiB for additionally charged owners** |**43,524,593**|

The test explicitly trims the GEO loader, verifies zero pins/resident bytes,
destroys it, closes its FILE provider and releases the external Selection handle.
It then also retires historical dictionary loaders before querying every copied
name/header/record/partition. Both complete CPU packets still match the frozen
original-delta-qualified results: CityHall21,771,948 bytes and Plaza2,747,568 bytes.
Exact original COHRES/header digests match after destruction; ASan exercises all
re-based pointers after old allocations are freed. The17,633,248-byte dictionary
allowance remains in the comparison even after the test later destroys those
owners; it is conservative, not a new stage-composition admission.

Seal before admitting additional actor/set/semantic owners where needed. Any
already-resident class/cache/actor/GPU/packet/provider owners must be charged in
retained_bytes during the old+new transition, not merely afterward. These tests
do not claim a globally composed dictionary/actor import, actual authoritative
actor availability, all391 resident bodies, GPU readiness or process RSS.

Release/ASan/UBSan each pass605 controls, including25 distinct cancellation
points, allocation and late-retain refusal, known aliases/endpoints, ownership
transfer and actual provider retirement. The qualifier freezes/revalidates59
transitive native/source inputs, uses no project Python imports and records
compiler frame measurements. The16KiB reserve covers the measured native helper
frames; external library/provider/compiler/runtime stacks remain the caller's
explicit allowance. No Android or LeakSanitizer execution is claimed.

Final receipt: `evidence/source-sealed-complete-host.json`. Earlier sealed-host
and final-host files are preserved exploratory receipts, not current source pins.
