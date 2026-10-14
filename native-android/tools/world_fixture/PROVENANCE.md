# Bounded Atlas world fixture

The selected source branch is `modern_bench_2wide` in Atlas Park. The exact
recovered model is `modern_bench_2wide__mbench`, model-table index 10 in the
version-seven `misc_sm.geo` member. Its 256 vertices and 188 triangles comprise
two genuine material partitions: `Signmetal.tga` has 48 triangles and
`modern_bench.tga` has 140. Both partitions are retained. The one source model
does not have a character bone table, weights, matrix indices, secondary UV
channel or stored vertex RGB. The canonical COHMESH1 adapter retains all 256
original vertices in each partition and partitions only the original triangle
indices; its one identity palette entry is native static-geometry scaffolding.

`pins.json` records exact ZIP member names, sizes, methods, local-header offsets,
CRC32 and SHA256 for the GEO and all four original wrappers. The two acquired
material pairs are Signmetal/stock grey and modern_bench/stock white. Stock
fillers are actual source textures, rather than generated replacements.

Acquisition uses the unchanged accepted Phase 6 HTTP range reader. Every
request requires HTTP 206, an exact Content-Range and a stable ETag. ZIP local
names, encryption bits, compression methods and bounded decoded envelopes
must match. The outer ZIP stores its inner ZIP. Each complete recovered member
passes size, CRC32 and full SHA256 verification. A locally reused member passes
these same three checks. Whole-archive SHA256 values are release provenance;
the bounded reader does not falsely claim to have verified entire archives.

The v7 GEO decoder parses little-endian fields and integer offsets without
casting disk pointers. This version has four header block sizes, a 140-byte
x86 ModelHeader and 232-byte model records containing nine 12-byte pack
descriptors. Source collision-grid and reduction packs remain present as
metadata but are not used for rendering, collision or LOD. Original
`uncompressDeltas` is independently compiled under the previously accepted
minimal host shim. Its complete indices, positions, normals and primary UV
outputs match the bounded decoder byte-for-byte, and the original GPU V-flip
expression matches each canonical vertex. Five checks cover 3,124 scalar
elements. This executes source scalar functions, rather than the whole Win32
client.

`world.bin` uses a 128-byte COHWOR09 header, two 96-byte part records, four
32-byte texture records, a 520-byte COHWRI09 input block and contiguous
COHMESH1/RGBA data. Its parts point at the final node of the six-link authored
Map Ref/group chain. Pos and PYR values are raw binary32 inputs, preserving
original omitted defaults and signed zero. Native rendering reconstructs
matrices at runtime. Sampled reference matrices never drive the rendering.

The scene metadata retains original TintColor `67 139 202 / 0 0 0`, Ambient
`28 31 40`, higher-parent TexSwap cubemap metadata and Geometry/AutoGroup
properties. The probe selects controlled camera/light/fog inputs and mip-zero
texture sampling. Those controls are identified independently from the
original authored map, and do not establish full Atlas lighting, cubemap
resolution, full scene sorting, collision, gameplay, networking or performance.

`world-reference.bin` is a separate Python row-matrix reference for original
group/view/projection semantics. The unchanged source math host oracle
qualifies that implementation independently. `material-reference.bin` uses COHWMAT9 with an explicit shader-mode word
per case and holds twelve scalar material cases, six per source partition, including explicitly
labeled diagnostic fade/fog/secondary-swatch/alpha-reference controls. Every
output file has an exact byte size and SHA256 in `world-fixture.json`. The
metadata is capped at 512 KiB before it can enter the APK.
