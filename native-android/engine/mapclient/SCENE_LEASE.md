# Actual-current scene receive loan

The optional scene observer still executes only after complete normal GROUPS
inspection, synchronously before the exact decoded network message is released.
Default service behavior, SCENE_INCOMPLETE and outgoing command policy are
unchanged. The callback may call only the new `coh_map_client_scene_lease` getter;
all other client reentry is forbidden, and owner access remains serialized.

The getter requires the exact currently active callback event address on the
actual opaque CohMapClient. A copied event, another client, and calls outside the
callback refuse without modifying output. It verifies the reader's actual decoded
allocation pointer/extent, bits, post-command cursor, alignment and byte ceiling
against the original retained reader and actual CohNetOwnedMessage. Output cannot
overlap the client, event, actual network descriptor or decoded allocation.

The returned value derives message ID, ordered ID/order, decoded-loan generation,
connection ID, transport profile and map/selection metadata from that actual
client and loan. It never accepts replacement identity labels. Its reader bytes
remain borrowed only through callback return; a durable evidence recorder must
copy and hash them under its own explicit budget before returning. Numeric
connection/map/message generations are local correlation observations and can
repeat on other owners/recreated transports; they are not durable session tokens.
No owning reference to the client or network allocation escapes this API.

The legacy `coh_map_client_begin` accepts a raw authorization DTO. Consequently a
positive selected DBID here is still NOT proof that this client consumed an
actual opaque DBSession handoff. `selected_dbid_owner_bound` remains0. An actual
DBSession→MapClient begin seam must derive that handoff inside the owner boundary
before this can change. Authentication/source-generation/actor/world admission
and application ACK remain separate prerequisites; no live authority is added.

Host controls use twelve minimal original-layout packet profiles and four large
fragmented/compressed scripted UDP scenarios (139794 decoded bytes). They compare
the exact reader and actual known message/connection/order/profile metadata,
reject copied/wrong-owner/expired observations and known output aliases, preserve
no-early-callback behavior for malformed bodies, and retain zero owned-loan bytes
when service returns. These are actual OS UDP tests with synthetic source-derived
peers, never a real MapServer capture or Thor acceptance. A separate wrapper
freezes executed helper implementations, transitive headers and original pins
before and after the release/ASan/UBSan run. Android execution remains unqualified.
