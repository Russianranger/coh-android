# Immutable source resource identity index

This additive standalone module consumes the source observer's `COHRES01`
records. It does not change production asset, bridge, renderer or client code.
It preserves exact regular file/slot versus external ordinal ownership, original
IDs, source definition/model names, the observed loaded GEO filename and exact
pointer-selected model row. Source TrickNode/TrickInfo flags and LOD values are
exposed as observations, with client semantic admission permanently unresolved.

The caller must independently admit the source/run/manifest receipt chain and
bind each record's SHA256 to it. The native index copies those records, verifies
their byte digests and obtains exact GEO paths/generations from independently
admitted pins. It never replaces file extensions, guesses a path, or authenticates
provenance from a supplied label alone. No-model records remain explicit source
identities and produce no resource view. A borrowed grammar-only view is available
for producer/native wire qualification and confers no digest or resource trust.

For each unique GEO, the index acquires a protected `CohAssetBlob`, hashes its
actual bytes, opens its bounded header workspace, and checks the selected exact
model name and original sorted runtime row, GEO version, vertex/triangle counts and every original
material partition's texture ID/name/triangle count. Equivalent case-insensitive
base model keys within one GEO are refused as ambiguous. Header support for a
version, including v8, is not draw/material support. Unimplemented model tricks,
auto-LOD, client texture tables, capabilities, swaps and material semantics stay
unresolved. A server observation cannot grant any of those permissions.

`coh_resource_library_key`, `coh_resource_model_key` and
`coh_resource_trick_key` reproduce bounded supported original lookup key rules.
They are qualified against unchanged `groupGetPublicName`, `groupNameIdx`,
`compareModelNamesAndLengths` and `trickFromObjectName` functions, with explicit
stash/error/storage fixture shells. Original StashDefault is case insensitive.
Only a final `&` triggers removal through the final underscore for public library
names; model lookup retains that clone suffix. Model base comparison stops at
the first `__`; trick lookup selects its suffix or the complete original model
name. Native keys admit nonempty ASCII strings shorter than 256 bytes. Full
source filenames can be longer in the wire observation. Helpers alone are not
an authentic loaded object-library dictionary: no such full dictionary exists in
the captured saved-definition catalog, and this index never fabricates it.

The index is sorted by exact owner kind/file/slot and queries allocate nothing.
All original model ambiguity scans happen during preparation and have a shared
16,777,216-comparison ceiling plus cancellation. Replacements require the next
index generation; asset generations cannot regress. An unchanged asset/source
capture generation requires byte-identical ordered records and receipt labels.
Old and candidate indexes remain distinct. Failure leaves the output/report and
old index unchanged, releases candidate workspaces and pins, and grants no
partial resource permit. The protected loader may retain newly unpinned bytes
in its ordinary bounded cache after an acquire/refusal; this is not index-owned
publication and this module does not trim unrelated cache state.

The aggregate reservation includes input records/descriptors, old/candidate
index ownership, GEO header workspaces, a 32 KiB stack reservation, caller retained
objects and a whole-loader reservation. The loader must have been configured
with a total allocation limit no larger than that reservation; its public API
cannot introspect configuration. Before/after-acquire statistics are checked
against the reservation. Source/pin strings, digest workspace and any external
source buffers not counted explicitly belong in caller `retained_bytes`.
Counters are named allocation reservations, not process RSS or GPU memory.

Run `check_resource_index.py --output NEW.json` for source lookup oracles and
release/ASan/UBSan controls. The retained observer fixture is a source-compiled
six-record fixture, not an actual runtime resource capture. Optional `--geo`,
`--geo-sha256`, `--geo-path` and `--model-row` verify a real hash-pinned GEO through
the protected API using an explicitly constructed ownership observation. This
still does not prove that any server had that particular model loaded. LSan is
disabled under the known sandbox `/proc` limitation; wrapped allocation balance
checks cover rollback and final retirement. No Android execution is implied.

The admitted GEO pin has two distinct identities: `source_geo_name` is the exact
observed `GeoLoadData.name`, while `id` is the authenticated canonical asset-loader
identity. Any difference (for example, an archive virtual path prefix) must be
stated by the admitted manifest. The index introduces no transformation between
them. An unchanged generation also preserves the exact selected loader identity.
Source model min/max, scale and radius are exposed separately from the actual
GEO row; they are not silently replaced by file values or used as qualified bounds.

Final host qualification compares 6,942 original lookup cases, 6,548 original
model-sort comparisons, and passes 21,849 source/4096-row controls plus 18,709
authentic-GEO controls in each release,
ASan and UBSan mode. The authentic GEO is the 1,289-byte v8
`data/object_library/worldnpcs/praetorian_box/g_praetorianbox_open.geo`, SHA256
`218d1b2ff890678cca25b005d295aff8f76c6f551acad6b2144d1786723239b5`,
model row 0 `FX_PraetorianBox_Open`. Its independent acquisition/provenance is
owned by the rigid-resource adapter qualification. This native test constructs an
explicit synthetic source owner over those authentic bytes; it is not evidence
that the original MapServer loaded this model. The actual source-resource capture,
complete loaded public-library dictionary, client material/trick/LOD profile,
matching live graph generation and resource-to-render admission remain required.

The consumer additionally enforces the exact producer limits before any variable
record walk: 128 KiB per record and 256 material partitions, with source/trick/
texture names bounded to 256 bytes. The final strict-record receipt binds these
controls and the independently authenticated v8 fixture.

The source observer records the pointer row after original `geoSortModels`, while
`coh_asset_geo_model` exposes disk order. These identities are separate:
`model_row` retains the observed runtime rank and `geo_disk_row` identifies the
verified disk row (UINT32_MAX before asset admission). Preparation computes the
unique case-insensitive base-key rank using unchanged original comparator
semantics and requires exact full model-name equality. Raw model names retain
directory bytes here; group lookup path stripping is a separate operation. A
selected equivalent base key is refused, since original qsort does not establish
stable identity between equal keys. No permutation allocation is needed.

The original loader's zero-texture-table `white` substitution is observed source
behavior, but the protected native GEO reader currently cannot admit that input.
Such rows remain unsupported and fail closed; this module does not synthesize a
texture or grant material authority. This limitation does not alter source-only
catalog/graph/resource structural joins.
