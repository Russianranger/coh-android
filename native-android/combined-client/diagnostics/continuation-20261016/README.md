# Read-only startup and memory investigation, 2026-10-16

This independent workstream changes no application/runtime code, donor input,
cache, profile, cleanup policy, workflow or APK. It adds an offline export
analyzer and records the evidence available at `fbc1aa0718c9a6d02a32cd6e14cfdff560dadbbd`.
Nothing here newly accepts Gates 25–27 or measures a 0.1.7 physical run.

## Current physical result

The retained physical 0.1.6 export was inspected read-only. Its archive SHA256
is `f4b0d29988272e83b2582094649660841a9e5217152b26dd461106e832016f3f`.
The [generated allowlisted analysis](thor-016-analysis.json) reproduces these
current code-7 stage boundaries:

| Stage | Entry, ms | Until next stage, ms |
| --- | ---: | ---: |
| Immutable server inputs | 8 | 618 |
| Server-only input admission | 631 | 5,280 |
| Private server inputs | 5,911 | 7,021 |
| Isolated required geometry | 12,932 | 1,223 |
| Wine initialization | 16,307 | 11,459 |
| Login/ODBC preparation | 27,766 | 14,336 |
| DbServer startup | 42,102 | 69,787 |
| Atlas startup | 111,889 | 280,303 |
| Server ready | **392,192** | — |

All remaining shorter transitions are retained in the JSON. These are
application-received stage boundaries, not profiler timings. DbServer and Atlas
boundaries account for **350,090 ms / 89.265%** of readiness latency. The DbServer
boundary can include preparation/configuration and the native readiness wait;
it is not solely native DbServer CPU time. Final elapsed time 421,288 ms is an
observation while ready, not another startup measurement. No stage age is
substituted for elapsed work.

The export includes a *different* server session's final guest report and four
historical attempts. The **438.672194 s cold mirror**, **67.560703 s beacon
preparation**, and **800,298 ms readiness** belong to historical code 5 / 0.1.4.
Current 0.1.6 cold/warm classification stays **unknown**. The faster result does
not prove a warm-cache optimization.

Source explains the evidence gap: `server_runtime.main` publishes the detailed
`latest-report.json` in `finally`, after cleanup. During a live ready run,
`ServerService` persists current stage/memory observations, while the detailed
report can still be from the preceding stopped session. `MainActivity` correctly
labels that member `previous-session-...`. This is an attribution issue for
analysis, not a reason to discard evidence or alter the running server.

## Memory and ownership

- Current 0.1.6: 416 valid Android memory samples, zero invalid samples, a final
  pressure-sequence count of zero, and no pressure-stop request. Minimum observed system headroom
  8,270,680,064 bytes; Java heap headroom 209,006,312 bytes.
- The 28 retained guest boundaries have maximum self high-water RSS 305,184 KiB,
  current RSS sample maximum 114,976 KiB and child high-water sample maximum
  305,184 KiB. `RUSAGE_CHILDREN` covers reaped children; it is not concurrent live
  Wine/DbServer/MapServer RSS. These peaks must not be added into a claimed
  process-tree peak. Cgroup current/limit/OOM counters remain unavailable.
- The accepted physical review identifies eight exit records as preceding the
  current native session (three low-memory, five reason 10). This analyzer
  deliberately leaves temporal attribution unknown because the launcher alone
  supplies no bound wall-clock origin. An exit record's mere presence never
  becomes evidence of a current kill.
- Historical code-4 interruption: last persisted stage was input admission at
  5,135 ms; seven valid samples showed at least 8,315,179,008 bytes system
  headroom and 245,580,856 bytes Java headroom. Android subsequently recorded
  reason 3, PSS 78,634 KiB and RSS 184,828 KiB. The existing audit places it
  approximately 5.4 s into that attempt. The allocation site, actual guest
  process-tree peak, cgroup limit and cause remain unknown.
- Admission hashes stream 1 MiB chunks; the retained audit found 81 payloads,
  3,872,410,072 bytes total, with a 1 MiB manifest-read cap. The later 48,591,999-
  byte visual manifest is not evidence it was materialized at the early failed
  stage. Cold geometry validation is already isolated and joined before
  PostgreSQL or Wine startup; its warm path retains exact validation.
- The current server is intentionally alive after client Return. That alone is
  not a leaked process. The historical final guest report records graceful
  PostgreSQL/Wine cleanup, reaped owned processes, removed presentation socket
  and preserved profile. Current 0.1.6 final Stop was not observed.

The owner retains a bounded inventory of at most 512 `OwnedProcess` records;
each capture is bounded to 2 MiB. This is a possible **aggregate** memory budget
concern (a loose theoretical 1 GiB output capacity), not observed consumption or
an established leak. The historical code-5 final report has 36 process records
and only **65,128 total recorded output bytes**. The current ready export has no
final child inventory. Reaping clears live processes but intentionally preserves
recorded output for subsequent parser/cleanup proof.

## Safe next measurements and separately qualified experiments

| Candidate | Evidence and uncertainty | Required proof before runtime change |
| --- | --- | --- |
| Preserve current preparation breakdown while ready | Current detail becomes available only at final cleanup | A bounded numeric session-bound snapshot; no raw SQL, account, process text or paths; independent publication/ownership tests. Alternatively inspect the normal final export after the user's next planned Stop. |
| Find the native Atlas startup bottleneck | Atlas stage is 280.303 s; no substage breakdown in current Combined export | Existing native dispatch/progress timestamps plus cache-consumer proof from the same current session; preserve tick/readiness gates. |
| Compare warm cache checkout with cold preparation | Source already supports receipt-backed checkout; historical cold cost is large | Same app/donor/import identity, explicit `warm_schema_restore` or `cold_server_data_mirror` receipt, and complete ready interval for each observed boot. Never delete accepted caches merely to manufacture a cold test. |
| Avoid repeated decoding of unchanged MapServer console | `map_crash_observation` calls `OwnedProcess.text()` during health polling; `text()` decodes the whole retained bytearray each call | Isolated benchmark at bounded output sizes; exact equivalence for markers split across chunks, UTF-8 boundaries and truncation/overflow; retain complete required source evidence and timely crash detection. No measured Thor benefit yet. |
| Bound aggregate retained child-output memory | Independent per-child bounds do not constrain aggregate bytes tightly | Record numeric aggregate current/high-water retained bytes and child count; identify captures still used by downstream parsers; qualify retention/release changes without weakening cleanup or SQL proof. Historical 65 KiB does not justify a production edit. |
| Diagnose early Android low-memory exit | Healthy sampled headroom did not identify the allocation or policy limit | Authorized numeric process-tree samples and an independently verified owned cgroup identity if accessible; transient allocation sampling/exit correlation. Do not read or export environment/command-line secrets or disable Android protections. |

The next 0.1.7 physical test should remain the existing consolidated protocol
test. No repeat of accepted 0.1.6 or forced cold-start experiment is needed for
this workstream. If a normal user-requested server Stop is performed later,
exporting afterward can attach the current finalized guest preparation receipt.
No runtime experiment was run in this workstream.

## Source binding and reproducibility

Four inspected donor modules (`diagnostic.py`, `client_startup_diagnostic.py`,
`local_character_server.py`, `local_login_server.py`) were recovered from the
prior admission audit. Each matches its retained imported `client-manifest.json`
SHA256 and the current repository bytes. Their hashes and other source hashes
are in [qualification.json](qualification.json). This verifies the audited donor
copy, not a fresh extraction of the user's current installed runtime.

Relevant original source paths/functions:

- `native-android/combined-client/runtime/server_runtime.py`: `main`,
  `prepare_geometry_before_servers`, `guest_resource_sample`,
  `Context.resource_boundary`, `Context.start`, `Owner.execute` and `Owner.cleanup`.
- `native-android/combined-client/app/src/main/java/org/coh/nativecombined/ServerService.java`:
  stage/memory capture, current report/session checks, cleanup and previous-attempt retention.
- `native-android/combined-client/app/src/main/java/org/coh/nativecombined/ServerMemoryPolicy.java`:
  1 s observation interval, 64 retained samples, admission and pressure cleanup.
- `native-android/combined-client/app/src/main/java/org/coh/nativecombined/MainActivity.java`:
  current/historical report export naming.
- `android/guest/client_startup_diagnostic.py`: `verify_assets` and same-process
  `verified_asset_matches` cache; no persistent unchecked hash bypass.
- `android/guest/local_character_server.py`: `prepare_runtime`,
  `prepare_atlas_data`, `sample_progress`, `map_crash_observation`, `health`.
- `android/guest/diagnostic.py`: `OUTPUT_LIMIT`, `OwnedProcess`, `Diagnostic.cleanup`.

Existing reviewed evidence:

- `../../evidence/20261016/thor-0.1.6-acceptance/THOR-016-ACCEPTANCE.md`
- `../../evidence/20261015/startup-repair-0.1.4/local/admission-audit.json`
- `../../evidence/20261015/startup-repair-0.1.4/thor-failure-sanitized.md`

Run from the repository root:

```sh
python3 -m unittest discover -s native-android/combined-client/diagnostics/continuation-20261016 -p 'test_*.py' -v
python3 native-android/combined-client/diagnostics/continuation-20261016/analyze_startup.py /path/to/COH-NativeCombined-export.zip
```

The analyzer opens inputs read-only and never extracts archives. It bounds
archive/member sizes, counts, JSON structure, arrays and numbers; rejects
unknown/path-like/duplicate/link/encrypted archive members, invalid CRCs,
duplicate JSON keys and nonfinite values; and emits only fixed keys, fixed stage
names, numeric observations, booleans and hashes. Native report bodies are
CRC-checked but never parsed or copied. Current/historical assignment requires
exact valid session equality; IDs themselves are not emitted. An older guest
receipt never supplies the current startup classification. Unknown remains
unknown. JSON and error messages do not echo input paths or arbitrary values.

26 host tests pass. The real physical export is checked against the accepted
numeric record. This offline-only addition requires no APK rebuild, Android
execution, sanitizer qualification or new Thor test; existing APK hashes remain
unchanged. Remove this directory to roll back the tool without runtime effects.
