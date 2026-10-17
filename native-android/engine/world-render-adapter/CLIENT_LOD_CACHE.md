# Exact historical CLIENT LOD dictionary inputs

`coh_wr_lod_cache` admits the exact retained `data/bin/lods.bin` and preserves
original initial dictionary precedence. It consumes actual cache/resource bytes;
it creates no live-generation receipt or material/mesh/world permission.

The cache is 1,059,016 bytes, SHA256
`13800255781138248226340be316cd628e98800d9ba889fe1aecc902e483b66a`, observed
schema word `e8361497`. Its retained archive is the already admitted
27,071,659-byte client cache ZIP, SHA256
`5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051`.
No recapture or archive acquisition is needed. Schema CRC is an observed identity,
not an independently recomputed current CLIENT parser/cache association.

## Native ownership and exact source semantics

The raw owner uses the protected asset loader and requires exact path, caller
historical input label, extent and complete SHA before parsing. It validates the
whole original persisted hierarchy: 738 source files, 4,976 ModelLODInfo records,
9,158 ordered AutoLOD children and 39 ForceAutomatic records. All 39 force rows
have no children. The native owner retains one loader pin and bounded offsets;
it does not allocate an eager runtime ModelLODInfo/EArray/string tree. Every
float, flag and optional model string stays observable. Public byte spans are
borrowed, not NUL-terminated, and require owner lifetime.

The dictionary stage consumes the raw owner only on final success. It obtains
original writable paths through an explicit resolver boundary, creates immutable
initial registration keys, sorts an index, preserves the first source ordinal
for duplicate case-insensitive keys, and retains raw source-admission metadata.
Initial postprocess truncates the first `__` in the **model name** before
registration. Original lookup appends the full model name to the resolved path
and then truncates the first `__` in the **whole key**. Appending a clone suffix
to a model ending in a single underscore can therefore change the lookup; the
qualifier preserves this source behavior. Original MAX_PATH registration
truncation is outside the admitted domain: combined keys requiring 260 or more
characters refuse rather than silently registering a shortened identity.

`coh_wr_lod_source_filename` implements the complete bounded original
`getLODFileName` projection, including first case-insensitive `/data/` and `.geo`
matches. It does not locate any filesystem entry. Lookup resolves that source
filename through the supplied writable-path boundary and executes the original
initial-cache early-return policy: an existing parsed row returns before
construction unless it has force-auto set and no children. Missing entries and
force-auto empty rows remain distinct results. No runtime reload/removed state,
dictionary insertion, geometry model or fallback material is invented.

## Authentic root query evidence

The qualifier admits the exact retained 12,596,422-byte COHRES capture, SHA
`8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6`, and exact
root partition ledger SHA
`46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a`.
All 3,083 root source ordinals, complete model/GEO names and ordered partitions
are independently compared before queries execute. Under the explicitly stated
fixture writable-path observer, unchanged original and native lookup agree:

| Historical root model observations | Count |
| --- | ---: |
| Existing explicit LOD row returns before automatic construction | 356 |
| No initial-cache entry for the source query | 2,727 |
| Force-auto empty row continues construction | 0 |

These are historical lookup observations, not renderable models, current
namespace membership, a CLIENT branch selection or current generation proof.
In particular, the 2,727 misses do not authorize a default base mesh or automatic
LOD construction: full Trick/default GEO/cape/tray/legacy/reduction policy remains
required. Existing explicit LOD rows also still need their actual geometry and
material dependencies.

Release, ASan and UBSan each passed 167,019 checks. All 4,976 native records and
9,158 children match unchanged original typed binary readers. Unchanged original
`fillInLODFilenames`, `lodinfoLoadPostProcess`, `getLODFileName` and the complete
lookup early-return prefix execute under explicit original allocator/EArray,
stash, writable-path and object-library observers. Actual object-library calls
are not replaced with an assertion that model filenames resolved: the observer
returns unresolved, and the native module grants no child geometry selection.
Derived common-path controls produce 50 duplicate keys and verify first-owner
precedence. A derived force-auto row with existing children still returns those
children, matching the source conditional.

Five production mutations must fail: near/fade field order, last duplicate
winning, force-auto bypassing existing children, wrong `/data/` handling and
missing complete-body digest comparison. Controls also cover exact/one-byte-short
budgets before allocation/callbacks, overflow, allocation/digest/path failure,
operation-boundary cancellation through final publication, malformed/truncated
children, corrupted source, absent generation, output aliases, old/output
preservation, pin survival through trim and actual loader baseline restoration.

## Memory and remaining production inputs

On the qualified 64-bit host, raw metadata owns 139,424 bytes; dictionary metadata
and keys own 1,373,496 bytes in addition to the consumed raw owner and pinned
cache. The whole configured loader reservation is charged, not merely current
resident bytes. Raw preparation adds a 16 KiB own control reserve; dictionary
preparation adds 32 KiB. Host release stack usage measured 12,432 bytes for cache
open plus its 112-byte child decoder, 704 bytes for dictionary stage and 1,696
bytes for lookup. Compiler/sanitizer, callback, provider, allocator, library,
code/runtime and other old/new owners must be included in external reservations.
The public opaque loader cannot prove its configured limit: callers must set
loader total <= loader reservation before entry. This is component accounting,
not Android process RSS or another independent 96 MiB allowance.

Production still needs the exact current CLIENT `fileLocateWrite` mapping and
cache/import generation; actual existing/reloaded/removed dictionary state;
`objectLibraryPathFromObj` and generated LOD model filenames; selected GEO legacy
or default LOD data, reductions and autolod distances; complete Trick/cape/tray
policy and effective material generation. A fixture path prefix or matching
historical cache hash does not supply these values. Current CLIENT/world
publication, Android build/execution, GLES and physical Thor acceptance remain
unqualified. Accepted APKs, protected renderer/gameplay support, JNI/build files,
server profiles and imports are unchanged.

```
python native-android/engine/world-render-adapter/check_lod_cache.py \
  --actual-cache /path/to/exact/lods.bin \
  --resources /path/to/exact/resources.cohres --output /tmp/FRESH-lod-cache.json
```
