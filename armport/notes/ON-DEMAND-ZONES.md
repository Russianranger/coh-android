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

## Shared memory (candidate measurement, not started)

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
- Next: run the DbServer workflow when no other chain runs; then King's Row on
  request (start with the cookie, delink on timeout), then the shared zone tree.
