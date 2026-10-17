# Atomic initial-character prefix composition

`coh_character_initial_read` consumes exact original `sendCharacterToClient`
order from its first server flag through `sdPackDiff(SendCharacterToSelf)`,
stopping immediately before `sendTray`. It composes the separately qualified
account prefix, complete `character_Send` wire metadata, original primary and
secondary set names, ally/gang IDs, PvP flags/timer, and full absolute self stats.
It records exact original offsets and commits reader/output only after the last
required self-stat field validates. Later-field refusal rolls back account bytes,
character metadata and names together. No parser scans for a plausible offset.

The output is a raw prefix transaction, not a complete character/full update.
It does not validate selected DBID or entity generation, admit dictionaries,
apply account entitlements, or publish an actor/ACK. Unknown class/origin/power
and powerset names remain explicit unresolved raw references. A source-profile
digest is required by the existing child contract and is not a proven imported
dictionary. Tray/UI/account/global tails and exact message end remain required.
Account entitlement bytes are sensitive; do not log or export them by default.

Output is 450,384 bytes and workspace 900,072 bytes on the qualified 64-bit host.
Both belong in caller heap/arena. The 8 MiB aggregate cap charges entire input,
output, workspace, caller retained ownership and an 8 KiB stack reservation.
The child `character_data_read` charges its own output/workspace/input; the parent
passes every other named byte as retained ownership, avoiding double charges.
No allocation or input lifetime survives the synchronous read. Reader, profile,
output, workspace, failure and input spans must be pairwise disjoint. Alias and
span-overflow checks precede writes. Output/reader are unchanged on refusal;
workspace is private scratch and failure diagnostics may change after admission.

Original set-name receiver uses bounded strncpy; the native importer refuses a
wire name exceeding 127 bytes plus NUL rather than truncating it. Non-debug
absolute self-stat schema and existing shared-set profile constraints remain.
Unsupported source profiles refuse the entire composed prefix.

The checker executes the unchanged exact first-three-group sender statement
block, the whole original `character_Send`, source `SendCharacterToSelf` schema
and original struct/scalar producer functions. Original account and post-character
consumer blocks, complete `entReceiveAllyID`/`entReceivePvP`, and original self-stat
consumer execute with explicit fixture shells. It deliberately does NOT execute
whole `receiveCharacterFromServer` or `character_Receive`; its consumer traverses
the character extent recorded by the original producer. Independent native child
parsing must consume exactly that extent, and all staged metadata bytes agree
with the previously qualified standalone parser. This does not qualify original
dictionary lookup or gameplay creation. Fixture source and boundaries are pinned;
legacy original writer runs unsanitized at O0. New implementation/harness execute
independently under release, ASan and UBSan with stable before/after source hashes.

90 source fixtures span both alignments and starting offsets, all eight builds,
shared-set profiles, inspirations/boosts/inventory, absent content, signed raw IDs,
unknown identifiers and exact string limits. The two supported rich canonical
bodies exercise every truncation. Tests also mutate every post-character byte
and sampled preceding bytes, preserve trailing enclosing-message data, verify
budgets/aliases and run 1,000 random bodies. All three modes pass 123,914 checks,
18,579 truncations and 8,466 mutations. C++ linkage passes. Optional NDK arguments
build standalone ARM64/x86_64 harnesses; no app or Android execution is implied.
