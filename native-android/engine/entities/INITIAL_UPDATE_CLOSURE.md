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
| 2 | rare / medium / very-rare flags | Complete selected SELF/CREATE composition now in `engine/selected-record/`; existing general `coh_ent_record` still refuses very-rare continuation |
| 3 | state mode | Supported |
| 4 | position and quaternion | Supported absolute/accepted position kernel; non-instant interpolated offsets still reject |
| 5 | sequence movement | Supported numeric sequence/tick/bits; no resolved animation resource |
| 6 | triggered moves and AI animation list | Bounded metadata; no FX execution |
| 7 | pchar flag and NetFX flag | Complete bounded NetFX event grammar supported; event handles/resources remain unresolved, list inspection does not retain events |
| 8 | costume and translucency | NPC index and sequence-name references supported. Complete appearance wire envelope and raw full/owned/custom bodies source-qualified standalone, including rewards/multiple/super/FX/NPC fallthrough. Selected raw SELF/CREATE composition validates these conditional variants using the supplied immutable dictionary and exact manifest; authentic runtime generation, semantic state application and general entity-list composition remain open |
| 9 | power customization and titles if very rare | Complete power-customization envelope and complete bounded titles update source-qualified standalone. Titles use the unchanged inline sender block and full original consumer, not complete sendEntity. Selected raw SELF/CREATE composition includes both; unresolved power CRCs, general records and authoritative application remain open |
| 10 | ragdoll | Bounded scalar consumption; not skeleton-qualified publication |
| 11 | basic character stats if pchar | Complete pinned basic absolute non-debug schema supported |
| 12 | vision phases, exclusive phase, yellow con | Supported numeric values |
| 13 | combat-mod shift if pchar | Supported numeric value |
| 14 | target/assist/taunter/placaters | Supported bounded metadata |
| 15 | status effects | Supported mask/vision/status-string metadata |
| 16 | self inventory sizes | Supported pinned five-type schema; does not contain inventory contents |
| 17 | self taskforce architect information and parameters if very rare | Complete bounded consecutive wire substructures qualified standalone, with cached/full/custom contact events and raw relative clock words. Selected raw SELF/CREATE owner composes both; prior-state application, retained contact resource identity and enclosing entity-list transaction remain open |
| 18 | odd-send, ally ID, ignore-combat flags/offset level | Complete bounded raw prefix is composed in the selected SELF/CREATE owner; no authoritative state application or general record admission |
| 19 | player type/subtype/praetorian/location | Complete bounded raw prefix qualified standalone; source self/player application remains separate |
| 20 | PvP, collision, selectable, no-draw, map visibility, contact/PNPC, con/walls | Complete bounded raw prefix qualified standalone; control/player/stale application remains separate |
| 21 | name, pet metadata, AFK | Complete bounded raw prefix qualified standalone; unresolved entity/power references and exact retain/clear/stale application remain separate |
| 22 | supergroup mission/tokens/recipes/details, leveling pact, logout | Complete bounded consecutive raw wire bodies source/host/sanitizer qualified standalone in `coh_very_rare_tail.*`; original stale-pact cursor mismatch retained as evidence; selected SELF/CREATE raw composition now includes this suffix; exact prior-state application and full entity-list composition remain open |
| 23 | teammate buff stream | Complete bounded `appendTeammatePacket`/`character_SendBuffs` raw grammar source/host/sanitizer qualified standalone in `coh_teammate_buffs.*`; power CRC/attribute dictionary authority, selected SELF/CREATE raw composition now includes the final buff body; stale/prior-state application and enclosing entity-list composition remain open |
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
| 13 | exact packet end and complete transactional admission | Source-ordered initial GLOBAL suffix through sky/slave is host/ASan/UBSan qualified using released bounded scratch loans and immutable packet-backed spans (`engine/initial-suffix/`, published2cdbaf42). Syntax-complete diagnostics return UNSUPPORTED for unowned dynamic data; reader/public output remain unchanged. Supported non-debug entity prelude composition is separately qualified in `engine/entity-frame/`; selected-player raw record composition is separately qualified in `engine/selected-record/`; authentic runtime dictionaries, other required records, whole-list integration and appended command framing still gate acceptance. Original server may append SERVER_BEGIN_BYTE_ALIGNED_DATA plus entityPacket commands; suffix end is not transport end. No actor or acknowledgment permitted |

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
not the complete global palette. `engine/costume-tree/` now decodes the entire
17,691,352-byte exact costume.bin offline with all13 actual source schemas.
Original reader/writer preserves every byte; independent streaming decoder and
original getters agree on138,760 nodes,2,030,156 fields and844,161 strings.
Original ParseTableCRC traversal/field handlers yield matching costume a3374618,
BodyParts cf27aba3 and superpalette f0095ef2 with explicit digest backing. This
proves schema CRC equality, not the runtime load branch. `engine/costume-builder/`
now executes complete original primary insertion order and modeled Win32-width
stash construction on those exact bins. Independent complete trace and slot replay
match every source slot/hole: ordinary13209/32768, extra156/256, palette224/512.
The source primary-slot projection SHA256 is
2e69212432d1b16a38f307aca16ac892cca56cf59128d5d8d25e71386da4af81.
Whole original SERVER finalprocessor with controlled account predicates preserves
all primary slots; ancillary dictionaries/account policy are explicitly excluded.
These are offline source-generation results, not an observed runtime generation.
Runtime cache/shared association and final immutable import admission still gate
actor publication; no actor receipt exists. The expanded29MiB source tree is offline preparer storage,
not qualified concurrently with Android world ownership under96MiB.

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
The selected initial SELF/CREATE record now has a bounded thirteen-stage raw
composition in engine/selected-record; entity-list integration, other/non-create
records, dictionary-bound character application and complete enclosing framing
remain implementation requirements. Outer character and PowerInfoUpdate/global wire bodies already
have qualified raw standalone/suffix owners; do not relabel those completed
subgrammars as missing. Source semantics and authentic runtime admission are
both required before complete publication.

## Source DB selection identity bootstrap

`engine/entity-bootstrap/` supersedes earlier claims that MAP_CONNECT has no
DBID. DB character lists/choose requests omit DBID, but the exact original DB
producer writes EntCon.id as the handoff first scalar. Queue forwards all7fields
unchanged. Generic raw `link_id` remains untrusted/command-context dependent.
Only the opaque validated DB session's WAIT_MAP owner associates that positive
signed32 field with its selected slot/generation and returns selected_dbid in the
one-shot handoff. Original whole producer/queue fixtures, complete native parse,
source-context and actual UDP owner refusal/lifecycle controls qualify this
boundary. This is not observed live Map identity or encrypted authentication.
The selected Map create must still agree on unique self DBID/entity/index and
normal viewed-entity profile. Original clientGetViewedEntity can select a slave;
that alternative cannot silently replace the selected character. Complete
self/character/dictionary/suffix/world/framing gates and actor/ACK remain open.
Read entity-bootstrap/CONTRACT.md for atomic transaction/lifetime requirements.

## Selected initial raw record composition

Source3dc8f9f28 and receipt55c1db2f0 add `engine/selected-record/` without
changing existing accepted clients or gameplay ownership. The thirteen ordered
stages consume create/pose/sequence, triggers/AI, NetFX, appearance, power
customization, titles, ragdoll, common character fields, taskforce, rare prefix,
SG/pact/logout and final teammate buffs. Every conditional required child must
validate before the reader and compact packet-backed result commit. Appearance,
power and other large child PODs occupy one charged scratch loan at a time;
immutable bit spans retain exact payloads under the enclosing packet lease.
Generation alone cannot replace the supplied dictionary manifest. The named
aggregate budget includes retained memory and pre-reserved callback charge;
existing stricter SG/buff limits remain enforced. No scanning, skipping or
transport-end assumption is introduced.

The standalone source/component fixture qualification passes 352,228 assertions
per release/ASan/UBSan mode, including 25,411 truncations, 12,148 byte mutations
and 1,260 loan controls. Its historical outer/status fields remain explicit
synthetic composition. The subsequent actual outer qualifier executes whole
original sendEntity control with independently qualified original child spans,
including genuine selected-self full basic stats, sequence, non-RAGDOLL and
status writers. Its 144 profiles compare all thirteen source/native boundaries,
inline source fields, later boundary rollback and mutations. All child payloads
are replayed at every bit offset before permitting relocation. Child fixture
objects remain independent of outer fixture objects; neither tranche claims
whole-engine execution, a live source generation, authentic selected identity or
actor. Original marker payloads alone do not qualify child grammar.

The closest record gates now are source-consistent whole selected-record oracle
inputs, admitted authentic costume/power/sequence dictionaries and runtime cache
generation, event retain/clear/application ownership, and complete list handling
for all other/non-create records plus selected-self uniqueness. This component
supports only initial selected SELF/CREATE and refuses other record profiles.
The owned positive selected DBID from the validated DB handoff must agree with
its self create. The whole list/control/deletes, character/global suffix, viewed
entity profile and enclosing command boundaries still need one atomic owner.
No renderer publication, immutable authoritative actor or completion ACK follows
from this raw record alone.

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

## Generic initial full-create list continuation

`engine/initial-record/` now shares a private grammar kernel with the unchanged
selected-only public profile. It stages the other-player/NPC initial branches,
including pchar-less and NetFX-only cases, with decoded self controlling
appearance/power, inventory and taskforce paths. Its compact whole-list owner
consumes every supported full-create record and the canonical sentinel,
preserves signed negative index deltas, enforces unique slot/server entity ID/
player DBID/selected self, and rolls back every public output on later failure.
Full mode/absolute position/quaternion/movement and rare groups are required;
noncreate/interpolated profiles remain unsupported. The existing 256-record
local bound is retained rather than replacing it with large per-entity PODs.
This does not change the older general `coh_ent_record`/`coh_ent_list` profiles.

The new source fixture tranche has 720 actual original outer-control record
profiles and 58 explicit list compositions with original bit writers, including
MAX-index sentinel, selected-last, negative deltas, duplicate identities,
256-record success, 257-record refusal and appended trailer preservation.
All 11,466 child relocation equalities pass; release, ASan and UBSan agree on
257,296 assertions, including 898 cuts, 11,464 mutations and 576 loan controls.
Parent/child aggregate charge is checked exactly, and the enclosing loan adapter
rejects aliases into the whole output/table/workspace, not only child outputs.
The selected-only component and actual outer regressions remain unchanged after
the kernel refactor. Original child/outer fixture object graphs are independent;
whole engine/visibility construction and actual runtime dictionaries remain
outside these host proofs.

The next implementation dependency is integrating this raw list with the
qualified control/deletes prelude and character/global suffix under one packet,
selection/session and dictionary generation. Exact appended command framing,
normal viewed-entity ownership, semantic dictionary/state/resource admission
and immutable actor publication remain open. A syntax-complete raw list alone
cannot emit READY, RECEIVED_CHARACTER or a full-update application ACK.


## Whole initial raw diagnostic composition (2026-10-17)

`engine/initial-update/` composes source header, complete supported generic
INITIAL create list, control, deletes, character groups1..6 and the complete
ten-stage global suffix under one bounded sequential-loan owner. Compact reports
retain exact immutable packet spans; no per-entity giant appearance POD and no
publication/ACK occur. The caller reader always stays unchanged because runtime
selected handoff/dictionary/world-generation authority is not yet admitted.

Trailing meta-command parsing consumes original nested GAME_CMDS15 and
BEGIN_BYTE_ALIGNED_DATA197 and requires a final Pack1zero at the exact payload
bit end. Unknown appended command bodies, missing/end-extra bits and marker cap
refuse. Read alignment padding is not required to be zero. This narrow framing
profile does not implement every possible appended game command. Retained
qualified original child bytes and complete original control writers form
explicit synthetic source-order joins, not a whole live original object graph.

Initial full_update forces both team and league upToDate flags to zero; existing
full social bodies are complete. A true flag is an impossible source initial
profile, not missing social grammar. Attributes are sent only at the owner/tick
modulo8 schedule. Their full branch additionally requires the saved combat
numbers window displaying; full ordered attribute values and modifier list now have a bounded schema-bound
raw decoder and additive enclosing profile; matching runtime generation and
semantic application remain unqualified. The monitor
branch already reads all11 source slots. Active invention raw producer data are
completely decoded in `coh_invention_update_read`, but the combined phase refuses
nonzero statusChange because the original invention_Receive is a no-op. Any
future producer-wire-only diagnostic extension must retain that distinction.

Same-packet create/delete order is preserved for admitted creates; unknown prior
tombstones require a previous-world owner. Raw control forced-position events
are not applied as final actor position. `initial-update/DICTIONARY_DEPENDENCIES.md`
records exact class/origin reverse-array lookup, normal/villain fallback, power
full-name CRC constructor, retained exact cache identities, SERVERONLY/shared
cache and callback gates. No invented BoneIdEnum requirement is added to an
exact cache-hit branch. Large power-tree eager materialization remains prohibited
by the aggregate working-set budget. Runtime dictionary generation, normal
viewed-entity ownership, semantic character/resources and actor application
remain gates even after supported raw initial syntax and exact end are read.

## Optional full attribute raw description (2026-10-17)

The additive `entity-attributes/coh_attrib_description` component now decodes the
full original ordered attribute-value and matching-modifier grammar, preserving
all raw power CRCs/source identities and exact row ordinals without applying
attribute/UI/contributor state. Its explicit full-schema prerequisite is the
new bounded `attribute-dictionary` candidate: exact authentic5892B cache,7cats/
69rows, whole original read/write byte equality and original ParseTableCRC with
static define traversal0x315acdb1. Normal/reverse ordering and all scalar/string
fields agree with an independent decoder. Runtime cache/shared selection and
matching live server generation remain unobserved; integrity does not mint
semantic dictionary or actor authority.

The native full reader is atomic across every required value/modifier and
optional callback cancellation. It retains finite raw floats, source2/3 names
and server IDs, and bounded unknown power/hash identities. The existing monitor
parser and social source are unchanged.144 retained whole-original full sender/
consumer fixtures and120 original monitor cases pass release/ASan/UBSan;
1,265,128 assertions/mode include416,464 every-bit truncations,648 cancellation
boundaries,181 mutations and13 explicit local modifier/text-cap/nonfinite/tag
controls. The latter are synthetic exact-original-leaf joins, not additional
original gameplay object executions. No complete initial update, actor or ACK
is accepted; the frozen original suffix/composer retains its previous monitor
profile. New additive schema-bound profiles preserve that API and behavior.

The additive `coh_initial_suffix_attributes_diagnostic` now composes that full/
monitor attribute transaction into the ten-stage source-ordered suffix. Original
suffix API and all native monitor/social implementations remain unchanged; nine
other dispatcher stage bodies are byte-identical to the frozen implementation.
80 exact-bit-offset full joins and55 existing source profiles qualify in the new
profile, with18,994 release/ASan/UBSan assertions/mode and4,675 balanced loans.
Schema/cache/control storage and parent aliases are checked/charged before loans;
peak active loan is5,993,424 bytes. Attribute-stage allowance is capped before
provider allocation by its standalone2MiB aggregate budget minus retained
parent/input charges, including explicit oversized-provider refusal. Whole suffix syntax still returns UNSUPPORTED
for world/dictionary ownership and never permits actor or ACK. The new additive `coh_initial_update_attributes_diagnostic` composes the same
optional grammar across header/list/control/deletes/suffix/commands with compact
packet-backed observations and sequential charged loans. The original enclosing
API remains unchanged. Its explicit source-leaf joins cover288 cases,96 raw
syntax/end candidates,42 truncations,138 mutations and108 loan controls. Exact
command-end framing retains its independent original-source qualification. All
whole-message failures preserve the public reader; runtime dictionary/current
selected owner/world authority, actor application and ACK remain false.

## Compact authentic origin/class cache prerequisites (2026-10-17)

`character-dictionary/coh_origins` now owns all five strings per original row,
preserves array indices/duplicate rows and source reverse ASCII name lookup.
The exact504B normal and124B villain cache bodies roundtrip through whole
original binary schemas and reproduce original ParseTableCRC0x6d177c17.
Fourteen original writer/consumer cases include unknown/empty names, duplicate
names, empty arrays and128/129 local-cap controls.80,864 assertions/mode pass
release/ASan/UBSan with19,668 truncations,19,680 mutations, C++ linkage and a
bounded copied owner. Qualifier project helper execution uses admitted source
bytes with stale-PYC and changed-source controls. Runtime shared-cache and
SERVERONLY generation association remain unobserved.

`character-dictionary/coh_classes` completes the raw nested class binary schema:
39 class fields,115 scalar attributes,115 attribute-array fields, named tables
and four final raw-pointer payloads. Exact normal1,219,292B/14-row and villain
4,228,088B/45-row bodies roundtrip through whole original readers/writers and
lookup functions; eight original writer variants and independent every-string/
root-field/modtable-span projections qualify with323,932 assertions/mode,
17,801 cuts,1,009 sampled mutations and recomputed-digest local-cap refusals.
The463,208B native owner copies linkage/name strings and leases immutable raw
attribute arrays rather than materializing a nested tree. The authentic villain
name Class_Minion_Henchman occupies indices23 and26; original reverse lookup
returns26. Both original rows/indices remain intact.

The frozen native class raw importer leaves source_crc_verified false. Its
original header observation is now supplemented by the separate nonshipping
exact dynamic-context reconstruction below. Original ParseTableCRC
includes g_pParsePowerDefines and its static wrapper, defined by s_PowerEnums,
AddSequencerDefines, AddAttributeDefines and AddAttribNames in original stash
iteration order. The new source-only provider reconstructs that historical
context; native runtime/cache-generation admission remains a separate prerequisite.
classes_Repack resolves real power categories/fallback arrays and creates final
attribute tables; classes_Finalize builds namedStash. Neither executes in this
raw importer. The retained cache has zero final-pointer payload sizes. No
class/origin semantic application or runtime/current-server identity is inferred.

Create wire selection uses normal arrays only for a player not being a critter,
otherwise villain arrays; character-name receive lookup has its distinct
normal-then-villain fallback. Actor composition must preserve those original
contexts, actual owned DB-to-Map selected identity and entity generation, and
must close power identifiers/current cache/world ownership. These copied raw
prerequisites do not publish an actor or authorize READY/RECEIVED_CHARACTER/ACK.

## Original dynamic define context and class schema CRC (2026-10-17)

The nonshipping `character-dictionary/class_defines_oracle` reconstructs the
actual historical dynamic context from all source s_PowerEnums, original E875
state rows, full source attribute offsets/aliases, exact10592B attrib_names and
normal origins. Whole original stash constructor/add/probe/resize/slot iteration,
DefineCreate/FromIntList/AddIntList/Add, all three Add*Defines/Names functions and
original ParseTableCRC/static/dynamic traversal execute. Original donor32-bit
ub4 and size_t AUTOINT behavior are explicit; whole source F32/AUTOINT macros
are retained with the donor field-width binding. The deep-string storage adapter
copies keys without choosing slots. No Win32 ABI/original unsafe-hash sanitizer
closure or actual StringTable engine startup is claimed.

The result matches exact historical class header0x7ff68aaf.1317 attempted
pairs produce1315 valid defines/2048 slots/four resizes. Independent source
construction compares all pairs and each slot/hole/value using independently
qualified byte-safe hash and probe/resize model:32051 comparisons across8
profiles. Omitted/reordered phases, changed parsed-name fixtures, an early
duplicate and wrong float default alter the CRC; a later case-insensitive
duplicate retains first value and CRC. Actual collisions are kEvade468 refusing
320 and kCombatPet_Group21 refusing24. All baseline trace/slot bytes are retained
with source/helper/input hashes; source-only helper/PYC controls qualify the
executed source graph. Original attrib_names schema also reproduces its
0x1f5ae0b6 header and exact whole-body roundtrip.

This closes an offline source-schema/constructor prerequisite, not native current
MapServer cache or entity-generation admission. Native class raw owner flags
remain unchanged. Actual power categories, classes_Repack/Finalize, SERVERONLY/
shared cache branch and current-server generation are still required before
semantic class/actor application. No actor or READY/RECEIVED_CHARACTER/ACK.

## Authentic raw category owner continuation (2026-10-17)

Source c92e1fdf5 and receipt81739adf6, independently sealed F e55bb842b,
qualify the exact historical239,304B powercats.bin payload and copied immutable
category owner. Original schemaCRC0x59248ecb and binary roundtrip match; all186
category rows,6,527 ordered set references and zero packed pointer-index rows
survive. Whole original category-only powerdict_CreateDictHashes and category
lookups execute:186 valid/512 slots. Dictionary-level set/power arrays are empty
in this profile; their semantic ownership/full dictionary remains unqualified.

Native release/ASan/UBSan each80,281 assertions qualify eight original-writer
variants,297 truncations,581 mutations, source duplicate refusal, unknown raw
identifiers, budget/alias/provider rollback. Owner374,856B and same transient
workspace fit the exact input under1MiB. Historical category/schema matching
does not admit current MapServer/SERVERONLY/cache generation or actor/ACK.
Actual class repack projection and named-table finalization remain separately
tracked components; no unchanged raw-importer authority flag was enabled.

## Compact selected-class source repack projection (2026-10-17)

Source534b6a9b6/receipt3c4dbac9e, independently sealed F5d1bf63a8, adds a
2,880B copied historical selected-class/level projection. Whole original
classes_Repack/CreateCharacterAttributes/TransposeArray executes using explicit
pointer/heap/category-lookup/retirement fixture interfaces. All59 actual rows
at first/middle/final levels and original-writer default/short-array/fallback
variants yield195 independent690-word comparisons; release/ASan/UBSan each
272,493 assertions, C++ and measured native stack pass. No full table allocation
for every class/level is needed. Source double-Defense, last-Absorb and absent
ElusivityBase/default1 behavior is preserved.

The frozen raw class importer remains unchanged with source_crc_verified false.
Separate historical schema proof and selected-row projection do not admit current
SERVERONLY/shared/cache generation, power-set/base-power ownership or authentic
actor/application ACK. Named-table Finalize/GetNamedTableValue is separately source-qualified below;
these components are not an accepted live dictionary.

## Bounded historical class named-table owner (2026-10-17)

Sources18892c8e1/9e337a4d6 plus REQUIRED588b0f698, receipts ee8882023/
5088b9e89/cf73aa246 and independent Fca42 qualify unchanged whole original
classes_Finalize/class_GetNamedTableValue and stash interfaces on exact class
inputs. Actual normal1,296 named tables and villain4,005 have no duplicates or
empty value arrays. Fourteen original-writer profiles cover same-class duplicate
refusal, empty keys, empty arrays, unknown names, empty table lists and bounded
work refusal;23,671 independent source/native queries and260,792 assertions
per release/ASan/UBSan mode pass.

The compact owner borrows the immutable raw class dictionary/input lease (56B);
value observations own24B. Empty string keys are source-supported. Missing keys
report found=false/source1.0 fallback; empty arrays refuse original unsafe
negative indexing. Oversized positive indices repeat the final value. Native
finite ASCII profile and8MiB aggregate budget are explicit. Every raw record
validates once; source key duplicate checks precharge at most8,388,608 length/
byte comparison work units. Source-accepted256 distinct259-byte keys cost
8,486,400 units independently and deliberately return native LIMIT atomically.

This closes historical class repack/named-value prerequisites without changing
frozen raw class owner flags. Full authentic set/base-power grammar/ID ownership,
actual SERVERONLY/shared/cache-generation association, selected Map/DB/entity
generation, world/resource closure and atomic actor/application ACK remain gates.
No runtime class identity is inferred merely from a matching historical CRC.

## Historical complete power-set schema and compact index (2026-10-17)

Source06eef892f/receipt38467ddaf, independently sealed Ffc8568d2a, qualifies
the exact3,179,276B historical powersets cache SHA256
afadc5f3ae6fc9c9c413924cec75bb911ff5cd4ce37388c6737cdb5786d9d547.
Unchanged original schemas/readers/writers and actual static definitions yield
ParseTableCRC0x2fe0d52d and byte-identical roundtrip. All30 fields/6,547 allocated
sets/20,351 ordered power-name refs/zero persisted pointer indices remain.
Whole original set-only CreateDictHashes/GetFullName executes; every16,384 hash
slot and first-winner index agrees with native. Raw duplicate rows persist and
constructor rejection is explicit. Eight original writer variants,4,754,836
assertions per release/ASan/UBSan,344 cuts248 mutations, C++ and native stack
controls pass.

The immutable metadata owner196,704B borrows the3,179,276B input; the equally
sized workspace retires after import. A bounded field getter preserves all
encoded fields without dense per-row field metadata or base-power objects.
Historical category-name audit resolves6,527 refs and preserves all20 additional
allocated sets not named by those refs. This is not world reachability or active
generation: full forward-pointer/basepower construction and matching current
SERVERONLY/shared/cache association remain gates. No actor or application ACK.

Standalone dictionary caps require phased pre-world imports or a future explicit
qualified parent/child aggregate-budget adapter. Live world bytes cannot silently
be omitted from retained_bytes; mathematical96MiB sums do not admit the running
global pipeline.

## Historical full-power stream and raw CRC index (2026-10-17)

Source9f7362cbf/receipt9d5c8dd83, independently sealed F43ed6d67d, qualifies
bounded traversal of exact62,047,164B powers.bin SHA256
25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d.
Original complete table readers/writers roundtrip all20,241 BasePower records,
and original fullname hash matches every stored CRC. Nested source grammar keeps
113,046 AttribModTemplate/7,165 SuppressPair/0 PowerVar/7,103 PowerCustomFX records.
Observed0xb553b8ff remains a header, not recomputed original ParseTableCRC.

The native1,048,744B immutable owner plus transient1,052,840B workspace uses a4KiB
read buffer and borrowed immutable file/provider lease, without eager62MB tree.
Every65,536 source integer-stash diagnostic slot agrees, with duplicate rows
preserved/first CRC winner returned. Six original-written record fixtures,
434,417 assertions per release/ASan/UBSan, source helper/Git binding, sampled
truncation/mutation/provider error/digest/cancellation rollback, exact budget,
C++ and native stack checks pass. The original host oracle remains unsanitized;
LSAN/Win32/Android are not qualified. Before/after-finish cancellation respects
digest retirement and preserves output.

This is standalone historical raw schema/index admission. Complete original
ParseTableCRC needs genuine static/default tables plus source dynamic defines;
no binary enum/default shells or matching observed header can replace it.
Whole global dictionary construction, original DuplicateMissingPowers/Finalize/
forward/back pointer semantics, CLIENT/SERVERONLY/cache branch and current
set/category/power generation association remain gates. Source forward-pointer
resolution includes alternate setFullName+'.'+power.shortName identities; raw
count equality is insufficient. Literal4MiB module import cap still needs phased
pre-world ownership or an explicit qualified global budget adapter. No semantic
class/power, selected-entity actor, world or READY/application ACK is published.
