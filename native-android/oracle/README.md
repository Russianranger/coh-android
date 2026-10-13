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

`coff-arithmetic.json` records static deconstruction inferences, exact SDK/member/function code hashes and function-relative instruction offsets. The selected `.asm.txt` files contain only RGB/alpha palette functions and the relevant color/alpha application slice. These offsets identify original COFF sections, not live Game virtual addresses. Static inspection predicts nearest-rounded thirds and DXT5 alpha interpolation, and a shared endpoint-order palette branch for DXT1/3/5. Whole-SDK decoded byte comparisons must confirm these predictions before changing native decode behavior.
