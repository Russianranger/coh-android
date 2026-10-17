# Retained runtime snapshot admission

Pinned implementation base: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.

This host-only Python module admits the retained evidence artifact from successful
run `38977202310`, artifact `12079509924`, for **offline analysis only**. It does
not change the catalog owner, graph, protocol, renderer, server or Android clients.
No capture, server startup, extraction or archive-supplied code execution occurs.

```
python native-android/engine/snapshot-admission/admit.py /path/to/evidence.zip
python native-android/engine/snapshot-admission/test_admit.py --capture-zip /path/to/evidence.zip
python native-android/engine/snapshot-admission/qualify.py --capture-zip /path/to/evidence.zip --output /new/path/qualification.json
```

`validate_archive(path)` returns a frozen `OfflineAdmission` only after every
member and all cross-receipt checks succeed. Refusal raises `AdmissionError`;
the CLI emits a nonzero status and no success JSON. Callers must treat the result
as provenance evidence, never a live rendering/protocol capability. No production
caller is added in this change.

The adjacent reviewed `capture-trust.json` pins all 34 member names, sizes and
SHA256 values. It records the historical container SHA for comparison, while
admission intentionally allows benign ZIP container metadata/compression changes.
Only STORE and DEFLATE are accepted. Duplicate/missing/extra names, symlinks and
special files, oversized archives, changed payloads and invalid ZIP CRCs refuse.
The compressed input is bounded to 4 MiB and uncompressed members to 16 MiB;
member sizes are checked before bounded reads. These limits describe input bytes,
not a Python-process memory cap. The retained payloads are held once for receipt
comparison; there is no claim that the interpreter heap is below 16 MiB.

The trust manifest is part of the reviewed source, not an archive input or a
caller-selected trust root. Its hashes bind the exact catalog, runtime snapshot,
source/run identities, cleanup receipt, source closure records, all retained logs
and diagnostics. Further semantic checks bind generation, exact catalog equality,
source revision/tree, exporter identity, runtime inventory, source/run hashes,
cleanup and offline scope. Release/ASan/UBSan **retained diagnostic receipts** must
agree exactly, including original CRC verification and all 33 root matrices.
The module does not execute those native tests again and does not independently
inspect a PE absent from this evidence archive. Source identity's compile receipt
hash remains retained provenance; no new binary qualification is claimed.

Actual retained diagnostic outcome: 33 roots/matrices, seven runtime future objects,
15,352 reachable regular definitions, 57,710 reachable edges, maximum depth 69.
Exactly one future object, `_mmayhem_curtain_8_01c`, is root-reachable; all seven
have no model, library path or successful bounds lookup. This admission preserves
those facts without silently inventing definitions or authorizing graph publication.
A matching live GROUPS transaction, physical generation, complete asset/material
closure and complete authoritative actor remain separate prerequisites.

Tests independently mutate each of the 34 members, remove every member, introduce
ambiguous/hostile ZIP names, duplicate members and symlinks, violate compressed
bounds, corrupt JSON, and exercise cross-receipt substitutions without relying on
the digest seal. No Android, physical Thor or real world qualification is claimed.

The coordinator qualifier runs both the seven-group implementation suite and F's
17 independent controls, binds their exact source hashes, refuses source or input
drift, and creates a complete receipt without replacing an existing output.
The narrow `native-snapshot-admission.yml` workflow downloads only the retained
successful artifact and validates its historical outer SHA before running these
checks. It starts no server and rebuilds no native binary or accepted APK.
If the retained artifact expires, the workflow refuses; it does not recapture.
