# Atlas instance transfer validation

Status: **passed** in [run 36297542986](https://github.com/Russianranger/coh-android/actions/runs/36297542986)
at `5f2c561058a186de59d3f27301eea210bd4bb66d`; terminal success was recorded
2026-09-27 05:56:06 UTC. All 15 transfer phases and the separate sustained regression passed.
The earlier accepted
[sustained-session baseline](SUSTAINED_SESSION_VALIDATION.md#accepted-hosted-validation-36295176484)
is run `36295176484` at `4e8058c3ffe20acda61b55023202d409ed1d0df1`.
It proved exact-name resume, missing-name refusal, restored live state, 66.953
seconds connected and a second protocol save. This gate adds a round trip
between two owned, prestarted Atlas instances before that final save.

## Scope and map identity

The pinned `data/server/db/maps.db` defines map 101 with `BaseMapID 1`.
DbServer and the client inherit the Atlas map path from map 1, so both instances
use the reviewed assets. Map 1 uses UDP 7001; the owned clone uses UDP 7002.
The clone starts after the service restart, shortly before the transfer legs.
Its manual startup disables idle expiry and does not use Launcher preload mode.

MapName and client base-map metadata are shared by the two instances. The client
instance number is also distinct from the database MapId. Destination proof must
therefore combine:

- An exact numeric map-container status response for the requested MapId,
  registered at the expected loopback endpoint, with current heartbeats.
- Independent character status showing the destination MapId and SmapId,
  connected and without `InMapXfer`.
- A fresh processed player update after the successful client handoff, tied to
  the new network peer and the original character ID and exact name.
- A fresh live currency response after destination arrival.

The diagnostic client retains its initial resume marker. A separate transfer
marker records a monotonic epoch only after successful `doMapXfer`, followed by
a processed steady `SERVER_UPDATE` on the new connection. Initial scene packets,
an old resume marker, an unchanged MapName, or a failed handoff cannot satisfy it.
The immutable upstream trees and accepted server executables remain unchanged.

## Acceptance

1. Complete the existing fresh creation, live influence 12,345, protocol save,
   same-cluster/service restart, missing-name refusal and sustained exact-name
   resume checks using the accepted stock runtime and separate diagnostic client.
2. Start the owned Atlas clone and independently require both map containers
   ready on their assigned ports. Retain the same client process and account.
3. Send `CMD mapmove 101`. Require transfer epoch 1, the original player identity,
   the actual clone endpoint, connected MapId/SmapId 101, current map heartbeats
   and a fresh live response showing influence 12,345. Independently wait for
   committed selected SQL with the original identity, influence 12,345 and
   LoginCount 2.
4. Send `CMD mapmove 1`. Require fresh transfer epoch 2 and the equivalent return
   evidence for MapId/SmapId 1 and UDP 7001. Each leg is bounded; a connection
   failure, unexpected identity or stale proof fails acceptance. Independently
   require the same committed selected SQL and LoginCount 2 after this leg.
5. Change influence to 23,456 through the game command protocol and verify it
   live. Request protocol logout and require independent committed SQL before
   forced client cleanup. Final identity and selected parent/child rows must
   match the first save except for that currency change. Require LoginCount 2,
   unchanged attribute mappings and exactly the original character inventory.
6. Finalize console evidence and verify owned services remain healthy before
   cleanup. Preserve selected phase, endpoint, player and SQL evidence.

The final LoginCount must show only the first login and resumed login; map
transfers must not add another login. The protocol quit notification confirms a
request, so it is never accepted as a save acknowledgement on its own.
The ordinary transfer sends a save without a commit acknowledgement. Independent
SQL polling is therefore required on each leg. The resumed login can first reach
committed SQL during the outbound transfer; a pre-transfer SQL count of 1 alone
does not indicate another login is needed.
These per-leg queries establish the currently committed selected state. They do
not acknowledge or timestamp a new identical transfer write. The later distinct
change to 23,456, followed by protocol logout and independent SQL before cleanup,
provides the fresh final-save evidence.

## Hosted execution and provenance

The `Character session and Atlas transfer` workflow builds one diagnostic
TestClient and runs separate sustained and transfer experiments against those
same bytes. The transfer case passes `--map-transfer` and requires its distinct
success status plus `map_transfer_validated`. A sustained-only pass cannot
satisfy the transfer gate. Both cases retain the existing source/package,
schema, template, reviewed-asset and server-binary verification.

The transfer artifact is `character-transfer-evidence`; the sustained regression
retains `character-session-evidence`. Only selected redacted diagnostics and
reports are published. Raw runtime data, credentials and full container payloads
stay in the disposable private test directory.

Hosted tooling passed all 119 checks on Windows and 114 on Linux, with five
Windows-only skips on Linux. This includes 68 Windows character checks, 13 map
checks and 38 diagnostic source/package checks. The latter exercise the actual
patched C selection, transfer and update helpers on both platforms.

## Accepted hosted validation: 36297542986

`TEST59440`, container ID 1, remained in the same resumed client process for
both transfers. Before transfer, 12 connected samples covered 64.953 seconds,
with a maximum gap of 6.234 seconds. Clone 101 was independently observed
unstarted, then ready on its assigned port before the first transfer.

| Leg | Fresh epoch | Connected peer | Independent MapId / SmapId | Live influence |
| --- | ---: | --- | --- | ---: |
| Atlas 1 → clone 101 | 1 | 127.0.0.1:7002 | 101 / 101 | 12,345 |
| Clone 101 → Atlas 1 | 2 | 127.0.0.1:7001 | 1 / 1 | 12,345 |

Each processed player update carried the original ID/name and a newly connected
peer. Both maps had current heartbeats, and independent arrival and settled
character status showed the requested destination without `InMapXfer`. The
received base map was 1 on both legs; instance numbers 2 and 1 were recorded
separately from the database map IDs.

Selected committed identity and parent/child rows stayed unchanged: one `ents`,
one `ents2`, 10 powers and 13 costume parts. LoginCount progressed
1 → 1 → 1 → 2 → 2 → 2 across first save, restart, missing-name refusal,
outbound arrival, return arrival and final save. Both arrival snapshots were
identical. After return, a fresh live command changed influence to 23,456;
protocol logout then committed that sole selected-data change before forced
cleanup. All three console observers finalized successfully and both maps
remained ready before cleanup.

The [raw report](postgresql-evidence/character-transfer-36297542986.json),
[complete artifact](postgresql-evidence/character-transfer-36297542986.zip) and
[acceptance/provenance record](postgresql-evidence/accepted-character-transfer-36297542986.json)
are preserved. Artifact `10924242591` is 15,804 bytes, SHA-256
`260589aa765e330a891f8769fe33108c22769c829d122110e4b2098041a5ce42`.
The [build manifest](postgresql-evidence/resume-testclient-build-36297542986.json)
and [source receipt](postgresql-evidence/resume-testclient-source-36297542986.json)
identify the separate diagnostic executable, SHA-256
`94c87a8166c1be8847a5fe106230eb894eb7543e628d8ed167cc09068827c856`.

The same workflow passed the separate sustained-session regression using those
same diagnostic bytes; its [report](postgresql-evidence/character-session-36297542986.json)
and [artifact](postgresql-evidence/character-session-36297542986.zip) are preserved.
The [stock-client regression 36297326643](https://github.com/Russianranger/coh-android/actions/runs/36297326643)
and all four [PostgreSQL jobs 36297326629](https://github.com/Russianranger/coh-android/actions/runs/36297326629)
also passed at implementation commit `3848133e5e644f4c166cc9e7f3e027288d06c2fd`.
The successful transfer retry only corrected the Windows test fixture and
recorded its failure; runtime code was identical between these two commits.

## First hosted attempt: tooling correction

[Run 36297326622](https://github.com/Russianranger/coh-android/actions/runs/36297326622)
at `3848133e5e644f4c166cc9e7f3e027288d06c2fd` stopped in Windows tooling.
All 68 character checks and 13 map checks passed there, as did the package and
noncompiled source checks. The actual-C behavior fixture failed to compile with
the runner's MinGW compiler; source inspection found an unconditional POSIX
`arpa/inet.h` include. Linux passed all 114 applicable checks, with five
Windows-only skips.

The fixture now uses Winsock headers, initialization and linking on Windows,
retains POSIX networking on Linux, and includes captured compiler diagnostics in
future failures. All 38 diagnostic checks still pass locally. This correction
does not change the client overlay, server runtime or transfer harness. The
[failed tooling record](postgresql-evidence/character-transfer-tooling-36297326622.json)
is preserved. The diagnostic build and both runtime experiments were skipped;
this attempt provides no transfer or sustained runtime acceptance.

This pass establishes the round trip between two prestarted Atlas instances.
It does not establish new-zone asset coverage, mission transfers, automatic
Launcher startup, combat, rendering/custom-client compatibility, auxiliary
services, graceful whole-server shutdown or Android execution. No APK result is
claimed. The next implementation priority is the
[M2 Thor diagnostic APK](ANDROID_PORT_PROPOSAL.md); these remaining server and
gameplay scopes are separate work, not prerequisites for that diagnostic APK.

## Source basis

Paths below are relative to the pinned source snapshots:

- `upstream/i24/data/server/db/maps.db`: clone 101 and its base-map relationship.
- `upstream/ouroboros/DBServer/src/dbinit.c`: clone map-path inheritance.
- `upstream/ouroboros/DBServer/src/status.c`: exact map and player container status.
- `upstream/ouroboros/DBServer/src/launchercomm.c`: Launcher-specific transient flags.
- `upstream/ouroboros/MapServer/src/cmdparse/cmdserver.c`: `SCMD_MAPMOVE` and
  `XFER_STATIC` selection without best-map substitution.
- `upstream/ouroboros/Utilities/TestClient/src/main.c`: client map-transfer loop.
- `upstream/ouroboros/Utilities/TestClient/src/externs.c`: diagnostic-client
  decoding of received base-map and instance metadata.
- `upstream/ouroboros/Game/src/clientcomm/clientcomm.c`: scene, ready and steady
  server update processing.
- `upstream/ouroboros/Game/src/gameComm/initClient.c`: client handoff completion.
- `upstream/ouroboros/Game/src/clientcomm/dbclient.c`: received destination endpoint;
  the wire database MapId is parsed without being retained in that client state.
- `upstream/ouroboros/MapServer/src/dbcomm/dbmapxfer.c` and `dbcontainer.c`:
  ordinary transfer save request without a commit callback.
- `upstream/ouroboros/MapServer/src/container/containercallbacks.c`: LoginCount
  increments for login, excluding map transfers and demand loading.
- `upstream/ouroboros/MapServer/src/svr/svr_player.c`: save delivery and idle expiry.
