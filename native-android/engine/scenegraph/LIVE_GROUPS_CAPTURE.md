# Exact live GROUPS evidence boundary

## What is implemented

The private original producer observer (`source_groups_eligibility.inc` plus
`source_groups_transaction.inc`) stages every pre-call file/slot/root eligibility
record before `worldSendUpdate` mutates force_reload, last_world_id and link time.
It then observes the same original logical Packet immediately before pktSend.
No sink or actual server capture is installed by those hooks. Output remains
provisional until the entire transaction and its matching source inventory bind.

The actual native receive seam now validates the synchronous event on the actual
opaque CohMapClient against the retained decoded CohNetOwnedMessage. The additive
`coh_map_scene_record_create` can run only within that actual callback, via that
getter. It copies/hashes exact full decoded bytes and retains the original logical
end, post-command start, alignment/byte ceiling, inspected footer/counts and
actual message/order/loan/connection/profile/map/selection observations. Copies
and invented event structures cannot mint records. Record views survive network
loan and client retirement; neither client nor an ongoing session is retained.

The record charges its complete object+copy, actual simultaneous borrowed network
loan and64KiB local scratch before allocation, with32MiB owned/96MiB aggregate
ceilings. Caller retained_bytes must add client/transport queues, codec, other
records/graphs/owners/assets, callback/provider contexts and stack, allocator
metadata and all other live memory. SHA256 provider must hash the actual supplied
bytes; it may not return an expected pin or mutate/reenter source. Constructor
failures free candidate state and preserve caller outputs. The immutable record
contains no account, password, cookie, key or caller-created session hash.

## Exact representation and ordering

Original `worldSendUpdate` uses pktCreate, optional pktSetCompression, then
pktSendBitsPack(SERVER_GROUPS) directly. Original pktSetCompression calls
pktSetByteAlignment before the first written bit. Finish receives the original
full logical packet including command, bitLength, byteAlignedMode and compress,
BEFORE pktSend ownership/compression/framing. Native `coh_net_next_owned` expands
zlib to its exact decoded allocation, preserving packed logical bits or full
expanded byte-aligned bits. The Map dispatcher consumes the command and keeps
that actual start cursor for GROUPS. A byte-aligned packet has the command at
bits0..31; packed command consumes its actual variable-width prefix. No reader
repacking, scalar re-encoding or substring extraction is permitted for evidence.

For the smallest initial producer/receiver pairing, use the actual modern direct
GROUPS profile and require complete exact original logical allocation/bitLength,
byte alignment and compression provenance to equal the native decoded allocation
and end. Compare independently parsed command and post-command cursor. Unused
last-byte bits remain raw evidence, but outside logical bitLength; a future
comparison must explicitly distinguish raw allocation SHA from logical bit
identity. Do not introduce an old-command/cookie rewrite merely because another
profile supports it. Source pktSendCmd handles legacy command remapping/cookies,
but this producer writes GROUPS directly; an unsupported actual source profile
must refuse until its exact transformation is source-qualified.

## Remaining minimal owner and source association

A recorded actual receive is NOT a same-generation world witness. The legacy
raw Map begin consumes an authorization DTO, so its selectedDBID remains unbound
when positive. The optional `coh_map_client_begin_owned` bridge now consumes the
actual opaque DBSession handoff once inside the Map begin path, retains that owner
through Map lifecycle and derives the source-qualified positive EntCon.id rather
than accepting replacement identity labels. An actual-current receive lease may
then carry selected_dbid_owner_bound1 for that expected source selection. This is
not complete Map entity identity or cryptographic AuthServer evidence. The receive
record copies the observed scope but retains NO session/handoff owner; historical
receive provenance does not become ongoing session authorization after retirement.
The complete Map entity/character transaction still must validate self identity.
Encryption/dev-auth scope remains explicit and separate.

The future private original-server caller must select the actual owned link,
record its nonsecret actual connection/profile and source-established entity
identity (if present), acquire the qualified source quiescent owner-thread lease,
and bind catalog/root/future/resource state AT THAT SAME boundary before the
producer mutates it. Previously detached source hashes can be reused only after
actual same-boundary source serialization/equality has been demonstrated. A
synthetic run/source/session hash or a connection pointer is not proof. Native
and source connection IDs are only correlation observations; bind independently
admitted owned run/session receipts and source-established identity separately.

A future capture needs genuinely new eligibility records and actual original
logical packet plus the actual native record. Final export should contain all
raw files/checksums, exact bit bounds/cursors/profile, actual owner provenance,
source/build/run identity, quiet-lease acquire/release and cleanup evidence.
Use CREATE_NEW private provisional paths/no-replace publication, flush/close/hash
all files, verify exact source-to-receive equality, and emit failure receipts
without a successful binding on any partial write/refusal. No sink/run/workflow,
launcher export or client shipping observer is installed here.

## Protocol equivalence and authority remain distinct

The qualified complete COHCAT+COHRTS seed supplies omitted raw protocol-wire
inputs; equivalence does not require reenacting the original CLIENT cache as a
ritual. The eligibility witness still must prove every transmitted/omitted slot
and exact root/file/footer ordering against those matching source inputs. A full
NEW_WORLD with every normal file and root represented is the current supported
scope; unsupported delta/base/raid paths refuse. Raw GroupBounds cache checksums,
CLIENT-derived tricks/material/LOD/resources, authoritative self identity and
world/actor publication remain separate. Actual receive origin, source protocol
compatibility and full live world authority must never be collapsed into one flag.

Host tests use actual OS UDP with source-derived scripted peers, not a real
MapServer or Thor packet. The accepted historic343112-bit Thor packet is absent;
its numeric report cannot reconstruct bytes or be retroactively matched. No
successful source capture or accepted APK is repeated by this work.
