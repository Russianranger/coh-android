# Source asset to native renderer bridge

This coordinator adapter connects the qualified asset loader/GEO kernels to the
generic renderer. It admits original-path/generation GEO models and source
material resolver rows, rather than a compiled mesh fixture or an asset-specific
renderer branch. Gates 22–24 remain scoped: this adapter does not establish full
map closure, original-PIGG qualification, broad rendering coverage or a complete
native gameplay client.

`coh_asset_render.h` owns a bounded mesh/texture CPU cache. `acquire` pins copied
geometry, partition state and decoded RGBA independently of loader cache trims.
`release` makes a mesh eligible for LRU eviction; `trim` frees only unpinned
meshes and unreferenced textures. A destroy attempt with pins returns `COH_STATE`
without modifying the bridge. Counts include the bridge object, cache tables,
allocation headers, CPU geometry/RGBA and temporary decode buffers. libc allocator
overhead, loader-owned memory, renderer-owned memory and GPU allocations are
separate budgets. Default limits are 32 MiB CPU, 32 meshes and 64 textures;
individual workspace, encoded stream, model, vertex, triangle and material limits
are explicit. Limit failure does not publish a partial mesh; cache warming and
unpinned eviction may occur before failure.

Only authentic-qualified GEO v0/v7, unit model scale and rigid geometry with no
skin or extra UV channels are admitted. The separately accepted character/rig
adapter is unchanged. Original index/material partitions and model-local
positions/normals are copied exactly. Both old-world UV sets use one source
`V=float32(1-diskV)` conversion, then the resolver's original ScaleST0/ScaleST1.
All matrices are supplied already composed in source column-major convention;
the bridge never changes position, winding, group transforms or instance scale.

The map/trick frontend resolves original GEO texture names, aliases, source
fallbacks, low-profile family, tint and sampler state. Each returned path is
copied before source read callbacks. No missing texture is invented here.
`resolver_generation` is part of cache identity: change it for effective trick,
alias or tint changes, or copy each material packet and set per-instance tint
before direct renderer submission. Shader families are the renderer's Multiply,
Dual and AddGlow; AddGlow still needs independently qualified authentic source
pairing. Mip-linear samplers are rejected because this adapter uploads mip zero.
Other unsupported families fail explicitly.

The genuine stock `grey.texture` exposed a new integration gap: the asset
module's compressed DDS subset rejected its source ARGB8888 payload. This bridge
adds native exact-mask BGRA-to-RGBA conversion matching the accepted offline
converter in `tools/material_fixture/prepare.py`. It requires the exact 32-bit
ARGB masks, 2D layout, bounded complete mip envelope and nonoverlapping output;
only mip zero is emitted. Generic compressed DDS uses the unchanged qualified
asset/core decoder. This does not silently broaden the asset module's existing
typed-format claims.

All calls and callbacks use one owner thread, with no callback reentry. Perform
bounded asset admission/prewarming before the render frame loop; cached acquire
does not reread/decode the model. `prepare` synchronously uploads retained RGBA
through caller callbacks only when a texture lacks a handle. The upload callback
may retain its GPU handle but must not retain the RGBA span. `submit` borrows
pinned mesh geometry until renderer flush completes. Release pins only after
flush. A partial submission failure retains earlier queued submissions under
the renderer's existing rules; drop that frame or flush deliberately.

For Surface loss, first call renderer `surface_lost` to discard queued borrowed
spans, then bridge `surface_lost`. Release callbacks receive `context_alive=0`
after actual context destruction and must issue no GL calls. CPU meshes and RGBA
survive; the replacement context gets fresh uploads with the new explicit
generation. Drop/restore GL sampler bindings around the accepted actor's separate
renderer as required by that adapter. The bridge owns no shader/GL implementation.

Reproduce the new adapter checks without repeating independent module suites:

```sh
python3 native-android/engine/bridge/check.py \
  --corpus /workspace/scratch/552733ac6bdc/next-world-raw \
  --source-root /workspace/scratch/bd17f7dd7d03/coh-native-coordinator \
  --ndk /workspace/scratch/bd17f7dd7d03/toolchains/android-ndk-r28c \
  --output /tmp/coh-bridge-qualification.json
```

The checked receipt records 2,254 ownership/lifecycle/capacity assertions on
three genuine floor/bench models and six material partitions; 19,852 float
components and 1,560 indices are byte-exact against the hash-pinned original
`uncompressDeltas` plus an independent source UV/partition adapter. All 39,040
uploaded texture pixels match Pillow, including actual stock grey. The ARGB
adapter has 120 varied-channel cases and 960 malformed/capacity/overlap cases.
ASan/UBSan pass the ownership suite; LSan is unavailable in this environment.
One thousand cache acquire/release cycles keep counted storage constant; peak
counted bridge memory is 462,508 bytes. The cumulative texture-decode count is
seven in the full suite because a deliberate missing-secondary negative first
warms one primary texture; the successful three-mesh/lifecycle path decodes its
six unique textures once and reuploads without decoding after Surface loss.
An 80 KiB limit case refuses admission and returns to the original cache baseline.

Strict Android ARM64 API 26 direct compile/link with `--no-undefined` passes:
69,080-byte ELF SHA-256
`c7a53301faa12c26bd75cc035f92cf725ac54aa8b4bd7f485013c6079f90fb7f`.
This receipt is host/source/build evidence. Android execution, real Adreno
rendering, integrated dynamic loading and new physical Thor acceptance belong to
the coordinator's client qualification. No FPS/performance or physical acceptance
claim is made by these isolated checks. Roll back additively after inspecting
integrated JNI dependents; retain the accepted client and earlier evidence.
