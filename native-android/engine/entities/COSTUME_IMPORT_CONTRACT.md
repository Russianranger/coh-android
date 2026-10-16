# Costume dictionary, bodies and appearance envelope contract

This additive staging API implements the pinned original raw `costume_receive`
body used by entire and owned costumes, and the raw `NPCcostume_receive` custom
color body. The complete outer `entReceiveCostume` wire envelope is now available
as standalone staging. It does not resolve render assets, compose persistent
entity state, certify a selected player or allow acknowledgments.
No authentic server costume dictionary is bundled or claimed captured.

## External import identity

`CohEntCostumeDictionaryInput` is an in-memory import boundary. The caller must
first obtain and verify a versioned capture from the matching authorized server
source and asset profile. The future capture receipt must bind:

- Original source tree, executable SHA256 and relevant configuration/profile.
- Costume and extra-string stash capacities and every original storage slot,
  including holes and present empty strings; the palette's exact slots, values
  and presence bitmap. Dense enumeration is incompatible with wire indices.
- Original body-part count/order and body-type enumeration; associated source
  files, loaded asset identities and resource generation.
- A canonical external serialization, byte length and SHA256, verified before
  this API is called, plus a nonzero session-owned generation identifier.

Source `log2i(stashGetMaxSize(table))` uses **ceiling log2 of the original stash
capacity** to determine packed index widths. The import must preserve capacity,
slot identity and holes; a table with identical names in another order is not
the same wire dictionary. Strings exclude their terminator. NULL with size zero
means a hole; non-NULL with size zero means an admitted empty string.

The loader compares supplied manifest bytes and generation against the caller's
expected identity and deep-copies the admitted data. It does **not** calculate
the external digest, prove provenance or authenticate a caller-supplied identity.
The expectation must come from an independently verified import receipt, never
from copying untrusted packet metadata back into the expected fields. The
in-memory structures are not an external disk format and contain native pointers.
Keep the versioned capture externally; do not embed unqualified large dictionaries
or server profiles in an APK.

## Ownership and limits

Loading and parsing run off the render thread. The loader creates one immutable
allocation, with at most 65,536 slots in each of three tables and an aggregate
4 MiB ceiling including metadata, slot arrays, palette, bitmap and string bytes.
String bodies are at most 259 non-NUL bytes. Body parts are 1..30; body types are
1..64. These are explicit admission limits. Unsupported larger source profiles
fail instead of truncating or partially publishing.

The loader requires an initially NULL output owner. Failures leave it NULL;
success retains no caller input pointers. Free the owner only after all readers
finish. There is no internal reference counting or concurrent destruction
protection. The transaction owner must provide synchronization and lifetime
management. A new generation must use a separately validated owner; failed
loading or parsing leaves the previous owner and output intact.

On the qualified 64-bit ABI a full body output is 49,008 bytes, caller workspace
80,920 bytes and custom output 16,904 bytes. Full-body parsing uses its caller
workspace and no heap allocation; custom parsing uses one bounded 16,904-byte
local candidate. Workspace contents after failure are unspecified and must not
be published. API objects and input storage must not alias. Allocate full
outputs/workspace outside the Android thread stack. Query `sizeof` on the target.

Aggregate transaction planning must include old dictionary + candidate dictionary
(up to 8 MiB together), every retained old/candidate costume body, workspace,
packet storage, entity table/scratch and renderer resources. The loader's 4 MiB
limit alone is not a complete session RAM budget. The appearance envelope is
692,064 bytes with a separate 772,984-byte workspace; its maximum is ten body
slots, one supergroup body, two reward lists of 256 source entries each, and one
custom NPC color body. Two output generations plus workspace, two maximum
dictionaries, and the existing entity table/scratch total 12,389,944 bytes before
packets, graph data and render assets. This is a planning bound, not a measured
whole-session allocation. Do not embed this envelope in every entity slot: the
future complete transaction must bound retained appearance events in aggregate. No
render-thread allocation, name scan or asset decoding is introduced here.

## Wire body and rollback

`coh_ent_costume` consumes source optional entity-type/prefix strings, body/skin
metadata, all 72 supergroup color words, all 30 scale values and the exact part
grammar. Cached strings/colors use the original variable width and insertion
order. Four part strings and two or four colors are followed by region/body-set
strings when the source extra-info flag is set. Missing indexed slots and bad
cache references reject. Scales must be finite. All resolved strings are copied
into the candidate output; they are unresolved geometry/texture/FX names, not
validated rig/material/resource handles.

`coh_ent_custom_costume` consumes the source skin word, six-bit bounded part
count, two color words and region string per part. It has no indexed dictionary
references. Both APIs require non-debug packet framing; their caller must check
the transport debug flag. Reader and output commit together only on complete
body success. Each output records its exact ending bit, but neither API requires
packet end because more original fields follow these substructures.

`coh_ent_costume_envelope` consumes the complete original appearance envelope:
optional type, own-player rewards and slot metadata, deferred intent, single or
multiple bodies, supergroup body/mode/emblem, special FX, NPC fallthrough/custom
colors, owned costume, sequence name and optional world group. The wire
`num_costume_slots` field is **additional slots**, not the total; the source
`costume_get_num_slots` adds one and product entitlements. Zero additional slots
is valid. Current and stored body indices are bounded independently by source
`MAX_COSTUMES=10`; transmitted additional slots are preserved as their eight-bit
value. Full self flag must match the enclosing transaction's independently
verified entity ownership. Rewards preserve source list positions and filtered
holes. A missing reward indexed string, unknown type, count beyond admitted
bounds or malformed late tail rolls back the entire envelope.

This output is a wire event, not persistent player state. It preserves deferred
intent and raw special-FX names; it does not schedule costume changes or perform
FX normalization. The later semantic owner must preserve prior world group for
absent/empty optional strings, retain custom NPC colors when that source flag is
absent, and clear prior full-costume special FX when its flag is absent. It must
apply source packet order and generation checks across the complete entity
transaction. The historical owned-costume consumer skips the body on stale
packets; the native parser deliberately validates its full body before any
future stale-event discard, avoiding cursor desynchronization. The oracle
executes nonstale original envelopes, not that historical stale-body bug.

Entire/owned/custom cases remain unsupported in `coh_ent_appearance` and
`coh_ent_record` until transaction composition and lifetime ownership exist.
Power-customization transaction composition (its wire syntax is now separately
qualified), titles and very-rare entity continuation are still open.
Consequently no standalone body or envelope can produce an authoritative actor,
make an entity list complete, or enable READY, RECEIVED_CHARACTER or full-update
acknowledgment.

## Qualification boundary

`costume_oracle.py` extracts and executes unchanged original
`costume_send`, `costume_receive`, `NPCcostume_send`, `NPCcostume_receive`, cached
string/color functions, indexed packet functions and BitStream primitives from
the pinned import. Synthetic engine objects, stash slots, body-part metadata and
storage adapters are explicit in `costume_oracle_shim.h`. Producer and consumer
execute independently before expected POD values are compared to native results.
Both bit-packed and byte-aligned modes cover extra-info/raw scales, implicit
part counts/quantized scales, zero parts and custom color bodies. Original `entSendCostume`, `entReceiveCostume` and both costume reward functions
also execute with deterministic storage/menu/render adapters. Ten envelope
scenarios in both alignment modes include self single/multiple/deferred,
supergroup/FX/NPC-custom fallthrough, owned, NPC, sequence, no appearance, ten
stored bodies and a new character with zero additional slots. Original decoded
bodies, consumer-owned fields and reward names are compared; source input metadata
provides expected presence and filtered reward positions not retained by the
original consumer. A call-through observer records only body destination and
ending cursor around the unchanged receiver. Runtime renderer/asset behavior,
FX canonicalization and a real MapServer do not execute in this oracle.

Tests verify every-bit truncation rollback, dictionary deep copies after input
destruction, identity mismatches, malformed indexed/cache references, finite
scales, count/string limits, aggregate memory refusal and randomized bodies.
See `qualification/appearance-envelope-20261016/` for current source hashes,
fixture identities and
host release/ASan/UBSan results. Android build/emulator, physical device and
authentic server interoperability require separate receipts. Rollback is a
revert of this additive entities-only change; accepted APKs and user data are
unmodified.
