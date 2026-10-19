# Bounded source occurrence to retained geometry integration

`coh_source_placement_prepare` connects the existing streamed source-instance and
candidate pipeline to the existing sealed SOURCE geometry subset. It performs
indexed access only, with no allocation, asset loading, callback, reference
transition or renderer publication. The offline preview remains unchanged.

The resolver requires the **same actual** join, catalog, snapshot and borrowed
graph owners. Equal source hashes or generation labels on a distinct join refuse.
It checks node-to-source ordinal, exact original resource-record bytes/hash,
model identity, graph/catalog generations, finite source matrix and candidate
semantic flags. Indexed root validation preserves the active original root slot;
root occurrences additionally match the exact original root matrix/node. Sealed
entries retain previously validated source model/header/material partitions and
canonical unscaled geometry. No material is synthesized or rebound.

The caller supplies an **unmodified successful candidate** from its retained
pager/context/graph contract. The resolver is not an independent authentication
of an arbitrary supplied matrix, path ordinal or descendant occurrence. Those
are source-walk values, never current server poses. Missing prepared geometry
and no-model occurrences return separate explicit diagnostic results. Only the
SOURCE_BODY unresolved bit may clear; every CLIENT material/LOD/visibility/cache
and live-generation restriction remains. Output geometry pointers borrow the
sealed owner; all its source/context/graph leases must remain alive.

## Memory and ownership

Before parsing the original resource row, the synchronous operation charges the
actual sealed allocation, its exact retained Selection/profile/join/catalog/
snapshot/graph tree, the separate candidate-context allocation, full input/output
and budget descriptors, and a 16 KiB native call reserve. The common join tree is
charged once because actual owners were matched. Every other live loader,
provider, walker, pager, batch, bounds array, old output, actor, GPU allocation,
allocator slack and runtime/callback workspace belongs in `retained_bytes`.
Overflow or the unchanged 96 MiB aggregate ceiling refuses before source parsing
and preserves output. Known sealed/context/map/source/control aliases and pointer
endpoint overflow refuse before dereferencing supplied candidates.

This is a standalone measured admission contract, not an installed parent ledger
adapter. No guessed owner ticket or lifetime boolean is accepted. Destruction of
unrelated external owners is never inferred from zero dependency counts.

The authentic host test prepares CityHall and Plaza using the existing exact
historical run 38994607354 capture/profile and one 1,104,239-byte GEO body, whose
SHA256 is `80e8e7530ab9d42ad98a6ddd065a0e40ba1cc1a999558241c3aebc17eb89db9a`.
It explicitly destroys the old GEO and dictionary loaders and closes their FILE
providers before creating source candidates and resolving placements. The
original whole-packet geometry digests and 21 material partitions remain intact.

| Accounted host observation | Value |
| --- | ---: |
| Streamed occurrences examined to locate both subset models | 76,192 |
| Modeled occurrences explicitly not prepared | 47,227 |
| Explicit no-model occurrences | 28,963 |
| Source geometry occurrences prepared | 2 |
| Sealed geometry owned allocation | 2,376,823 bytes |
| Exact shared source-owner tree | 37,128,632 bytes |
| Earlier old-to-sealed transition peak | 93,228,133 bytes |
| Placement query complete named aggregate | 57,403,703 bytes |
| Prior dictionary/caller allowance conservatively retained | 17,633,248 bytes |

These values are named payload/reserve accounting, **not** physical RAM, process
RSS/PSS or GPU measurements. The query allocates zero bytes, including at the
supported first-allocation fault point and across 128 repeated preparations.
Exact/one-byte-short aggregate admission, overflow, altered identities/matrices,
aliases/endpoints and equal-hash distinct actual join owners are tested. The
existing preparation dependency cancellation/allocation/late-retain rollback
controls remain in the focused composed fixture. The native query-frame closure
is measured separately at O0/O1/O2 against its charged reserve; full graph reports
are not copied onto its stack. Release, ASan and UBSan each pass **312,809**
controls with identical results. Conservative sums of every reached emitted
native frame are 5,120/4,648/4,104 bytes at O0/O1/O2, below the 16,384-byte reserve.

## Reproduce focused qualification

```sh
python3 native-android/engine/scenecatalog/prepare_source_placement.py \
  --source-root . --output /private/source-placement
python3 native-android/engine/scenecatalog/check_source_placement.py \
  --capture-directory /private/source-placement/capture \
  --body-directory /private/source-placement/bodies \
  --dictionary-source-root . \
  --dictionary-cache /private/source-placement/tricks.bin \
  --output /private/source-placement-host.json
```

The checker freezes the transitive native/include closure, pinned capture/cache
inputs and exact prior original-delta geometry receipts, then runs release, ASan
and UBSan sequentially. The preparation tool reuses the retained archive/cache
and range-acquires only this single authenticated GEO, rather than every world
asset. No server is started and no accepted APK/profile/import changes.

Host receipt: `evidence/source-placement-host.json`. Dedicated CI:
`.github/workflows/native-world-resource-integration.yml`. Android, emulator and
physical Thor execution are not claimed by the host receipt; LeakSanitizer is
disabled in this environment. This subset remains **nonrendered**: effective
CLIENT materials/UV state, lighting/LOD, GPU owners, current live GROUPS/generation,
authoritative actors and atomic world publication are unsupported. READY,
RECEIVED_CHARACTER and application full-update ACK remain prohibited.
