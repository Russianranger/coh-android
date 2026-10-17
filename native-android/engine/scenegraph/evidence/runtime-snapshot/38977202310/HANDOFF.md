# Captured Atlas roots and future ownership

Run [38977202310](https://github.com/Russianranger/coh-android/actions/runs/38977202310)
at source `3e8b5c9f5b794b58a66c6d8c62a593b926a10873` captured the missing
startup-boundary root and future-object observations. The private server was
stopped before offline decoding. This is an original-runtime source snapshot,
not a received client GROUPS transaction or an authoritative world session.

Artifact [12079509924](https://github.com/Russianranger/coh-android/actions/runs/38977202310/artifacts/12079509924)
is 2,024,961 bytes, SHA256
`8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d`.
Its 34 members total 12,324,476 expanded bytes. The independent inspection
rechecked every member's ZIP CRC, SHA256 and extracted bytes; 14 native, four
producer, five helper, 33 orchestration and 17 original full-file source hashes;
the exact exporter PE and compile/stage receipts; source/run binding; and owned
process cleanup. The reproducible result is `capture-inspection.json`.

The canonical archive is
`native-android/corpus/server-catalog/runtime-snapshot-38977202310/evidence.zip`.
The original 12,179,670-byte catalog remains unchanged, with SHA256
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`.
The new sidecar is only 6,585 bytes, SHA256
`c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02`.

## Seven-name result

Each name is a distinct observed `group_info.pre_alloc` object, outside all
40,225 original definition slots. All original IDs are zero; pointer incidence
and canonical source lookup distinguish them. Each has one incoming catalog
edge and no children or model. Each library path and cached-bounds lookup is
absent. Live bounds are zero except `lod_scale=1`; the only set bounds flag is
`editor_visible_only`. Scratch lookup bounds are zero. These are captured
source values, not invented definitions or permission to skip asset admission.

| Name | Root reachable |
| --- | --- |
| `_cot_warpgate_base` | No |
| `_cot_warpgate_glow` | No |
| `_mmayhem_curtain_8_01c` | **Yes** |
| `_mmayhem_curtain_8_02c` | No |
| `_mmayhem_curtain_8_03c` | No |
| `_mmayhem_curtain_16_01c` | No |
| `_mmayhem_curtain_16_02c` | No |

The reachable object enters through the previously reported catalog edge
file 376, definition slot 32, child 1. The hosted diagnostic proves reachability
from the complete root set; it does not emit a per-root path witness.

## Root closure and memory

All 33 root slots are active, refer to original file 0
`maps/City_Zones/City_01_01/City_01_01.txt`, and retain their exact definition
slots, names and source matrices in the inspection. Every 49-byte original
matrix encoding agrees with the qualified native decoder. Complete name
resolution covers 508 files, 40,225 original slots and 130,314 catalog links.
The root closure contains 15,352 regular definitions, one future object and
57,710 links, with maximum depth 69. Both original CRCs pass:
definitions 3,173,822,562 and references 3,649,375,123.

| Named ownership | Bytes |
| --- | ---: |
| Original catalog input | 12,179,670 |
| Sidecar input | 6,585 |
| Diagnostic index pool | 2,457,700 |
| Largest decoded-record scratch | 1,654,842 |
| **Measured native heap peak** | **16,298,797** |
| Output report | 34,192 |
| Parser stack reservations | 196,608 |
| Host harness/provider reserve | 262,144 |
| **Charged aggregate peak** | **16,791,741** |

This pool stores identities and links for diagnostics. It is not a resident
render graph with every instance transform, geometry, texture or material.
The figures exclude allocator overhead and process RSS. They must not be
presented as the complete live world's memory requirement.

## Qualification reused and next work

The unchanged hosted report `runtime-graph-diagnostic.json`, SHA256
`cfaa86f3977bda91f9018b69d32fb2c83202b34206b75dd194d028ee7a42cb1e`,
passed release, ASan and UBSan with identical captured results, 17 captured-pair
controls per mode and 21,726 fixture controls per mode. Inspection reused those
successful runs: zero native reruns and zero additional server starts. No
production scenegraph or APK changed. Android execution of this new diagnostic
is pending separately; existing compact Android qualification remains valid.

The seven-name provenance uncertainty is resolved for this exact startup
snapshot. The accepted strict compact importer still refuses a catalog alone:
publishing these separately observed futures needs an explicitly bound graph
owner and independent rollback/lifetime qualification. Authentic assets and
materials remain separate prerequisites. A later live client transaction must
establish its own matching GROUPS generation, complete character update and
generation-coherent renderer publication; neither this snapshot nor matching
historical CRCs establishes those conditions.

To reproduce the inspection, run `inspect_runtime_snapshot_capture.py` with
`--artifact-root` pointing to the downloaded ZIP/member-manifest/extracted
directory, `--candidate` to the admitted Win32 candidate, `--source-root` to a
repository containing source revision `3e8b5c9f5`, and `--output` to a new JSON
receipt. The inspector verifies original container framing and scalar fields;
it reuses the hosted qualified C wire parser instead of duplicating its grammar.
