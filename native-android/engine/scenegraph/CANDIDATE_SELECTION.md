# Lossless source candidate selection

`coh_runtime_candidates` preserves every original root-to-node occurrence as a bounded resource/visibility candidate. It does not cull. Source bounds and SERVER flags are insufficient to infer complete CLIENT visibility, so a candidate cannot disappear merely because one observed flag suggests hidden geometry or one source box appears outside a camera volume.

## Original CLIENT prerequisites

The audit reads original `Game/src/graphics/groupdraw.c`, `groupdrawinline.c`, `groupdraw.h`, `gfxwindow.h`, and `Common/group/grouptrack.c`. Exact numerical producer functions/macros and audit sources are pinned in qualification evidence.

| Original operation | Required state not established by a SERVER source box |
| --- | --- |
| `makeAGroupEnt` | Actual CLIENT definition mid/radius/shadow distance; inherited view scale; CLIENT definition/model tricks; preload completion; cached editor, fog, fade, dynamic-parent flags |
| `closeEnough` | View-space midpoint, parent-fade midpoint, actual cache values and game LOD scale; fog/doorframe/child-fade exceptions |
| `sphereInFrustum` | Effective CLIENT sphere and actual viewport/frustum; possible shadow-volume visibility even when the ordinary sphere is outside |
| `drawDefInternal` | Editor/view mode, inherited fade/no-fog state, near LOD, tray/portal routing, dynamic parents, occlusion, shadow and effective tricks/material state |
| `trackerSetMid` | Actual CLIENT definition bounds and tracker transform; tracker radius and GroupEnt radius are separate source computations |

`makeAGroupEnt` may preload the definition before constructing caches. `drawDefInternal` can route trays/dynamic children through other paths. A source AABB/point is therefore not a verified substitute for these predicates, and no new sphere-scale or generic near/far clamp is introduced. Source numerical group bounds retain their existing nongeneric source-volume semantics.

`coh_client_distance_project` implements only unchanged-original `closeEnough` arithmetic when complete CLIENT inputs are supplied. It preserves parent midpoint selection, exception flags, signed scalar semantics and the original zero-distance return. Only used finite inputs are required. It does not acquire those CLIENT inputs, test a frustum, or authorize dropping a candidate. SERVER lod6 does not construct the required caches. Its results cannot clear the candidate pager's unresolved mask.

## Exact source ownership and paging

The immutable context retains the actual resource join, checks its actual graph pointer, catalog/snapshot byte addresses/extents and copied bindings, and creates one bounded node-to-source-ordinal inverse map. Ordinal is never assumed equal to node. Duplicate/missing active mappings refuse. Whole raw source records remain in the retained join, including observed SERVER hide/trick/unknown flags; output copies their exact source ordinal and SHA256. A borrowed raw-record query remains valid through context retirement. This is no path alias, body acquire, material selection or live-generation proof.

The graph is borrowed and must be externally retained and immutable until the last context/pager retires. Reference counters are not atomic: serialize context retain/free and pager open/close, and prevent retirement while queries or paging borrow the context. Opening a pager retains the context; closing releases it once. An open pager borrows its immutable instance batch and optional bounds array. The bounds report is consumed synchronously. A walker may advance only with another batch allocation while the old batch remains open. Caller controls, output, batch, bounds and known private/source spans must be disjoint. Opaque owner/graph/cancellation storage disjointness remains a caller obligation.

Each next call emits one record per processed input occurrence, including no-model groups and future/effect candidates. Every record keeps unresolved CLIENT cache, tricks, parent draw, camera, shadow/fog/portal, dynamic, LOD, material and live-generation state. Model records additionally require body admission. Missing/blocked source bounds add a separate unresolved bit; computed and explicitly captured future bounds are copied only when finite and ordered. No default box is interpreted as real data. No observed SERVER hidden flag clears a prerequisite or removes a record.

Source-body/profile resolution remains outside this module. The exact ordinal can be consumed by A's independently retained SourceBody lease and E's renderer adapter only after their actual owner/binding requirements pass. Multiple references do not duplicate owner payloads: context reports distinguish its owned bytes from unique join/catalog/snapshot/graph dependency bytes. Other body/index/profile/loader/GPU owners must be charged by actual identity, not by equal hashes or blindly adding overlapping whole-owner totals.

Pages have at most 1,024 records and a row-step limit. No allocation, I/O, lookup scan or record parsing occurs while paging. Cursor/report commit only after full call success; output storage is scratch on failure. Input order and path multiplicity remain unchanged across any page capacity. Completion of an empty batch is explicit. No visibility rejection/admission, body/material admission or world permit is produced.

## Qualification

Host release, ASan and UBSan each pass 9,703 controls covering inverse mapping with deliberately different source ordinals, raw-record identity, allocation failure cleanup, cancellation rollback, retained-join lifetime through open pagers, repeated-path preservation, no-model/missing-bounds cases, exact continuation, aliases and budgets. The pure numerical projection matches 4,096 fixtures from unchanged original `closeEnough`, original flag enum and original macros. It is not actual CLIENT execution or a Win32 ABI claim. Paging allocates nothing.

A fresh diagnostic reuses the exact retained run 38994607354 triple, revalidates its binding and source/input hashes, reconstructs existing source bounds and streams every occurrence through small pages. It performs no new capture, server run, download, accepted APK build or GPU work. All release/ASan/UBSan results agree:

| Observation | Count |
| --- | ---: |
| Occurrences preserved | 564,559 |
| Model candidates | 384,280 |
| No-model/effect/future candidates | 180,279 |
| Source bounds available | 564,559 |
| CLIENT-unresolved records preserved | 564,559 |
| Visibility rejections/admissions | 0 |
| Instance batches / candidate pages | 2,206 / 81,597 |

Context ownership is 161,496 bytes; unique retained metadata dependencies are 36,956,417 bytes. Candidate-phase named reservation is 39,418,545 bytes. Earlier source-bounds phase reservation is 47,995,381 bytes and join preparation peak is 51,666,433 bytes. These are named native reservations, exclude Python/process RSS and allocator bookkeeping, and contain no acquired GEO bodies, material/GPU resources or device execution. All source-generation, visibility, asset and world-authority flags remain false. Android/Thor, actual CLIENT prerequisites, matched live GROUPS, authoritative actors and rendered-world acceptance remain separate gates.
