# Native Android experiments - Phase 2

Isolated C modules for Android Bionic `arm64-v8a`, based on the accepted client
source. These targets are independent of the shipping Game and launcher targets.

Implemented test slices:

- Fixed-width Blowfish with checked key/block lengths and unaligned-safe,
  explicitly little-endian game packet words.
- Fixed 596-byte animation headers and 20-byte bone records, offset/span
  validation and native-width borrowed views.
- Fixed 12-byte geometry pack descriptors and v3-v8 model-record metadata.

This is not a native game or a complete animation/geometry loader. Rotation
expansion, geometry delta/collision decoding, real-asset corpus parity, live
protocol exchange, Android Surface rendering and Thor execution are separate
gates. Results will distinguish host execution from Android cross-compilation.

The upstream sources are immutable. `tools/generate_crypto.py --check` verifies
the crypto derivative against the original source hash and preserves its author
notice. Generated buffers and test data do not access personal profiles.
