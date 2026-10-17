# Exact source-seal measurement and parent prerequisite

A complete scoped parent adapter is not yet justified by the available lifetime
contracts. This change implements the smallest concrete prerequisite instead of
assigning guessed bytes or pretending to release shared allocations.

`coh_source_sealed_measure` derives the exact private candidate allocation and
complete old+new preflight from actual immutable mesh-batch owners. The existing
factory now consumes this same internal measurement path and remeasures itself;
an externally supplied plan is never a capability. The read-only function makes
no allocation, callback or reference change and preserves outputs on refusal.
It checks known source/control aliases, endpoints, original owned/aggregate caps
and every region's overflow/alignment. It returns actual source identities and
borrowed spans, not caller generation labels. Its plan requires the input batch
and external graph/loader/provider lifetimes to remain intact.

`coh_source_ws_probe` consumes only the root working-set read-only report API.
It adds the **entire actual parent.booked value** to the standalone module's
existing retained_bytes, then measures that unpartitioned contract. It does not
subtract presumed duplicate owners, guessed source reservations or source-loader
capacity. The diagnostic copy-only CohWsPlan uses the measured candidate bytes
and native preparation reserve. It does not authorize use of that partial plan.

The probe never calls prepare/commit/release, changes parent counters or retains
source/parent owners. `admission_permitted`, `input_ticket_verified` and
`external_lifetimes_verified` are always false. Opaque parent/source/control
allocations remain explicitly caller-disjoint, with known source spans guarded.
The underlying standalone module still applies its complete96MiB aggregate
contract; child_limit has not replaced it.

Three concrete lifecycle gaps prevent promotion to a real reservation adapter:

1. The generic parent API has no read-only ticket-to-actual-input-owner lookup.
   A supplied ticket cannot be proven to reserve this actual input batch and its
   exact shared dependency/loader owners. A numeric parent report is insufficient.
2. Sealed destruction releases its Selection reference; it does not destroy the
   externally leased graph or prove that other join/catalog/snapshot/Selection
   references have retired. A ticket for all shared_source_bytes therefore cannot
   be released merely because coh_source_sealed_free returned.
3. Loader/provider leases are externally held. Actual batch getters identify the
   real loaders and reservations, but parent-ticket correlation and provider
   lifetime/footprint ownership remain unregistered. Consuming the batch or seeing
   zero loader dependencies in the new owner cannot release their global charge.

These are precise missing ownership operations. No boolean witness or hash label
can supply them. The next safe full adapter must take actual qualified input,
shared-root and provider/loader billing leases, preserve their charges through
copy/retirement, and release each charge only after its owned resources are truly
destroyed. This prerequisite deliberately makes no stage-composition admission.

The actual CityHall/Plaza source data and full-cache TexOpt/Trick dependency test
still passes after factoring the measurement. New controls verify exact measured
versus actual candidate bytes/peak, zero allocator calls during measurement,
known aliases/endpoints, refused owned limits, actual parent-report immutability,
exact parent.booked addition and an8MiB reservation causing conservative refusal
without mutating parent or output. The generic test reservation is aborted without
allocating a child; it is not treated as an actual source-input ticket.

Release/ASan/UBSan each pass624 controls, including all prior real loader/provider
retirement and both original-delta-qualified packet regressions. This focused
fixture reuses the retained bodies and capture; no full corpus/server/CI repeat.
The exact root parent API source is included read-only in the native/source hash
closure. Final evidence: `evidence/source-measure-host.json`.

No renderer/material/actor/live-world permission, Android execution or physical
Thor qualification is added.
