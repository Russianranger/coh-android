# Actual root resources and original full-body candidates

The actual source capture contains 3,083 reachable model observations representing
2,916 exact GEO/model-name pairs in 391 source GEO filenames. Correlation uses the
manifests' explicit original PIGG `provenance.entries[*].path`. It does not invent
a native path by adding a prefix, changing an extension or stripping a suffix.
The separately stored manifest asset path is only a candidate loader identity.

| Original provenance lookup | GEO files |
|---|---:|
| Exact original source path bytes | 218 |
| ASCII case-folded original source path | 173 |
| Missing or ambiguous candidates across these two manifests | 0 |
| Atlas world supplement candidates | 388 |
| Client visual supplement candidates | 3 |
| Observed/manifest GEO version agreement | 391 |

The three client-visual candidates are `Shop_tailor.geo`,
`vanguard_platforms.geo` and `big_detail.geo`; full paths and SHA256s are in the
machine-readable receipt. The existing authentic PraetorianBox fixture is absent
from this captured resource stream and establishes no Atlas membership.

The client-visual manifest is SHA256
`8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2`.
The Atlas world manifest is SHA256
`204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86`.
The latter was recovered from the existing Git blob, without downloading another
asset bundle. Both hashes match the actual capture's control-fixture
`client_asset_hashes`; that fixture hash itself matches the captured source
identity. This proves the retained preparation manifest chain. The receipt keeps
the actual source/run/binding hashes, aggregate runtime inventory, original
archive/table/range metadata, full-body manifest SHA and exact source owner
records. Every captured model observation is associated with its candidate file
without claiming the candidate body has been acquired or its model verified.

The original preparation code gives the next proof steps concrete boundaries:
`atlas_beacon_package.ensure_required_geometry` selects client-visual full GEO
byte/hash records, verifies existing selected outputs or extracts verified
payloads, then seals `atlas-required-geometry` outputs. `atlas_world_assets`
verifies existing supplement bytes against exact manifest pins and installs
missing files. `local_character_server.stage_map_data` mirrors verified roots
with explicit file ownership and selection rules. The captured control fixture
records their preparation completion and source identities. These rules must
remain part of any complete per-file generation proof.

The resource observer captures header-derived in-memory records, not the exact
opened file SHA or header-byte SHA. The artifact retains a hash of the complete
post-preparation runtime inventory, but not that inventory's individual leaf
records, selected-GEO marker outputs, or an opened-file provenance receipt.
Manifest version/name/metadata agreement therefore remains a lookup result here.
The report deliberately sets `same_source_generation_established` and
`assets_admitted` false. Native GEO admission still requires authenticated body
bytes, the source-generation/selection proof, exact original sorted model rank
versus disk row, full model/material partition checks, and effective CLIENT
material/trick/capability/swap/LOD closure. No additional server capture was run.

`correlate_resource_manifest.py` consumes a hash-pinned native closure receipt,
the exact resource stream and independently pinned manifests. It verifies the
source-to-control-fixture manifest chain, retains every reachable original owner
and model/texture observation, and emits candidates only. It performs no asset
acquisition, mutation, server operation or rendering.
