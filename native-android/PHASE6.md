# Phase 6: real mesh, skinning and material probe

This phase reconstructs one bounded part of the original character renderer for Android Bionic ARM64. The separate diagnostic package is `org.coh.materialprobe`, version `0.1.0-phase6`. It uses a real Arachnos Wretch sleeve mesh and the geometry's default material, with controlled palette, light, color and fog parameters. It is not the complete NPC costume or a playable client.

## Recovered contracts

- The version-three `.geo` fixture contains 116 vertices, 198 triangles and three draw-local bones, mapped to original global IDs `[9, 5, 7]`. Thirty-seven vertices exercise genuine two-bone blending.
- The original model loader expands one weight byte into two complementary float weights, flips the texture V coordinate before upload, and converts two encoded matrix-row indices into local palette slots. Native fixture views use checked offsets and fixed-width integers; legacy file pointers never become native pointers.
- The original GPU shader blends two transformed positions and normals, then normalizes the blended normal. The old software fallback leaves normals unnormalized and has a different contract.
- Each local bone supplies three affine vec4 rows. `Mat4` columns are transposed into these rows; the shader addresses rows using local slot times three. The source limit is 15 local bones, while this fixture uses three.
- The selected shader variant is hardware skinning, view-space diffuse vertex lighting, no texture-coordinate transform, and `COLORBLEND_DUAL`, without bump mapping, reflection, shadow maps or high-quality variants.
- The stock dual-color formula uses base alpha as a tint mask and secondary alpha times color fade as output alpha. Linear fog affects RGB. The GLES derivative implements the original strict `GL_GREATER` alpha test with discard.
- Source-over blending uses `SRC_ALPHA, ONE_MINUS_SRC_ALPHA` for all four channels. Destination alpha therefore follows the original same-factor rule, including the squared source-alpha term. The oracle includes normalized RGBA8 clamping and quantization.

See [the shader contract](material-probe/contract/README.md), [REA-assisted binary observations](PHASE6-REA.md) and the hash-pinned evidence under `evidence/phase6/`.

## Real fixture and controlled inputs

The source geometry is `player_library/V_Arachnos_Wretch_Sleeves.geo`, model `GEO_Sleeves_Wretch`. Its embedded default texture name is `Sleeves_Wretch_Base.tga`. The default material uses this real base texture and the real stock `grey.tga` fallback. The grey asset is an 8x8 ARGB8888 DDS; the base uses DXT5. The published fixture tools recover only the selected, hash-pinned release members using bounded HTTP ranges, verify their bytes, and package normalized RGBA8.

The NPC costume definition overrides the sleeve's texture, so this proof does not reproduce the complete Wretch costume. Identity and nontrivial controlled palette poses exercise the recovered shader contract; they do not reconstruct an original animation, inverse bind rig or socket state. Lighting, colors and fog are controlled valid inputs rather than captured runtime parameters.

The APK bundles `mesh.bin`, `poses.bin`, `texture0.rgba`, `texture1.rgba` and `material-reference.bin`. Java verifies every asset's exact byte count and SHA256 before JNI. The native parser validates counts, spans, topology, finite floats, weights and palette indices before allocating GPU objects.

## Qualification work

Host checks compare the bounded native parser and deformation routine with separately prepared scalar pose goldens. Malformed offset, index, weight, float and palette inputs must fail without publishing an invalid view; sanitizer execution covers mutations and truncation. A separate, hash-pinned original scalar geometry function checks the offline delta decoder. These are host source-function checks, not execution of the complete Windows client.

The GLES probe compares transform-feedback positions and normals for every real vertex in both controlled poses. The translated normal calculation refines the reciprocal length once while retaining the original built-in normalized result as a separate GPU diagnostic; the 1e-4 absolute parity tolerance is unchanged. It compares GPU-skinned rendering with a CPU-reference geometry rendering, with the reported pixel coverage and tolerance. Eighteen material cases compare offscreen RGBA8 pixels with a scalar source-semantic oracle: fourteen use the real texture pair and four add an explicitly controlled one-pixel secondary swatch to detect channel-mask and secondary-alpha errors. They cover tint, lighting inputs, alpha rejection, fog and blending. Each JNI call rebuilds and releases two complete EGL contexts, presents the real mesh, checks actual window RGB samples and swaps buffers.

The UI retains the qualified serial Surface lifecycle design. Resize changes both actual dimensions, so this gate also exercises display scale. Obsolete/background results cannot qualify a current Surface, active-session failures remain sticky, and export captures the foreground report before the document picker changes lifecycle state.

## Qualified build and hosted execution

[Android build and emulator qualification](https://github.com/Russianranger/coh-android/actions/runs/38461198804) passed at code `6ba92ede53bf48814bf2a02aceedebd3934eef10`. The ARM64 APK is **314,985 bytes**, SHA256 `478c16eb36ef13e87ee17fbe08760dc610366cc50ce46e2f568f44ce99a3d4e5`. Its isolated debug signature, `org.coh.materialprobe` package, ARM64-only ELF64 AArch64 library and all five bundled fixture hashes were checked. The dedicated x86_64 emulator APK is a separate file.

The [qualification receipt](evidence/phase6/qualification.json) records independent artifact-digest verification and recomputed counters. Android13/API33 with SwiftShader passed four current-surface runs and eight complete EGL context lifetimes:

- 11,136 GPU position/normal component comparisons; zero mismatches at the unchanged 1e-4 tolerance. Maximum observed position error was zero and normal error was 1.1920929e-7.
- 1,988,600 skinned/reference image pixel comparisons, including 135,072 useful nonbackground interior pixels. The explicit two-pixel geometry-edge exclusion removed 370,696 comparisons. Both poses had useful coverage in every cycle.
- 589,824 material RGBA pixel comparisons covering all 18 cases per cycle. Skin and material comparisons had zero mismatches at a two-quantization-unit tolerance; the largest observed channel difference was one unit.
- 392 actual window RGB samples, zero mismatches; all swaps and app GPU cleanup passed, with zero GL/EGL errors.
- Actual sizes 1038x764 and 778x573, three Surface generations, resize on both axes, Surface recreation and Home/foreground recovery passed. One obsolete result was retained in history and excluded from qualification.
- The final screenshot was visually reviewed: the real textured sleeve appears with green **MATERIAL GATE PASSED** status.

The [first failed emulator record](evidence/phase6/first-emulator-failure.json) is preserved. That program failed 23 transform components with maximum error 0.000192046165. Making normalization explicit and refining the reciprocal length resolved the comparison without relaxing its tolerance. The built-in normal diagnostic in the modified program also matched, so this run does not isolate the exact original compiler/driver cause or establish that refinement alone caused the improvement.

These counts repeat one source fixture and controlled inputs; they are not distinct assets or a gameplay benchmark. **Physical AYN Thor/Adreno 740 acceptance passed.** The [device receipt](evidence/phase6/thor-qualification.json) records eight successful runs, sixteen complete EGL context lifetimes, four Surface generations, two actual widths and heights, and Home/foreground recovery. All transform, skin-image, material and window comparisons passed with zero mismatches or GL/EGL errors. The final exported report qualifies; the supplied screenshot was captured earlier while lifecycle qualification was pending.

Device totals are 22,272 gated GPU transform components, 11,136 stock-normal diagnostic components, 3,977,200 skin/reference pixel comparisons including 270,144 useful interior pixels, 1,179,648 material RGBA pixel comparisons and 784 window RGB samples. Maximum position error was 2.38418579e-7, maximum normal error 1.1920929e-7 and maximum material channel difference one byte. Every bundled fixture hash matches the delivered APK; the report itself does not measure the APK digest. The accepted Phase 5 texture/Surface gate remains separate.

## Thor acceptance procedure

1. Install the ARM64 **COH Native Material Probe** APK. It installs beside the texture probe and shipping launcher.
2. Open the probe and confirm the sleeve mesh appears. Wait for the first check, use **Resize surface**, then **Recreate surface**, and wait for **MATERIAL GATE PASSED**.
3. Press Home, return, and wait for the current Surface to pass again. Use **Run check** if needed.
4. Use **Export report**, save the JSON and return it with a screenshot. Export failures before restarting the app so the failed session remains reviewable.

Accept only actual ARM64 Thor/Adreno evidence with matching fixture hashes, nonzero transform/material/render comparisons, clean errors and cleanup, two actual widths and heights, separate Surface generations and foreground recovery. Hosted emulator results alone do not qualify the Adreno driver.

## Limits and following work

The scalar material oracle follows pinned Cg source arithmetic; it does not execute the original Cg program on the original GPU. Transform feedback independently checks positions and normals; the CPU-reference and GPU-skinned image paths share the vertex lighting shader. The controlled probe disables backface culling, so original clockwise/backface-culling behavior is unqualified. Generic DXT5 RGBA conversion preserves the GPU-role alpha contract, but is not a capture of original-driver compressed-texture interpolation. Window RGB checks exclude Android compositor alpha. Unexpected GPU reset, process death, continuous frame pacing, the complete material family and scene passes remain outside this proof.

Phase 7 now recovers the original rig, socket and animation playback contracts using real base-skeleton and run assets. Complete character assembly remains a following gate before scene/world integration. FPS, startup and zone-load improvements require measurements from the playable client; this probe makes none of those claims.
