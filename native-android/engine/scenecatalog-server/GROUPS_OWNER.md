# Original producer owner association preparation

`source_groups_owner.inc` is a new disabled private helper; it installs no hook,
callback, sink or server role. A future qualified original MapServer caller can
invoke it immediately before actual worldSendUpdate/eligibility observation on
that same exclusive client/entity/link owner thread. It derives identity from
actual source objects, accepting no replacement DBID, generation or session hash.

The actual request path is `svrHandleClientMsg`: ClientLink comes from the actual
link's userData; CLIENT_REQSCENE checks registered membership and an initialized
character before `worldSendUpdate(client->link,1)`, then resets ready state.
`clientSetEntity` sets both client.entity and entity.client. `entAllocCommon`
assigns entity.owner as the actual entities[] index; `entInUse` checks its active
range/state. These whole producer/type source files and exact functions are
pinned. The helper checks exact registered-link and client incidence, reciprocal
link/client/entity pointers, source-active entity-table incidence and initialized
Character parent. It observes client.entity, never a viewed/slave target. It does not attest the
entity type as PLAYER or the presence of a Player subobject.

The initial private capture policy is deliberately stricter than the generic
worldSendUpdate surface: one actual registered occurrence, clean connected UDP,
no pending/connecting/dead/removed state, bounded supported version, valid entity
DBID/entityID/serverindex and exact Character parent. It does not normalize source
protocol flags or claim every original call necessarily satisfies this policy.
Registered links are capped65536; entity storage uses original10240 cap/range.
The observer allocates nothing, does not yield/load, and commits output only after
all checks. Known output/source/table aliases refuse. All other engine storage
and opaque class objects remain caller-disjoint; original objects/tables must be
valid and stable before traversal. Source pointer validity is an engine/caller
precondition, not a parser accepting arbitrary pointers.

The fixed192-byte little-endian record has magicCOHOWN01 followed by46U32 words:
version/recordsize; DBID/entityID/serverindex; client/entity ready; NetLink UID,
connection_id/connect_id/protocol/type/operation; link count/slot; connected,
pending,connecting,disconnected,destroyed,removed; compression allowed/default,
ordered allowed/default,separate-controls,cookie-send/echo FLAGS (never cookies);
pre-update link time/worldID,current worldID,last processed/received/ordered IDs;
lastsent/acked fullupdate IDs; entity map/static-map IDs; observed initialized and
parent-owned flags; source-only1; source-generation/crypto/native-decode/world0;
actual nonsecret auth UID. Every pointer stays private. IDs/generations/slots are
local observations, never durable pointer-derived tokens or global session IDs.

A successful source record is only producer-side owner association. The future
caller still needs actual same-boundary catalog/root/future/resource equality,
quiescence lease, exact eligibility+logical packet and actual native receive
record with independently bound run/source/session provenance. It does not prove
that a worldSendUpdate executed, a packet reached Android, the native selected
entity was decoded, or authentication/actor/world admission succeeded. No old
detached hashes or historic Thor counters are reused as generation proof here.

The host oracle executes unchanged clientSetEntity, applyNetworkVersionToLink,
character_IsInitialized and entInUse, plus exact unchanged CLIENT_REQSCENE guard
and membership slices. Original ClientLink/Array/enums are copied unchanged;
Entity/Character/NetLink use explicit source-checked member-subset HOST storage.
External position/log/flush services are observation-only fixture callbacks.
Tests cover constructor backrefs/NOCOLL/log callbacks, protocol versions0..5,
ready states, original assertion guards, maximum link scan, malformed ownership,
late failure/output rollback, alias refusal and source inputs unchanged. This is
not Win32 ABI/layout or complete MapServer execution qualification. No existing
eligibility/transaction hook, workflow, service or accepted client is changed.

The qualifier freezes every local dependency before executing its original-source
extraction helper, executes the admitted helper bytes, and verifies the complete
closure before and after helper execution and at completion. Five owned temporary
file controls exercise unchanged execution and pre-execution, during-execution
and final source mutation refusal. Existing historical receipts remain unchanged.
