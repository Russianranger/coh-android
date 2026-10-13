# Bounded native complete-character morphology

This module extends the accepted raw animation sampler for the authored
`V_Arachnos_Wretch` NPC appearance. It preserves the existing Phase7 files.
`coh_character.c` includes the unchanged animation implementation in one
translation unit so it can sample raw local keys before the source morph
translation and `animDelta` subtraction. Do not compile `coh_animation.c`
separately into the same executable.

`COHMOR01` contains a 256-byte little-endian header and 99 ordered 28-byte
records: source bone ID, three original fat-model scale components, and three
original skinny-model scale components. Missing scale models use the source
unit default. The container stores authored appearance parameters and source
model scale triples, not sampled palettes or precomputed animated vertices.
The native parser checks the exact envelope, reserved fields, record order,
finite inputs, positive model scales, and bounded root/limb scales before
publishing its output.

The source Huge body type is enum value 4. `changeBoneScaleEx` clamps the selected
per-axis appearance ratio and computes `1 + ((modelScale - 1) * abs(ratio))`.
Waist and chest use their separate authored ratios; head scale does not use
the global body ratio; facial bones use their own vectors; the two bosom bones
use unit scales for Huge. Wretch's appearance values are passed directly to the
client function. Type scale-range values are validation limits, not factors
to multiply into those NPC parameters.

The source operation order is preserved:

1. Decode and interpolate real compressed local keys using the accepted raw
   sampler. Add the source shoulder, neck, and hip morph translations, then
   subtract the original animation delta.
2. Convert the quaternion using the original matrix convention. Apply the
   source limb scale/unscale basis operations without modifying translation.
   `scaleBone` post-multiplies; `unscaleBone` pre-multiplies.
3. Form the entity root from authored `GeomScale 1.3 1.3 1.3`, then apply the
   leg correction `1 + (0.8 * -0.03319)` to the root. Compose each local node
   under its unscaled parent, including both original outer roots.
4. For a skin matrix, compute `parentWorld * (localNode * boneScale)` in this
   order. The render bone scale does not propagate to children. Apply the
   inverse bind translation and attachment offset as two separate float32
   point transformations, then upload three affine rows per palette bone.

`coh_character_sample` returns the actual sampled rotations, morphed positions,
and the parent hierarchy matrices including the entity root. The palette API
reconstructs the local matrix from those values to preserve the source's
parent/local/scale multiplication order. Normals follow the accepted original
GPU weighted-basis contract; this is not an inverse-transpose replacement.

`tools/character_fixture/original_actor_check.py` executes the unchanged original
`changeBoneScaleEx`, `animateGfxNodeBone`, scale/unscale helpers, raw-key functions,
and matrix functions on the actual input files. Compatibility helpers select a
single clip, no transition blending, zero aiming, and no character creator.
Original absent scale models are represented by their unit default. Source
and extracted-function hashes are pinned. Oracle JSON is made exclusively from
original kernel outputs; the portable native implementation is loaded only to
compare results. A separate Python hierarchy/palette/geometry generator never
calls the native character implementation.

`native_character_check.py` compares all 60 hierarchy nodes and the 11 draws
containing 2,626 vertices against that independent reference at six integer and
fractional checkpoints. It checks malformed morphology and scene envelopes,
preserves failed outputs, and runs deterministic ASan/UBSan mutations and
truncations. LeakSanitizer is disabled because this execution host restricts
its process inspection; the parser itself has no heap allocations.

This gate covers the actual complete authored costume, actual body morphology,
one original run clip, attachment palettes, and native rendering. It does not
implement sequence state selection, transitions, aiming, movement-derived
clip speed, world rendering, FX, networking, or the complete playable client.
