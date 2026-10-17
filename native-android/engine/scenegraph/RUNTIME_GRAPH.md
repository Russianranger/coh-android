# Immutable original-runtime source graph

`runtime_graph.h` extends the existing runtime snapshot diagnostic with a compact
immutable graph. It reuses the same two-pass streaming catalog walk, original
CRC recomputation, source owner validation, root matrix decoder, canonical lookup,
root-reachable DFS and same-boundary catalog/snapshot admission. No application,
JNI, shipping renderer or accepted APK is changed.

The interrupted historical worker-b `runtime_graph.h` and graph hooks inside
`runtime_snapshot.c` were recovered by content from the preserved worktree. The
builder, publication, views and tests complete those hooks. The previous audit
entry point remains compatible and retains its original diagnostic accounting.

Nodes preserve every allocated original file/slot, then separately indexed
observed pre_alloc objects. Slot holes remain holes. Child order and child
matrices, root slot order and the exact original raw root matrices are retained.
An observed external with no model/children has `empty_owned_future=1`: it remains
an explicit named source node. This flag grants no resource or rendering permit
and does not synthesize a saved definition. Inactive slots expose no name.
Canonical public name queries require exact spelling, without new aliases.

The builder borrows immutable caller-owned input spans through graph retirement.
It validates exact byte pins before parsing; provenance records remain the
caller's responsibility. A graph can only advance by one graph generation;
asset/catalog generations cannot regress. Reusing the catalog generation must
retain the complete catalog/snapshot/source/run identity. Publication requires
the exact predecessor used to build the candidate. Construction and publication
leave outputs unchanged on failure. Retirement is caller serialized; borrowers
must finish before the graph and input owner are released.

Accounting charges the complete predecessor pool/object and both predecessor
inputs, even if old/new inputs alias. It also includes the candidate object,
pool, input spans, transient decoded record, output and stack reservations.
Caller owner indexes, digest scratch and resource allocations must be supplied in
`retained_bytes`. Limits remain 32 MiB owned and 96 MiB aggregate named payload;
allocator overhead and process RSS are outside this contract.

`check_runtime_snapshot.py --sanitize` now tests graph views, root/slot/name
identities, generation rollover, same-generation provenance mismatch, predecessor
retirement, aggregate admission, every allocation failure and cancellation point
on eight original-source fixtures. Actual-capture replay also exercises graph
construction/views/retirement without expensive exhaustive fault injection over
the full authentic corpus. Receipts explicitly distinguish source graph checks
from published application worlds. The fixture producer remains unchanged.

Remaining independent gates are a matching received live GROUPS generation,
qualified geometry/texture and inherited material/trick/LOD resources, immutable
selected-character transaction and atomic renderer publication. No graph API
sets assets_admitted, groups_received, actor_admitted or world_authority.

## Authentic retained capture qualification

The exact catalog/snapshot from workflow `38977202310` passed release, ASan
and UBSan graph checks after owned-service cleanup. Receipt:
`evidence/runtime-graph/authentic-host-qualification.json`. The corpus contains
40,232 nodes (40,225 original slots plus seven separately owned future objects),
130,314 ordered edges, 33 exact root matrices, 15,352 reachable regular nodes
and one reachable external (`_mmayhem_curtain_8_01c`). The other six captured
externals are unreachable from the 33 observed roots. All seven future records
have no model and no children; their identities remain explicit. Both source
CRCs pass. Graph owned bytes are 9,714,724; aggregate named peak is 24,048,821
bytes. Eight source fixtures ran 25,340 controls and the authentic corpus ran
291774 controls per native mode. Actual-capture graph views and atomic
replacement were tested; no application world was published. Android compilation,
emulator execution and physical Thor acceptance remain unqualified.

## Root ownership witnesses

`coh_runtime_graph_witness` returns a deterministic shortest root-to-node path,
with ties selected in original root slot and child order. It uses an explicit
caller-owned workspace of `report.nodes * sizeof(CohRuntimeGraphWitnessWork)`
bytes (482,784 bytes for the authentic corpus), no allocation and bounded
O(nodes + edges) traversal. Charge this workspace in aggregate retained memory;
it is temporary diagnostic/query state, not persistent per-instance storage.
The query also uses one local `CohRuntimeGraphWitness` on the stack and a
caller-owned output. These query reservations are additional to the graph
builder's `graph_aggregate_peak_bytes`; that build-only report does not include
a later witness call. The test harness's overall measured heap peak may instead
be dominated by replacement graph construction, so it is not a query-specific
memory measurement.
Each witness names the exact root slot, graph nodes and global child edge
indexes, so consumers can inspect original file/slot identities and compose the
already retained original root/child matrices. Multiple instance paths may reach
the same node; this one witness is not a world-instance enumeration.

The query preserves output on cancellation, insufficient workspace, invalid
arguments and unreachable targets. Original-source fixtures qualify every node,
every cancellation poll, path edge ownership, deterministic replay, depth 128,
unreachable/inactive slots and refusal controls. Authentic replay qualifies all
seven future identities and records the sole reachable future's exact witness in
`evidence/runtime-graph/witness-host-qualification.json`, independently under
release, ASan and UBSan. No server was restarted. No live GROUPS generation,
resource, actor or renderer admission is inferred from a source witness.

The authentic witness for `_mmayhem_curtain_8_01c` starts at root slot 7 and
contains nine nodes (eight ordered edges). The other six captured future objects
return `COH_NOT_FOUND` without altering the witness output. The three native
modes agree exactly on these results: 84,996 controls on each source fixture
corpus and 332,053 on each authentic replay. Android build/execution and physical
Thor qualification of this additive query remain pending.
