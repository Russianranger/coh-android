# Bounded legacy Atlas rigid geometry

The additive CPU adapter now accepts the conservative rigid subset of GEO versions 0 and 8. Versions 2–7 remain closed. This closes a geometry-format dependency for the dominant legacy Atlas files without changing protected assets, renderer, bridge or build files.

The selected authentic body is `object_library/Buildings/Elements/signs/Neon/neon.geo`, SHA256 `83933b54db373bf83e0a73f128068b63b8375e00f0f288b6f6e0e0637792c9e7` (3,684 bytes). `_sign_Neon_BarVERT` is an observed root-reachable source model at owner file 457 / slot 3, resource ordinal 35283. Its original disk row is **3**; its sorted runtime row is **0**. These identities must not be interchanged. The candidate report and exact capture/provenance identities are retained in `rigid-atlas-v0-pins.json`. Case-folded import provenance establishes a lookup candidate, not the server's directly opened file hash or matching source generation.

The original `readModel` uses a fixed 216-byte `ModelFormatOnDisk_v2` record for version 0. Its seven pack descriptors map to the shared tris, vertices, normals, UV, weights, matrix indices and grid channels; legacy has no secondary UV channel. Original assertions require serialized trick, grid-cell, collision, tags and portal pointers to be null. The adapter enforces these assertions, rejects nonzero legacy flags pending CLIENT semantics, and preserves existing refusal of bones, unsupported channels, alternate pivots, nonunit scale and unsupported material state. Existing exact hash, model, partition, generation, reservation, cancellation and retained pin checks remain in force.

The legacy envelope retains the original GetVrml four-byte bias workaround: payload begins at the first header word plus eight bytes. Authored malformed controls cover the full fixed record and pointer constraints. The authentic 90-vertex / 56-triangle model produces a complete renderer packet equal to the unchanged original delta decoder, original partition order and source V-coordinate flip. Material and loaded-generation suppliers in this test are explicitly fixtures. They grant no authentic CLIENT material, resource generation, actor, world or rendering admission.

`check_rigid_legacy.py` runs release, ASan and UBSan controls and compares the entire actual and authored packets with original-source decoding. It also extracts unchanged `readModel`, PackData, PolyGrid and legacy disk definitions, compiles a freestanding true 32-bit Linux consumer, checks 14 original layout scalars from its object, and attempts execution. The destination Model is a narrow test structure containing source-assigned fields; this is not a full original client build. Successful execution compares 52 metadata/pack scalars. The current local kernel refuses ELF32 execution with errno 8; the retained local receipt explicitly sets `original_consumer_executed=false`. Compilation/layout checks do not qualify consumer execution.

For the coordinator's minimal Ubuntu host-only follow-up, require execution:

```sh
python native-android/engine/world-render-adapter/check_rigid_legacy.py \
  --actual-geo /tmp/FRESH-NEON/data/object_library/buildings/elements/signs/neon/neon.geo \
  --output /tmp/FRESH-RESULT.json \
  --oracle-output /tmp/FRESH-ORACLE \
  --require-original32
```

Both result path and oracle directory must be fresh. The oracle directory retains generated source, object, executable, layout bytes and execution output or exact refusal. Retain that directory as evidence, including failures. GNU C compiler, binutils, Python, zlib/OpenSSL development libraries and the existing original-delta qualifier dependencies are required. No 32-bit libc is needed: the consumer links with `ld -m elf_i386` and uses Linux system calls directly. The host kernel must actually support ELF32 execution. The required flag exits nonzero and records `passed=false` when execution is unavailable.

A's `acquire_resource_candidates.py --source-geo 'object_library/Buildings/Elements/signs/Neon/neon.geo'` retrieves this one exact body from the existing manifest/candidate pins. Reuse the already verified local cache during development; no whole archive or 391-body re-download is needed. No MapServer, AuthServer, APK or accepted-client retest is part of this qualifier.

Remaining gates include matching live catalog/resource generation, actual CLIENT trick/material/LOD decisions, complete texture and Surface ownership, authoritative actor state and atomic world publication. CPU geometry qualification does not close those gates. This module has not yet been built for Android or executed on Android/Thor in this legacy scope.
