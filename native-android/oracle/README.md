# Original NVIDIA decoder oracle

`nvdxt_reference.cpp` links the existing, pinned **Win32 NVIDIA nvDXTlibMT_S.lib** selected by `upstream/ouroboros/cmake/dependencies/NvDxt.cmake`. The original decoder implementation is compiled vendor machine code in that library. The available `decompress.cpp` and `nvdxt.cpp` are client programs, not its complete implementation.

Build on a Windows Visual Studio C++ host:

```cmd
native-android\oracle\build.cmd out\original-oracle
out\original-oracle\nvdxt-reference.exe input.dds out.raw out.rgba out.json
```

The build uses x86 `/MT`, the exact Game library variant, and Microsoft's `legacy_stdio_definitions.lib` for legacy CRT entry points. It verifies SDK/source hashes and produces a PE32 receipt. No alternate decoder implementation is substituted.

Each invocation decodes one independently validated DXT1/3/5 DDS with `SpecifiedMipMaps=1`, matching `uncompressRawTexInfo`. To qualify quality mip skipping, the caller must construct the same reduced DDS header and remaining payload as `ddsLoad`; selecting all mips in the original API is a different contract.

The adapter bounds input size, dimensions, the full declared mip chain and read callbacks. It aborts on an out-of-range SDK read rather than continuing with substituted bytes. The SDK's output is validated against its CRT allocation size before reading. Raw row bytes and their channel-normalized, tightly packed RGBA output are saved separately. JSON preserves SDK dimensions, row pitch, depth, source format, allocation size and callback reads. The old Game consumer swaps B/R for four-byte pixels and expands three-byte BGR pixels with opaque alpha; this adapter applies those conversions. It requires `row_bytes == width * depth`, because the consumer traverses tightly packed pixels; row padding fails qualification with SDK metadata printed to stderr rather than being silently cropped.

Run only the well-formed, provenance-checked corpus in a subprocess with a timeout. A failed callback, SDK error, layout anomaly or byte mismatch is a qualification failure. Successful build or an independent decoder agreement alone does not establish original decoder parity or Android rendering.

`coff-arithmetic.json` records deconstruction inferences, exact SDK/member/function code hashes and function-relative instruction offsets. The selected `.asm.txt` files contain only RGB/alpha palette functions and the relevant color/alpha application and output-depth slices. These offsets identify original COFF sections, not live Game virtual addresses. Whole-SDK decoded byte comparisons confirmed nearest-rounded thirds, DXT5 alpha interpolation and the shared endpoint-order palette branch. Additional synthetic probes confirmed that DXT1 loses CPU cutout alpha and DXT3/5 with zero visible alpha also become opaque through the old depth3 consumer. The generic texture decoder retains its standard alpha behavior; these legacy rules apply only to the separate compatibility API.

`generate_edge_cases.py` creates explicitly synthetic SDK contract probes, including 1x1 and 2x2 images whose padded block pixels have opposite alpha. Preserve `DDSD_MIPMAPCOUNT` in these headers, as the game producer does. The original SDK may allocate a padded full mip-width layout when that flag is absent, despite reporting a tight `row_bytes`; the compatibility API deliberately rejects that header contract. Supplemental probes do not qualify real DXT3 assets, which are absent from the current real corpus.
