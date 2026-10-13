# Phase 9: bounded source world and camera gate

This phase currently records **analysis only**. No Phase 9 geometry member has been acquired, no native scene implementation has been built, and no world-rendering APK is qualified. Accepted Phase 6–8 implementations remain unchanged. The accompanying [scene recovery receipt](evidence/phase9/scene-recovery.json) pins the exact source files and distinguishes recovered scene text from inventoried, unrecovered binary assets.

## Selected real scene branch

The first world fixture will select one authored `modern_bench_2wide` branch from Atlas Park. This is one source geometry root instance; its actual material partitions and resulting draw calls remain unknown until the GEO model table is recovered. “2wide” is the model name, not a claim of two draw calls.

Every ancestor transform is preserved from `upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_geometry.txt`. The selected branch is a bounded scene subset. Other children of each parent remain outside the fixture and are not silently represented as loaded.

| Parent → selected child | Authored position | Authored PYR in degrees |
|---|---|---|
| Map Ref → `grp_Geometry` | `511.380371 426 -703.999756` | Omitted |
| `grp_Geometry` → `grp141198` | `-296.317322 -417.42926 -280.957397` | Omitted |
| `grp141198` → `grp141203` | `408.936951 33.42926 -431.042847` | `0 89.999985 -0` |
| `grp141203` → `grp141205` | Omitted | Omitted |
| `grp141205` → `grp141259`, first authored occurrence | `24.5 32 -40` | Omitted |
| `grp141259` → `Streets/Elements/misc_sm/modern_bench_2wide` | Omitted | `0 90.000038 0` |

The child defines `TintColor 67 139 202   0 0 0`. Its parent `grp141205` defines `Ambient 28 31 40`. Higher parents retain the original `TexSwap generic_cubemap_face0 City_01_01_grpcubemap141152_face0 0` and Geometry/AutoGroup properties. These are authored metadata; their complete renderer/light resolution is still pending. Omitted transforms require original parser defaults rather than assumptions in an ad hoc conversion.

The source loader stores position and calls `createMat3YPR`, with degree conversion supplied by `TOK_PYRDEGREES`/`TOK_DEGREES_X`. Original group traversal composes parent and local matrices. Runtime matrix reconstruction must preserve the source binary32 operation order and actual world coordinates; sampled expected matrices must never drive rendering.

## Asset and material closure

The previous Atlas-world ZIP inventory identifies these exact members in `payloads/runtime/atlas-world-supplement.zip` inside `COH-Assets-1.0.0-Base.zip`:

| Member | Original bytes | ZIP method | Local-header offset | CRC32 |
|---|---:|---:|---:|---|
| `data/object_library/streets/elements/misc_sm/misc_sm.geo` | 51,138 | Stored | 56,969,607 | `40e8fb08` |
| `data/texture_library/world/streets/elements/monorail/modern_bench.texture` | 22,225 | Deflate | 157,524,166 | `dbcd5e30` |

The inner archive is 207,803,201 bytes. Its published SHA256 is provenance, not a locally verified whole-archive hash. These are inventory locators, not complete member verification: **neither member has a Phase 9 SHA256, parsed model table, geometry count, or texture-decoding proof yet**. Exact sizes, local ZIP envelope, CRC32, stable HTTP range ETags and full recovered member SHA256 must be checked during acquisition. The accepted actual Phase 8 stock-white wrapper is already available with its verified source pin.

`upstream/i24/data/tricks/streets/elements/streets_misc.txt` declares `modern_bench.tga` with `Surface METAL`, `Blend white.tga`, and `BlendType ColorBlendDual`. This makes the accepted dual-color shader family a concrete candidate. The library `.rootnames` and `.txt` identify `modern_bench_2wide` directly. The GEO's exact texture table, model trick suffixes, UV channels, static vertex colors, normal-light/static-light branch, sampler flags and material partitions must confirm that candidate before native rendering claims it. The `mbench` trick defines LOD distance/fade values; association with the selected recovered GEO name remains unverified.

Linear mip-zero filtering is a previously recovered source default, but the selected world wrapper's flags, addressing and mip policy remain unqualified. Controlled lighting can qualify shader arithmetic while retaining original Ambient metadata; it does not establish original Atlas ambient/vertex-light fidelity.

Concrete benches are deferred because their original definition adds a baked shadow model. Bus-stop glass is deferred because its trick requires reflection texture state and `SimpleAlphaSort`. The pillar group is deferred because its full authored closure contains 43 pillars and a city wall across more than 3,000 scene units.

## Camera and qualification contract

Recover the unchanged source bodies of `gfxSetViewMat`, `rdrFixMat`, `rdrSetupPerspectiveProjection` and `rdrSetupFrustum`. The original view conversion transposes the camera rotation and mirrors X using `diag(-1,+1,+1)` before computing view translation. Substituting a generic look-at matrix would lose that source convention. A bounded test camera is explicit controlled input, not a captured gameplay camera. Aspect/FOV policy must state whether the original gameplay adjustment above 4:3 is selected.

The proposed host oracle executes unchanged source degree conversion, matrix construction/composition, view conversion, perspective and geometry-expansion kernels under documented minimal compatibility wrappers. Independent references then verify world positions, normals, eye/clip-space outputs and selected material arithmetic. GPU transform feedback and pixel checks must require useful geometry coverage, source culling and depth behavior. Controlled overlap/near-plane witnesses must be labeled separately from original map transforms. A full original scene sorter is not established by one branch; source pointer tie comparisons need an explicit portable policy before broader sorting qualification.

The future probe must distinguish passing render checks from completed lifecycle qualification. Before background recovery, its status should say **Render checks passed; lifecycle check required**. A green gate requires actual two-axis resize, successful Surface recreation, an explicit Home test with recorded pause/stop and required destruction observations, then resume, a new current Surface generation, and a successful nonobsolete native result with matching inputs. Sticky active failures cannot be erased by later stale successes. Export remains an immutable foreground snapshot; callbacks caused by the subsequent file picker cannot retroactively satisfy the Home test. Existing Phase 8 UI is not changed by this analysis.

The user accepted the remaining Phase 8 Home/return requirement on October 13 and directed implementation of this successor gate; the acceptance receipt distinguishes confirmation from measured events. This deconstruction makes no full Atlas load, camera collision, playable client, networking, FPS, startup or zoning claim.
