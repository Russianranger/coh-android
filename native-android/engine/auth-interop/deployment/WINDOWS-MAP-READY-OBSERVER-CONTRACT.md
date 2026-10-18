# Proposed retained-handle same-realm Map readiness boundary

This is source research and an API contract, with exact source pins in
`../evidence/windows-map-ready-observer-source-20261018/audit-v2.json`. It does not
implement a monitor, launcher, platform backend or readiness detector. No
project import, API, compiler, test, socket, account, profile or service was
executed. Original source is read at immutable9c29e08c8d7e0ab38cff00f2997c39738a56ad07.

## Existing interfaces do not yet compose into a live Map

The new fresh-character CLI2b63 proposal correctly takes only private policy
and credentials, measures its own executable, and invokes the new public owner
once. Its96-byte policy is a bounded private input, not evidence that a Map is
registered or ready. Its platform API remains declarations with no backend.

E's frozen `OwnedProfileProcess.cs` f23a4c57 source is deliberately inert-only.
It launches only `--inert-probe`, waits for child exit, and always terminates/
observes the job before deleting the profile/account. It returns no live lease
or raw handle. It cannot currently launch Map, keep it alive while a creation
probe runs, or furnish a readiness proof. Its private journal/creation identity
and fixed public receipt must not be promoted to those roles. The new installed
compiler recipe is build-only and does not change that lifetime.

A future separate fixed Map role needs a reviewed opaque live lease phase:
retain the returned actual Map process/thread handles, assigned job, exact
fresh SID/profile, private GUI and file/log ownership until the coordinator
finishes readiness observation and the one fresh-character probe. A distinct
terminal close phase performs all existing job/handle/hive/profile/account
checks. An outer timeout/crash remains quarantined/unobserved cleanup. No
general executable, arbitrary command or raw handle/PID/SID public getter is
introduced. The inert role and its source/test proof stay unchanged history.

Private Map stdout/stderr capture also remains unqualified. The inert helper
forwards no parent stdhandles; its silent child is insufficient for ordinary
Map logging. A source-owned same-target-user bootstrap that opens exact private
logs before Map launch is one possible future scope, with its own suspended
launch, inherited job and both retained process identities. It requires a
separately reviewed process limit/cleanup contract; it cannot be inserted into
the current one-active-process inert job. A shell string or assumed-valid
cross-logon handle value is not a capture mechanism. No raw logs reach CI.

## Original state chain and what the monitor actually proves

| Source edge | Required observation and limit |
| --- | --- |
| `dbInit(0)` loads the static maps file. | Admit the actual staged source/asset Map1 container. No SQL identity rewrite or manufactured container row. |
| `registerDbClient` accepts positive Map1 only when its container exists. A nonzero launcher cookie must match; cookie0 follows the ordinary manual-command-line branch. | Only reviewed positive Map1 argv with ordinary cookie0/no launcher role. Do not synthesize a launcher grant or bypass its comparison. |
| Registration stores actual link/IPs/UDP/TCP, sets `active=1, starting=1`. | Current owned Map→Db6997 channel and process generations. Registration is not readiness. |
| Map `logNetInit` connects original TCP6989 before registration. With `UseLogServer0`, Db `logNetInit` binds6989 itself. | Current DbPID owns both6997 and6989 listeners; current MapPID owns both actual TCP peers. No extra LogServer, config toggle, skipped call or deadline repair. |
| Map `dbReadyForPlayers` sends its actual map id. Db `dbClientReadyForPlayers` clears `starting`. | A ready-send console marker alone is insufficient. Observe Db's current container state independently. |
| `svrMonSendList(CONTAINER_MAPS,active_only=1)` changes to include rows with `active || starting`. | Exact full MAPSERVERS response containing Map1 and explicit `Starting=0` implies active through this producer. `Active` is NOT a serialized schema field. |
| `freeMapContainer` clears active, starting and link. | Such a row is excluded by the producer; a missing/deleted row cannot be treated as ready because its local zero default is0. |

The original ready handler does not compare the packet's map id against its
`link` argument. The monitor state is therefore a Db readiness-state witness,
not direct READY packet attribution or proof of its sender. A fresh exclusive
realm, no unowned Db6997 clients, retained current process generations, and the
registered Map's exact endpoints/link remain necessary. Public output must keep
`ready_command_sender_attributed=false`. No new source guard is silently added
to the original server to make that claim stronger.

MapCon's monitor PID/host fields come from remote-process statistics. They are
not native retained-handle generations and are not a required PID authority
for the manual cookie0 branch. Match processes using the actual held Windows
handles, process creation times, independently admitted PE bytes, owned socket
tables and exact registered endpoint. Do not substitute a remote PID or clock.

## Minimal read-only monitor exchange

The original monitor listener is Db-owned TCP6996, using ordinary NetLink TCP,
default network profile5. This is not Auth framing or the existing UDP adapter.
Major/minor protocol constants are20110804. A new bounded observer may send the
application `DBSVRMON_CONNECT` with only the exact major DWORD; the original
server permits omitted minor and leaves `allow_new_container_types=0`. After
its positive connect reply, the server schedules a full update automatically.
No REQUEST, REQUESTDIFF, REQUESTVERSION, REQUEST_PLAYERS, RELAY, EXEC or logstats
application request is necessary. Transport control/ACK teardown is separate.

There is no original maps-only request. The full-update producer sends maps
first, then crashed maps/launchers (and newer server-app types when requested),
plus stats. The minimal proposed observer consumes exactly CONNECT acceptance
and the first complete FULL MAPSERVERS snapshot, then closes its own socket.
Later buffered bytes/frames are discarded on close and are not called parsed,
accepted or classified. If a different application message arrives before the
required map snapshot, or the first map message is a diff, the attempt refuses.
It never opens a player request or command/relay path to avoid handling them.

Each readiness poll is a NEW bounded read-only full-snapshot connection under
the same retained process/realm lease. This avoids diff/history/default-zero
reuse. An absent/starting Map returns WAITING; an unknown schema, malformed
frame/body, extra/duplicate row/field, replacement generation or unexpected
command returns REFUSED. There is no Auth/creation retry. Poll count, deadline,
bytes, frames and allocations need explicit source-qualified bounds before any
implementation; the original5s connect/no-timeout convenience functions are
not automatically deadline-safe APIs. Never inherit netConnectEx's downgrade
retry as acceptance of another network profile.

The original ServerMonitor receiver is not a strict admission implementation:
it calls `sdUnpackParseInfo(..., false)` and can retain out-of-sync/invalid
fields. A new observer must first require the exact pinned schema recursively,
including field name, type, parameter, order, nested BaseCon/NetLink and counts.
It must use fixed bounded storage, reject schema ambiguity and decode the whole
first map snapshot transactionally, including terminators/deletes/exact logical
end. No received schema may install arbitrary callbacks, allocate from peer
lengths or authorize field skipping. Full ParserSend forces all relevant
fields, so `Starting` must be explicitly present exactly once with integer0;
absence/default0 is not readiness. String/float/stat fields are private bounded
decode inputs only and never public identities or executable commands.

This codec/transport remains a NEW unimplemented source scope. It needs an
original writer/schema oracle and focused malformed/fragmented/full/diff/bounds
controls before host execution. Reusing the GUI monitor entrypoint would add
autostart/command/UI behavior and permissive schema handling; this proposal
does not authorize that reuse or a generic monitor command surface.

## Retained-handle observer contract

The future coordinator owns an opaque `FreshRealmMapLease`, constructed only
by its qualified Auth/Db/SQL and fixed Map launcher. Its immutable private state
contains held Db/Map process handles, their admitted executable/generation
identities, the live profile/job lease, source-owned Map1 routing and the staged
asset/source policy. No caller can inject a UID/DBID/cookie or replace those
handles. A process opened only from policy-file PID is observation authority,
not a substitute for the launcher's original lifetime ownership.

`ObserveMapReadyOnce(lease, bounded_deadline)` returns only a fixed enum
WAITING/READY/REFUSED and fixed scalar flags. Within one consuming call:

1. Verify the same retained Db/Map handles are alive (actual wait state), their
   creation generations and private executable identities remain equal, SQL
   generation remains current, and the original profile/job lease is live.
2. Verify Db-owned6997/6989/6996 listeners, current owned Map6997+6989 channels
   and the observer→Db6996 pair through exact socket ownership in both
   directions. Refuse any additional/unowned Map service client in this fresh
   realm. This is read-only observation, never a listener takeover.
3. Read a fresh complete map snapshot from that owned connection under the
   exact schema/profile. Require the single expected Map1 row, explicit
   `Starting=0`, exact current registered loopback UDP7001/IP candidate and
   present NetLink. Validate row/internal ID equality and all other fields;
   no stale snapshot/diff inheritance or duplicate ID is admitted.
4. Recheck all retained generations/identities, channel/listener ownership and
   live profile/job state after the snapshot. Close the owned monitor socket
   and observe that observer handle retirement. Any late observation/close
   failure blocks READY and preserves the first failure.

Fixed output can include schema, outcome/failure enums, bounded poll/frame/
byte counts and booleans for full schema/message, expected row/endpoints/link,
explicit starting-zero, current generations/channels and observer cleanup.
It exports no PID/TID/SID/ticks/path/hash/nonce, map name/host/version/SQL text,
packet/schema bodies, UID/DBID/cookie or raw Win32/exception strings. A private
driver may retain exact selectors for lifecycle recovery under its journal
contract; they never become public monitor evidence.

Only READY under that exact current lease permits creating the native probe's
private policy file. Bracket the one creation attempt with the same observer
and process/realm checks; post-probe failure cannot be overwritten by native
success. A missed before/after observation does not erase possible persistent
allocation, and cleanup is not SQL rollback. The file is not itself a reusable
READY receipt. Do not change its current96-byte layout to claim monitor state
the native process did not observe; a driver receipt keeps that separate.

Before actual Windows use, remaining gates are the inert helper's real build/
WinAPI qualification, fixed live Map role and private capture, exact current
Map PE/DLL/assets admission, same-realm startup registration, new read-only
monitor codec/OS ownership controls and new probe platform implementation.
Existing Auth/list/selected cases and owner controls are not rerun by this
source proposal. Normal version/reference checksum, initialized character,
Map client body, READY/character/full-update ACK and world authority stay false.
