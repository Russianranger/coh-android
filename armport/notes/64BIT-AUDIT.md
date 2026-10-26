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
| 0034 | `.geo` files: `ModelHeader` (140 bytes on disk), `PolyGrid` (32), `PackData` (12), name tables (32-bit offsets converted to pointers in place), `BoneInfo` (32-bit pointer slots), collision `PolyCell` trees (32-bit offsets) and a `(U32)` base pointer. The name table and `BoneInfo` copies are separate allocations on 64-bit; each `GeoLoadData` keeps its copies and frees them on client unload (`modelListFree`) and server unload (`restoreStubOffsets`) | model headers, names, mesh data and collision misread or truncated |
| 0036 | Entity, power, recipe and task pointers kept in the expression evaluator's int table (`eval_StoreInt`, and `eval_FetchInt(..., (int *)&ptr)` writing 4 of 8 bytes) in 6 Common files | combat, power-slot, recipe and supergroup expressions would see broken pointers |
| 0037 | StashTable removal wrote `U32_TO_PTR(STASH_TABLE_DELETED_SLOT_VALUE)`, cutting the 64-bit deleted marker to `0x00000000fffffffe` | every hash-table removal left a live entry; createbins asserted on re-registering `auto>` |
| 0039 | Pointer arrays described to the textparser as int arrays (`TOK_AUTOINTEARRAY` of `ppPowers`, `ppPowerSets`, `ppItems`, `ppDetails`, for shared-memory copies); textparser int arrays are 32-bit | createbins asserted loading the power dictionary |
| 0040 | `.geo` format version 2 model records read as a raw `ModelFormatOnDisk_v2` (216 bytes on disk, pointers) | release client crashed in `geoLoadStubs` on a garbage model name |
| 0043 | SMF text attributes keep the font face (`TTDrawContext *`) in an int stack (`smf_PushAttrib`, `smf_InitTextAttribs`); the font-height cache keyed on the first 8 bytes of {font pointer, size} | release client crashed in `ttGetFontHeight` on a font pointer cut to 32 bits; every size of a font would have shared one cached height |
| 0044 | `SOCKET` (64-bit on ARM64 Windows) passed as `int` in the receive path: `pktGetUdp`, `netAddLink`, the `accept` result | none seen (Winsock handles are small, and `-1` still compares equal to `INVALID_SOCKET` after widening); fixed so no handle value depends on that |

All file-layout constants above were checked against the 32-bit structures by
compiling them for i686 with static assertions (sizes and field offsets).

## Not 64-bit, found on the way

| Patch | Problem | Effect before the fix |
|---|---|---|
| 0042 | Production clients read `scenes/`, `ent_types/`, `object_library/`, `geobin/` only from piggs; CI has loose data (`ARMPORT_LOOSE_DATA`) | scene load failed |
| 0045 | The fake-auth DbServer honours the client's no-version-check flag; the Release client can only set it with a level-9 command (`ARMPORT_NO_VERSION_CHECK`) | DbServer answered the login with WrongVersion |
| 0047 | `groupFileRecalcBounds` and the tree check in `groupDefFree` did not skip empty def slots (members that failed to load; the 32-bit MapServer logs the same "can't find member" on this data), unlike `groupRecalcAllBounds` | client crashed loading Atlas Park's world groups |

## Known, not fixed yet

Patch 0050 changes ARM64 llvm-mingw worker queue indices, sleep flag and thread
state to sequentially consistent atomic loads/stores and publishes the event
before THREAD_RUNNING. The original negative control misses a wake; the patched
case dispatches it, and both wrap 4096 commands/replies in run 40035482170,
libraries job 120693769990. See WORKER-QUEUE.md for the remaining x86 ordering
limitation and why this is not an established Atlas stall fix.

Patches 0048 (zone progress) and 0049 (texture queue progress) are diagnostics
only, like 0046: inert unless ARMPORT_STDIO_LOG is set; no gameplay, queue order
or timeout changes. They are retained to diagnose original loading failures.

- `libs/UtilitiesLib/src/utils/DirMonitor.c:338`: completion key narrowed to
  U32 (development-mode file watching only).

Reviewed and safe: the network library otherwise keeps `SOCKET` in `SOCKET`
fields (`net_structdefs.h`); its other narrowings (`rsa.c`, `bignum.c`) store
`strlen` results and pointer differences of short key strings in `int`. `net_masterlist.c` completion keys (32-bit indices),
byte counts from `fread`/`fileSize`, textparser `intptr_t` parameters that
hold integers, window ids passed through `void *` in the UI.


0052: diagnostic CRT stream correction. file.h's fprintf macro takes a
FileWrapper*, so passing CRT stderr from armport_zone_trace.h was invalid.
The header now temporarily restores the CRT function and preserves caller
macros. A negative/positive compile control and ARM64 Wine regression cover
the tex.c include order. Evidence: notes/M3-LOAD-STALL.md, run 40035482170.


0053–0055: i686 replay-reference build opt-ins, not additional ARM64 pointer
fixes. They select matching reduced SDKs, fail rather than recover local SEH
in the reference, and use clang vector-lane syntax. The original receiver is
compiled unchanged. See M3-REPLAY-PLAN.md for compile evidence and exclusions.

0056: opt-in original-receiver replay entry, not a pointer or decoder fix.
The normal network callback retains statistics and dispatches through the
same original switch; replay enters below transport statistics after normal
startup. Extra receive/output initialization is listed in the patch's new
header. No upstream file is modified. See replay/README.md: initial scope
is cursor/ACK execution and deliberately cannot claim state equivalence.

0057: bounded swap/model and error-dialog progress diagnostics. No pointer
fix or loading behavior change; follows the post-drain stop reproduced in
40042636088 and 40043254025. ARM64/i686 OptDebug Game links pass locally.


0062: initialize costumeVerifyTextures' entire dummy Appearance. Its optional
costumeFilePrefix was read uninitialized in determineTextureNames. Run
40097455262 has equal complete error counts on both targets but case-only
spelling differences; run 40099922039 tests this correction. This is a shared
source bug exposed by architecture-dependent stack contents, not an allowance
for ARM64-only errors. No acceptance normalization is added.

0063: collision-grid node storage and lookup must preserve pointer width.
Run 40094942248's exact Release executable resolves 0x1400a4da4 to
groupGridActivate (groupgrid.c:96:14), reading def+0x88 through a truncated
tracker. GridEnts.entries, GridIdxList entry pointers, insertion temporaries,
checkGridCellObjs and processGridEntries now use uintptr_t. The latter's int
temporary could classify a high pointer as a small numeric ID. The group tag
is still bit 0; IDs below 100000 still use the original numeric tag table.
Host command `python3 armport/tests/grid_pointers.py --source
../patchwork-active/src --expect-full-width 1` returns storage=1, sphere=1,
collision=1, distinct=1. The same command with upstream/ouroboros and expected
0 returns all four as 0. Both generated ARM64 Windows controls compile.
The test adapts allocators/unrelated geometry but executes the original grid
function bodies; high tokens are never dereferenced. Wine/Atlas CI is required.


0071: modelCreateCtris allocated an expanded ARM64 PolyCell grid but placed
triangles at the original disk byte count, overwriting native pointers and
retained indices. Use uiGridAllocSize, matching the shared-heap path. Replay
40128377861 and Atlas 40128377899 both fault in objSplitPlanes; the exact
symbols, operands, allocation controls and both target compiles are recorded
in ../evidence/m3-review12-grid-and-runtime-40128377861.json. Runtime repair
still requires new CI; i686's computed grid extent remains the raw size.

0072 caches the existing power trace opt-in. 0073 is an inert-unless-enabled
selected-power diagnostic at M4's actual caller; no pointer filtering or game
logic repair. Exact M4 40127841088 symbols and command outputs are in the same
evidence JSON. It is not a power-pointer fix or milestone qualification.
