This additive provider executes whole unchanged original `entSendCharacterStats`,
`ParserSendEmptyDiff`, `entSendSeqMoveUpdate`, `entSendRagdollUpdate` and
`character_SendStatusEffects` with the already pinned original bitstream and
struct-schema functions. `leaf_oracle.build(root, work)` returns a ctypes library
and source proof. `original_record_leaf(kind, scenario, aligned, prefix, out,
&bits, &begin, &end)` emits the whole wire including seed prefix. Output storage
is 65,536 bytes; kinds 1..4 and scenarios 0..3, unaligned prefixes 0..7 or aligned
prefix 0 only. This is a trusted host fixture, with assertions as fixture guards.

Kind 1 is selected-self basic stats. Scenario 0 is initial full nonzero stats;
1 is usual no-body update, 2 has no character, 3 is full all-zero stats. The
initial full update sends the complete `SendBasicCharacter` schema despite the
source comment describing a one-bit empty diff. The unchanged original
`ParserSendEmptyDiff` passes force-all-fields to `ParserSend`. Full bodies are
also consumed by the unchanged original schema receiver; scenario 0 equals the
existing complete schema producer exactly at every tested bit offset.

Kind 2 executes the original non-RAGDOLL build branch. Kind 3 is prepared
sequence state with no stance, optional move/tick fields and source-defined
sticky-state constants. A stance lookup is an assertion-refused fixture branch.
Kind 4 executes original status bit predicates, auto fields and designer strings.
Class lookup, array size and attribute storage are explicit fixture interfaces;
they do not establish real dictionary or gameplay identity. Status/sequence wire
projections are independently compared, not original consumer qualification.

The checker freezes helper, included native-header and original-source bytes
before imports and checks them after execution; original additional function,
constant and full-file LF hashes have a separate fixed manifest. It executes
144 cases with 630 explicit controls. The historical trusted host producer is
not sanitizer qualified. There is no whole engine, Win32 ABI, original outer
transaction, live packet, dictionary, actor or ACK admission from this helper.
The existing frozen outer-order provider is unchanged; combining these actual
leaf bodies with it remains a separate source-qualified composition step.
