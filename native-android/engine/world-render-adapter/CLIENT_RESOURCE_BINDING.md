# CLIENT material/resource supplier boundary

The rigid GEO adapter now has exact authentic geometry and associated cached
texture **test inputs**. This is CPU source-resource qualification, with no
world/material publication capability. No fallback, white texture or invented
lighting binding is supplied. The actual Box model's ownership in the captured
Atlas generation has not been established. The later Neon legacy fixture is a
root-reachable source model/body lookup candidate with exact retained bytes; it
also does not establish matching directly opened live resource generation.

## Implemented sampling projection and authentic texture proof

`coh_wr_sampler_project` projects separately qualified final CLIENT sampling
values into a zero-handle renderer texture descriptor. It owns no pins and does
not authenticate its caller. It has no material/actor/world output. Source
`texSetupParamsFromBind` and the sampling block of `texCopyDirect` are compiled
unchanged against narrow GL-call observers. 1,280 source combinations exercise
clamp-over-mirror precedence, repeat, POINTSAMPLE, NOMIP and DDS counts. Two
production mutations must fail. Refusals leave output unchanged. JPEG, cubemap,
border, unsupported anisotropy/clamp modes and incomplete linear mip chains
refuse. POINTSAMPLE selects NEAREST for both filters even with mip storage.

`TexReadInfo.mip_count` comes directly from DDS `dwMipMapCount` **after** original
skip reduction (`ddsLoad` in `tex.c`), not the number of additional levels. Zero
is the original non-mipmap count; positive counts can select mip filtering.
The original upload's `<= mip_count` loop also stops when width and height reach
zero. This helper validates supplied level bounds independently; it does not
copy that loop or accept partial linear mip chains.

The authentic cached texture is recovered by `acquire_sampler_texture.py` using
existing bounded ZIP range code. Exact payload SHA and ZIP CRC are verified;
full archive hashes and original PIGG reacquisition are not claimed. Pins retain
the fully verified published manifest's original PIGG provenance. Raw bytes stay
outside Git. `check_sampler.py` admits the exact SHA **before** native execution.

- GEO partition name: `Box-1.tga`, from actual `FX_PraetorianBox_Open` fixture.
- Published texture: `data/texture_library/npcs/objects/praetorian_box/box-1.texture`.
- Texture SHA256: `c36001854f75ff7e8ef5304138537f1de4b71dcc3529a9a40f6093fde959df9a`.
- 43,990 bytes, 256x256 DXT1, 9 levels, 349,524 decoded RGBA bytes.
- Independent Pillow decoding of **every** mip exactly matches the protected CPU decoder.
- Cached flags192 are CLAMPS|CLAMPT. This does not establish effective CLIENT flags.

Original `TextureFileHeader.flags` is **TexOptFlags**. `BasicTexture.flags` is a
separate TexFlags enum. The cached header is not sufficient to infer final
`BasicTexture.texopt_flags`: `texResetTrickBasedParametersBasic` replaces that
field using `trickFromTextureDirName`. A filename suffix match likewise does not
establish `texFindVerify`, alias, locale, composite or scene-swap selection.

## Immutable full-mip CPU resource owner

`coh_wr_texture_acquire` now supplies actual retained texture bytes, without
inferring a material. It admits exact path/generation/digest, retains a protected
loader blob pin and one owned contiguous RGBA8 chain, and publishes only after
all declared levels finish. Every view survives loader trim. Release requires
borrowers/uploads to have finished, drops the blob pin, frees storage and nulls
the owner. No cached flag is relabeled as effective CLIENT state.

The whole explicitly configured loader reservation is charged **before** acquire;
its historical allocation peak must fit that reservation. The opaque public API
cannot inspect the loader's configured limit: the caller must configure
`total_bytes <= loader_reservation`. Source/digest/other resources/old textures
must be charged as external bytes. Owned chain bytes and struct fit an aggregate
cap (hard maximum256MiB), dimension/mip/decoded-size limits, with no transient
reallocation. This is an explicit working-set contract, not a process RSS cap.
Tests cover exact budget and one-byte-short refusal, allocation failure before
loader decode and owner allocation, wrong generation/digest, loader trim/pin
retirement, cancellation before/during/after all-level decoding and malformed
source rollback. Every owner level matches the independent authentic oracle.

This owner performs no GL upload. The current rigid material validator still
refuses MIP_LINEAR: that guard must remain until a qualified full-chain upload
and retained Surface binding supplier exists. Sampler projection can describe
future full texture creation; it does not emulate original subimage/cubemap or
inherited GL-state updates.

## Exact supplier prerequisites

| Supplier | Required retained immutable values | Current evidence boundary |
|---|---|---|
| SERVER resource capture + A join | Exact catalog/runtime snapshot/graph generation, COHRES bytes SHA, owner definition and original model/GEO row, GLD/model load state, model/trick/info flags, model scale/bounds and six source LOD values | A `coh_resource_join_sources` exposes raw owner observations; `match_index` proves their binding equality. Actual source runtime capture is retained; observed GLD/model states are NOT_LOADED/header-only. This is source ownership, not completed CLIENT asset/material resolution. |
| CLIENT texture resolution | Model partition -> effective TexBind/BasicTexture identity after directory lookup, normalization, aliases, locale, Basic/composite and **scene** swaps; matching client data/tricks generation | Not carried by SERVER COHRES or current scene CRCs. The fixture association is not a live resolved binding. |
| CLIENT shader/material producer | Effective TexOpt/model trick state, `texResetTrickBasedParametersComposite` / `texSetBindsSubComposite` selection, shader family/layers and fallback choice under pinned capabilities, bind scales, color/alpha/blend/depth/fog/glow semantics | Existing renderer supports a bounded subset; each unrepresented state must refuse. Source labels and nonzero SHA values are not semantic proof. |
| CLIENT sampling producer | Final `BasicTexture.texopt_flags`, selected target, effective anisotropy and clamp mode; `ddsLoad` post-skip dimensions/count and every retained mip | Pure source projection implemented. Authentic cached bytes decoded; effective client producer has not supplied a record. |
| CLIENT visibility/lighting producer | Selected LOD/reduction, inherited group/model tricks, visibility/fade and render ordering; appropriate baked vertex colors/lightgrid/environment lighting and effects | Source LOD floats and bounds alone do not select LOD or determine lighting. No default light/white replacement. |
| Resource owner | Exact asset path/SHA/generation, qualified material-generation/partition identity; CPU blob+material+texture pins and aggregate reservations; GPU names valid through flush and Surface recreation | Rigid owner retains CPU/material pins; texture owner retains blob+all RGBA levels. Sampler projection owns none. Additive GPU mip ownership and standalone EGL qualification remain separate from authentic material/Surface binding admission. |
| World/actor admission | Fully validated source transactions, root/child closure and transforms, authentic resources, complete selected-character identity/generation and atomic generation-consistent publication | Not granted by these CPU helpers or by source-only snapshots. |

A supplier may use A's raw `CohResourceSource`/binding identity to anchor the
first row and consume immutable views. `unresolved_client_semantics==1` is a
hard boundary: no raw SERVER observation may be relabeled as resolved CLIENT
material/capability/LOD state. These are client-only dependencies, not additional
fields to fabricate in the SERVER protocol. The retained SERVER source capture closes raw source observations; original CLIENT
semantic resolution and matching live generation are still needed.

`coh_wr_lod_project` now implements the complete numerical CLIENT
`modelCalcAlpha` projection from separately resolved inputs. It grants no LOD
model selection or visibility permit. See `CLIENT_LOD_AND_ZERO_ROWS.md` for exact
inputs and the boundary for retained zero-draw header rows.

## Qualification

```
python native-android/engine/world-render-adapter/acquire_sampler_texture.py --output /tmp/new-box-texture
python native-android/engine/world-render-adapter/check_sampler.py --actual-texture /tmp/new-box-texture/box-1.texture --output /tmp/new-sampler-proof.json
```

Host release, ASan (leak detection disabled) and UBSan results are recorded with
exact original/owned/protected dependency hashes. Original texture-header size
and flags/alpha offsets are compile-time checked. This does not execute Android,
GLES, an original CLIENT session, a live GROUPS transaction or the Thor.
