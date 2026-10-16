# Complete neutral Male appearance preview — 2026-10-16

The appearance-owned actor transaction and optional GLES owner assemble and draw a complete neutral Male costume: source-menu Pants Tight, Chest Tight, legacy Head, Gloves Smooth, Boots Smooth and Hair Martial Arts. Six costume choices become eight original socket draws, 943 vertices and 3,792 indices. Original GEO, original textures, source color/skin routing and the source-qualified Male jump_n_smash neutral rig are used. The original menu permits the explicitly selected None mask for five parts; preparation verifies each pinned selector and its Include. The white None binding is an engine semantic, not a fabricated replacement for missing texture data.

This is a selected custom costume, not the source Clear button output or an authored NPC morphology. Female/Huge complete rendering, custom proportions, arbitrary multi-material meshes, exact original culling/trick/lighting image equivalence and multi-actor rendering remain open. This does not close Gate 31. The unchanged Wretch path remains the support client's default regression baseline.

## Prepare and integrate

From a clean repository with Python, zlib and a C compiler:

```sh
python native-android/engine/appearance/prepare_actor.py --output /tmp/coh-male --source-root .
```

The tool verifies the existing tracked character-avatar-defaults.zip, range-fetches only one pinned original legacy face texture plus two pinned animation members, reuses the existing canonical geometry/animation decoders and produces appearance-male.bin plus actor.json. It never fetches the complete Base pack. `--assets-root` and `--rig` permit verified recovered inputs. Source files can be read from a sparse checkout's Git object database. Exact package: 1,673,302 bytes; SHA256 `bda4a9f1098281d3ddc32842aeda792e83cebb0be3185d9458e3402032f77df9`. Large source archives remain external; this selected fixture is 1.60 MiB.

Compile coh_appearance.c, coh_appearance_adapters.c, coh_appearance_mesh.c, coh_appearance_render.c, coh_appearance_actor.c and coh_appearance_preview.c with the existing character, asset loader/GEO, canonical mesh and generic renderer/GLES sources exactly once. No shared renderer edits are needed. The preview header documents ownership. Load and SHA-verify the package off the frame path; create performs no GL or I/O. Retain immutable package bytes until destroy. Call draw only from the GL owner, after binding the destination framebuffer. Surface generations must identify context lifetimes; loss with context_alive=0 never deletes old names in a replacement context. Keep Wretch default and expose an explicit Male preview toggle and accurate visible-body label. No networking is involved.

The whole-actor transaction accepts complete snapshots, not deltas. Each non-clear socket requires full admitted mesh/material coverage. Errors leave published descriptors unchanged; use separate staging vertex/index arenas because failed work can write them. geometry_id must identify rendered actor/part storage, not merely shared source geometry. External 64-bit generations require a range-checked adapter before entering the existing 32-bit bridge; no such narrowing occurs in this private preview.

Stats must be copied by the render owner into an application snapshot. owned_cpu_bytes covers preview-owned arrays and struct, excluding generic backend CPU allocations; borrowed_package_bytes is shared immutable source storage; texture_bytes counts retained source RGBA even after loss, not active GPU residency. GPU buffer bytes become zero on context loss. No full-process memory or allocation-free backend proof is inferred from these counters.

## Qualification and limits

Receipts in qualification/actor-20261016 preserve source/asset pins, host negatives, original-source comparisons, ARM64/x86_64 compile results and real Mesa GLES context tests. Host and ASan/UBSan each passed 93 negative cases and 64 create/destroy cycles. The original geometry oracle matched 1,160,514 scalar elements across 789 real supplemental models. The original costume oracle matched 137 identities and 192 color bytes plus 14 branch cases (existence callbacks mocked there; actual selected asset closure is separately verified during preparation). Source-qualified canonical rig SHA matches the existing sequencer family receipt.

The initial production GLES owner exercised three source poses in two contexts, but those samples missed source root movement outside its fixed camera. Actual Android screenshot review caught cropping and rejected visual qualification. The corrected owner now fixes the first source pose, fits its complete bounds into the centered 70% of the actual viewport and preserves the package. Fresh tests verify identical restored images and stable counters over 100 further frames and recover from injected partial submission and texture-upload errors. This is llvmpipe host GPU API execution, not Android or Adreno acceptance. ARM64 and x86_64 API26 shared libraries link with no undefined symbols. Worker A owns Android application/emulator integration and its independent receipt. Physical Thor acceptance is pending.

Low-quality source dual-texture shaders are reused; neutral lighting is chosen for this isolated camera. Hair is alpha blended and two sided; full original trick/material state equivalence is not established. No Female/Huge or multi-actor fallback is silently shown. Further complete body fixtures need authenticated remaining geometry/textures, matching family rig and explicit original morph/material qualification.

Rollback: omit the preview source/asset and toggle in the optional support integration, then revert this appearance-only commit normally. No accepted application, shared live interface or primary-owned source was changed. Keep prior qualification receipts and accepted APKs.

## Android screenshot framing correction

Code 201 emulator screenshots showed only legs at the top of the landscape Surface. The camera was fitted to the first pose while local time advanced the original jump_n_smash root translation. This was reproduced on host at 1.2 seconds: landscape silhouette bounds were [823,0,984,278] on a 1920×790 framebuffer. The correction freezes the first source pose for costume inspection and calculates scale from both the original bounds and current aspect ratio. No original animation data or GPU kernels changed. The time argument remains validated but does not advance this inspection pose; source jump previews elsewhere retain their own scope.

`tests/preview_framing.py` checks 36 actual raster frames across 1920×790, 1080×959, 640×1280 and 1280×480, with nine clock values through 86,400 seconds and deliberately inherited nonzero viewport/scissor and disabled depth/color writes. The original owner fails; the corrected owner keeps the complete silhouette centered inside the fitted margins with identical images at every clock. Landscape bounds become [818,119,1102,671], portrait bounds [368,144,712,815]. Application overlays may obscure this region, so the application decides whether to show mock chat/tray while inspecting the costume.

Fresh receipts in qualification/framing-20261016 include before/after images, 110 context/failure-recovery frames, host/ASan/UBSan negatives and strict ARM64/x86_64 compilation. Corrected preview-owned CPU accounting is 153,536 bytes, buffer storage remains 67,976 bytes and the package hash is unchanged. These host images do not establish corrected Android visual or physical acceptance: the consolidated APK must be rebuilt and its actual screenshots reviewed.
