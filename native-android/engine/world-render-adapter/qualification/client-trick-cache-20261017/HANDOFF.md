# Complete historical Trick cache input

Source commit: `3d2d20b99`. Host receipt SHA256: `b393880118a5a6a1c9187c244c3a6c8eb1c801700cf7a0fa7e5f27a8078edb00`.

All 3,644 persisted TrickInfo rows, 106 StAnim children and 273 AutoLOD children pass 84,839 controls per release, ASan and UBSan mode. Standalone production exports are independently checked. The compact host64 owner occupies 208,600 bytes; records and child views decode lazily from a retained exact body instead of allocating runtime trees.

Exact retained `tricks.bin`: 13,537,052 bytes, SHA256 `cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1`. Original donor archives and deterministic committed compressed body remain preserved. Admission requires the same already-qualified opaque TexOpt cache, whole-body hash, observed schema identifier, historical import label and exact file/source-age associations. Complete unknown flags, hierarchy and source ordering remain intact; highest ordinal owns duplicate case-insensitive historical names.

The oracle executes unchanged original typed readers and original numeric/group-tray setup statements. EArray allocation and reverse-name ownership use explicitly labeled host observers; original Win32 runtime layout, schema CRC recomputation, dictionary insertion, animation-track binding and full CLIENT execution are not claimed. LeakSanitizer is disabled for the established container limitation; ASan and UBSan checks pass.

Budget admission charges whole configured loader reservations, existing TexOpt metadata/static reserve, the new compact owner and a 32 KiB preparation/static reserve before acquisition/allocation. Cancellation and malformed/truncated fields, arrays, timestamps, digest errors, allocation failures, generation mismatch, aliases and rollback are exercised.

This closes persisted historical TrickInfo/StAnim/AutoLOD grammar and a narrow original scalar projection. Captured SERVER Trick names/flags still need a separately proven ownership/generation association; current CLIENT animation tracks, AutoLOD/model resources, active Basic/composite namespace, capabilities, assets and renderer Surface remain missing prerequisites. No actor, material, world or live permission is minted. Android builds/execution and physical Thor execution have not been performed for this module.

Reproduction (temporary compiler directory must exist):

```sh
mkdir -p /dev/coh-build-scratch
TMPDIR=/dev/coh-build-scratch python native-android/engine/world-render-adapter/check_trick_cache.py --actual-cache /workspace/scratch/9174d12e2a11/tex-parser-authentic/tricks.bin --output /tmp/FRESH-trick-host.json
```

Only additive world-render-adapter paths changed; no captures, servers, network acquisitions, APK rebuilds or protected gameplay/build changes.
