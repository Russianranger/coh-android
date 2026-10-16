# Saved catalog to authenticated asset resolution

This is a read-only next-blocker audit at integration revision
`140ee62d7b648de737fcec5e7d80b52bfbb9ae67`. Exact source and public-interface
blob identities are in `evidence/asset-resolution-audit.json`. The inspected
asset, bridge, renderer, appearance and offline-world paths are unchanged from
the accepted continuation checkpoint `cda93d96f8696e6a0f2ec6940a0c96e5b852f281`.
This audit neither grants ownership of those modules nor qualifies new runtime
behavior. Any later integration must check intervening changes with their owner.

## Concrete blocker after the saved catalog

Original `sendDef` sends `def->model->name`. It does not send the model's GEO
filename, archive identity, texture dependencies, model trick, resolved material
profile, or geometry bounds. `groupModelFind` resolves the model through the
separate loaded object-library name index. A catalog file's `fullname` is not
proof that its named geometry belongs to the corresponding `.geo` file.

Worker A confirmed that the current disposable capture candidate preserves
exact saved-definition records and original footers, but does not export an
independent loaded object-library/model-to-GEO map or versioned trick/material
tables. Its existing external source/profile binding remains required. This
audit does not change that candidate or imply a successful runtime capture.

A resolver that substitutes a guessed file path or accepts only the current
name CRC would therefore establish the wrong identity boundary. No production
resolver is added in this checkpoint: its necessary authentic lookup inputs are
not available. Existing topology/metadata preparation remains useful and closed
to rendering while those inputs are acquired.

## Original resolution chain

| Boundary | Original source functions | Required behavior and input |
|---|---|---|
| Definition geometry | `Game/src/group/groupnetrecv.c`: `getGeo`, `receiveDef` | Resolve the received model name, then apply model trick flags. The prior `setClientFlags` call also resolves explicit definition textures and TexWord properties. |
| Public object name to GEO | `Common/group/group.c`: `groupModelFind`; `Common/group/groupfilelib.c`: `groupGetPublicName`, `groupNameIdx`, `objectLibraryEntryFromObj`, `objectLibraryEntryFromIdx` | Strip directory for the query; public-name handling removes the final clone suffix only for names ending in `&`; library lookup removes the `__` trick suffix. Preserve the selected original library row and its `dir_idx`/file name, then change that file extension to `.geo`. |
| Model within the GEO | `Common/seq/anim.c`: `modelFind`, `compareModelNamesAndLengths`, `compareModelBSearch` | Case-insensitive comparison of the exact model base before the first `__`, with lengths compared as well. Do not choose an arbitrary prefix match or the first model. Duplicate equivalent model keys must be treated as ambiguous unless source selection is independently established. |
| Model trick | `Common/seq/anim.c`: `modelInitTrickNodeFromName`; `Common/seq/tricks.c`: `trickFromObjectName` | A model containing `__` selects the suffix; otherwise the complete model name is a trick lookup key. The loaded trick table and its generation are separate inputs. Missing required tricks remain unresolved. |
| Definition/model semantics | `Common/group/groupfileload.c`: `groupSetTrickFlags`, `groupSetLodValues`; `Game/src/group/groupnetrecv.c`: `groupSetDrawInfo` | Model tricks affect LOD, visibility, volume/collision flags and shadow distance. Client auto-LOD models can add model dependencies; definition LOD overrides are reapplied. Raw received fields alone cannot reproduce these results. |
| GEO material partitions | `Common/seq/anim.c`: model texture-index/name tables; `Game/src/render/model_cache.c`: `modelSetupVertexObject` | Preserve each original triangle partition and texture-table identity. UV handling depends on the admitted material profile; no repartitioning or invented material is permitted. |
| Texture/material identity | `Common/seq/tricks.c`: `trickFromTextureName`; `Game/src/render/tex.c`: `texFixName`, `texFind`, `texFindComposite`, `texCheckForSceneMaterialSwap` | Texture tricks have direct-name and directory fallback lookup, extension/locale handling, and separate basic/composite tables. Composite lookup includes scene material swaps. Logical names are not authenticated archive paths. |
| Effective material | `Game/src/render/tex.c`: `texResetTrickBasedParametersBasic`, `texResetTrickBasedParametersComposite`, `texSetBindsSubComposite`, `texFindVerify`, `fixLightingScalesOnFallback` | Resolve actual texture layers, source defaults, ScaleST, shader family, lighting and sampler flags under an explicit capability profile. Loaded runtime capability/fallback state matters. A default such as grey/white/black must be an explicit source rule with an authenticated asset, never a missing-resource success fallback. |
| Per-definition replacement | `Common/group/group.c`: `createDefTexSwap`; `Game/src/group/groupnetrecv.c`: `setClientFlags` | Preserve basic versus composite texture swaps, tint, TexWord dynamic layout dependencies and their ordering. Unimplemented dynamic text, cube maps, water or other material families remain unsupported. |

The original helpers contain historical unchecked string operations. A future
native adapter must use bounded nonempty inputs and qualify supported semantics
against unchanged original functions with explicit safe fixture storage; copying
those operations into production is not an acceptable port.

## What the checksums establish

`groupInfoCrcDefs` hashes definition names in original file/slot order, using
`NAMELESS` for allocated inactive slots and omitting null slots.
`groupInfoCrcRefs` hashes each active reference's definition name and its first
child definition name, if present. These existing topology oracles do **not**
authenticate model bytes, transforms, textures, tricks or materials.

The independent per-file bounds checksum is produced by
`objectLibraryWriteBoundsFileIfDifferent` and checked by
`objectLibraryLoadBoundsFileInternal`. It hashes each public definition's raw
`GroupBounds` bytes followed by its exact name, in original order, through
`cryptAdler32Init/Update/Final`. `GroupBoundsMembers` contains binary32 values,
a recursive count and C bitfields. Its producer ABI, padding, bit layout and
original serialized record bytes matter. Reconstructing that checksum from
model AABBs or a host C struct is not equivalent. Existing saved-definition
import checks the supplied bounds-checksum identity; it does not yet recompute
that value from authenticated resolved geometry and source bounds semantics.

The follow-up import needs exact source bounds records or a separately qualified
decoder of matching `geobin/... .bounds` files, with original producer/consumer
ABI evidence. Source bounds verification and cryptographic asset provenance are
separate requirements.

## Existing public interfaces usable without edits

| Interface | Stable consumption contract | Admission limit or remaining obligation |
|---|---|---|
| `assets/coh_asset_loader.h` | `coh_asset_lookup`, `coh_asset_acquire`, `coh_asset_identity`, `coh_asset_release`, `coh_asset_resolve` | One loader-owner thread; immutable source generation; pins outlive views. Use exact nonzero generations. Recorded archive MD5 is explicitly **not** a verified digest. Verify external content identities before mounting/admission. |
| `assets/coh_asset_geo.h` | `coh_asset_geo_workspace/open/model/material/stream`, original delta kernels | Versions 0 and 2..8 are readable. Header workspace and pinned source must outlive borrowed views. Model/material parsing is not full draw admission or trick resolution. |
| `bridge/coh_asset_render.h` | `CohBridgeResolveMaterial`, `coh_bridge_acquire/mesh_part/prepare/submit` | Existing rigid bridge admits only GEO v0/v7, unit scale, supported rigid channels and material families. Resolve every material partition; exact source texture IDs and resolver generation are caller obligations. Existing default bridge CPU budget is 32 MiB, separate from loader/graph/GPU memory. |
| `renderer/coh_renderer.h` | Immutable geometry/material submission and explicit Surface lifecycle | Renderer kernels do not authenticate scene, entity or resource identity. Geometry borrowers must finish before retained resources are released. |
| `appearance/coh_appearance_render.h` | `coh_appearance_mesh_requirements/build`, `coh_appearance_render_part` | Existing v0/2..8 mesh conversion is an actor/rig contract. The render adapter admits source-qualified ColorBlend Dual only and requires an independently admitted rig/socket/pose. It is not permission to route arbitrary world GEO through a fake one-bone actor. |
| `offline-world/coh_offline_world.h` | `coh_offline_validate/select/transform/release` | Borrowed immutable generation; source-ready geometry/materials required before `ready=1`. Loader-owner selection, 256 instances/dependencies, explicit pin retirement. Origin-only preparation cells are not conservative render/collision bounds. |

Offline preparation's retained Atlas report lists 738 version-8 dependency
endpoints, 760 v0, 315 v7, 37 v5, 18 v2, 10 v4 and 62 uninspected. These are
offline metadata counts, **not** the pending captured server catalog or rendered
instances. They demonstrate why the rigid bridge's v0/v7 restriction cannot be
assumed to cover the real world. Broadening that protected bridge requires its
owner and independent decoder/material/GPU qualification.

## Smallest useful additive resolver after input capture

Implement an immutable `scenegraph`-owned asset index on the asset-loader thread,
without changing protected APIs or granting render permission:

1. Admit an externally authenticated manifest bound to source tree, server/map
   generation, archive/payload hashes, exact library rows, GEO model table rows,
   loaded trick/material tables, scene swaps and capability profile. A supplied
   SHA string alone is not proof of those bytes. Detect duplicate/ambiguous keys.
2. Build bounded indexes for library public-name to GEO identity, GEO/base-model
   to exact model row, and basic/composite texture identities. Preserve full
   source model/trick names and original slots. Resolve each graph definition
   once; publish only copied identifiers or explicitly retained immutable pins.
3. Open authenticated GEO bytes through the existing reader and compare the
   selected full model name, index and every original material partition with
   the manifest. Return exact source dependencies, unresolved semantic masks
   and required memory; do not mark a draw ready from name matching alone.
4. Qualify a deliberately narrow material profile against unchanged original
   model/trick/texture functions. Reject any unsupported flags/LOD/texture word,
   swap, lighting or shader semantics atomically. Feed only admitted rows through
   `CohBridgeResolveMaterial`, with a new resolver generation on semantic change.
5. Include old/candidate index, retained raw pins, GEO header workspaces, decoded
   geometry/materials, catalog, graph generations and renderer resources in the
   aggregate transaction budget. No name scans, source I/O or allocation belongs
   on the render thread. Old pins retire only after consumer acknowledgement.

Qualification must cover exact original lookup comparisons; clone/trick/case
ambiguity; dictionary/asset-generation mismatch; missing material chains;
same-name/different-payload substitution; checksum mismatch; every preparation
failure and cancellation; bounded large indexes; old-generation retirement;
ASan/UBSan; Android build/execution. Real catalog binding and resolved source
assets still require their own evidence. No accepted APK rebuild or device test
is justified by this audit alone.
