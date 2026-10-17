# Source GEO headers with zero-draw model identities

The authenticated Shop_tailor v8 body contains 72 original disk rows. Four rows
(`LlegR`, `FootR`, `LlegL`, `FootL`, disk rows 34–37) have zero vertex, triangle
and material counts. They are explicit captured Model owners and are unreachable
from the current roots. Their finite point bounds and scale remain meaningful
source metadata. GRID and reduction packs are nonempty; these records are not
blank data and are never removed or rewritten.

The accepted protected GEO reader rejects an entire file containing such rows.
The additive `coh_resource_geo_source` adapter leaves that reader unchanged. It
tries the protected reader first. Its narrow v8 fallback validates every original
row, table/name/record/payload extent and material identity. Every ordinary model
is delegated to the protected model reader. A zero-draw row must have all three
draw counts zero, no reflection quads or bone-info pointer, empty mesh/reflection
streams, finite scale and finite ordered bounds. GRID and reduction metadata
packs retain their exact offsets and byte counts with bounded payload spans.
Those packs are not implicitly decoded, executed or declared valid collision or
LOD resources. Empty texture-name tables remain unsupported; no default texture
is synthesized.

No file projection, row deletion or reordering occurs. Source queries keep the
exact full name, source sorted runtime bucket/row and original disk row. The
resource view marks `zero_draw_model`; its material lookup returns NOT_FOUND and
leaves output unchanged. It provides no mesh or draw permit. The index retains
the complete blob and header workspace through all borrowed views. Preparation
walks each original disk row with a cursor, avoiding a hidden quadratic ordinal
lookup inside each model-name scan. Existing work/cancellation and aggregate
reservations remain in force.

The qualification compiles the unchanged original `readModel` body from
`Common/seq/anim.c`, with explicit 32-bit disk `PolyGrid`/`PackData` layout shells,
and compares all 72 actual records' names, counts, scale, offsets and ten packs.
It is a host v8 field-copy oracle; it does not claim original Win32 ABI or v2
execution. Original pointer-signedness warnings are isolated to that unchanged
oracle. Release, ASan and UBSan each pass 3,475 source and malformed-input
controls, including all ordinary-row validation, nonempty forbidden mesh packs,
zero-count combinations, metadata span errors and transactional refusal.

All 391 recovered root-required GEO files now pass source core-header/model and
material-partition comparison in all three host modes. This compares 8,250
captured model-owner observations for those files, including four zero-draw
owners. It does not decode every vertex/index stream or close CLIENT materials,
tricks, lighting, animation, LOD, runtime opened-file generation, world or actor
publication. Previous 388/390-file receipts and their precise refusals remain
retained as historical evidence.

The alias-hardening follow-up checks known source/workspace/output/counter spans
and overflow-safe endpoints before calling the protected reader. Model queries
also refuse overlapping output/control/source spans. Its final frozen source
passes 3,492 controls per host mode, including every open-span pair, overflowing
input/workspace endpoints and model-output aliases. The earlier 391-body receipt
remains explicitly bound to its pre-guard source; the guard does not change valid
disjoint-input parsing or body comparisons.
