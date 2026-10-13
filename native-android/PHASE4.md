# Phase 4: original NVIDIA decoder parity

**The selected real-texture CPU parity gate passed.** The explicit legacy decoder matches the pinned original Win32 NVIDIA SDK byte-for-byte on 12 real textures, all 111 declared mip levels and 1,753,450 pixels (7,013,800 RGBA bytes). Eighteen separate synthetic probes qualify additional SDK edge behavior. Neither result qualifies Android rendering or the entire asset catalog.

Qualification code: `92b9dc9a841f0006cd36f0d52dc67c0836f7ca92`.
[Original decoder CI](https://github.com/Russianranger/coh-android/actions/runs/38446476188) and [portable-core CI](https://github.com/Russianranger/coh-android/actions/runs/38446476233) passed.
[Digest-verified full evidence](https://github.com/Russianranger/coh-android/actions/runs/38446476188/artifacts/11838830128) includes original raw bytes, normalized RGBA, per-case dimensions/read traces, executable build receipt, native outputs and acquisition provenance. Durable per-case hashes and counts are in `evidence/phase4/comparison.json`.

## Original reference and input chain

The reference harness links the existing `nvDXTlibMT_S.lib` chosen by the imported Game build, SHA256 `1e9988ad52a01f44368d8d4150990ef2a033536a7a705424f04333143cd63b73`. The decoder is the vendor's Win32 machine code, not a reimplementation. A modern MSVC x86 `/MT` harness supplies bounded callbacks and verifies output allocation/extents. It saves raw BGR(A) and applies the exact tightly packed `uncompressRawTexInfo` channel conversion. Source and binary hashes are checked before building. The full Game executable is not run.

DDS inputs come from asset release `coh-assets-v1.0.0`, Base ZIP's `client-visual-assets.zip`. Every selected wrapper SHA256 matches the published child manifest, which was independently downloaded and fully SHA256-verified. ZIP member CRC, wrapper envelope, DDS payload and each mip span are checked. The full Base/nested ZIP hashes are release-declared; those complete archives were not downloaded or locally hash-verified. `tools/corpus/pins.json` preserves the source chain and original PIGG receipt limits.

Fresh acquisition recovered the 1,392,104 DDS bytes using 3,096,044 response bytes in 19 strict HTTP206 requests. It tests five DXT1 and seven DXT5 textures spanning body/bump/normal data, world masks/glow and narrow images (64x4 through 256x1024/512x512). Every declared tail down to 1x1 is tested. Coverage includes both DXT1 palette branches and both DXT5 alpha interpolation branches.

For each quality mip, `dds_gate.py` reconstructs the original loader's reduced width/height/count plus complete remaining payload. Other header fields are retained. The reference uses `SpecifiedMipMaps=1`, preserving the client contract. All reference invocations completed, and real cases returned the expected width, height and tightly packed row layout.

## Newly confirmed reconstruction requirements

The Phase 3 generic decoder initially matched 26/111 real cases. The other 85 had one-unit interpolation differences, totaling 725,302 channel bytes. The compatibility path now matches every byte.

| Contract | Original CPU SDK behavior | Native handling |
|---|---|---|
| RGB thirds | Adds 1 before division by 3 | Legacy decoder preserves rounded interpolation |
| DXT5 alpha | Adds 3 before division by 7; 2 before division by 5 | Legacy decoder preserves rounded alpha |
| DXT3/5 color ordering | Shares the endpoint-order palette branch with DXT1 | Preserved in legacy path; generic path retains standard four-color treatment |
| DXT1 cutout alpha | CPU output always becomes depth3; old consumer makes alpha opaque | Legacy path outputs opaque alpha; generic/GPU fallback path retains cutout alpha |
| All-zero visible DXT3/5 alpha | SDK returns depth3; consumer makes output opaque | Legacy path preserves this behavior; padding pixels do not affect the decision |
| Mip metadata | Missing `DDSD_MIPMAPCOUNT` can produce a padded SDK layout with misleading row metadata | Legacy API rejects the missing flag; generic base-only DDS remains supported |

The alpha/depth and endpoint edge contracts were confirmed by actual original-SDK probes, including 1x1/2x2 images where visible and padding alpha disagree. Focused COFF evidence remains under `oracle/`. These old CPU semantics belong to the raw texture path; applying them globally to ordinary GPU texture uploads would discard transparency.

Use `coh_dds_rgba_legacy` for a qualified replacement of the old raw CPU conversion. Keep `coh_dds_rgba` for generic BC decoding. Both use caller-owned, bounded, disjoint input/output and have no global stream pointer, NVIDIA/Windows runtime dependency or hidden allocation. They are still isolated experiments rather than shipping integration.

## Verification and limits

- Real original-SDK parity: **111/111 cases**, zero differing RGBA bytes.
- Supplemental original-SDK behavior: **18/18 synthetic cases**. These are not additional real textures.
- Standalone core: **12,026 assertions**, hosted sanitizer checks and Android Bionic ARM64 compilation passed.
- Generic path still passes the **1,095 Pillow comparisons**. Crypto and bounded asset regressions remain in the independent workflow.
- The pinned producer emits DXT1, DXT5 and DXT5nm; DXT3 is reader compatibility. A bounded search classified 206 other texture candidates as 108 DXT1/98 DXT5, with no DXT3. Real DXT3 parity is unqualified.
- This real corpus has no DXT1 transparent selector3. A bounded followup checked ten vegetation candidates and found no qualifying cutout fixture. The original-SDK cutout contract is qualified synthetically; real cutout visibility remains a renderer acceptance requirement.
- Uncompressed DDS layouts, broad asset-corpus parity, GPU fidelity, Android device execution, context lifecycle, world entry and performance remain separate gates. No playable native APK is claimed.

## Next gate

Build a minimal Android Surface/EGL renderer using one hash-qualified real texture. Verify direct presentation on the Thor's Adreno GPU, image output, resize and context recreation. Choose the decoder according to CPU versus GPU texture role, then add a real material and skinned fixture with the recovered shader contracts. Preserve the working client as the fallback while native rendering is qualified.
