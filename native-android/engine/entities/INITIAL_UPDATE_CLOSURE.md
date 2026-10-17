Qualification update: source `234d9c71869c91ccf8453e2a0e29df2ed0f18b32`
passed standalone suffix host/sanitizers, both ABI builds and Android13x86_64
execution in run38991372171 (2,701,932 controls). New teammate grammar passed
host/sanitizers and both ABI builds in run38991372131 (812,687 per mode);
teammate Android execution remains pending. Exact artifacts are retained in the
20261017 emergency recovery handoff. Full initial-update/actor/ACK gates below
remain open; no physical or live-world acceptance follows from these results.

# Initial authoritative update closure ledger

Checkpoint: additive entity continuation from remote
`cda93d96f8696e6a0f2ec6940a0c96e5b852f281`. Original source import:
`0b75ade0c801735e10c5798f641948a45cc50488`; exact source hashes are in
`source-pins.json`. This ledger records implementation boundaries, not acceptance.

Qualification update: primary run
[38970381196](https://github.com/Russianranger/coh-android/actions/runs/38970381196)
at source `41b4f585f90023e06ea2c8e7c50f4d505deb8e4f` passed host/sanitizers,
ARM64 and x86_64 builds, and Android 13 x86_64 execution. Globals passed 6,968,876
checks including 1,038,766 badge checks. Evidence:
`native-android/combined-client/evidence/20261016/primary-recovery-next/primary-android13-41b4f585/`.
These are standalone source-oracle contracts; ARM64 execution, physical Thor,
complete initial transaction and authoritative actor acceptance are not implied.

## Entity record, original `Game/src/entity/entrecv.c:entReceive` order

| Step | Boundary | Status / remaining work |
|---|---|---|
| 1 | Delta index and `checkEntCreate` | Supported create metadata including pet power CRC; dictionary references unresolved |
| 2 | rare / medium / very-rare flags | Read; very-rare continuation still rejects |
| 3 | state mode | Supported |
| 4 | position and quaternion | Supported absolute/accepted position kernel; non-instant interpolated offsets still reject |
| 5 | sequence movement | Supported numeric sequence/tick/bits; no resolved animation resource |
| 6 | triggered moves and AI animation list | Bounded metadata; no FX execution |
| 7 | pchar flag and NetFX flag | Complete bounded NetFX event grammar supported; event handles/resources remain unresolved, list inspection does not retain events |
| 8 | costume and translucency | NPC index and sequence-name references supported. Complete appearance wire envelope and raw full/owned/custom bodies source-qualified standalone, including rewards/multiple/super/FX/NPC fallthrough. Entity records still reject these variants pending dictionary capture, complete transaction ownership and semantic state composition |
| 9 | power customization and titles if very rare | Complete power-customization envelope and complete bounded titles update source-qualified standalone. Titles use the unchanged inline sender block and full original consumer, not complete sendEntity. Unresolved power CRCs and entity-record composition remain open |
| 10 | ragdoll | Bounded scalar consumption; not skeleton-qualified publication |
| 11 | basic character stats if pchar | Complete pinned basic absolute non-debug schema supported |
| 12 | vision phases, exclusive phase, yellow con | Supported numeric values |
| 13 | combat-mod shift if pchar | Supported numeric value |
| 14 | target/assist/taunter/placaters | Supported bounded metadata |
| 15 | status effects | Supported mask/vision/status-string metadata |
| 16 | self inventory sizes | Supported pinned five-type schema; does not contain inventory contents |
| 17 | self taskforce architect information and parameters if very rare | Complete bounded consecutive wire substructures qualified standalone, with cached/full/custom contact events and raw relative clock words. Prior-state application, retained contact resource identity and complete entity composition remain open |
| 18 | odd-send, ally ID, ignore-combat flags/offset level | Complete bounded raw prefix qualified standalone; no state application or record composition |
| 19 | player type/subtype/praetorian/location | Complete bounded raw prefix qualified standalone; source self/player application remains separate |
| 20 | PvP, collision, selectable, no-draw, map visibility, contact/PNPC, con/walls | Complete bounded raw prefix qualified standalone; control/player/stale application remains separate |
| 21 | name, pet metadata, AFK | Complete bounded raw prefix qualified standalone; unresolved entity/power references and exact retain/clear/stale application remain separate |
| 22 | supergroup mission/tokens/recipes/details, leveling pact, logout | Complete bounded consecutive raw wire bodies source/host/sanitizer qualified standalone in `coh_very_rare_tail.*`; original stale-pact cursor mismatch retained as evidence; exact prior-state application and full entity composition remain open |
| 23 | teammate buff stream | Complete bounded `appendTeammatePacket`/`character_SendBuffs` raw grammar source/host/sanitizer qualified standalone in `coh_teammate_buffs.*`; power CRC/attribute dictionary authority, stale/prior-state application and enclosing entity composition remain open |
| 24 | canonical list sentinel; global unique self ownership | Supported across caller's complete supplied staging table |

## ALLENTS outer tail, original `entReceiveUpdate` order

The existing replication header parser is separate. Entity-list success does not
validate any row below. `coh_ent_full_update_tail` rejects without consuming data.

| Step | Boundary | Status / dependency |
|---|---|---|
| 1 | optional per-entity debug and global entity debug | Unsupported; transport/debug-profile contract required |
| 2 | `playerReceiveControlState` | Worker F's independently qualified `engine/entity-control/` supplies standalone bounded control staging (original TEST_CLIENT oracle); no outer-tail composition, physics-history execution or diagnostic recording admission |
| 3 | `entReceiveDeletes` | Standalone parser and staging apply supported; correct outer offset not established |
| 4 | `receiveCharacterFromServer` for full update | Unsupported composition; expanded below |
| 4a | otherwise `SendCharacterToSelf` stats | Standalone complete absolute schema supported; correct outer offset not established |
| 5 | power-info update, power-mode update | PowerInfoUpdate remains unsupported. Complete standalone power-mode replacement/retain wire grammar is source/Android qualified in `engine/entity-globals/`; enclosing offsets, dictionary resolution and transaction composition remain open |
| 6 | badge update and full-update badge monitor | Complete bounded standalone badge/player/supergroup/history and ten monitor-ID wire bodies source/host/sanitizer qualified in `engine/entity-globals/coh_badges.*`; both Android ABI builds and Android 13 x86_64 execution passed in run 38970381196. Dictionary/UI application, original monitor filtering/sorting and enclosing transaction remain open; no physical or authoritative actor acceptance |
| 7 | generic inventory and invention updates | Unsupported |
| 8 | workshop string | Unsupported in outer transaction |
| 9 | conditional team, super stats, conditional league | Unsupported |
| 10 | optional attribute descriptions | Unsupported |
| 11 | dynamic groups and sky fade | Unsupported |
| 12 | optional slave pitch/yaw/roll | Unsupported |
| 13 | exact packet end and complete transactional admission | Absent; acknowledgments must remain disabled |

## Full character tail, original `receiveCharacterFromServer` order

1. Five packed server-state flags; auth-user-data bytes; player type/subtype,
   praetorian progress and location.
2. `character_Receive`: class/origin **names** and dictionary lookup; packed
   level, combat-mod shift, build, location; complete power builds/sets/powers;
   inspirations; boosts; inventory contents. Numeric create class/origin indices
   alone do not satisfy this name/dictionary identity. The separately qualified
   `engine/character-data/` stages complete `character_Send` wire metadata under
   an explicitly bound shared-powerset profile. Its class/origin/power/reward/
   inventory references remain unresolved. Complete original gameplay-consumer
   application, dictionary authority and the outer transaction remain open.
3. Original power-set names; ally and PvP; `SendCharacterToSelf` statistics
   (only this standalone statistic substructure is implemented).
4. Tray and tray mode; entity name; entity strings; full help state;
   all original window records (source count and field grammar must be pinned).
5. Reward-token list and active-player-token list; LFG and hidden masks;
   supergroup mode/emblem; skills; team-buff/dock/inspiration modes; features.
6. Chat settings; titles; description; comment; keybinds/profile; options or
   mouse settings; dividers; control-first/nocoll; friends; combat-monitor stats;
   rename flag.

All six groups still require a bounded transactional owner. Reuse the qualified
standalone parsers; they do not establish whole-message admission. Apparent optional
absence cannot be assumed; native parsing must validate the actual wire flags.
Unknown data must never be skipped by scanning for a plausible later sentinel.

## Smallest next authentic closure

First close complete **selected self create**, then the global initial tail:

1. Capture/import the exact costume string/color stash slots and source body-part
   metadata through the new bounded versioned dictionary contract. Raw costume
   bodies, cached/indexed string/color grammar and the complete original outer
   appearance envelope are now source-qualified standalone. Compose those wire
   events into the complete entity transaction: packet order, prior costume
   ownership, deferred intent, optional-field retain/clear rules and generation
   lifetimes. Compose the now source-qualified power-customization envelope with
   an admitted power dictionary and the now standalone-qualified title update. Preserve every
   candidate costume event across the complete record under an explicit aggregate
   budget; do not embed the large envelope in every slot. Consume through read-only additive
   contracts with gameplay appearance ownership; do not edit its internals.
2. Retain/resolve staged NetFX events and compose the now standalone-qualified
   supergroup/leveling-pact/logout suffix and teammate buffs with all earlier
   entity fields; close interpolation encountered by the actual source profile. Independent original
   producer/consumer comparisons and later-record rollback are required.
3. Compose the separately qualified control-state block, retain/deduplicate its
   future-push events, and reuse the qualified complete `character_Send` wire
   metadata. Implement dictionary-bound `character_Receive` state application
   with pinned class/origin/basepower identities and the still-missing outer
   character UI/account grammars and post-character global tails, including
   PowerInfoUpdate. Standalone wire metadata is not that whole transaction.
4. Execute original complete initial-update producer in a disposable source
   environment; bind synthetic oracle and authentic capture identities separately.
   Apply exact-end, selected DBID/entity ownership, dictionary generations, stale
   packet/session and delete validation in one transaction.

This is not blocked solely on server access: the unimplemented client grammars
remain substantial. Source substructures can continue without server access;
final complete qualification needs authentic source/profile dictionaries and
actual complete packets. A capture alone cannot make an incomplete parser safe.
The unsupported very-rare/buff continuations, outer character fields,
PowerInfoUpdate and later global tails are missing source implementations or
composition, not merely runtime-data admission failures.

## Immutable actor boundary

Current PODs are mutable staging, not actor snapshots. There is deliberately no
public conversion that certifies a `CohEntSlot` or `CohEntList` as complete. The
renderer adapter may use deterministic fixtures under its fixture policy.
Production publication must be owned by a future complete transaction layer and
must bind selected DBID, unique slot/entity generation, exact packet/session,
position/orientation, basic/self stats, class/origin/costume/sequence dictionaries
and resource generation. All global tails and exact message end must pass before
minting its receipt. Failed preparation leaves the previous published generation
untouched. No READY/RECEIVED_CHARACTER/full-update ACK may depend on these staging
APIs or user-supplied booleans alone.
