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

No parser allocates memory or retains packet pointers. NetFX is copied into
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

`check.py` pins 23 original files imported at
`0b75ade0c801735e10c5798f641948a45cc50488`. It compiles unchanged original BitStream
functions, create/pet/position/quaternion/sequence/AI/delete/costume/target and
inventory producers. Exact original `ParserSend`, `sdPackStruct`, scalar/struct
senders, `ParserRecv`, `sdUnpackStruct`, scalar/struct receivers and the original
schema declarations independently produce and consume basic/self statistics.
Original quaternion consumption remains independently compared. Original
`entSendNetFx` and `entReceiveNetFx` independently verify all event fields, both
origin/target modes, forced/incremental source filtering and zero counts.

`oracle_shim.h` and `stats_oracle_shim.h` adapt deterministic synthetic engine
objects/storage. Unsupported engine callbacks abort. Original NPC/sequence
costume producer paths are executed; full/owned costume paths are not. Target
and inventory fixtures execute complete original component producers. Status
strings are manual source-layout fixtures, not executed original status
producers/consumers. Complete supported record/list fixtures compose original
components plus audited outer flags; they do not execute complete original
`sendEntity`, `entSendUpdate` or a MapServer. No synthetic fixture is actual
server traffic.

Tests include every-bit truncation/rollback, malformed and duplicate fields,
negative statistics, per-field stale packets, tombstones, ownership conflicts,
and 20,000 randomized bodies. Release, ASan and UBSan run the same native tests.
The historical source oracle runs trusted padded inputs at `-O0` outside
sanitizers; LeakSanitizer is disabled because sandbox `/proc` walking is
unavailable. Cross-build receipts are not emulator or physical acceptance.

```sh
python native-android/engine/entities/check.py --source-root . --sanitize \
  --fixtures-output /tmp/entities-fixtures.h --output /tmp/entities-host.json \
  --ndk /path/to/android-ndk-r28c --android-output /tmp/entities-android
```

See `INITIAL_UPDATE_CLOSURE.md` for precise remaining source-ordered branches and
actor admission rules. Rollback is reverting this additive module change; no
APK, asset, profile, account, database or saved-character migration exists.
