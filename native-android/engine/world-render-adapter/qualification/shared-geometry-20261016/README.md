# Shared geometry qualification

Implementation: `a6be4cc20e2686453e5bbbe7c0d3a168becfa813`.

Clean source before/after; exact unchanged source hashes in `host.json`.
Release, ASan and UBSan each pass **29,148 checks** with identical native results.
The unchanged original source `mulMat44Inline` is executed for 512 comparisons.

New coverage includes distinct-ID hash collision handling, byte-equal separate
spans, conflicting vertex/index/count identity rejection, source mutation after
copy, both allocation failures, cancelled comparison/copy rollback, an exact
scratch-plus-candidate budget boundary, and 4,096 draws sharing a maximum-size
mesh. Prior mailbox/generation/Surface/retirement/concurrent-reader controls run
unchanged. No allocations or frees occur during all 4,096 adapter draw lookups.

Measured named ownership for the explicitly synthetic shared-mesh fixture:

| Quantity | Bytes |
|---|---:|
| Unique geometry | 4,456,448 |
| Snapshot with 4,096 descriptors | 5,964,128 |
| Preparation scratch | 49,152 |
| External reservation, including exact input buffers | 39,518,208 |
| Maximum aggregate, including bindings | 45,580,768 |
| Calculated old per-instance geometry payload | 18,253,611,008 |

The instance workload is still 268,435,456 vertices and 805,306,368 indices.
Only adapter spans were produced for this large fixture, not renderer submissions
or GPU draws. The capacity result is not a live-world/FPS claim. Separate accepted
renderer submission/flush tests execute only their bounded original fixtures.

The old worker's three owned implementation/test files match recovery base
`66146bbee` exactly; `recovery.json` preserves hashes. Its linked Git common directory
was unavailable, so byte comparison establishes source recovery, not recovered
unpublished commit history. Baseline Android evidence stays valid for baseline
bytes. New Android ARM64/x86_64 build and Android13 execution remain coordinator
CI gates; no local NDK exists. Physical Thor acceptance and authentic world entry
remain false. ASan/UBSan are qualified; LSan execution is not claimed.
