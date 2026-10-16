# Bounded native entity inspection and staging

This optional C99 module advances original-source entity parsing beyond the
existing update-header and standalone position inspection. It is **not wired
into Combined**, does not alter the accepted APK, and does not acknowledge a
full update or publish an authoritative actor. Gates 25–27 remain open.

## Implemented boundaries

| Entry point | Source-qualified scope |
|---|---|
| `coh_ent_next_index` | Original `previous + packed_delta + 1` sparse list indices, overflow checked; starts at -1 |
| `coh_ent_create` | `checkEntCreate` create/sentinel bits, entity generation, player/self/DBID, optional pet metadata without basepower, class/origin indices, titles, name/phase/seed, villain/group/definition references, optional animation and persistent-NPC names, contact handle |
| `coh_ent_orientation` | Original nonlinear 9-bit quaternion reconstruction and per-component packet ordering, recomputed nonnegative W and normalization |
| `coh_ent_record` | Complete **supported individual** create/update records through trailing teammate flag, using the accepted 24-bit scale-64 position kernel; modes, movement sequence values, bounded triggered moves, AI list, absent costume, translucency, bounded ragdoll values, numeric vision metadata |
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
parse the complete entity list, global debugging/control state, deletes,
character/full-stats, powers, badges, inventories, teams/leagues, dynamic groups,
sky and embedded commands; resolve all necessary class/origin/appearance/data
schemas; validate global unique self ownership; then commit the whole packet
transaction. That complete tail is not implemented here. No executable code in
this module sends `READY`, `RECEIVED_CHARACTER`, `ACK_FULL_UPDATE`, or any socket
message. No offline preview data participates.

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

An unknown entity update index returns `COH_STATE`; unlike the original client,
this module does not fabricate a dummy entity. An older create/update cannot
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
it fails. A terminator after the maximum admitted index is conservatively
rejected by the index helper. Entity generations are separate positive signed
IDs up to `INT32_MAX`, **not** capped to the slot index: fixtures include generation
70001. Generations are derived from the original server `++ent_id`; positive
signed range is this module's explicit admission budget. Class/origin indices
are capped at 65535 pending actual dictionary admission. Delete batches have a
native 256-record limit (original server can emit more), triggered moves a
16-record budget, and strings retain the bounded original receiving capacities
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

```sh
python native-android/engine/entities/check.py --source-root . --sanitize \
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
