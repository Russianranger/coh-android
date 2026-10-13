# Phase 6 shader and material contract

This is a bounded reconstruction of the stock **HW_SKINNED / COLORBLEND_DUAL** path. It uses a real geometry part and its default primary texture plus the original stock grey fallback. It does not reconstruct the complete Arachnos Wretch NPC costume, animation, bump maps, cubemaps, shadows or all material variants. Parameters are controlled fixture values, not a capture of a running game's state.

`source-hashes.json` pins the eight original Cg/include files and the relevant renderer/material source. `reference-shaders/` preserves the original file bytes and headers. `shader-contract.json` pins the three GLSL ES 3 source files and records their limits and validation scope. The Python oracle evaluates source semantics independently of those GLSL files; it is not an execution of the old Cg compiler or an original-game image oracle.

## Why this is the smallest faithful material path

`Game/src/render/thread/rt_bonedmodel.c:294-320` accepts dual-color, bump dual-color and multi materials for regular boned draws. A modulate-only skinned fixture would combine original shaders outside that regular draw path. `Game/src/render/rendertree.c:496-532` promotes an ordinary skinned material to `BLENDMODE_COLORBLEND_DUAL` when the bump/multi paths are not selected. `rt_shaderMgr.c:482,1010` maps that material and draw mode to `colorblenddualfp.cg` and the `vp_master_vp.cg` skin/diffuse variant.

The chosen real part is `GEO_Sleeves_Wretch` in `v_arachnos_wretch_sleeves.geo`: 116 vertices, 198 triangles and three local bones with global identities `[9,5,7]`. Its geometry default texture is `Sleeves_Wretch_Base.tga`. The generic fallback is the original grey texture, as `tex.c:1036-1044` selects `grey_tex` when no generic mapping is specified; `tex.c:2774,2791` finds/loads that real asset. The recovered `grey.texture` is an 8x8 ARGB8888 DDS with four mips and RGBA `(128,128,128,255)` pixels. Its wrapper SHA256 is `b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013`.

The NPC costume definition is a separate binding: `v_arachnos_henchmen.nd:973-981` names `Skin_Wretch_Base`, `Texture2 none` and costume colors. `costume_client.c:396-410` prefixes non-explicit texture names with the body-part texture name. The native fixture uses the geometry default binding and controlled colors; it does not claim to reproduce those NPC costume overrides.

## Bone inputs and conventions

The file has one U8 weight and two U8 row indices per vertex. Original `model_cache.c:469-472` computes `float(byte) / 255.f` and its complement. These are two influences, not four. The shader uses `weights.y`; original `vp_master_vp.cg:109-124` treats each index as **already multiplied by three**.

Palette slot `j` maps through the model's `bone_ID[j]` to `SeqGfxData.bpt`. `renderbonedmodel.c:137-158` folds the socket offset into each transform's translation. `rt_bonedmodel.c:197-229` uploads three vec4 rows per affine transform:

`[mp[0][k], mp[1][k], mp[2][k], mp[3][k]]`, for `k=0,1,2`.

The geometry format supports at most **15** local bones. The original shader stores 48 vec4 rows; at most 45 rows are used by this format. All row indices must be nonnegative multiples of three and `index + 2 < actual_bone_count * 3` before drawing. The renderer must use integer vertex attributes for `aRowIndices` at location 5, not normalized shorts.

The original GPU helpers in `functions.cgh:565-584` interpolate two transformed positions and **normalize the blended normal**. The old CPU `DeformObject` path does not normalize and is a different contract. The independent CPU control for this native shader must use the GPU helper's normalized result.

`Game/src/render/model_cache.c:92-97` flips both texture-coordinate V values with `1-V` before upload. The geometry decoder's raw UV is a different view from this prepared VBO input. The fixture must apply this source-derived preparation once, then the shader reads UVs unchanged. `tex.c:878-882` sets both bind scales to one when no texture option is selected; this fixture declares that unit-scale branch. It does not implement the complete texture-trick resolver or the source's optional CPU scale processing in `model_cache.c:111-149`.

`skinned_dual.vert` exposes view position, normalized normal, projected position, lighting color and fog coordinate as outputs. The initial transform-feedback comparison can capture `vViewPosition` and `vNormal` as six floats per vertex. Parameters and palette rows must be binary32 values, with explicit absolute/relative tolerance when compared with the scalar binary64 oracle. A proposed initial geometry tolerance is `2e-5`; report measured maximum errors and do not loosen it silently.

## Original material arithmetic

`functions.cgh:598-605` first mixes constant color 1 toward color 0 using the dual texture's RGB channels, then mixes toward white using **base alpha as a tint mask**, then multiplies base RGB. Output alpha is **dual alpha times constant color 0 alpha**. Base alpha and interpolated vertex alpha are not coverage multipliers.

`colorblenddualfp.cg:48-51,82` multiplies RGB by four times interpolated vertex RGB and applies fog. `vp_master_vp.cg:200-202` computes vertex lighting as saturated normal/light dot product times diffuse plus ambient. Source inputs already specify the light vector; the translation does not introduce another normalization of the light.

Fog uses view-space radial distance `sqrt(dot(position,position)+1e-16)`, calculated per vertex. It is interpolated before the fragment calculation. `functions.cgh:157-162` calculates the factor `clamp(inverse_range * (fog_end - fog_coordinate), 0, 1)` and mixes fog RGB toward material RGB. Alpha is unchanged.

Original `rt_init.c:44-57` selects clockwise fronts, back-face culling, LEQUAL depth, source-alpha blending and `GL_GREATER` alpha testing with reference zero. GLES implements the alpha test with `discard` unless `alpha > reference`. Equality fails. `rt_tricks.c:448-466` also contains explicit cutout/alpha-reference variants; controlled reference cases cover their comparison arithmetic without claiming that the selected geometry enables those tricks.

For a normalized RGBA8 target, the original same blend factors apply to **all four channels**:

`result = source * source_alpha + destination * (1 - source_alpha)`.

Thus output alpha is `source_alpha² + destination_alpha*(1-source_alpha)`. It is not the result of separate alpha blend factors. Fixed-point source, destination and factors are clamped before blending, as specified in [OpenGL ES 3.2, section 15.1.5](https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf). The oracle includes RGBA8 clear quantization and final normalized-byte quantization. The pixel gate allows at most two quantization units per component.

## Fixed binary material oracle

`build_material_reference.py` exports `prepare` and `generate`, with this signature:

```python
binary, case_metadata = prepare(texture0_rgba, width0, height0,
                                texture1_rgba, width1, height1)
```

Texture bytes use the ordinary GPU role: generic DDS decoding retains alpha. The legacy raw CPU DDS conversion's opaque-alpha exceptions must not be applied globally to these textures.

The binary filename is `material-reference.bin`. A 48-byte little-endian `<8s10I>` header contains magic `COHMAT6\0`, version 1, output width 64, height 64, case count 18, record size 112, primary width/height, secondary width/height and a zero reserved word.

Each case consists of a 112-byte `<26f2I>` parameter record followed immediately by `64*64*4` expected RGBA bytes. Record fields are six vec4s: constant 0, constant 1, vertex color, fog parameters, fog color and clear color; then fog coordinate, alpha reference, flags and reserved. Flag bit 0 enables source-alpha blending. Flag bit 1 selects the controlled dual swatch described below; allowed flags are zero through three. Fog parameters use `.z = end`, `.w = inverse range`.

The first 14 cases use the two real assets and test tinting, colored lighting, no/middle/full fog, zero/half/full fade, strict alpha thresholds, bright output clamping and blending over a destination with nonzero alpha. The original grey map has constant RGB and opaque alpha, so this real pair alone cannot detect every mistaken dual channel/alpha calculation. Four additional diagnostic cases replace only the dual sampler with a controlled 1x1 RGBA8 swatch `(51,153,230,128)`. They cover colored dual masking, half fade with blending, alpha reference 0.5 passing and reference 0.6 rejecting. The swatch is generated test input, not another original asset. It must be bound only for flag bit 1 and the real dual map restored for other cases.

The inputs are rounded to binary32 before scalar evaluation. The generator records actual discard/pass counts and labels each case `original_asset` or `controlled_swatch`. It does not infer texture coverage from labels. The selected real primary's alpha is nonconstant, so base-alpha masking does not erase the diagnostic dual-color contributions. Other real dual-alpha maps and material families remain outside this fixture.

Sampler settings for this controlled arithmetic gate are nearest filtering, clamp-to-edge and level zero. At pixel `(x,y)`, the quad samples normalized UV `(x+.5,y+.5)/64`. Texture row zero is uploaded as GL row zero, and expected FBO bytes have no Y flip. This isolates material arithmetic. It does not qualify the source's mipmapping, LOD bias, wrapping or filtering fidelity. The source sets a -2 texture LOD bias in `rt_bonedmodel.c:485-486`; that separate sampler gate remains open.

## Objective qualification

1. Validate the actual geometry, local palette, indices, weights and texture hashes before the GPU upload. Include real vertices with nontrivial two-bone weights.
2. Compare GPU transform feedback with the independently prepared scalar geometry outputs under bind and controlled noncommuting poses; report counts and maximum position/normal errors.
3. Draw the actual mesh with GPU skinning and compare with a CPU-posed control using the same material. Report useful interior coverage and any explicit triangle-edge mask; reject an empty or near-empty comparison. This tests native skinning equivalence, not original-game appearance.
4. Render all 18 material cases, compare every 64x64 RGBA component against the scalar reference within two normalized-byte units, and report the 14 real-pair cases separately from the four controlled-swatch cases. Test dual alpha/channel calculations, alpha equality, zero fade, full/middle fog and destination alpha behavior.
5. Recreate contexts and surfaces, resend all buffers/palettes/textures/uniforms and repeat. Verify actual window presentation and resource cleanup. Offscreen color comparison does not qualify Android compositor alpha.
6. Keep physical Thor qualification separate from hosted compilation or emulator results. Original Cg execution, captured runtime parameters, a real animated costume, full material catalog and game integration remain future gates.

The source-semantic Python boundary checks and binary-layout synthetic checks have passed. Shader execution, actual mesh/texture parity and physical device results must be recorded by the renderer's separate build and device evidence.
