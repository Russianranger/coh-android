# Real texture corpus provenance

The 12 compressed fixtures contain 1,392,104 DDS bytes and 111 declared mip levels: five DXT1 textures and seven DXT5 textures. They cover narrow textures (64x4 and 256x16), square world masks/glow maps (128x128 and 512x512), character/body/bump maps (256x512), and a 256x1024 normal map. Every mip tail down to 1x1 is retained.

Inputs came from `coh-assets-v1.0.0/COH-Assets-1.0.0-Base.zip`, inside `payloads/runtime/client-visual-assets.zip`. Full outer and inner archive SHA256 values are release-declared; those archives were not fully downloaded or hashed locally. Selected ZIP members passed `zipfile` CRC32validation. Each complete `.texture` wrapper SHA256matched the published `client-visual-manifest.json`, independently downloaded in full and verified against SHA256 `8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2`. DDS payloads are extracted unchanged at the wrapper's advertised header offset, then hash-pinned together with every mip span.

The manifest records original Thunderspy PIGG source paths and pinned source/metadata/range receipts. These are retained verbatim in `pins.json`; they do not establish full PIGG archive verification. The manifest pins imported data commit `d51533ec8e6a9cf726b9214968077a05fdcf19f3` and source commit `0b75ade0c801735e10c5798f641948a45cc50488`.

A fresh rerun of `acquire.py` recovered all 12 DDS files byte-identically using 3,096,044response bytes in 19 exact HTTP206requests, with stable ETag checks. Its output is acquisition evidence only; native pixel compatibility and original nvDXT parity are separate checks.

Six initial candidate textures used uncompressed ARGB8888 DDS and were excluded from this compressed-format corpus. Their metadata remains in `excluded_records`; supporting those formats is a separate requirement. No real DXT3 fixture is claimed in this set.
