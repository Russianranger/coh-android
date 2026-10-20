# Combined OS-process memory observations

The existing single memory worker now reads the Android app/native-client, Wine
servers, PostgreSQL and other same-UID helpers together from `/proc`. No guest
process is spawned. ServerService requests an observation while its existing
runtime process runs; ordinary phase requests also collect when due. The cadence
is five seconds with a 1.5-second scan window, 32 process rows, 8,192 directory
entries and 16KiB per proc file (argv is 4KiB). Existing server admission,
transport/parser/report/resource limits remain unchanged.

A process is identified by PID plus kernel start ticks, checked before/after
reading its status/rollup. The app and native client share one row; role groups
are disjoint. Kernel comm and executable argv positions identify Wine/PostgreSQL;
commands, paths, passwords and process names are never exported. Reused or
vanished PIDs discard measurements. Unreadable metrics, absent expected roles,
process/directory/window limits and unknown statuses remain explicit. There is
no fallback from an unavailable value to zero.

`memory_diagnostics.same_uid_process_set` is included in both existing JSON/ZIP
exports. It contains per-process RSS/PSS, measured partial sums, complete totals
when the enumerated set and required roles are observed, timestamps, scan age
and sampled complete-total peaks. PSS is proportional. Summed RSS repeats shared
pages and is not unique physical RAM. Samples have a bounded time window and
are not atomic snapshots or absolute peaks. Unknown process ownership/OS
visibility cannot be guessed; observed partial sums remain labeled separately.
Existing app-only phase values must not be added to this already-inclusive set.
No GPU total, whole-device fit, crash cause or runtime admission follows.

Android onTrimMemory/onLowMemory callbacks are retained separately. Existing
ApplicationExitInfo records now include numeric PID for correlation. A recorded
LOW_MEMORY reason is OS evidence; a SIGKILL/status alone is not an OOM diagnosis.
Callbacks do not prove a kill. The earlier actual exit history remains intact.

Publication copies a bounded completed map under a short lock; proc I/O does
not hold the snapshot lock or run on render/network/UI ownership. Only the
latest 32-row set, scalar peaks and existing nine phase slots are retained.
Scratch input is bounded per file and streamed; no full smaps/world scan occurs.

Focused tests:
* `qualification/check_process_set_memory.py`: 24 checks over complete/partial
  app+Wine+PostgreSQL fixtures, self overlap, PID reuse, roles, malformed/overflow
  values, missing files, limits and real host proc parsing; Java heap capped128MiB.
* `qualification/check_memory_worker.py`:39 checks,9,000 queued requests,two
  injected failures and actual production callback/worker behavior with Android
  collaborators explicitly doubled.
* `qualification/check_phase_memory.py`:2,899 checks; existing policies unchanged.
* `tools/test_process_set_contract.py`:four export/dedup/privacy/missing-total
  controls, including a maximal32-row export below12KiB.

These are Java/host OS qualifications, not Android/Thor memory measurements.
No ASan/UBSan claim applies to this Java-only increment. Android13 execution and
physical simultaneous server/client peak observations belong to the next APK.

The additive `entity-diagnostic` profile selects0.1.13/code14 explicitly with
`-PcohBuildProfile=entity-diagnostic`; default/historical profiles and signer are
preserved. Packaging uses the existing build and Android execution workflow.
