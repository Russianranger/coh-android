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

The second milestone composes `coh_initial_netfx_probe` at `ai_end_bit`. It
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

`check_initial_aianim_probe.py --sanitize --output NEW.json` executes the
unchanged original AI producer on explicit source fixture shells and verifies
raw string boundaries, optional fields and rounded Booleans. Its generated JNI
fixture verifies the retained triggered-prefix header/source receipt, appends
the original AI leaf and an opaque NetFX witness. Release/ASan/UBSan each pass
1,083,959 checks across89 fixtures,162,778 shortened extents and20,752 mutations.

`check_initial_netfx_probe.py --sanitize --output NEW.json` executes only the
unchanged original NetFX producer/consumer entrypoints:6 comparisons, including
full-send, nonforce and empty lists in packed and compressed modes. Its JNI
fixture verifies the retained AI prefix, appends explicit two-flag framing,
original full-send3-effect output and an opaque costume witness. The enclosing
`sendEntity` framing is source-qualified; the complete original producer
transaction is not executed. Release/ASan/UBSan each pass103,857 checks across
95 fixtures,14,806 bit truncations and2,156 mutations.

The affected JNI adapter uses explicit controller/JNI doubles for same-loan
composition, both newly added projections/refusals, fixed report capacity and
cleanup. Receipts and reproducible source hashes are in
`qualification/initial-aianim-20261019/` and `initial-netfx-20261019/`; focused CI
is `Native initial ALLENTS AI and NetFX probes`. Accepted earlier-stage suites
and general renderer/compiler/network/Android13 qualification are not repeated.
No new original-server transaction, physical packet body or Thor run is claimed.
Exactly two milestones finish here; costume is the next session's boundary.

The previously reported unsupported Map count is the ordinary successful GROUPS
inspector's deliberate UNSUPPORTED boundary (command6, exact consumed end), which
the capture wrapper continues past. It is not an unidentified failed message.
Gates 25–27 remain open. No new APK is produced for this bounded source step.
