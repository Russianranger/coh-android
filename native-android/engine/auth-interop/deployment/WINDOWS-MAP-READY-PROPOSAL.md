# Same-realm Windows Map deployment: source findings and bounded next scope

This is a source/API research proposal. No Map, registry, user-account, profile,
service or Windows API action was executed. The immutable source audit reads
revision `d9adf2b431a039357f8bfe878d3d0da991a81b19`: 31 files and 59 named
whole-function definitions, with byte offsets and hashes in
`../evidence/windows-map-deployment-source-20261018/audit.json`. It also reads one
already retained older Map build ZIP. That old binary is not the pending new
initial-owner Map build, and this audit admits neither binary for live use.

The preferred next deployment design is a new disposable Windows local account
and complete fresh profile for Map only. It preserves Map's ordinary registry
paths and source behavior. Auth, DbServer, LocalDB and the actual Auth account
stay in the existing runner-owned disposable realm. This is feasible from the
documented API contracts, but the launcher, profile/desktop/file ownership and
cleanup controls below remain unimplemented and unqualified. No Map nonce-path
overlay or general registry hook is justified at this stage.

## Ordinary connection and registration chain

| Original operation | Exact source behavior | Future admission consequence |
| --- | --- | --- |
| `parseArgs1/parseArgs2` | `-map_id 1` selects a positive ordinary Map ID and clears `local_server`; `-db 127.0.0.1` supplies the Db host. | Fixed allowlisted argv; no negative editor-map ID, `-localmapserver`, launcher role or caller character DBID. |
| `connectToDbserver` / `dbTryConnect` | Original TCP connection to `DEFAULT_DB_PORT=6997`, then `DBCLIENT_INITIAL_CONNECT` with `DBSERVER_PROTOCOL_VERSION=20110503`. | Observe current Map→current Db process-owned TCP pair; leave the exact protocol check intact. |
| Map `logNetInit` | A synchronous original TCP connection to port6989 occurs before registration; `NO_TIMEOUT` is0. | Add exact current DbPID listener/pair checks. Do not infer absence, raise a deadline or bypass this call. |
| Db startup with `UseLogServer 0` | DbServer's distinct `logNetInit` in `DBServer/src/logserver.c` binds6989 in that same process. | No extra LogServer process or config change is required by the source. Actual listener availability is still an observation gate. |
| Db `dbInit(0)` | Loads `server/db/maps.db` through `containerListLoadFile` and marks the loaded maps static. `-start 0` does not skip that load. | Admit the exact staged flat file and verify the intended positive Atlas container exists; never seed or rewrite character SQL identities. |
| Map `dbRegister` / Db `registerDbClient` | Sends Map ID, IPs, ports, static-link bit, launcher cookie and patch-version string. Positive IDs require an existing container. The original command-line branch permits launcher cookie0; nonzero cookies must match the actual launcher request. | If manual registration is used, label that exact original branch. Do not invent a launcher cookie or relax the server check. |
| Db registration | Assigns the actual live link/endpoints, `active=1`, `starting=1`; sends the source container list to Map. | Bind registration to current Map/Db generations and actual channel, not a stale log line or historical map row. |
| Map startup to ready | `groupLoadMap`, `dbSetupMap`, then `dbReadyForPlayers` sends the actual Map ID and batch-sends. Db `dbClientReadyForPlayers` clears that container's `starting` flag. | A live listener or Map console text alone is insufficient to claim the Db received this transition. |

The audited startup/registration path communicates with DbServer over its
ordinary wire. `dbExecuteSql` itself sends `DBCLIENT_EXECUTE_SQL` over that link;
it does not open a PostgreSQL or ODBC connection. The existing Map CMake target
links AILib, UtilitiesLib, Lua and PhysX. This is a bounded path/import finding,
not a statement that every conceivable Map role/plugin is backend-independent.

The retained old Map PE has exactly 7,507,456 bytes, SHA256
`fa4eedf702e14c9c79e0bf72abf6a4b0fd2f3bca9b14e3c911ee3974d7e99b14`,
i386, no delay imports, and eleven direct DLL imports: PhysXLoader,
PhysXCooking and nine Windows platform DLLs. No direct ODBC/libpq import occurs.
`preloadDLLs` additionally attempts to load PhysXCore by name, so an import table
alone is not a complete dynamic DLL closure. These facts do not qualify PhysX
startup, transitive dependencies, newer Map bytes or any Windows runtime.

## Concrete isolation problem in an unchanged Windows launch

`testClientSetDb` always uses `HKCU\SOFTWARE\Cryptic\TestClient` and writes
`CS`; it is called both by `-db` parsing and `dbTryConnect`. The compiled staged
old `svr_init.c` still contains the ordinary hardcoded `regSetAppName("CoH")`.
The Map version calls reach `isExecutableInInstallDir` and
`regGetInstallationDir`, which can create `HKCU\SOFTWARE\Cryptic\CoH` and can
delete a wrong-type `Installation Directory` value. A fresh CWD or process job
does not isolate those effects from the runner profile.

The ordinary locale getter currently returns English directly, and the startup
validity guard does not take its locale-write branch. `duGetIntDebugSetting`
reads HKLM; `initRegReader` does not create a missing key until a writer invokes
`rrLazyWriteInit`. Beacon installation can write HKCU Run and `c:/Beaconizer`,
but that branch is reached through the excluded beacon role. The future argv
gate must reject all beacon/editor/query/creation-bin/alternate-role switches,
not rely on an informal intended command line.

An in-main `RegOverridePredefKey` or two-path source redirection could bound
audited post-main application writes, but would not by itself establish
isolation for DLL/CRT work before main. The retained PE includes closed PhysX
DLL dependencies; this audit does not infer their registry behavior. A fresh
OS user and loaded whole profile avoids needing to infer which of these HKCU
writes occur before or after main. It is profile isolation, not a whole Windows
filesystem, HKLM, kernel-object or network namespace.

## Research contract for a new disposable OS-user lease

Microsoft documents that `CreateProcessWithLogonW(LOGON_WITH_PROFILE)` loads
the target user's hive before returning. It requires local-logon permission;
it cannot be called by LocalSystem. Target-user access to the image, CWD,
window station and desktop must be granted. `CREATE_SUSPENDED` supports
association with the owned job before execution. Use a fully specified image,
mutable bounded command line, explicit CWD and a qualified environment.

Primary sources, checked2026-10-18:

- [CreateProcessWithLogonW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw)
- [Process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)

Proposed lease behavior, not yet implemented:

1. Gate on the explicitly qualified hosted Windows environment and actual
   suitable caller token. Create only a fresh bounded random local username
   (within the documented20-character limit), never reuse an existing name.
   `NetUserAdd` success establishes ownership; retain the resulting exact SID
   privately and revalidate name→SID before any destructive cleanup. Keep the
   generated OS password only in wipeable private native storage, never argv,
   environment, log, SQL or public receipt. Do not add the account to
   Administrators or change a preexisting account, policy or profile.
2. Give only that SID, the runner and SYSTEM access to the new private Map
   files/working tree and output directories. Shared source inputs are read-only;
   mutable caches, temporary files and logs are owned copies. Reparse/identity
   checks, exact pre/post hashes and absent-before-create ownership remain
   mandatory. Explicit access must be observed, not inferred from the runner's
   current permissions. No domain/network share or integrated SQL login is used.
3. Use an independently owned private window station/desktop if the target
   cannot use a suitable inherited one without modifying existing ACLs. Preserve
   existing desktop security. Station/desktop creation and handle ownership need
   dedicated qualification; `SetProcessWindowStation` is process-wide, so it
   must not silently alter the long-lived Python coordinator's GUI context.
4. Launch the exact admitted Map executable suspended with the loaded target
   profile. Keep the returned process AND primary-thread handles. Verify actual
   process token SID, PE path/hash, creation generation, primary-thread owner
   and generation; assign to the exact owned job, recheck, then require
   `ResumeThread`'s previous count to be1. A failed/late launch, assignment,
   resume or handle close cannot be retried as the same attempt or counted clean.
   The existing Popen-based `DevelopmentJob` cannot impersonate this native
   handle-returning API unchanged. A new adapter must prove the same job-empty
   and direct-process exit gates without weakening accepted helpers.
5. Do not assume parent stdout handle values work across the new logon.
   `STARTF_USESTDHANDLES` has an explicit validity obligation. Resolve and
   qualify private capture before executing Map: either proven valid target
   handles or a small source-owned same-user bootstrap that opens its private
   logs and launches the exact Map as an inherited job member. The latter is a
   new executable/lifetime scope, not a shell command string fallback. No raw
   Map text may reach the public CI console or artifact.
6. On teardown, first terminate/observe the complete owned job empty and every
   retained process exited, then close native/process/thread/profile observation
   handles. Require bounded hive-unloaded observation before profile deletion;
   do not infer current-host unload timing from historical OS-specific notes.
   Use `DeleteProfileW` for only the exact newly owned SID/profile, then remove
   the exact newly owned account with `NetUserDel` and verify both absences.
   Attempt independent cleanup paths while preserving first cause. A failure
   leaves cleanup false and retained ownership information; never delete by
   username prefix or recurse over unrelated profile directories.

The user-management APIs require appropriate administrative authority. Profile
deletion is a separate administrative operation; deleting an account is not a
profile-cleanup proof. If explicitly loading a profile is needed, its retained
`hProfile` must be released by `UnloadUserProfile` after all hive handles close;
that path additionally requires the documented backup/restore privileges. The
implicit `LOGON_WITH_PROFILE` path must not invent such a handle.

- [NetUserAdd](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuseradd)
- [NetUserDel](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuserdel)
- [DeleteProfileW](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteprofilew)
- [LoadUserProfileW](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-loaduserprofilew)
- [UnloadUserProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-unloaduserprofile)
- [Window-station security](https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights)
- [Desktop security](https://learn.microsoft.com/en-us/windows/win32/winstation/desktop-security-and-access-rights)
- [CreateDesktopW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdesktopw)
- [SetProcessWindowStation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocesswindowstation)

## Minimal hosted-driver extension after review

Keep existing Auth→empty-list and all selected/default behavior exact. A new
typed Map scope can compose the same fresh owned Auth/Db/SQL activation, admit
the separately retained exact Map build/source receipt plus its entire runtime
DLL/data closure, prepare the fresh OS-user lease, and start Map with only the
reviewed ordinary Atlas argv. It should reuse existing published asset recovery
and exact manifests, not rebuild a donor or transplant the PG database dump.
The old compile input receipts identify the required1.63GB base asset volume,
server animations/manifest, client caches and full FX input; a1202-byte startup
receipt is an input identity record, not the actual ready runtime asset tree.

Before any character attempt, require current Map/Db generations, loopback
endpoints, Db-owned6997/6989 listeners and their actual Map-owned channels.
Preserve the qualified loopback listener overlay/default policy and firewall
scope. Same local host/network access is not SQL/Auth identity: Map gets entity
ownership only from this DbServer's actual allocated container transfer. The
existing PG/Wine profile restores a historical private character; its separate
dump, account and identity do not qualify this fresh MSSQL realm.

The source has a possible read-only readiness observer: the original ServerMonitor
MapCon schema includes `Starting`, Map ID, IPs and UDP port, and `svrMonSendList`
serializes those actual current containers. A future bounded source-qualified
monitor client could request only Map status and privately validate the actual
registered Map entry becomes active/not-starting. It must not expose command
execution/relay/player requests, trust source names from the peer, export raw
container text or treat a schema/CRC mismatch as skippable. This observer is
unimplemented and is a separate protocol admission requirement, not a present
readiness proof. A Map-side ready-send flag alone must keep Db-ready-received
false.

Only after Map readiness and the new creation-session primitives are source/API
qualified can a new owner perform fresh Auth→matching empty list→one ordinary
empty-slot CHOOSE_PLAYER→actual server-allocated MAP_CONNECT offer. It stops
with a deliberately uninitialized container, no Map client connect/body, READY
or full-update ACK. Destroying sockets does not roll back that persistent
allocation. The entire fresh disposable SQL database must be retired after all
owned services stop; no historical UID/DBID reassignment or fabricated grant is
allowed. Normal client version/checksum reference admission stays unaccepted.

New work, once approved, needs only new user/profile/ACL/desktop/native-launch
and cleanup controls, plus exact new artifact/source admission and bounded
Map-ready observation. No old Auth-only/list/native/parser suite is replayed by
this proposal. Actual Windows account/profile APIs, DLL load, Map startup,
registration/readiness and character allocation all remain false here.
