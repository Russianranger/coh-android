# Gate 22: opt-in indexed native asset module

Implementation and host qualification cover the subset below. This is **not a passed full-game gate**, Android qualification or Thor acceptance. Existing APKs, JNI, root builds, scene code and gates 19–21 are untouched. No code branches on a particular asset filename or model ID.

## Public API and integration

- `coh_asset_loader.h`: original virtual path plus content generation; transactional PIGG index mounts and explicit loose-file mounts; O(1)-average hashed case-insensitive/slash-normalized lookup; owned lazy reads; acquire/release pins; bounded LRU cache and accounting; bounded dependency traversal with cycle detection.
- `coh_asset_geo.h`: original GEO envelope/header/model/material metadata; caller-owned decompressed header workspace and immutable payload views; bounded packed-stream extraction; original delta channels into caller-owned float/U32 arrays. Geometry, source scale, texture names and material triangle partitions are data for a renderer adapter.
- `.texture` wrapper metadata and qualified native DDS DXT1/3/5 decoding; complete raw animation track admission through the accepted `coh_anim_header`/`coh_anim_bone` kernels; Ogg/Vorbis identification.
- Optional `coh_asset_audio.h`: forwards pinned compressed bytes to existing `coh_decode_ogg`; owned `CohDecodedAudio` is released with existing `coh_decode_release`. Compile `coh_asset_audio.c` and link the existing native decoder, or enable `COH_ASSET_WITH_AUDIO` after adding `native-android/decode`. No codec fork or fixture fallback.

Create a loader with explicit entry/source, heap, decoded/stored asset, resident byte and cache-entry ceilings. Mount immutable archive sources using a synchronous exact-read callback. Source contexts/handles and contents must remain alive and unchanged until loader destruction. For external asset packs already extracted by the current importer, mount each original relative path with `coh_asset_mount_file`; the importer retains responsibility for ZIP extraction, manifest/checksum verification and Android FD/SAF ownership. No filesystem or network operation is hidden in this module.

All calls and callbacks use one owner thread. Callbacks must not reenter the loader, mount sources or destroy it. An acquired blob owns stable bytes until matching release; retain a pin while borrowed typed views are used. Latest mount wins generation-zero requests, exact generations remain available. Duplicate path+generation mounts fail. A destroy attempt with live pins returns `COH_STATE` without changing the loader. Null/already-destroyed teardown is safe. Eviction never touches pinned data. `coh_asset_trim` releases all unpinned resident data.

Dependency traversal asks a caller-owned source parser for original dependency IDs. IDs are resolved immediately before another callback, aliases are not guessed, and cycles terminate. This separates reliable lookup/ownership from map/group/trick semantics that gate 23 must qualify. On an error no graph pins remain retained; the `visited` count records completed nodes. Cache state may warm or evict during an unsuccessful request, but no partial requested blob is published.

Cancellation is polled before work, between archive records, during source reads/decompression and between graph nodes. Read/decode work stays off renderer and audio callbacks. Renderer bridge must copy/own GPU submissions according to the renderer contract; the loader never owns GL handles. Surface recreation does not invalidate the CPU cache. The audio adapter is an off-thread call; its existing decoder owns a separate bounded budget, outside loader counters.

## Supported formats and source provenance

Source files and LF-normalized SHA256 receipts are recorded in `evidence/host.json`:

- Ouroboros `libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h`, `src/utils/piglib.c`: little-endian PIGG archive marker `0x0123`, record marker `0x3456`, 16-byte base archive header, 48-byte base file header, 32-bit offsets, zlib-wrapped compressed payloads and retained MD5/timestamp identity fields.
- `libs/UtilitiesLib/src/components/datapool.c`: 12-byte pool header and U32 length-prefixed pool items; original name strings are preserved. Lookup follows original slash conversion and case-insensitive stash lookup; traversal/absolute paths are rejected at this new mount boundary.
- `Game/src/render/tex.h`: original 32-byte TEX/TX2 wrapper and payload position.
- `Common/seq/anim.c`: GEO envelope/table layout and scalar `uncompressDeltas`. Original function is hash-pinned, compiled independently through the existing reviewed shim, and executed on admitted authentic streams.
- Reused unchanged code: `native-android/src/coh_assets.c`, `coh_dds.c`; optional `native-android/decode/coh_decode.c` and its byte-pinned Ogg/Vorbis dependencies.

PIGG base-record version declarations 1/2 with record size at least 48 and extended archive/record sizes are admitted. Shorter historical records, HOGG, encrypted archives and 64-bit reserved offsets are unsupported. Cached header DataPool structure and IDs are validated but data is not retained as a second cache. MD5 fields are preserved and exposed, **not recomputed**; trust/integrity is still established by the existing external pack manifests before mount. zlib streams must end exactly at the declared stored and decoded lengths; trailing compressed bytes are rejected.

GEO layout implementations admit v0 and v2–v8. This recovered authentic corpus qualifies **v0 and v7 only**. Unrepresented versions need independent authentic corpus qualification before production admission. Vertex positions/normals/UVs and indices retain source binary32 delta behavior. UV `1-V`, inverse bind, bone palettes, skin weights, tangent generation and GPU packing remain explicit downstream adapters; they are not silently transformed here. Header parsing validates all records/pack spans/material references in a bounded linear walk. Per-index model access walks earlier records; callers processing very large model tables should build their own bounded index in gate 23 rather than repeatedly accessing indices from zero.

Unsupported typed paths: TGA, ARGB8888/uncompressed DDS, unsupported DDS families/cubemaps/volumes, raw animation delta modes rejected by the accepted kernel, animation blending/rig reconstruction beyond that kernel, non-Vorbis Ogg and streaming music. Ogg identification is not full-stream validation; the optional existing decoder supplies CRC/EOS validation and its current format/clip limits. No complete map/group/trick dependency resolver, external ZIP reader, asynchronous IO scheduler, game asset hot reload or production Android importer adapter is supplied.

## Reproduce host qualification

From repository root:

```sh
python3 native-android/engine/assets/check.py \
  --output /tmp/coh-assets-proof.json \
  --source-root /path/to/full/checkout \
  --corpus-root /path/to/recovered/corpus-root \
  --sanitize
```

`--output` is a JSON **file**. Full source root must contain `upstream/ouroboros`. The recovered corpus root used in this run was `/workspace/scratch/552733ac6bdc`, holding hash-pinned top-level GEO/textures and `coh-next/native-android/tools/*/corpus`, plus the integration assets. The test discovers files through existing acquisition pins and validates SHA256 before using them; it does not download or embed game assets. Without `--corpus-root`, synthetic unit tests run but `host_qualified` remains false. Standalone `CMakeLists.txt` is an optional subdirectory, never included by existing APK builds.

Current receipt:

- 20,502 C assertions; 13 SHA256-pinned original files: 55 models in two authentic GEO files, 464 packed streams, two texture wrappers, eight animation files across Huge/Male rigs, one Ogg sound.
- 220 delta channels / 62,059 scalar values byte-exact against independently compiled original `uncompressDeltas`; every GEO table/model/packed-stream result matches a separate Python implementation. 20,480 texture pixels exactly match independent Pillow DDS output.
- Original-format synthetic PIGG containers carry authentic payloads with alternating compressed/stored entries. This exercises generalized lookup and byte-exact extraction, **not an original PIGG archive execution oracle**. An original archive corpus/source-loader comparison remains pending.
- 1,832 malformed/truncated probes, including 1,000 archive mutations; precise missing paths, duplicate identity rollback, cycles/capacity, cancellation, bad zlib/trailing bytes, path traversal rejection and pinned-cache pressure.
- 1,000 repeated acquire/release/trim cycles return tracked heap to the same indexed baseline. Measured peak counted module heap 176,086 bytes and resident payload 133,838 bytes under explicit 4 MiB / 512 KiB ceilings. Caller buffers, C stack, libc allocator overhead and existing codec heap are excluded. Timings are host diagnostic durations, not Thor or gameplay benchmarks.
- AddressSanitizer and UndefinedBehaviorSanitizer pass. LeakSanitizer could not inspect `/proc/.../task` under this execution environment; an initial leak-enabled run failed in LeakSanitizer setup. The recorded rerun uses `detect_leaks=0`; no leak-sanitizer pass is claimed.

No Android ABI build, emulator rendering/lifecycle result, physical Thor test, Atlas Park/Kings Row full map load or device memory/FPS claim is included in this worker receipt. Coordinator owns Android cross-build and cross-module adapters; these must be recorded separately.

## Integration and rollback

Coordinator can cherry-pick the self-contained assets commit after fetching `native-android` and checking for newly added `engine/assets` paths. The library stays opt-in until a loader→geometry/material renderer bridge and asset→native decoder/audio bridge pass authentic cross-module tests. The live Session Client is not a dependency. Existing accepted DLL-free native kernels are reused without edits.

Before production use, qualify real PIGG containers, other supported GEO versions and additional asset classes; implement Android immutable read callbacks and external-pack index admission; add a source-authentic map/group/trick dependency frontend and bounded streaming selection. These are explicit gate 22/23 requirements rather than passed behavior. Roll back through an additive revert of this module commit and coordinator adapters, keeping prior APKs and their receipts unchanged; never reset the shared branch.
