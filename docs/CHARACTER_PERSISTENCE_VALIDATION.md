# Character persistence validation

Status: **implementation awaiting hosted execution**. The prerequisite
[asset-backed template and Atlas Park run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
passed: all 56 generated outputs matched, followed by 62.235 seconds of
DB-confirmed map readiness. The existing generic-container tests and map
readiness do not establish game-character persistence.

The `Character persistence` workflow reuses those accepted comparison/map
reports and the matching reference/schema packages, stages a fresh runtime,
and runs `database/postgresql/tests/run_character_persistence.py`. It runs
on the continuation branch and relevant main pushes, or manually with explicit
input run IDs. Pull requests run tooling checks only. Credentials, full private
containers and the disposable database remain outside uploaded evidence.

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

For a later complete second session, add a small TestClient-only `-resumeonly`
option that clears CREATE while preserving STAY_CONNECTED, fails explicitly if
the exact requested character is absent, and reports the actual server-provided
character ID. That would require a newly identified reference build and its
normal regression gates. Do not patch the current reference binaries in place.

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
