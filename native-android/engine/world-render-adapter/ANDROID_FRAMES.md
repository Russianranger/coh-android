# Bounded-frame standalone Android qualification

The new driver admits both exact ABI artifacts and requires the recovered frame
corpus: at least32,284 checks,1,025 ordered draws, three batches and selective
binding. Release, ASan and UBSan results must be identical, as must both build
receipts' expected native results. The executing frame driver, delegated driver and common admission helper are
pinned in qualification and both ABI receipts; absent or changed Python bytes
refuse before device execution. Every source, original fixture and ELF hash
is checked by the existing continuation adapter driver. An old shared-geometry
artifact without the new frame fields refuses. Build receipts always retain
`executed=false`.

Coordinator build commands (clean committed checkout; pinned NDK installed):

```sh
python3 -m unittest discover -s native-android/engine/world-render-adapter/tests -p 'test_frame_driver.py' -v
python3 native-android/engine/world-render-adapter/check.py --source-root . --sanitize --ndk /tmp/native-primary-ndk/android-ndk-r28c --output native-android/results/frame-adapter/qualification.json --android-output native-android/results/frame-adapter/android
python3 native-android/engine/world-render-adapter/run_frames_android.py --source-root . --artifacts native-android/results/frame-adapter --validate-only --output native-android/results/frame-admission/receipt.json
```

Upload `results/frame-adapter/` completely, including `original_matrix.h`, then
restore it at that path on the same source commit in the Android13 job. Inside
the existing pinned Android emulator runner, execute:

```sh
python3 native-android/engine/world-render-adapter/run_frames_android.py --source-root . --adb "$ANDROID_HOME/platform-tools/adb" --serial emulator-5554 --artifacts native-android/results/frame-adapter --output native-android/results/frame-execution/receipt.json
```

Upload the complete frame-execution directory even on failure. The delegated
`execution/receipt.json` and numbered logs preserve command attempts, exit codes,
actual native-result validation and cleanup independently. Evidence directories
must be fresh; prior evidence must not be erased to rerun. The outer receipt
retains both runner hashes, source identities, both binary hashes and the exact
expected/result corpus. Admission-only cannot claim Android execution. This
driver executes x86_64 only on Android13 emulator; ARM64 is build-qualified only.
No APK, GLES, physical Thor or real world session is qualified by these fixtures.
No shared workflow or accepted client was edited for this tranche.

## Upstream bridge assessment

Worker B's `runtime_graph.h` (`1d98a3c70`) now exports immutable source
root, child and node views. Root/edge order and original matrices survive;
node views retain authentic saved slots and separately observed future owners.
`CohRuntimeGraphBinding` binds source/catalog/runtime/run identities, while
borrowed catalog/snapshot storage remains caller-pinned through retirement.
This supersedes the earlier diagnostic-only snapshot interface assessment.

These views support an eventual add-only, off-thread graph-to-draw mapper:
walk active roots in retained order, compose source root/child matrices, inspect
node model wire metadata, resolve actual GEO/material/texture owners through
qualified adapters and emit bounded ordered `CohWrDrawInput` spans. External
`empty_owned_future` nodes retain their real identity without inventing meshes.
The mapper must reserve pinned graph/catalog/snapshot, decoded resources,
traversal scratch and candidate renderer storage in one aggregate inventory.

The source graph explicitly grants no live GROUPS, resource or actor permit.
A graph instance cannot yet supply required renderer asset/render-semantic
prerequisites or selected actor/full-update closure. `CohWrInput` remains the
appropriate boundary once those producers expose exact resources and matching
live transaction/catalog generation. No conversion from source graph success
to complete `CohWrReceipt` is implemented. Whole-world traversal is not a flat
renderer list: preserve instance transforms and qualified visibility/LOD, with
bounded working sets and independently verified ownership.

Frame visibility is a qualified producer choice over an already complete
snapshot, never a way to omit unresolved dependencies. Keep source snapshot
capture, graph readiness, asset readiness, actor readiness and encrypted-auth
acceptance as separate qualification facts.
