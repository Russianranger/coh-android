# Parent reservation foundation — uninstalled

The existing dictionary APIs enforce small standalone aggregate caps. Their
`retained_bytes` fields cannot omit a live world or another dictionary. This
module does not alter those APIs, raise their caps or establish a combined
pipeline. Concrete source-owned adapters remain required.

This ledger books full child persistent/temporary/call reservations under one
96MiB parent, including actual fixed parent metadata and a 16KiB call reserve.
It allocates only at parent creation. Preparation either reserves everything or
changes nothing. Commit is permitted after actual child temporary cleanup, and
can only shrink persistent reservation. Abort/release follow actual cleanup;
the ledger itself cannot free or inspect a module owner. Outstanding tickets
prevent parent destruction. Serial/slot/parent correlation prevents stale or
wrong-parent tickets from retiring a newer reservation. These are accounting
identifiers, not source identities, session tokens or security capabilities.

An owner pointer is only a billing key. The generic API cannot establish actual
sizes, deduplicate source dependencies, retain a provider or prove liveness.
Qualified adapters must derive costs and dependency identities from actual
opaque module owners, reserve all new storage/work before callbacks/allocation,
keep every source/provider lease live, and retire charges only after resources
are really retired. Duplicate keys are rejected, not implicitly deduplicated.
Unregistered external allocations, actual stack/allocator slack and borrowed
inputs must also be reserved by the future concrete integration.

Child policy ceilings never replace the unchanged module caps. A future nested
entry point must explicitly accept and validate the parent reservation. Passing
only a child's bytes to a current standalone all-retained API is **not**
authorized by this module. No current origin/category/class/graph/renderer
constructor consumes these tickets. No JNI/CMake/client path installs it.

Host tests use synthetic billing keys/byte reservations and exercise global and
child cap refusal, exact capacity, transactional preservation, slot exhaustion,
stale/cross-parent tickets, commit shrink, duplicate owners and lifecycle. Actual
parent allocator calls are counted. They are not integrated allocation/RSS or
world+actor/GPU measurements. Android builds/execution, source generation, server
world and Thor acceptance remain unqualified.
