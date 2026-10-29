# DbServer system time and Wine requests: measurement proposal

Status: source investigation, 2026-10-29. **Experiments and runtime changes below
are proposed, not implemented or device-validated.** No request counters or esync
are shipped by this document. Complements `SERVER-LIFECYCLE-PLAN.md:78–94` and
`NATIVE-SERVER-BRINGUP.md:92–147`; those retain lifecycle/native-port ownership.
All local source references below are under `upstream/ouroboros/`; upstream was
read only. Instrumentation must use patchwork and the exact prepared recipe.

## What the current evidence establishes

The 428 s DbServer system CPU and 67 threads reported in `M5-HANDOFF.md:100–104`
are cumulative values at capture. They do **not** establish 428 s of startup cost,
nor identify the active threads. Collect PID/starttime-bound CPU deltas for SQL
connection setup, schema setup, map startup, ready idle, combat and zoning.

The selected SQL pool is `SemaphoreWorkerPool<Semaphore>`
(`Common/sql/sqltask.cpp:9–26`); `SQLCONN_MAX` is 65 (`sqlconn.h:15`) and
`DBServer/src/sql_fifo.c:26,160–175` creates 64 workers. Each worker blocks in
`WaitForSingleObject(INFINITE)` until work, and each push releases its semaphore
(`libs/UtilitiesLib/include/utilitieslib/UtilsCXX/semaphoreworkerpool.hpp:18–23,51–64`).
There is no perpetual 1 ms polling loop in these idle workers. Pool freeze/thaw
are empty (`workerpoolbase.hpp:10–14`); generic TaskThread sleep helpers must not
be counted as this pool's executed path. A barrier enqueues one item per worker
(`sql_fifo.c:290–299`) and uses keyed-event synchronization
(`sqltask.cpp:93–106`, `UtilsCXX/keyedcondition.hpp:18–46`). Keepalives enqueue 64
commands only once per 60 s (`DBServer/src/dbinit.c:352–367`).

**Correction to the handoff's broad wait/request inference:** on the pinned
Wine commit `b073859675060c9211fcbccfd90e4e87520dc2c2`, nonalertable `Sleep(0)`,
`Sleep(1)` and `SleepEx(1,FALSE)` use local yield/select paths, not a wineserver
request simply because they sleep. [`NtDelayExecution:1642–1677`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/sync.c#L1642)
only takes `server_wait` for alertable delays; [`NtYieldExecution:1618–1635`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/sync.c#L1618)
uses `sched_yield` and, when enabled, two `getrusage` calls. These can still cost
host system CPU/PRoot crossings. Semaphore release and object waits do issue
requests ([release:396–409](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/sync.c#L396),
[wait:1572–1592](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/sync.c#L1572)).

## Ranked hypotheses and distinguishing experiments

These are source-supported mechanisms, not measured causes or predicted savings.

| Priority / mechanism | Exact source evidence | Bounded experiment and decision |
|---|---|---|
| 1. Main-thread 1 ms IOCP polling | `DBServer/src/dbinit.c:370–377,1984–1991` calls `NMMonitor(1)` each loop. `libs/UtilitiesLib/src/network/net_masterlist.c:267–305` sleeps if no completion port, otherwise calls `GetQueuedCompletionStatus`, then drains with timeout zero. Wine [`NtRemoveIoCompletion:2029–2068`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/sync.c#L2029) sends `remove_completion`, conditionally waits (`select` request), and conditionally sends `get_thread_completion`. | First count requests for DbServer's first thread plus IOCP calls/timeouts. Compare identical ready-idle windows, then an opt-in 1 ms versus 5 ms timeout fixture. Record SQL completion and network response latency, save/reopen/zoning success and CPU; increased timeout must not hide functional delay. A fall in empty IOCP polls/request rate is the distinguishing signal. |
| 2. Main-thread SQL completion polling during startup | `sql_fifo.c:271–275` blocks in `sql_task_pop`; `UtilsCXX/semaphoreworkerpool.hpp:112–127` repeatedly scans all output rings. `UtilsCXX/taskthread.hpp:12–34` tries 40 fast yields, then `SwitchToThread` and conditional nonalertable 1 ms sleep. Schema setup waits at `dbinit.c:1190,1218`. | Add phase timestamps and counters for empty result scans, fast/slow yields and blocked-finish duration, flushing only once per 5 s. Correlate main-thread CPU against counts and actual Wine requests. High local yields with modest requests supports a completion-wakeup/batched-wait experiment; it does not support adding a render-worker spin. Preserve per-container order and barrier completion. |
| 3. Background log writer wakes every 1 ms | `libs/UtilitiesLib/src/utils/log.c:141` defaults to 1 ms; `1193–1243` drains messages, checks sorted-log/handle flushes, then sleeps. Full-source search for `logBackgroundWriterSetSleep` finds only its definition and MapServer beacon's 500 ms override (`MapServer/src/beacon/beaconClientServer.c:2849`), no DbServer override. | Attribute thread CPU and count empty writer passes. In a diagnostic prepared-source variant, use the existing setter for 10 ms versus 1 ms. Measure queue high-water mark, enqueue blocking, flush latency, final log completeness and CPU. This can reduce local wakeups even when Wine request counts barely change. Do not describe every pass as disk I/O: flush helpers can decide nothing is due. |
| 4. Connection/schema cost or driver transaction polling | `Common/sql/sqlconn.c:309–334,729–753` allocates and connects 65 handles serially; `dbinit.c:1084–1099,1181–1218` initializes ODBC/FIFO and schema. `sqlconn.c:650–661` retries `SQLEndTran` after `SQL_STILL_EXECUTING` with `Sleep(0)`. Async support is checked at `704–718`; `sql_fifo.c:671–677` logs the synchronous fallback. | Time connection and schema phases separately; count connection attempts, transaction polls and SQL outcomes without logging credentials/query text. Check the actual driver's capability/fallback output. Only optimize transaction polling if `SQL_STILL_EXECUTING` is observed. Attribute PostgreSQL and DbServer CPU separately. |
| 5. SQL worker fanout / barriers / keepalive bursts | 64 semaphore workers, keyed-event barriers, and 60 s keepalive described above. `sql_fifo.c:31,262–268` requires a power-of-two worker count and hashes container IDs to preserve ordering. | Count work dispatches, barrier items/duration and keepalive epochs alongside per-thread requests. Continuous traffic implicates real work or polling elsewhere; 60 s bursts implicate keepalives. A later 64 versus 16 worker experiment must keep connection-index and ordering invariants and pass save/reopen/load tests. Thread count alone is not a justification to reduce workers. |

First use fresh-process phase deltas on a copied disposable profile and matched
warm/cold cache states. Collect untraced baseline windows as well as diagnostic
windows; do not attribute tracing overhead to the ordinary game. Any native
counter/timeout experiment requires extracted-real-source CI tests and the
normal sequential build/requalification pipeline before a Thor candidate.

## Actual wineserver request counts: bounded implementation

`armport/app/server_metrics.py:304` currently reports
`request_counter_producer_not_wired`. Keep that explicit until a producer exists.
CPU time, `/proc/io` syscall counts, Windows API calls and socket bytes are not
interchangeable with protocol request counts.

1. **First diagnostic, unchanged runtime:** probe the exact retained binaries in
   a fresh private fixture, start `wineserver -f -d` before clients, and pipe its
   stderr directly to a streaming sanitizer. Count only request records from
   [`call_req_handler:291–315`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/request.c#L291)
   / [`trace_request:1561–1575`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/trace.c#L1561),
   distinguishing reply records. Start before initialization so
   [`init_first_thread:1411–1428`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/thread.c#L1411)
   maps Windows IDs to Unix PID/TID. Join to owned PID/starttime records; never
   infer ownership from executable names. Label uncertain thread/process joins
   unknown, including ID reuse and preinitialization requests.
2. Bound memory to a fixed request allowlist, 256 process identities and 4096
   thread identities; overflow goes to explicit unattributed counters. Use a
   64 KiB maximum line with discard-until-newline handling and bounded buffers.
   Export only 5 s monotonic-window counts, identity/provenance, bytes consumed,
   parser/overflow/drop counters and CPU overhead. Keep cumulative counters so a
   missed output window can be identified. Do not store raw payloads or command
   lines; `server/trace.c:1007–1014` can expose them. Define `complete=false` on
   framing loss, oversized records, missing mapping or failed capture.
3. Capture selected 60 s ready-idle/SQL-load windows after mapping from process
   startup; impose an overall fixture deadline. At the measurement boundary
   continue safely draining/discarding until normal owned teardown. Do not close
   the pipe or kill the shared wineserver to cap a trace. Debug is global and
   sticky via [`thread.c:1425`](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/thread.c#L1425);
   removing `WINEDEBUG` does not disable an already-debugging server. This is a
   dedicated diagnostic run, not a low-overhead live sampling toggle.
4. Before device use, test real pinned trace-format fixtures: request/reply
   separation, fragmented and overlong records, malicious payload/newline text,
   initialization attribution, reuse, unknown IDs, saturation, full output pipe
   and consumer failure. If safe bounded draining cannot be maintained, mark
   the fixture failed and use ordinary owned teardown. No raw trace export.
5. **Routine low-overhead producer, separate runtime proposal:** increment fixed
   per-process-generation/request-enum saturating counters at `call_req_handler`
   before dispatch. No per-request formatting, allocation, file writes or locks
   in the single-threaded server path. Snapshot in the server event loop every
   5 s to a bounded nonblocking output channel, with explicit dropped-snapshot,
   overflow and final-exit records. This measures dispatched requests, not API
   calls or wait latency. It changes the Wine binary/pin and needs separate
   provenance/qualification; it is not part of current server telemetry.

## Esync proposal: scope requiring acceptance before implementation

The retained producer is [lsb-android `runtime-fex-v3` Dockerfile:18–47](https://github.com/Russianranger/lsb-android/blob/runtime-fex-v3/native/fex/Dockerfile#L18),
with [manifest pins/digest](https://github.com/Russianranger/lsb-android/blob/runtime-fex-v3/runtime/fex-bundle.json):
Wine `b0738596…`, FEX `320c5f18…`, bundle SHA256
`030f38066af7b786c142e199cb84adec037840b0f029338849e43f99203a93e1`.
The recipe builds Wine's aarch64/i386 architecture pair and carries the exit-grace,
FEX-loader and wow64-suspend changes; it contains no esync patch/configuration.
Setting `WINEESYNC=1` on these sources is not an esync implementation.

The [Valve implementation reference](https://github.com/ValveSoftware/wine/blob/proton_9.0/README.esync)
uses eventfds and shared memory and requires server/client mode agreement. Its
[`server/protocol.def:4095–4146`](https://github.com/ValveSoftware/wine/blob/proton_9.0/server/protocol.def#L4095)
adds `create_esync`, `open_esync` and `get_esync_fd` requests. Thus this is an
internal client/server protocol and runtime-binary change, even though the
game-facing Win32 API remains the same. That branch is design evidence, **not**
an approved patchset or a claim of compatibility with our Wine 10/FEX build.

Proposed scope, to be accepted before changing the runtime:

- Select and pin an auditable esync patchset rebased onto the exact Wine commit;
  rebuild all matching client/server components, preserving existing FEX and
  Wine fixes. New source/patch/binary digests and notices are required. Use at
  most two compiler processes, including replacing the historical recipe's
  `-j4`/`--parallel 4` during this new build; no competing CI.
- Use a separate prefix/session with no mixed old/new wineserver clients. Verify
  actual Thor eventfd, shared-memory mapping and file-descriptor limits under
  Android/PRoot; availability/performance is not established by the design doc.
  Never alter global host limits as an incidental optimization.
- Compare baseline retained runtime, experimental runtime with esync off, and
  the **same** experimental runtime with esync on; hold FEX/data/profile/cache
  state constant. Keep fsync/ntsync outside scope. Measure untraced startup,
  frame/tick timing, CPU and energy/temperature only when device data exists.
- Gate mixed ARM64/i386 semaphore/event/mutex, named/duplicated-handle,
  wait-any/wait-all, APC and shutdown fixtures, then 65-connection SQL,
  save/reopen and confirmed zoning/cleanup. Keyed-event barriers still use the
  server in the cited esync design; ordinary local nonalertable sleeps are
  already outside wineserver. Do not promise to eliminate IOCP requests or
  infer a numerical gain from semaphore counts alone.
- Obtain acceptance of this runtime-change proposal before implementation;
  retain the current pin meanwhile. Normal reviewer approval remains mandatory
  before handing a candidate APK to the user, and release/publication still
  requires the user's approval.
