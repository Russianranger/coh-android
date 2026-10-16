# Power customization wire staging

`coh_ent_power_custom` consumes the complete pinned non-debug
`entReceivePowerCust` wire envelope. It stages raw customization events; it does
not resolve base powers, certify character ownership or compose an entity/full
update. No acknowledgment or actor-publication API is enabled.

Original source boundaries are `Common/entity/power_customization.c`:
`powerCustList_send`, `powerCustList_receive`, `comparePowerCustomizations`;
`MapServer/src/entity/entsend.c`: `entSendPowerCust`; and
`Game/src/entity/entrecv.c`: `entReceivePowerCust`. The source import and hashes
are bound by `source-pins.json` and the qualification receipt.

The envelope supports no change, full self/other-player metadata, single or
multiple self lists, and the owned-list variant. A full other-player envelope
contains only its false self flag. Self flag must match the caller's already
verified entity ownership. Current/list indices are bounded by source
`MAX_COSTUMES=10`. The wire additional-slot field retains its eight-bit value;
it is not a total-slot count. Original `costume_get_num_slots` is executed by the
oracle, including product entitlements, to verify that distinction.

Each list has a presence bit, auto-sized item count and repeated auto-sized
power full-name CRC, primary color, secondary color and raw token string. The
result preserves wire order and duplicate CRCs. It records contiguous ranges in
one fixed array, so no per-list allocation or name search occurs. Missing-list
presence means retain prior data; present with zero items means replace with an
empty list. Those are future transaction semantics, not side effects of parsing.

An explicit admission limit allows 512 items per list, 4,096 across an envelope
and 259 non-NUL bytes per token. Unknown envelope types, incompatible self flag,
out-of-range slots, excessive per-list/aggregate counts and incomplete or long
tokens reject the entire envelope. No prefix or previous list publishes on a
late failure. Reader/output remain unchanged; workspace may contain partial
unpublishable data. The parser always validates owned-list bodies, including
before a future stale-event discard; it does not copy the historical owned
consumer's stale-body skip.

Power IDs remain unresolved unsigned wire CRCs, including IDs absent from the
eventual dictionary. The original consumer can assign an unresolved power to
`none` and sorts the list; staging must not treat that fallback as successful
asset resolution. A complete transaction owner must bind the actual source
power dictionary, session/packet/entity and resource generations, resolve every
required reference, and apply the chosen original order/duplicate semantics
before publishing actor or effect state. No synthetic dictionary establishes
real server compatibility. Raw customization colors/tokens do not substitute
for full character powers, builds, inventory or attribute replication.

On the qualified 64-bit ABI the envelope and workspace are each 1,114,392 bytes.
Both belong off the thread stack. The wire parser allocates nothing and retains
no input pointers. Old output + new output + scratch require up to 3,343,176
bytes in addition to appearance dictionaries/envelopes, entity table/scratch,
packet storage, graph and render resources. Do not embed this large envelope in
every entity slot. A future complete transaction must bound aggregate retained
events and account for all other owners. Larger wire fixtures use an explicitly
bounded standalone reader; this does not expand the accepted session dispatch's
ordinary packet admission policy.

The oracle executes the unchanged original producer/consumer functions,
auto-sized packet functions, sort comparator and slot-count function. Explicit
adapters implement synthetic power dictionary lookup, earray allocation,
StructCopy storage and account products. Observers record only original lookup
arguments, list destinations and ending cursors. Expected colors/tokens come
from original consumed lists, matched back to known unique fixture tokens;
native parsing itself is never used to construct expectations. Cases cover
reordered dictionary IDs, a missing synthetic dictionary ID, duplicate IDs,
maximum ten slots via product entitlements, absent versus present-empty lists,
self/other/owned and no-change envelopes. This does not qualify actual power
dictionary data or runtime customization application.

See `qualification/power-custom-20261016/` for host release/ASan/UBSan results,
exact hashes and malformed/rollback evidence. Android build/emulator, physical
Thor and authentic server interoperability require independent receipts. The
accepted APKs, source gameplay modules, profiles and saved characters are
unchanged. Reverting this additive entities-only change restores the prior API.
