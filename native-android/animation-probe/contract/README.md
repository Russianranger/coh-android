# Real animation, hierarchy and socket contract

Phase 7 extends the qualified Phase 6 sleeves/material slice with the original `huge/skel_ready.anim` base and `huge/run.anim` motion. The native sampler receives the original Win32 disk bytes and evaluates keys on the device. Reference matrices and geometry are validation controls; the preview must use the native sampler's runtime palette.

The fixture retains the real 116-vertex, 198-triangle `GEO_Sleeves_Wretch` and palette order `[9,5,7]`. Its attachment node is `BONEID_SLEEVES=72`. The mesh's first palette entry9 is a deforming bone, not the attachment socket. All60 base hierarchy nodes and 44 motion tracks must be validated, even though only seven nodes affect this mesh's palette and socket.

## Source binding and exact clock

The source paths below are hash-pinned in `source-hashes.json`.

| Relationship | Original source location |
|---|---|
| Wretch selects `player.txt`, type `huge` | `upstream/i24/data/ent_types/v_arachnos_wretch.txt:6–8` |
| `huge` selects base `huge\skel_ready`, parent `male` | `upstream/i24/data/sequencers/player.txt:302–305` |
| RunCycle selects `huge\run 1 25` | `upstream/i24/data/sequencers/player/motion.inc:140–145,187–192` |
| Ready uses the same real base | `upstream/i24/data/sequencers/player/readies.inc:21–23` |
| Type lookup recurses through parent only after no direct match | `Common/seq/seqload.c:959–989` |
| Animation name becomes`player_library/animations/<NAME>.anim` | `Common/seq/animtrack.c:268–295` |
| Motion backup/base hierarchy comes from its`baseAnimName` | `Common/seq/animtrack.c:252–262` |
| Sleeves has one socket named `SLEEVES` | `upstream/i24/data/defs/ui/bodyparts.bp:170–176` |
| One-part socket resolves from GeoName through`bone_IdFromName` | `Common/gameData/BodyPart.c:73–75` |
| Costume geometry is attached at the resolved body-part bone | `Game/src/entity/costume_client.c:315–368`; `Game/src/entity/entclient.c:3335–3343` |

Common and Game source paths in this document are relative to `upstream/ouroboros/`. The actual base file contains the parent chains `9→7→5→2→1→0` and `72→2→1→0`, and two outer roots, 0 and 61. The outer sequencer node has an invalid bone ID, so the original translation accumulator skips both roots and leaves their btt totals zero. The motion omits 72. Base fallback is therefore exercised by this real pair.

The authored first/last values are literal sampling frame coordinates `1` and`25`. `seqload.c:103–108` parses integers unchanged; its only endpoint fixup is replacement of a zero last frame with track length at658–659. `seqsequence.c:657–675` reads these values and initializes the current frame to first. `seqanimate.c:837–838` separates that literal frame into integer and remainder values. There is no decrement to frame0.

`seqCycleFrame` at `seqsequence.c:694–700` subtracts `last-first` once when the caller detects `frame>last`; a remaining overshoot resets to first. Frame 25 is retained. Examples:25+0→25,25+0.25→1.25,1+49→1. This differs from ordinary modulo looping.

The controlled clock uses 30 frame units per second with multiplier 1. `Game/src/graphics/gfx.c:318,337–338` defines TIMESTEP in thirtieths of a second. RunCycle's MoveRate 0.7 is a movement-speed target: `entclient.c:1174–1190` divides actual movement rate by target rate and clamps the multiplier to 0.25..2;2520–2521 applies that result to TIMESTEP. This probe does not reconstruct that movement or SmoothSprint state.

## Source math

`seqskeleton.c:978–992` attaches motion tracks first, then backup/base tracks for missing IDs. Missing motion IDs are marked `GFXNODE_DONTANIMATE`; `seqanimate.c:618–624` keeps their initialized base matrices rather than playing the base clip. In particular,72 retains its base first position and raw base first quaternion. `seqskeleton.c:616–643` converts the base quaternion without an extra normalize step.

The sequencer base supplies initial positions and rotations at `seqskeleton.c:1004–1016`. Its first position is compared with the attached track's first position to compute `animDelta` at1023–1025. Animated positions subtract this delta at `seqanimate.c:198`. Rotation interpolation uses`quatInterp` at `libs/UtilitiesLib/src/utils/Quat.c:312–333`: short-arc normalized linear interpolation, not SLERP. Move-transition blending and actor morph adjustments are controlled off.

The independent hierarchy oracle uses 3x4 affine **rows**. Original Mat4 storage uses three basis columns and a translation vector. `Quat.c:157–182` is transposed when converted into upload rows; its positive Z quaternion rotates X toward negative Y. `mathutil.h:691–705,740–744` gives parent/local affine multiplication and point transformation.

For each sampled bone, with unit bone scale and identity outer transform:

1. Compose`world[bone]=world[parent]*local[bone]`.
2. Compute base translation totals`btt` from first sequencer-base positions. Root totals start zero; other nodes add their base local position to their parent's total (`seqskeleton.c:39–60`). This is translation accumulation, not an inverse of a general posed matrix.
3. Compute`bpt[bone]` with the world's linear part and translation`transformPoint(world[bone],-btt[bone])` (`Game/src/render/rendertree.c:2649–2657`).
4. For local palette slot j, select global bone `bone_ID[j]`, keep its bpt linear part and set translation`transformPoint(bpt[bone_ID[j]],btt[72])` (`renderbonedmodel.c:137–159`).

Equivalently, final palette translation is `world.translation+world.linear*(btt[72]-btt[bone])`. Applying a second complete inverse-bind matrix or using9 as the socket changes source behavior. `rt_bonedmodel.c:197–229` uploads three vec4 rows per local bone. Palette order remains`[9,5,7]`. The unchanged Phase 6 shader lerps the two transformed positions and normals with weight.y, then normalizes the blended normal.

## Reference binary

`rig-reference.bin` uses little-endian scalar values, no pointers and no alignment padding. Its magic is `COHAGL01`, version 1,128-byte header, total 63572 bytes. Zero-reserved header bytes100..127 are required.

| Header byte | Type | Meaning / fixed value |
|---:|---|---|
|0|8bytes|`COHAGL01`|
|8,12|u32|version 1,header 128|
|16,20,24,28|u32|samples6,bones60,palette3,vertices116|
|32,36,40,44|u32|bone IDs128,parent IDs368,palette IDs608,btt620|
|48,52,56|u32|cases1340,case stride10372,total63572|
|60,64|u32|socket72,flags0|
|68,72,76,80,84|u32|per-case offsets:local4,world1684,bpt4564,palette7444,mesh7588|
|88,92,96|f32|ticks/sec30,first1,last25|

The shared data is 60 ascending u32 global IDs, 60s32 parents (`-1` denotes an outer root), 3 u32 palette IDs and 60 XYZ float32 btt vectors. Each case stores one float32 frame, 60local quaternionXYZW+positionXYZ records, 60world3x4 matrices, 60bpt3x4 matrices, 3palette3x4 matrices and 116positionXYZ+unitnormalXYZ records. Cases are at frames `[1,1.5,5.25,12.5,24.5,25]`.

`hierarchy_reference.generate(original_samples,mesh_bytes)` consumes local channels from the retained original-function **host** oracle, independently computes hierarchy/socket/palette arithmetic in Python binary64, serializes float32 palettes and evaluates scalar GPU skin from those serialized inputs. It never invokes the portable C animation sampler. Its hand-derived self-checks cover quaternion sign, parent multiplication, root btt, socket/inverse-translation combination, raw base quaternion preservation and cycle boundaries.

The objective gate compares native local channels and all 60 hierarchy/btt/bpt/palette stages with the reference, then checks GPU position/normal parity at 1e-4 and useful interior image RGBA within 2 byte units. Each context presents a 45-tick preview sampled from the raw keys on device, with measurable temporal changes and at least one cycle wrap. Two contexts give 90 ticks per run. Existing Phase 6 alpha/fog/blend/material controls remain in the gate. Qualified context lifecycle results must identify which emulator/device ran them.

These are source-semantic checks using real data. They do not establish a captured Windows runtime palette, original Cg bit parity, full NPC appearance, complete move-state behavior, actor scaling/morphing, costume assembly, audio, networking or whole-game performance.
