# 64-bit (LLP64) audit

The client was written for 32-bit Windows. On ARM64 Windows pointers and
handles are 64 bits while `int` and `long` stay 32 bits, so any pointer or
handle kept in an `int`/`long`, or any file structure that contains a pointer,
breaks.

## No address-space safety net under the app's Wine

`armport/tests/src/address_space_test.c`, run in CI under the app's Wine 10
(job `libraries`, run 39715218375): with and without the large-address-aware
flag, the CRT heap, HeapAlloc, VirtualAlloc and the stack are all near
`0x7ffffe000000`, and the image loads at `0x140000000`. Wine does not keep a
non-large-address-aware 64-bit program below 2 GB, so truncated pointers are
never safe; they have to be fixed.

## How to list candidates

```sh
python3 armport/scripts/prepare.py --out /tmp/w64
python3 armport/survey/survey.py --toolchain /tmp/tc --structparser /tmp/sp/StructParser \
    --target win-arm64 --work /tmp/w64 --patched --warn64 --warn-width --out w64.json
```

At patch 0031 (UtilitiesLib, Common and Game): 236 int-to-pointer casts,
162 pointer-to-int casts, 128 pointer-sized integers narrowed to 32 bits.
Most int-to-pointer and pointer-to-int casts carry small integers through a
`void *` (window ids, font scales) and are safe. The narrowings are where
handles get cut.

## Fixed

| Patch | Problem | Effect before the fix |
|---|---|---|
| 0030 | `DDSURFACEDESC2` (DDS file header) held a pointer, 136 bytes instead of 124 | every DDS texture failed to decode |
| 0031 | `_findfirst32` handles (`intptr_t`) kept in `int`/`long` in UtilitiesLib | directory scans found nothing; createbins could not see `sequencers/*.statebits` |
| 0032 | `MainWndProc`/`DefWindowProc_timed` returned `LONG` | `LRESULT` values above 32 bits (handles) truncated |
| 0033 | `.anim` files are 32-bit memory images (`SkeletonAnimTrack` 596 bytes, `BoneAnimTrack` 20, pointers as 32-bit offsets) | every field after the first pointer misread; createbins asserted in `animtrack.c` (no skeleton hierarchy) |
| 0034 | `.geo` files: `ModelHeader` (140 bytes on disk), `PolyGrid` (32), `PackData` (12), name tables (32-bit offsets converted to pointers in place), `BoneInfo` (32-bit pointer slots), collision `PolyCell` trees (32-bit offsets) and a `(U32)` base pointer | model headers, names, mesh data and collision misread or truncated |
| 0036 | Entity, power, recipe and task pointers kept in the expression evaluator's int table (`eval_StoreInt`, and `eval_FetchInt(..., (int *)&ptr)` writing 4 of 8 bytes) in 6 Common files | combat, power-slot, recipe and supergroup expressions would see broken pointers |
| 0037 | StashTable removal wrote `U32_TO_PTR(STASH_TABLE_DELETED_SLOT_VALUE)`, cutting the 64-bit deleted marker to `0x00000000fffffffe` | every hash-table removal left a live entry; createbins asserted on re-registering `auto>` |
| 0039 | Pointer arrays described to the textparser as int arrays (`TOK_AUTOINTEARRAY` of `ppPowers`, `ppPowerSets`, `ppItems`, `ppDetails`, for shared-memory copies); textparser int arrays are 32-bit | createbins asserted loading the power dictionary |

## Known, not fixed yet

- `libs/UtilitiesLib/src/utils/DirMonitor.c:338`: completion key narrowed to
  U32 (development-mode file watching only).
- `libs/UtilitiesLib/src/network/*`: `SOCKET` values kept in `int`. Socket
  handles are small numbers under Wine; revisit if networking misbehaves.

Reviewed and safe: `net_masterlist.c` completion keys (32-bit indices),
byte counts from `fread`/`fileSize`, textparser `intptr_t` parameters that
hold integers, window ids passed through `void *` in the UI.
