The upstream code basis is the existing locked source import
`0b75ade0c801735e10c5798f641948a45cc50488` and companion i24 data
`d51533ec8e6a9cf726b9214968077a05fdcf19f3`. `source-pins.json` records LF-normalized
whole-file and unchanged-function hashes for original `animPlayInst` timing,
`animInterpNodeWithLastPosition`, quaternion normalization/interpolation,
quaternion-to-matrix conversion and vector interpolation/threshold math.
`oracle.py` extracts unchanged functions with minimal storage/platform stubs;
it is independent of the shipping playback implementation.

`families.py` also uses the existing, hash-pinned original scalar raw-key decoder
oracle (`tools/animation_fixture/original_animation_check.py`), rather than
comparing the native sampler to itself. It exercises each reachable bone at
integer/fractional/mid/end times. Source local delta handling is retained.
The new-family blend references take raw sampled poses and execute the original
per-bone transition helper, then compose hierarchy rows from original quaternion
matrices. New authored graph declarations reuse the existing source exporter and
original sequencer oracle with no kernel modification.

Authentic clips come from the existing external `coh-assets-v1.0.0` Reference
archive, acquired by the coordinator using its indexed ZIP records. The clip
payloads are not embedded, edited or replaced with baked poses. Original raw
member SHA256 and byte lengths are pinned in `extra-asset-pins.json`; all base
and motion encoded keys remain inside canonical `COHRIG01` test containers.
The coordinator owns the outer archive/index/range acquisition receipt and asset
packaging. The source-authority details of that acquisition must accompany any
consolidated APK rather than treating this module's self-recorded hash alone as
an archive-authority claim.

`fixtures/expanded_graph.json` pins a six-move authored source subset, with ranges
whose missing last frame was resolved from the now admitted original clip header.
Original unmatched links and unavailable clips remain unavailable. Unknown
side effects are not redirected to mock state. The wave raw clip lacks a
qualified authored emote binding and is explicitly only raw-pose evidence.

Qualification receipts are additive under `qualification/`. None is proof of
Android execution, full player-graph closure, authored FX routing, gameplay
physics, primary-agent network/session interoperability or physical acceptance.
