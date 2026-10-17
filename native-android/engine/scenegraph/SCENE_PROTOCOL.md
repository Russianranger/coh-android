# Immutable native scene protocol inputs

`CohSceneProtocol` owns a bounded descriptor array over a fully qualified compact
source graph. It retains the actual CatalogOwner and complete SnapshotOwner, and
optionally a validated GROUPS witness. Every descriptor preserves exact original
file/slot/node order, tombstone/external classification and the complete original
wire span, including optional metadata. No eager definition tree or duplicate
wire allocation is introduced. This is protocol-input state, not CLIENT derived
state or a server-authoritative world.

The graph itself remains caller-borrowed. The caller keeps its existing graph
lease and source-owner lifetime contract through every state ref/query and all
candidate publication. State references do not retain or own the graph. Actual
graph catalog/snapshot spans must equal those retained by the supplied owners;
byte-equal separate owner allocations refuse. SnapshotOwner's actual catalog
binding, snapshot/run hashes and audit flags must match the graph's recorded
catalog/source/run/asset identities. Caller assertions do not replace these
recorded ownership checks. No new hashing of already immutable owners is needed.

NULL GROUPS import produces a source-only seed. Every update_presence_known flag
is zero: no event or omission is inferred. A nonNULL import requires witness,
expected binding and exact reader together. The complete seed/witness comparator
runs before the candidate can escape; eligible equal updates and verified saved
omissions are recorded for ordinary slots. Captured external future objects
remain separately classified with unknown ordinary-update presence. No client
cache execution is required to retain raw omitted fields. CLIENT post-trick,
resource, material, LOD, visibility/collision and actor prerequisites remain open.

Local preparation generation advances exactly one. Catalog/asset/graph/snapshot
generations cannot regress. A retained catalog generation preserves its exact
catalog/snapshot/source/run identities; an unchanged asset generation preserves
inventory identity. Within the same source generation, a checked GROUPS state
cannot silently become source-only. A candidate records its exact expected
previous state pointer. Serialized publication transfers it only if that exact
state is current and the next generation matches; competing stale candidates
refuse without changing pointers. This is not cross-thread atomic publication.
The caller keeps old alive until publication or discard, and retires all borrowers
before releasing old. No implicit retain of old creates a hidden dependency chain.

The state retains its explicit actual owners and releases every acquired ref on
failure. Reports, output pointers, old states and incoming readers remain unchanged
on every refusal. Provisional descriptor writes and emitted masks never escape.
Cancellation before, during and after construction discards the whole candidate.
The graph adapter getter returns only the same borrowed source graph, with no
world/resource/actor token. Record/report getters reject overlap with known state
or source allocations. Opaque owner/graph/provider allocations remain disjoint by
caller contract. Reference operations are serialized, not atomic.

Named budgets charge old+new state and dependencies even if aliased: compact graph
payload, actual CatalogOwner allocation, complete SnapshotOwner allocation and
optional witness allocation. The new witness owned-bytes getter returns actual
payload only, not its already-accounted source dependencies. Temporary input
reader bytes and emitted mask are charged for their construction phase. The
constructor adds64KiB for its own union-reused metadata frame and128KiB for the
nested qualified GROUPS/seed core. Snapshot reports and graph reports share one
union to avoid simultaneous large stack objects. Other owners, allocator slack,
opaque callback/digest contexts and provider stacks belong in retained_bytes.
Owned32MiB and aggregate96MiB caps remain unchanged. Named reservations are not RSS,
GPU or whole-process budgets. Old refs are not retained implicitly.

Qualification uses the same four unchanged original worldSendUpdate fixture
transactions and independently admitted source owners. It checks source-only and
witness modes, exact full-wire views and existing compact-graph lookup, separate
byte-equal wrong owners, stale labels/generation/publication, each candidate
allocation fault, cancellation at every stage, aliases, bounded ownership and
report rollback. No live packet or same-session source generation is claimed.
All CLIENT-derived, bounds-cache recomputation, source-generation and world flags
remain false. No ACK, Android build, emulator/Thor qualification or new APK is
produced by this module.
