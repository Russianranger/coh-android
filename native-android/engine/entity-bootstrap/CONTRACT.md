# DB selection identity bootstrap and actor transaction boundary

Earlier statements that selected_dbid must remain0 because no DBID is in the
handoff were incorrect for the pinned original DBGAMESERVER_MAP_CONNECT producer.
The DB character LIST and choose request omit DBID. The handoff first field is
written by sendLoginInfoToGameClient as ent_con->id. Its Game consumer names a
local variable link_id and ignores it; that local name does not change producer
semantics. Generic CohAuthMapHandoff.link_id remains raw because other command
contexts must be separately qualified. This is a source correction, not a new
source field or a guessed slot/link/cookie identity.

The opaque CohDbSession owns these stages: authorized DB transport → accepted
SEND_PLAYERS with session UID → validated existing unlocked nonvisitor choice
and monotonic selection generation → WAIT_MAP → exact whole MAP_CONNECT →
positive signed32 first field → one-shot owned handoff.selected_dbid. No public
POD-to-DBID promotion helper is exposed. Wrong phase, zero/high DBID, malformed
command/payload, cancellation/failure/stale session refuse without handoff.
The existing take consumes owner state and starts graceful disconnect. Merely
parsing generic handoff bytes or providing an arbitrary raw link_id cannot mint
an identity through this owner. As with all C APIs, caller modification of POD
copies does not authenticate them; integration must consume this actual owner.

Original source chain:

1. DB sendPlayers stores ContainerId in server-owned client.players[wire_slot].
   handleChoosePlayer selects this entry as char_id and loads CONTAINER_ENTS.
   For existing characters the supplied name is not the identity lookup.
2. handlePlayerContainerLoaded obtains EntCon.id and hands that container to Map.
   Map dealWithContainer sets e.db_id=ci.id and returns its generated login cookie.
   dbReceiveEnts sends ACK entries(ci.id,cookie); DB handleContainerAck looks up
   exactly that container ID before sendLoginInfoToGameClient(container,cookie).
3. Its packet first scalar is ent_con.id, then mapID, two addresses, UDP/TCP ports,
   cookie. QueueServer passdbOrMapConnect copies all seven packed fields unchanged.
4. Map CLIENT_CONNECT resolves entFromLoginCookie and clientSetEntity. Resume
   repeats cookie association. entSendCreate marks e==player_ent and sends e.db_id.
   Server tick uses clientGetViewedEntity, which returns slave when present.
   Thus the normal non-slave profile requires self.dbid==owned selected_dbid;
   a different viewed/slave entity is an explicit unsupported identity profile.

The whole original DB producer and whole Queue passthrough execute in the oracle
with original bit writer/readers. Fixtures cover direct/queue/advertised IP,
both alignments and old/current commands, edge signed DBIDs and cookies. Mock
container/account/IP policy/packet factory effects are explicit; no running DB,
Map, AuthServer or Win32 ABI acceptance is claimed. Native socket regression
uses those exact original-producer fixtures and source-qualified metadata.

Authoritative actor transaction contract (not enabled by this module):

- Retain owned DB selection/handoff generation, endpoint/cookie/channel provenance
  and normal-vs-slave profile through complete Map establishment. Local fake-auth
  retains only its documented provisional scope; encrypted login remains separate.
- Stage the single self create marked by the admitted original producer, with
  DBID equality to this handoff, server entity ID/index/generation and deletion
  checks. Full required appearance/rare/common/control grammar must pass.
- Stage the complete character/global suffix in source order under exactly
  matching dictionaries/world/resource generations, preserving immutable packet
  lease and complete control/entity event lifetimes and later-command framing.
- Publish DB identity, selected entity, character and world/actor state atomically
  only after all required components validate. Rollback includes newly learned
  identity and source events on any late field/dictionary/resource failure.
- No READY, RECEIVED_CHARACTER or full-update ACK follows merely from handoff,
  unique self, name equality, prelude, source fixture, or this source correction.

No actor or transport application ACK implementation is added. The original Game
calls notifyReceivedCharacter early during create; native intentionally does not
copy that premature side effect before complete transaction validation.
