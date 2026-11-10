# On-demand zones and a pre-loaded spare zone server (design, 2026-11-04)

Goal: any character can be played in any of the 66 static zones, and zone
doors, trains, instances and missions work, on a device with at most 16 GB of
memory. Never start everything (the user's PC "start everything" script needs
more than 30 GB). Studies and evidence: [HANDOFF-X86.md](../../HANDOFF-X86.md),
"Other zones".

## What the game does and what we change

| Step | Stock deployment | Device today | Design |
|---|---|---|---|
| A map is needed (login, door, train, mission) | DbServer `launcherCommStartProcess` sends `mapserver.exe ... -map_id N -cookie C` to a Launcher | No Launcher: a static zone's container is **deleted** (mapxfer.c:312), missions fail | DbServer publishes `map-N-C.json` to the supervisor (`database/external-maps`, patch `patches/external-maps/0001`), keeps the map `starting`, never deletes a static zone |
| Process start | Launcher runs the command | Supervisor pre-starts Atlas (1), King's Row (5) itself | Supervisor starts (or assigns a spare to) map N with cookie C, in its own owned process group |
| Ready | MapServer registers (cookie), loads, `READY_FOR_PLAYERS` | same | same; waiting players continue |
| Failure | Launcher crash report → delink | — | Supervisor delinks (`MapServer.exe -dbquery -delink N`): waiting players get "MapFailed" instead of a hang |

## Request record (format 1)

`map-<id>-<cookie>.json`, written to a temporary name and renamed:
`format, sequence, map_id, cookie, base_map_id, is_static, transient,
dont_auto_start, preload_transient, db_process_id, map_name, mission_info,
command`. Strings are JSON-escaped; a field that would overflow refuses the
request instead of truncating it. Gate: `COH_WINE_DB_EXTERNAL_MAPS=1` with
manual Atlas mode on and an existing `COH_WINE_DB_EXTERNAL_MAPS_DIR`; any other
value is refused (no maps start) rather than silently falling back.

## Supervisor responsibilities

1. Poll the request directory on the existing server-health cadence; accept a
   record only from the owned DbServer (`db_process_id`) and only once per
   `(map_id, cookie)`.
2. Start `MapServer.exe -nogui -db 127.0.0.1 -nosharedmemory -nostats -udp
   <free port> -tcp 0 -map_id N -cookie C -donotautogroup ...` plus
   `-transient` when the record says so, never the record's `-launcher`.
   Ports: 7001 upward, as `-udp -1` would choose.
3. Zone data: one shared tree for every on-demand zone, laid out like a PC
   install (shared read-only folders + one private `bin`, `geobin`, `server`),
   so a spare can do its shared loading before it knows its zone. Per-zone
   files are already separated by path (`geobin/maps/<zone>`,
   `server/maps/<zone>/*.bcn`). Prepared bins are trusted so concurrent
   servers do not rewrite them. Atlas and King's Row keep their own verified
   trees until the shared tree is proven; a second server writing into the
   Atlas tree would invalidate its sealed cache (compare 0.13.50 session 2).
4. Timeout and failure: a process that exits before registering, or is not
   ready within its budget, is stopped and the map delinked.
5. Memory policy (defaults, all settings in the app): the current zone; the
   zone just left stays resident for one trip back, then exits; at most one
   pre-loaded spare; missions and instances exit when empty (`-transient`,
   the DbServer's mission shutdown). Report each process's `rss_kib`.
6. Character select: the client waits 90 s for its map. Pre-start the saved
   zone of the most recently played character while the client starts
   (likely choice), and start others on demand; a client option to wait longer
   (`-notimeout`) needs checking in production mode.

## Pre-loaded spare zone server (MapServer patch, next)

The MapServer only learns its map in `connectToDbserver` → `dbRegister`
(svr_init.c:2137), after 198-211 s of shared loading on the Thor; the map's
own part is 33-49 s. A spare started with a new flag (for example
`-armportspare <file>`):

- runs every shared phase, then blocks before `connectToDbserver` until the
  supervisor writes its assignment (map id, cookie, UDP port);
- sets `db_state.map_id`, `local_server=0` (`parseArgs2` otherwise defaults to
  edit mode, and `lock_doors` depends on it), re-runs the `base_map_id` /
  `instance_id` lookup from `staticMapInfosLoad` (staticMapInfo.c:590-605),
  then continues;
- optional: move `gridCacheSetSize` after registration so static maps get
  their larger grid.

Expected: a zone or mission ready about 35-50 s after it is needed instead of
about 4 minutes, at the memory cost of one extra MapServer. Measure that cost
(0.13.53 `rss_kib`) before turning it on by default. The stock shared-memory
mode (`ParserLoadFilesShared`) could let processes share the parsed data but
is untested under Wine/FEX; a later experiment.

## Shared memory (owner's choice 2026-11-04: first; spare server on hold)

Device figures (0.13.53, rss_kib): client 2.1-2.3 GB, Atlas MapServer 1.8 GB,
King's Row 1.9 GB, DbServer 0.4 GB, total 6.2-6.3 GB with both zones; Android
reported 6.9 GB available when King's Row started. A spare server would idle at
most of another 1.9 GB. 0.13.54 adds the switch (`COH_SHARED_HEAP`, app option
"Shared server memory", off; CI input `shared_heap`), per-server PSS every 30 s,
and the native decision from each MapServer console. CI starts only Atlas, so CI
shows whether the shared heap reserves and Atlas still passes; the second
server mapping the first one's data is a device measurement (King's Row
`sequencer_info` 60 s + `definitions` 45 s of its 143 s are the candidates).


Every device MapServer runs with `-nosharedmemory`, so each one parses and holds
its own copy of the shared definitions (the 198-211 s shared phase, and most of
King's Row's 1.7 GB peak). The stock deployment loads them once into a shared
heap (`ParserLoadFilesShared`, `reserveSharedHeapSpace`) that later MapServers
map instead of parsing; `-tsr` exists only to keep that heap alive
(`checkTsr`, svr_init.c:1810). If that works under Wine and FEX, it would cut
both the start time and the memory of every zone after the first, which the
spare server does not. It needs fixed-address mappings shared across Wine
processes; untested, and earlier notes kept it off for the ARM MapServer study
(MAPSERVER-STARTUP-60S.md). Measure after the 0.13.53 `rss_kib` figures: two
MapServers, shared heap on, in CI and then on the Thor.

## Owner's decisions 2026-11-05 and the plan from here

User (0.13.54 test, 22:46 CST): a zone trigger (door, tunnel) should show a
loading screen and take the character out of the world; the monorail should
board immediately, then load; open the whole zone list; full screen 1280x720,
launcher options in a floating movable touch icon, controller mapping like the
trasc launcher; "The biggest priority is nailing the map/zone server ... for
seamless travel with reduced overhead." Answers: **current zone + one spare**
(two zone servers); **open all zones now** under the game's own rules, NPC
pathing following zone by zone.

Evidence (0.13.54 export 20261105-043833): King's Row cold 191 s (Python 53 s
+ native 138 s) with the player waiting at the station; trip departure → ready
on the new map 30.6 s / 30.9 s (about 12 s hand-off + 18 s client map load);
return to resident Atlas 9 s; RSS ≈ PSS per server (Atlas 1.78 GB, King's Row
1.90 GB: nothing shared); device total 16.0 GB, 10.2 GB available at setup.

Stock zoning already does what the owner asks (dbmapxfer.c): at
MAPXFER_TELL_CLIENT_IDLE the player is controlsFrozen, UNTARGETABLE_TRANSFERING
and INVINCIBLE_TRANSFERING; the client gets SERVER_MAP_XFER_WAIT and shows its
load screen at once (commServerWaitOK); the DbServer keeps the player waiting
(waitingEntities.c) until the map is active or fails ("MapFailed" →
dbUndoMapXfer, player back in the old map). No client timeout applies while
waiting (the 60 s DEFAULT_TIMEOUT phases start after SERVER_MAP_XFER). The
station queue (patches/monorail, "Stay near the station") was a workaround for
multi-minute starts and is dropped in stock travel mode.

Steps:
1. **Stock travel** (`COH_STOCK_TRAVEL=1`, guest `zone_travel.py`): no monorail
   environment (stock door/monorail/tunnel path); the external-maps DbServer
   publishes each start; the supervisor's start policy starts it with the
   cookie (`-cookie C`, no `-launcher`), at most two zone servers (a third
   request stops the idle resident zone, never the current or a starting one);
   a start not ready in 900 s or that exits is stopped and delinked. Arrival is
   read from the character status (map changes while connected). Trees: Atlas
   (1, 101), King's Row (5), then one shared tree for every other zone.
2. **Pre-loaded spare** (MapServer layer like trusted bins, Thor server only):
   shared loading first, then block before `connectToDbserver` until assigned.
3. **NPC pathing** for every zone in CI; door records.
4. **Interface** (Java first): full-window immersive view, floating gear with
   the launcher options, controller mapping ported from trasc
   (ControllerInput/Manager/Dialog), mouse wheel; then true 1280x720
   (client-launcher.c `-screen 800 600`, Xtigervnc geometry, Java limits).

## Step 2 plan: one MapServer layer for the spare and a CI trip

Native changes reach the device only through the Thor (test) server: the
shipping MapServer's monorail receipt pins `CONTRACT` and its four patched files
(`native_monorail_contract.py`), so the monorail layer itself must not change.
Precedent: trusted bins (95be44b46) — a patch under `patches/mapserver-*` applied
by `armport/scripts/prepare_server_metrics_source.py` after 0119, its files added
to the metrics receipt, guest admission in `armport_server_metrics_contract.py`.

One layer `patches/mapserver-zone-travel/0001`, default off, env-gated:
- `ARMPORT_SPARE_FILE=<path>`: run every shared phase, then block before
  `connectToDbserver` (svr_init.c:2137) until the file names map id, cookie
  and UDP port; set `db_state.map_id`, `local_server=0`, redo the
  `staticMapInfosLoad` base/instance lookup, continue. Guest: one spare per
  session beside the current zone (owner's choice), assigned by the start policy
  instead of a cold start; a new spare warms at low priority after each trip.
- `ARMPORT_TEST_TRAVEL=<map_id>` (CI only): after the THORHERO player has been
  ready 30 s, one `DoorAnimEnter(e, NULL, nowhere, map_id, NULL,
  "LinkFrom_Monorail_ParagonCity", XFER_STATIC, errmsg)` — the stock path a
  monorail stop takes — so CI covers request → start → transfer → arrival →
  save in the destination → reopen there.
- Zoning events for any static map (today `identity` admits only 1/5/101).

## 0.13.68: the saved zone starts beside the client; the spare layer is built (2026-11-10)

Thor 0.13.66 (export 20261110-213045): Mercy Island took 113 s to prepare and
227 s to start, all after Enter Game; the console shows every shared load
(174 s) finishing before "Connecting to dbserver", so the design above still
holds. Two parts, built separately:

1. **Early start of the saved zone** (`COH_EARLY_ZONE=1`, app option "Start my
   saved zone while the game starts (Reopen)", on by default; CI input
   `early_zone`). `begin_early_zone` starts the saved character's own zone at
   the session's map stage, before the client starts, with no cookie:
   `registerDbClient` (DBServer/src/dbinit.c) refuses a cookie only when the
   server sends one that differs, so a static zone started by hand registers
   as Atlas Park and King's Row did in 0.13.50-0.13.58. A request the game
   makes for it while it loads is the session's own (`session_flow`): nothing
   is started twice and nothing is delinked. `_tick_early_zone` follows it:
   ready (first completed tick), asked for by the game, or failed. A failure
   after the game asked delinks that request, so the game reports it and the
   next Enter Game starts the zone the ordinary way.
   Limits: only a saved character (a new one has no zone yet), only the lowest
   map id of a world (a hero saved in Atlas Park 101 may be sent to 1), no
   other zone server running, and MemAvailable of at least 3072 MiB (0.13.57
   started a second zone beside the client and Android closed the app; one
   zone beside the client is what 0.13.50-0.13.56 ran). The report's
   `initial_zone.early_start` gives the decision and the times.
   This needs no MapServer change and helps only the first zone of a Reopen.
2. **Spare layer for trips** (`patches/mapserver-zone-travel/0001`,
   `ARMPORT_SPARE_FILE`): the wait before `connectToDbserver` described above,
   for a zone that is not known in advance (a trip's destination, a new
   character's starting zone, a mission). Built into the instrumented
   MapServer and covered by the host fixture; no supervisor uses it yet. The
   supervisor part (one spare beside the current zone, assigned at the
   DbServer's request, a new spare after each trip) needs the 0.13.67 memory
   trace first.

## Data every zone needs (later)

- NPC pathing graphs (`.bcn`): only Atlas and King's Row have them (asset pack).
  Generate the others in CI, or on first visit, and seal them.
- Door records: mission doors and contact lookups use doors reported by static
  maps that have run (`Doors.db`, none shipped). Produce one in CI by running
  every static zone once.
- A CI zone survey: start each of the 66 static maps once (pass/fail, time,
  missing data, beacon status).

## Milestones

1. DbServer hook built and qualified (startup-bundle pipeline), off by default;
   supervisor observes requests and delinks the ones it cannot serve; starts
   King's Row on request.
2. Any static zone on demand; generic saved destination (remove the 1/101/5
   checks); last-played zone pre-start.
3. Pre-loaded spare (MapServer patch), memory permitting.
4. Missions and instances; door records; pathing graphs.

## Status

- Done: the two studies; the DbServer overlay and patch with
  `armport/tests/external_map_requests.py` (5 modes, escaped records, overflow
  refused, patch applies to the staged sources; POSIX stand-in, and MSVC with
  the real Win32 API inside the Windows workflow).
- Done (not yet run in CI): the build pipeline. The device DbServer is
  `startup-dbserver.exe` + `startup-dbserver-manifest.json`, role
  `manual_atlas_dbserver_levelup_ui_repair` (0.13.36 donor: 1,664,512 bytes,
  `ea1d43d7…`). `armport/server/package_external_maps_dbserver.py` stages the
  same five layers (PostgreSQL → Wine ODBC → manual Atlas → cancelled-child save
  → level-up read; their receipts equal the donor manifest's) and adds this one
  as a sixth receipt (`external-maps-dbserver-build-input.json`, role
  `manual_atlas_dbserver_external_maps`). `.github/workflows/armport-external-maps-dbserver.yml`
  (dispatch only) runs the retained native contracts plus ours under MSVC,
  builds only DbServer (2 compiler processes) and packages it. Local staging of
  the full source tree passes. The guest accepts the role only with the exact
  receipt digest above the exact shipped level-up layer, installs it inert
  (`external_maps.enabled: false`) and keeps the level-up contracts
  (`armport/tests/test_external_maps_dbserver.py`).
- Done: APK admission behind `build_thor_apk.py --external-maps-dbserver DIR`
  (`stage_app_assets.external_maps_dbserver`): only `startup-dbserver.exe` and
  its manifest change, the package must validate and sit on the donor's exact
  level-up executable and ancestry; recorded as `armport_external_maps_dbserver`.
- Done (milestone 1, observe and delink): `android/guest/external_map_supervisor.py`,
  shipped as a guest dependency and inert unless `COH_EXTERNAL_MAPS=1` and the
  installed DbServer is the external-maps layer. The character server then
  gives the DbServer a fresh private request directory
  (`state/external-map-requests-<session>`), reads each record once (exact
  fields, ASCII, size bound; only after the DbServer's own acknowledgement and
  request marker line; one `db_process_id`; increasing sequence), leaves the
  maps its flow starts itself alone (1; zoning: 1, 101, 5) and delinks every
  other request, one owned `-dbquery -delink` at a time (16 at most per
  session). Anything unexpected stops it instead of acting. The record
  command's game options are checked against an allowlist and the start
  arguments are planned (`-cookie`, no `-launcher`, `-locale 0` dropped), but
  no map is started yet. `armport/tests/test_external_map_supervisor.py` reads
  records written by the overlay itself (POSIX stand-in).
- Built (2026-11-04, run 41883310382 at b169c5e84, first run through the
  workflow's narrow push trigger): MSVC contracts PASS (the request records
  under the real Win32 API, plus the retained launcher-wait, cancelled-child
  save and level-up contracts); `DbServer.exe` 1,667,584 bytes (level-up donor
  1,664,512), sha256 `5d9b2f014be4f8e298cfa8ba73cffb336fd632a5a57699bfa3ff317407d7f187`,
  no unresolved imports; artifact `armport-external-maps-dbserver` (90 days).
  Not run in a guest yet.
- Ready (not yet run): CI admission. The CI guest's retained 0.10.0 donor has
  no startup DbServer (it runs the stock package DbServer, which waits for a
  Launcher; the device runs the manual Atlas level-up lineage). Runtime input
  `external_maps_run_id` downloads that run's `armport-external-maps-dbserver`,
  `interactive_host.py --external-maps-dbserver` checks the run (this workflow,
  success, head = the package's commit), adds the two payloads
  (`stage_app_assets.external_maps_dbserver(ci_runtime=True)`; the package's own
  five-layer receipt is the contract and the guest re-checks it) and sets
  `COH_EXTERNAL_MAPS=1`. The 'startup detail' notices carry `external_maps`
  (requests, decisions, delinks, manual Atlas acknowledgement). Such a runtime
  never qualifies servers for an APK. First CI run of the device DbServer
  lineage in a guest, so creation may surface differences.
- CI run (2026-11-05, runtime 41961253764 at a66b533f6): creation and reopen
  pass with the device DbServer lineage plus this layer; supervisor enabled,
  manual Atlas acknowledged, 0 requests (Atlas is started by the supervisor;
  the DbServer prints its own acknowledgement only at its first map start).
- Shared memory, CI verdict (0.13.54): the heap reserves (1024 MB) but 2 of 2
  sessions failed after login (lost logout; 267 s client stall with repeated
  welcome dialogs). Off; not a basis for zone memory savings yet. The device
  `pss_kib` figures decide whether a spare server fits.
- Next: King's Row on request (start with the cookie, delink on timeout), then
  the shared zone tree.
