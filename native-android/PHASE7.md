# Phase 7: real encoded animation, hierarchy and socket probe

This isolated package is `org.coh.animationprobe`, version `0.1.0-phase7`. It continues from accepted Thor texture and material gates using the same real Arachnos Wretch sleeve mesh, now animated from original encoded assets rather than controlled bone palettes. It reconstructs a bounded native animation path for Android Bionic ARM64.

## Recovered source and real assets

The Wretch definition selects the player sequencer's huge type. Its base skeleton is `huge/skel_ready`; the authored RunCycle range is `huge/run 1 25`. Those frame integers remain literal through the loader and playback. The huge type's parent is male; the selected huge run is present, so parent motion fallback is not needed in this fixture.

The original base file is 6,171 bytes with 60 reachable bone tracks. The run file is 5,331 bytes with 44 tracks. Both are recovered from pinned release archive members with bounded exact HTTP ranges, stable archive ETags, ZIP CRC and source SHA256 checks. Whole large release archives are not downloaded or claimed hash-verified by this acquisition. The APK's `COHRIG01` fixture embeds the unmodified source files and palette IDs; it contains no baked animation palettes.

The mesh uses draw-local global IDs `[9,5,7]`, corresponding to right lower arm, collar and upper arm. Its attachment is socket 72 (`BONEID_SLEEVES`), not palette bone 9. Required ancestors are `[0,1,2,5,7,9,72]`; the runtime validates and composes the full 60-node base hierarchy. Socket 72 has a real base track and no run track, exercising source base fallback.

## Native reconstruction

The native sampler decodes this corpus's five-byte linear quaternion keys and six-byte or three-float position keys directly from checked raw offsets. It preserves the original quaternion's missing-component bias, signed 16-bit position scale `1/32000`, per-channel frame clamp, shortest-hemisphere normalized linear interpolation, and source matrix sign/column convention. Unsupported encodings fail; this is not a complete animation format implementation.

First motion position minus first base position forms the source animation delta, which is subtracted from sampled positions. Bones absent from the run use the raw first base quaternion and position, without adding normalization. Parent transforms compose into world matrices. The base bind translations sum first base positions and leave each outer root translation at zero (including hips 0 and root 61). Upload palettes apply world transform, inverse bind translation, then the sleeve socket bind translation in the original two point-transform order.

The bounded preview uses neutral effective rate one and source timestep units of 30 ticks per second. It advances incrementally with the original strict `frame > last` cycle test: subtract `last-first` once; if still beyond the end, reset to first. Frame 25 itself is valid. This is not modulo of an inclusive 25-frame range. RunCycle MoveRate 0.7 is a movement-speed target, not a direct animation-rate multiplier.

## Independent checks and lifecycle

The original-function host oracle retains pinned source function bodies for key expansion, local sampling and quaternion math. Independent Python hierarchy and socket arithmetic consumes those local samples rather than running the portable sampler. Six checkpoints at frames 1, 1.5, 5.25, 12.5, 24.5 and 25 include all 60 bones, bind translations, world matrices, inverse-bind matrices, three socket palette entries, and expected geometry for all 116 real mesh vertices.

Native CPU stage comparisons precede GPU transform-feedback and skinned/reference rendering. The existing dual-color, alpha, fog and offscreen material checks remain in this separate package. Float tolerance stays 1e-4 and RGBA tolerance stays two quantization units; two-pixel triangle-edge exclusion is reported explicitly.

Each check creates and releases two EGL contexts. Each context decodes and presents 45 actual animation frames, requiring distinct palettes and a clock wrap. This is a repeatable bounded preview, approximately three seconds per check, followed by the checked final image. It is not continuous gameplay or a frame-pacing benchmark. Java retains serial execution, immutable exports, obsolete-result exclusion, sticky active failures and strict SHA256 verification of all six assets.

## Qualification status

Host original-function parity passed: 13,020 local-channel comparisons and 46,656 source matrix/bind/socket scalars have zero observed error, with nine original clock cases. An independent Python hierarchy/socket reference also passed 11,556 native stage scalars at six checkpoints; the largest error was 1.1920929e-6. All 5,220 vertex instances across the bounded 45-tick preview fit the controlled projection without clipping. The [host receipts](evidence/phase7/original-local-parity.json), [independent stage receipt](evidence/phase7/independent-stage-parity.json) and [preview bounds receipt](evidence/phase7/preview-bounds-check.json) preserve their inputs and limits.

The bounded host gate additionally passed 15,732 stage/skin scalars, 66 targeted malformed or API rejections, 19 clock cases, and 34,927 exact-allocation raw-byte truncation/mutation checks under ASan and UBSan. Failed outputs remain unchanged; the [host gate receipt](evidence/phase7/host-animation-proof.json) records the tested source hashes.

[Hosted Android build and emulator qualification](https://github.com/Russianranger/coh-android/actions/runs/38471355989) passed at source `fc25a90a0d0a2ecf1733950d8f5c40be1f022b2f`. The ARM64-only APK is **386,171 bytes**, SHA256 `1b3d9baa4a85312e6afc5c21e00e0921eaa0881c89cb286085ce73c1784b11f6`. Its single ELF64 AArch64 library, debug signature, package, metadata and all six fixture payloads were verified. The separate x86_64 APK was executed on Android13/API33 with SwiftShader.

The [qualification receipt](evidence/phase7/qualification.json) records independently verified artifact digests and recomputed counters: six successful current-surface runs, twelve complete EGL context lifetimes, four Surface generations, two actual widths and heights, and Home/foreground recovery. Three retained obsolete results were excluded.

Android execution passed 138,672 native key/hierarchy/bind/socket scalars, 50,112 GPU position/normal components, 9,662,940 skinned/reference image pixels (178,668 useful interior pixels; 953,892 explicit edge exclusions), 884,736 material RGBA pixels and 588 actual window RGB samples. All gated mismatches and GL/EGL errors were zero. Maximum GPU position error was 9.53674316e-7; maximum normal error was 1.78813934e-7. Skin/material channel errors were at most one byte at the unchanged two-byte tolerance.

The runtime presented 540 animated frames with twelve clock wraps. Thirty-six temporal image captures produced twenty-four changed images and 586,272 pixels different from the first pose. The final screenshot was visually reviewed with green **ANIMATION GATE PASSED** and the bent textured sleeve visible. These repeated checks cover one real clip and mesh, not a gameplay or frame-pacing benchmark.

**Physical AYN Thor/Adreno 740 acceptance passed on October 13, 2026.** The [Thor animation receipt](evidence/phase7/thor-qualification.json) preserves 44 independently checked report invariants and the original report digest. Six successful same-session runs created and released twelve EGL contexts across four Surface generations and two actual widths and heights. The observed recovery sequence was pause, Surface destruction, stop, resume, creation of generation 3 and successful foreground request 9. Final captured request 14 passed on generation 4 at 1,884 × 389; no later incomplete request exists in that snapshot.

Thor checked 138,672 native key/hierarchy/bind/socket scalars, 50,112 GPU position/normal components, 9,662,940 skinned/reference image pixels (178,668 useful interior pixels; 953,892 reported edge exclusions), 884,736 material pixels and 588 actual window RGB samples. All comparison mismatches, GL/EGL errors and sticky session failures were zero. Maximum inverse-bind error was 1.1920929e-6; maximum GPU position error was 9.53674316e-7 and normal error was 1.78813934e-7. Skin/material channel error was at most one byte, with the unchanged 1e-4 float and two-byte tolerances.

The device presented 540 actual animated frames and twelve clock wraps; every context exercised 24 distinct palettes. Thirty-six temporal captures included twenty-four changed images and 586,284 pixels different from the first image. All six measured fixture payloads match the independently qualified ARM64 APK and offline corpus, totaling 642,610 bytes. The uploaded report measures asset digests rather than the installed APK digest or source commit; those build identifiers come from the separately verified delivery receipt.

The supplied screenshot shows the bent textured sleeve while generation 6 is running and qualification is pending. It is in-progress visual evidence, not a final status image. The audited JSON is an immutable export ending at the accepted generation 4: export captures the bytes before opening the document picker, and later Surface/lifecycle callbacks cannot rewrite those exported bytes. The raw report and screenshot remain unchanged; the unredacted image, device fingerprint and session/process identifier are not published. Phase 6 device acceptance remains recorded separately in [its receipt](evidence/phase6/thor-qualification.json).

## Thor acceptance procedure

1. Install **CoH Native Animation Probe** alongside the previous probes.
2. Open it and watch the sleeve move during the automatic check. Wait for completion, use **Resize surface**, then **Recreate surface**, waiting for each check.
3. Press Home, return and wait for the foreground animation check. Use **Run check** to replay the bounded animation.
4. Confirm **ANIMATION GATE PASSED**, then **Export report** and return the JSON with a screenshot. Preserve failed-session reports before restarting.

Accept only genuine ARM64 Thor/Adreno evidence with all six matching asset hashes, successful native stages, nonzero animated frame and pixel coverage, clean errors/cleanup, two actual widths and heights, separate Surface generations and foreground recovery. Hosted emulator execution does not establish hardware acceptance.

## Limits and next gate

The controlled diagnostic uses unit actor and bone scale, zero body morphs and an identity outer transform. Wretch entity scale 1.3 and costume texture overrides are not applied. Full movement-derived speed, sequence state selection, cross-clip transitions, reverse playback, effects, mirrored attachments, body proportions and complete costume assembly remain separate work.

The source-function oracle does not execute the complete Win32 client. [REA-assisted binary anchor observations](PHASE7-REA.md) identify investigation seams without claiming source-to-binary function equivalence. The shader/material proof retains Phase 6 limits for original Cg execution, compressed-texture driver behavior, culling and compositor alpha. Unexpected GPU reset, process death, full scene passes, networking and playable-client performance remain unqualified.

The real rig/socket/animation gate has passed on Thor. Phase 8 assembles and qualifies the complete character before scene/world integration.
