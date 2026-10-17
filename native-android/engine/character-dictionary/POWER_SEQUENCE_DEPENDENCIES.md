# Whole initial power sequence dependencies

This is a read-only source review and design handoff, not a new receiver or
qualification of a whole character. It extends the dependency analysis after
`coh_initial_power_slots_create` source `0df0504c2ea75d89f4a983a569a17733707f775e`.
Its historical constructor receipt remains unchanged. No previous qualifier was
rerun. Current dictionary generation, complete initial character, actor
publication and every application ACK remain refused.

`qualification/power-sequence-source-review-20261017.json` records exact byte
hashes for seven original files and LF-normalized hashes for 24 complete function
bodies. Its SHA256 is
`3f45c231c91bca276bb9ee83b66ef5567dce91079571f89d2c72b71ddde4c950`.
The CLIENT `character_SelectBuildLightweight` definition is selected explicitly;
the preceding SERVER definition must not be substituted. Source paths below are
relative to `upstream/ouroboros/`.

## Required source order and identity

1. `Game/src/entity/character_net_client.c::character_Receive` resolves actual
   class/origin pointers, calls CreatePartOne, stores outer level/build fields,
   receives powers, inspirations, boost inventory and inventories, then calls
   CreatePartTwo. Whole ReceivePowers is one phase, not a complete actor.
2. `Common/entity/character_net.c::character_ReceivePowers` destroys the received
   sets, resets their arrays, and reverse-grants new empty shared set objects
   into build 0. Builds 1..7 copy those SAME set object identities in source order.
   CLIENT BuyPowerSet excludes the SERVER-only free-power grant branch. Initial
   reuse therefore arises within the new received sequence; a caller-supplied
   previous Power is unnecessary and cannot establish this phase's state.
3. For a player, ReceivePowers explicitly assigns `iLevel=iBuildLevels[0]` once.
   CLIENT SelectBuildLightweight swaps current build and set arrays, but does
   not change iLevel. Purchased-slot arithmetic and LevelFinalize use build 0's
   level throughout all builds. Regular ReceivePowerBoost temporarily assigns
   the current build's level for slot requires and restores the saved level.
4. `character_OwnsPowerSet` searches owned set objects in reverse by BasePowerSet
   pointer identity. `character_OwnsPower` searches matching sets and their
   powers in reverse by `ppowOriginal` pointer identity. Repeated shared base-set
   references can make BuyPowerSet choose a later set while OwnsPower finds an
   earlier set's Power. Neither wire group ordinal nor a deduplicated base-set
   table represents these owned identities.
5. The temporary branch tests the chosen owned set's reverse parent category
   name against `Temporary_Powers` case-insensitively. It does not use a later
   last-write gameplay category ID. Temporary powers always create another
   instance; regular powers reuse the existing instance and preserve its UID,
   ignoring the later wire UID, including zero or a colliding value.
6. New `power_SetUniqueID` uses an integer-key registry. A zero or colliding new
   UID enters the assertion/random fallback. Signed int bit patterns are valid
   source keys; a positive-only native clamp is not source semantics. A future
   owner must own the source random branch or refuse that whole candidate.
7. Every received record overwrites set level and all transmitted power scalar
   fields before LevelFinalize. Reused LevelFinalize only grows ppBoosts; it
   does not shrink when a later record has fewer boosts. Slots beyond that later
   wire count can retain Boost objects. Each transmitted regular slot is first
   destroyed and then independently received, including the absent case.
8. Every old global Boost is cleared before the record's global receive loop.
   The present branch constructs a Boost then eaInsert at the WIRE index.
   `libs/UtilitiesLib/src/components/earray.c::eaInsertDbg` rejects an index above
   current count. An absent earlier global entry can therefore cause a later
   present Boost to be constructed but not inserted. Do not fabricate holes or
   skip resolving/constructing discarded entries. A native cleanup of source
   orphan allocations must be explicit while preserving resulting state.
9. Regular `power_ReplaceBoost` constructs a complete Boost, evaluates its slot
   requires against evolving Entity/Power/Boost state, and can destroy/refuse
   that Boost. `power_sloteval_Eval` uses character evaluation functions plus
   the PowerBoostsSlotted special function. The cache expressions exist, but
   native evaluation and its owned semantic Entity state remain code gaps.
10. Every present Boost includes level, combines, all vars and typed powerup
    reward slots. Nonzero reward IDs need current salvage, proficiency and
    recipe/detail-recipe owners. `RewardItemType.c::rewarditemtype_NameFromId`
    returns NULL for ID 0 before its type switch. Donor Salvage.bin,
    Proficiencies.bin, ProficiencyIds.bin and baserecipes.bin are available;
    native typed import/ID joins and generation ownership are not implemented.
11. Stance clearing, enabled/manual-disabled flags, ranges, charges, usage and
    available times, creation times, set-level overwrites, final selected build
    and active build must all be owned. The final packet active build can differ
    from the initial build label; final CLIENT iLevel still retains build 0.
    CreatePartTwo later auto-issues more powers after the inventories. These
    required effects cannot be silently omitted from whole-character claims.

The relevant exact functions include ReceivePowerBoost, CreatePartOne/Two,
AddNewPowerSet, OwnsPowerSet/OwnsPower, BuyPowerSet, GrantAutoIssueBuildSharedPowerSets,
CLIENT SelectBuildLightweight, powerset_Create/AddNewPower, power_SetUniqueID,
power_Create/LevelFinalize/AddBoostSlot/BoostCheckRequires/ReplaceBoost/DestroyBoost,
power_sloteval_Eval, boost_Create, rewarditemtype_NameFromId and eaInsertDbg.

## Future complete phase owner; no implementation yet

The smallest meaningful next implementation is one atomic source-ordered
ReceivePowers sequence owner, provisionally `coh_character_power_sequence.*`.
A stand-alone reuse predicate or caller-populated previous-instance structure
would leave these identity, order and Boost-object requirements unresolved and
is not planned.

Its input should be existing fully parsed `CohCharacterData`, the SAME finalized
IDs/join/shared layout/stream provider and schedules leases, and actual typed
reward/evaluation owners when the packet requires them. It must not duplicate
the qualified full packet parser or accept caller-count authority. Candidate
output needs copied build-to-set-instance references, set and Power instances,
a UID registry, every received scalar, sparse occupied regular/global Boost
objects and an event-to-instance map. Per-Power vector lengths plus sparse
occupied slots avoid a 1024 by 4096 dense table.

Proposed bounds derived from existing raw parser caps are 1024 Power instances,
1536 set instances (at most 256 shared +1024 per-Power buys +256 empty groups),
3328 build/set references (8*256 shared +1024 +256), and 2048 Boost records.
Target candidate owner and workspace each at most 640 KiB plus one 65,536 B selected
record workspace; these are design targets, not an admitted ABI. A literal 8 MiB
aggregate and 64 MiB work cap would have to charge all simultaneously live
owners/provider contexts/retained allocation/stack before callbacks and refuse
on capacity, I/O, mutation, cancellation, unresolved identity or unsafe integer
arithmetic. Reads remain at most 4096 B and complete selected records are walked.
The entire old output remains intact until final cancellation and commit.

Current native sizes measured during this review for categories, compact sets,
stream, join, IDs, shared layout, schedules, retained set input and raw character
are respectively 374,856; 196,704; 1,048,744; 524,344; 689,184; 32,792; 16,496;
3,179,276; 449,688 bytes: 6,512,084 bytes total (6.21 MiB). This is a lower bound
for those owners, not a total process-RSS or final aggregate proof. ABI/layout,
actual packet bytes, new candidate/workspace, evaluator and reward owners still
need exact accounting.

## Hard inputs before implementation or actor publication

No authentic complete initial-character/ALLENTS packet has yet been observed
by this owner. Required evidence is its complete owned payload, exact logical
bit length and byte-alignment/legacy profile, selected DB identity and actual
session/lease generation, plus the actual loaded current dictionary family and
shared-list loader branch/generation. Historical GROUPS packets, retained cache
bytes and scalar constructor qualification do not provide that evidence.

The future phase refuses unknown CRCs/parents/categories, cross-dictionary or
retired leases, missing Boost requires/reward dependencies, new UID random
branches without their source owner, or any resource/transaction failure. It
cannot skip actual Boost objects or remaining ReceivePowers fields. An authentic
packet can establish which branches are exercised and make the complete phase
scope reviewable; it cannot grant current dictionary or actor authority itself.
The next possible receive-only evidence path is analyzed separately in
`INITIAL_CHARACTER_CAPTURE_DEPENDENCIES.md`.
