# Independent normal GROUPS structural review

Reviewed clean integration commit:
`127ce7292297aebb55b3b1dbeb59000a1cab91dc`, tree
`93390b9fb6f765e4b864669eac66995e56c1f955`.
`review-binding.json` records the exact reviewed file hashes and independent
probe bindings; later documentation commits do not change that source claim.

This review covers the bounded normal-world wire traversal and its additive
Map/JNI/report integration. It does not qualify imported asset resolution,
checksums against an imported graph, authoritative transforms, entities,
authentication, a live world or physical acceptance of 0.1.7.

The pinned producer and matching original consumer were independently read.
Their normalized hashes match `engine/replication/source-pins.json`:

| Source | SHA256 of normalized LF bytes |
|---|---|
| `MapServer/src/group/groupnetsend.c` | `cd739e2a1b424bf089017be73d3c42adef0f23aca7563e8577cfc98ecdfebff9` |
| `Game/src/group/groupnetrecv.c` | `f4cccb5a51acea3448191965470eaa349034c4f6fa1c729fa52aed0888c7004d` |

The normal grammar matches both ends: optional floats, eight-byte light and fog
colors, bit32 property counts, two property types, raw affine matrices, packed
matrix flags and half-integer components, deletion records and both sentinels.
Child names can refer forward. Saved library definitions can be omitted even
from a full update. File slots arrive in implicit order 1 through N-1, then 0.
Footer file count is not a definition count, and active roots are not the count
of records in an incremental update. Checksums are observed numeric fields.

Source ascending definition IDs are justified by `groupDefNew`,
`groupDefPtrFromFuture`, `groupAssignToFile`, `groupSwapDefs` and `groupDefDup` in
`Common/group/group.c`, which maintain `file->defs[id]` identity. The producer
loops file slots in ascending order. Root indices likewise come from its
ascending loop, while remaining sparse identities. The native inspector does
not retain or resolve a name graph, so it does not claim to detect name aliases,
cycles or missing imported definitions. Team-area values 5 through 7 are
uninterpreted structural metadata and grant no team semantics.

The parser has bounded scalar work, strings and aggregate records, no recursive
traversal and no allocation. Its borrowed input remains owned by the synchronous
Map receive call. Both cursor and inspection output roll back on failure. The
numeric failure checkpoint is the last completed read boundary; PREFIX uses the
existing transactional prefix parser and therefore reports its starting
boundary on failure, rather than an individual malformed prefix field.

The separate adversarial probe checks both scalar profiles, every-bit
truncation of four small complete fixtures, extreme/signed IDs, sparse roots,
duplicate/decreasing IDs, counts, texture masks, nonfinite matrices, property
name/value boundaries, exact end and output rollback. It is an independently
written synthetic input generator, not another original-producer oracle.
`independent-probe.json` records release, ASan and UBSan results, exact native
source hashes, allocation wrappers, undefined symbols and compiler stack usage.
The largest emitted native frame is a per-function measurement, not a measured
total process stack or device memory result.

The corrected original-producer oracle was independently reexecuted from this
integration tree: 41 exact helper/producer bodies from 16 pinned files generate
44 fixtures. Its receipt matches the committed source receipt. Compression
mode transitions now execute the unchanged original setters; packed cases use
incremental updates and byte-aligned cases use full updates or an explicit
aligned factory default. Command-number and checksum-primitive adapters are
explicit. This is controlled source execution, not a complete original server
or client. `repeated-source-oracle.json` records that repeat. The broad decoder
worker sanitizer receipt is referenced by hash in `review-binding.json`; its
test counts are not represented as another independent review run.

`jni_probe.py` extracts the exact current report and phase functions without body
edits and executes them against a host-only `NewStringUTF` capture shim. Strict
format checking, all 23 inspection field mappings, three failure fields and the
maximum scalar serialization size are recorded in `jni-probe.json`. Actual
Android JNI execution is qualified separately by the emulator driver.

The Map path was independently reviewed for synchronous owned-view release on
every inspection outcome, preserved last-complete inspection on later failure,
new-session clearing, unchanged selected-identity guards and absence of
REQALLENTS/READY/full-update acknowledgement/spawn publication. The UI adds only
structural progress/failure text. Return to launcher is unchanged.

Public `server_identity_bound` describes the DbServer session binding. It is
not proof of a selected character DB ID or an AuthServer login. The Android
qualification contract must preserve this distinction. Comparing fixture footer
integers to expected source-produced footer integers tests serialization only;
it is not verification of the imported asset graph's CRC.

Reproduce from the integrated source tree:

```sh
python3 native-android/combined-client/evidence/20261016/full-scene-0.1.7/review/independent_probe.py --source-root "$PWD" --output /tmp/coh-groups-review.json
python3 native-android/combined-client/evidence/20261016/full-scene-0.1.7/review/jni_probe.py --source-root "$PWD" --output /tmp/coh-groups-jni-review.json
```
