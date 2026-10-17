# Owned source body to fixed legacy CPU formats

`coh_source_rigid_v2_create`, `_v3_create`, and `_v4_create` are separate opt-ins.
Their request supplies only a whole-join source ordinal and external digest/material
callbacks. The actual opaque SourceBody supplies the exact file, complete model
name, whole-body SHA, observed record SHA, graph node, owner/generation counters,
source/run commitments and asset identity. The common implementation checks the
actual version before allocation or material callbacks. Default source0/8 and
separate v5/v7 factories keep their existing policies.

Successful construction transfers the Body to the CPU owner. Every refusal leaves
the caller's Body, output and report unchanged. Renderer/material pins retire
before the Body. Graph and loader are borrowed dependencies and must outlive all
owners, as documented in `coh_source_rigid.h` and the SourceBody contract.

The authentic test covers all 35 unique root-reachable v2/v3/v4 GEO-model pairs,
36 captured owner routes and ten unique files. The duplicate v3 Hallway mesh has
two independently checked source-record identities. Each request passes through
the registered exact-cold-capture selection and whole-body validation. Every part
retains its captured texture ID/name/count and matches the complete CPU packet
qualified against unchanged original delta decoding in low-level commit
814f3ebfe. That dependency receipt is rehashed, its source pins verified and each
route compared against its exact body/record/packet expectations by the driver.
Original 32-bit readModel execution remains unqualified locally (ELF32 errno8).
GRID, reduction and legacy LOD metadata are preserved; their runtime application
and portal/invisibility behavior are outside this CPU conversion scope.

Release, ASan and UBSan each passed 955,827 integrated controls, including default
0/8 and separate v5/v7 routes, wrong-policy, digest, ownership, aliases, cancellation,
material refusal, allocation failure, rollback and complete allocator balance.
The test mounts fourteen immutable loose sources sequentially (capacity16), with
32MiB whole-loader reservation and existing byte/cache caps unchanged. Its maximum
named legacy bridge reservation is 71,454,259 bytes, including shared actual
retained owners once, current file owner, loader reservation, caller reservation
and conversion scratch/candidate peak. This is not process RSS or Android heap.
The inherited `body_peak_bytes=71,063,020` is the earlier Neon Body measurement,
not this bridge maximum. No eager all-file mesh/texture residency is claimed.

All material callbacks are explicit fixtures. Derived origin is limited to the
registered procedural cold-capture FILE scope; direct-open observation, CLIENT
materials/LOD, live generation and world authority stay false. No Android, server,
CI or APK execution was performed for this tranche.

Reproduce with `check_source_rigid_legacy_formats.py`, passing the retained capture,
body directory and frozen814 renderer tree. The final receipt is
`evidence/source-rigid-legacy-final-host.json`; default and v5/v7-only regressions
are recorded separately beside it. No existing historical receipt is replaced.
