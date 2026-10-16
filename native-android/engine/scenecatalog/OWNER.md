# Retained catalog ownership and matching diagnostics

`coh_catalog_owner` is an additive preparation-side owner for the already
qualified streaming reader. It copies and SHA256-checks catalog bytes, completely
validates every record, builds original file/slot indexes and retains immutable
storage until the last serialized reference is released. It does not load a
server, build a world graph, resolve assets or permit protocol completion.

The SHA256 callback must be independently qualified and must hash the supplied
owned copy. No implicit provider, trusted-digest shortcut or Android dependency
is selected. Trusted payload/source/inventory pins come from separately admitted
provenance, never from the payload being authenticated. `source_sha256` identifies
the checked source evidence. The host capture runner uses the exact external
capture manifest hash and the original source-runtime inventory hash. Its
explicit OpenSSL provider is host test code only. The portable fixture provider
is a byte-for-byte allowlist of unchanged original producer outputs whose SHA256
values Python hashlib computes; it is deliberately not shipping cryptography.

Owner generations increase exactly by one. Catalog, asset and map generations
cannot regress. A retained generation cannot silently change its corresponding
digest; changed producer evidence requires a new catalog generation. A detached
capture has zero map generation and zero map digest. It can be retained and
inspected, but `compare_groups` refuses it. This is the correct state for the
retained isolated capture: physical Thor/map-session provenance is still absent.

`compare_groups` accepts a complete original GROUPS reader, runs the existing
structural parser without advancing the caller reader and compares new-world,
file count, original definition/reference footer CRCs and active-root count.
Its numeric mismatch mask is diagnostic only. The catalog has no root matrices;
matching footers do not recompute the reference CRC or establish same-session
authority. Matching file names/checksums, authoritative root slot/name/matrix
records, reachable topology, model/material generations, character identity and
complete actor transactions remain separate requirements.

Each file index is 20 bytes and each original slot index 8 bytes. A bounded
on-demand prefix read yields copied definition identity/name/child count and
original wire offsets without allocating or rescanning the file list. Holes
remain distinct from allocated tombstones. The original walk's temporary decoded
record pointers never escape. Refcounts are intentionally non-atomic: the
preparation/publication owner serializes retain/release and retires all borrowers
before dropping their pins. No native renderer/JNI/Combined application is wired
to this module by this change.

For a compact graph, retain its catalog owner before borrowing `owner_bytes`, and
release only after graph retirement. The compact builder already charges its
borrowed input span; charge `owner_owned_bytes - borrowed_span.size` as the
additional owner reservation in its `retained_bytes`. Charge every other live
owner, old graph, retained asset, callback workspace and allocation slack as well.
The owner-create path itself conservatively charges both source input and its
copy, plus any explicitly supplied old owner, even when input aliases old bytes.

The retained authentic capture requires **12,511,918 bytes** of named owner data:
12,179,670 immutable bytes, 331,960 index bytes and 288 owner descriptor bytes on
the qualified 64-bit host. Its independently decoded records remain 40,225 slots,
130,314 children and 508 files. Complete creation peaks at **26,477,502 bytes**
including the caller's original input, one 1,654,842-byte decoded record, the
existing 64 KiB walk stack reserve and a separate 64 KiB host provider reservation.
These are measured/accounted payload values, not allocator overhead or process
RSS. Destroying the original input before indexed reads succeeds. The old eager
materializer and its 32 MiB refusal remain unchanged.

## Reproducible qualification

```sh
python3 native-android/engine/scenecatalog/check.py \
  --source-root . --sanitize --output /private/owner-host.json
python3 native-android/engine/scenecatalog/check_owner_file.py \
  --capture-directory /private/extracted-capture --output /private/owner-real.json
python3 native-android/engine/scenecatalog/audit_missing_sources.py \
  --source-root . --output /private/missing-source.json
```

The portable suite runs original producer fixtures, malformed/truncated payloads,
every owner allocation failure, exact/one-byte-short memory budgets, generation
and provenance rejection, detached map refusal, footer CRC mismatch and retained
lifetime checks. It tracks malloc/calloc/free and runs release, ASan and UBSan.
The authentic replay independently verifies the retained capture/receipt first,
uses real OpenSSL SHA256 over the copied bytes and scans every indexed slot in all
three modes. Eight malformed CLI/digest controls run in each mode. LeakSanitizer
cannot read this managed executor's `/proc/<pid>/task`; the original failure is
retained in the evidence note, and no LeakSanitizer acceptance is claimed.

The existing catalog workflow includes the new owner source and fixtures through
`check.py`, builds both Android ABIs and executes its fixtures on Android 13.
New owner Android execution remains pending that exact-source run. Previously
successful standalone streaming run **38953090330** is reused for its unchanged
streaming scope; its passing artifact identities are recorded in the evidence.
No accepted APK is rebuilt and no new physical test is requested.
