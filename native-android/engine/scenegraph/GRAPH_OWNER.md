# Owned compact source graph

`coh_runtime_graph_owner_create` owns the compact graph and retains the actual
CatalogOwner and SnapshotOwner. Exact catalog pointer/extent and complete catalog
binding must agree with the snapshot's retained catalog. Graph source/run hashes
and generations derive from those owners, with a real SHA256 provider rehashing
the bytes. Equal labels on another catalog allocation do not replace ownership.
Destruction frees the graph before releasing its source owners. Reference counts,
preparation and access require caller serialization; no historical owner chain is
retained. The old owner stays caller-held during construction. Borrowed views
must not be freed or independently published by callers.

The additive `coh_runtime_graph_build_limited` reserves graph object plus pool
against a caller-specified ceiling before pool allocation. The old build wrapper
still uses32MiB. The owner reserves its own metadata separately within the same
32MiB ceiling, and charges full old/new actual source-owner payloads, even when
aliased, before graph allocations. Its own allocation occurs only after the core
has admitted the complete graph phase. Allocation failure at either phase frees
all candidate allocations and releases only the references acquired here.

Aggregate<=96MiB includes192KiB nested runtime/catalog scratch and64KiB local
owner scratch. Raw input spans are charged by the core; complete source-owner
metadata/indexes/slack beyond those spans are charged by the owner. All other
live owners, provider contexts/stack and allocator metadata remain caller charged.
These are named payload reservations, not process RSS. Compiler stack controls
cover the host compiler only; Android compilation/execution remains unqualified.

`coh_scene_protocol_create_owned` derives its graph and source owners from that
actual owner and retains it through the final protocol-state release. This closes
the graph lifetime gap for record/slot/graph queries without altering the existing
borrowed constructor contract. Its budget adds the actual GraphOwner metadata;
the original constructor already charges graph and complete source-owner payloads.
Prior state dependencies include their own retained metadata too. The final state
releases its witness and source references before releasing its graph owner, which
then frees the graph before its own source references. External consumers of the
borrowed graph still require a retained GraphOwner/state for their entire lifetime.

Controls and all known input/source spans are checked for disjointness before
writes. Opaque allocation interiors and callback/provider contexts additionally
remain caller-disjoint, as documented by the existing source-owner interfaces.
No observer, digest or cancel callback may mutate the immutable source owners.

The focused qualifier preserves the original producer fixtures and borrowed API
regressions, adds exact pool-cap preallocation controls, every candidate allocation
fault, wrong actual catalog owner, generation/cancel/budget/alias refusal, and an
owned GROUPS-compatible state whose external graph, catalog and snapshot creator
references all retire before successful queries. Final cleanup has zero tracked
allocations. Release, ASan and UBSan operate on source-derived synthetic inputs;
no live GROUPS transaction, CLIENT derived state, resources, actor, ACK, renderer
or world authority is supplied by this ownership contract.
