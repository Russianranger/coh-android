# Native world session: next parallel contracts

This read-only source audit follows the qualified native session foundation at
`28c46f015e4405b162c87c9dcdab98de7c04ea39`. It adds no decoder or acceptance
claim. Gates 22–24 remain physically accepted; full gates 25–27 remain pending.

| Independent stream | Concrete contract and acceptance boundary |
|---|---|
| Controlled server | Matching AuthServer/DbServer/MapServer binaries, effective protocol/encryption/checksum policy, AuthServer-compatible SQL/ODBC schema, disposable account and existing character. Record the actual encrypted Auth→DB→Map exchange using the redacted [capture contract](engine/session/server-oracle/CAPTURE-CONTRACT.md). Development fake auth does not qualify account login. |
| Static scene transaction | Complete bounded static `SERVER_GROUPS`: matrix/property helpers; file/definition/child/reference/string budgets; exact sentinels, CRC trailers and end validation; existing asset-catalog resolution. Reject base/raid explicitly. Stage every change until the entire transaction validates. Only complete scene acceptance can authorize requesting all entities. |
| Entity record and identity | Complete source entity-create and conditional record traversal; server-index/DBID/own-player metadata; position/orientation/sequencer/costume schema mapping; generation and packet-order protection. An unknown branch rejects the entire update. Recognizing a candidate own-player DBID alone cannot spawn an actor. |
| Full-update tails | Independently bounded control/future-push/physics/deletion leaves, then complete character/dictionary/struct-diff, power/inventory/team and appended game-command tails. Build paired original-producer oracles. Defer full-update application ACK, READY and RECEIVED_CHARACTER until full-message validation and atomic state publication. |
| Android application | Bind the session owner to one native owner thread, Android permissions/JNI, explicit endpoint and selection UI, foreground reauthentication and diagnostics export. Join controller/camera, validated server pose and the existing support audio/UI/animation adapters. Preserve accepted offline and conventional clients. Ship one combined APK once this integrated path has a meaningful physical test. |

## Source read order and unframed boundaries

`Game/src/group/groupnetrecv.c:worldReceiveGroups` reads the existing metadata
prefix, packed file count, `receiveGroupFile` indices 1..N−1 then 0, root
references, two packed counts and two CRC32 trailers. Each file has a get-file
bit, path, checksum32 and base-file bit. Ordinary definitions use def-id-plus1
records terminated by zero. Root references use a packed index, UINT32_MAX
sentinel, definition name and, when nonempty, `getMat4`.

`receiveDef` contains in-use/name/modification fields, children with names and
matrices, then presence-controlled LOD, lighting, cubemap, sound, fog, volume,
beacon, tint, texture, alpha and property branches, texture swaps, geometry name
and hide state. There is no per-definition, file or reference byte length.
Unknown fields cannot be skipped safely. `libs/UtilitiesLib/src/network/netcomp.c:getMat4`
uses flags and optional compressed position/angles/scales or twelve raw floats.
`Common/group/groupProperties.c:ReadGroupPropertiesFromPacket` contains a 32-bit
count and name/value strings/type flags. Base/raid dispatch reaches
`Game/src/bases/baseclientrecv.c:baseReceive` and `baseReceiveAndLoad`, with a
zipped envelope and optional binary diff requiring independent expansion/patch
budgets and schema handling; it is outside the proposed static-map admission.

For `SERVER_ALLENTS`, `Game/src/clientcomm/clientcomm.c` consumes full-update ID;
the native client must defer the original early application ACK.
`Game/src/entity/entrecv.c:entReceiveUpdate` then reads the odd-send flag,
`cmdOldReceive`, clocks/debug/interpolation, and delta-indexed entity records
through `entReceive` and `checkEntCreate`. The source entity terminator is
delta 0/create 1/last-ent 1. A create includes packed 12-bit server entity ID,
type, PLAYER make-player flag, optional access level and packed 22-bit DBID,
followed by many conditional create/state/appearance branches.

After the entity loop come debug state, `playerReceiveControlState` future
pushes/physics/control state, `entReceiveDeletes`, full-update
`receiveCharacterFromServer`, powers/badges/inventories/team/supergroup/league,
attributes, dynamic groups, sky and optional slave camera. Character receive
reaches `character_net_client.c:character_Receive`, dictionary-dependent powers
and inventory, the self-character struct diff, trays/windows/chat/keybinds/
options/friends and further state. Finally `handleGameCmd` may consume an
appended command stream including `SERVER_BEGIN_BYTE_ALIGNED_DATA` realignment.
Entity records and the full character tail have no generic skippable byte length.
Compare `MapServer/src/entity/entsend.c`,
`MapServer/src/gameComm/sendToClient.c` and the full-character producer
`MapServer/src/entity/entserver.c:sendCharacterToClient`. Character schema
references include `Common/entity/attrib_net.c:SendCharacterToSelf` and
`SendBasicCharacter`; `sdUnpackDiff` aliases `ParserRecv` from
`libs/UtilitiesLib/src/utils/structNet.c`. The original early
`Game/src/gameComm/initClient.c:notifyReceivedCharacter` side effect must also
be staged. Unknown shortcut argument schemas can block safe update-prefix
consumption before the entity list; only ten schemas are currently admitted.

These are implementation gaps independent of server access. Both entity and
tail streams can develop source-oracle tests concurrently, but neither alone
qualifies a live world. Current native NetLink/replication reassembly bounds
are 16 KiB; the DB wire parser's 64 KiB bound does not enlarge transport admission.
Measure genuine source packet sizes before designing any additive widening.

Real server access, authentic account/character handoff, complete decoding,
Android execution of that actual session and physical Thor acceptance are
separate requirements. Scripted peers and original-function oracles cannot
substitute for them.
