# Initial ALLENTS first-create observation

The physical Combined 0.1.9 Thor reports prove initial packet receipt, not a
complete character transaction. The standalone report records INITIAL_OBSERVED;
the ZIP's later CLOSED state preserves the observation and verifies two owned
sockets closed. Their raw packet body was deliberately not retained.

The Combined diagnostic observer now calls `coh_initial_create_probe` during
the exact synchronous ALLENTS loan, using its actual shortcut schema and owned
selected DBID. It reparses the header from the **post-command** cursor, then
decodes the first delta and the complete original `entSendCreate` block using
existing native parsers. No second create grammar or speculative dictionary
generation is introduced. Default production Map/Local/replication sources and
Combined 0.1.9 imports, version, signing, saves and profiles are unchanged.

The numeric `world_handoff.first_create` report retains header/create end bits,
the first failing stage/cursor, entity index/type, self flag and raw self DBID
comparison. No name, DBID, entity ID, packet pointer or packet bytes are retained.
Before observation the report is null. A complete create normally reports
`UNSUPPORTED / FIRST_RECORD_BODY_REQUIRED`. Truncated/malformed input or an
unsupported header/profile reports its own earlier boundary. This syntax result
is separate from successful raw capture and never creates a transport failure.
The next record cannot be located until the current record's body is decoded.
No scan, skip, application ACK or gameplay publication occurs.

The next bounded body stage is now composed in that same loan. After a fully
validated create, `coh_initial_pose_probe` reads the rare flags, mode, absolute
position and complete quaternion. It reuses fresh position/orientation parsers
with the **actual transport message ID**, not a fabricated dictionary generation
or previous actor baseline. The original full-create profile requires all three
rare flags, a mode update, position mask7 and quaternion mask7; partial profiles
refuse. A zero mode is valid. Create position has no interpolation-extra bit.

`world_handoff.first_record_pose` reports numeric stage/end-bit observations
separately from the preserved create result. Successful pose inspection stops
at `UNSUPPORTED / FIRST_SEQUENCE_BODY_REQUIRED`; if the packet ends exactly
there, the pose remains validated and that missing next body reports INVALID.
It retains no coordinates, quaternion, mode value, packet ID or borrowed pointer.
Neither this stage nor its ordering stamps establish character/session ownership.
An unvalidated create leaves the pose report null. A missing transport ID
is explicitly reported as an INPUT refusal rather than replaced with a constant.

After that pose boundary validates, `coh_initial_sequence_probe` now reads the
same loan at `pose_end_bit`. It requires the initial movement-update flag, then
consumes optional Pack8 movement index, optional Pack4 timing and optional
11-bit movement flags. Rounded byte-aligned fields are width checked. It
preserves the existing consumer bounds of INT32_MAX for index and 65535 for
timing; absent optional fields are legitimate zero values.

The new numeric `world_handoff.first_record_sequence` projection retains only
offsets, presence and validation status. No movement index, timing, flags,
sequence/resource identity or packet pointer survives. Successful syntax stops
before triggered moves at `UNSUPPORTED / FIRST_TRIGGERED_MOVES_REQUIRED`; if no
following bits exist, sequence validation remains true but that next boundary
reports INVALID. Unvalidated create/pose prefixes leave the sequence report null.
This raw sequence observation neither resolves animation resources nor applies
character/actor state, packet ordering, an ACK or any authority.

The next exact-loan stage, `coh_initial_triggered_probe`, now starts at the
validated `sequence_end_bit`. It reads Pack1 count, then each Pack10 index,
Pack6 delayed timing and Boolean/optional Pack16 FX ID. Zero entries are valid,
including the original `set_triggered_moves` branch. The existing native cap16
is preserved although original `MAX_TRIGGEREDMOVES` is20; count17+ reports LIMIT
at this deliberately narrower profile boundary. Index/timing keep signed32
bounds; optional FX retains the fullU32 wire domain. Pack widths are minima,
not scalar maxima, and rounded compressed Booleans must still be0 or1.

`world_handoff.first_record_triggered_moves` retains only count, complete-entry
progress, end bits and the first failing stage/entry. Partial records do not
increment complete-entry progress. No entry values, FX/resource identities or
event/actor state are retained or applied. Successful syntax stops before the
AI-animation outer flag at `UNSUPPORTED / FIRST_AI_ANIMATION_REQUIRED`; no next
bits reports INVALID there with completed-list diagnostics preserved. An
unvalidated sequence leaves this report null. Its result stays separate from the
following AI-animation observation.

After the triggered list validates, `coh_initial_aianim_probe` starts at its
exact `triggered_end_bit`. Full-create requires the outer update flag1. The
inner optional-string flag may0 (NULL/empty), otherwise raw bytes are streamed
through NUL without copying, UTF-8 assumptions or animation assignment. The
native selected-record limit1000 includes NUL:999 characters plus terminator
fit;1000 nonzero bytes refuse with LIMIT. Compressed rounded flags remain
strict Booleans. Only byte count, presence and first failure are retained in
`world_handoff.first_record_ai_animation`. Success stops at
`UNSUPPORTED / FIRST_NETFX_REQUIRED`; exact end reports INVALID there with the
AI prefix still validated. No string or resource identity survives the loan.

The accepted NetFX stage composes `coh_initial_netfx_probe` at `ai_end_bit`. It
reads `pchar_things` and `inPhase`; only both1 introduce a NetFX list, while the
other three combinations have no count. The existing transactional
`coh_ent_netfx` parser consumes the complete bounded list into local scratch,
then discards it. Its32-effect cap, command/ID, finite-float, reference, bone
and timer bounds remain intact. Original server lists are dynamically sized;
the native32 cap is explicitly a narrower supported profile. Effect count is
published only after the complete list validates. No effect is executed or
resolved, and no FX ID, handle, coordinates or borrowed reference is retained.

`world_handoff.first_record_netfx` retains flags, count, offsets and the exact
child parser's first failure. It stops at
`UNSUPPORTED / FIRST_COSTUME_BODY_REQUIRED`; exact end reports INVALID there
with the NetFX prefix validated. An unvalidated AI prefix leaves it null.
Repeated create/envelope `inPhase` consistency remains unproved, explicitly
reported as `cross_prefix_in_phase_verified:false`; no whole-record acceptance
or ownership follows from these separate syntax observations. Existing report
capacity7168 bytes and all transport cleanup/resource limits are preserved.

The accepted costume-prefix observer, `coh_initial_costume_probe`, starts at that exact
`netfx_end_bit` in the same loan. It validates the optional Boolean/Pack2
appearance selector. Full-create requires a nonzero selector; type0 and unknown
types refuse. Entire-costume type1 compares its self bit with this same first
create's raw self observation. A mismatch reports STATE before rewards; a match
is only wire consistency, never selected-player ownership.

For self type1, it reads both U32 reward counts with the existing256-per-group
cap and streams absent reward flags. At the first present reward it stops
BEFORE `pktSendIndexedString`, reporting
`FIRST_COSTUME_REWARD_STRING_REQUIRED`. That field can select a literal or a
stash index; no dictionary dependency is asserted before its branch is read.
When both lists contain only absent entries, it reads deferred/current-slot/
additional-slot and stored-list framing. Initial creates force
`send_all_costume=1`, so self single-current updates refuse at MULTIPLE rather
than being admitted as an initial profile. Preserve10 stored bodies, nonzero
list count, current-slot bounds and current<count for full lists. Other-player
costumes require single-body framing. Slot/deferred values are never applied.

Complete type1 framing and owned type2 stop BEFORE the first raw costume body
at `FIRST_COSTUME_DICTIONARY_REQUIRED`: the existing full-body native decoder
requires a separately verified immutable dictionary/manifest. NPC type3 and
sequence type4 are classified at `FIRST_NPC_COSTUME_BODY_REQUIRED` and
`FIRST_SEQUENCE_COSTUME_BODY_REQUIRED`; their dictionary-free nested bodies
remain unread in this one milestone. Exact end at a next-body/string boundary
reports INVALID there, while any completed framing diagnostics survive.

`world_handoff.first_record_costume_prefix` retains only numeric progress,
counts, wire-self consistency and first failure. It does not call the complete
costume-envelope parser, supply any generation, resolve names/resources, skip
nested fields, or reach translucency. The fixed7168-byte total report limit,
cleanup and prior observations remain intact. Complete costume/character,
actor, ownership, generation and application ACK acceptance remain false.

The accepted first-literal observer, `coh_initial_reward_probe`, decodes exactly ONE nested
`pktSendIndexedString` leaf. The receiver calls it from the same loan only when
the accepted costume-prefix stage reaches a present reward. Its input cursor is
that prefix's `prefix_end_bit`, immediately after the outer reward flag. No
other record is scanned and the prior numeric prefix result is preserved.

Under this non-debug profile, nested presence must1: nested0 inside a present
reward is INVALID, matching the existing native envelope rule. The storage
flag is a strict Boolean. For `inTable=0`, raw bytes stream through NUL with the
existing `CohEntCostumeText.value` cap260 INCLUDING NUL:259 text bytes fit;
260 nonzero bytes return LIMIT. Nonnull empty literals are valid, and high-byte
text needs no invented UTF-8 restriction. No name or buffer is retained.

A complete literal sets only `literal_validated` and stops at
`FIRST_REWARD_CONTINUATION_REQUIRED` BEFORE remaining rewards or costume
framing. It neither accepts nor resumes the enclosing list. `inTable=1` stops at
`FIRST_REWARD_DICTIONARY_REQUIRED` immediately after that flag, BEFORE any
packed index even in the byte-aligned profile. No dictionary/generation argument
is supplied. Exact end at either boundary reports INVALID; a completed literal
remains observed. Malformed/truncated fields preserve their first scalar cursor.

The compact `world_handoff.first_reward_string` child reports status, stage,
stop bit, text-byte count and literal validation under the parent report's
unchanged authority-false fields. It remains null if no present reward is
reached. This one leaf grants no reward-list, costume, character, ownership,
source-generation, actor or application ACK acceptance.

The accepted `coh_initial_reward_list_probe` continues the bounded
reward-list syntax after that first literal. In the same synchronous loan, the
receiver derives the first count cursor from validated type1/self1 selector
framing: `selector_end_bit + (compressed ? 8 : 1)`. The new parser independently
re-reads BOTH actual U32 counts and every entry; it never accepts saved counts,
indexes or a previous report as resume context. Existing prefix and first-leaf
implementations/results remain unchanged.

Each group keeps the native256-entry cap, so at most512 flags/literals are
inspected. Absent flags count as complete entries. Every present entry reuses
the accepted literal parser, including strict flags, nested-null refusal and
the260-byte NUL-inclusive cap. Only complete literals advance the scratch reader
and entry count; an indexed or partial string preserves the current group,
zero-based entry index and precise child failure cursor/stage. Indexed storage
stops immediately before Pack, including in the compressed profile.

A complete literal at exact packet end is still counted. The enclosing parser
then distinguishes a missing next flag/count from both groups being complete.
Both groups complete sets `list_validated` for syntax only and stops BEFORE
original deferred/slot framing at `COH_INITIAL_REWARD_LIST_SLOTS` (stage6).
An exact end there returns INVALID with list completion preserved; otherwise
this diagnostic boundary returns UNSUPPORTED. That accepted helper remains unchanged. A separate bounded slot observer now
consumes this boundary as described below; reward eligibility/catalog membership
and all authority remain unaccepted.

The five existing `first_reward_string` fields remain intact. A compact
`progress` array is appended inside that same child only after continuation
runs, preserving its192-byte limit and the7,168-byte total report cap:

| Position | Meaning |
| --- | --- |
| 0 | Continuation status:1 INVALID,2 UNSUPPORTED,4 LIMIT |
| 1 | Stage:2 COUNT,3 FLAG,4 STRING,5 DICTIONARY,6 SLOTS |
| 2 | Reward group1 or2 |
| 3 | Zero-based active entry index;0 for count/empty group |
| 4 | Completed entries in group1 |
| 5 | Completed entries in group2 |
| 6 | Absolute first-failure/next-boundary bit |
| 7 | Both groups' syntax complete:0 or1 |
| 8 | Child leaf stage on STRING/DICTIONARY failure; otherwise0 |

The unchanged leaf stage enum maps2 PRESENCE,3 STORAGE,4 TEXT,5 DICTIONARY,
6 CONTINUATION. Partial/indexed entries never increment completion. A complete
reward list is not a complete character record or a session ownership proof.

The current addition, `coh_initial_costume_slots_probe`, starts at that exact
`list.end_bit` in the same immutable loan, only for validated type1/self1 initial
framing. It also runs after exact-end list completion, diagnosing the missing
deferred field rather than losing completed reward syntax. It reads strictly:

`deferred Boolean → current8 → additional8 → full-list Boolean → stored count4`

Each scalar has its own first-failure stage. Current must be<10; the full-list
flag must1 for this source initial profile; count must1..10 and current<count.
Current>=10 is LIMIT immediately after current, before additional slots. The
additional field admits all0..255 as raw syntax: original `num_costume_slots`
means additional slots, not total entitlement or ownership. The deferred bit is
observed without applying a timer policy. Rounded byte-aligned Boolean/count
values are width checked. Full-list0 returns UNSUPPORTED/MULTIPLE; no count or
body is read. Count0/11..15 and current>=count return LIMIT/COUNT.

Complete framing records only `framing_validated` and stops at
`COH_INITIAL_COSTUME_SLOTS_BODY`, BEFORE the first `costume_send` byte. It returns
UNSUPPORTED if bits remain, INVALID at exact end; framing completion survives.
No body dictionary flag/index, resource, translucency or following costume is
inspected. It never returns COH_OK. The old prefix, literal and reward-list
implementations/results remain unchanged; no dictionary/generation argument,
allocation, retained text/pointer or authority/application ACK is added.

Reward failures retain the accepted9-value `progress` tuple above. After both
lists complete, stage8..13 discriminates this compact7-value projection:

| Position | Meaning |
| --- | --- |
| 0 | Slot status:1 INVALID,2 UNSUPPORTED,4 LIMIT |
| 1 | 8 DEFERRED,9 CURRENT,10 ADDITIONAL,11 MULTIPLE,12 COUNT,13 FIRST_COSTUME_BODY_REQUIRED |
| 2,3 | Completed reward entries for groups1,2 |
| 4 | Reward-list end / slot begin bit |
| 5 | First-failure offset from slot begin; absolute cursor=position4+5 |
| 6 | Packed numeric slot metadata, described below |

Metadata bits:0 deferred;1..8 current;9..16 additional;17 full-list flag;
18..21 stored count;22 framing complete. Fields not yet read remain0. Completed
lists imply group2 and no reward-leaf failure; the prior final index is
`max(done1-1,0)`. No progress information is discarded. Maximum framing is22
packed or40 byte-aligned bits. Formatter rejects invalid domains/context before
packing. The first-literal's five fields,192-byte child,7,168-byte report,
existing overflow guard and cleanup are preserved.

## Original protocol evidence

In `upstream/ouroboros/MapServer/src/entity/entsend.c`, `entSendUpdate` initializes
the previous index to -1; `sendEntity` writes the signed delta as U32 and the
create bit before `entSendCreate`. The whole create producer writes its end flag,
entity ID/type, optional self/access/DBID, pet metadata, class/origin indices,
strings, seed and contact metadata. The visible list can precede the fallback
self send: the first entity need not be the selected character. Canonical list
termination is delta0/create1/end1. Byte-aligned booleans must still be 0 or 1.
`Game/src/entity/entrecv.c:entReceiveUpdate` confirms the enclosing source order.

The pose section is the unchanged original `entSendModes`, `entSendPosUpdate`
and `entSendQrotUpdate` calls at `entsend.c:3555..3565`, after the rare flags.
The create/full-update branch forces mode transmission and position/quaternion
masks7. The pose probe preserves its boundary before `entSendSeqMoveUpdate`;
the separate sequence probe now consumes that next leaf. Native validation mirrors the full-create invariants already used
by the private selected-record kernel without its later dictionary prerequisites.

`entSendSeqMoveUpdate` at `entsend.c:2582` and its original Game consumer agree
on update/optional-index/optional-timing/optional-movement order, with
`NEXTMOVEBIT_COUNT=11`. Full-create forces movement update1. The next medium-rare
call is `entSendSeqTriggeredMoves`, now handled by its separate bounded probe. Original server
`Entity.net_move_change_time` is U8; the original consumer receives U16. Fixtures
above255 therefore qualify the established consumer range only and must not be
claimed as representable original server object state. The bounded fixture
stance shells likewise do not establish live power/animation lookup or ownership.

`entSendSeqTriggeredMoves` at `entsend.c:2655..2684` and the corresponding Game
consumer use the same count/index/timing/FX order. The original producer adds a
delay clamped to0..15 only without FX, and uses zero added delay with FX. Its
timing expression converts through F32; original-producer high-timing fixtures
use safe representable values. INT32_MAX timing and overflow endpoints are
synthetic wire controls, avoiding out-of-range source float-to-int conversion.
The immediately following `entSendAiAnimList` at `entsend.c:2642..2652` writes
outer update then `pktSendIfSetString`: Boolean nonempty string followed by
raw NUL-terminated bytes. `send_appearance` is forced by create/full-update at
`entsend.c:3423..3431`. The original Game consumer assigns the animation list;
this diagnostic never calls that assignment. Original strings are not bounded
by1000; that limit comes from the existing private native selected-record.

`entsend.c:3582..3595` writes both NetFX envelope flags and conditionally calls
`entSendNetFx`, followed by costume in the already-required medium-rare branch.
The original Game consumer at `entrecv.c:3209..3227` confirms that ordering and
condition. Unchanged whole original producer `entSendNetFx` at `entsend.c:480`
and consumer `entReceiveNetFx` at `entrecv.c:1166` qualify the leaf grammar.
Framing shells do not establish actual server character state.

For the current prefix, `entSendCostume` at `entsend.c:2757..2900` defines the
selector/variant order. The original `sendEntity` create/full-update branch at
`entsend.c:3383..3388` forces `send_all_costume=1`, independently of the forced
appearance flag. The self branch writes rewards, deferred/current/additional
slots, full-list flag/count and then nested `costume_send`; the other-player
branch writes deferred, flag0 and one body. `entReceiveCostume` at
`entrecv.c:1931` confirms the framing. `ent_SendCostumeRewards` and its consumer
at `Common/entity/costume.c:3271..3355` define both count/flag groups. The next
`pktSendIndexedString` at `net_packetutil.c:191..217` can emit a literal or a
stash index; the accepted costume-prefix observer stops before those choice bits. No original nested
serializer/consumer behavior or dictionary identity is qualified by opaque
callsite witnesses.

For the new leaf, unchanged `pktSendIndexedString` at
`net_packetutil.c:191..217` and `pktGetIndexedString` at219..259 agree on nested
presence/storage/literal order. `str` is tested for null, not empty. The
non-debug profile excludes the optional debug string. `defaultBitsPack` uses
original `log2i(stashGetMaxSize(table))`: original storage-slot capacity, not
reward count or populated entries. The diagnostic never consumes that index.
Fixture stash capacities/hits are explicit adapters and establish no real
runtime dictionary, manifest or resource identity.

The current two-group continuation follows the unchanged whole
`ent_SendCostumeRewards` and `ent_ReceiveCostumeRewards` at
`Common/entity/costume.c:3271..3355`: U32 count/flags/indexed strings, then the
second independent U32 count/flags/indexed strings. Original dynamic lists are
not capped256; this is the deliberately preserved native profile limit. The
return to `entSendCostume` is immediately before deferred/current/additional
slot metadata. The new parser stops at that return boundary and never reads
those following fields. A fixture reward predicate or stash adapter cannot
establish actual reward eligibility or a genuine resource generation.

`e->id` is a raw server entity generation, distinct from entity slot, DBID,
packet ID and Map generation. A matching self create is only wire consistency
against the owned local-development handoff; it does not establish whole-list
uniqueness, authenticated server identity or source dictionary ownership.

The existing `initial-update` diagnostic composes list, control, deletes,
character/global suffix and command tail. It requires an actual costume
dictionary/manifest generation before complete records can be admitted. No Map,
message or session counter can substitute for that generation. All character,
source-generation, actor, ACK and world-authority flags remain false.

## Qualification scope

`check_initial_costume_slots_probe.py --sanitize --output NEW.json` executes
unchanged whole original `entSendCostume` and original bit writers. Explicit
member-subset fixture shells, a reward-call adapter and opaque `costume_send`
observers isolate the framing between reward return and first body call. It
does not claim original reward/catalog lookup, body serialization or a live
server transaction. The Game consumer is inspected, not executed. Initial
full-create requirements are qualified against source; native10-slot bounds
remain deliberate. Accepted source/receipt hashes are checked; old checker
mains and source/native suites are not replayed.

Release, ASan and UBSan each pass193,303 checks across158 fixtures, including
3,206 shortened extents,3,206 mutations,29,219 unread-tail controls,10 API/alias
controls and25 formatter-domain controls. Compressed malformed Boolean/count
values are synthetic controls: original `bsWriteBits` masks nominal width
before rounding; source count16 writes0 in both profiles. Native probe stack
is176 bytes; formatter frames are48/64 bytes, bounded.

Affected JNI release/ASan/UBSan each pass3,273 checks across60 scenarios, with
72 wiped frees. Observed maximum report is7,151 bytes. Bounded projection checks
reach7,163 bytes (155-byte child), preserving all other observed fixture fields.
This does not qualify every possible transport-counter combination or global
RSS; the existing overflow guard remains. All authority/application ACK fields
remain false.

The JNI fixture keeps the accepted two-list prefix bit-for-bit through1695,
then uses source-generated framing: deferred1,current1,additional255,full-list1,
count2. Framing ends1717 before opaque costume body witnesses. Mutating those
unread body bits cannot change the observation. Existing reward/list failures
remain explicit; exact-list end now identifies missing deferred. New controls
exercise each shortened scalar, full-list0, count0/15/current>=count and exact
body end, preserving authority-false fields and wiped cleanup.

Receipts/source hashes are in `qualification/initial-costume-slots-20261019/`;
focused CI is `Native initial ALLENTS costume-slot framing`. Exactly ONE slot
framing milestone ends here, before bodies. No renderer/compiler/network/
Android13 suites, original-server transaction, new Thor run or APK is claimed.
No complete server-backed costume/character acceptance is claimed.

The previously reported unsupported Map count is the ordinary successful GROUPS
inspector's deliberate UNSUPPORTED boundary (command6, exact consumed end), which
the capture wrapper continues past. It is not an unidentified failed message.
Gates 25–27 remain open. No new APK is produced for this bounded source step.
