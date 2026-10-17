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
| 1 | optional per-entity debug and global entity debug | `engine/entity-frame/` composes the supported full-update header/list/control/delete prelude. Non-debug zero-consumption follows the pinned original global-debug guard; debug=true refuses. Original debug dictionaries/recording/command framing remain unsupported |
| 2 | `playerReceiveControlState` | Existing source-qualified bounded control staging is composed after the supported non-debug entity list in `engine/entity-frame/`. Full-state original producer and TEST_CLIENT consumer fixtures qualify offsets; physics-history execution, pushes application and diagnostic recording remain unsupported |
| 3 | `entReceiveDeletes` | Existing parser/staging apply now composes after control in the supported entity prelude. Candidate tombstones, source packet ordering (equal create/delete packet IDs retain live slot), selected DBID/entity/index and late rollback are checked. Unsupported authentic entity-record branches still prevent broad initial-packet acceptance |
| 4 | `receiveCharacterFromServer` for full update | Complete bounded raw outer-body groups1..6 composition source/host/sanitizer qualified in `coh_character_outer.*`; dictionary/gameplay application, required semantic presence/identity and enclosing ALLENTS composition remain open |
| 4a | otherwise `SendCharacterToSelf` stats | Standalone complete absolute schema supported; correct outer offset not established |
| 5 | power-info update, power-mode update | Complete standalone raw PowerInfoUpdate staging is source/host/sanitizer qualified in `engine/entity-globals/POWER_INFO_CONTRACT.md`, including both flag branches and mandatory range list. Independently qualified `coh_power_ranges.*` preserves the narrower range-only/flag=false contract and refuses flag=true. Raw CRC/F32 events have no dictionary/state authority. Complete standalone power-mode replacement/retain wire grammar is source/Android qualified in `engine/entity-globals/`; enclosing offsets, dictionary resolution and transaction composition remain open |
| 6 | badge update and full-update badge monitor | Complete bounded standalone badge/player/supergroup/history and ten monitor-ID wire bodies source/host/sanitizer qualified in `engine/entity-globals/coh_badges.*`; both Android ABI builds and Android 13 x86_64 execution passed in run 38970381196. Dictionary/UI application, original monitor filtering/sorting and enclosing transaction remain open; no physical or authoritative actor acceptance |
| 7 | generic inventory and invention updates | Complete bounded raw inventory staging and producer-defined invention diagnostics are source/host/ASan/UBSan qualified in `engine/entity-inventory/`. Auction text remains opaque; dictionary/parser semantics unresolved. Original invention consumer is a no-op: nonzero status is refused by the normal phase, including state zero |
| 8 | workshop string | Exact original sender/consumer statements qualified with original bitstream code. Atomic inventory/invention/workshop composition admits at most31 bytes plus NUL and refuses overflow; no workshop lookup or gameplay application |
| 9 | conditional team, super stats, conditional league | Complete raw team/league source producer/consumer fixtures and bounded native staging qualified. Superstats whole producer and independent model qualified; original consumer executable qualification remains open. `engine/entity-social/` qualifies ordered fragment composition and skip flags, without previous/local state application or dictionary authority |
| 10 | optional attribute descriptions | Monitor-only11-slot body qualified against whole original producer/consumer with explicit description/value/UI fixture shells. Full mode refuses until the exact ordered category/attribute/contribution dictionaries are admitted. Outer present flag is composed in the diagnostic suffix |
| 11 | dynamic groups and sky fade | Dynamic full-zlib/delta wire diagnostic qualified against whole original producer and independent model; numeric expected count does not authenticate original tracker occurrence order, generation or graph ownership. External zlib stack/sanitizer closure remains open. Whole original sky sender/consumer qualified; actual sky resources unresolved |
| 12 | optional slave pitch/yaw/roll | Exact original conditional producer/consumer blocks and finite3F32 raw staging qualified. Outer master/slave/control-client ownership selection is not executed by those fixtures. Camera PYR is not selected-character orientation |
| 13 | exact packet end and complete transactional admission | Source-ordered initial GLOBAL suffix through sky/slave is host/ASan/UBSan qualified using released bounded scratch loans and immutable packet-backed spans (`engine/initial-suffix/`, published2cdbaf42). Syntax-complete diagnostics return UNSUPPORTED for unowned dynamic data; reader/public output remain unchanged. Supported non-debug entity prelude composition is separately qualified in `engine/entity-frame/`; authentic selected-player very-rare/appearance/taskforce/buff record closure, dictionaries and appended command framing still gate acceptance. Original server may append SERVER_BEGIN_BYTE_ALIGNED_DATA plus entityPacket commands; suffix end is not transport end. No actor or acknowledgment permitted |

## Full character tail, original `receiveCharacterFromServer` order

1. Five packed server-state flags; auth-user-data bytes; player type/subtype,
   praetorian progress and location. Complete bounded standalone pre-character
   wire prefix is source/host/ASan/UBSan qualified in `coh_character_prefix.*`.
   Original auth array is 128 bytes and always aligns to the next byte, even
   outside byte-aligned scalar mode. Auth bytes remain un-applied account
   entitlement metadata; no full-character or outer-update composition.
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

Groups1..6 now have a bounded atomic raw owner in `coh_character_outer.*`:
account prefix, complete `character_Send` metadata, original powerset names,
ally/gang/PvP/self stats, then full tray/modes/name/strings/help/windows, ordered
reward/account/chat/title/keybind/options/control/friend/monitor/rename tails.
The composed source fixtures preserve exact child cursor boundaries and late-
field rollback. Original whole group5/6 sender/consumer and helper functions
execute independently with explicit fixture shells and complete field/string
projections. The enclosing whole original character function is not executed.
The raw owner ends after rename. Dictionary authority, original
`character_Receive` gameplay application, selected identity, required semantic
presence masks and complete enclosing packet admission remain open. This raw
wire closure does not establish whole-message admission. Apparent optional
absence cannot be assumed; native parsing must validate the actual wire flags.
Unknown data must never be skipped by scanning for a plausible later sentinel.

## Authentic costume input and cache-branch progress

Exact client donor bins are preserved and verified in
`qualification/costume-export-20261017/`. `engine/costume-inputs/` fully decodes
BodyParts.bin and supergroupColors.bin against original whole body table
readers/writers:28ordered parts and160ordered RGB records, with complete original
byte roundtrips. This does not establish current server cache consumption.
`engine/stash32/` preserves modeled Win32 uint32 hash arithmetic, original probe
and resize order; its source-checked160color super-palette prefix has256slots,
not the complete global palette. Full costume.bin/tree and ordinary/extra/final
palette dictionaries remain under development; no complete slot generation or
actor receipt exists.

Read `engine/costume-inputs/CACHE_HIT_SCOPE.md` and its source audit. Successful
original ParserLoadFiles binary read returns BEFORE text preprocessing:
ParseBoneNames/costume_preprocess are not rerun on that route. Missing generated
BoneIdEnum is a text/fallback-regeneration dependency, not an invented gate for
exact admitted binary-cache-hit consumption. Original shared first/error paths
still run passed final costume_fillExtraData; shared data-acquired reuses existing
state without rerunning it. Actual source/profile/cache/shared branch selection,
complete builder semantics and generation equality must be established.

## Closest selected-record composition dependencies

The core `coh_ent_record` still refuses actual supported-by-standalone branches;
its list/frame success currently covers only the restricted existing profile.
In source order, the next bounded composition work is:

1. Replace only the medium-rare appearance parser's refusal of owned/full/custom
   variants with the standalone complete costume envelope under an admitted
   matching dictionary and selected-self identity. Preserve translucency, stale
   costume packet ordering, prior ownership/deferred/retain-clear events and all
   candidate lifetimes; do not place huge costume envelopes in every entity slot.
2. Replace the very-rare immediate POWER_CUSTOM refusal with complete standalone
   power customization then titles, and continue into existing ragdoll/common
   pchar/stats/vision/target/status/inventory-size fields at their real offsets.
   Raw CRCs remain unresolved until admitted dictionaries are bound.
3. Compose the later very-rare block: selected-self taskforce architect/parameter
   body with the admitted costume dictionary, then qualified rare-prefix fields
   through AFK, then qualified supergroup/leveling-pact/logout suffix. These are
   separate source boundaries; success of the early very-rare pair does not
   authorize skipping this later block.
4. Compose the complete teammate/buff grammar at the FINAL per-entity flag. Core
   parser currently consumes that flag and refuses true. Preserve raw CRC/mod
   identities, source order and state-retain/diff/delete/timer semantics, with
   atomic rollback if any preceding or later entity fails.
5. Close noninstant/interpolated pose branches if the actual selected source
   profile needs them; keep current refusal when not qualified. Retain NetFX/
   sequence events with exact asset generations, and source control future-push/
   record_motion semantics at their separate frame boundary.

After those record branches, compose list/control/delete with the qualified raw
character/global suffix using source flags and stable offsets. Maintain unique
selected DBID/index/entity generation, packet/session/deletion ordering,
aggregate scratch/retained budgets and dictionary/resource lifetimes. Neither
standalone complete wire bodies nor a numeric source-prefix slot count can mint
an actor or completion acknowledgment.

## Smallest next authentic closure

First close complete **selected self create**, then the global initial tail:

1. Derive with the qualified original offline builder or capture/import exact costume
   string/color stash slots and source body-part
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
   with pinned class/origin/basepower identities; compose the now complete raw
   outer character owner with post-character global tails, including
   PowerInfoUpdate. Standalone wire metadata is not that whole transaction.
4. Execute original complete initial-update producer in a disposable source
   environment; bind synthetic oracle and authentic capture identities separately.
   Apply exact-end, selected DBID/entity ownership, dictionary generations, stale
   packet/session and delete validation in one transaction.

This is not blocked solely on server access: the unimplemented client grammars
remain substantial. Source substructures can continue without server access;
final complete qualification needs authentic source/profile dictionaries and
actual complete packets. A capture alone cannot make an incomplete parser safe.
The remaining entity very-rare/appearance/buff composition, dictionary-bound
character application and complete enclosing framing remain implementation
requirements. Outer character and PowerInfoUpdate/global wire bodies already
have qualified raw standalone/suffix owners; do not relabel those completed
subgrammars as missing. Source semantics and authentic runtime admission are
both required before complete publication.

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

## New standalone Android13 wire checkpoint

Source d949c59fd579bd7256445078cc6aeacc3b331c70, run38993564322 and exact
artifact12086321527 qualify the new character prefix and power-range/false
PowerInfo bodies on host release/ASan/UBSan, ARM64+x86_64 builds and actual
Android13x86_64. Prefix646561/280 fixtures and ranges85440/208 fixtures match;
owned device files are removed and verified absent. ARM64 execution, whole
character/full true PowerInfo, enclosing exact-end transaction, actual dictionary/
DBID admission, immutable actor and completion ACK remain unqualified. Full
receipts are retained under independent-wire-android13-38993564322; do not
promote these standalone successes into full-update application.
