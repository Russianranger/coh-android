# Exact root-model Trick resource obligations

Source `853c38349`; host receipt SHA256 `f6f0dbb5ee72b823f10756ab70ee832b12c03a998aa55883120d40e6af4b565c`.

The historical name/source-file correlation touches 528 distinct Trick rows on 1,959 named root-model observations. The retained dependency ledger identifies every original owner/file/slot/ID, source ordinal, exact model/GEO and historical row/source-age for 32 observations using 13 StAnim rows and 50 observations using three AutoLOD rows. All persisted child fields, wire offsets and hierarchy remain available. No rows or required resources are silently removed.

CLIENT and SERVER variants each pass 1,682 source controls in release, ASan and UBSan. Unchanged original setStAnim and animFindTrackInSkeleton execute with explicitly labeled skeleton/loader/string observers. Exact isolated setup-animation and conditional AutoLOD-copy blocks execute with host storage observers. Three semantic mutations are refused: requiring both texture tracks, using the second child and filling later LODs after the original first eligible pair. Generated source and all six binary hashes are retained in the receipt. LeakSanitizer remains disabled for the established container limitation.

StAnim requires successful tscroll/name lookup and at least one source bone track 0/1; only then can setup set STANIMATE. AutoLOD child presence alone does not establish runtime selection: existing LOD dictionary precedence, force_auto/no_lod/legacy/cape/tray, GEO default/reductions/radius/distances, model names and object library resolution remain required. The three historical AutoLOD rows are conditional obligations, not evidence that all 50 models currently select them.

No actual animation or LOD resource was loaded. No complete LOD function, original allocator/string implementation or runtime ABI is qualified. Active CLIENT generation/namespace, material/world permission, Android execution and physical qualification remain false. All former source/evidence files remain frozen; this tranche adds four source files plus this evidence only. No new captures, downloads, CI, worktrees, APK builds or protected path changes.

Reproduce with a fresh receipt path:

```sh
mkdir -p /dev/coh-build-scratch
TMPDIR=/dev/coh-build-scratch python native-android/engine/world-render-adapter/check_trick_dependencies.py --actual-cache /workspace/scratch/9174d12e2a11/tex-parser-authentic/tricks.bin --resources /workspace/scratch/9174d12e2a11/resource-evidence-38994607354/evidence/capture/resources.cohres --root-partitions /workspace/scratch/9174d12e2a11/source-rigid-special/native-android/engine/scenecatalog/evidence/root-model-texture-partitions-38994607354.json --output /tmp/FRESH-root-trick-dependencies.json
```
