# Fresh character owner: opaque API sufficiency and minimal missing primitive

This is a source-only proposal, not an implemented or qualified owner. Existing
opaque APIs are insufficient, so implementation stops at this review boundary.
It follows `../deployment/AUTH-FRESH-CHARACTER-HANDOFF-PROPOSAL.md` and its pinned
27-file/43-whole-function original source chain. The current C50 kernel,
17-project-object runtime, completed empty-list owner, existing character choice,
Map serializers and accepted profiles remain unchanged. No `.c` inclusion,
symbol renaming, private-struct access or secure-owner fork is proposed here.

## Exact unavailable operation

`coh_db_session_choose` calls `coh_db_player_choose`, which refuses `p->empty`.
It cannot encode the ordinary authenticated empty-slot creation branch through
its public state machine. The completed `CohAuthDbDevelopmentOwner` correctly
cancels and destroys its controllers after its strict empty-list predicate;
it has no continuation, controller, grant or list getter. It must remain that
way. Its completed success receipt cannot be reused as a live grant.

`CohLogin` does provide the public operations needed by a new composition owner
to manage its own genuinely fresh Auth login and read that same controller's
sensitive authorization privately. `CohDbSession` provides the complete list,
diagnostics and actual MAP_CONNECT parser. The missing operation is creation
inside that **same opaque DB session**, followed by creation-specific offer
retirement. The new owner must use those public components and the reviewed
new primitive; it must not duplicate the existing secure owner's implementation
or manufacture an external receipt API.

## Proposed C-owned change

`coh_db_empty_creation_proposal.h` gives exact candidate declarations and
lifetime rules for review with C. It is not part of any target or ordinary
header. The proposed two operations are:

1. `coh_db_session_create_empty`: admit the ordinary-auth CHARACTERS context
   from actual private state, then consume the per-session-object attempt
   before inspecting request generations, slot, name, encoding or queue.
   Next compare expected generations and validate the current unlocked empty
   wire slot. Stale generations or invalid request fields cannot retry that
   same admitted object. The
   original source enum is Atlas hero1, local-map IP is zero and the unchanged
   pure `coh_db_choose_encode` supplies the grammar. Only a successful reliable
   queue sets a distinct creation mode and ordinary WAIT_MAP state. Any later
   owner failure/cancel cannot retry that object, even with a new begin.
2. `coh_db_session_retire_created_offer`: require that distinct mode and a real
   source-parsed MAP_CONNECT, privately validate the positive server-allocated
   DBID, nonreserved actual Map cookie, actual owned Map endpoint/id and all
   generations, then cancel/wipe before emitting a small fixed summary. No
   cookie/UID/DBID is supplied or returned. This terminal offer cannot later be
   used for Map creation.

C's read-only source assessment agrees these operations also need two narrow
**existing handoff guards**: ordinary raw and typed handoff takes must refuse
creation mode. Without them, an uninitialized allocation offer could reach the
existing `newCharacter=0` Map controller. Those guards preserve behavior for all
existing noncreation sessions and avoid widening any Map serializer. Distinct
creation state and the per-object attempt latch stay private; no raw fields are
added to the public owner diagnostics.

An expected generation is a staleness comparison, not caller authentication.
The session must independently retain actual ordinary-auth identity and matching
list facts. `begin_local` is refused; exactly one lifetime complete list, no
queue/unsupported/choice/handoff, internal slot index consistency, EMPTY status,
nonvisitor/unlocked state and actual current list UID are mandatory. Name
length/ASCII/NUL/control rules are only local bounds; the original server still
owns name validity, reservation, slot capacity and actual allocation.

Existing accounting is cumulative across begin; list generation here means the
real `player_lists` sequence. The first owner requires exactly1. A replaced list
or rebegin cannot become a fresh creation authorization by caller declaration.
The outer owner consumes its own begin and creation attempts before the public
component calls, including allocation or input failure, and keeps its cancel
callback under a busy/reentry guard. A native endpoint or generation comparison
is not an independent proof of the peer process. The future hosted driver must
observe the exact owned Auth/Db/Map/SQL executable paths, binary identities and
process start generations before and after the transaction, retaining current
channel/listener ownership and private platform teardown gates.

## New owner once the primitive is reviewed

The new unprotected owner will expose only configuration, one begin, monotonic
service with cancellation, fixed diagnostics, cancel/close and destroy. Its
private configuration holds actual admitted Auth endpoint/crypto, fresh
transport entropy, measured probe checksum, a bounded private new name and an
owned Map registration/endpoint. No caller grant, account UID, cookie, DBID,
player list, DB controller or handoff setter/getter is allowed.

It independently performs fresh encrypted Auth login, original registered shard
selection, private actual-authorization bridge and original real-auth DB begin.
It retains provider/crypto lifetimes, matches the internal UID to the current
list and requires the same strict unsupported/queue policy as the completed
empty-list owner. It then invokes the new creation primitive once. Success stops
at the server's actual offer for a **CONTAINER_UNINITIALIZED**, not a complete,
saved or resumable character. The new owner retires the offer and destroys both
controllers before scalar success. No Map client socket/body, READY,
RECEIVED_CHARACTER, full-update ACK, scene or actor authority is permitted.
Normal version and checksum-reference admission remain false under the explicit
provisional development exception.

## New focused qualification only

No old Auth-only, completed-list, native17, C50 or prior core suite is rerun.
The eventual new controls must execute the new code, not a separately modeled
state machine. Existing source writer/consumer and choose-encoder provenance is
reused at its immutable pins; any newly required original-chain oracle must
retain exact whole-function bytes from the existing 27/43 audit and keep server
allocator/SQL/Map actions explicitly synthetic.

New negative transactions must cover:

- Missing/wrong UID through the private genuine-authorization bridge, wrong
  shard, noncurrent/replaced list, stale receipt/session/list/selection generation
  and a second owner or reused component lifecycle.
- Nonempty, locked, visitor, invalid-index and no-capacity slots; bounded name
  rejection, generation overflow, exactly-one attempt despite encode/queue
  refusal, duplicate create, cancel/reentry before and after queue.
- Source-allocated DBID/Map cookie arrival only through the real parser; absent,
  malformed, wrong-state/endpoint/map/generation offer, duplicate retirement,
  and creation-mode refusal by both existing raw/typed handoff routes.
- First-failure preservation, secret retirement, controller/socket cleanup and
  every allocation failure. A synthetic cancellation must **not** claim rollback
  of a synthetic previously allocated server row. Model the persistent container
  as still present until the separately owned database is retired; fail any
  result that confuses socket closure with persistence rollback.

The source/API proposal itself makes no host-test, original function execution,
compiler, network, Windows, SQL or runtime claim. Root integration stays held
until the current receiver scene's immutable launch and the C interface/source
qualification are independently reviewed.

## Separate deployment blocker

Even a correct owner cannot allocate a useful handoff without a compatible
owned Map READY_FOR_PLAYERS against the **same fresh MSSQL DbServer**, exact map
assets/definitions, original interserver protocol and verified registered UDP
endpoint. The current list driver owns no Map/Launcher and uses `-start 0`.
The historical PG/fake-auth Atlas profile/character identity supplies neither
that runtime nor a matching Auth account. No SQL AuthId rewrite, historical
DBID296 attachment or copied row is allowed.

Original creation writes the container before handoff. Native cancel/offer
retirement proves no SQL rollback. An eventual actual driver must stop every
owned service (including Map) with bounded job-empty/resource proofs, retire the
whole disposable database and separately verify its absence. Until that
same-backend Map/source/configuration prerequisite is admitted, there is no
actual run proposal. Full initialized Map character creation requires the
separate original creation body and data-backed authored choices already
listed in the parent source proposal.
