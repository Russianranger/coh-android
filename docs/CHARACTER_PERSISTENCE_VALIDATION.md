# Character persistence validation

Status, 2026-09-27: **fresh fake-auth character creation, protocol logout/save,
PostgreSQL/game-service restart and exact-name short resume passed** in
[run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135).
Sustained gameplay and Android execution remain unvalidated. The prerequisite
[asset-backed template and Atlas Park run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
passed: all 56 generated outputs matched, followed by 62.235 seconds of
DB-confirmed map readiness. The existing generic-container tests and map
readiness alone do not establish game-character persistence.

The `Character persistence` workflow reuses those accepted comparison/map
reports and the matching reference/schema packages, stages a fresh runtime,
and runs `database/postgresql/tests/run_character_persistence.py`. It runs
on the continuation branch and relevant main pushes, or manually with explicit
input run IDs. Pull requests run tooling checks only. Credentials, full private
containers and the disposable database remain outside uploaded evidence.

## First hosted attempt: 36269025801

[Run 36269025801](https://github.com/Russianranger/coh-android/actions/runs/36269025801)
at `3d61ca929dc825ba9424279553797b66498df418` passed 55 Windows tooling checks
and 52 Linux checks (three Windows-only skips). Its runtime job reached fresh
DbServer/Atlas Park readiness, an empty diagnostic account, TestClient launcher
identity and a newly created character matching stock `-find` and independent
SQL. It then failed with `Unknown character status flags` before the currency,
protocol logout, saved-state or restart/resume phases.

The status line itself had no flags. The parser's multiline `\s*` could consume
its line ending and capture subsequent process output as flags. The correction
bounds matching to one line; unknown flags and mismatched identities still fail.
Preserved evidence: [artifact ZIP](postgresql-evidence/character-persistence-36269025801.zip)
and [report](postgresql-evidence/character-persistence-36269025801.json).
Artifact `10914634985`, 3,908 bytes, SHA-256
`99ca2a984344d479f5843f7ce0900d9fd8ee69e8162ed1b2d83b432ee1ce3a04`.
This attempt is failure evidence, not accepted persistence proof.

The correction is commit `cc3c82a87e2c3eabe1478b13ea031e3923423b10`. All 40
portable character tests passed locally; three Windows transport checks were
skipped. [Retry 36270565732](https://github.com/Russianranger/coh-android/actions/runs/36270565732)
used a fresh runtime and disposable database. It reached an independently
confirmed connected character on Atlas Park, proving the status-parser fix,
then failed because the creation branch text was missing from captured stdout.

TestClient is a GUI executable whose `WinMain` calls `newConsoleWindow`. If
`AllocConsole` succeeds, the preserved utility code reopens stdout/stderr to
`CONOUT$`, bypassing harness redirection. A proposed console preallocation
fix was rejected by its Windows GUI regression in
[run 36280623154](https://github.com/Russianranger/coh-android/actions/runs/36280623154):
`AllocConsole` still succeeded even with `CREATE_NEW_CONSOLE`. The runtime job
was skipped. The [failed regression record](postgresql-evidence/character-console-36280623154.json)
preserves that observation.

The replacement captures the actual TestClient console using an observer
attached to the owned client PID before releasing the launcher version exchange.
It holds the console across the short client exit and writes bounded private
snapshots. Creation/resume assertions and failure diagnostics remain required;
console overflow or loss must fail the experiment. Its first hosted Windows
regression ([36281169823](https://github.com/Russianranger/coh-android/actions/runs/36281169823))
stopped at observer startup with `WinError 5`; the game experiment was skipped.
The follow-up adds exact Windows API failure labels and opens the owned buffer
with read/write access for sizing. No console characters are written by the
observer. [Regression record](postgresql-evidence/character-console-36281169823.json).

Preserved retry: [artifact ZIP](postgresql-evidence/character-persistence-36270565732.zip)
and [report](postgresql-evidence/character-persistence-36270565732.json). Artifact
`10915916224`, 4,136 bytes, SHA-256
`676ad69d27d588844cbd92a2f989d092b585a7ff0b0db0e5d9880e04985b648f`.
It did not reach currency, logout, saved-state, restart or resume acceptance.

## First committed save and cleanup correction

[Run 36281372316](https://github.com/Russianranger/coh-android/actions/runs/36281372316)
uses commit `5d98c4dfaa4ce3a828e6359cf3fafefcb0f0d675`. Its Windows tooling passed
all 53 character checks, including the retained-console rapid-exit regression
and three actual named-pipe checks, plus 13 existing map checks. Linux passed
49 character checks and 13 map checks, with four Windows checks skipped.
The full runtime created and connected a fresh character, observed influence
12345 via the live server, requested protocol logout and verified committed SQL:
one parent, one `ents2`, seven powers and twelve costume parts, with `LoginCount`
1 and valid attribute references. It then failed during restart because forced
client-tree cleanup destroyed the console before the observer's final capture
(`GetConsoleScreenBufferInfo`, `WinError 233`). The observer is now finalized
before forced cleanup, after the independent logout/save proof. The short resume
observer still stays attached until its client exits naturally.

Preserved [full artifact](postgresql-evidence/character-persistence-36281372316.zip)
and [report](postgresql-evidence/character-persistence-36281372316.json): artifact
`10919515668`, 5,969 bytes, SHA-256
`e3bdcdf7b8e4f87a15048d0582db703d743b102e50fe19e2d769831c57ecbb51`.
That attempt observed the committed first-session save but did not validate
restart/resume. The corrected run below completed both remaining phases.

## Accepted hosted validation: 36282414135

[Run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135)
completed successfully on 2026-09-27 at 00:40:07 UTC using commit
`86e512e85c8350714bc7b58668bf11443dc164f8`. All eight recorded phases passed,
with an empty failure list and status
`fresh_fakeauth_character_persistence_short_resume_passed_gameplay_unvalidated`.

The fresh account created `TEST20636`, container ID 1, and connected to Atlas
Park. A normal command changed live influence to 12,345. Protocol logout was
independently confirmed in committed SQL before any forced client cleanup.
PostgreSQL, DbServer and MapServer restarted against the same database without
reseed/import. Selected parent and child rows and identity remained unchanged:
one `ents`, one `ents2`, seven powers and thirteen costume parts. Attribute
references and mappings also passed their checks.

The exact-name resume selected slot 0 with creation disabled, reached the scene
exchange and exited naturally with code 0. Selected rows remained identical;
`LoginCount` progressed **1 → 1 → 2** across logout, restart and resume. Both
console observers took final snapshots and exited 0 without forced termination.
The second connection is a short scene probe: processing of queued `CLIENT_READY`,
sustained gameplay and graceful whole-server shutdown are not established.

Windows passed all 54 character checks (including three real named-pipe and two
GUI-console checks) plus 13 map checks. Linux passed 49 character and 13 map
checks, skipping five Windows-only checks. All four jobs in the same-commit
[PostgreSQL regression run 36282414187](https://github.com/Russianranger/coh-android/actions/runs/36282414187)
also passed.

Preserved [complete artifact](postgresql-evidence/character-persistence-36282414135.zip),
[report](postgresql-evidence/character-persistence-36282414135.json) and
[acceptance/provenance record](postgresql-evidence/accepted-character-persistence-36282414135.json).
Artifact `10918974991`, 7,936 bytes, SHA-256
`0dafdeb556326fb743d49ffd4d4075fe989aee2975eec31857256fc5b424db99`.
The original source snapshot and accepted reference executables are unchanged.

## Run and inspect the harness

Use the `Character persistence` Actions workflow. Its reviewed default inputs
are schema run `36088012666`, reference run `36088012664`, gate run
`36176806895` and release asset `588984151`. It first runs the acceptance tests
on Linux and Windows, including three real Windows named-pipe transport checks.
The runtime job verifies the input workflows and artifact provenance before
creating its disposable database. Both the runtime staging and the driver's
private-copy verification inspect the full data set and can take several minutes.

Inspect `character-persistence-report.json` and `selected-diagnostics.txt` in
the `character-persistence-evidence` artifact. A pass requires status
`fresh_fakeauth_character_persistence_short_resume_passed_gameplay_unvalidated`,
an empty failure list, all recorded phases, unchanged selected parent/child
fields across restart/resume, and the expected `LoginCount` progression.
The report preserves runtime/schema/gate hashes, selected pipe events and SQL
snapshots. The original game source and reference executables remain unchanged.

The harness restarts PostgreSQL itself as well as DbServer and MapServer, using
the same cluster without reseeding or dump import. Its final process cleanup
is separate from the already-observed protocol logout. It does not validate
graceful whole-server shutdown or a sustained second player session.

## Protocol and acceptance contract

Use the same fixture-OFF reference binaries, accepted schema/attribute mappings,
reviewed assets and private disposable PostgreSQL database as the one-map test.
Do not import a player's account or saves. Preserve the upstream source pin
`0b75ade0c801735e10c5798f641948a45cc50488`; this first experiment needs no C changes.

## Runtime configuration

Reuse `database/postgresql/tests/run_one_map.py` staging, provider setup, service
readiness checks, process ownership, bounded logs and credential redaction. The
private `data/server/db/servers.cfg` must contain the generated PostgreSQL
`SqlDbProvider`, `SqlDbName` and `SqlLogin` settings, without the original MSSQL
`SqlInit` statement. Retain these diagnostic settings:

```text
AdvertisedIp 127.0.0.1
UseFakeAuth 1
UseQueueServer 0
BlockFreePlayersIfNoAccountServer 0
DefaultAccessLevel 9
```

Access level 9 permits a controlled currency change through the normal game
command protocol. This is a disposable diagnostic configuration. Continue using
the one-map harness's auxiliary-service suppression, including `-nostats`.

Start the same services and verify map 1 readiness before launching TestClient:

```text
DbServer.exe -start 0
MapServer.exe -nogui -nosharedmemory -nostats -db 127.0.0.1 -map_id 1 -udp 7001 -tcp 0
```

The pinned TestClient's `-fakeauth` requires `-db` or `-cs`, rejects `-auth`, and
skips AccountServer character-slot redemption. DbServer still reads its staged
account/product definitions. AuthServer, QueueServer and AccountServer are not
prerequisites for this narrow route; their actual functionality remains untested.

## First session: create, change, quit and wait for persistence

1. Create a local, duplex, message-mode Windows named-pipe server at
   `\\.\pipe\TestClientLauncher` **before** starting TestClient. Use one client
   at a time. Messages are NUL-terminated byte strings, not newline-framed JSON.
   Continuously drain messages so a blocked pipe cannot freeze the client.
2. Choose a fresh short ASCII account name and first prove no `ents` rows exist
   for it. The client generates the character name; do not assume a particular
   `TESTnnnnn` name. Launch from the staged runtime directory:

   ```text
   TestClient.exe -db 127.0.0.1 -fakeauth -authname CohPersist01 -dontpause -nosharedmemory -nolevel -TEAMACCEPT -FOLLOW -SUPERGROUPACCEPT -LEAGUEACCEPT
   ```

   The `-FLAG` arguments disable the named default behaviors. Do not use
   `-disconnect`: it prevents the main loop needed for launcher commands.
   Do not use `-cov`; default creation targets Primal Hero/Atlas Park.
3. Handle `VersionRequest: NULL` by returning the chosen diagnostic version as
   one NUL-terminated message, using the reference package's version where
   available. Record it. This direct fake-auth route sets `no_version_check`;
   it is not evidence of compatibility with another client build. Record the
   `PID:`, `Player:`, `MapName:` and `Status:` messages with timestamps and verify
   the reported PID belongs to this child process.
4. Require character creation to reach the map: a nonempty `Player:` name,
   Atlas Park `MapName:`, `Status: Running`, continued service health and an
   independently identified positive character ID for this account. Reject
   `ERROR`, `CRASH`, creation failure, timeout and SQL failure diagnostics.
   Neither `Status: Running` nor process exit 0 alone proves success.
   Require `-getstatus 3 ID` to identify that character on `MapId 1`, without
   `NoConnect` or `InMapXfer`, before requesting logout.
5. Send `CMD influence 12345` over the pipe. This becomes an ordinary MapServer
   command. Request `CMD debug RECORDED_CHARACTER_NAME` and require the server's
   live character report to identify the player/account and show `Current cash:
   12345 (Influence)`. A DbServer container may be stale until a save; its value
   alone is not evidence of the live change. Do not write the currency directly
   in SQL or force a pre-logout save to satisfy this gate.
6. Send `CMD quit`. The client calls `commSendQuitGame(0)` and reports
   `QuitNow:`. **That message only confirms the request; it is not a save ACK.**
   Keep the map and database services alive until server logout/unload evidence
   and independent committed SQL reads confirm the saved character, currency
   and child rows. A forced TestClient termination is a disconnect test, not a
   successful protocol-logout test.
   The stock TestClient's disconnect path can call `quitToLogin`, then
   `FatalErrorf("Booted back to login screen")`; its `windowExit` also reports
   `Status: ERROR` and exits -1. Any exception for this exact client shutdown
   path must be limited to after the recorded quit request. Unrelated failures,
   service errors, missing SQL persistence, or earlier client errors still fail.
7. Once persistence is observed, capture the first SQL snapshot and stop only
   the owned test processes. Restart DbServer and Atlas Park against the same
   database, without reseeding, importing a dump, or replacing attribute maps.
   Confirm readiness and saved rows before resuming.

The actual logout path packages the initialized owned entity through
`svrSendEntListToDb`, then sends `dbSendPlayerDisconnect`. Therefore a timer,
client exit, logout log, or unlocked container alone cannot replace the committed
SQL check. Use a bounded wait and report timeout as failure.

Useful stock queries, with separate argv entries and a 10,000 ms timeout:

```text
MapServer.exe -db 127.0.0.1 -dbquery -timeout 10000 -find 3 Name "RECORDED_CHARACTER_NAME"
MapServer.exe -db 127.0.0.1 -dbquery -timeout 10000 -get 3 RECORDED_CHARACTER_ID
MapServer.exe -db 127.0.0.1 -dbquery -timeout 10000 -getstatus 3 RECORDED_CHARACTER_ID
```

List 3 is `CONTAINER_ENTS`. `-find` returns `container_id = N`; `-get` can load
an offline container, so its existence is not proof that the player is online.
Keep full container payloads private; publish selected diagnostic fields only.
`-getstatus` reads only an already loaded container. Following a confirmed
connected state, `NoConnect` or `invalid container request` can support logout
evidence (the latter can mean the container unloaded), but neither is sufficient
without a surviving independently committed SQL row and healthy services.

## Second session: exact-name resume with creation disabled

The supported stock command is **order-sensitive**:

```text
TestClient.exe -db 127.0.0.1 -fakeauth -authname CohPersist01 -dontpause -nosharedmemory -justlogin -character "RECORDED_CHARACTER_NAME"
```

`-justlogin` clears the mode mask, including CREATE; the following `-character`
enables RESUME. This also leaves STAY_CONNECTED off, so the stock executable
returns after the resume/scene exchange instead of entering its command loop.
It cannot provide a second sustained session or a launcher-controlled second
logout in this mode. Label this result a **short resume probe**, and allow the
server to finish any disconnect save before taking the final snapshot.

The mode table's first three names are empty: `-CREATE`, `-RESUME` and `-STAY`
are not supported toggles. A normal `-character NAME` retains CREATE fallback.
Do not describe that command as a no-fallback test.

Acceptance for the short probe requires all of the following:

- Exact `Found character NAME in slot N` evidence; reject `Unable to locate
  character`, even if the process exits 0 or reports `Running`.
- The resume branch and scene response evidence, including the returned map and
  player identity, without `simulateCharacterCreate()` or creation diagnostics.
- The same account, character ID and name; no extra character rows.
- The saved value 12345 and selected stable parent/child fields survive service
  restart and resume. Record `LoginCount` as progression evidence, not a stable
  field. Require server-side evidence before claiming active gameplay: the
  short probe can exit before a queued `CLIENT_READY` packet is processed.

The next [sustained-session validation](SUSTAINED_SESSION_VALIDATION.md) adds a
small TestClient-only `-resumeonly` option that disables CREATE while retaining
STAY_CONNECTED, fails explicitly if the exact requested character is absent,
and reports the actual server-provided character ID. It builds a separately
identified diagnostic client and validates it against the accepted server runtime;
the current reference package is not modified in place. Hosted acceptance of
that sustained-session gate is pending.

## SQL evidence and scope

Derive actual table/column names from the accepted `ents.template`, rather than
assuming a different shard schema. Query by the recorded `ContainerId`; order
child rows by their schema keys. Suggested comparisons:

| Data | Compare |
| --- | --- |
| `ents` | `ContainerId`, `AuthId`, `AuthName`, `Name`, `Class`, `Origin`, `Level`, `ExperiencePoints`, `InfluencePoints`, character description and creation identity |
| `ents2` | One matching child record; selected build/origin/faction fields such as `CurBuild`, `originalPrimary`, `originalSecondary`, `PraetorianProgress` |
| `powers` | Nonempty rows; category/set/power IDs, bought levels, build and unique IDs |
| `costumeparts` | Nonempty selected costume rows; part/geometry/texture/color identifiers and row keys; do not require optional `supercostumeparts` rows |

Do not compare every serialized byte: login counters, active timestamps, play
time, position, health/endurance, power recharge times and login-generated
rewards can change legitimately. Define the selected fields before execution;
record unexpected changes rather than broadening exclusions to force a pass.
Check every selected child references the same character and that attribute IDs
use the unchanged accepted mappings.

Publish redacted phase results, source/runtime/schema hashes, timestamps,
recorded character identity, selected SQL snapshots and failure diagnostics.
This would establish only the exercised fresh fake-auth character path. It would
not establish custom-client compatibility, combat, transfers, auxiliary services,
graceful whole-server shutdown, Android execution or performance.

## Source basis

Paths below are relative to the repository's immutable `upstream/ouroboros/`:

- `Utilities/TestClient/src/main.c`: `checkArgs`, `flag_names`,
  `handleLauncherMessage`, `checkPipe`, creation/resume branches and main loop.
- `Utilities/TestClient/src/testClientInclude.h`: `TestMode` bits.
- `Utilities/TestClient/src/PipeClient.c`: pipe name, message mode, NUL framing.
- `Utilities/TestClient/src/testClientCmdParse.c`: `handle_quit`.
- `Game/src/gameComm/initClient.c`: `gCreateLocation`, `choosePlayerWrapper`,
  `checkForCharacterCreate`, fake-auth slot-redemption branch.
- `Game/src/gameData/randomCharCreate.c`: `simulateCharacterCreate`, `genName`.
- `Game/src/clientcomm/clientcomm.c`: `commReqScene`, `commSendQuitGame`.
- `DBServer/src/clientcomm.c`: `genFakeAuthId`, `handleLogin`,
  `determineStartMapId` (Primal Hero selects Atlas Park map 1).
- `MapServer/src/svr/svr_player.c`: `svrCompletelyUnloadPlayerAndMaybeLogout`,
  `svrSendEntListToDb`, `playerEntCheckDisconnect`.
- `MapServer/src/cmdparse/cmdserver.c`: `SCMD_INFLUENCE` uses `ent_SetInfluence`.
- `MapServer/src/dbcomm/dbquery.c`: `-find`, `-get`, timeout handling.
- `DBServer/src/status.c`: `entStatusCb` (`NoConnect`, `InMapXfer`, map IDs);
  `DBServer/src/container.c`: `containerSendStatus` checks loaded containers.
- `data/server/db/servers.cfg`: fake-auth and auxiliary-service defaults.

Generated schema basis: the `data/server/db/templates/ents.template` payload in
`docs/schema-generation-evidence/accepted-36088012666.zip` (inner schema ZIP).
