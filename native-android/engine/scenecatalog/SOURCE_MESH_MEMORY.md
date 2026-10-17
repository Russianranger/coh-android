# Canonical SOURCE geometry and a real retained-owner budget

`coh_source_mesh_v8_create` is an additive SOURCE base-geometry owner, not a new
renderer or material entry. It derives the exact disk row, path, model, generation
counter and complete-body digest from an existing opaque SourceBody lease. It
rehashes that body, preserves its index/header/GRID/reductions and transfers the
Body only after all validation, cancellation and allocations succeed. The graph
and loader remain explicit borrowed dependencies until this owner retires.

A single canonical vertex array is shared by every material partition. Positions,
normals and indices use the qualified unchanged delta readers. Base UV is
`sourceU, 1-sourceV` in both channels with neutral carrier color. Effective CLIENT
materials can have different UV scales: this owner does not apply or invent them.
It exposes source parts without renderer geometry IDs. Reflection, alternate
pivots, absent UV, skinning, lightmap/nonunit-scale and other existing special
cases remain refusals. Only explicit version8 is supported. No existing rigid or
SourceBody bridge policy changes.

The authentic CityHall model (whole-join ordinal26509, profile file344,
`AP_CityHall_Makeover_01`) has32,056 vertices,19,193 triangles and12 partitions.
The existing rigid path allocates12 vertex arrays (21,541,632 bytes). The new
source owner uses one array (1,795,136 bytes), without claiming arbitrary-material
packet equivalence. Streamed complete output with fixture UV scales1 matches the
frozen469 full21,771,948-byte packet SHA
`e026c08ea55313eab0ac01276cc9a0231fdfe07d111817393b9ce1e4e477cc3d`.
That historical packet was independently checked against the unchanged original
delta consumer; the broad sweep and whole original loader are not rerun here.

The aggregate test uses actual immutable catalog/snapshot/compact graph/resource
join/profile/Body owners, plus real historical14,715-row TexOpt and3,644-row Trick
owners over the exact13,537,052-byte tricks.bin. Dictionary input generation17 is
a historical label, separate from source asset counter20261016. Both dictionary
owners pin the same actual cache blob (second acquire adds no read/allocation).
A fresh16MiB dictionary loader is configured before source GEO loading; caps are
lower than the earlier32MiB tests. The source GEO loader retains its32MiB limit.
No13.5MiB duplicate host buffer is used: FILE read_at supplies the loaders.

| CityHall mesh preparation charge | Bytes |
| --- | ---: |
| Unique actual source retained owners |37,201,573|
| Entire source GEO loader reservation |33,554,432|
| Entire dictionary loader reservation |16,777,216|
| TexOpt + Trick owned metadata |528,352|
| Dictionary static/frame allowance |65,536|
| Explicit diagnostic/provider allowance |262,144|
| New persistent mesh owner |2,026,524|
| New temporary decode allocations |642,957|
| Native mesh preparation frame reserve |16,384|
| **Named aggregate peak** |**91,075,118**|
| **Capacity remaining below96MiB** |**9,588,178**|

Actual dictionary admission peaks71,432,929 bytes, with GEO loader absent. Body
admission while dictionaries persist peaks88,429,410 bytes. Actual loader peaks
are13,537,988 dictionary /1,106,925 CityHall GEO bytes; the larger configured
reservations, not observed usage, are charged above. Temporary decode storage
retires before publication; persistent source/dictionary/blob owners stay alive.
The old isolated rigid CityHall preparation peak94,484,170 bytes did not include
these actual dictionary owners, so the reports have different retained sets.

This is one exact authentic model and dependency set, not an all-world resident
budget or process RSS measurement. There is currently no qualified immutable
authoritative actor owner. The9,588,178 bytes are an explicit future-owner allowance,
not an invented actor allocation or proof that all future materials/GPU resources
fit. A caller must charge every other actual owner and transient provider/runtime
peak in retained_bytes. Budget-minus-one and additional-retained-bytes-plus-one
refuse transactionally; exact96MiB boundary succeeds. Native factory frames and
called native helper file maxima are measured separately; external library,
OpenSSL, zlib, FILE/provider/compiler/OS stacks remain within the explicit caller
allowance contract, not a universal RSS guarantee.

`check_source_mesh.py` freezes the transitive quoted C/include dependency closure
before compilation and revalidates it and all inputs afterward. It uses no project
Python imports or bytecode caches. Release/ASan/UBSan each pass390 controls,
including early/late cancellation, all three factory allocation failures, digest
refusal, known alias guards, shared-part identity/contiguity, getter bounds,
exact packet SHA, output/Body rollback, full-boundary capacity and final zero
loader pins. LeakSanitizer and Android execution are not claimed. Exact source,
input, packet and compiler frame receipts are in
`evidence/source-mesh-aggregate-host.json`.

Active CLIENT material/Basic/composite/LOD/animation association, authoritative
actor transaction, live GROUPS/source generation association and GPU publication
remain separate required gates. Render-ready, client-material and world flags
stay false. E's detached dictionary work can reduce a future configuration further;
this evidence deliberately exercises the currently qualified full-cache owners.
