# Two-model historical CLIENT request inventory

`coh_source_material_plan` adds an exact-key inventory join between an existing
sealed SOURCE geometry partition and an existing immutable historical CLIENT
TexOpt table-owner record. It does not alter placement, renderer, APK, offline
preview, source geometry or the previously qualified CLIENT policy modules.
Deleting the additive files rolls this tranche back; no data migration occurs.

The actual CityHall/Plaza source owners produce 21 partition plans and 14 unique
TexOpt owner records. Those records contain 37 distinct raw postprocessed layer
strings, including source-defined sentinel/default requests. A string such as
`none`, `white` or `black` is retained as an observation, never treated as a
resolved texture identity. Every layer's null/present-empty distinction and
original slot ordering survive. Enabled fallback base/blend/bump names occupy
slots 13–15 after original slots 0–12. The plan copies keys, source file/age,
source flags/blend, cache identity, table ordinal and geometry source identities;
it holds no pointers or leases. The fixture prints and verifies those copies
after actually releasing each record and the cache, Surface, loader and FILE.

Only a positive ASCII case-insensitive **exact** key association is supported.
The existing independently qualified cache lookup chooses the highest-ordinal
original table owner; a different record refuses. No extension trimming, alias,
composite/default lookup, texture swap, search order or absent-table conclusion
is supplied by this module. CLIENT label 17 and SOURCE asset generation 20261016
remain separately recorded historical identities and are never joined into a
current world generation. The exact full cache SHA, original source provenance
and already qualified postprocess/lookup code are readmitted before and after
the focused test; their old suites are not replayed or relabeled as new proof.

Before examining parts/keys, the query reserves actual sealed allocation,
its actual shared source-owner tree, actual immutable record allocation, budget,
output and a 32 KiB native call reserve under the unchanged 96 MiB ceiling.
Caller `retained_bytes` separately covers old and candidate resources, live
cache/Surface/loader/provider owners, borrowed controls, scratch, GPU/upload
resources and allocator/compiler/runtime peaks. The real test derives its live
cache/Surface/loader charges from those owners, reserves its copied-plan array
and caller frame/provider allowance, and refuses exact-minus-one/overflow caps
without mutating output. It emits no generic reservation ticket and is not an
installed global process/GPU adapter. Unknown external ownership cannot be
replaced with a zero charge to claim renderer admission.

Focused release/ASan/UBSan qualification composes the same authentic capture,
one 1,104,239-byte GEO and the existing unchanged geometry construction/rollback
fixture with the new query. It exercises missing/wrong records, wrong slots and
parts, null inputs, known opaque/source/control aliases, pointer endpoint
overflow, allocation-fault no-allocation behavior, exact and one-byte-short
budgets, full result preservation and actual input teardown. Every emitted
reached native query/getter frame is measured at O0/O1/O2. Per-mode host executable
high-water RSS is recorded separately from named reservations, using a fresh
Python wrapper with one native child. It is not Android RSS/PSS, GPU measurement,
physical Thor fit, an absolute device peak or leak proof; LeakSanitizer is disabled.

Reproduce with a fresh external work/output path, under the coordinator build
lock:

```sh
flock /tmp/coh-cycle-build.lock python3 \
  native-android/engine/scenecatalog/check_source_material_plan.py \
  --source-root . --work /tmp/source-material-plan \
  --output /tmp/source-material-plan.json
```

The checker streams only the existing bounded capture and one source GEO, not the
world archive. `--prepared` can reuse an existing preparation; every used input
is rehashed. The generated composed fixture and raw outputs remain in `--work`;
the compact committed qualification receipt binds their exact compiler inputs.

This milestone is **PARTIAL WITH EXACT BLOCKER**: source partition keys now have
source-qualified immutable CLIENT TexOpt owner/dependency inventories. Effective
CLIENT TexBind/Basic namespace, actual texture bodies/default identities and
source/current generation association remain unproved. No texture, material,
GPU candidate, live world/actor, READY, RECEIVED_CHARACTER or application ACK is
admitted. Next, acquire and hash only this finite dependency set, resolve it
against an authentic ordered CLIENT namespace/default owner, then implement a
concrete lifetime/rollback adapter before any GPU publication. Do not redo the
accepted two-model geometry or increase a memory cap to proceed.
