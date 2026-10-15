# Gate31 resource and render bridge

Pinned starting repository revision: `3c5da1d8cd501d778e270d395109d40666fbe37a`.
Original source revision: `0b75ade0c801735e10c5798f641948a45cc50488`.
Original data revision: `d51533ec8e6a9cf726b9214968077a05fdcf19f3`.

This additive module extends the existing appearance assembly. It does not
replace the accepted Wretch actor or infer a skeleton from an appearance prefix.
The existing `evidence/host.json` assembly receipt remains unchanged. New
qualification is recorded separately in `evidence/render-bridge.json`.

## Public interface and ownership

`coh_appearance_render.h` adds two independent paths:

1. `coh_appearance_mesh_requirements` and `coh_appearance_mesh_build` convert one
   already-resolved original GEO model into the unchanged `COHMESH1` contract.
   The existing bounded GEO/delta readers perform the decoding. Source global
   bone IDs, weight division/complement, palette row division, vertex order,
   triangles and `modelFixup` UV V flip are preserved. An unboned source model
   uses the caller's original socket as its explicit one-bone fallback. Multiple
   source materials remain separate ranges in the pinned GEO table. No resource
   is selected by guessed filename, mirrored or substituted.
2. `coh_appearance_render_part` takes an immutable mesh, a source-compatible rig
   and composed pose, an explicitly selected source material range, and two
   texture identity bindings. It uses the unchanged palette and CPU skin kernels
   and emits an existing `CohRenderDraw` in caller-owned vertex/index arenas.
   This portable bridge is for integration and comparisons, not a claim of GPU
   skinning or an optimized frame path. It supports the already-qualified
   `COLORBLEND_DUAL` material and original effective costume colors. Other
   material families return `COH_UNSUPPORTED`.

| Owner | Retained state and responsibility |
| --- | --- |
| Appearance/actor owner | Actor ID, appearance generation, exact source costume delta and body type |
| Asset owner | Pinned GEO bytes/header, canonical mesh, exact source path/model, immutable geometry identity |
| Sequencer/rig owner | Rig ID/generation, matching source hierarchy, composed pose and increasing pose generation |
| Material/GL owner | Actual texture resolution/upload, exact logical source texture names, material flags and Surface generation |
| Renderer owner | Synchronous consumption of output vertices/indices through flush; resource upload/cache policy |

The bridge rejects actor, rig, body, appearance and Surface generation
disagreement. Model identity is source case-insensitive and ignores `__trick`
suffixes, matching existing appearance lookup. Path and texture identities are
case-insensitive exact logical identities. A texture named `none` remains the
original unbound marker; the material owner must explicitly bind its qualified
white texture when needed. This interface checks caller-supplied identity
agreement, not cryptographic authenticity; import provenance remains the asset
owner's responsibility.

Resource generation and Surface generation are distinct. Surface recreation
replaces GPU handles, while the canonical mesh/rig remains immutable. Because
the bridge CPU-skins vertices, `CohRenderGeometry.generation` is the actor pose
generation; callers must advance it when the input pose changes. Skinning cache
reuse has not been enabled or performance-qualified.

All borrowed resources must remain pinned for synchronous execution. Output
vertex/index arrays must remain alive through renderer flush. Conversion runs on
an asset/control thread. The module allocates no heap, opens no files, starts no
threads and makes no GL or network calls. Caller buffers may not alias inputs or
one another. Conversion scratch and frame arenas may change on error, but public
result objects, published mesh bytes and diagnostics remain unchanged on failure.

## Actual qualification

| Evidence | Result | Boundary |
| --- | --- | --- |
| Native conversion | 402 genuine v8 models, 79,687 vertices, 271,239 indices | Individual parts, not complete costumes |
| Source oracle | 1,227,483 scalar elements, byte exact | Executed original delta plus source GPU UV/weight/row expressions |
| Accepted Wretch converter regression | 31 genuine v2/v3 models, 99,108 scalar elements, byte exact | New converter only; accepted application unchanged |
| Male/Female/Huge neutral rig/socket compatibility | 402 models at 3 poses each, 1,206 part poses | Genuine source rigs; custom morphology and full costume closure remain open |
| Defensive tests | 521 capacity, malformed bone, identity and generation cases | Original legacy oracle receives only authenticated valid source inputs |
| ASan/UBSan | Passed | LeakSanitizer disabled for restricted `/proc`; no module heap calls |
| Android build | ARM64 API26 linked with undefined-symbol rejection | Native library build, not Android execution |
| Android emulator / physical Thor | Pending | No acceptance claim |

`--gpu` additionally qualifies bounded host Mesa transform-feedback packets for
one original pants part per body type, three authentic neutral poses and three
lighting modes, across two real GL context generations. It uses the unchanged
renderer vertex shader and the new CPU-skin bridge output. This is untextured
part-transform evidence, not a complete actor image, original costume material,
GPU skinning, Android/Adreno measurement or full Gate31 completion. Exact GPU
driver, comparisons and errors are in the separate receipt.

The actual host GPU run passed 132,840 scalar comparisons across the two
contexts, maximum absolute error `1.14856762e-6` against tolerance `1e-4`, on
Mesa llvmpipe OpenGL ES 3.2. The GPU fixtures are explicitly partial pants parts;
they must not be reported as three complete rendered characters.

The seven GEO resources were reacquired with the unchanged bounded acquisition
tool: exact ZIP member identity, stored/decoded length, CRC and independent
manifest SHA are checked. Full outer/inner archive hashes are published
provenance rather than a subset-download verification. No binary assets are
committed. The Wretch source geometry was similarly recovered and each consumed
file rechecked against existing pins; its unnecessary texture acquisition was
not needed for this converter proof.

Neutral family rigs are the sequencer worker's regenerated
`{male,fem,huge}-jump_n_smash.bin` files. Their exact SHA values are recorded in
the receipt. Sequencer source receipts own raw-key, hierarchy and blending
comparisons; the appearance receipt adds actual mesh palette/socket compatibility.

## Integration

1. Link `coh_appearance_mesh.c` and `coh_appearance_render.c` alongside the existing
   appearance adapters and unchanged `coh_mesh.c`/`coh_character.c` kernels.
   `coh_character.c` already includes animation; never compile animation twice.
   The opt-in CMake `COH_APPEARANCE_WITH_RENDER_BRIDGE` option requires
   `COH_APPEARANCE_WITH_ADAPTERS` and one caller-provided
   `coh_appearance_mesh_kernel` target. Reuse an existing mesh target if present.
2. Resolve exact costume delta identities using the asset owner, then resolve the
   model once with `coh_appearance_geo_model`. Convert each immutable model once
   on the control thread. Keep its source material table and bone/rig provenance.
3. Select the matching sequencer rig. The new sequencer actor API's active rig
   and returned composed pose can be passed directly; copy its actor, rig and
   appearance generations. A null morph means a separately-qualified neutral
   rig, not an implicit default morphology for an authored NPC. Existing custom
   Huge/Wretch morphology remains available; Male/Female custom morphology is
   still unsupported.
4. For each source material table range, supply `first_triangle*3` and
   `triangle_count*3`, source-qualified material settings and resolved logical
   texture names/handles for the current Surface. Allocate frame arenas outside
   real-time callbacks and submit the returned draw before their reuse.
5. Preserve accepted Wretch as its own actor slot. A missing part, texture, rig
   or morph is an explicit missing dependency, not a substituted resource.

This commit requires no shared renderer, support application, JNI, workflow,
session, live-server or packet changes. A coordinator may opt into it later.
Rollback is disabling the opt-in target/adapter calls or reverting this additive
appearance-only commit. Immutable imported assets and accepted APK 0.3.0 remain
unchanged.

## Remaining Gate31 work

Male/Female/Huge complete authored costume closure still needs every real
geometry/texture attachment, the authored morphology, source material/trick
selection, complete image comparisons and Android/Thor execution. The real
partial corpus is not a complete costume pack. Some authored Male paths remain
absent from Base; `v_male_*` is not an implicit alias for missing `male_*` files.
Cloth/capes, FX attachments and high-quality material variants remain outside
this bridge. Full Gate31 remains open.

To reproduce only the changed module qualification:

```sh
python native-android/engine/appearance/check_render.py \
  --source-root /path/to/verified/source \
  --corpus-root /path/to/appearance-corpus \
  --wretch-corpus /path/to/wretch-source-geometry \
  --families-root /path/to/verified/showcase-build/families \
  --sanitize --gpu --ndk /path/to/android-ndk-r28c \
  --output /path/to/render-bridge.json
```
