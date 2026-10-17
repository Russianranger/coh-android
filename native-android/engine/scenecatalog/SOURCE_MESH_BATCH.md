# Immutable SOURCE mesh batch

The new batch owns a bounded, source-ordered subset of actual opaque canonical
mesh owners. It is a dependency/lookup boundary for later renderer integration,
not a draw batch or material constructor. No path, model, SHA, graph-node or
source-generation value is accepted from the caller. Those values remain the
actual Body/index/compiled-profile/join records captured in each mesh.

New narrow Body and Mesh dependency getters return actual borrowed opaque owner
identities and immutable owned byte counts. The batch requires the same actual
selection, join, catalog, snapshot, graph and profile identities. Identical
source/run hashes or generation counters cannot substitute for these owners.
Different Body/index owners are charged separately, even for the same GEO file.
The common join/catalog/snapshot/graph/selection/profile are charged once. Each
actual loader is charged once at its maximum recorded reservation; equivalent
paths or hashes never deduplicate ownership. Graph and loader leases remain
externally held through batch retirement, as required by the existing owners.

The factory accepts at most64 actual meshes/4096 parts, already in strictly
increasing whole-join ordinal. Duplicate ordinal/mesh/Body/index, descending order,
null entries, mixed selection identity, cancellation, allocation failure, aliases
and over-budget input refuse without changing any input slot, output or report.
Only complete success transfers every mesh and clears all caller slots. No caps
are raised. Known storage/endpoints are checked; caller-disjoint opaque owner and
control allocations remain an explicit precondition.

Ordinal lookup uses binary search; known-output-alias validation also examines
at most64 owners. Entry views return actual stored source identities and the
original partition prefix. Part views retain source material labels/order and
shared canonical geometry, without renderer geometry IDs. All views require
batch lifetime. Destruction retires meshes before their Body/index pins. Neither
retaining nor transferring a mesh makes an external graph or loader owned.

The actual retained test prepares CityHall ordinal26509 and Plaza ordinal26510
from separate immutable Body/index owners over the same loader/blob/profile.
It keeps real historical full-cache TexOpt/Trick owners alive throughout.

| Named two-model batch charge | Bytes |
| --- | ---: |
| Shared source owners |37,128,632|
| Two Body/index owners, additionally |145,882|
| Two canonical mesh owners |2,371,124|
| Batch owner |1,608|
| Common GEO loader reservation |33,554,432|
| Retained dictionary loader/metadata + caller allowances |17,633,248|
| Batch preparation frames |16,384|
| **Batch preparation total** |**90,851,310**|

The target two-model preparation sequence peaks91,075,118 bytes at the earlier
CityHall decode stage. Thus9,588,178 bytes remain below96MiB for explicitly charged
future owners in this exact configuration. A separate negative control stages
an additional selection/Body/mesh with the same fixed hashes; it must refuse
cross-selection admission. Its extra-owner preparation peak is separately
recorded in the receipt and is not the target two-model capacity claim.

Release/ASan/UBSan exercise actual transfer and final zero pins, all cancellation
points, candidate allocation refusal, ordering/duplicate/alias/budget controls,
exact shared-owner accounting, genuine equal-hash distinct-selection refusal,
lookup and partition ordering. CityHall's complete fixture-UV1 packet still
matches the previously original-delta-qualified SHA. The qualifier freezes and
revalidates its transitive C/include closure, uses no project Python imports and
records source/input/compiler-frame identities. Final evidence:
`evidence/source-mesh-batch-preflight-host.json` (419 controls per mode).
The earlier sealed-host receipt remains historical to2e4e94ebf. The final
preflight adds the caller/own/frame minimum before owner measurement, then
admits the complete aggregate before any cancellation callback or allocation.
Read-only owner measurement is independently bounded to at most64 squared
comparisons and performs no I/O, parsing, allocation or external callback.
An explicit over-budget-plus-cancel control proves callback count stays zero.

SOURCE mesh UVs remain canonical/unscaled. Actual CLIENT material UV transforms,
Basic/composite/texture ownership, current-generation binding, actors, GPU
resource ownership, live GROUPS and atomic world publication remain separate
requirements. Renderer/material/actor/world readiness flags all stay false.
