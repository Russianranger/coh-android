# Bounded client FolderCache constructor candidate — 0.13.37 research

This is a **nonshipping native candidate**, based on the retained Game source
recipe at repository commit `3570430cefdb15d9b239563e85cccf4d8fe6f32e`.
It has not run as an actual Game, on Wine or on the AYN Thor. It does not
authorize an APK publication or assert a sub-one-minute client startup.

## Why this stage

The 0.13.36 physical reports show texture headers taking 39.542 seconds and
38.494 seconds while the existing texture-header index supplies all 38,986
records with zero ordinary header reads. `texScanForTexHeaders` still calls
`fileScanAllDataDirs("texture_library", ...)`, which constructs the ordinary
FolderCache tree before visiting the binds. Texture composites, material tricks
and bind setup also lie inside that interval. No nested native timing currently
isolates their individual contributions.

`FolderCacheAddFolderToNode` enumerates one directory using the stock
`fwFindFirstFile` / `fwFindNextFile` APIs, then inserts each entry using
`FolderNodeAdd`. That function stores siblings in case-insensitive sorted linked
lists, with a fast append path only for an entry beyond the current tail.
Unsorted incoming names can therefore require quadratic string comparisons.

The original `upstream/i24/data` inventory provides this reproducible **host
enumeration-order model**, not a Windows/Thor observation or time forecast:

| Tree | Source files | Directories including root | Largest sibling count | Modeled stock comparisons | Ascending insertion comparisons |
|---|---:|---:|---:|---:|---:|
| `scripts.loc` | 52,149 | 338 | 6,852 | 28,999,937 | 52,148 |
| `fx` | 61,854 | 1,720 | 1,041 | 2,542,182 | 61,853 |
| `object_library` | 4,694 | 2,951 | 92 | 19,423 | 4,693 |

The physical second report has a 17.417-second interval between the initial
`SCRIPTS.LOC` metadata request for `npcs_client.bin` and the next items-loading
message. It contains the entire NPC preload; the model does not prove that all
17.417 seconds are insertion CPU time. Client FX loading takes 34.756 seconds
in the same report; ordinary tree construction, BIN freshness, decoding and
validation remain separately unmeasured within that interval.

Actual Assets 1.0.0 texture sibling counts are not available in this checkout.
The `.geo` and texture closure in the device is also larger than the source-only
table above. The candidate must be measured using the complete original assets.

## Candidate and preserved behavior

Only the disposable staged `FolderCache.c` changes. Its existing per-entry body
is extracted literally into one helper; `continue` becomes the equivalent
one-entry `return`. `FolderCacheNode.c` and `FolderNodeAdd` remain byte exact.
All provider priority, PIG selection, directional DST timestamp handling,
metadata attributes, ignore/exclusion logic and linked-list operations remain
the native operations.

`COH_CLIENT_FOLDER_METADATA_SORT=1` admits a bounded constructor batch only
for the stock global `folder_cache`, when both sibling head and tail are null
and `fc->nodeCreateCallback` is null. The default stays disabled. The batch
stores metadata from the one existing directory enumeration, sorts entry names
using the same native `stricmp`, and then executes the ordinary constructor
body for every entry. The final native sibling order is already sorted in the
control path, so subsequent traversal has the same order.

The native provider loop and child recursion are retained. Temporary metadata
is freed before child enumeration. Its maximum is 16,384 rows for one directory;
the portable fixture observes a 324-byte row, or 5,308,416 bytes (5.06 MiB) of
retained batch payload. During the final `realloc` growth, the old and new
payloads may overlap up to 7,962,624 bytes (7.59 MiB), plus allocator overhead.
This is not an absolute process memory bound. The actual Win32 ABI and peak
process memory must be measured independently. This is temporary memory,
not a persistent cache or an animation/texture payload preload.

When allocation fails or the entry limit is reached, buffered metadata is
flushed in its original arrival order, the current entry is processed normally,
and the existing enumeration continues. It is never restarted. Case-insensitive
aliases restore the original ordinals before native construction. An existing
node-create callback bypasses collection altogether, retaining exact callback
chronology. These fallbacks preserve the character/database boundary: this code
has no SQL or character access.

The constructor admits only an empty sibling list. A controlled 4,096-file
fixture found that sorting with a later PIG tail could double insertion work;
populated PIG and earlier-GDD lists therefore retain the ordinary constructor.
A complete Game comparison must report actual provider counts and separate
enumeration, insertion, decode and downstream bind costs. Native diagnostic rows
include `arrival_inversions` to show whether the actual filesystem order has
anything for this stage to optimize. Already ascending enumeration may gain
nothing and still incurs sorting work.

A pinned closed-source audit scans 4,880 retained C/C++ source/header files and
finds no assignment to `nodeCreateCallback`. The stock global cache owner calls
`FolderCacheCreate`, which clears the structure using `calloc`. The audit binds
the factory, owner file and all callback-reference sources. Generic runtime
callback transitions or arbitrary memory mutations are not qualified by this
candidate. A new source assignment fails candidate source admission.

## Executed host gates

`host-evidence.json` records **9 focused host tests** and **398 executed cases**
in an actual extracted-C fixture. The fixture uses the complete original
`FolderNodeAdd`, complete original and patched constructors, native per-entry
body and candidate header. Enumeration metadata and allocation failures are
controlled fixtures; Linux Windows types are explicitly adapters.

The cases cover 64 randomized traces, three provider generations, PIG/DST
selection, file attributes, nested and empty directories, case aliases,
callback chronology, exact environment admission, allocation failures on the
first and second batch allocation, and the 16,384-entry limit. All node names,
metadata, `seen_in_fs`, file indexes, parent/previous/next/tail links, traversal
membership, native constructor counters and enumeration counts compare exactly.
Fallbacks additionally compare the root per-entry constructor arrival trace.
The fixture asserts that no parent metadata batch survives into recursion.

An independently staged full retained source recipe passed the immutable
5,995-file / 173,081,714-byte snapshot verification and all 43 retained
source/schema/callsite pins after the one explicit constructor override.
Historical receipts were not rewritten. This was source qualification only,
without a native Game build.

Run host tests:

```text
python -m unittest discover -s tools -p test_native_client_folder_sort_source.py -v
```

Run the actual Win32 fixture from a Windows compiler environment:

```text
python tools/test_native_client_folder_sort_source.py --windows-qualify --output folder-sort-win32.json
```

Stage after the complete retained Game recipe, then package using
`validate_staged_source()` so the one new constructor path is authenticated while
all earlier source/receipt/schema pins remain exact:

```text
python tools/prepare_native_client_folder_sort_source.py --source-staging <disposable-retained-game-source>
```

## Required next gates

1. Actual Win32 fixture execution and Game build with the retained imports,
   renderer, Cg, gameplay and startup observers.
2. Complete Assets 1.0.0 cold/warm Game comparisons, including metadata-batch
   activation rows and independent GPU/renderer/login readiness.
3. Exact native texture bind, trick, FX, group and other definition counts and
   identities, plus stock BIN freshness decisions and fallback evidence.
4. Native Atlas/Kings character entry, movement and zoning behavior, save/report
   reliability and controlled temporary/peak memory observations.
5. Physical AYN Thor qualification before any claimed device speed improvement.

No texture, shader, FX, asset validation, cache freshness or driver operation is
bypassed by this stage. The full CLIENT FX catalog remains required.
