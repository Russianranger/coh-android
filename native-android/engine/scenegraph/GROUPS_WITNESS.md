# Optional immutable GROUPS eligibility compatibility witness

`coh_runtime_groups_witness` is additive; the existing conservative comparator is
unchanged. It imports the exact fixed64-byte records defined by the nonshipping
`source_groups_eligibility.inc`, an exact normalized post-command reader and
independently checked hash/provenance labels. It owns immutable copies of records
and the complete reader byte allocation, retains the actual CatalogOwner and
indexes original file/slot order. The graph and exact borrowed snapshot owner
remain externally retained through the last witness release. No graph retain is
implied. Refs are serialized, not atomic. Preparation runs off the render thread.

The observed U16 `GroupDef.file_idx` is not the file's catalog ordinal. Original
SERVER `autoGroupSelection` in `Common/group/group.c` marks modified file0 definitions
saved and sets file_idx=-1 to prevent sending them. `addFileIdx` in
`Common/group/groupfileload.c` also sets -1 when map_full_load. The resulting U16
observation is65535. Thus file0 can omit saved definitions under original source
rules; neither forcing every file0 record nor equating file_idx to its owner
file ordinal represents the general producer. The existing comparator deliberately
keeps its stricter compatibility restriction. This optional path is required to
represent such observed omissions; no flags are fabricated from names or files.

Admission here means importing a complete immutable diagnostic witness, not
admitting a live game generation. The narrow initial grammar requires full
NEW_WORLD, every normal file present, all allocated source slots represented in
the witness and every root slot emitted. Every file/definition/root count and
order must match the exact retained catalog/graph. Definition ID/in_use and
active-definition modification time are checked against original retained wire;
root activity is checked against the retained snapshot. File checksums match the
catalog. Every recorded eligibility decision is independently rederived: full
update bypasses time filters but not saved omission; force_reload bypasses both;
modified_on_disk bypasses saved omission. Inactive definitions remain records,
and eligible tombstones must still appear in the packet. Base/raid, delta file
absence, sparse roots, catalog holes, incomplete records and other encodings
remain refused. Time-omission count is zero in this initial full-update scope.

Exact graph identity, actual owner/source spans and catalog/snapshot/source/run
pins must agree. The caller also supplies expected observation, map generation,
selection generation, DBID and session digest labels. Comparing with another
owner (even byte equal), another graph or stale expected labels refuses. The
provider must compute SHA256 over actual owned bytes. Those labels and SHA values
are external provenance input: computing a hash does not establish source/runtime
capture trust, authenticate a network connection or turn a synthetic fixture into
a real producer observation. A manifest chain still must establish that the
witness, exact packet and catalog/runtime inventory were observed at the SAME
source owner-thread boundary. File saved/modified/force flags cannot be recovered
from the catalog by this parser. False caller provenance is not solved by hashes.

The extension structurally validates the complete packet, then checks exact file
names/checksums, every eligible definition exactly once in original slot order,
every source-ineligible omitted definition and every root name/packed matrix
against the immutable source graph. File0 receives the same eligibility treatment
as other files. A missing eligible definition, an emitted saved omission, extra
row, late malformed tail, stale owner or changed bytes cannot publish a candidate.
Reader and output remain unchanged on refusal. The immutable owner is created
only after full packet comparison succeeds. The comparison performs no allocations.
Known input/control/source spans are checked disjoint; opaque engine/digest owner
storage must be disjoint by caller contract. Diagnostic batches do not escape.

Budgets include owner payload/index, input and copied records/packet, graph,
actual catalog allocation, borrowed raw snapshot payload and128KiB scratch reserve.
The complete SnapshotOwner allocation is NOT inferable from that span: its
metadata/index/slack and every other hidden dependency beyond raw snapshot.size
MUST be added to retained_bytes, together with opaque graph/digest contexts. Input and
copied bytes are charged even if a caller could otherwise alias them. Other
owners, allocator slack, digest scratch and allocation metadata must be charged
in retained_bytes. The bounds are named reservations, not RSS or GPU memory.
Every constructor failure frees its provisional copy and retained catalog ref;
report and candidate remain unchanged. No automatic publication/old-owner swap
is provided.

Four trusted fixtures execute the unchanged original worldSendUpdate producer,
not a synthetic transaction envelope. They pair the same source objects' catalog,
root snapshot and exact pre-producer witness with normal send, file0 saved65535
omission, force_reload override and modified_on_disk override. Source/client
function and shim provenance is frozen before/after qualification. The earlier
observer qualification separately covers1728 original sendGroupFile predicate
combinations including UINT_MAX timestamps. Native release/ASan/UBSan controls
exercise truncation, every record's decision, missing eligible wire, wrong owner,
stale bindings, budgets, alias refusal, malformed late tail and each allocation
failure with rollback/leak checks.

Remaining blockers are unchanged: historical Thor343112-bit raw packet is absent;
no actual live observer/capture has run. The CLIENT receive path imports omitted
saved definitions through existing files or bounds/full loads before applying
wire updates. This module proves neither those imports nor matching CLIENT asset
or post-trick/material/LOD state. A full authoritative actor transaction and
same-session world generation are also required. All source-generation, assets,
world and actor/ACK publication authority stays false. No Android build, emulator,
Thor execution, accepted APK rebuild or server workflow is claimed.

The128KiB native-core reserve replaces the earlier64KiB reservation after
compiler stack-usage review measured nested constructor/comparator frames above
64KiB. This changes named admission accounting, not allocation caps. The owned
32MiB and aggregate96MiB limits remain unchanged. Source-only seed traversal also
uses this comparator reserve. `check_groups_stack.py` records conservative summed
native helper frames for release/ASan/UBSan; external digest/callback/library
ownership reservations remain caller-charged. Other target compilers still need
their own stack review before Android qualification.
