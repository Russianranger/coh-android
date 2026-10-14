# Authored bounded WALK scene input

Gate 19 adds the actual Atlas trainstation floor and a second actually authored
bench instance to the existing persistent native client. The accepted original
benchmark `world.bin` remains unchanged. This does not claim complete Atlas
loading, lights, materials, scene sorting or live server interoperability.

The source map, fixed source declaration, release GEO and DDS identities are
pinned. `_trnstation_infloor` is model 5 in legacy unversioned `trainstation.geo`:
71 source vertices, 88 triangles, two material partitions. The selected bench is
`grp141205 -> grp141259` at `Pos -29.5 32 -41.5`; it uses the exact accepted
`modern_bench_2wide__mbench` geometry/materials, rather than an invented obstacle.
Every ancestor transform is retained. Source default material collision flags
are derived after the unchanged `createCTri` validity test. Disk PolyCell offsets
and triangle references are decoded without relocating x86 pointers.

The source floor detail alias `mono_station_floor_det` is absent from the
published fixture archives. The selected real base textures use the unchanged
original legacy `texFindVerify(..., grey_tex, ...)` fallback. The exact original
function and binding assignment are compiled and exercised with the absent
alias. This gives source-faithful missing-asset behavior, while detailed floor
appearance remains an explicit asset closure limitation. The fallback is the
already accepted original stock grey texture, not generated pixels.

The `COHWALK1` immutable container carries four render parts, six real textures
and 276 collision records in 202,880 bytes. Mesh vertices are baked through the
native source-transform implementation and checked against the independent
binary32 reference. The native parser proof compares every indexed render
position to its collision record byte-for-byte (828 vertices). It exercises
malformed count/span/reserved fields, truncation, misalignment and unchanged
failure outputs under UBSan. The runtime builds an original CTri cache over the
small selected closure; disk grid membership remains provenance evidence.

```sh
python3 native-android/tools/walkable_fixture/check.py \
  --source-root . \
  --accepted-assets native-android/results/accepted-session-assets \
  --corpus native-android/results/session-walkable-corpus \
  --output native-android/results/session-walkable-assets \
  --evidence-output native-android/results/session-client/walkable
```

Default qualification verifies all 1,585 immutable original trick blobs and
requires the three new floor direct declarations to resolve only to the pinned
monorail file. Sparse local preparation can explicitly skip that complete-tree
audit; its metadata records the new floor alias closure as pending. CI must not
skip it. No character, benchmark rendering or previous physical gate is retested
by this tool.

`coh_walkable_scene_parse` checks the contiguous immutable container, 16 MiB
maximum bytes, at most 32 parts, 16 textures and 8,192 collision triangles. It
borrows caller-owned bytes and accepts little-endian IEEE binary32 Android
ARM64/x86 hosts. The header stores real scene bounds and source-frame spawn:
`[582.5,74,-1380]`, control yaw approximately pi. Forward approaches the genuine
bench along world negative Z. Fixture edges remain incomplete scene edges and
must be handled by the separate bounded-session safety adapter.
