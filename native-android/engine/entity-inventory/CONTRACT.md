# Original inventory, invention and workshop staging

This module stages the original post-badge ALLENTS subtransaction in source order:
`entity_SendInvUpdate` → `entity_SendInventionUpdate` → workshop string. It stops
before the team-up-to-date flag. It does not consume a network packet boundary.
The later team, supergroup, league, global state and command framing still need
composition and validation before any initial-update completion acknowledgment.

`coh_inventory_update_read` reads all original generic inventory item fields and
the optional auction wrapper string. Ordered duplicates, unknown raw types and
identifiers remain raw. Concept type 1 has four finite IEEE32 variable words;
other types follow the source default ID-only branch. Auction serialization text
is preserved as opaque input; no auction parser, item dictionary, trading state
or gameplay operation is executed. Local admission limits are 2048 items and
256 KiB including the auction string terminator. Oversized input is refused.

`coh_invention_update_read` independently decodes the complete producer-defined
invention body: status, state, recipe, boost index, four variables, ten powerup
slots and ten concept slots. Each slot admits up to 64 concepts, total 640.
Unknown numeric states and identifiers are retained. These limits are local
resource admission bounds, not claims about source dictionary limits.

There is a concrete original-source incompatibility: `invention_Send` emits
state and possibly the remaining invention body when status changes, while
`invention_Receive` has its entire body commented out. The standalone diagnostic
stager marks `original_consumer_compatible` only for status zero. The atomic
`coh_inventory_phase_read` returns `COH_UNSUPPORTED` for every nonzero status,
including state zero, with the caller's reader and output unchanged. It never
treats the original empty consumer as evidence of an empty producer body.

Powerup reward IDs retain the original producer's char-narrowed transmitted
word. Host source fixtures demonstrate signed-char behavior for IDs 127, 128
and 300; this is explicitly not Win32 ABI qualification or dictionary authority.
Workshop text admits at most 31 bytes plus NUL, a stricter explicit local bound
than the original `strncpy(..., 32)` consumer. Refused text is never truncated.

All outputs and workspaces are caller-owned POD storage; use a heap or bounded
arena. Input, reader, output and workspace spans must be pairwise disjoint.
All decoders validate their complete subtransaction before committing output
and reader. Workspace is scratch on either outcome. The phase budget charges
input, output, all child workspaces, an 8192-byte conservative stack reserve
and caller-retained bytes exactly once within an 8 MiB ceiling. Sequential
children consume the same immutable input span and do not retain pointers.

The source oracle providers in `diagnostics/allents-tail-20261017` execute the
whole unchanged inventory producer/consumer and active invention producer,
validator and no-op consumer, using explicit synthetic fixture storage and
auction serialization/parser callbacks. The workshop oracle executes the exact
original sender/consumer statements and original bitstream functions, not the
whole enclosing ALLENTS functions. Those qualification scopes remain distinct.
`check.py` pins original source, provider files, native inputs and fixture bytes;
it checks field projections, source cursor boundaries, trailing unread data,
all selected fixture truncations, byte mutations, random input, admission and
atomic rollback, aggregate budgets, alias refusal, C++ linkage and emitted
stack usage. Release, ASan and UBSan execute the same checks. Original source
oracles themselves run unsanitized with their historical fixture shells.

Implemented: host raw staging and source qualification only. Android build and
execution are separately recorded when performed. No live server transaction,
Android app execution, authoritative actor, dictionary admission or ACK is
qualified by these host tests.
