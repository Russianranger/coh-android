# Current named-owner overlap correction

This audit compiles an actual C object containing the current owner definitions,
then checks every size **and alignment** against C++ public declarations and
verbatim extracted private declarations. It does not execute module preparation,
an old qualifier, a capture, a renderer or a provider. The receipt binds the audit
script, generated C/C++ source hashes, compiler versions, current include closure
and eight preserved receipts. Host layout is not an Android ABI or RSS result.

Run only this new inspection, from the integrated checkout:

```sh
python3 native-android/combined-client/diagnostics/continuation-f-20261017/latest-owner-overlap/qualify.py \
  --source-root . --output "$RUNNER_TEMP/latest-owner-overlap.json"
```

The local receipt's additional, disjoint B/C owners are:

| Owner | Bytes |
| --- | ---: |
| Raw LOD cache metadata | 139,424 |
| LOD dictionary retaining that cache | 1,373,496 |
| Borrowed power-stream dictionary metadata | 1,048,744 |
| Complete power join | 524,344 |
| Sorted power-ID view | 689,184 |
| Shared-set layout | 32,792 |
| **Additional named total** | **3,807,984** |

The power-stream dictionary is necessary transitively, although its source
predates the new join. It was absent from the old 6,827,548-byte dictionary
comparison. Its file-backed power input is not silently billed as a retained
62 MiB heap span; the actual file/provider/context/scratch and any mapping still
need their own charges. Join, ID and shared-set workspaces add 524,344, 689,184
and 32,792 bytes during their respective calls. An append also retains its prior
32,792-byte shared-set owner until successful disjoint copying and actual caller
release. Workspaces may retire after return only through actual caller cleanup.

The old/candidate reference of 100,074,681 bytes plus these named owners is
**103,882,665**, exceeding the 100,663,296-byte cap by **3,219,369** before new
workspace, loader/provider, actor, material or GPU charges. The historical
post-cleanup/all-old-dictionaries-and-sets reference becomes 71,169,215 bytes.
That latter arithmetic grants no current fit or retirement credit. Four old
sealed-receipt source files differ from the current checkout; their exact
historical/current hashes are retained explicitly. Those old world quantities
remain comparison references, rather than a new measurement of current code.

B's model policy has no retained heap owner; one retained caller result is
2,088 bytes, plus its borrowed inputs and 4 KiB control reservation. New optional
Trick-selection/schedules/boost-slot public headers, when present in the supplied
checkout, are included automatically in C/C++ layout inspection and the named
schedule/slot-owner proposal. Their new qualifier receipts must still establish
behavior independently; this script does not qualify them. Its checked-in local
receipt predates those not-yet-integrated headers.

E adds a shared budget/presentation/mailbox total of 288 bytes. Each prepared
bundle adds 80 bytes plus a 168-byte frame, 56-byte bindings, eight bytes per
selected index and 26 bytes per snapshot draw. All allocations use the same
adapter aggregate; another 96 MiB budget is not created as additional capacity.
An immutable snapshot adds 352 bytes plus 368 per draw and copied unique
geometry bytes. Identical camera publications can share a snapshot. A different
snapshot retains old and candidate geometry simultaneously until real retirement.

The source fixture's 2,376,823-byte sealed owner contains canonical shared vertex
storage. Its 21,771,948-byte `packet_bytes` measurement covers **the first bar
mesh's 12 partitions**, not both meshes' complete payload. E's straightforward
one-identity-per-part adaptation copies each complete distinct geometry/index
span; it does not retain the canonical source vertex sharing across partitions.
The conditional 21-descriptor example therefore uses that known bar payload,
omits the second mesh's payload and the mandatory selected actor, and remains
unexecuted. One snapshot/bundle/result proposal totals 92,952,637 bytes; two
totals 114,733,683. These are conditional named-overlap comparisons, not evidence
that a valid source consumer can currently be constructed or that another
source-selected geometry representation would have identical costs.

The concrete next retirement boundary is **after successful `coh_wr_prepare`
return**, when every selected descriptor and unique geometry byte has been
copied and rebased into the immutable snapshot. Only then, after every separate
material/source borrower is transferred or released, may the actual
`coh_source_sealed_free` release canonical geometry and its Selection lease.
The copied candidate and original source must coexist throughout validation and
copying. Current scene graph/catalog state needed for later GROUPS deltas cannot
be discarded just because presentation owns copied draw data.

The actual existing deferred callback is
`coh_wr_presentation_collect -> resources.drop`, followed by real bindings/frame
destruction and final snapshot collection. Its production bridge must own a real
resource lease, release the actual remaining B pins/owners, then perform actual
`coh_asset_trim`, successful loader destruction and provider/FILE close before
reducing an external reservation. Current callbacks prove the adapter lifetime
with fixture providers; no production source/GPU provider is wired here. The
older sealed-source fixture explicitly performs loader/provider destruction;
that fixture result is not a current application cleanup event. No arithmetic
subtraction is taken as retirement in this audit.

A's new graphical/PostgreSQL/MapServer capture helpers execute on separate host
and server processes, so their disk dump limit and server-capture envelope are
not new resident Combined-client owners under this cap. Their output still does
not close current scene, material or character authority. No common parent/module
adapter currently books every owner together. Literal standalone child caps do
not automatically become parent tickets; passing zero retained bytes would not
establish aggregate admission. No Android, RSS, peak-disk, startup or frame-pacing
improvement follows from these comparisons.
