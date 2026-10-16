# Bounded catalog streaming and external capture

`coh_scenecatalog_walk` validates every original serialized definition while
owning one decoded record at a time. It reuses `coh_scenegraph_definition_read`
and disposes that record before continuing or returning any callback failure.
The existing eager catalog importer's 32 MiB cap and replacement rollback are
unchanged. The API and native file validator do not publish a graph or actor.

Run this synchronous preparation off the render thread. The caller supplies
working, aggregate and retained-byte limits. Working memory
charges the entire immutable input span, a 64 KiB reserve for stack/descriptors
and bounded preflight indexes, and the one record's allocated payload. Its
ceiling remains 32 MiB. Aggregate memory adds the caller's declared maximum
external retained state and cannot exceed the shared `COH_SG_TRANSACTION_MAX`
96 MiB cap. Declare old graphs, candidate graphs, retained assets, callback
scratch and other external state; do not under-report growth during callbacks.
These are payload/stack accounting bounds, not allocator metadata or process RSS
measurements. On decode failure, partial allocations have already been freed but
the shared decoder provides no peak-byte receipt; `failed_record_peak_unknown`
marks that uncertainty. Known peaks then cover successfully decoded records only;
`working_upper_bound` and `aggregate_upper_bound` retain conservative admitted
bounds. Complete successful walks report their measured payload peak. The host GCC-O2 emitted-frame audit sums to 27,744 bytes for a
conservative decoder/preflight closure, below the charged 64 KiB. Android stack
execution and device RAM measurements remain separate qualification.

Input/reserve and aggregate budgets are admitted before preflight reads the input.
The complete envelope/name-CRC/count preflight runs before any callback. File
callbacks include empty files and exact original name, index, bounds checksum,
slot count, allocated-record count and catalog generation. Slot callbacks visit
all original slots in increasing order. A null hole has `allocated=0`, no decoded
definition and zero wire offsets/lengths. An allocated tombstone has
`allocated=1` and `definition->in_use=0`. Allocated records expose the exact
16-byte source record header offset, original serialized-wire offset/length,
bit length and scalar alignment, plus the borrowed decoded definition and input
span. Child names and matrices are available in that decoded definition.

Decoded pointers and all view descriptors expire when the callback returns.
Budget, visitor, report and callback-control storage must be disjoint from input
and each other; budget and visitor remain immutable for the call. The callback
must copy required compact fields or retain offsets into separately
owned, immutable input storage whose lifetime it explicitly maintains. It must
not mutate borrowed input or views. Callbacks stage changes only: even after an
earlier callback succeeds, a later record, allocation or cancellation can fail.
The caller discards all staged state on any non-OK return. Only complete success
permits the next independent validation step; it never grants rendering or ACK
permission. A null visitor performs complete record validation without callbacks.

COHCAT01 stores root count and reference CRC, **not root slots or transforms**.
Those must come from the corresponding original GROUPS transaction. Name CRCs
are not payload authentication. Verify the external SHA256/source provenance and
asset generation before passing the bytes to this API. Complete wire validation
also does not guarantee that every child name resolves to a saved definition:
original client `groupDefFuture`/asset loading can supply additional definitions.
The compact graph owner must reject missing names and unsupported asset semantics
without publishing partial topology.

## Authentic isolated Atlas capture

[Run 38948147691](https://github.com/Russianranger/coh-android/actions/runs/38948147691)
executed the unchanged qualified exporter on the disposable public-asset Atlas
server. [Artifact 12067129520](https://github.com/Russianranger/coh-android/actions/runs/38948147691/artifacts/12067129520)
is 2,145,443 bytes with SHA256
`6f45437efd8fe7c16b7468634f2ad1914ba446b739632e59d65dc6912624ade3`.
Its `capture/catalog.cohcat` is 12,179,670 bytes with SHA256
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`.
The source-bound external manifest is
`../scenecatalog-server/evidence/capture-38948147691/external-capture.json`.
The payload remains external; it is neither checked into Git nor embedded in an
APK. Preserve the artifact before its stated retention expiry.

The catalog contains 508 files, 40,225 allocated definitions/slots and 130,314
child links. Complete native streaming validation consumed every record and all
12,179,670 bytes under release, ASan and UBSan. The recomputed definition-name
CRC is 3173822562. The original producer's reference CRC3649375123 and active
root count33 match the historical accepted footer; their actual root transforms
are not in the catalog and cannot be recomputed from this sidecar alone.

Peak record payload is 1,654,842 bytes; charged input+reserve+record working memory
is 13,900,048 bytes. The independent F audit measured the same peak. Eager import
still refuses before allocation: its fixed-array minimum alone is 44,548,720
bytes, beyond 32 MiB. The original hosted receipt is preserved exactly: its
`passed:false` and `historical_thor_footer_matches:false` reflect the eager
validator failure before the footer comparison was reached. They do not report
an observed footer mismatch. Later offline streaming qualification is separate.

The source inventory remained unchanged and all owned server/PostgreSQL/Wine
cleanup checks passed. This used a new empty disposable database and public
asset fixture, not the user's Thor profile. It establishes authentic saved-record
capture and host validation, not a same-session GROUPS binding, current Thor
asset generation, resolved geometry/materials, authoritative actor or live world.
B's compact reconstruction independently found an unresolved child such as
`_cot_warpgate_base`; validation success must not erase that graph blocker.

Reproduce offline qualification after verifying and extracting the exact artifact:

```sh
python3 native-android/engine/scenecatalog/check_file.py --source-root . \
  --capture-directory /private/extracted-artifact \
  --output /private/new-stream-qualification.json \
  --binary /private/new-qualified-validator --sanitize
/private/new-qualified-validator /private/extracted-artifact/capture/catalog.cohcat 20261016 --stream
```

The driver verifies exact captured payload and receipt identities against the
committed external manifest, original rich source fixtures, malformed CLI/file
controls, complete capture decoding in release/ASan/UBSan and unchanged eager
refusal. The exact tested release executable is retained. The capture does not
need another server startup to improve or qualify a native consumer.

Source/API dependency: qualified graph commits `c147e36ac` and `72b2518fb` supply
the current dynamic decoder and shared transaction ceiling. Rebuild affected
native components from one tree; accepted APKs remain untouched. Rolling back
this additive API/CLI/tests restores the eager importer without altering any
accepted client, server profile or captured artifact.
