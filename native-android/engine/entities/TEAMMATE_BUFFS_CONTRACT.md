# Bounded teammate-buff wire staging

`coh_ent_teammate_buffs` consumes the complete original `appendTeammatePacket`
wire body after the very-rare entity suffix. It includes the teammate and buffs
presence bits, `character_SendBuffs`, and `basepower_Send`. It stages full and
difference records in original reverse-send order, deletions, null/unknown power
CRCs, blink/timer flags, raw UID words, modifier presence and every raw signed
magnitude/attribute-hash word. Missing modifier data means retain previous data;
no inferred empty replacement is applied.

This function is standalone wire staging. The caller must establish the offset
from the entire preceding entity grammar. Success neither completes an entity
nor proves dictionary authority, selected DBID, stale/prior-state application,
full ALLENTS/UPDATE acceptance, immutable actor publication or an ACK. There is
no code change to production entities, renderer, JNI or accepted applications.

Limits are local refusal bounds: 256 buffs, 64 modifiers per buff and 2,048 total
modifiers. They are not advertised original maxima. Output and workspace are
24,616 bytes each on the qualified host; both belong in caller heap or arena.
The 4 MiB aggregate cap charges input, both complete PODs, a 4 KiB stack reserve
and declared retained enclosing ownership. No dynamic allocation or retained
input occurs inside the parser. Input/reader/output/workspace spans must be
disjoint; overflow and aliases refuse before writing. Refusal leaves output and
reader byte-for-byte unchanged, including late truncation and exhausted budgets.

`check_teammate_buffs.py --sanitize --output NEW.json` extracts six complete
original functions unchanged and verifies full source hashes. Original
BuffSettings enum is extracted from pinned `Common/comm_game.h`. Synthetic entity,
stash, dictionary and UI shells are explicitly limited to fixture behavior.
They are not original dictionary or game-state qualification. Legacy bit packing
runs unsanitized at O0; native implementation runs separately in release, ASan
and UBSan. Source bytes/revision are verified before and after. C++ linkage and
production stack usage are checked; optional NDK flags build standalone ABIs.

280 fixtures cover both alignment profiles, starting bit offsets, no teammate,
no update, no character, no-send/no-numbers for self/pet/team, full/diff/delete,
unknown and null powers, cached modifiers, absent timers, zero and maximum UID,
signed words, reordered diffs and every local count boundary. Complete source
consumer observations are compared through an explicit fixture-only projection
for both current and stale packets. That projection tests raw-event sufficiency
for those observations; it does not implement the original application state.
Each supported fixture also checks unread later-message bytes. Native tests
exercise all cuts of rich canonical fixtures, every byte mutation of supported
fixtures, budget/alias refusal and 10,000 deterministic random inputs.

The checker reports actual counts, never assumes mutated data must be invalid.
On a mutation that remains valid, it checks bounded output/cursor invariants;
on refusal, reader/output rollback is required. No Android or physical execution,
whole producer, live network acceptance or authoritative actor is implied.
