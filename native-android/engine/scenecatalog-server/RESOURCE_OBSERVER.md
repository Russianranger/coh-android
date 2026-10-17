# Read-only loaded resource association supplier

`source_resources.inc` is a new **nonshipping** source observer intended for a
future reviewed capture. It does not start a server, repeat the catalog capture,
modify an existing capture/exporter, load a resource, mutate a model/trick/library,
or issue a network message. Include it after `source_snapshot.inc`, with the
unchanged `seq/anim.h` and `seq/tricks.h` declarations available. No sink or capture
workflow is activated by this component.

The source caller must hold a stable exclusive owner-thread boundary for the
catalog, runtime roots/futures, object library, loaded models and trick data for
the entire operation. No callback may invoke source code, lazy loaders or mutate
that state. Supply a caller-owned 128 KiB scratch span and a temporary unpublished
sink; discard all output on any nonzero status. Caller owns sink allocation and
scratch accounting. The observer itself allocates nothing and retains nothing.
Two passes validate complete source ownership and measure bytes before writing.
The original catalog header/report, both CRCs, root count and exact pointer
incidence are checked; regular and pre_alloc identity rules are reused unchanged.
Output remains a source observation, not a native render/resource permit.

For every active regular definition, followed by every exact observed pre_alloc
owner, the observer preserves whether a model actually exists. With a model, it
requires `model->gld` and the exact pointer to occur **once** in
`gld->modelheader.models`, retaining that original row. It copies the original
model and loaded GEO path strings without deriving either from a definition name.
`objectLibraryPathFromObj(def->name)` is a separate read-only lookup observation;
no library path is equated with the actual loaded GEO identity. It does not call
`modelFind`, `groupModelFind`, `geoLoad`, `objectLibraryLoad` or any texture loader.

Original `modelFind` does a case-insensitive comparison of the caller's name
before its first `__` against `Model.namelen_notrick`, then returns the original
header's model pointer. Therefore callers' suffixes are not new models, GEO rows
or new trick owners. The observer records the returned pointer's **actual** name
and `Model.trick`/`TrickInfo` identities; it never invents a suffix alias or attaches
a trick from the requested name. The oracle extracts and executes the unchanged
original four comparison/modelFind functions to qualify this distinction.

Texture partitions preserve original `TexID.id`, triangle count and the exact
`gld->texnames.strings[id]` observation, in source partition order. Observed
`TrickNode` flags, `TrickInfo` name/file, model/group flags and six LOD/shadow floats
are copied. Model bounds/scale/radius and GEO version/loadstate are observations.
Neither loaded-state bits nor the GEO version are claims that the native decoder
supports that format. A missing model is explicit; it is never replaced with a
geometry fixture. Missing/duplicate model rows, invalid texture-name indexes,
nonfinite floats or overlong/invalid strings refuse the entire candidate.

## COHRES01 record contract

A stream is the concatenation of bounded records; each begins with eight bytes
`COHRES01`. All u32 and IEEE754 F32 bit patterns are explicit little endian. No
ABI structs, pointers, bitfield layouts or padding are serialized. Native consumers
must bind the exact stream/catalog/runtime pair to independently checked source,
run, inventory and exporter identities before use. A syntactically valid record
alone provides no provenance. All records must share the admitted generation.

| Byte offset | u32 field |
| --- | --- |
| 8 / 12 / 16 / 20 | Version 1 / header bytes 192 / total record bytes / asset generation |
| 24 / 28 / 32 / 36 | Owner kind (regular 1, external 2) / file (UINT32_MAX external) / saved slot or separate external ordinal / original source ID |
| 40 / 44 | Model present 0/1 / capability mask 1 = SERVER observation only |
| 48 / 52 / 56 / 60 / 64 | String byte lengths including NUL: definition / actual model / loaded GEO / trick name / trick source file |
| 68 / 72 / 76 / 80 | Exact original model pointer row / observed GEO version / GEO loadstate / model loadstate |
| 84 / 88 / 92 / 96 | Model flags / vertex count / triangle count / texture partition count |
| 100 / 104 / 108 / 112 | Trick present / TrickInfo present / TrickNode flags1 / flags2 |
| 116 / 120 / 124 | TrickInfo model flags / group flags / separate object-library lookup path bytes |

Offsets 128..167 contain Model min[3], max[3], scale[3], radius as ten F32 values.
Offsets 168..191 contain TrickInfo lod_near, lod_far, lod_nearfade, lod_farfade,
lod_scale and shadow_dist as six F32 values. Missing TrickInfo gives zero fields.
After the header come six strings in the table's order (library path last), then
`tex_count` records: u32 texture ID, u32 triangle count, u32 NUL-terminated name
byte count, name bytes. All nonempty strings are visible ASCII, at most 256 bytes
including NUL; loaded GEO name is bounded by the original 192-byte array. Optional
absent strings have length zero. A no-model record has row UINT32_MAX and all
model/trick fields zero; its definition and optional library path remain explicit.

Limits are 128 KiB per record, 64 MiB total, 256 texture partitions per model,
65,536 header model rows, and existing catalog file/slot/child/future limits.
Exceeding a limit is a concrete unsupported capture, not permission to omit data.
`client_materials_available` and `client_lods_available` remain zero: SERVER Model
has no CLIENT `tex_binds`, shader blend modes, client LOD model pointers or complete
resolved TexOpt/material hierarchy. Trick colors, animated ST semantics, texture
option inheritance and full material/LOD closure remain uncaptured. This stream
must never be admitted as a complete resource generation by itself.

## Qualification and missing authentic evidence

Run `python resource_oracle.py --source-root REPO --output receipt.json --sanitize
--fixtures-output DIRECTORY`. Original source and unchanged function bodies are
independently pinned by `resource-source-pins.json`; the actual new observer is
instrumented under ASan/UBSan, while the preexisting legacy source bit grammar
keeps its documented sanitizer exclusions. Trusted fixture structs represent only
named fields and are **not** original ABI/layout evidence. The fixture exercises
GEO version 8 as an observed unsupported version, exact pointer row ownership,
trick suffix/case lookup, texture order, empty pre_alloc identities, corrupt
catalog association, malformed sources and callback refusal. No service executes.
Worker A independently parses these exact bytes using its native source-record
view and keeps real GEO admission closed until protected asset checks pass.

The successful retained workflow `38977202310` exported sendDef geometry names
and root/future metadata. Its source identity records only an aggregate runtime
inventory (176,613 files, 4,273,657,217 bytes and ordered inventory hash), not the
loaded model->gld pointers/header rows, texture partitions or original trick
objects needed here. Those authentic associations cannot be reconstructed from
the retained catalog/root sidecar alone. No new capture has been run. The new
supplier requires an independently reviewed source build and a specifically
justified future same-boundary capture before any authentic resource claims.

## Reviewed private staging and source sink

`stage_resources.py` creates a separate private MapServer source variant from the
same validated startup donor prerequisite as `stage_snapshot.py`. It never edits
the accepted executable, existing capture, workflow or donor. Its exact receipt is
`native-resource-snapshot-server-build-input.json`; build role is
`nonshipping_startup_catalog_root_and_resource_snapshot`. It includes the unchanged
catalog/root producer and path validator alongside the new resource observer.
There is exactly one normal owner callback, after `dbSetupMap()` and before
`dbReadyForPlayers()`, named `coh_source_resource_snapshot_startup`.

The new sink is disabled unless **all three** explicit paths and nonzero generation
are present. New variable: `COH_NATIVE_RESOURCE_SNAPSHOT_OUTPUT`; original catalog
and root variable names stay the same for this private variant. All paths require
original strict private-drive admission, pairwise no aliases, no existing finals
and CREATE_NEW partials. The callback copies bytes only; it neither yields to the
engine nor calls model/resource loaders. Source association observation occurs
contiguously with the unchanged catalog/root exports; this new variant exists to
recover data the previous capture did not serialize. It must not be run merely to
reproduce an old catalog/root receipt.

All three partials are flushed and closed before any rename. On a later failure,
cleanup removes only partials and final names whose creation/rename this invocation
actually owned. Existing outputs are never replaced or deleted. Partial/final
leftovers from failed deletion are explicit in `COH_RESOURCE_SNAPSHOT_V1` and must
block admission. A process crash cannot make the multi-file rename atomic; no
candidate is admitted without complete receipt, exact hashes and external owned
service cleanup. Success requires catalog/root/resource byte counts all match
producer reports. The resource scratch is an explicit static 128 KiB nonshipping
reservation. Per-pass exact row scans are additionally capped at 64 Mi pointer
comparisons, with `model_row_comparisons` reported; two passes cap this work at
128 Mi comparisons. Exceeding the budget refuses the capture rather than omitting
associations. Existing catalog identity/inventory iteration remains separately
bounded by its original limits.

`record_resource_compile.py` verifies the staged source, Win32 PE/CMake identity,
original published donors and overlays, then packages a compile-only receipt with
schema `coh-resource-snapshot-compile-v1`. It performs no build or runtime capture.
Run `check_resources_stage.py --output receipt.json --sanitize` for seven staging
and 696 WinAPI-shim sink controls in release/ASan/UBSan. These include failure at
every create/write/flush/close/rename position, producer refusals, independent
cleanup-delete failures, source/receipt drift, path collision and preexisting-output
preservation. LeakSanitizer cannot inspect this executor's process namespace;
ASan runs with leak detection disabled. There is no sink dynamic allocation.
Actual Win32 compilation and Wine/original-server execution remain unqualified.

The coordinator must extend runtime source/run binding for a future capture:
source identity must pin this **new** exporter PE, resource stage/compile receipt,
resource observer/sink and orchestration source plus exact mounted inventory; run
identity must reference that source identity, private fresh services and owner
callback; capture receipt must reference source/run SHA256, hashes/sizes of all
three files, complete sink counters and verified cleanup. Old snapshot source/run
identities cannot be reused to label the new resource stream. Matching the retained
catalog SHA256 is a comparison witness, never a replacement or live-generation
permit. Worker A's native resource index then independently verifies each copied
record and exact GEO input. Material/LOD completeness remains false throughout.

The final source observer additionally refuses the original `LOADING` state (2)
for the observed GEO/model. Original `LOAD_HEADER` deliberately permits stable
`NOT_LOADED` (1) GEO data stubs; header-only metadata is not mislabeled as complete
loaded geometry. This guard does not replace the exclusive owner/quiescence
prerequisite. Fixture controls compare Model/GEO/TrickNode/TrickInfo bytes before
and after observation and confirm no source mutation. Final host receipt has
106 source controls per release/ASan/UBSan mode, seven staging suites and 696 sink
controls per mode. No actual Win32 build or resource capture is included.

## Isolated resource capture orchestration and binding

`admit_resources.py` is a separate same-workflow compile-artifact admission path.
It requires schema `coh-resource-snapshot-compile-v1`, the exact new stage role,
clean pinned source revision and all expected archive members/overlay hashes. It
creates a new private candidate with schema `coh-resource-snapshot-candidate-v1`,
including separate original catalog and new resource producer pins. It refuses
old snapshot candidates and never modifies installed servers.

`capture_resources.py` preserves the previous `capture_snapshot.py` unchanged.
It reuses the qualified disposable DB/Wine/process cleanup helpers and exact
published DB donor, driver probe, path probe and retained catalog. Its host guard
requires nonroot, GitHub-hosted Linux in this repository; local controls never
launch anything. CLI arguments intentionally match `capture_snapshot.py`; the
`--candidate-directory` must be admitted by `admit_resources.py`, and `--output`
and `--work` must be new private directories. The new private candidate requests
all three source outputs in one owner callback. No snapshot-only workflow is
modified or implicitly activated.

A justified new hosted attempt supplies **new** source/run identities under schemas
`coh-resource-snapshot-source-v1` and `coh-resource-snapshot-run-v1`; they pin the
new PE, compile/stage receipts, source observer and orchestration source, exact
runtime inventory and original donors. They cannot inherit the old successful
snapshot identities. `COH_RESOURCE_SNAPSHOT_V1` must report successful producer
statuses, zero cleanup leftovers, explicit CLIENT material/LOD absence and bounded
consistent record/model/texture/work counters. Runtime artifacts copy out before
teardown; failures preserve any surviving outputs as unaccepted diagnostics.

The driver bounds the resource stream before parsing (64 MiB, 65,600 rows, 256
textures per row), requires visible ASCII/NUL names, finite numeric observations,
same generation, original regular row ordering/ID shape and exact pre_alloc
name/ID/model association against the root sidecar. Ordinary file/slot/name/model
association to every actual catalog definition remains a **mandatory downstream
native catalog-owner/graph gate**. This structural capture pairing deliberately
sets `native_decode_completed=false` and grants no resource permit.

After stopping and verifying every owned service, confirming source/inventory and
retained catalog unchanged, and redacting bounded diagnostics, `build_binding`
rechecks the copied catalog/root/resource SHA256 and sizes, source/run SHA256,
new identity schemas, producer/PE/inventory/revision/callback identity and all
cleanup/scope flags. It repeats structural pairing on the copied immutable files.
Any final binding refusal changes the final capture receipt to `passed=false`
with its failure code; no binding is emitted. Only after successful validation is
`capture-receipt.json` written and `resource-binding.json` minted with schema
`coh-resource-snapshot-binding-v1`. This binding explicitly carries no native,
CLIENT material/LOD, live GROUPS, actor or world authority.

`check_capture_resources.py --output receipt.json` runs six offline suites covering
role/PE/hash admission, sink counters, generation/source order/external pairing,
bounded texture parsing, exact copied-byte/source-run/cleanup refusal and isolated
host nonlaunch. Fixtures substitute small test catalogs; they establish no real
capture. Source and native consumers require independent reviews before the one
justified hosted attempt. The source loader/model/trick quiescence prerequisite
is external to host orchestration and must be qualified by that source run.
