# Actual source resource/root closure (run 38994607354)

The successful disposable capture's `resources.cohres` is 12,596,422 bytes,
SHA256 `8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6`.
The catalog and root/future snapshot remain byte-identical to the earlier accepted
source capture. New source/run identities are retained; historical run labels are
not reused. The read-only native association verifies every regular slot and
future ordinal against the owned catalog, snapshot and graph before reporting.

| Source dependency | All records | Root reachable |
|---|---:|---:|
| Active owner records | 40,232 | 15,353 |
| Model references | 9,611 | 3,083 |
| Exact observed GEO filenames | 467 | 391 |
| Unique GEO/model-name pairs | 9,230 | 2,916 |
| Observed texture partitions | 17,790 | 5,535 |
| Distinct texture names | 3,413 | 1,769 |
| No-model group containers with children | 30,614 | 12,269 |
| Empty runtime future objects | 7 | 1 |

There are zero missing original geometry observations: each original nonempty
geometry string has an exactly matching captured model. No-model regular records
are group containers. Treating their count as missing models would be incorrect.
All model observations have original `GeoLoadData.loadstate == NOT_LOADED (1)`
and model loadstate zero. These are source-loaded header stubs, not proof of
full geometry bodies, effective client materials, client LODs or renderer support.

All seven previously unresolved names are explicitly observed empty future
owners, original ID zero, no model and no object-library observation. Only
`_mmayhem_curtain_8_01c` is reachable. The other six are `_cot_warpgate_base`,
`_cot_warpgate_glow`, `_mmayhem_curtain_8_02c`, `_mmayhem_curtain_8_03c`,
`_mmayhem_curtain_16_01c`, `_mmayhem_curtain_16_02c`. None is replaced,
removed or fabricated into geometry.

`inspect_resource_closure.py` accepts an independently trusted binding digest,
revalidates cleanup/provenance with the existing capture validator, compiles the
current standalone native join plus a read-only graph/resource accessor, and
classifies each joined owner. Source and capture bytes are rechecked afterwards.
Its receipt lists all 391 reachable exact source GEO names. This additional
closure report is host release analysis; the separate integrated native join
qualification owns sanitizer evidence. No GEO body is opened by this report.

Next admission requires authenticated full GEO assets from the matching source
generation, exact source-name/manifest association, original sorted-runtime to
disk-row validation, and complete client resource semantics. A client visual
manifest name match is a lookup candidate until content and generation are
independently established. A live GROUPS generation and selected authoritative
actor transaction remain separate prerequisites for world publication.
