# Proposed fresh authenticated character allocation and handoff

Actual run `39097070843` now establishes the provisional development-policy
Auth→DB transaction through one complete matching list of **48 empty, unlocked
slots**. Its canonical evidence is
`../evidence/auth-db-inventory13-success-39097070843/`. This proposal is a new
scope; it does not resume that completed owner or reuse its wiped grant.

The read-only source audit at
`../evidence/fresh-character-source-scope-20261018/audit.json` pins 27 whole files
and 43 whole functions from published
`f3ee9db6bc8a323c896769f0952dd242fc79e2f4`. No creation, Map, test or compiler
was executed for this proposal. An initial audit-development selector named a
nonexistent native function and refused; the corrected selector pins the actual
`coh_map_serialize`. No failed result was treated as qualification.

## Original identity and creation chain

| Original source | Required behavior |
| --- | --- |
| Game `dbChoosePlayer` | Sends slot, local-map IP, bounded name and `createLocation`; it sends no UID or DBID. |
| DB `handleChoosePlayer` | Takes `client->char_id` from that authenticated client's own `players[slot]`. A zero entry enters creation, validates/reserves the name, then asynchronously counts unlocked characters for the same `client->auth_id`. |
| DB `s_finishHandleChoosePlayer` | Enforces owned slot capacity, allocates a real `EntCon`, and writes the current client's AuthId/account/name plus source-derived start map/type. This is a real container write before Map handoff. |
| DB `handlePlayerContainerLoaded` / `setNewMap` | Carries that server container into the owned destination Map, with its real container lock and original waiting-entity machinery. |
| Map `containerHandleEntity` → DB `handleContainerAck` | Map loads that exact server entity, creates its actual login cookie and returns a container acknowledgment. |
| DB `sendLoginInfoToGameClient` | Only a container handed to Map can yield `MAP_CONNECT`: first field is actual `EntCon.id`, followed by map ID, addresses, ports and the Map-generated cookie. |
| Game `sendCharacterCreate` / Map `CLIENT_CONNECT` | A fresh character requires `newCharacter=1` and the full original creation tail. Existing `newCharacter=0` is refused for an uninitialized entity. |

The ordinary creation-location enum is in `Common/comm_backend.h`.
`DBGAMECLIENT_CREATE_PLAYER_PRIMAL_HERO` is enum value1; the original
`determineStartMapId` selects Atlas base1 or an original available clone.
Routing/override and actual owned Map identity still need admission; the client
must not invent a map, cookie, DBID or character-list entry.

Historical character296 and its account relationship cannot be attached to this
fresh account by SQL. The new identity must come from the real authenticated
slot and server allocation. No row cloning, AuthId substitution, direct
container seeding, fake-auth receipt or imported handoff is proposed.

## Smallest separate opaque owner

Proposed new deployment-only files:

- `windows/auth_fresh_character_owner.{h,c}`: an opaque one-shot owner that
  performs its own fresh encrypted Auth→registered shard→real-auth DB login.
- `windows/wrapped_db_fresh_creation.c` and private header: one composition TU
  includes the current received-prefix/session TU and adds a private
  `coh_db_fresh_creation_begin` operation. The ordinary session source,
  existing-character choose APIs, wire encoder and Map serializer stay intact.
- A new probe, driver scope and focused ownership controls, reviewed before any
  actual execution. No default or completed-empty-list scope is widened.

A suggested outer API is create/configure, begin(private credentials, monotonic
clock), service(cancel), diagnostics, cancel/close and destroy. Configuration
contains the admitted crypto provider, fresh transport entropy, measured probe
checksum, a private bounded unique character name and the single explicit
Atlas-hero creation location. No grant, UID, cookie, DBID, borrowed controller,
player list or raw packet can be supplied or returned.

The owner consumes its Auth begin attempt before calling the controller, and
consumes its creation attempt **before encoding or queueing**, even if either
fails. It keeps the genuine Auth authorization and original DH/provider lifetimes
through private bridge consumption, with no retry/rebegin/recreate after any
terminal result. Cancellation callbacks remain reentry guarded and are polled
before bridge, queue and scalar publication.

Creation is permitted only after exactly one complete matching-UID list from the
same current session/receipt/transport generation, with no queue, unsupported,
prior choice or handoff. Internally choose a real parsed wire slot that is
EMPTY, unlocked and nonvisitor; require actual slot availability and a bounded
nonempty source-valid name. All other list state remains private. The new
private operation uses the unchanged `coh_db_choose_encode` and reliable queue;
it advances the same selection generation and enters WAIT_MAP only after the
queue succeeds. It exposes no raw external authorization route.

Only the actual current WAIT_MAP `MAP_CONNECT` parser may supply the positive
server DBID and cookie. A typed handoff is taken exactly once, validated against
its session/receipt/selection generation and source-owned Map endpoint, then
retired and wiped inside this new owner. For this first scope **no Map client
socket is opened**. Do not pass this handoff into the existing resume-only Map
controller: it would send `newCharacter=0` for an uninitialized entity.

Diagnostics may report fixed stages/counts/Booleans, creation attempted, one
server-allocated-container handoff observed and private buffers destroyed. They
must report initialized/resumable character, completed creation, character saved,
Map client acceptance, scene/world, READY, RECEIVED_CHARACTER and full-update ACK
as false. An allocated placeholder is not a complete player.

## Side effects, teardown and prerequisites

Unlike the completed empty-list scope, original `s_finishHandleChoosePlayer`
writes a real container before the handoff. Socket cancellation or handoff
retirement is **not** a persistent-row rollback. On immediate routing failure,
original `doneWaitingChoosePlayerFailed` may delete a `just_created` container;
that branch does not establish successful-path deletion. The actual driver must
own an entirely fresh disposable database and all registered Map processes,
stop those services with the existing suspended-launch/job-empty proofs, then
drop and verify absence of the whole owned database. No targeted SQL character
or ownership rewrite is a cleanup substitute. Report native/socket cleanup and
persistent database retirement separately, preserving the first failure.

Before any actual attempt, independently admit:

1. A compatible original Map executable and its build/source/import closure,
   registered and READY_FOR_PLAYERS against **this same** owned MSSQL DbServer,
   plus its process generation, interserver ownership and exact advertised
   loopback UDP endpoint. The current Auth→DB scope starts Db with `-start 0`
   and owns no Map or Launcher. Either an already owned ready Map or a genuine
   owned Launcher path is required; otherwise original routing can return
   `NoLaunchersRunning` and delete the new container. No endpoint alias suffices.
2. The exact original Db↔Map protocol and both processes' version/provider
   inputs. The accepted manual Atlas PG/fake-auth Db profile cannot supply this
   transaction. Its historical character/save identity and PostgreSQL database
   cannot be transferred into the MSSQL account. Reusing a compatible Map PE
   would require an explicit owned runtime/configuration admission.
3. Exact Atlas map metadata/data and all definitions/assets needed by that Map
   to load an uninitialized player container and generate a cookie, with schema
   and template compatibility. Existing saved-character scene success does not
   prove this fresh-container branch. Keep all logs private: originals print
   Auth names, DBIDs and cookies.
4. The explicit provisional development exception and genuine fresh Auth
   membership/UID context. Normal version and checksum-reference admission
   remain independently blocked; success cannot change those flags. No
   installation/version/reference values or production profile are proposed.
5. New focused controls for nonempty/locked/visitor/out-of-range slot, wrong UID,
   duplicate/replaced list, stale generation, repeated creation, queue failure,
   cancellation/reentry, malformed/foreign handoff, wrong Map ownership, late
   teardown failure and database-retirement refusal. Do not replay old Auth-only
   or completed empty-list suites.

## Later full Map character creation

The current source **does contain** the definition previously described as
absent by the older Map audit: `Game/src/gameComm/initClient.c::sendCharacterCreate`.
It writes the creation bit and calls `sendCharacterToServer`; the latter emits
`CLIENTINP_SENDING_CHARACTER`, player type, class/origin/two initial powers,
tray, costume, power customizations, title/article/gender and entity strings.
`character_SendCreate` selects the first power in each original primary and
secondary category, and writes each real power CRC plus its character power
unique ID; there is no fabricated power-count field.

A later full creation serializer needs actual authored class/origin and valid
initial primary/secondary choices tied to the same admitted game definitions,
real per-character power-ID ownership, bounded tray/costume/customization data
and independently source-qualified writer/receiver parity for the whole body.
Map's original receiver validates class/origin/power availability and costume,
initializes the character, then the sending-character branch persists it. A
name and empty slot alone do not provide this payload. Existing DB-list parsing,
initial-character receive parsing and dictionary recovery do not qualify an
outgoing creation serializer. No full creation or persistence claim is made by
the proposed first handoff-only owner.
