# Server metrics package development — not a shipping candidate

Development checkpoint, 2026-10-29: 0.13.46/code 61 connects patch 0119's separately built Win32 MapServer to optional build/runtime/APK inputs, authenticated guest admission and bounded native-console exports. **No .46 native CI, runtime, APK or device result exists yet.** The 0.13.45 candidate retains both old server donors and awaits review at PR #8 comment 6485053545. Do not hand a .46 package to a device before serialized qualification and Claude approval.

The two exact source lineages are intentionally distinct:

| Variant | Donor | Existing behavior retained |
| --- | --- | --- |
| `retained_progress` | Retained 0.10 CI; MapServer `52f85c9e…0fb`, manifest `ef1e5b1a…24cd` | Original map-progress producer, before native responsiveness and monorail |
| `thor_certified_startup` | Startup MapServer retained in pinned 0.13.36 APK; 7,475,200 bytes, SHA256 `fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363` | Native responsiveness, monorail, certified animation loader and 720-second station preparation budget |

A passing retained-runtime test does not execute or qualify the Thor variant. The historical donor records are in `docs/android-evidence/mapserver-progress-package-36630872719.json` and `docs/android-evidence/client-map-startup-0.13.32-publication.json` (`complete_preparation/native_admission/game_package`). The modern reader also requires the exact accepted producer from `release-client-map-startup-0.13.32.json`.

## Producer API

Run the exact baseline producer first, then `prepare_server_metrics_source.py`; see [SERVER-METRICS-PRODUCER.md](SERVER-METRICS-PRODUCER.md) for native source and extracted-source checks. The caller authenticates the outer donor and extracts its **original raw** `game-package.json`; do not canonicalize that file. The packaging CLI is:

```sh
python armport/app/server_package.py package \
  --binary-directory BUILD/bin/OptDebug \
  --prepared-source PREPARED --cmake-cache BUILD/CMakeCache.txt \
  --predecessor-manifest DONOR/game-package.json \
  --predecessor-bytes EXACT_BYTES --predecessor-sha256 EXACT_SHA256 \
  --source-report server-metrics-source-checks.json \
  --variant retained_progress --repository-commit EXACT_COMMIT --run-id EXACT_RUN \
  --upstream-root BASELINE --output server-metrics-retained-progress.zip
```

Use `thor_certified_startup` only with its own source, executable, source-test report and donor. `--upstream-root BASELINE` must be a clean checkout of `c86a57962363dbe2dc2091dadde6abdfaa2e1e1c`. The accepted animation certificate pins that historical validator's source bytes; using today's changed guest helper would invalidate the immutable predecessor. This frozen host baseline reproduces original source/certificate inputs only. The guest receives the current authenticated compatibility helper. Native patch 0119 and its test script are read from the current candidate, not the baseline. Both `package(...)` and `read_package(...)` validate the source recipe; `package(...)` also verifies the actual prepared files. The report validator binds positive cases and the unpatched negative control to those exact files. The report explicitly identifies POSIX clock/file shims; it does not claim execution of the shipping Windows PE.

The deterministic ZIP has exactly `MapServer.exe`, `server-metrics-build.json`, `previous-game-package.json` and `server-metrics-source-checks.json`. It binds the PDB hash and size but leaves symbols in a separate CI artifact. The executable bound is 64 MiB; symbols have a separate 256 MiB bound. Historical progress PDB evidence is 40,038,400 bytes; the new modern PDB size still needs measuring.

## Staging API and limits

```sh
python armport/app/server_package.py patch-game \
  --game-archive DONOR/game-package.tar.gz \
  --server-archive server-metrics-retained-progress.zip \
  --variant retained_progress --repository-commit EXACT_COMMIT --run-id EXACT_RUN \
  --upstream-root BASELINE --output STAGED/game-package.tar.gz
```

`patch_game(...)` requires an absent output path. It verifies every donor native member and actual PE imports, then changes only `MapServer.exe` and `game-package.json`. The additive `armport_server_metrics` receipt records exact raw and canonical predecessor digests. `previous_package(...)` reconstructs metadata only; it is **not** current-PE authentication or a guest authorization API.

Old nested manifest key order is preserved. The historical character-events contract hashes insertion-order JSON; sorting all keys would invalidate its receipt even if values were unchanged. Canonical serialization is used for new digest comparisons, not for rewriting the old ancestry.

## Serialized CI and admission

All candidate commits use `[skip ci]`. Ask the CI dispatcher to run only these stages, waiting for complete success before the next one:

1. `armport-build.yml` at the exact candidate SHA with `build_server_metrics=true`. Existing ARM64 jobs finish first; the source job authenticates both original APKs and the actual animation data, prepares both lineages and runs extracted-source positive/unpatched controls. The dependent Windows job runs real animation/monorail fixtures, then builds both Win32 MapServers sequentially. `_CL_=/MP1`, CMake parallel level 1 and `--parallel 1` constrain these builds. No compiler concurrency has yet been measured in this new job.
2. `armport-app-runtime.yml` at that same SHA with **client_run_id, data_run_id and server_run_id all set to the successful build run**. The retained-progress binary must pass creation and reopen with distinct session IDs, preserved profile/character and no reported failures. `armport-app-server-metrics` binds both exact ZIPs to those sessions. It explicitly marks the modern Thor binary as not runtime-executed.
3. `armport-thor-apk.yml` at the same SHA with `m4_run_id` equal to that successful runtime run and `server_metrics=true`. It rechecks native/run/head/package pins, stages only the modern server variant, and produces 0.13.46/code 61. Post all three runs, artifact ID, ZIP digest, APK bytes/hash and provenance notice before asking Claude for candidate handoff approval.

The build artifact `armport-server-metrics-native` contains `server-metrics-retained-progress.zip`, `server-metrics-thor-certified-startup.zip` and their pins. PDBs, build logs and real Windows fixture evidence are separate in `armport-server-metrics-native-evidence`. `armport-server-metrics-source` retains the exact prepared input bundle. Defaults leave native metrics packaging disabled.

`stage_app_assets` authenticates the original game archive, the selected server ZIP and its source receipt before creating output. It replaces only MapServer and the game manifest inside the new game archive, adds a runtime-owned binding/helper, and repins the client/runtime inventories. **client-runtime.zip, DbServer and all other native members remain unchanged.** The independent client/runtime data closure is not the source of the launched MapServer.

`armport_server_metrics_contract.py` checks the binding against the runtime inventory and the actual current PE before exposing predecessor metadata to existing progress, startup, monorail, cache, animation, FX and beacon readers. Exported producer evidence names the actual new binary/run/head. Existing historical hash lists are not widened. Reopen and stock-power compatibility use that authenticated producer proof. `ARMPORT_SERVER_METRICS=1` is set only after actual launch-path verification.

## Measurement limits

`server_metrics.py` parses only 0119's exact records from an owned process generation and matching Windows PID/map progress. It rotates bounded console tails (8 KiB per map, 32 KiB total) and reserves 5 ms within the existing 50 ms observation target. Missing, disabled, unknown activation, partial, malformed, stale and clock-error states remain explicit. Raw console payload is not added to the metric report; ordinary console evidence remains separate. The sampler does not change readiness or save/cleanup acceptance.

Native records distinguish maximum main-loop work from work-plus-sleep, and total inclusive outer `fileAlloc`/`fileAllocEx` time. They cover only post-ready main-thread work, excluding startup, background file calls and direct `fread`; they are not disk-only timing. CPU counters and existing progress rates remain independent. **Wine request counts are still unavailable.** Collection overhead, FPS, tick-rate, startup, battery and thermal improvements need measured runtime/device evidence; none is claimed here.

## Host validation

`python armport/tests/test_server_package.py`: **23 passed, 0 skipped**. Tests validate both real historical metadata readers; deterministic archives; exact donor/run/head/source-report binding; real PE import parsing; rejection of alternate architecture/imports, changed DbServer/history, duplicate/traversal/link entries and failed partial publication. Synthetic executable tests exercise packaging only. Neither a new Windows MapServer nor the modern full-data source tree was built or executed by this suite.

Final local integration check: **392 tests passed**, using the installed JDK compiler module through a local `javac` launcher and `ARMPORT_SERVER_BASELINE_ROOT` pointing to the pristine pinned checkout. Included: 33 telemetry, 21 guest-admission, 14 pipeline, 23 package, 10 source-lineage and 8 producer tests. The earlier missing-launcher failures were environment setup failures; the final complete run passes. Actual retained prepared-source ASan/UBSan positive cases and the specific original-code missing-metrics negative assertion also pass. See `../evidence/server-metrics-retained-donor-host-checks.json` for that separately run native fixture. These are host checks, not shipping Win32 server execution. Independent workflow review found and fixed the sparse baseline's missing `.gitignore`; all current Python/YAML syntax and whitespace checks pass.
