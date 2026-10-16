# Bounded native entity inspection and staging

This optional C99 module advances original-source entity parsing beyond the
existing update-header and standalone position inspection. It is **not wired
into Combined**, does not alter the accepted APK, and does not acknowledge a
full update or publish an authoritative actor. Gates 25–27 remain open.

## Implemented boundaries

| Entry point | Source-qualified scope |
|---|---|
| `coh_ent_next_index` | Original `previous + packed_delta + 1` sparse list candidates with explicit modulo-2^32 arithmetic and bounded result; starts at -1 and supports source append passes that descend |
| `coh_ent_create` | `checkEntCreate` create/sentinel bits, entity generation, player/self/DBID, optional pet metadata without basepower, class/origin indices, titles, name/phase/seed, villain/group/definition references, optional animation and persistent-NPC names, contact handle |
| `coh_ent_orientation` | Original nonlinear 9-bit quaternion reconstruction and per-component packet ordering, recomputed nonnegative W and normalization |
| `coh_ent_record` | Complete **supported individual** create/update records through trailing teammate flag, using the accepted 24-bit scale-64 position kernel; modes, movement sequence values, bounded triggered moves, AI list, absent costume, translucency, bounded ragdoll values, numeric vision metadata |
| `coh_ent_list` | Atomic complete **supported list substructure** through the canonical end sentinel, including descending indices and the sentinel after the maximum entity slot; validates selected/self ownership across the caller's entire bounded staging table |
| `coh_ent_deletes` | Complete standalone delete count and index/generation pairs, at a known source-defined substructure boundary |
| `coh_ent_stage_deletes` | Atomic batch application to caller-owned staging slots/tombstones with original creation/deletion packet ordering |
| `coh_ent_full_update_tail` | Always returns `COH_UNSUPPORTED` at the supplied boundary; no attempt to skip opaque character/global tails |

`coh_ent_create` is a metadata-only entry point and does not prove an entity
record is complete. Its diagnostic class, origin, owner, creator and contact
identities are **unresolved numeric references**. Optional strings besides the
entity name are bounded and discarded; they do not create valid appearance or
asset state. The selected DBID must match a self-player create. A nonself player
claiming the selected DBID is rejected. Other-player DBIDs are validated positive
signed values and retained as their own identities.

A successful `coh_ent_record` is one supported record in a **staging buffer**.
It does not mean a whole ALLENTS/UPDATE is valid. Production integration must
support the necessary entity branches, parse global debugging/control state, deletes,
character/full-stats, powers, badges, inventories, teams/leagues, dynamic groups,
sky and embedded commands; resolve all necessary class/origin/appearance/data
schemas; validate global unique self ownership; then commit the whole packet
transaction. That complete tail is not implemented here. No executable code in
this module sends `READY`, `RECEIVED_CHARACTER`, `ACK_FULL_UPDATE`, or any socket
message. No offline preview data participates.

`coh_ent_list` starts at the first source delta and consumes only the entity-list
substructure. It accepts a caller-owned table of at most 256 uniquely indexed
slots/tombstones and a separate `CohEntListWorkspace`. The workspace is scratch
(150,528 bytes on the host ABI); use an arena, heap or static owner, rather than
putting it on the call stack. The caller must supply its complete staging table;
ownership checks cover that supplied table and cannot detect omitted entities.
Each referenced slot must already be indexed in the table, including creates.
Missing capacity is `COH_NOT_FOUND`, never a new dummy entity. The workspace may
contain partially parsed values after failure; it must never be published.
The reader, input table and list receipt change only after the full supported
list and ownership checks succeed. All API objects must be nonaliasing and have
one owner thread. Unmentioned slots retain their values.

The list owner rejects duplicate record indices, including after a descending
append, and requires the original producer's canonical packed delta 0 / create
1 / end 1 sentinel. It probes this sentinel before applying ordinary entity
slot bounds: after entity 10239 its synthetic index is 10240. The sentinel is
not an entity or a duplicate record, even if its synthetic index equals an
earlier entity index. The delta helper alone retains its candidate bound of
0..10239; the list owner handles the maximum-slot sentinel separately.

Both the seeded table and completed staged table must have at most one live
self player. A live self must have player type and the selected DBID; a live
nonself player cannot claim that DBID. These are explicit native admission
guards: the old client simply selected the last `make_player` object, and did
not validate packet-wide uniqueness. Empty lists and fragments with no self
remain valid grammar and report `self_index=0`; they establish no selected
character authority. A self receipt also remains unresolved staging metadata,
with no appearance, character-tail, actor or ACK authority.

## Exact unsupported boundaries

These branches fail closed with numeric stage and last completed scalar bit
position. Public reader, staging slot and output structures remain unchanged:

- Pet creation with a basepower dictionary reference.
- Interpolated position offsets when interpolation is active and movement is
  not instantaneous. The accepted standalone position kernel is reused only
  after authentic preceding record fields have been read.
- Network FX with character state, any nonzero appearance type, and every
  `very_rare_bits` continuation (starting at power customization).
- Character-stat schema (`pchar_things`), therefore real player full updates,
  targeting/status/inventory and self taskforce state.
- Teammate/buff payloads and the entire full-update/global/character tail.

A known staging slot with no live entity returns `COH_STATE` on update; an
index absent from the list caller's table returns `COH_NOT_FOUND`. Unlike the
original client, this module does not fabricate a dummy entity. An older create/update cannot
replace a newer slot generation or bypass a newer deletion tombstone. Duplicate
create packets with the same creation packet ID are rejected as a conservative
admission rule, even though the old client can reuse the existing object.
Orientation updates use the original strict greater-than per component rule;
position retains the original per-bit ordering including equality. Deletion
uses source packet ordering rather than requiring generation IDs to match: a
newer deletion removes the older occupant even if the slot was reused. Equal
create/delete packet IDs retain that occupant, matching the original source.

Packet IDs use the original unsigned comparisons; wraparound recovery is not
implemented. A transport/session owner must reset staging on a new session and
must not use this module to admit a wrapped sequence silently. Every index in a
delete batch must already have a staging slot or tombstone; missing capacity
rejects the entire batch without mutation.

Source slot indices are bounded to `1..10239` (`MAX_ENTITIES_PRIVATE=10240`).
Index zero is admitted only as the empty-list terminator; a create/update using
it fails. Entity generations are separate positive signed
IDs up to `INT32_MAX`, **not** capped to the slot index: fixtures include generation
70001. Generations are derived from the original server `++ent_id`; positive
signed range is this module's explicit admission budget. Class/origin indices
are capped at 65535 pending actual dictionary admission. Delete batches have a
native 256-record limit (original server can emit more), triggered moves a
16-record budget, entity lists and supplied tables a 256-slot budget, and
strings retain the bounded original receiving capacities
(up to 1000 bytes including NUL). Exceeding a limit is reported, never silently
truncated. No parser allocates heap memory or stores borrowed packet pointers.
All APIs require a single owner thread and nonaliasing input/output structures.

## Source oracle and evidence

`source-pins.json` pins 14 original files from the imported Thunderspies source
at `0b75ade0c801735e10c5798f641948a45cc50488`. The checker compiles 24 unchanged
original functions: BitStream writers/reader, optional scalar/string/auto
writers, `entSendCreate`, `entSendPetInfo`, `entSendPosUpdate`,
`entSendQrotUpdate`, `entSendModes`, `entSendSeqTriggeredMoves`,
`entSendAiAnimList`, `entSendDeletes`, `unpackQuatElem`, quaternion helpers and
`entGetOrientation`. `oracle_shim.h` supplies explicitly synthetic engine data
and lookup adapters. It does not emulate a MapServer, a real account, or a
complete class/power/appearance dictionary. The unsupported generic collision
prediction adapter aborts if the fixture accidentally exercises it.

Individual create and deletion fixtures execute the complete original producer.
Quaternion expected values execute the original client consumer, including
partial, stale and duplicate-component updates. Complete supported record
fixtures compose the original create/position/quaternion/mode/trigger/AI
producers in the audited outer source field order, with explicit field writes
for other flags and sequence/ragdoll/vision values. They are **not** produced by
the entire original `entSend` outer function. Separate manual source-layout
fixtures, every-bit truncation, malformed counts/identity/ranges, unsupported
branches, rollback, tombstone ordering and 20,000 randomized bodies cover the
native parser. All fixtures are synthetic; none proves actual server traffic.

List fixtures compose those same unchanged original component functions into a
single original BitStream. Cases include ascending and descending NPC records,
entity 10239 followed by the sentinel, and synthetic self metadata. The self
fixtures deliberately suppress `pchar_things` and other unsupported player
branches; they are not real complete player creates. This fixture composer
does not execute the original complete `sendEntity` or `entSendUpdate` function.
Manual list fixtures separately cover malformed sentinels, duplicate/zero
indices, missing slots, unknown updates and a later unsupported appearance.
Tests check every-bit truncation with table/reader/receipt rollback, seeded
global ownership conflicts, untouched self slots, stale creates/updates and
deletion tombstones. Release, ASan and UBSan run the same fixture/test set.

```sh
python native-android/engine/entities/check.py --source-root . --sanitize \
  --fixtures-output /tmp/entities-fixtures.h \
  --output /tmp/entities-host.json \
  --ndk /path/to/android-ndk-r28c --android-output /tmp/entities-android
cmake -S native-android/engine/entities -B /tmp/entities-cmake
cmake --build /tmp/entities-cmake
```

The Android output contains one retained `fixtures.h`, per-ABI executables and
receipts binding fixture/source/binary SHA256 values. Host release, ASan and
UBSan execute the same new code and fixture set. The historical x86 original
oracle runs at `-O0` on trusted aligned/padded inputs outside sanitizer coverage.
LeakSanitizer is disabled because its `/proc` walk is unavailable in this
sandbox; ASan memory-access and UBSan checks remain enabled. Android cross-build
receipts say `executed:false`; execution requires a separate Android 13 x86_64
qualification receipt. Cross-building ARM64 is not physical Thor acceptance.

Rollback is removal/revert of this additive directory. There is no APK, profile,
asset, character, account, launcher or saved-data migration.
