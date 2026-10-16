# Captured catalog memory audit

This read-only host experiment uses the retained catalog from disposable capture
run **38948147691**. Its 12,179,670 bytes independently hash to
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`.
The capture receipt remains a failed whole-job receipt because its eager native
validator hit the existing memory limit. This audit does not change that receipt
or establish a matching live GROUPS transaction, Thor generation or render permit.

`ledger.c` includes the existing catalog implementation to measure its actual
private types, runs the existing envelope preflight, and decodes/disposes one
record at a time with the unchanged existing definition decoder. It writes only
numeric aggregate observations. All **40,225 records** consumed their exact bit
length; all were in use. Observed totals are **508 files, 130,314 children and
423 swaps**. The retained header carries 33 roots; actual root records/transforms
are not part of this catalog and were not decoded here.

The source files, exact source checkout, harness and generated host binary are
hash-bound in `ledger.json`. Sizes below are allocation payloads measured on the
qualified x86_64 host, not Android RSS/PSS, allocator overhead or process limits.
No runtime, accepted APK, catalog format, memory limit or imported payload changed.

| Current eager representation | Bytes |
|---|---:|
| One definition object | 1,104 |
| One child object, including its original 48-byte matrix | 308 |
| One swap object | 516 |
| Catalog fixed minimum before any record allocation | 44,548,720 |
| All child arrays | 40,136,712 |
| All swap arrays | 218,268 |
| Copied original definition bodies | 11,329,585 |
| Complete eager catalog payload | **96,233,285** |
| Borrowed capture input, additional to eager payload | 12,179,670 |

The fixed catalog minimum is already 42.485 MiB, exceeding the unchanged 32 MiB
cap. Complete eager ownership would be 91.775 MiB before input or graph copies.
An eager graph using exact capacities would require at least 98,335,809 bytes
with file/root arrays and two definition/name indexes, before traversal scratch.
Geometric capacity growth can add further transient allocation. Increasing only
the catalog cap therefore cannot make the existing graph fit its 32 MiB cap.

The largest serialized record is 245,230 bytes. The largest one-record decoded
dynamic allocation is **1,654,842 bytes**, at file 0 / slot 5468. No record exceeds
4,575 children or nine swaps. Input + largest decoded allocation + 64 KiB stack
reserve is **13,900,048 bytes**; caller-retained state must still be added. This
supports bounded streaming validation without constructing an eager full catalog.

## Compact representation options

These are explicitly **design estimates, not implemented ABI sizes or measured
compact graph admission**. They retain exact names, matrices, original slots and
serialized metadata. They do not substitute asset resolution or drop metadata.

The observed actual string storage is 1,171,067 bytes for four definition fields,
2,256,967 bytes for child names, 14,125 bytes for swap names and 35,377 bytes for
file names, including terminators and without deduplication. Replacing the fixed
name arrays with exact-length pools removes **71,419,872 bytes** of unused string
capacity from the eager representation. Definition and child names observed in
this particular capture are at most 59 bytes; retaining existing parser limits
avoids treating that observation as a universal source constraint.

One concrete accounting model uses 64-byte definition rows with string/pool/wire
offsets, 56-byte children retaining the full 48-byte matrix, 12-byte swaps, and
24-byte file rows. It preserves the source file/slot identities. Exact copied
strings, two 131,072-slot indexes, bounded traversal scratch, stack/header
allowances and conservative 33-root allowances total **15,665,831 bytes** before
wire bodies. Adding one owned copy of every original body gives **26,995,416
bytes**. Adding the observed one-record streaming decode scratch gives a candidate
preparation estimate of **28,650,258 bytes (27.323 MiB)** before old state, borrowed
input and external resources.

Two such compact snapshots plus captured input and one-record decode scratch
are estimated at **67,825,344 bytes (64.683 MiB)** when each snapshot copies its
wire bodies. Retaining one immutable, explicitly generation-owned catalog buffer
and storing validated offsets instead gives an estimated **45,166,174 bytes
(43.074 MiB)** for two snapshots, the shared input and record scratch. The second
design needs a qualified pin/retirement contract across replacement and
incremental updates. A borrowed raw pointer without that ownership is insufficient.

Both estimates exclude real asset pins, geometry/texture payloads, source lookup
manifests/indexes, allocator metadata and other application state. Root names and
row sizes are allowances because their matching GROUPS records were not captured.
An implementation must perform checked aggregate admission before allocating,
count old/new catalog owners and all retired readers, reserve streaming scratch,
and preserve the prior snapshot on every failure. Passing this arithmetic is not
complete graph or server-world qualification.

## Reproduction

Use source files matching `ledger.json` and the retained capture; the harness
does not fetch, deploy or start any server:

```sh
cc -std=c99 -O2 -Wall -Wextra -Werror \
  -I native-android/engine/scenecatalog \
  native-android/combined-client/evidence/20261016/startup-diagnostics/catalog-memory/ledger.c \
  native-android/engine/scenegraph/coh_scenegraph.c \
  native-android/engine/replication/coh_replication.c \
  native-android/engine/replication/coh_groups.c -lm -o /tmp/catalog-memory-ledger
/tmp/catalog-memory-ledger /path/to/retained/catalog.cohcat
```

Host record decoding and numeric accounting passed. This experiment does not
claim a new sanitizer run, Android build/execution, device performance change,
real authentication, resolved geometry/materials or completed gates 25–27.
