# Phase 9: bounded source world and camera gate

This phase implements an isolated native Android source-world and camera probe, package `org.coh.worldprobe`, version `0.1.0-phase9`. Accepted Phase 6–8 implementations remain unchanged. The original [scene recovery receipt](evidence/phase9/scene-recovery.json) preserves the initial source deconstruction; acquisition and implementation now recover the authentic geometry and texture members. Actual Android qualification is pending the hosted gate.

## Selected real scene branch

The first world fixture will select one authored `modern_bench_2wide` branch from Atlas Park. The recovered GEO version 7 model is `modern_bench_2wide__mbench`: one source root with 256 vertices and 188 triangles. It has two actual material partitions: Signmetal (48 triangles) and modern_bench (140 triangles). Each canonical draw retains its 256 source vertices, for 512 GPU input vertices and 564 total indices. The two seats are geometry within this one model, rather than two independently instanced model roots.

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

The inner archive is 207,803,201 bytes. Its published SHA256 is provenance, not a locally verified whole-archive hash. The [world corpus pins](tools/world_fixture/pins.json) now include complete SHA256 identities for the GEO and four authentic texture wrappers: Signmetal, grey, modern_bench and white. A fresh bounded acquisition used ten exact ranges and 571,276 downloaded bytes, stable archive ETags, exact local ZIP names/envelopes, and all CRC32/member SHA256 checks. Whole archive hashes remain declared provenance. Stock grey/white pixels are decoded from real wrappers, not fabricated textures.

`upstream/i24/data/tricks/streets/elements/streets_misc.txt` declares `modern_bench.tga` with `Surface METAL`, `Blend white.tga`, and `BlendType ColorBlendDual`. This makes the accepted dual-color shader family a concrete candidate. The library `.rootnames` and `.txt` identify `modern_bench_2wide` directly. The GEO texture table also exposes Signmetal, which uses the original MULTIPLY program with authentic grey. The world shader translates both original fragment programs: MULTIPLY has RGB gain eight, and COLORBLEND_DUAL has RGB gain four. Source runtime UV duplication and V inversion follow the original static model-cache path. The recovered `__mbench` suffix associates the authored far/fade settings (250/75); runtime LOD selection remains unqualified. No static vertex-color stream is present in the recovered GEO. Full source lookup verification over all 1,585 original trick files is required before CI preparation marks material resolution qualified; local partial-source results remain provisional.

Linear mip-zero filtering is a previously recovered source default, but the selected world wrapper's flags, addressing and mip policy remain unqualified. Controlled lighting can qualify shader arithmetic while retaining original Ambient metadata; it does not establish original Atlas ambient/vertex-light fidelity.

Concrete benches are deferred because their original definition adds a baked shadow model. Bus-stop glass is deferred because its trick requires reflection texture state and `SimpleAlphaSort`. The pillar group is deferred because its full authored closure contains 43 pillars and a city wall across more than 3,000 scene units.

## Camera and qualification contract

Recover the unchanged source bodies of `gfxSetViewMat`, `rdrFixMat`, `rdrSetupPerspectiveProjection` and `rdrSetupFrustum`. The original view conversion transposes the camera rotation and mirrors X using `diag(-1,+1,+1)` before computing view translation. Substituting a generic look-at matrix would lose that source convention. A bounded test camera is explicit controlled input, not a captured gameplay camera. Aspect/FOV policy must state whether the original gameplay adjustment above 4:3 is selected.

The proposed host oracle executes unchanged source degree conversion, matrix construction/composition, view conversion, perspective and geometry-expansion kernels under documented minimal compatibility wrappers. Independent references then verify world positions, normals, eye/clip-space outputs and selected material arithmetic. GPU transform feedback and pixel checks must require useful geometry coverage, source culling and depth behavior. Controlled overlap/near-plane witnesses must be labeled separately from original map transforms. A full original scene sorter is not established by one branch; source pointer tie comparisons need an explicit portable policy before broader sorting qualification.

The future probe must distinguish passing render checks from completed lifecycle qualification. Before background recovery, its status should say **Render checks passed; lifecycle check required**. A green gate requires actual two-axis resize, successful Surface recreation, an explicit Home test with recorded pause/stop and required destruction observations, then resume, a new current Surface generation, and a successful nonobsolete native result with matching inputs. Sticky active failures cannot be erased by later stale successes. Export remains an immutable foreground snapshot; callbacks caused by the subsequent file picker cannot retroactively satisfy the Home test. Existing Phase 8 UI is not changed by this analysis.

The user accepted the remaining Phase 8 Home/return requirement on October 13 and directed implementation of this successor gate; the acceptance receipt distinguishes confirmation from measured events. This deconstruction makes no full Atlas load, camera collision, playable client, networking, FPS, startup or zoning claim.

## Implementation and host evidence

Three bounded assets drive the isolated package: `world.bin` stores original Pos/PYR inputs, controlled camera inputs, canonical meshes and authentic RGBA textures; `world-reference.bin` stores comparison matrices/geometry; `material-reference.bin` stores twelve independent shader cases. Runtime rendering computes its matrices from source inputs. Golden matrices and geometry are comparison data and do not drive the preview or actual-image path.

Original source traversal composes view with each parent/child matrix before transforming vertices. The native implementation retains that binary32 operation order and the original camera X mirror. The [unchanged source oracle](evidence/phase9/original-world-parity.json) passes 40,744 float components across fifteen functions; the independent reference passes 40,680 components. The [geometry oracle](evidence/phase9/original-delta-parity.json) checks 3,124 original scalar elements byte-exact. The [host proof](evidence/phase9/host-world-proof.json) passes 40,320 components and 6,545 ASan/UBSan checks, including 6,000 mutations. These tests use documented minimal source compatibility wrappers, not an original Game execution.

The new GLES3 renderer checks 39,936 GPU components per context (world positions, unnormalized eye normals, eye positions, homogeneous clip coordinates), six perspective images, useful coverage for each partition, twelve material cases, and five labeled depth/culling/near/far diagnostics. It retains a 1e-4 absolute transform tolerance, two RGBA byte units and a two-pixel triangle guard. World sampling uses linear mip-zero filtering; analytic shader cases and exact window transfer use nearest sampling. Lighting is controlled neutral ambient 0.25 with zero diffuse/specular; source Ambient/TexSwap/LOD metadata is retained without claiming the full Atlas lighting or cubemap pipeline.

Each check creates/releases two EGL contexts and presents two bounded 45-frame camera previews. The [host Mesa smoke receipt](evidence/phase9/host-renderer-smoke.json) passes all renderer checks in a Linux pbuffer harness, with zero errors and mismatches; it is explicitly not Android or Thor qualification. The [UI host checks](evidence/phase9/ui-host-checks.json) verify sixteen lifecycle cases. Actual SDK/NDK, lint, package, source-trick and Android13 SwiftShader execution remain the hosted gate.

The retained REA-assisted client checkpoint was queried read-only again with a 90-second deadline, no import/autoanalysis/client execution, and all ten files unchanged. The [world seam receipt](evidence/phase9/rea-world-seams.json) includes raw anchors for group loading, graphics/window code, render tricks and `gfxSetViewMat`; the inherited partial database has no recovered references to them. No new source-to-binary function identity is claimed.

## Device test

Install **CoH Native World Probe** beside the accepted character probe. Confirm the blue bench seats and metal frame during the camera preview. Resize, wait; recreate, wait; press Home, return and wait. This package displays a green **WORLD GATE PASSED** only after the callback-based background/return sequence as well as both actual dimensions and Surface generations. Export the current JSON report and return it with a screenshot.
