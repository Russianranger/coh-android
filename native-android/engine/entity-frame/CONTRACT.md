# Supported full-update entity prelude

`coh_entity_frame_read` composes the existing qualified replication command/header,
entity list, non-debug control body and delete body in exact original order. It
stops immediately before receiveCharacterFromServer. This establishes the next
correct offset within supported profiles; it does not certify the character/global
suffix or outer command/transport boundary. The original global-debug consumer
has no wire reads outside its hasEntDebugInfo guard; debug=true is refused rather
than silently skipping that grammar. Full ALLENTS must have odd_send1 as the
original producer always does. Both existing normalized and legacy+5 command
profiles are explicit; UPDATE is unsupported by this full-reset entry point.

The caller supplies a bounded unique admission set of server indices, at most256.
Every admitted slot is initialized with original empty defaults for full-reset
semantics. No entity exists merely because its index is admitted. The source list
must create/read each record, reject unknown indices and preserve unique self
ownership. At least one live selected self must match the caller's DB-selected
DBID, original entity ID and server index; zero self and duplicate self fail.
Caller session/schema generations must match, but raw context numbers do not
perform authentication or establish source/dictionary identity by themselves.

Deletes stage against the same candidate table. Every referenced index needs an
admitted tombstone; unknown delete indices fail. Original packet ordering is
preserved: a create and delete in the same packet retain the entity. Selected
identity must still match after deletes and have source-decoded valid position.
The output retains this raw selected slot, control events, delete events and
immutable packet-backed cursor boundaries. None is a renderer-facing actor or
permission to apply control/prediction state. Missing dictionaries remain missing.
Caller must retain immutable packet bytes under its lifetime token while any
packet view is used; no copy/refcount or asynchronous ownership is created.

All explicit reader/context/schema/index/output/workspace/failure/input spans are
pairwise disjoint and overflow checked. Input, all declared objects,64KiB native
stack reserve and caller-retained storage count once within8MiB. Caller uses heap
or arena for the fixed workspace/output. No allocation, callback, gameplay or
network action occurs. Output and reader commit only after the entire prelude
passes; failure reports are diagnostic and workspace is discarded.

Qualification reuses unchanged original entity-create/position/orientation/delete
component producers and full original control producer/TEST_CLIENT consumer.
Synthetic list wrappers and original bit writers construct header/list/control/
delete joins at matching absolute offsets. Fixture wrappers add a prefix before
original components and invoke the control producer with full_state1. This is not
whole original sendEntity, entSendUpdate or entReceiveUpdate execution and not
an authentic capture. Entity and control fixtures have independent synthetic
owners; no cross-component position/physics-history coherence is claimed. Tests include selected DBID/entity matching, no/duplicate
self, descending and maximum source indices, both command profiles/alignments,
debug and full-odd refusal, unknown shortcuts, stage truncations, mutations,
late rollback, malformed schema, aliases and exact aggregate budget controls.

Authentic input gaps remain concrete: no captured live initial ALLENTS packet is
qualified here; actual selected-player records commonly require very-rare,
appearance/power customization/taskforce/buff bodies whose qualified standalone
parsers have not yet been composed into coh_ent_record. Unsupported branches and
non-instant interpolation/record_motion still refuse. The supplied index set is
a local admission policy, not a fabricated enumeration of a live map. Source
class/origin/power/appearance dictionaries, complete suffix dynamic ownership,
command framing, authenticated session identity and selected-actor publication
remain separate gates. No READY, RECEIVED_CHARACTER or full-update ACK is added.
