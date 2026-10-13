# Phase 8: complete source character assembly

This isolated `org.coh.characterprobe` package, version `0.1.0-phase8`, expands the accepted Thor animation probe into the complete source-selected Arachnos Wretch character. It reconstructs actor morphology, all costume draw instances, actual texture overrides and a source-defined COLORBLEND_DUAL renderer profile. It is a bounded native character probe for Android Bionic ARM64.

## Real costume and asset recovery

The authored costume has ten visible categories and eleven real draw instances: pants, chest, head, left glove, both boots, belt, hair, neck, sleeves and shoulder assembly. The selected right glove model is absent from the original asset; original lookup accepts `None`. The probe retains that asymmetry and does not invent a mirrored model.

The fixture has 2,626 vertices, 2,986 triangles, 620 genuine blended vertices and 45 per-draw bone palette entries. The head uses older GEO version two; other costume files use version three. Missing bone-info geometry uses the recovered original one-bone adapter. Original geometry expansion is checked against unchanged source functions across 66 channels and 40,470 scalar elements. Canonical geometry preserves the original UV flip and byte-weight conversion.

Seventeen real mip-zero runtime textures supply the source-selected low-profile materials, including actual `grey.texture` and `white.texture` assets. Large release archives are read using bounded HTTP ranges, stable ETags, exact ZIP envelopes, CRC and complete member SHA256 pins; whole archive hashes remain release-declared rather than locally verified. All five JNI assets have exact byte and SHA256 manifests.

See [the binding contract](character-probe/contract/README.md), [material resolution](character-probe/contract/MATERIALS.md) and [asset provenance](tools/character_fixture/PROVENANCE.md).

## Actor morphology and source operation order

The real huge base skeleton and run clip remain unchanged. The native actor computes Wretch's actual costume body parameters and type parameters, including entity geometry scale 1.3, from a bounded source-scale input. The `COHMOR01` fixture retains 99 original large/skinny model-scale triples and appearance/type parameters; it contains no sampled palettes.

Morph translations are added before animation-delta subtraction. Limb scale/unscale operations and root/hip corrections preserve original order. Entity scale is applied at the outer root before hierarchy composition. Render bone scale applies as `parent_world * (local_node * bone_scale)` and does not propagate into children; source traversal stores the unscaled node world matrix. Palettes then perform inverse-bind and attachment translations as two original point transforms.

The accepted raw animation implementation is included once by the new character module. Accepted Phase 6/7 files are preserved. The unchanged source actor oracle executes original morphology, node-animation and scale/unscale functions under documented neutral single-clip compatibility helpers. The independent Python reference consumes those source local channels, then computes full hierarchy, node scales, per-draw socket palettes and all skinned vertex positions/normals. It does not call the portable sampler.

## Source-selected material profile and draw state

The probe disables original MULTITEX and BUMPMAPS capabilities, selecting genuine source COLORBLEND_DUAL paths for the costume's six X_* material identities. Five use automatic MULTI fallback; Chest first demotes to the older bump-dual path and then suppresses bump mapping. Actual Base1/detail-mask identities and original costume colors are retained. White and non-swappable masks follow source override rules.

Stored fallback lighting factors are metadata; the original boned dual path directly uploads actor lighting and does not apply those stored half factors. The probe uses controlled lighting and clamp addressing. Character geometry uses linear mip-zero filtering, consistent with the source default when no point-sample flag or mip chain is selected. The separate 66 analytic material cases retain their declared nearest mip-zero sampler. Original mip chains and address/filter families, advanced multi-layer, bump and reflection variants remain unqualified.

Source clockwise front faces and back culling are used except genuine DoubleSided Hair and Neck. Hair's actual mask retains alpha 0–216 and source-over blending. Depth writes remain enabled: original GEO alpha-sorting suppression and disabled custom-override alpha detection do not support inventing automatic late hair or disabled depth writes. The probe uses deterministic declared draw order; original whole-scene type/distance sorting remains outside this gate. [The alpha-order audit](character-probe/contract/alpha-order-source-audit.md) preserves this distinction.

## Native qualification design

Six checkpoints at frames 1, 1.5, 5.25, 12.5, 24.5 and 25 check the full 60-node actor hierarchy, morphology, all eleven palettes and 2,626 vertex outputs. GPU transform feedback checks every position and normal. Each draw receives a standalone GPU-versus-independent-reference image check in a close-up camera fitted to its six reference geometry checkpoints with a 20 percent margin. Each piece requires at least 64 useful pixels per pose outside the two-pixel triangle-edge guard. This catches small hair and head draws that the full-character camera cannot qualify separately. Six assembled images retain the independent full-character camera and compare RGBA with the same edge guard. Float tolerance remains 1e-4 and RGBA tolerance two byte units.

Sixty-six material cases exercise actual costume colors, masks, alpha, fog and blending; forty-four use real texture pairs and twenty-two add an explicitly controlled secondary swatch. The accepted GLSL shader sources remain unchanged. GPU-skinned and reference-geometry image paths share vertex lighting; transform feedback independently checks geometry and normals.

Each JNI call creates and releases two EGL contexts. Each context samples original raw keys and presents 45 animated frames, requiring a source clock wrap, distinct palettes and visible GPU image changes. The camera fits all preview frames plus fractional checkpoints. Final-window RGB checks follow the preview. Java preserves actual two-axis resize, generation/request guards, sticky active failures, obsolete-result exclusion and immutable foreground export.

## Qualification status

Original source actor checks passed 11,469 float comparisons at six checkpoints with zero error. The [host proof](evidence/phase8/host-character-proof.json) checks 109,308 native float components against the independent reference with zero mismatches and a maximum error of 1.43051147e-6. It also passes 333 named malformed inputs, 3,224 truncations, and 10,070 ASan/UBSan checks.

Actual Android SDK/NDK compilation, lint, APK signing/ABI/input verification, portable core checks, and Android 13 x86_64/SwiftShader execution passed in [run 38481572798](https://github.com/Russianranger/coh-android/actions/runs/38481572798). The [qualification receipt](evidence/phase8/qualification.json) records six successful same-session runs, twelve clean EGL lifetimes, four Surface generations, two actual widths and heights, and verified pause/stop/destruction/foreground recovery. All comparison mismatches and GL/EGL errors are zero. GPU transforms had a maximum absolute error of 1.43051147e-6; standalone and analytic material images differed by at most one byte, and assembled images matched exactly. Every piece has useful close-up coverage at every checkpoint. The full Wretch and green pass banner were visually reviewed.

The [build receipt](evidence/phase8/build-receipt.json) binds the delivered ARM64 APK to source commit `608eeffa7ececad26bfce5fc2ef00a3cbc81e243`: **1,999,956 bytes**, SHA256 `7b63e2de27eb84f678fecf2d91e37eb2d2eaf18728e4aa17abe98ef07c9ee71e`. Its sole native library is AArch64 `libcoh_character_probe.so`, linked to Android Bionic, EGL and GLESv3. All five binary assets exactly match independently prepared host inputs.

Physical Thor character rendering, animation, materials, two-axis resize and explicit Surface recreation passed in the October 13 `COH-NativeCharacter-20261013-181750.json` export. The [Thor receipt](evidence/phase8/thor-qualification.json) records 2,543 audit assertions, three successful same-session runs, six clean EGL contexts, two actual dimensions (1884x389 and 1413x291), two Surface generations, 270 animated frames, and zero comparison mismatches or GL/EGL errors. All five fixture inputs and the reported fixture metadata match the delivered ARM64 package. GPU maximum absolute error was 1.43051147e-6; assembled images matched exactly, with at most one byte of standalone/material error. The screenshot shows the complete Wretch during the first in-progress run; it is not a final green acceptance screenshot.

The user explicitly accepted the remaining Home/return requirement on October 13 and directed work to the next gate. Phase 8 is therefore accepted. The [Thor receipt](evidence/phase8/thor-qualification.json) distinguishes measured character/resize/recreation results from this user-confirmed lifecycle acceptance; the immutable export still has no pause/stop/second-resume events and no new events are invented. Accepted Thor Phase 7 remains in [its receipt](evidence/phase7/thor-qualification.json).

Earlier failed sessions are retained: [the manifest-loader bound failure](evidence/phase8/first-emulator-failure.json) never reached native rendering, and [the nearest-filter Hair failure](evidence/phase8/hair-image-failure.json) had five non-edge pixel mismatches while actor and GPU transforms passed. A bounded metadata check now precedes packaging. Geometry image comparison passed after adopting source-aligned linear mip-zero filtering; the exact five prior pixel locations were not captured, so no stronger per-pixel cause is assigned. The [sampler source audit](evidence/phase8/source-sampler-policy.json) preserves default-filter evidence and runtime-table limits. Reference buffers, the two-byte color tolerance and the two-pixel triangle guard were preserved. Bounded pixel/UV/depth failure diagnostics remain available for future device failures.

The [Phase 8 REA continuation](PHASE8-REA.md) records a fresh bounded read-only query of the retained client checkpoint. All ten checkpoint files remained unchanged; raw character/material anchors were found but no source function identity was assigned from the partial binary database.

## Thor acceptance procedure

1. Install **CoH Native Character Probe** beside the previous probes.
2. Confirm the complete Wretch appears and animates during each check. Wait, use **Resize surface**, then **Recreate surface**, waiting for each check.
3. Press Home, return and wait for the current foreground check. **Run check** replays the bounded animation.
4. Confirm **CHARACTER GATE PASSED**, then export JSON and return it with a screenshot. Preserve failed-session exports before restarting.

Accept only actual ARM64 Thor/Adreno evidence with matching five-asset hashes, nonzero per-part transform/image coverage, all actor/material comparisons passing, clean errors/cleanup, two actual widths and heights, separate Surface generations and foreground recovery.

## Limits and following work

This gate covers one complete source character in a controlled source renderer profile and one real animation clip. It does not execute the full movement-driven sequencer, transitions, aiming, collision, cloth/effects, player customization or the complete Windows Game. Original Cg/driver capture, high-quality materials, mip/filter families and original scene sorting remain separate. Unexpected GPU reset, process death and continuous frame pacing are unqualified. It makes no playable-client FPS, startup or zoning claim.

Following device acceptance, recover and qualify scene rendering, camera/world transforms and remaining material passes before native input, networking and playable-client integration.
