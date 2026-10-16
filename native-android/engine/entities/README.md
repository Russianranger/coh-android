# Bounded native entity inspection and staging

This optional C99 module parses original-source entity substructures. It is
**not wired into Combined**, does not modify accepted APKs, and cannot admit a
complete ALLENTS/UPDATE transaction or publish a server-authoritative actor.
`coh_ent_full_update_tail` remains unconditionally unsupported. No API emits
READY, RECEIVED_CHARACTER, ACK_FULL_UPDATE, BASEPOWER_NOT_FOUND or other packets.
Gates 25–27 remain open.

## Current boundaries

| Entry point | Implemented scope |
|---|---|
| `coh_ent_next_index` | Original modular sparse-list index arithmetic; descending passes supported |
| `coh_ent_create` | Full audited create-header branches including player/self/DBID, pet basepower full-name CRC, class/origin indices, titles/name/phase/seed and other bounded references |
| `coh_ent_orientation` | Original nonlinear 9-bit XYZ quaternion reconstruction and per-component packet ordering |
| `coh_ent_appearance` | NPC dictionary index/costume index and sequence-name appearances, world-group string, translucency; full, owned and custom NPC costumes fail closed |
| `coh_ent_costume_dictionary_load` | Immutable generation-bound deep copy of original sparse string/color table slots, at most 4 MiB; import identity must be independently verified |
| `coh_ent_costume` | Complete pinned raw `costume_receive` body shared by full/owned costumes; standalone and reused by the appearance envelope, outside entity record integration |
| `coh_ent_custom_costume` | Complete pinned raw `NPCcostume_receive` custom color body; standalone and reused by the appearance envelope, outside entity record integration |
| `coh_ent_costume_envelope` | Standalone complete pinned appearance wire envelope: self rewards, full/single/multiple/deferred, supergroup, FX, NPC/custom fallthrough, owned and sequence variants; not yet composed into entity records |
| `coh_ent_power_custom` | Standalone complete pinned power-customization wire envelope and lists: self/other/owned, slot metadata, raw power CRC/color/token events; no power dictionary or entity-record admission |
| `coh_ent_titles` | Standalone complete title/name/player-metadata update, bounded original string sizes and exact stale/equal packet behavior; not yet composed into entity records |
| `coh_ent_taskforce` | Complete bounded consecutive selected-self architect and taskforce-parameter substructures, optional contact costume reuse, raw time deltas and retain/clear event flags; no taskforce state application or record admission |
| `coh_ent_rare_prefix` | Consecutive bounded odd-send/combat/player/PvP/collision/name/pet/AFK wire events; no state application, dictionary resolution or record admission |
| `coh_ent_character_stats` | Complete pinned basic/self absolute non-debug stat schemas: current/max attributes, levels, XP/debt/rest/influence, per-scalar packet ordering |
| `coh_ent_netfx` | Complete bounded original NetFX grammar, including entity/position origins and targets; unresolved events only |
| `coh_ent_target` | Target, assist, taunter, self clear-target and bounded placater list |
| `coh_ent_status_effects` | Crowd-control mask, vision metadata and bounded designer-status strings |
| `coh_ent_inventory_sizes` | Pinned five inventory types, used/total capacities, auction and boost capacities |
| `coh_ent_record` | Atomic supported individual records including NetFX events, basic stats, target/status and self inventory sizes; supported NPC/sequence references and prior movement/sequence/ragdoll/vision branches |
| `coh_ent_list` | Atomic supported list through canonical sentinel; selected/self ownership over supplied complete bounded table |
| `coh_ent_deletes`, `coh_ent_stage_deletes` | Standalone delete grammar and atomic staging with original creation/deletion packet ordering |
| `coh_ent_full_update_tail` | Always unsupported; consumes nothing and cannot unlock rendering/acknowledgment |

All references remain **unresolved staging metadata**. A power CRC, NPC index,
class/origin index, sequence or world-group string is not an admitted dictionary,
rig, texture or resource generation. Optional create strings other than entity
name remain bounded/discarded. No offline preview data establishes identity.

A self player must match the selected DBID; a nonself player cannot claim it.
The list validates at most one self across the entire supplied table, including
untouched slots. An empty list or zero-self fragment is valid syntax and provides
no player authority. Missing indexed capacity never creates a dummy entity.
The canonical delta=0/create=1/end=1 sentinel is checked before ordinary slot
bounds, including after entity 10239. Duplicate records are rejected, including
when an append pass descends. Table, result and reader commit together only after
all supported records and ownership checks succeed.

## Statistic schemas and source comparison

`Common/entity/attrib_net.c` is pinned and its unchanged declarations are compiled
in the source oracle. `SendBasicCharacter` maps low-resolution attributes into
stable named slots; `SendCharacterToSelf` maps highest-resolution current and
high-resolution maximum attributes. The public arrays use this order:

- Attributes: hit points, absorb, endurance, meter, perception radius, player
  stealth radius, confusion, to-hit.
- Integers: level, combat level, XP, debt, rested XP, influence.

Absolute packed signed values are decoded explicitly, including negative stats.
The original quantization and original consumer produce the expected values.
Every scalar has its own packet ID and valid bit. A stale scalar is consumed
without replacing newer state; equal IDs retain original acceptance semantics.
The schema walker rejects unknown/duplicate fields, removed embedded structs
and relative nested values. These APIs require non-debug packets and absolute
`ParserRecv(..., sendAbsoluteOverride=true)` framing. The session owner must
check the transport debug flag; `CohRepReader` does not carry it.

An important source detail: `ParserSendEmptyDiff` calls `ParserSend` with the
same old/new object, **but a forced full update still serializes all fields**.
It cannot safely be treated as a single zero bit. The record parser now accepts
the full basic schema, and the self schema is available at its standalone
source boundary. Neither means `receiveCharacterFromServer` is complete.

## Limits, ownership and rollback

No wire parser allocates memory or retains packet pointers. The separate costume
dictionary loader deep-copies an admitted import into one allocation. NetFX is copied into
`CohEntRecord` as bounded unresolved event metadata. The existing list inspection
API does not retain per-record event lists; a future complete transaction owner
must explicitly retain them before publishing or executing any effects. List
validation is not event delivery (the same applies to triggered moves). The
NetFX client timer is retained as its packed wire integer; the original engine
converts that integer to `F32` when populating its runtime NetFx object. API objects must not alias
one another and have one owner thread. Workspace contents after failure are
unspecified and must never be published. On the current 64-bit ABI:

- `CohEntSlot`: 3,600 bytes.
- 256-slot caller table: 921,600 bytes.
- `CohEntListWorkspace`: 922,624 bytes.
- Table plus scratch: 1,844,224 bytes, excluding packet and caller metadata.
- `CohEntCostume`: 49,008 bytes; its separate workspace: 80,920 bytes.
- `CohEntCustomCostume`: 16,904 bytes; one bounded local candidate during parsing.
- `CohEntCostumeEnvelope`: 692,064 bytes; separate workspace: 772,984 bytes.
- `CohEntPowerCustomEnvelope` and workspace: 1,114,392 bytes each; at most 512
  items per list and 4,096 across ten lists. See `POWER_CUSTOM_CONTRACT.md`.
- `CohEntTitles`: 388 bytes, including a single bounded local candidate during
  parsing; not embedded into every existing entity slot. See `TITLES_CONTRACT.md`.
- `CohEntTaskforce`: 70,632 bytes; off-stack workspace: 151,552 bytes. One prior
  event, candidate event and workspace total 292,816 bytes before shared costume
  dictionaries/other session data. See `TASKFORCE_CONTRACT.md`.
- `CohEntRarePrefix`: 1,456 bytes, plus a bounded local candidate; raw presence
  events only. See `RARE_PREFIX_CONTRACT.md`.
- Immutable costume dictionary: at most 4,194,304 bytes, including slot tables,
  palette, strings and owner metadata. A generation swap retaining the old owner
  may temporarily require two dictionaries; see `COSTUME_IMPORT_CONTRACT.md`.

Allocate the table and scratch on the heap, arena or static owner, never the
Android thread stack. Query `sizeof` on the target ABI. Record-local temporaries
are bounded. Slot count remains 256; this is an explicit admission ceiling,
not whole-zone scalability acceptance. Definitions and graphs have separate
budgets owned by their modules.

Additional budgets: slots 1..10239; positive signed entity IDs and DBIDs;
16 triggered moves; 32 NetFX events; 256 deletes; 32 placaters; 16 designer statuses of at most
127 non-NUL bytes; 259-byte sequence/world-group strings; exactly five inventory
types. Inventory capacities admit signed-positive integer range and do not
assume used <= capacity (source inventories may be over capacity). Exceeding
bounds fails rather than truncates. Packet IDs use source unsigned comparisons;
transport must reset state for a new session and refuse silent wraparound.

Creation cannot replace a newer generation/tombstone. Duplicate create packet
IDs are conservatively rejected. Deletes compare source packet order, not delete
entity-ID equality; equal creation/delete packet IDs preserve the live occupant.
Generation replacement resets appearance, stat channels, inventory and target
state together through `coh_ent_slot_init`.

## Source oracles and evidence

`check.py` pins 33 original files imported at
`0b75ade0c801735e10c5798f641948a45cc50488`. It compiles unchanged original BitStream
functions, create/pet/position/quaternion/sequence/AI/delete/costume/target and
inventory producers. Exact original `ParserSend`, `sdPackStruct`, scalar/struct
senders, `ParserRecv`, `sdUnpackStruct`, scalar/struct receivers and the original
schema declarations independently produce and consume basic/self statistics.
Original quaternion consumption remains independently compared. Original
`entSendNetFx` and `entReceiveNetFx` independently verify all event fields, both
origin/target modes, forced/incremental source filtering and zero counts.

`oracle_shim.h`, `stats_oracle_shim.h` and `costume_oracle_shim.h` adapt deterministic synthetic engine
objects/storage. Unsupported engine callbacks abort. Original NPC/sequence
costume producer paths are executed. The separate costume oracle executes the
unchanged raw `costume_send`/`costume_receive` and
`NPCcostume_send`/`NPCcostume_receive` producer/consumer pairs, including original
cached/indexed string and color functions. It compares all 30 scales, all 72
supergroup color words, part strings/colors and body metadata in both wire
alignment modes. The outer appearance producer `entSendCostume`, consumer
`entReceiveCostume` and both original reward functions now execute independently
as well. Fixture storage/menu/render adapters provide deterministic destinations
and side effects; runtime costume application, deferred scheduling, FX
canonicalization and resource lookup are not qualified. Target
and inventory fixtures execute complete original component producers. Status
strings are manual source-layout fixtures, not executed original status
producers/consumers. Complete supported record/list fixtures compose original
components plus audited outer flags; they do not execute complete original
`sendEntity`, `entSendUpdate` or a MapServer. No synthetic fixture is actual
server traffic.

The title oracle extracts the unchanged `if(e->pl)` title statement block from
the very-rare section of `sendEntity`; it **does not execute complete
`sendEntity`**. The complete unchanged `entReceiveTitles` consumer executes
against array-backed fixture entity/player storage. Both source fragment hashes
and scope are recorded separately. Packet string and storage adapters are
explicit; the source bit writer/reader and automatic integer functions execute
unchanged. This compares all fields over 54 producer fixtures and 162
fresh/equal/stale consumer applications. See `TITLES_CONTRACT.md`.

Original power-customization list/envelope producers and consumers, sort
comparator, auto-sized packet functions and actual slot-count function also
execute. Explicit synthetic dictionary/earray/StructCopy/product adapters cover
unknown dictionary IDs, duplicates, ordering, absent versus empty lists and
maximum ten slots. Raw power CRCs remain unresolved; original source lookup
fallbacks do not establish asset validity. Native output retains wire order.

Tests include every-bit truncation/rollback, malformed and duplicate fields,
negative statistics, per-field stale packets, tombstones, ownership conflicts,
and 25,000 randomized bodies. Costume tests include immutable dictionary copies,
generation mismatches, sparse holes, cache underflow, invalid indexed references,
nonfinite scales and aggregate dictionary budget refusal. Release, ASan and UBSan run the same native tests.
The historical source oracle runs trusted padded inputs at `-O0` outside
sanitizers; LeakSanitizer is disabled because sandbox `/proc` walking is
unavailable. Cross-build receipts are not emulator or physical acceptance.

```sh
python native-android/engine/entities/check.py --source-root . --sanitize \
  --fixtures-output /tmp/entities-fixtures.h --output /tmp/entities-host.json \
  --ndk /path/to/android-ndk-r28c --android-output /tmp/entities-android
```

Generated fixtures require both the requested fixture header and its sibling
`costume_fixtures.h`; the checker copies both into the Android output directory.
No authentic costume dictionary has been captured. The load API compares a
supplied generation and manifest identity; it does not calculate a capture
digest or authenticate that identity. See `COSTUME_IMPORT_CONTRACT.md` for the
external verification prerequisite and unresolved asset boundaries.

See `INITIAL_UPDATE_CLOSURE.md` for precise remaining source-ordered branches and
actor admission rules. Rollback is reverting this additive module change; no
APK, asset, profile, account, database or saved-character migration exists.
