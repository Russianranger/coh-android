# Disposable catalog capture and external delivery contract

This is an independently staged **deployment candidate**, not an authorization to
replace the working MapServer or an authentic capture. The accepted Combined
0.1.7 server/profile/APK remain the rollback and are not inputs to any mutation
performed by `delivery.py`. There is no launch, process-management, profile edit,
server-configuration edit, archive extraction or network operation in this tool.

## Exact binary reused

| Identity | Admitted value |
| --- | --- |
| Source | `887bef22f5f6403d8589ac00a1269c9438e263a6` |
| Original compile run | `38926873046` |
| Artifact | `12058121070` |
| ZIP bytes / SHA256 | 3,286,082 / `a57cb97659db151d66941fa8c00baadb1c70eeedd1c37d46565e687a778b6529` |
| MapServer.exe bytes / SHA256 | 7,487,488 / `f96f5d51467083a58523187760458ad77e6a48d7b696b0d090aafa8e94e95f39` |
| Compile receipt SHA256 | `303bad9e25ed52bf505e98dc568cfe92d58403ddd31f26fe579b40664ae4cdd6` |

`candidate` admits exactly that ZIP and receipt, verifies every inventoried member
and exact bundle membership, verifies the current original exporter/sink include
bytes against the compiled sources, and writes the exact PE, original compile
receipt and numeric deployment plan into a **new** private directory. It does
not rebuild anything. An incompatible new exporter must obtain its own reviewed
compile identity; do not loosen these pins to accept it.

```sh
python native-android/engine/scenecatalog-server/delivery.py candidate \
  --compile-archive /private/windows-12058121070.zip \
  --source-root . --output /private/new-catalog-candidate
```

The candidate's deployment plan explicitly records that actual profile
compatibility, runtime execution, deployment and authentic capture are false.
The plan must not be rewritten into an execution receipt.

## Remaining disposable runtime qualification

A full matching server/runtime/asset/profile copy is currently unavailable to
this worker. The compile ZIP alone has neither the runtime dependencies nor the
actual saved-definition asset generation. No original MapServer was executed;
no catalog was captured. Do not infer compatibility from file/root counts.

Before a separately approved reversible deployment, the integration owner must:

1. Inventory source, complete loaded asset bytes, map identity, runtime binaries
   and a consistent disposable profile/database snapshot. Compare the actual
   loaded MapServer source lineage and certified animation/startup prerequisite
   to the preserved compile receipt. Similar names or matching CRCs do not prove
   matching content. Preserve the inventories and their independently verified
   SHA256 identities. Never expose profile contents or credentials in public logs.
2. Provision a private, disposable Windows/compatible Win32 environment with all
   existing server dependencies. Give it separate database service/data,
   credentials, ports, working directory and process ownership. Confirm it cannot
   connect to the working database or write to the accepted runtime/profile.
3. Reuse the existing qualified normal startup configuration in that isolated
   environment, substituting the admitted exporter only in the disposable copy.
   This tool deliberately supplies no guessed startup command, port or profile
   path. Those values require the actual deployment inventory.
4. Assign a new nonzero uint32 asset generation tied to the inventory. Provision
   a private exclusively owned output parent and an absent drive-absolute output
   filename admitted by `source_sink.inc`. Set
   `COH_NATIVE_SCENE_CATALOG_OUTPUT` and
   `COH_NATIVE_SCENE_CATALOG_GENERATION` only in the disposable process environment.
5. Start the owned isolated DB/Map processes. Preserve the complete numeric sink
   status line: status1 and successful producer completion are necessary. Verify
   the output is final rather than `.partial`; preserve startup and shutdown
   receipts, process/executable identity, generation, map and asset inventory.
6. Obtain the complete structurally validated GROUPS transaction from the same
   loaded generation. Compare file count, definition/reference CRCs and active
   roots. The accepted Thor observation (508 files,33 roots, CRCs3173822562 and
   3649375123) is historical evidence; it must not substitute for a matching new
   capture receipt. Preserve exact file/slot order and all original records.
7. Stop only the disposable owned processes. Preserve capture/provenance receipts.
   Rollback means discarding only the owned disposable files after retaining
   evidence. The working server/profile/database/APK require no restoration
   because they were never modified.

## External storage admission

Store `catalog.cohcat` outside the APK, under a generation and independently
verified asset identity. The delivery binding is a small JSON document (at most
64KiB) with exactly these fields; SHA256 values are lowercase64-character hex:

| Field | Required value |
| --- | --- |
| `schema` | `coh-catalog-delivery-binding-v1` |
| `catalog.bytes`, `catalog.sha256` | Exact complete exported payload,48bytes–32MiB |
| `generation` | Nonzero uint32 inventory generation |
| `groups.files` | Complete GROUPS file count,at most1024 |
| `groups.definitions_crc`, `groups.references_crc` | Original validated GROUPS footer uint32 values |
| `groups.active_roots` | Original active-root count,at most65536 |
| `groups.receipt_sha256` | Exact independently reviewed GROUPS receipt |
| `provenance.source_revision`, `provenance.exporter_sha256` | Exact source and PE identities above |
| `provenance.asset_inventory_sha256` | Actual complete source asset inventory |
| `provenance.profile_snapshot_sha256` | Private disposable profile snapshot identity |
| `provenance.map_identity_sha256` | Loaded map identity receipt |
| `provenance.capture_receipt_sha256` | Actual runtime capture/provenance receipt |

The integration owner reviews those receipts and supplies the **binding SHA256
through an independent trusted channel**, not by hashing an untrusted sidecar
and trusting its assertions. A hash binds bytes; it does not establish who
produced them. The admission tool checks digest shapes and pins, but does not
independently examine the external receipts or claim their authenticity.

```sh
python native-android/engine/scenecatalog-server/delivery.py admit \
  --catalog /private/captured/catalog.cohcat \
  --binding /private/approved-binding.json \
  --binding-sha256 TRUSTED_BINDING_SHA256 \
  --output /private/new-generation-storage
```

This command verifies stream size/SHA256 and the exact header/footer binding,
then copies in64KiB chunks, rehashing the actual copied bytes. Names/records in
the catalog are not filesystem paths and are never extracted. Symlinks,
hardlinked inputs, linked ancestors, duplicate JSON keys, invalid field/type
sets, nonfinite values, over-limit files and preexisting destinations reject.
Inputs/output parents must be private, exclusively owned and stable; path checks
are not protection for an attacker-writable parent. Failure removes only files
created by this invocation in its newly created directory. No existing directory
is replaced. Consumers must require the final `storage-admission.json` receipt;
an interrupted partial directory is never an accepted generation. Directory
rename/fsync and crash recovery are the future Android storage owner's concern.

The receipt deliberately reports `native_decode_completed:false`,
`authentic_capture_established:false`, `graph_published:false` and
`renderer_authorized:false`. Header admission is not complete catalog decoding.
A correctly hashed malformed record may pass this storage gate and MUST be
rejected by the next native gate. Tests retain that distinction explicitly.

## Android import and atomic publication order

This Python tool is offline deployment/storage tooling; it is not wired into the
Combined APK. The coordinator owns the eventual Java/JNI/storage implementation.

1. Independently validate provenance and digest of the complete external binding.
2. Verify exact source, asset, profile, map and generation ownership and payload
   SHA256 before passing bytes to the native decoder. Retain those identities
   with the generation; deny unknown/stale generations.
3. Decode on a preparation thread using unchanged `coh_scenecatalog_preflight`
   and `coh_scenecatalog_load`. Never publish based on the delivery header alone.
   Complete record/cursor/name-CRC validation and ownership limits still apply.
4. Bind the matching complete GROUPS via `coh_scenecatalog_match`; apply the
   scenegraph with qualified generation-bound geometry/material callbacks and
   recompute both checksums, transformations and graph semantics. An equal footer
   is not enough. Preserve file/slot identities, null holes and tombstones.
5. Account for `CohCatalogReport.owned_bytes`, borrowed input, retained prior
   catalog, old/new graphs, scratch and asset views in one aggregate preparation
   budget. Catalog32MiB ownership and64MiB replacement limits are independent
   sublimits, not a whole-process cap. No decoding/allocation runs on render.
6. Retain catalog lifetime until the synchronous graph import returns; it lends
   pointers to immutable records. The graph deep-copies them. Coordinate immutable
   snapshot/resource-generation ownership with renderer integration.
7. Publish only after complete graph AND authoritative character validation.
   Failure keeps the old generation; it never sends READY or grants live-world
   authority. Preserve exact admitted external assets for rollback.

The test suite covers bounded transport, context/footer mismatches, corruption
between initial read and copy, no-replace behavior, link refusals and rollback.
The existing native/source/ASan/UBSan catalog and sink suites remain separate.
No new Android or physical acceptance is inferred from these Python tests.
