# Focused original Map initial-send observer

This is a new nonshipping diagnostic role for the missing response after the
physical Thor diagnostic received GROUPS, queued REQALLENTS and observed a peer
transport ACK. The device receipt does not establish server dispatch or a cause
for its timeout. The new role observes the actual same-session original server
path. It grants no character, normal-authentication, actor or world authority.

The retained accepted fresh Map build from run39099315295 is a Win32/i386
VS2026 OptDebug PE, SHA256
`73e6c724fcdd9b1caaa03bd675d38d075cc452575539cb99b19b6d1124113aba`.
Its 6784966-byte ZIP, SHA256
`cd27cda26fae3bf5ab76889f82c2b467cc97423c260e69c997a62cff9756156b`,
has45 members and no object, static-library or link-response closure. A changed-TU
relink cannot be reproduced from that artifact. One build of the new MapServer
target is necessary. This is a new-role build; no accepted suite, qualifier,
Android package, crypto build or old helper execution is requested.

## Build procedure

The root workflow owns execution. It first admits the current raw/Git source and
the unchanged published startup inputs, then uses these existing source-only
stages in a new private `C:/isrc` tree:

```powershell
python tools/android/interactive/map_startup_inputs.py --output out/native-inputs --cache out/asset-cache
python tools/prepare_map_startup_source.py --output C:/isrc --animations-pigg out/native-inputs/server-animations.pigg --animation-manifest out/native-inputs/server-animation-manifest.json
python native-android/engine/scenecatalog-server/stage_groups_capture.py --source-root . --already-staged C:/isrc
python native-android/engine/scenecatalog-server/fresh_callback_observer/stage.py --source-root . --already-staged C:/isrc
Copy-Item out/native-inputs/map-startup-inputs.json C:/isrc/map-startup-inputs.json
python native-android/tools/server-initial-observer-20261018/recipe.py stage --source-root . --already-staged C:/isrc
python native-android/tools/server-initial-observer-20261018/recipe.py verify-stage --source-root . --already-staged C:/isrc
```

Configure and build from `C:/isrc`, preserving the accepted target,
configuration, generator and input policy:

```powershell
cmake --preset vs2026 "-DPATCH_EXECUTABLE=C:/Program Files/Git/usr/bin/patch.exe" -DCOH_PG_PERSISTENCE_TESTS=OFF
cmake --build out/build/vs2026 --config OptDebug --parallel 4 --target MapServer
```

Record from the repository, after the workflow repeats current source and whole
published-input admission. The record command performs no compilation or runtime:

```powershell
python native-android/tools/server-initial-observer-20261018/recipe.py record --source-root . --already-staged C:/isrc --binary C:/isrc/out/build/vs2026/bin/OptDebug/MapServer.exe --cmake-cache C:/isrc/out/build/vs2026/CMakeCache.txt --output "$env:RUNNER_TEMP/server-initial-compile"
```

Upload only the compile directory as the selected binary artifact; put compiler
logs and other workflow evidence in a separate artifact. Export its actual
artifact ID/digest and the SHA256 of `compile-only-receipt.json` as job outputs.
The dependent Linux job binds the download to this successful build job, same
run/attempt and source revision, then executes:

```sh
python native-android/tools/server-initial-observer-20261018/recipe.py verify-artifact --source-root . --compile-directory "$COMPILE_DIRECTORY" --expected-source-revision "$GITHUB_SHA" --receipt-sha256 "$COMPILE_RECEIPT_SHA256"
```

The importable equivalent is
`verify_artifact(compile_directory, source_root, expected_source_revision, receipt_sha256)`.
It returns `(compile_receipt, stage_receipt)` and raises on refusal.
`artifact_names(source_root)` returns the exact non-receipt file inventory;
the selected artifact additionally contains only `compile-only-receipt.json`.
`checkout_closure(source_root)` and `unchanged_checkout(source_root, pins)` bind
the current inherited and new source suppliers before and after operations.

## Admission and scope

The compile schema is `coh-server-initial-observer-compile-v1`, build role
`nonshipping_same_owner_initial_send_observer`. The new source-stage receipt is
`native-server-initial-observer-build-input.json`. Every new hook is reversed
before all inherited fresh-role source checks. All actual patched source bytes,
new headers/implementations, inherited inputs and the CMake cache accompany the
PE. The verifier rejects extra files/directories, link aliases, duplicate JSON
keys, source changes, mismatched receipt pins, wrong revisions, a DLL/x64 image
or a different generator/platform/configuration.

The cache establishes the recorded generator/platform/configuration; it does
not independently establish the complete compiler/SDK binary closure. The
recipe never claims external archives were verified by its record command: the
workflow separately retains its whole-input checks before and after building.
No object-cache reuse, accepted-role equivalence or qualifier replay is claimed.

The new adapter's environment key is
`COH_NATIVE_INITIAL_SEND_LEDGER_OUTPUT`; runtime orchestration must precreate the
private owned output `server-initial-ledger.json`, bound4096 bytes, and project
only the fixed `coh-server-initial-ledger-v1` numeric fields after owned service
retirement. The Map PE substitution and this explicit diagnostic output are the
new runtime inputs. Existing original service, DB/Map handoff, owner and cleanup
guards remain required. The current device Map and this nonshipping Linux/Wine
role are distinct binaries; a result from this role does not establish device
server equivalence.

`test_recipe.py` contains only new admission-envelope and storage controls.
Its synthetic PE and explicit inherited-checker doubles are labeled controls,
not real Windows compilation or original source/runtime qualification. A owns
the separate real-source hook-reversal and portable ledger controls.

## Prepared-baseline correction after the first actual attempt

Run39176566626 admitted the published source and passed the inherited fresh
source stages, then refused the new hook supplier's full-file baseline guard.
No compiler or original service transaction ran. The trace did not name the
failed file or retain its actual staged bytes. Exact source reconstruction
shows that the old hook constant incorrectly selected raw `svr_tick.c` SHA256
`790635fec2f21e49981c776815eb8e927e79ef5a277324b0e3601cc3b4bbade0`.
The accepted preparation chain produces73504 bytes with SHA256
`a3810c112556b258ee2456a51eb28d6afeefd14b81c2fa97ed431659ae42a3d5`,
also recorded in the accepted nested monorail receipt. The other two newly
hooked TUs retain their exact raw upstream hashes through that chain.

`prepared_inputs.py` reconstructs all three files through the fixed ordered
PostgreSQL, game-loopback, mapserver-progress, character-events and monorail
patches. It applies only selected TU hunks in a new private temporary directory,
checks original/patch/final hashes and records each transition. No old preparer,
compiler, service or host qualifier entrypoint runs. The new recipe also checks
every reversed hook file present in the inherited startup hash closure against
that prepared hash before artifact admission.

The corrected source integration is run with an explicit new output:

```sh
python native-android/tools/server-initial-observer-20261018/check_integration.py --output native-android/tools/server-initial-observer-20261018/qualification/baseline-repair-01/source-integration.json
```

The earlier raw-input source proofs remain historical. The new local check
materializes the selected28-member composition and all three prepared hook
inputs; it does not materialize every one of the47 inherited startup files,
including the unretained generated animation-certificate table. The actual
workflow's full private `stage` and `verify-stage` checks still require
`all_inherited=True` before compilation and recording. The corrected baseline
constant leaves the hook edits and all four compiled overlays unchanged; their
retained portable host execution evidence is reused without replay.
