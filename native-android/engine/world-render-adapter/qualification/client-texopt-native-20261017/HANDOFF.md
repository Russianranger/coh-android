# Compact native historical CLIENT TexOpt reconstruction

Source: `725070a9e0439abc237eb6e91898273abe2b43f4`.

The host receipt is `host.json`, SHA256 `5eee268d5ab2871ee6faf63361f5e123745669cdd2637aeb05c16f80c1f763bd`.

Release, ASan and UBSan each pass 1,515,598 controls, including all supported historical rows against unchanged original CLIENT `setupTexOpt`, original typed cache readers, and original Surface preparation/lookup. The native component retains a 319,752-byte metadata owner over one pinned exact raw cache and constructs an independent 6,192-byte stored/postprocessed record. These sizes are 64-bit host observations.

All 14,715 ordinary persisted TexOpt records are validated. Postprocessing succeeds for 14,714. Ordinal 10,499 retains its original UTF8 replacement bytes and refuses as outside the source-qualified ASCII postprocess domain. No name repair, silent deletion or replacement occurs.

The test preserves exact source order, duplicate winner/source filename, every stored and computed field, all13 layers and scale/scroll/default distinctions, cancellation/allocation/digest/budget rollback, path/generation refusal, and independently retained record lifetime after cache/Surface/loader retirement. Header/source functions and parser declarations are regenerated from readonly source and byte-compared. The qualifier admits its entire source closure before helper imports and checks identities after execution.

Reproduce from repository root using retained exact bodies (no acquisition):

```
python native-android/engine/world-render-adapter/check_texopt_setup.py --actual-cache /absolute/path/tricks.bin --actual-states /absolute/path/seqstatebits.bin --output /fresh/external/host.json
```

The raw cache and Surface bodies remain preserved by the earlier deterministic compressed-body retention commits. Their source/run acquisition identities are documented in `CLIENT_TEXOPT_NATIVE.md` and the earlier cache/Surface evidence. Original archives are unchanged.

This is source/host qualification. It does not recompute the original compiled table CRC or execute a real CLIENT, Android ABI, Android application, Thor, BasicTexture/composite factory or live game. Historical generation labels prevent local preparation mixing; they are not active CLIENT, scene or resource generation authority. All material/world authority remains false.

Remaining prerequisites: exact active Basic namespace/overlay and original composite factory, directory/locale/scene/definition substitutions, full Trick/AutoLOD semantics, capability/fallback profile, all layer asset/texture/GPU owners and matching live generations. Existing protected renderer/asset/Support sources were read only.
