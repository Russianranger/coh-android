# Original runtime roots and future-object snapshot

This separate nonshipping experiment captures **new missing data**: original
root slots/transforms and actual ownership of child objects outside regular
saved-definition files. The retained catalog and accepted APKs are unchanged.
Neither the saved catalog ZIP nor the accepted 0.1.7 evidence contains those
root values. A fresh private process is necessary because the earlier owned
Wine/PostgreSQL processes were completely stopped.

The hook runs once, immediately after the original normal `groupLoadMap` and
`dbSetupMap`, before `dbReadyForPlayers`. The owner thread emits the unchanged
catalog and new sidecar without yielding, loading new objects, mutating source
objects or sending a packet. The catalog is only an equality witness: its full
12,179,670 bytes must hash to
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`.
The original retained corpus remains the canonical input.

`COHRTS01` is a little-endian diagnostic envelope. The 80-byte header contains
version/header/total bytes, asset generation, catalog bytes, files, slots,
definitions, children, root-slot count, active roots, external count and both
original name CRCs; the final 16 bytes are zero. Every root slot follows in
original order, including null-definition tombstones. A present record has a
32-byte identity/extent header, canonical NUL name, 12 raw F32 matrix values,
and unchanged original byte-aligned `sendMat4` output. Regular targets use
original file/slot identity. External targets use a separate ordinal.

External ordinals are assigned by actual pointer incidence from all regular
children and roots, then their bounded external closure. The `pre_alloc->defs`
array is never enumerated, and source numeric IDs are not treated as unique.
Every target must be active, canonical name lookup must return the same pointer,
and regular file/slot or global pre-allocation ownership must match exactly.
Distinct pointers with the same canonical name are refused. Every external has
a 36-byte header (ordinal, original ID, four ownership flags, model-present,
name bytes, wire bits/bytes, bounds-lookup result, library-path bytes), two
60-byte explicit bounds records, name, optional library path and unchanged
`sendDef` bytes. Bounds contain 13 F32 values, signed recursive count and a
26-bit flag mask in original `GroupBoundsMembers` declaration order. No native
bitfield padding or pointer addresses are serialized.

`objectLibraryGetBounds` writes only a zeroed scratch definition. Its raw-name
lookup and `objectLibraryPathFromObj`'s public-name lookup remain separate
observations: a path does not imply bounds were found. Missing lookup output
is zero; the actual live bounds are still preserved. This records source facts
without making a future object a supported native rendering primitive.

Bounds are 1,024 files, 65,536 regular slots and root slots, 64 external objects,
262,144 combined regular/external child links, 256-byte NUL names/paths,
256-byte matrix wire, 4 MiB definition wire and 16 MiB total sidecar. Source
record creation uses the original packet allocator, so these are output and
traversal bounds, **not a hard process allocation/RSS limit**. The native
diagnostic consumer has independent aggregate ownership accounting.

The paired sink uses the qualified C-drive no-reparse checks, exclusive partial
files, flush/close and rename-without-replacement. Failure can leave one final
file, which the wrapper preserves explicitly as unaccepted evidence. Complete
outputs are retained before graph decoding, then all owned process groups,
private Wine prefix and PostgreSQL are stopped. No native client, TestClient,
AuthServer or application READY/ACK runs in this scope.

The wrapper reuses the exact donor/assets, original DB schema/ODBC probes,
inventory, progress, private copy, listener and owned cleanup helpers. Diagnostic
export recovers the private credentials even after partial PostgreSQL setup and
redacts each bounded log before taking its tail. Unverified credentials suppress
diagnostic export. The private copied executable is verified before launch and
again after capture. It builds only a new diagnostic MapServer because the prior exporter
PE cannot emit roots or future ownership. `source-identity.json` binds exact PE,
stage/compile receipts, runtime inventory, map and source pins.
`run-identity.json`, written before Map launch, adds a fresh nonce and disposable
DB-schema identity. Their exact-byte SHA256 values are independent of the final
receipt. `snapshot-binding.json` exists only after exact catalog equality and
successful cleanup and names `catalog.cohcat` and `runtime.cohrts`. The offline
consumer runs after shutdown. All records remain **source/runtime snapshots**,
not real GROUPS transactions, selected actors, live-world or Thor acceptance.

Run `check_snapshot.py --source-root . --sanitize --output <new.json>
--fixtures-output <new-directory>` for new producer, sink and deployment
controls. Original `sendDef`, `sendMat4`, packet and CRC bodies are reused
unchanged; fixture objects are synthetic. The known legacy bit-packing oracle
is excluded from UBSan while the new observer is instrumented. ASan and UBSan
run the observer and actual paired sink. The local WinAPI shim proves sink
control flow, not Windows execution. Existing source-only catalog validation
and accepted APK/device tests need no repeat.

The later real GROUPS path is separate. The recovered native world-capture probe
requires an actual initialized saved character. The existing one-row
`seed_fixture` (ID90001/auth77/map5) is a schema/restart fixture and cannot satisfy
that prerequisite. Exact original `TestClientCreate.exe` and bridge binaries are
available in the .34 donor; a future experiment can create a real disposable
character, use its own original full protocol, request protocol quit, independently
verify saved SQL and disconnected state, and only then reconnect through the
native three-command capture. That probe still must never send READY,
RECEIVED_CHARACTER or full-update ACK. Matching later live generation also needs
an omitted-definition witness/mutator audit at actual GROUPS serialization;
startup counts/CRCs alone do not prove matrices or definitions stayed unchanged.
