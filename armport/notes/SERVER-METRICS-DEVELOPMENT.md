# Server metrics package development — not a shipping candidate

`armport/app/server_package.py` stages patch 0119's separately built Win32 MapServer. It is **not connected to the runtime/APK pipeline or guest compatibility readers**. The 0.13.45 baseline candidate retains both old server donors. Do not hand a package from this work to a device until the remaining integration, serialized CI and reviewer gate are complete.

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
  --output server-metrics-retained-progress.zip
```

Use `thor_certified_startup` only with its own source, executable, source-test report and donor. `--upstream-root REPO` allows a sparse worktree to read immutable upstream from the full checkout. Both `package(...)` and `read_package(...)` validate the source recipe; `package(...)` also verifies the actual prepared files. The report validator binds positive cases and the unpatched negative control to those exact files. The report explicitly identifies POSIX clock/file shims; it does not claim execution of the shipping Windows PE.

The deterministic ZIP has exactly `MapServer.exe`, `server-metrics-build.json`, `previous-game-package.json` and `server-metrics-source-checks.json`. It binds the PDB hash and size but leaves symbols in a separate CI artifact. The executable bound is 64 MiB; symbols have a separate 256 MiB bound. Historical progress PDB evidence is 40,038,400 bytes; the new modern PDB size still needs measuring.

## Staging API and limits

```sh
python armport/app/server_package.py patch-game \
  --game-archive DONOR/game-package.tar.gz \
  --server-archive server-metrics-retained-progress.zip \
  --variant retained_progress --repository-commit EXACT_COMMIT --run-id EXACT_RUN \
  --output STAGED/game-package.tar.gz
```

`patch_game(...)` requires an absent output path. It verifies every donor native member and actual PE imports, then changes only `MapServer.exe` and `game-package.json`. The additive `armport_server_metrics` receipt records exact raw and canonical predecessor digests. `previous_package(...)` reconstructs metadata only; it is **not** current-PE authentication or a guest authorization API.

Old nested manifest key order is preserved. The historical character-events contract hashes insertion-order JSON; sorting all keys would invalidate its receipt even if values were unchanged. Canonical serialization is used for new digest comparisons, not for rewriting the old ancestry.

Remaining integration is explicit:

- Add the dependent Windows MapServer producer after ARM64 compilation; build the two i686 variants sequentially. Enforce at most two compiler processes, including the existing `/MP` setting. Cache fixture-OFF validation alone does not establish compiler concurrency.
- Retain PDBs, build logs and actual animation/monorail fixture evidence. Neither the package reader nor the POSIX metric fixture substitutes for Windows build execution or Thor validation.
- Authenticate the appropriate outer donor before passing its manifest pin. Wire `stage_app_assets`, `interactive_host`, runtime workflow and APK builder with exact variant/run/head inputs and explicit changed-file allowlists.
- Implement a single guest metrics contract that authenticates the new PE before projecting its old ancestry. Route local-server extraction/verification, progress/monorail, cache, animation, beacon and FX consumers through it. Do not broaden the old hash allowlists.
- Requalify runtime, build APK, post exact artifact/digest/provenance, obtain Claude approval, then run the full Thor test. Retained 0.10 success must remain labeled separately from modern server/device evidence.

## Host validation

`python armport/tests/test_server_package.py`: **22 passed, 0 skipped**. Tests validate both real historical metadata readers; deterministic archives; exact donor/run/head/source-report binding; real PE import parsing; rejection of alternate architecture/imports, changed DbServer/history, duplicate/traversal/link entries and failed partial publication. Synthetic executable tests exercise packaging only. Neither a new Windows MapServer nor the modern full-data source tree was built or executed by this suite.
