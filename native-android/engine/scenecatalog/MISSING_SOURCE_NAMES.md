# Seven unresolved names: original source requirements

The seven recorded missing edges are not spelling guesses or names needing
underscores removed. They are explicit original `Group` references with matching
empty `RootMod` declarations. None has a `Def`/`Obj` binding in the corresponding
retained `.rootnames` file. The pinned source audit records file SHA256 values,
declaration lines and independent executable source controls.

| Catalog file | Parent slot | Child | Missing name |
|---:|---:|---:|---|
| 110 | 61 | 1 | `_cot_warpgate_base` |
| 110 | 61 | 2 | `_cot_warpgate_glow` |
| 376 | 32 | 1 | `_mmayhem_curtain_8_01c` |
| 376 | 33 | 1 | `_mmayhem_curtain_8_02c` |
| 376 | 34 | 1 | `_mmayhem_curtain_8_03c` |
| 376 | 35 | 1 | `_mmayhem_curtain_16_01c` |
| 376 | 36 | 1 | `_mmayhem_curtain_16_02c` |

The first pair comes from
`upstream/i24/data/object_library/Villain_Lairs/cot/elements/magicrunes/magicrunes.txt`.
The others come from
`upstream/i24/data/object_library/Villain_Lairs/unique/mother_mayhem/mmayhem_details/mmayhem_details.txt`.
Their corresponding `.rootnames` files provide other model definitions but omit
all seven names. Original `groupLoadInternal` reads `.rootnames` and then text,
or the corresponding valid binary cache. `addDef` immediately refuses a record
with no children and no object/model name, so an empty `RootMod` is not a complete
saved definition. Copying those declarations into a native graph would not
reproduce original definition admission.

Original `addGroups` attempts name lookup/library load and then calls
`groupDefFuture` when unresolved. `groupDefFuture` uses the separate
`group_info.pre_alloc` file. Unchanged `groupDefNew` explicitly does not append a
preallocated definition to normal `file->defs` or increment its slot count. The
nonshipping catalog exporter traverses only `group_info.files[0..file_count)`.
The original client `receiveDef` similarly creates a future name when necessary.
`groupDefFind` strips the final `/` prefix; this does not turn any of these seven
already bare names into a saved definition.

The source audit executes unchanged whole `groupDefNew` and `groupDefFuture`
functions in bounded fixture memory/hash/bounds shims, plus the exact original
early-return guard from `addDef`. Each release/ASan/UBSan mode passes 31 checks:
empty/nonempty/object guard combinations, seven future names outside regular
slots, and a regular-definition control. It does not execute the full loader,
read actual captured `pre_alloc` objects or qualify geometry/bounds behavior.

This explains a concrete way that an authentic saved-file catalog can contain
child names absent from its saved-file definitions. It is an inference about
the captured runtime, not a claim that its exact future objects were exported.
The separate compact audit verifies every authentic edge and retains all seven
missing identities without publishing placeholders. None is currently proven
reachable or unreachable from the Atlas roots.

Remaining inputs are precise:

1. The matching original GROUPS root slots, names and matrices, tied to the
   source/catalog/runtime generation, to establish reachable closure and
   recompute the original reference CRC.
2. Exact loaded object-library/rootname/binary-cache and model/GEO inventory
   identities if a missing name is expected to become a real loaded definition.
3. If a reachable reference is intentionally an unresolved original future,
   a separately source-qualified explicit nonrenderable-future representation
   and lifetime semantics. This tranche does not implement or admit that policy.

The existing catalog is intact and useful; these findings do not justify another
expensive MapServer startup merely to export the same saved files again.

## Captured runtime resolution (run 38977202310)

The retained successful sidecar now provides the missing original ownership
observation. All seven names are separately observed `pre_alloc` definitions;
each has original ID zero, no model, no library path and a failed object-library
bounds lookup. `_mmayhem_curtain_8_01c` alone is reachable from the 33 roots.
The other six are not root reachable in this captured source generation. Their
regular parent slots and links remain preserved; none was deleted or converted
into a renderable placeholder. Exact catalog SHA256 remains
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`;
sidecar SHA256 is
`c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02`.

The native audit validates all 33 root matrices, both original CRCs and full
name closure. The root closure has 15,352 regular definitions, one external,
57,710 edges and maximum depth 69. These facts supersede the historical missing
ownership/reachability statements above, within this source snapshot only.
They do not establish a matching live GROUPS transaction, asset inventory
admission, model/GEO/material resolution or physical Thor world authority.

`coh_catalog_snapshot.[ch]` adds a preparation-only immutable owner: exact catalog
owner/source/asset/map binding, copied byte pin, run digest, bounded diagnostic
closure and retained catalog lifetime. Its capture receipts must be independently
admitted before use. A caller-provided nonzero receipt label is never independent
proof. This module is not in production CMake and does not enable completion ACKs
or rendering. Its test driver reuses the existing test-only matrix bridge.
