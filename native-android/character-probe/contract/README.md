# Phase 8 authored Wretch character contract

This gate assembles the complete `Arachnos_Wretch` costume with its actual huge
base skeleton, original encoded run clip, source actor proportions and source
costume overrides. It uses the original renderer's documented automatic
`COLORBLEND_DUAL` material fallback with multi-texture and bump mapping disabled.
That is a deliberate source renderer quality selection. High quality multi-layer,
normal-map and reflected materials require a later gate; the diagnostic does not
claim a full-quality original-client pixel match.

`binding.json` retains the authored values, resolved aliases and every actual
highest-detail model. `source-hashes.json` pins the immutable source/data bytes.
The original uploads, accepted earlier probes and original source are unchanged.

## Exact geometry and socket binding

| Costume part | Actual model | Socket ID | Palette global IDs | Vertices / triangles |
| --- | --- | ---: | --- | ---: |
| Pants | `GEO_Hips_Wretch` | 0 | 25, 23, 0, 26, 24 | 318 / 370 |
| Chest | `GEO_Chest_Wretch` | 2 | 3, 2, 5, 8, 6, 10, 0, 1, 7 | 409 / 520 |
| Head | `GEO_Head_Wretch__NOLOD` | 4 | 4, 3 | 160 / 263 |
| Gloves, left | `GEO_LarmL_Wretch` | 10 | 12, 10, 20, 18, 14, 16, 39 | 370 / 349 |
| Boots, right | `GEO_LlegR_Wretch` | 25 | 25, 27, 29 | 230 / 212 |
| Boots, left | `GEO_LlegL_Wretch` | 26 | 26, 28, 30 | 230 / 212 |
| Belt | `GEO_Belt_Wretch` | 34 | 0 | 98 / 76 |
| Hair | `GEO_Hair_Jack__Collar2x` | 43 | 4 | 322 / 288 |
| Neck | `GEO_Neck_Wretch__Collar2x` | 3 | 2, 5, 6, 3 | 308 / 414 |
| Sleeves | `GEO_Sleeves_Wretch` | 72 | 9, 5, 7 | 116 / 198 |
| Shoulders | `GEO_Spadr_Wretch` | 47 | 11, 9, 19, 17, 13, 15, 40 | 65 / 84 |

There are ten visible costume categories, eleven actual draws, 2,626 vertices,
2,986 triangles and 45 uploaded palette matrices. The glove file contains only
the left model. `entclient.c:3308–3314` explicitly accepts missing `Larm` geometry
as `NONE`; the probe preserves that absence. The right stump is the separately
authored shoulder model. It does not synthesize or mirror the left glove.
ChestDetail and Top are explicitly `None`. Hair and belt retain their genuine
single-bone skinned data. Head uses the original GEO version 2 decoder; all other
selected files use version 3.

The costume source is `i24/data/defs/v_villain_costumes/v_arachnos_henchmen.nd`
at lines 849–988. BodyPart mappings are `i24/data/defs/ui/bodyparts.bp` and
`Common/gameData/BodyPart.c:51–93`; IDs follow `Common/seq/bones.h`. The original
`costume_client.c:238–369` constructs the file/model aliases and independently
resolves the right/left variants of the two-part body categories.
`Common/seq/anim.c:98–117,171–172,1737–1739` compares model names
case-insensitively using their length before the `__` trick suffix. The fixture
uses that same model identity while preserving the suffix's render flags.

## Authored appearance and selected material quality

`costume_client.c:374–474` removes an initial `!` for an exact texture alias;
otherwise it prefixes the BodyPart texture name. `gender_prefix_fixup:71–99`
adds a costume prefix only when that prefixed texture actually exists. The
fixture acquisition checks the selected aliases against the complete release
texture index rather than assuming every candidate prefix exists.

The six composites are the actual Pants, Chest, Gloves, Boots, Belt and Neck
costume overrides. The selected fallback resolves their `Base1` and `DualColor1`
layers through the original material rules. Their source definitions, complete
high-quality layer identities and fallback details are recorded separately by
the material audit. Geometry-default textures are retained only as provenance;
they are not substituted for the authored overrides.

`get_color` in `costume_client.c:39–49` checks the *authored Texture1* for `SKIN`.
For Head, Sleeves and Shoulders it assigns SkinColor `(179,140,120)` to effective
color 1 and authored Color1 to effective color 2. `changeColor` sets both draw
color alphas to 255. Hair's two authored colors are black. Colors 3 and 4 are
retained for the future complete high-quality material gate.

The NPC's scalar appearance fields are parsed directly by ordinary `TOK_F32`
entries in `Common/entity/costume.c:1774–1784`; `costume_Apply` passes the same
appearance into `changeBoneScaleEx` at `costume_client.c:661`. Type scale ranges
are validation limits, as demonstrated by `costume_ValidateScales:605–640`.
They do not multiply the authored Chest/Waist/Shoulder/Hip values. The entity type
supplies `GeomScale (1.3,1.3,1.3)`, shoulder/neck/hip translations and the original
fat/skinny bone-scale GEOs. The actor math oracle pins those operations and their
source ordering separately.

## Independent reference

`hierarchy_reference.py` receives actual local quaternion/position/local rows
from the unchanged-original-function actor oracle. It independently composes
all 60 hierarchy nodes in Python binary64. Limb scales in the original local rows
propagate through that traversal; the later render `node->bonescale` multiplies
each individual node's basis and does not propagate into its children. This
matches `rendertree.c:2649–2657` and its separate traversal matrix.

Bind translations are independently accumulated from the neutral first base
positions. The source outer-root slots and hips translation are zero. For each
draw, the reference first transforms `-btt[bone]` through that bone's scaled
world matrix, then separately transforms `btt[socket]` through the resulting
inverse-bind matrix. The two native float32 point operations must remain separate.
Reference palettes are serialized to float32 before independent scalar skinning,
matching the values uploaded to the GPU.

The frozen `COHCHR01` envelope is 438,216 bytes: a 128-byte header, 2,320 shared
bytes and six cases of 72,628 bytes at source frames
`1, 1.5, 5.25, 12.5, 24.5, 25`. Its shared records contain 60 IDs, 60 parents,
60 bind translations, 60 bone scales, the actor root matrix and eleven 32-byte
draw records. Cases contain 60 local quaternion/position records, 60 unscaled
world matrices, 60 node-scaled matrices, 45 draw palettes and every vertex's
position/normalized normal. Metadata gives every offset, draw identity and hash.

The generator never loads the portable native character implementation. Analytic
self-checks exercise node-scale nonpropagation, inverse-bind/socket order,
normal normalization and cycle rejection. This is a source-semantic scalar and
native GPU parity gate; it is not an original Windows runtime capture, complete
gameplay sequencer, movement controller, full character creator or performance
measurement.
