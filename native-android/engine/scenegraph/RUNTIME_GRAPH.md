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
