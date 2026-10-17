# Bounded bottom-up source bounds

`coh_runtime_bounds_diagnose` walks the immutable runtime graph in exact root and child order, using a capped iterative stack and caller-owned rows/child scratch. Shared children are computed once. Only root-reachable components are visited; cycles, bad targets, depth excess and insufficient budget refuse without changing the report. Workspace is scratch and may change on any return. A successful report may still carry explicit missing/dependency blockers. Known work/control/report and exposed source spans are checked for pairwise overlap with overflow-safe endpoints before any scratch write; overlapping spans refuse atomically. Opaque graph allocations and callback contexts remain explicit caller ownership preconditions because their extents are not exposed. No heap is allocated by the adapter. Caller input owners, callback/header reservations and other retained allocations must remain charged; graph payload and complete supplied scratch capacities are added explicitly. Accounting is named payload reservation, not process RSS.

Ordinary nodes obtain independently qualified definition/model input through a synchronous callback. The standalone actual-capture diagnostic decodes each exact retained definition's volume metadata and uses the matching source-observed Model min/max from the immutable resource join. It disposes one decoded definition before advancing; the caller reserves 8 MiB for that decode plus 256 KiB for driver/metadata/digest stack. This proves source numerical reconstruction only: source model boxes have not been compared with GEO-body boxes, and no GEO files or materials are loaded by this diagnostic.

## Future data was already captured

The original `source_snapshot.inc:coh_snapshot_external` serializes **both** the actual live future `GroupBounds` and the separate library-lookup scratch `GroupBounds`. Each is 60 bytes of explicit named fields, not a compiler bitfield dump. The old native envelope validated both spans but did not expose them. `coh_runtime_graph_external_bounds` now returns parsed values and the exact borrowed raw spans from that authenticated retained snapshot. It adds no allocation or graph-layout growth. Live data never comes from lookup-miss zeroes.

All seven actual future records have zero min/max/mid/radius/vis/shadow/recursive count, lod_scale1 and flags`0x02000000` (observed SERVER editor_visible_only). All lookups miss and their separate lookup records are zero. Six futures are unreachable; `_mmayhem_curtain_8_01c` is reachable. These are actual captured values, not fabricated definitions or constructor assumptions. Captured SERVER flags do not prove effective CLIENT flags or draw policy.

Before this getter, the bounded diagnostic conservatively blocked that future, its eight ancestors and root slot7 (`grp_Geometry`, node5469). The retained `evidence/pre-future-bounds-view/` is **pre-adapter evidence**, not proof that capture data was missing. With exact observed future bounds, source numerical reconstruction completes all 33 roots:15,352 ordinary nodes plus one captured future, with no missing or blocked reachable node. The other six futures remain explicit graph owners; they are not removed.

Original `groupDefFuture` allocates through `groupDefNew`, whose pool initializes with zeroing `Default` mode; it then calls `objectLibraryGetBounds`, which can overwrite the whole GroupBounds region. CLIENT `groupSetBounds` and `groupSetVisBounds` return early for pre_alloc, while SERVER does not take that branch. `groupAssignToFile`, library loading, group recentering and bounds/visibility recalculation have additional mutation paths. Consequently a constructor-only zero proof would be insufficient. The captured lod_scale1/editor-visible flag also demonstrates that the complete live bounds state is not merely unmodified constructor zeroes. No new capture or unsupported lifetime invariant is required here.

## Qualification and remaining resource work

The graph API fixtures cover shared DAGs, a disconnected cycle, reachable cycle/bad-target refusals, missing input and future propagation, captured future reuse, exact-budget refusal and cancellation rollback. Release, ASan and UBSan each pass173 controls. Existing runtime-snapshot fixtures independently walk the original envelope and compare every parsed future field and raw span, enforce no allocation/output rollback, and retain malformed-input/graph qualification:85,272 controls per mode. Source numerical kernel parity is separately qualified in GROUP_BOUNDS.md.

The actual run38994607354 capture is revalidated before and after native execution; release/ASan/UBSan outputs agree. Python independently walks exact source envelope spans and checks every future live/lookup byte against the getter. Bounds scratch/reservation is47,995,373 bytes including retained owners and callback reserves; the earlier join import peak remains51,666,425 bytes. Maximum first-visit DFS depth is69. No Android execution, GEO-body bounds equality, original runtime-file generation, CLIENT LOD/material or world admission is established.

The391 routed candidate files span versions0:159,2:5,3:1,4:4,5:10,7:57,8:155. Their2,916 reachable model pairs span versions0:1,121;2:21;3:2;4:12;5:82;7:428;8:1,250. E's current v8-only rigid adapter therefore covers a format subset, not the complete Atlas world. A owns acquisition/body provenance; E owns original geometry conversion. The protected GEO model view does not expose min/max. A future per-file bounds adapter can consume its borrowed header only after unchanged-source format offsets are qualified. Its blob/header/decode reservations must be charged alongside the retained metadata and bounds rows, without flattening every file into one scene. `groupSetLodValues` is already qualified separately, but its required post-trick/CLIENT ModelLODInfo input has not been admitted, so this traversal does not fabricate LOD output.

Run standalone host qualification:

```sh
python native-android/engine/scenegraph/check_runtime_bounds.py --output NEW.json --sanitize
python native-android/engine/scenegraph/check_runtime_snapshot.py --output NEW.json --sanitize
python native-android/engine/scenegraph/inspect_runtime_bounds.py --capture-directory CAPTURE \
  --binding-sha256 7c42a9612e4e08ee6463c3a8f87d2cf0749ff2baa8183d6b3c58281ec004c39c --output NEW.json
```
