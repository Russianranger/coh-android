# CLIENT LOD projection and zero-draw source rows

`coh_wr_lod_project` supplies the numerical projection in original CLIENT `modelCalcAlpha`. It compares all result fields against the unchanged original function under narrow type/global shims. Both FINAL and non-FINAL branches execute. It is a pure projection, like the sampling helper: its output is not a semantic, resource, visibility or world permit.

The caller must supply the selected AutoLOD (when applicable), definition ranges, inherited draw scale and CLIENT global scale, debug fade policy, effective model/draw tricks, parent fade-node/radii, effective fog distance/clipping policy, sun lamp alpha and inherited alpha/stipple state. These values must belong to the admitted CLIENT resource/context generation. Raw SERVER LOD values, source trick observations and cached texture flags cannot be substituted. `draw_alpha == 0` is the original inherited-alpha sentinel, not zero opacity. The original window early return bypasses later fog/alpha modulation; early returns preserve the initialized stipple value. The helper intentionally preserves both details.

The bounded input subset rejects nonfinite/negative distances, radii, ranges and scales; invalid boolean/enumerated bounds; alpha/debug fade outside [0,1]; reversed active near/far and zero window-far. Overflow or underflow that would make window division invalid refuses before publication. Aliased inputs/outputs refuse, and every failure preserves output. Source source-model selection, occlusion, water/base-editor overrides, load completion, blend order, shader compatibility, material lighting and draw admission remain separate.

The actual source resource capture includes GLD NOT_LOADED/model-loadstate-zero header observations. A's `coh_resource_geo_source_open/model` and immutable resource index preserve all raw rows, including qualifying version-8 headers with zero vertices, triangles and material partitions. This is sufficient for source identity and hierarchy reconstruction. It does not establish a CLIENT decision that the corresponding definition has no effects, children or inherited state.

A coherent resource adapter may consume those views as follows:

1. Retain the exact admitted body/index and its catalog/runtime/resource/manifest generation bindings. Preserve original disk rows and sorted runtime identity separately.
2. Preserve a zero-draw row as source metadata. Never manufacture a renderer geometry object, invoke a fake material supplier, remove a definition, stop child traversal or skip inherited effects because of that row.
3. For an ordinary selected row in a body containing zero rows, the source-header wrapper validates each ordinary row with the protected decoder. A future rigid decoder entry point may consume that admitted view while retaining the original blob pin, whole-file digest and budgets. Default rigid acquire still uses protected whole-body open and deliberately refuses such bodies. The separate `coh_wr_rigid_source_acquire` explicitly selects A's qualified source wrapper; it admits only ordinary selected rows and rejects a selected zero row before material acquisition. No caller-supplied parser or metadata view is accepted.
4. Resolve CLIENT material/texture/trick/AutoLOD state separately; only then use numerical LOD/sampling projections. Effective absence of an optional texture, default lighting or unsupported CLIENT state cannot be inferred from a zero header or missing source field.
5. Require complete ordinary geometry, every texture mip, Surface/context ownership, selected authoritative actor and matching live generation before world publication.

The additive API therefore does not widen zero-row admission into draw capability. A's index remains the owner of zero metadata. The explicit source rigid entry retains its own exact body pin, hash and budget through CPU decode and cleanup; it does not own the whole index or its catalog/runtime generation. Production callers must additionally retain and independently match the index generation. The default entry retains its previous policy. Neither entry grants CLIENT material authority, and neither replaces protected APIs or reinterprets zero rows as an empty world.

`check_rigid_source.py` uses the exact retained Shop_tailor body (SHA98f0d86d789f90fc35e5e9f5008bf987ef97ba90998cae99f5c9930036fa80d9). All72 source rows and the four zero names/ordinals remain present. Its observed roof model at disk59 yields a complete original-delta-equal four-vertex/two-triangle packet under explicit fixture materials/generations. Tests cover selected-zero refusal before material calls, default-entry refusal, wrong digest, absent name, cancellation, bounds, old-output preservation, pinned lifetime through trim and corrupted zero sibling refusal. This is source/body CPU qualification; no live source-generation or material/world authority is claimed.

`check_lod.py --output /tmp/FRESH-lod.json` runs release, ASan and UBSan source comparisons, malformed-input/output preservation controls and three mutations (near-boundary, NightLight/AddGlow and the original double-literal stipple threshold). Source and all helper dependencies are pinned before execution and checked afterward. No original CLIENT process, Android, GLES or Thor execution is claimed.

The rigid selection loop advances a bounded raw record cursor and decodes borrowed one-row views at row zero. The selected raw offset is retained directly. This avoids repeated scans from the first record while preserving original ordinals. A private test observer requires exactly72 decoder calls with row zero and increasing original offsets for the authentic body; both default and explicit source entries use the same linear selection plumbing.

## Automatic source LOD construction

`coh_wr_lod_autodata` now implements the complete numerical construction in
original CLIENT `lodinfoFillInAutoData`. It consumes separately resolved model
radius, source triangle count, Trick near/near-fade/far/far-fade/shadow values and
an explicitly present or absent three-distance reduction array. Its fixed output
contains at most four ordered rows with exact source error and fallback-material
flags. It allocates nothing, borrows no source storage and retains no asset,
material, dictionary or GPU ownership. Every refusal preserves the output.

The original loop tests the **previous iteration's** triangle count before
updating that count, admits strict 125-unit near/far thresholds, initially avoids
high-poly quarter reduction, and uses a strict radius-greater-than-200 condition
for its 25-unit fades. Only an entirely zero Trick range tuple enables the
quarter-far default fade. The implementation preserves those distinctions;
negative finite reduction distances retain the original stop-sentinel behavior.
Nonfinite/negative model/range inputs, unsigned triangle counts outside the
source signed-int domain, invalid presence flags, overflow and output aliases
refuse before publication. This is a bounded valid source domain; it does not
make malformed original inputs valid.

The qualifier executes the unchanged original function against narrow
lookup/Trick, fixed allocator and EArray observers. Release, ASan and UBSan each
pass 74,366 checks over 17,799 source comparisons. The comparisons include all
3,083 exact root-model radius/triangle/Trick numeric observations in retained
COHRES SHA `8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6`,
joined by exact source ordinal/model/GEO/partition identities to the previously
qualified root ledger. **COHRES does not capture CLIENT reduction arrays**. Those
authentic numeric controls explicitly test the source function with a NULL array;
they do not assert that the actual model has no reductions. Separate derived
controls exercise all four row counts, threshold boundaries, prior-loop counts,
integer truncation, negative-distance stop, supplied Trick fades, rollback and
source-int limits. Five production semantic mutations must fail. The existing
`modelCalcAlpha` qualifier still passes all 311,296 source combinations in all
three modes against its unchanged original function.

The retained client cache archive also contains original `data/bin/lods.bin`:
1,059,016 bytes, SHA
`13800255781138248226340be316cd628e98800d9ba889fe1aecc902e483b66a`.
That availability is not native admission or an active CLIENT dictionary.
Original `lodinfoFromObjectName` first consults a fileLocateWrite-derived LOD
hash and can return an existing nonremoved row before automatic construction.
Current dictionary precedence, removed/force-auto state, default GEO/legacy LOD,
Trick AutoLOD children, cape/tray policy, original model/reduction selection,
object-library lookup and matching CLIENT generation must still be resolved by
the caller before using these numerical rows for visibility or draw selection.
No row grants a reduced mesh, fallback material, current resource, world or actor
permit. Android, GLES and physical Thor execution remain unqualified.

```
python native-android/engine/world-render-adapter/check_lod_autodata.py \
  --resources /path/to/exact/resources.cohres --output /tmp/FRESH-autolod.json
```
