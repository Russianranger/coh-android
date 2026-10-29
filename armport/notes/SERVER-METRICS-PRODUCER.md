# Native server metrics producer checkpoint

This experimental source producer is separate from the 0.13.45 APK inputs.
It has host source tests, not a Windows MapServer build or Thor validation.
Package and guest integration status is in [SERVER-METRICS-DEVELOPMENT.md](SERVER-METRICS-DEVELOPMENT.md).

## Producer integration — 2026-10-29

The opt-in pipeline is now implemented in `armport-build.yml`; it has **not yet
run**. Dispatch with `build_server_metrics=true` to add `server-metrics-source`
after the existing client/server jobs, then `server-metrics-native`. The input
defaults to false. No separate workflow or overlapping native stage is started.

[server_metrics_producer.py](../scripts/server_metrics_producer.py) authenticates
the complete retained 0.10 APK and build report and the complete pinned 0.13.36
APK before extracting either game package. It preserves each raw predecessor
manifest and builds both source trees against their actual donor receipts.
The retained receipt uses CRLF for two PostgreSQL overlay files; the adapter now
reproduces that already accepted byte profile in fresh staging before applying
the unchanged overlay chain. It does not normalize the donor's receipt.

Both jobs use a pristine, separately checked-out baseline at
`c86a57962363dbe2dc2091dadde6abdfaa2e1e1c`, passed as `--upstream-root`. The shared
`server_package.baseline_root` gate verifies the exact Git head and a clean
working tree. This is required because the historical animation certificate
pins the old guest animation helper's bytes, while the new runtime admission
helper changes that file. Sparse baseline checkouts include `.gitignore`, so
ordinary Python bytecode caches do not falsely dirty the baseline. Modern
generation also refuses cached certificate modules imported from another root.

The Linux job runs eight extracted-source cases plus the specific upstream
negative control on **each actual prepared variant**. Its bounded archive binds
every transferred source byte, source report, donor manifest and animation
input to the producer commit/run and frozen baseline. The Windows job verifies
that closure again, executes the existing genuine Win32 animation-certificate
and monorail-boundary fixtures, then builds only MapServer for the retained and
modern variants, sequentially. `CMAKE_BUILD_PARALLEL_LEVEL=1`, `--parallel 1`, and
`_CL_=/MP1` bound the builds. `_CL_` is appended after command-line options, so
the existing project `/MP` cannot override the limit
([Microsoft documentation](https://learn.microsoft.com/en-us/cpp/build/reference/cl-environment-variables?view=msvc-170)).
The compiler process count is constrained by those settings, not reported as a
measured process count.

Artifacts from the same ArmPort build run are:

- `armport-server-metrics-source`: exact prepared input tarball and its digest.
- `armport-server-metrics-native`: flat `server-metrics-retained-progress.zip`
  and `server-metrics-thor-certified-startup.zip`, plus their byte pins.
- `armport-server-metrics-native-evidence`: PDBs, configuration/build logs,
  source reports and genuine Windows fixture evidence. A failure does not upload
  the success-only native package artifact.

Each native ZIP retains its four-member contract: `MapServer.exe`,
`server-metrics-build.json`, `previous-game-package.json` and
`server-metrics-source-checks.json`. The POSIX fixture report remains explicitly
separate from Windows PE execution. The producer compiles the shipping binary
but does not launch it, qualify the app runtime or validate Thor behavior.

Additional local results for this integration:

- `ARMPORT_SERVER_BASELINE_ROOT=../coh-server-baseline python3
  armport/tests/test_server_metrics_source.py -v`: **10 passed**, including the
  actual retained CRLF donor and the wrong-module-root generation refusal.
- `python3 armport/tests/test_server_metrics_producer.py -v`: **8 passed**.
  These are archive/identity/sequencing tests; compiler commands are mocked in
  the sequencing test and make no Windows execution claim.
- The actual retained donor source receipt is
  `8e26c7eafbb4546976eefa0212394a7bfaaa8a5af347710303ecbd0d1fe47885`.
  Eight extracted runtime cases and the specific upstream runtime negative
  control passed locally against that tree, with one compiler at a time.

No full modern source tree, Windows build or new server APK has been produced
locally. The first opt-in Actions run must recover the exact published animation
PIGG/manifest and both donors; missing or changed inputs fail closed. Runtime
qualification and the Thor APK must consume the appropriate variant from the
same build chain, preserving the distinction between retained CI execution and
modern device evidence.

## Native source and measurement scope

Patch [0119](../patches/0119-armport-server-tick-file-metrics.patch) was authored
in patchwork commit `04b0e9a6cb77756939f4d4708c5f66a73166aff4` and exported with
`armport/scripts/patchwork.py export`. Its SHA-256 is
`49c0f73d9ea0a0ecb8d2f1de9a48ec1d5b20dc3c641e058bc8c1a5947440c387`.
No immutable upstream file was edited.

`ARMPORT_SERVER_METRICS=1` enables the observer after server startup, immediately
before the main loop. Every other value leaves it disabled. Disabled file-load
observation makes no clock calls or log writes. TLS limits file-load accounting
to the main thread that initialized the observer; other programs and worker
threads remain disabled.

The `ARMPORT_SERVER_METRICS_V1` record contains map ID, Windows PID, actual window
seconds, completed iterations, maximum work time, maximum work-plus-sleep time,
and outer `fileAlloc`/`fileAllocEx` wall time, attempts and NULL returns. It emits
at the first completed loop at or after five seconds; a stalled loop can delay
the record. It is not a five-second watchdog.

Work includes all pre-existing main-loop operations before `sleepAndCalcTimers`.
The complete-loop measurement includes all pre-existing operations through the
end of that loop, including the retained `PRE_TICK`, `POST_TICK`, `SLEEP` and
`SLEEP_DONE` progress observers. The metrics logger's own output cost is excluded
from both maxima, but included in the next window's wall-time denominator.
The observer adds clock/TLS/accounting overhead when enabled; its cost under
FEX/Wine and on Thor has not been measured.

File time includes lookup, allocation, read/decompression and callbacks, and
failed attempts. Nested calls count once at the outer boundary. It excludes
startup, background loads, direct `fread` and other file APIs. It is not disk-only
time, parser time, or all server I/O. `Reading <seq>` output is not used as an I/O
counter. No wineserver protocol request count is supplied by this observer.

Clock failure/backward movement emits an error and disables metrics without
changing server behavior. Counters saturate rather than wrap.

## Two exact server source lineages

[prepare_server_metrics_source.py](../scripts/prepare_server_metrics_source.py)
selectively applies 0119 over one existing producer:

| Variant | Existing source producer | Retained behavior |
| --- | --- | --- |
| `retained_progress` | `prepare_mapserver_progress_source.py` | Exact 0.10 progress/creation/PostgreSQL lineage |
| `thor_certified_startup` | `prepare_map_startup_source.py` | Character events, monorail, certified animation data and 720-second station preparation budget |

The adapter reconstructs the native patch outputs from immutable input. It
checks that its loop insertion transform exactly matches 0119 on the plain
source, then places the same begin/end hooks outside the retained progress
markers. It validates every preimage before writing. Existing source receipts
are untouched; `server-metrics-build-input.json` separately binds the baseline,
nested receipts, patch, two modified preimages, four resulting native files and
all retained predecessor overlay identities. `--baseline-receipt` additionally
requires exact equality with the chosen donor's actual source receipt.

The full retained-progress tree was staged locally and tested. The modern
variant's receipt, hook rebase, animation-table pin and 720-second budget were
checked against the real 0.13.32 publication metadata. **Full modern staging was
not run**: it requires the actual pinned animation PIGG and manifest, which were
not available in this workspace. The producer does not invent or substitute a
certificate table.

## Reproduction and observed checks

From this experimental worktree, the following commands were run successfully
with a separate full repository at `../coh-android`:

```sh
python3 armport/scripts/prepare_server_metrics_source.py \
  --variant retained_progress \
  --upstream-root ../coh-android \
  --output ../server-metrics-progress-source-v2
python3 armport/tests/server_metrics_native.py \
  --source ../server-metrics-progress-source-v2 \
  --negative-control ../coh-android/upstream/ouroboros \
  --upstream-root ../coh-android \
  --report armport/evidence/server-metrics-host-checks.json
python3 armport/tests/test_server_metrics_source.py \
  --upstream-root ../coh-android -v
python3 armport/tests/server_metrics_native.py --source ../patchwork/src
```

For a normal full checkout, omit `--upstream-root` and use its own
`upstream/ouroboros` for the negative control. All output directories must be
fresh. The original source verifier reported 5,995 files, 173,081,714 bytes,
snapshot `0b75ade0c801735e10c5798f641948a45cc50488`.

Observed results:

- Eight source identity/refusal tests passed, including exact baseline retention,
  wrong donor, source/receipt tampering, existing/linked header, JSON type
  substitution and published host-report binding.
- Eight runtime cases passed on the actual staged retained source: five-second
  boundary/reset, disabled, nested/failed loads, thread isolation, slow loop,
  failed/backward clocks, saturation and retained progress-marker time.
- The marker case adds 10 ms to each of four real extracted loop call sites;
  measured work is 280 ms, complete loop 1,040 ms and file time 50 ms. Direct
  assertions require the first/last loop statements to be the metrics hooks.
- The unpatched upstream loop/file functions compiled successfully, then failed
  the specific runtime assertion for missing tick/file counts. A compiler error,
  crash or unrelated failure does not satisfy this negative control.
- The plain 0119 patchwork source still passes its seven runtime cases; it has
  no retained progress-marker calls.

The fixture compiles the extracted prepared loop, real `fileAlloc` bodies and
real metrics implementation with GCC, ASan/UBSan and pthreads. Only deterministic
Windows clock, thread-storage and file-I/O adapters are supplied. Compilers ran
sequentially, one process at a time.

[server-metrics-host-checks.json](../evidence/server-metrics-host-checks.json)
records the compiler, generated fixture hashes and source hashes. Its source
receipt digest is
`5ae22dfb1e62b48d7b620113259776d2a9e67ed9b26e37db7eec0ea309f228a6`.
`shipping_binary_executed` is explicitly false. The report identity validator
does not authenticate arbitrary reports: CI must execute the checks and retain
their logs.

## Remaining execution and qualification

No Windows executable, native symbols or server-containing APK was built here.
The implemented opt-in producer still needs its first actual run. It builds the
two lineages separately and retains their exact donor receipts. ARM64 and i686
builds remain sequential; the persisted CMake cache alone cannot prove compiler
concurrency.

The ARM64 client build's source test does not replace either Win32 MapServer
build or runtime requalification. These changes do not port DbServer/MapServer
to ARM64, alter the pinned Wine runtime, enable esync, stop prior map processes,
or measure startup file loads. A future producer and consumer integration must
preserve the user's ordered pipeline, then obtain reviewer approval before a
server-instrumented APK is handed to the user.
