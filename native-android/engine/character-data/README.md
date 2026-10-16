# Bounded initial character wire metadata

This isolated module stages the complete **wire grammar of `character_Send`**.
It does not execute `character_CreatePartOne/Two`, resolve dictionaries, establish
selected-player ownership, complete the enclosing full update, send ACKs, or
publish a renderable actor. The existing entity statistics, appearance, gameplay,
physics and Combined modules are unchanged.

Exact source pairs are `MapServer/src/entity/character_net_server.c::character_Send`
and `Game/src/entity/character_net_client.c::character_Receive`. Nested powers,
boosts and inventories are in `Common/entity/character_net.c`. Source files can
be recovered from Git when absent from a sparse checkout; qualification verifies
all normalized LF hashes before extracting original functions.

## Required structural profile

The loaded power dictionary determines `g_numSharedPowersets` through
`powerdict_FindSharedPowersets`: it counts sets marked `bIsShared`. The value
starts at -1, is **not on the wire**, and controls how many records builds 1–7
omit. It cannot be guessed from packet length, numeric entity class indices or
an offline preview. An unbound value refuses decoding.

`CohCharacterWireProfile` supplies a nonzero generation, source/profile SHA256,
explicitly bound shared-set count, and whether the source owner is a player.
The caller must verify this identity against the authorized source/dictionary
generation before use. The parser checks required identity fields and uses the
count; it does not independently authenticate that receipt. Synthetic oracle
profiles are explicitly fixtures. No actual server dictionary was captured here.
Every output retains the profile and sets `dictionary_bindings_verified=0`.

The supported player profile additionally requires each build's declared total
set count to be at least the shared-prefix count. The unchanged producer can
emit smaller counts and simply skip that build's set loop; this decoder safely
refuses that layout. Original initialization/auto-issue behavior and the actual
loaded dictionaries must establish this stricter invariant before real-player
admission. Original-producer fixtures explicitly verify this refusal boundary.

## Preserved data and admission

- Exact class/origin names, level, combat-mod shift, current build and location.
- Player/nonplayer discriminator, eight build levels and exact ordered build
  indices, active build and matching final restoration index. Build 0 owns
  shared set records; later builds retain their original set indices and shared
  prefix count without duplicating resource objects.
- Set purchase levels and empty-set root CRCs; ordered power CRCs, levels, range,
  charges, usage/availability times, 32-bit creation time, enabled/manual-disabled
  flags, unique IDs, regular and global boost slots including empty slots.
- Boost CRCs, levels, combines, four float variables and up to ten reward
  powerup slots with exact type/ID/filled metadata.
- Inspiration grid up to 5×4; all 70 indexed boost inventory slots; the five
  generic inventories, capacities, transmitted indices, quantities, IDs,
  concept variables and auction capacity.

The original producer omits null powers from server arrays, a limitation noted
in its own source. The native data preserves **transmitted order and unique
IDs**; it cannot recover unsent server array holes or authorize tray references.
Class/origin names and all power/reward/inventory IDs remain unresolved references.
Missing dictionaries are not replaced by synthetic gameplay objects.
The initial header level/current-build and subsequent active-build/build-level
fields are preserved independently. The original consumer later switches builds
and levels while creating gameplay state; raw metadata is not that final state.

Native limits are aggregate 256 transmitted sets, 1,024 powers, 2,048 boost
records across regular/global/inventory slots, and 2,048 generic inventory items.
Counts and canonical build/slot/type order are checked before loops; all floats
must be finite. Unknown fixed inventory counts, changed 70-slot schema, malformed
flags, zero required base-power CRCs, unsupported bounds and inconsistent build
ordering fail closed. A maximum supported real character has not been measured;
these are admission ceilings, not a claim that every server character fits.

## Ownership and RAM

`coh_character_data_read` consumes an initialized non-debug `CohRepReader`, a
profile, caller-owned output and caller-owned scratch. No heap allocation,
dictionary lookup or gameplay callback occurs. The old output and candidate
scratch are each 449,688 bytes on the qualified 64-bit host. Their aggregate is
899,376 bytes, plus the full borrowed input span and caller-declared retained
memory. All are included in the supplied budget, which may not exceed 8 MiB.
This bounds the component's admitted ownership; the caller must include any
other concurrently retained application state in `retained_bytes`.
The cap covers named storage, excluding bounded C call-stack use and allocator
bookkeeping. It is not a measured process RSS or total application working set.

Allocate the large PODs in an arena, heap or static owner, not on the stack.
Reader, failure diagnostic, old output and candidate scratch must be mutually
disjoint and disjoint from input. Reader/failure must also be disjoint from the
profile. Alias refusal occurs before any writes, including diagnostics. Profile
metadata may reside within output/scratch; it is copied before scratch changes.
The input is borrowed only during the synchronous
call. Reader and old output commit together only after the complete supported
character block succeeds; scratch is unspecified on failure. The enclosing
entity transaction must still validate all later full-update fields, ownership
and matching dictionary/resource generations before any actor publication.
Rollback discards the candidate. Run preparation off the rendering thread.

## Qualification scope

```sh
python3 native-android/engine/character-data/check.py --source-root . \
  --sanitize --output /tmp/character-data.json \
  --fixtures-output /tmp/character-data-fixtures/fixtures.h
```

The oracle executes unchanged **whole `character_Send` and every nested wire
producer**. Its explicit owner/earray/clock/dictionary fixtures are synthetic.
The original `basepower_Receive`, inspiration, boost and inventory consumers
independently decode produced tail components and their stored fields are
compared with native output. Full gameplay `character_Receive` and its power
construction consumer are **not executed or claimed qualified**. The native
power metadata is checked against deterministic producer fixture inputs.

The 30 whole-producer fixtures include 25 supported nonplayer/eight-build cases
and five source-produced shared-prefix profile refusals. Supported cases cover
shared-set counts 0/1/2, empty sets, omitted null powers, regular/global boosts,
ten powerup slots, populated/empty inventory and inspirations, both scalar modes,
and ordinary bit offsets 0/1/7 and aligned offsets 0/8. Native tests cover every
byte-spaced truncation and final-bit truncation, mutations, aggregate limits,
invalid profiles, nonfinite values, wrong types/indices/counts, RAM and alias
admission, exact byte rollback, and 2,000 deterministic random malformed inputs.
Original x86-oriented writing/reading runs only on trusted padded fixtures at
`-O0`; ASan/UBSan qualify new native code and tests, not historical aliasing code.

Optional `--ndk PATH --android-output DIR` writes `fixtures.h` and standalone
ARM64/x86_64 `coh_character_data_test` executables with per-ABI build receipts.
Those receipts explicitly say `executed:false`; emulator execution, actual Thor
acceptance and real server interoperability require separate evidence. The
isolated CMake target `coh_native_character_data` can receive generated fixtures
through `COH_CHARACTER_DATA_FIXTURE_DIR`. Shared CI, JNI and final integration
remain coordinator-owned. No accepted APK is rebuilt by this work.

The retained `qualification/20261016/host.json` records 232,005 checks in each
release/ASan/UBSan run, exact original function/file hashes, native input hashes,
fixture identity and worker source base. It records implementation and host/source
qualification only. No local NDK, emulator, physical device or authentic server
execution was available for this checkpoint. Removing the isolated module is
the rollback; no application or server runtime was activated.
