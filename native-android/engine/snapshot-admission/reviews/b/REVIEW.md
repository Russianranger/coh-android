# Independent runtime snapshot review B

Review base: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.
Only this new review directory is changed. Existing graph/catalog, protected
runtime and concurrent worktrees are read-only. No capture, server, workflow,
APK build, live networking or production publication was performed.

## Retained bytes and independent replay

The retained successful artifact ZIP SHA256 is
`8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d`.
All 34 ZIP members pass CRC checking. `inspect_retained.py` independently parses
the pinned actual binary envelope without importing either the C decoder or the
new admission module. `independent-envelope.json` records every exact root
file/slot/name, raw finite matrix and each distinct external object/wire digest.
All 33 active roots have regular file/slot ownership. All seven future objects
have original ID zero; this does not collapse their independently named and
indexed captured identities into one object. No matrix is fabricated.

The pinned `engine/scenegraph/check_runtime_snapshot.py --sanitize` was run
against these exact actual catalog/snapshot bytes. Original upstream files were
read from the preexisting recovery checkout; initial/final source checks apply.
The resulting original-source, native, producer and helper hashes match the
hosted diagnostic exactly, as do fixture and actual-capture results. The fresh
receipt is `native-replay.json`: eight fixtures, 21,726 release controls with
matching ASan/UBSan controls; actual capture passes 17 controls in each mode.
No server startup was repeated. ASan leak sanitizer is disabled as explicitly
reported by the original checker; owned allocation failure cleanup is checked.

All three modes agree on:

- 508 files, 40,225 regular definitions/slots and 130,314 regular child edges.
- 33 active root records, all 33 original packed/raw matrix pairs verified.
- Definition CRC 3173822562 and reference CRC 3649375123 recomputed and verified.
- 15,352 root-reachable regular definitions and 57,710 reachable edges.
- Maximum root-reachable depth 69.
- Seven real runtime future objects; one is root-reachable.

| Captured future identity | Root-reachable | Source model | Bounds lookup | Library path |
|---|---|---|---|---|
| `_cot_warpgate_base` | No | Absent | Miss | Empty |
| `_cot_warpgate_glow` | No | Absent | Miss | Empty |
| `_mmayhem_curtain_8_01c` | Yes | Absent | Miss | Empty |
| `_mmayhem_curtain_8_02c` | No | Absent | Miss | Empty |
| `_mmayhem_curtain_8_03c` | No | Absent | Miss | Empty |
| `_mmayhem_curtain_16_01c` | No | Absent | Miss | Empty |
| `_mmayhem_curtain_16_02c` | No | Absent | Miss | Empty |

The previous missing ownership/name-closure input is now present in this source
snapshot. This does not turn these empty futures into renderable geometry.
The reachable curtain requires separately source-qualified future/lifetime
semantics. The six unreachable futures remain retained and audited, not removed.

Original reference CRC covers root and first-child names, not all transforms.
Exact matrix validation and source/run SHA bindings are separate checks.
Date-like asset generation 20261016 and matching CRCs are not physical-session
identity. This capture contains no received live GROUPS transaction.

## New offline admission review

Reviewed A's new `admit.py` SHA256
`66c33602009b4247c96c8c6d9e6a394f51852842536ae8aa2c732cad191f8bbb`
and adjacent `capture-trust.json` SHA256
`ad496a806005bb272acd1a30e54260ac46ed56c0768cb22c77161a8ee23811c5`.
The CLI successfully admits the exact retained artifact for offline analysis.
The final reviewed revision additionally normalizes zlib/EOF failures into
AdmissionError; it does not change any binding or authority checks.
The local trust manifest seals member names/sizes/hashes; archive-provided hashes
alone cannot admit changed bytes. Entry count, duplicate names, aggregate bytes,
symlinks, encrypted members and duplicate JSON keys are checked. No extraction
or archive-supplied code execution occurs. Source/run/catalog/snapshot/cleanup
receipts and all qualification-mode results are cross-bound before returning a
frozen result with immutable reachable-name tuple.

The reviewed module is suitable for this exact retained offline artifact. Its
positive result is not a generalized new-capture admission or native scene owner.
All live world, actor, renderer, graph publication and physical generation flags
remain false. Its independent mutation suite is owned and recorded by A.

## Remaining world prerequisites

A matching live GROUPS/session generation, immutable graph ownership and future
representation, authentic GEO/material/trick/LOD admission, complete authoritative
actor transaction and atomic GLES publication remain unqualified here. No Android
execution, physical Thor or live world acceptance is claimed by this review.
Native audited ownership accounting is not complete application RSS or GPU memory.
