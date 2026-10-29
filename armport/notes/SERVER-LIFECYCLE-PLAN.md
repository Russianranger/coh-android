# Prior-zone retirement and Wine request measurement

Design checkpoint, 2026-10-28. **No production retirement change is implemented by this document.** Obtain the 0.13.45 host-metrics baseline and the subsequent native-duration evidence before enabling retirement. No CPU, tick-rate, FPS, battery, or startup improvement is measured here.

Update after review 5692088051: `MapLaunchHistory` now supplies bounded immutable
launch descriptors and unique 256 KiB console tails, with current/resident labels.
Resident travel does not create a new launch generation. It is observational,
not native-process authentication or retirement authority. Existing progress,
reply/control paths and readiness/save/cleanup remain unchanged. Unique native
control paths, confirmed-transfer retirement and safe restart are still future
work; this first slice does not claim that the full generation lifecycle is done.

Harness anchors below refer to source commit `0bf31c81` (the relevant lifecycle files are unchanged from `7d3f234c`). Native anchors refer to the source prepared with patches 0001–0118 in `/tmp/audit-native-prepared/src`, not edited `upstream/`. Wine anchors refer to the exact commit in `android/runtime-lock.json:17`, `b073859675060c9211fcbccfd90e4e87520dc2c2`; the linked source was read through GitHub. Compilers, CI, runtime pins, and production lifecycle code were not changed for this investigation.

## What arrival proves, and what it does not

The correct scheduling point is the successful `arrival_final_character` branch of `android/guest/character_zoning.py:1060–1108`, after its existing checks and `_activate(target)`. It must only schedule retirement; it must not synchronously wait for the old process to exit.

- `connected()` at lines 103–108 requires the exact supported map/static map, loopback address, loaded and connected flags, and `in_map_transfer == False`.
- `_observe_arrival()` at lines 1030–1073 first checks exact character identity through DbServer, then the destination endpoint and live completed-tick progress, then fresh destination `CLIENT_READY` evidence. It rejects readiness preceding delivery and previously seen readiness hashes. It finally queries the exact character again and verifies that the original client process remains alive.
- `map_native_events()` at lines 376–383 parses the currently owned destination console against its progress record, launch time, session, character/auth IDs, and map ID. A future generation must get a distinct progress/console history; map ID alone is insufficient.
- The transfer receipt deliberately says `sql_transfer_commit_acknowledged: False` at line 1090. Arrival is a live handoff proof, not durable SQL-save proof. Preserve that distinction and the ordinary logout/committed-SQL/reopen acceptance path.

The native handoff explains why a confirmed destination can survive retirement of the source:

1. `MapServer/src/dbcomm/dbmapxfer.c:132–145` removes the source entity from `PLAYER_ENTS_OWNED`, sends its current state to DbServer, and then requests transfer. Its comment explicitly says subsequent source changes are not permanent.
2. `DBServer/src/dbdispatch.c:1130–1158` unlocks the source container, calls `setNewMap(..., write_sql=1)`, and checks that ownership changed. `DBServer/src/mapxfer.c:413–428` queues the map update; `finishSetNewMap():454–469` locks the container to the destination link and sends it there.
3. **The old callback link matters as well as the lock.** `DBServer/src/dbinit.c:124–130` logs out stranded entities if either their lock OR their callback link belongs to the disappearing map. `sendLoginInfoToGameClient()` in `mapxfer.c:143–150` clears that callback before the client receives its destination handoff. Merely observing `MapId=target` would be too early; the full existing arrival checks follow this transition.
4. An old-map disconnect cannot unload a character now locked by another map: `DBServer/src/dbdispatch.c:1396–1399` rejects it. The source disconnect path frees its transferred entity without a save at `MapServer/src/svr/svr_player.c:772–787`.
5. `freeMapContainer()` in `DBServer/src/dbinit.c:174–188` clears the old map and unlocks containers belonging to its link. Static map containers remain available for restart.

These are source-backed ordering arguments, **not device proof** and not a guarantee against a simultaneous destination/DbServer crash. Add regression tests for the lock *and callback-link* case before enabling retirement; retain save/reopen device validation. Do not force a SQL save or fake a transfer-commit acknowledgement to make this optimization pass.

## Recommended shutdown API

Use a small, opt-in native retirement request that the **specific source MapServer generation consumes itself**, then call the existing `dbRequestShutdown()`. This avoids host signals as the normal lifecycle mechanism and allows both source and DbServer to refuse shutdown when busy.

`MapServer/src/dbcomm/dbcontainer.c:999–1007` sends `DBCLIENT_REQUEST_SHUTDOWN` on the requesting map's own DbServer link. `DBServer/src/dbdispatch.c:2469–2494` checks that the current map container still owns that exact link and that players, connecting players, and waiting players sum to zero. It then sends a terminal shutdown to that same link. `MapServer/src/container/containercallbacks.c:1040–1058` follows the stock player-sync/ack, cleanup, logging, and exit path. The existing idle-exit option is not sufficient: `svr_player.c:469–500` excludes master static maps and uses minute-scale policy; destination launches also explicitly pass `-idleExitTimeout 0` (`character_zoning.py:750`).

Proposed native contract, to implement with patchwork and extracted-source CI:

- At launch, set a private retirement-file path and a random generation nonce for that MapServer only; retain the global Wine ownership token. Include map ID, native process ID/start identity, session/epoch, and generation in the bounded request/ack contract. Never export nonce values or inherited environment. Use the existing bounded private control-file patterns as a reference, not a general command interpreter.
- After the full arrival proof, atomically write one request for the *old* generation. The native poll runs at a low fixed cadence in the existing tick, validates the complete contract, checks zero local owned/active/connecting player entities and no source transfer in flight, then calls `dbRequestShutdown()` once. If local state is still draining, retry only within a bounded request lifetime. DbServer supplies the independent link/empty-map check described above.
- Emit a structured native request/refusal witness with sanitized identity, counts and reason. The host must observe actual process/task exit and DbServer map-not-ready status; a request or acknowledgement alone is not retirement proof. Stock log shutdown can take time (`logSendDisconnect(30)`); poll asynchronously in the main lifecycle observer, without sleeping or making health wait.
- Keep the old process under normal health observation until a valid request was issued. Thereafter distinguish expected graceful exit from a crash/overflow. On refusal, timeout, unreadable ownership, or uncertain identity, retain the process/evidence and report retirement incomplete. **First implementation has no forced-kill fallback.** The existing whole-session cleanup still owns any remaining processes.

Do not use `wineserver -k/-w`, `WineProcessOwner.cleanup()`, or `Diagnostic.cleanup()` for this operation: they own the entire shared client/DbServer/map session (`diagnostic.py:558–582,1183–1202`). `OwnedProcess.stop()` uses process-group signals (`diagnostic.py:275–294`) and does not itself prove all escaped Wine/FEX descendants exited. Do not use process names as kill authorization.

The stock `MapServer.exe -dbquery -delink <map_id>` exists (`MapServer/src/dbcomm/dbquery.c:319–327`), but it bypasses the empty-map handshake and identifies a map ID rather than a launch generation (`DBServer/src/dbdispatch.c:2653–2656,2671–2715`). It is not the proposed production control. The unrelated `-shutdown` command at `dbquery.c:305–317` requests DbServer shutdown and must not be used here.

## Generation ownership, dormant runtime, and return travel

Introduce a bounded generation record for every launch, including initial Atlas/saved-map launch, not only `_spawn_map()`. Suggested states are `starting`, `ready`, `active`, `retirement_requested`, `stopped`, and `retirement_incomplete`. Keep process history separate from the current resident `maps` lookup. `MAX_EPOCHS=4` (`character_zoning.py:27`) already bounds travel; preserve it.

Each generation owns a distinct progress path, retirement request path, console parsing offsets, native-event history, and optional scheduler state. Today `_spawn_map():725–727` rejects any existing `character-zoning-<id>-progress.bin`; the initial map uses its own fixed progress file. `monorail_environment():371–374` and `_authorize_station():390–400` also use fixed per-map reply paths. Allocate generation-specific paths or safely reset control state only after the previous generation is proved stopped. Old reply/ready/progress records must never authorize a new launch. Keep receipts and bounded consoles for all generations; `collect():1269–1293` currently exports only the current `maps` entries using map-ID filenames.

For ownership proof, extend the existing verifier with a second private generation marker while retaining `COH_WINE_SESSION`. Require both markers, the real UID/PID namespace, PID plus starttime, and the existing zombie-leader/live-worker checks (`diagnostic.py:298–558`). Keep generation verifier state/receipts independent of the global cleanup verifier. Explicitly exclude pinned shared wineserver/DbServer/client/FEX service identities; a helper inheriting a marker must never make a shared service eligible for signaling. The first implementation only uses this verifier to establish exit, not to kill. Unknown or inaccessible descendants mean incomplete proof. Any future force path would separately require `signal_owned()` reinspection and pidfd identity handling, with tests for PID reuse and shared-service exclusion.

After source exit and DbServer not-ready proof, remove that generation from live `maps` (or explicitly classify it so `health():849–854` does not require a deliberately stopped process alive). Keep an immutable history entry and a **dormant runtime lease**. `prepare_atlas_runtime():1476–1516` and `prepare_kings_row_runtime():1772–1780` already reuse a fully prepared session runtime. Retain that runtime/data tree and credential configuration in place for a later launch; do not checkout again, remove the directory, rename it, or release its cache while the session is live.

This is particularly important when Atlas shares the base runtime with DbServer. `prepare_atlas_runtime():1479–1484` documents the live DbServer paths. `ServerDataCache.release()` requires both `wine_prefix_stopped` and `owned_processes_reaped` (`character_server_data_cache.py:596–625`); `local_character_server.py:1725–1730` releases both caches only at final cleanup. **Source-map retirement is not sufficient cache-release proof.** Keep final cleanup unchanged and retain all launch children in `ctx.children` for its reaping proof (`diagnostic.py:1218–1228`).

On return travel, wait for any in-progress retirement before launching that map ID again. Revalidate the retained runtime identity, require DbServer not-ready and the UDP port free, then launch a new generation and perform the entire existing native-readiness/arrival handshake. A stopped map is not a resident warm map: `preparation_budgets():73–82` currently grants residents only 90 seconds. Give restart the existing nonresident native-start allowance until measurements justify another bound; do not silently extend the enclosing save reserve or call this a fast warm start. The same source definitions/sequencers must still load in a restarted process even though its on-disk assets/caches remain prepared.

Serialize retirement and the next travel/save request in the existing observer loop (`character_zoning.py:1125–1165`), not in `health()`. A new return request cannot target an old generation already committed to shutdown. Cancellation/timeout must preserve the active destination and ordinary save route. Retiring the previous zone may increase return-trip latency; measure and report that tradeoff.

## Required tests and evidence

Implementation order:

1. Finish baseline metrics wiring/export, collect all resident maps and owned process CPU during Atlas, destination preparation, and King's Row. Preserve native duration unavailability until its producer is present. Establish collection overhead before attributing a stall to the game.
2. Add generation records and unique control/progress paths with retirement disabled. Test Atlas → King's Row → Atlas → King's Row, saved-King's startup, and final archive/cleanup across multiple generations. This preparatory work can proceed while reviews are pending.
3. Add the native self-retirement request through `patchwork.py`, its extracted-source checks, and the host scheduling/poll state machine. Do not ship forced killing or early cache release as part of this first version.
4. Run the required sequential build → requalification → APK pipeline. Publish exact provenance/artifacts to the reviewer, obtain Claude approval, then run Thor with retirement enabled and repeat the baseline itinerary, combat/save/reopen and cancellation cases.
5. Compare identical active-zone intervals before/after source exit: each map's ticks/longest tick/file-load time, old/new process user/system CPU, DbServer and wineserver CPU, client FPS, collection overhead, and return startup. Temperature/battery effects remain unmeasured unless a separate device measurement is added. A CI pass is not device validation.

Focused negative tests:

- Arrival with target map assignment only, stale/duplicate `CLIENT_READY`, wrong character/session/epoch, transfer flag still set, dead/replaced client, or dead destination: no retirement request.
- Native request with wrong nonce/map/native PID/generation, stale age, malformed/oversized/replaced file, nonzero owned/active/connecting player count, or pending transfer: no shutdown. Extract the actual prepared predicate and actual `dbRequestShutdown()` call site; an unpatched source negative control must lack/reject the retirement behavior.
- Extract/mock the real DbServer request handler: wrong link and each nonzero player count refuse; only current empty map link receives shutdown. Test `unloadStrandedEnts()` ownership AND callback-link behavior and the actual transfer callback clearing, so the no-lost-character argument cannot be reduced to map-ID matching.
- PID reuse, replaced starttime, zombie leader with live workers, unreadable environment, wrong UID/namespace, missing generation/global marker, and shared service identity: exit proof remains incomplete, never signals. No process-group/all-Wine kill API is invoked by retirement.
- Expected graceful exit does not trip ordinary live-map health, unexpected crash/overflow still does; request ack alone does not set `stopped`; map-not-ready alone does not set process-exited.
- Restart cannot consume the old progress/native-ready/monorail reply or overwrite old evidence. A concurrent return request waits or is safely declined; no duplicate map-ID generation runs. Cache checkout/release is unchanged during retirement, and final cleanup still requires all generations and Wine tasks reaped before cache return.

## Wine request counts without changing the pinned runtime

Current `armport/app/server_metrics.py:135–137` correctly says `request_counter_producer_not_wired`. Linux process CPU/thread counters are observable now. `/proc/<pid>/io` syscall counts are **not** wineserver request counts; neither are client event API call counts or socket byte totals. A request may contain variable payload reads, and replies/fd transfers add separate syscalls ([pinned `server/request.c:325–366`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/request.c#L325)).

There is a no-rebuild diagnostic path in the pinned Wine source:

- [`server/main.c:46–70`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/main.c#L46) supports foreground `wineserver -f -d`. [`server/request.c:291–315`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/request.c#L291) calls `trace_request()` once per dispatched request when debug is enabled.
- [`server/trace.c:1561–1592`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/trace.c#L1561) emits request names prefixed by Wine thread ID and separate reply lines. Count request records, not all lines; reconstruct Windows thread/process and Unix PID mapping from initialization records, handle thread-ID reuse, and label unmapped counts unknown. [`server/thread.c:1411–1428`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/thread.c#L1411) ties the first thread's Unix PID/TID and reply Windows IDs together.
- `WINEDEBUG=+server` can also enable the server debug flag through [`dlls/ntdll/unix/server.c:1613–1621`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/server.c#L1613). This is **global for the shared wineserver**, not one game's process: `server/thread.c:1425` takes `max(debug_level, req->debug_level)`. Removing the environment flag from later clients does not turn it back off. A dedicated diagnostic session is required; do not enable it in an ordinary live session for a supposedly cheap 5-second sample.

Source support does not prove the shipped binary/launcher capture works. First probe the exact pinned runtime in an isolated fixture, verify protocol/version and startup tracing, and verify no replacement Wine build is introduced. Starting a foreground traced server must happen before other Wine clients in that fixture; starting it beside an existing server does not attach tracing to that existing process.

Full tracing formats every request/reply and can materially perturb the system CPU/IPC workload under investigation. It can expose command lines and other payloads (`server/trace.c:1007–1014` prints startup command-line fields). Never add raw protocol traces to guest exports. A diagnostic collector must stream into a bounded parser that exports only allowlisted request-name/count/process-identity summaries, discards payload immediately, records parse/drop/truncation/unknown attribution counts and overhead, and drains safely. Do not use a raw log truncated by killing wineserver; ending collection must not terminate the shared server. Captures that overflow or begin after initialization cannot claim complete per-process counts. Validate request/reply separation, fragmented records, unknown requests, missing mappings, ID reuse, and saturation with fixtures before a device experiment.

For routine low-overhead 5-second per-process request counts, the concrete instrumentation point is `call_req_handler()` before dispatch, accumulating per-process/request counters and exporting bounded intervals without payload formatting. That requires a **new pinned Wine runtime** and its own provenance/qualification; it is a proposal, not an implemented counter. Instrumenting only game `SetEvent`/wait calls covers a subset and must be labeled API calls, not actual Wine requests. ptrace/eBPF availability, permission, symbols, and overhead on Thor have not been established and are not a shortcut claimed by this plan.

Keep esync evaluation separate: it also changes the pinned runtime and must be proposed before implementation. A heavily traced run can diagnose request mix, but cannot by itself quantify an esync performance gain or substitute for ordinary-runtime A/B measurements.
