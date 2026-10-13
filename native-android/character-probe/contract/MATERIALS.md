# Phase 8 Wretch costume material contract

The probe selects an original renderer profile with `GFXF_MULTITEX=0`,
`GFXF_BUMPMAPS=0`, and hardware vertex skinning enabled. Every draw uses the
original `COLORBLEND_DUAL` fragment family without `BIT_HIGH_QUALITY`,
`BIT_SHADOWMAP`, or `BIT_DEBUG`. This is a source-defined low quality path;
the complete high quality MULTI/bump/reflection appearance is a later gate.
The accepted Phase 6 `skinned_dual.vert`, `dual_tint.frag`, and quad vertex
shader are reused without modification.

The virtual X_* costume aliases are resolved from the original material
definitions. The probe never substitutes the default texture named by the GEO
for the requested costume override. `materials.json` pins the original source
files and supplies the resolved pairs and RGB colors in exact draw order.

| Draw | Actual base | Actual dual input |
|---|---|---|
| Pants | Hips_Arachnos_Wretch_01 | Hips_Arachnos_Crab_01_Mask |
| Chest | Chest_Arachnos_Wretch_01 | Chest_Wolf_01b |
| Head | Face_Skin_Wretch_base | white |
| Gloves | Glove_Wretch_Armor | glove_wolf_01b |
| BootsRight | Boot_Arachnos_Wretch_01 | Boot_Arachnos_Wretch_Mask |
| BootsLeft | Boot_Arachnos_Wretch_01 | Boot_Arachnos_Wretch_Mask |
| Belt | belt_wolf_01 | white |
| Hair | Hair_Wretch | Hair_Wretch_Mask |
| Neck | neck_wretch_01 | neck_wolf_01b |
| Sleeves | Sleeves_Skin_Wretch_Base | white |
| Shoulders | Glove_Skin_Wretch_Base | white |

`tricks.c::setupTexOpt` clears `none` and `texture_name*` before determining
the material family. Chest has no mask, so its second material is removed and
its Base1/DualColor1/BumpMap1 skeleton is demoted to an old dual+bump family;
disabling bump capability selects the ordinary dual family. The other five
X_* identities retain their masks, require MULTI, and use the original
automatic fallback from `tex.c::texResetTrickBasedParametersComposite`.
Belt's cleared DualColor1 becomes the stock white texture input.
`texFindNeededBinds` resolves this required texture, and `texMakeWhite` loads
`white.tga`; the fixture retains the actual acquired pixels, dimensions, and
source hash rather than assuming an engine-generated one-pixel substitute.

All authored X_* DualColor1 layers are non-swappable. Character generic
overrides apply only when `getSwapX` finds the corresponding swappable bit;
the costume's requested white therefore cannot erase the authored detail
masks. Old-style skin and hair bind the actual costume generic override.
The RGB colors use the exact source operation `float(byte) * (1.f / 255.f)`.
Skin-color replacement is defined by `binding.json`, not guessed from the
texture's appearance.

Automatic fallback stores ambient and diffuse scale 0.5 in TexOpt metadata.
The `rt_bonedmodel.c::drawLoopBoned` ordinary dual branch directly uploads the
character's ambient/diffuse values; it does not apply these stored scales.
The probe therefore uses draw multipliers 1 for all parts, with explicit
controlled character lighting. `BMB_NV1XWORLD` changes a legacy NV1X register
combiner selection, not the ordinary Cg fragment operations.

Hair and Neck use the original `Collar2x` object trick, which is DoubleSided.
It supplies no alpha-reference or AlphaCutout flag. The default strict-positive
alpha test follows `rt_state.c`'s `glAlphaFunc(GL_GREATER,0)`. Actual acquired dual
textures have alpha 255 except Hair_Wretch_Mask, whose DXT5 mip zero contains
alpha values from 0 through 216. Hair alpha must be retained and blended;
opaque treatment of that draw is incorrect. Native source draw-state evidence
and the scene fixture record control culling, blend, and depth-write state.
The original default is clockwise front faces and back-face culling
(`rt_init.c:44–46`). Collar2x disables culling for Hair and Neck; all other
draws retain the default. `rt_tricks.c` disables depth writes only for an
explicit NoZWrite trick; Collar2x has no such flag. Hair therefore retains
source depth writes despite its partial alpha. Applying an invented late
transparent pass with disabled depth writes would be a different contract.
`model.c` explicitly skips `modelNeedsAlphaSort` for GEO_* player geometry,
and `rendertree.c` disables the custom-texture alpha-sort check with an
`if(0 && ...)` guard. Collar2x supplies no specific alpha-sort trick, so a
nonopaque hair mask alone does not imply an original alpha-sort node flag.
The scalar quad references independently exercise these material alpha
operations, but do not prove a complete original scene sorting implementation.

## Scalar material reference

`build_character_material_reference.py::prepare(parts,textures)` emits
`COHCMAT8`. It imports the accepted independent source-semantic scalar
evaluator, which does not execute or parse GLSL. Six cases are retained for
each of the eleven actual draws, including both boots, for 66 cases total:
authored RGB colors, half-fade RGBA source-over, mid-fog, strict alpha-ref-one
discard, controlled dual RGB/alpha, and controlled dual alpha-ref-0.6 discard.
The controlled swatch is explicitly diagnostic RGBA8 `(51,153,230,128)`;
it is never represented as an original game texture.

The cases use real base/dual RGBA textures, nearest/clamp mip-zero sampling,
64x64 output, binary32 uniforms, and Python binary64 scalar arithmetic.
GPU RGBA8 results allow the accepted maximum two quantization units of error.
Source alpha is `dual.a * const0.a`; base alpha is a tint mask and does not
multiply output alpha. Fixed-function RGBA blending uses
`SRC_ALPHA/ONE_MINUS_SRC_ALPHA` for all channels, including destination alpha.
Each actual draw is sampled with its original effective RGB colors.

| Header offset | Type | Value |
|---|---|---|
| 0 | 8 bytes | COHCMAT8 |
| 8 | u32 | version 1 |
| 12 | u32 | header bytes 64 |
| 16, 20 | u32 | width, height 64 |
| 24 | u32 | case count 6 × part count |
| 28 | u32 | case-record bytes 128 |
| 32 | u32 | part count |
| 36 | u32 | RGBA byte count per case 16384 |
| 40 | u32 | complete case stride 16512 |
| 44 | u32 | case data offset 64 |
| 48 | u32 | total file bytes |
| 52, 56, 60 | u32 | zero reserves |

Each 128-byte case begins with six vec4 values in order: const0, const1,
vertex color, fog parameters, fog color, clear color. Binary32 fog-coordinate
and alpha-reference follow at offsets 96 and 100. Flags at 104 use bit zero
for RGBA blending and bit one for the diagnostic dual swatch. Part index and
case index occupy 108 and 112; offsets 116,120,124 are zero. The expected
64x64 RGBA bytes immediately follow, in lower-left FBO order without Y flip.
The eleven-draw file is 1,089,856 bytes.

`--self-check` exercises independently specified scalar boundaries and exact
source color conversion. Fixture metadata records every case hash, discarded
pixel count, real texture identity, and controlled input status. Original
Windows/Cg pixel capture, original driver compressed-texture interpolation,
runtime filtering/mip selection, scene lighting, and high quality materials
remain outside this acceptance claim.
