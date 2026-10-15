# Source audit and acceptance boundary

Exact LF-normalized hashes are in `source-pins.json` and the executed host receipt.
The unchanged-source C oracle extracts these functions directly from original
`upstream/ouroboros/Game/src/entity/costume_client.c`:

- `get_color`: SKIN matching routes the appearance skin to primary and original
  primary to secondary, rather than tinting every part with skin.
- `gender_prefix_fixup`: candidate existence controls prefix selection; the
  source uses `.tga` for lookup, then drops that suffix for selected identity.
- `calc_tex_types1`: authored final `a` means dual pass, final `x` single texture.
- `bodyPartIsLinkedToChest`, `doChangeGeo`: source candidate list, paired R/L,
  explicit GEO selection, one-sided limb clearing and preserve/no-call branches.
- `determineTextureNames`: explicit texture flags, NONE, texture slots, 01a hack
  and source order of prefix probes.

The oracle also executes original `costumePrefixName` with the original nine
`g_BodyTypeInfos` records from `Common/entity/costume.c`. Shims provide only
string concatenation, mocked source texture/model existence, original container
size and collection of `changeGeo` intents. It never calls the new assembly code.
Duplicate source changeGeo intents to the same socket collapse to the final
source assignment, matching the reusable output delta semantics.

The four authentic NPC records are read from exact original i24 `.nd` blocks.
All 28 original `BodyPart` entries come from `defs/ui/bodyparts.bp`; symbolic bone
numbers come from `Common/seq/bones.h`. Some legacy `Wep_R` names have no exact
symbol in that source enumeration; the test importer preserves INVALID and the
new module preserves the original doChangeGeo early return. A production parser
must use its authoritative source bone-name map and must not manufacture geometry.

The original helper's `BodyType` is appearance routing, distinct from a custom
NPC sequencer's skeleton/morph family. The existing accepted Wretch palette
remains Huge and is reused unchanged; this module does not infer a new skeleton
from appearance routing. Authored or player bodytype must come from the owner.

Seven authentic GEO payloads are independent manifest-SHA-verified original game
resources with ZIP CRC, original PIGG provenance and bounded acquisition. Their
402 model names/counts/scales and all 1,608 delta streams are independently read,
then decoded through the existing qualified native readers and compared byte for
byte with original `Common/seq/anim.c::uncompressDeltas` (908,735 scalar values).
No GEO or decoder implementation is modified.

The accepted rig/morph adapter is compared with the unchanged accepted character
palette kernel over six frames and all 11 accepted Wretch draws (3,240 float
components). This proves adapter regression behavior; independent source palette
qualification remains the original accepted receipt, preserved without repetition.

The module has host and ARM64 link evidence. It has no Android execution,
emulator rendering, original Windows capture, newly rendered body, physical
Thor or full Gate31 acceptance. Source authored NPC filenames occasionally lack
corresponding Base pack resources; missing names are not silently aliased.
