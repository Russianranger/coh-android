The actual scene39096463127 source-profile v2 refused at the exact original
`!entInUse(entity->owner)` atom. The independently retained public evidence is
under combined-client/diagnostics/continuation-f-20261017/owner-reason-scene-39096463127.
That atom combines a live-range check with ENTITY_IN_USE. It does not establish
that the actual entity was sleeping, or identify the later native timeout cause.

The original containerHandleEntity path creates a PLAYER, adds map ownership,
then assigns ENTITY_SLEEPING. CLIENT_CONNECT binds the entity and moves it into
the ACTIVE player list without changing its state. New ClientLink initialization
sets NOT_READY. CLIENT_REQSCENE checks the initialized Character and calls
worldSendUpdate before its ready reset. Only CLIENT_READY's resumeCharacter
wakes the entity to ENTITY_IN_USE. entFinishUpdate explicitly documents initial
self delivery while the player is sleeping. A rule requiring ENTITY_IN_USE alone
therefore excludes a source-defined legitimate fresh pre-entry owner.
The original allocator zero-initializes Entity before its initialization and
container load; ready and the outgoing transfer fields start clear.

The fresh-only specialization retains every old entInUse success unchanged.
Otherwise it requires the already source-bounded owner to be below entities_max,
exact ENTITY_SLEEPING (no free/unknown/mixed sleeping states), PLAYER type, map
owned, a nonnull Player pointer, client NOT_READY and entity ready0. It excludes
relay/demand loads, incoming transfer provenance and every outgoing/waiting
transfer flag or non-idle MapXferStep. This is a conservative subset for the
fresh disposable initial GROUPS call, not a generic sleeping-player admission or
an ALLENTS owner check. Original outgoing transfer drops map ownership before
sleeping; the extra phase/provenance guards also refuse that separate lifecycle.

Before the first type access it refuses output overlap with the complete
entinfo span. Existing private bounds precede the new helper, whose explicit
live bound precedes state/type indexing. Every other original table/backlink,
initialized Character, UDP/connection/incidence/alias predicate and final output
commit remains byte-exact under the existing47-atom diagnostic layer. The
original shared owner helper and accepted83 role remain unchanged. The fresh
stager replaces one atom and inserts one local read-only helper; it changes no
entity, client phase, request, READY or ACK. Fixed additional refusal names carry
no values, identities, pointers or paths. Probe schemas remain v2/36 and public
v2/43 keys; the13 extra enum names are source/PE-bound and grant no authority.

Run only the new focused qualification from a committed source freeze:

    python native-android/engine/scenecatalog-server/fresh_callback_observer/check_initial_owner.py --source-root ROOT --output NEW_PRIVATE_DIR

It executes the exact specialized gate, retained original prepare/entInUse/
Character functions and actual first-latch body using explicit host member-
subset storage. It compares unchanged active-path and sleeping-candidate output,
checks every new guard, live/private bounds, all non-active state bytes and client
phases, transfer stages, entinfo alias, representative later original guards,
rollback and first-cause retention. Six targeted mutations must fail. The small
pure probe parser checks the13 actual source-emitted names and refuses private
or type-unsafe values. Original lifecycle facts are exact source anchors and
ordering checks, not execution of complete lifecycle functions. Type accesses
use a checked host accessor with the same value/identity to expose unsafe access
ordering. No original Win32 layout, complete server, FolderCache/native/47-atom
suite, runtime transaction, actual sleeping state or leak qualification is
claimed. Address checks remain enabled; the host's existing /proc restriction
requires detect_leaks=0. A newly compiled and independently admitted Map PE is
required before another live attempt; no live result is minted by these tests.

LOCAL6 names, role, compile schema,19 retained artifacts and stage/record/admit
CLIs stay fixed. Only fresh API/emitter/stager compiled slots change. Probe.py
and focused qualifier/test/doc/source hashes require their own current closure.
Historical qualification receipts and PEs retain their exact older source pins.
