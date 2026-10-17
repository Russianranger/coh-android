# Immutable captured-source import

`coh_catalog_snapshot_create` retains the existing immutable catalog owner and
copies the bounded runtime sidecar. It checks every catalog binding field, exact
SHA256 input bytes, source/run labels, generation progression, complete original
source name closure, root matrices and CRCs through the existing bounded audit.
Failure leaves both prior import and caller output unchanged. Retain/release and
borrowed views are serialized by the caller; the catalog remains alive after the
caller's original reference is released. Views do not expose mutable bytes.

The aggregate budget includes the caller's original snapshot, the owned copy,
catalog span and indexes, the import/report storage, existing old import, any
separate old catalog owner, audit scratch and its named stack reservations.
The same retained catalog span is charged once. Other input owners, digest
scratch and callback work belong in caller `retained_bytes`. Limits describe
named allocation boundaries, never process RSS, allocator metadata or GPU memory.

A source generation must still be independently admitted from the source/run,
PE, inventory, same-boundary capture and cleanup receipts. This API establishes
immutable source preparation, not live-session generation, asset authority,
actor identity, GROUPS receipt, ACK permission or renderer publication. Production
build integration remains disabled while the runtime matrix reader is exposed
only through the existing standalone diagnostic bridge.

Run the exact captured archive through:

```
python native-android/engine/scenecatalog/check_snapshot_owner.py \
  --capture-zip PATH/evidence.zip --output NEW_RECEIPT.json
```

The archive must match SHA256
`8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d`.
The driver verifies ZIP CRCs and exact catalog/snapshot digests, compiles release,
ASan and UBSan modes, and binds source/binary identities. It covers malformed
pins, every-17-byte truncation, header byte mutations, three preparation/pool
allocation failures (the existing audit separately qualifies its internal
allocations), provider refusal, cancellation, exact budget boundary, generation
rollback, distinct old catalog ownership and retained-reference lifetime.
The inventory digest in the harness is an explicitly labeled fixture marker;
this suite does not claim authentic whole-runtime inventory admission.

LeakSanitizer cannot inspect `/proc` task state in this sandbox and exited with
its documented ptrace/environment fatal error. The retained failure receipt
records this boundary. ASan uses `detect_leaks=0`; explicit wrapped allocation
balance checks cover each refusal and final cleanup, and no LSan success is claimed.

The composed actual-corpus test consumes B's immutable graph API. A retains the
catalog and sidecar throughout B's borrowed-input lifetime. The caller charges A
owner descriptors, catalog indexes, the other retained import and original input
buffers in `retained_bytes`; B charges its borrowed spans and graph pool. A
separate explicit lease is released only after the last graph is retired. The
test validates graph generation replacement, a failed snapshot pin replacement,
atomic publication and continued root access after the caller's catalog/import
references are released. This is source graph lifetime evidence only.
