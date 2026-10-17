# Nine special root-model pairs

These are nine distinct root-reachable model-owner references from the existing
qualified391-file closure. Their retained full bodies and captured source records
are unchanged. None is removed from the graph or converted to ordinary material
geometry by this tranche.

| Captured wholejoin ordinal | Exact model | Source prerequisite |
|---|---|---|
|23835|`_deco_skyscraper_01`|33 planar-reflection quads|
|23839|`_deco_skyscraper_02`|20 planar-reflection quads|
|23855|`_deco_skyscraper_05`|62 planar-reflection quads|
|23848|`_deco_skyscaper_06`|68 planar-reflection quads|
|23676|`_deco_skyscraper_07`|126 planar-reflection quads|
|23856|`_deco_skyscraper_13`|29 planar-reflection quads|
|25926|`_ArchEnt_Bldg_Exterior`|20 planar-reflection quads|
|35044|`_conifer_shadow_sml1__ffshadowlg`|UV stream absent; captured CASTSHADOW flag|
|39692|`masterpivot`|Three alternate-pivot Mat4s|

`coh_source_special_prepare` takes an actual opaque SourceBody and wholejoin
ordinal. It returns an immutable borrowed supplemental view: exact source lease,
358 total decoded planar quads across the seven reflector models, raw and parsed
active alternate-pivot matrices, and explicit absence of the conifer's UV stream.
It allocates nothing, retains no extra references and never transfers ownership.
The Body, graph, loader and caller workspace must remain alive and immutable
through all view use. Its output remains unchanged on refusal; scratch may change.
Known source/workspace/control aliases and overflowing endpoints refuse before
writes. Capacity is bounded to1MiB, decoded reflection stream to256KiB, and quads
to256 per model. The actual test uses512KiB workspace sequentially per file.

The original CLIENT `modelSetupPRQuads` decodes `count*4` positions with stride3
through original delta decoding. `groupdrawinline.c` forwards these points unless
`no_planar_reflections` is set. `rendertree.c` processes them only under actual
planar-reflection/fog state, transforms them with the actual instance matrix and
selects planes using view state. Preserving the extra geometry is necessary;
these decoded points do not establish reflection render targets, shader state,
visibility, CLIENT materials or a correct ordinary draw packet. The new contract
leaves those prerequisites pending. It does not silently discard pack9.

The captured conifer source record has flags1 `0x00810000` and flags2
`0x00400000`, the original `TRICK2_CASTSHADOW` bit. Original group draw sends such
models to `modelAddShadow` instead of the ordinary AVSN branch. Original VBO
creation allocates texture coordinates only when `modelHasSts` holds, so absence
of UVs is a source-defined state. The stencil-shadow consumer needs positions,
indices, extrusion direction/distance, lighting and render state; this helper
preserves the observed branch prerequisite without synthesizing UVs or assuming
that SERVER trick state proves final CLIENT state. No shadow renderer is added.

Original `geoLoadData` rebases `Model.api` from the GEO payload; `AltPivotInfo`
is an int count plus15 Mat4 slots. `fx.c` uses an active matrix only when the FX
altpiv request is positive and within count. The actual masterpivot body has three
active matrices. The helper bounds the complete724-byte source structure,
preserves its raw bytes, checks all active floats and copies the active matrices.
It does not use an FX attachment matrix to reposition the base world mesh.
An eventual CPU mesh owner must retain this information and qualify the FX
consumer separately; the ordinary rigid gate remains conservative.

The actual input ledger `tests/source_special_routes.json` records every exact
body/model/ordinal and expected extra-channel hash. `check_source_special.py`
independently compiles unchanged original delta decoding for the seven reflection
streams; all4296 floats match native output byte for byte. The36 active pivot
floats match exact payload bytes. Synthetic stub-lease controls test malformed
channel grammar only and cannot establish Body admission or source provenance.
The host receipt names these scopes separately. Original32 readModel, Android,
server, GPU, CLIENT material and world acceptance are not claimed.

`inspect_root_partitions.py` independently reconstructs all3083 root owner rows /
5535 captured texture partitions from exact resources SHA85007649... and the
previously qualified2916-pair coverage SHA5df9bc58.... The reproducible output SHA
is46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a.
This supplies exact observed basenames to the texture dictionary worker. It is
not a CLIENT texture namespace, texture-body acquisition or material lookup.

Final qualification is `evidence/source-special-qualified-host.json`:63 source
pins,23 exact inputs,948264 integrated controls per release/ASan/UBSan plus58
separate synthetic grammar controls per mode. The named maximum reservation is
71794134 bytes, including actual retained source dependencies, one32MiB loader
reservation,512KiB workspace and caller reservations. It is not process RSS.
Body preparation separately reserves the live workspace while acquiring each
file; no eager nine-file geometry residency is introduced. Complete allocation
balance and unchanged default0/8 fixture bridges pass in the same replay.

The earlier `source-special-first-host.json` is an uncommitted historical
pre-tightening receipt. `source-special-final-host.json` is an empty failed-write
receipt preserved after ENOSPC. Neither is the final proof. No final production
source changed during the successful qualified replay; dependency hashes were
reverified after durable receipt creation.

The follow-up `evidence/source-special-stack-host.json` supersedes the original
qualified receipt for current preparation budgeting. The module now explicitly
charges16KiB for its own native preparation frames before polling/decoding;
external zlib, callback/system stack and other live owners remain caller charged.
GCC `-fstack-usage` measured the bounded preparation/lease/index/stream/delta
frames in each mode; their conservative listed-frame sum is below16KiB (static
or dynamic,bounded only). An explicit budget omitting that reserve refuses for
every authentic route. Current controls are948273 per mode plus58 grammar checks;
maximum named reservation71810518 bytes. Ordinary policies and source extras are
unchanged; the historical33707 receipt remains valid for its earlier scope.
