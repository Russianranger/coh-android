# Consecutive rare entity wire events

`coh_ent_rare_prefix` stages the consecutive source fields after selected-self
architect/taskforce data and immediately before `entReceiveOtherSupergroupInfo`.
It consumes odd-send, ally/gang, ignore-combat and offset level, player
classification, PvP, collision/selectability/drawing/map/contact flags, con/wall
flags, optional entity name, complete pet metadata and AFK. It is not a complete
very-rare tail, entity record, actor snapshot or ALLENTS transaction.

The reader and output commit together after the entire prefix succeeds. On an
error both retain their exact prior bytes; optional failure diagnostics may
change. Objects must not alias and must have one owner thread. The parser makes
no allocations, retains no packet pointers and performs no game callbacks. Its
1,456-byte output and equally bounded local candidate are not embedded in every
entity slot. A prior output, candidate destination and local staging value use
4,368 bytes on the current 64-bit ABI, plus the reader/failure scalars and borrowed
packet. The transaction owner must include retained events and the input span in
its aggregate session budget. The output's `end_bit` is this component boundary,
not permission to acknowledge a full update.

All presence flags are retained. Optional absence is not equated to clearing
previous state. Pet owner/creator indices and the optional power CRC remain
unresolved references. An owner must be in 1–10,239; creator zero is allowed.
Name (128), source receiver's pet power display buffer (1,000), and AFK (48)
capacities include the terminator. The pet-name capacity of 128 is a native
admission policy; the original pet-name storage is dynamic. Oversized strings
fail rather than reproducing unsafe copies/truncation. Byte-aligned scalar bits
outside each source logical width and an ignore-combat value above one fail
closed. `combat_shift_wire` preserves the unsigned source word; `combat_shift`
subtracts eight modulo 2^32 and explicitly interprets the signed result without
implementation-defined narrowing. Other packed IDs/timers/state retain raw words.

## Source qualification

Original import: `0b75ade0c801735e10c5798f641948a45cc50488`.
The existing `source-pins.json` binds full original files. `check.py` additionally
records the exact LF hashes of the producer/consumer inline blocks and each
component consumer.

The oracle executes the unchanged consecutive inline statements from original
`MapServer/src/entity/entsend.c::sendEntity` and
`Game/src/entity/entrecv.c::entReceive`. It also executes complete unchanged
`entSendPetInfo`, `entSendAfk`, `basepower_Send`, `basepower_Receive`, and the
12 named component consumers through AFK. This is **not execution of complete
sendEntity or entReceive**. Synthetic owner storage, one known power CRC lookup,
packet scalar/string adapters and inert UI callback shells are explicit. Unknown
power lookup diagnostics abort instead of silently passing or sending traffic.
No class/power dictionary authenticity or gameplay UI behavior is established.

There are 72 producer fixtures over all bit offsets and byte-aligned mode. Native
raw events are compared with the synthetic producer's input metadata; 288
independently executed original consumer runs additionally assert exact cursor
end and applicable state fields across fresh/stale and self/nonself contexts.
This distinction matters: native raw events are not the original applied state.
Cases cover absent/non-player metadata, optional empty strings, maximum admitted
strings, absent pet creator/power/name/display, AFK retain/replace, negative and
large combat shifts and packed signed words. Adversarial fixtures use the original
scalar writers only and are labelled separately; they are not complete producer
runs. Every truncation, deterministic byte mutations, malformed presence/width,
missing/oversized owner and oversized string cases preserve rollback. Another
5,000 randomized buffers cover this API in the release/ASan/UBSan suites.

## Application remains deliberately separate

The original component consumers contain rules a future transaction owner must
qualify before applying these events:

- Collision/no-draw for the selected player use control state. Map/contact/name
  updates also exclude the local player in these consumers.
- Selectability is cleared for players and even for stale packets; pet names
  update even on stale packets. A non-pet event clears prior pet metadata without
  a stale check. These are observed source behaviors, not native apply logic.
- Empty/absent entity and pet names retain prior names. Missing pet power retains
  the prior power; missing/empty display clears it on fresh pet updates.
- AFK false changes the flag but retains its message. AFK true without a message
  retains the previous message. Player storage must exist before message apply.
- Owner/creator references require current entity generations; raw indices cannot
  establish identity. Optional creator zero does not independently clear an old
  resolved creator in the original update consumer.

No source packet ID, entity generation or selected DBID is accepted by this raw
API. It cannot decide stale ordering, emit ACKs or certify actor ownership. The
future complete record owner must validate all later supergroup, leveling-pact,
logout and teammate-buff data, retained costume/power dictionaries and all global
full-update tails before committing any state or producing READY/RECEIVED_CHARACTER.

Remove the additive API and tests to roll back this component. Existing record
admission and accepted APKs are unchanged. Host/source qualification is separate
from Android build/execution, physical Thor acceptance and real server capture;
none of the latter is claimed by this standalone receipt.
