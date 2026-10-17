# Actual reachable rigid metadata coverage

This is a read-only audit of the retained 391 complete GEO bodies and the exact captured root-reachable model observations. It applies the current conservative rigid entry's metadata gates; passing those gates is only a candidate for later CPU decoding, allocation limits and material resolution. No decoder, material, source generation, visibility, LOD or draw authority is granted.

`evidence/actual-rigid-metadata-coverage-final-38994607354.json` records every exact body SHA, source ordinal, model name, raw disk row, selected metadata and refusal reason. Each body is rehashed before opening. Exact whole candidate/body/closure receipt digests and renderer gate source digests are pinned. All original row order and identities remain intact; runtime sorted rows are not substituted for raw disk rows.

| GEO version | Bodies | Unique root model pairs | Root model-owner references |
| --- | ---: | ---: | ---: |
| 0 | 159 | 1,121 | 1,265 |
| 2 | 5 | 21 | 21 |
| 3 | 1 | 2 | 3 |
| 4 | 4 | 12 | 12 |
| 5 | 10 | 82 | 82 |
| 7 | 57 | 428 | 429 |
| 8 | 155 | 1,250 | 1,271 |
| Total | 391 | 2,916 | 3,083 |

The current versions 0/8 adapter leaves 2,362 unique pairs / 2,527 owner references as metadata candidates. It refuses 545 pairs / 547 references because versions 2–7 are not enabled. Version 7 is the largest concrete remaining version gap. This audit does not recommend removing that gate without original-consumer and actual-stream qualification.

Nine other pairs refuse selected metadata:

- Seven reflection models (also nonempty reflection pack 9): `_deco_skyscraper_01`, `_deco_skyscraper_02`, `_deco_skyscraper_05`, `_deco_skyscaper_06`, `_deco_skyscraper_07`, `_deco_skyscraper_13`, `_ArchEnt_Bldg_Exterior`.
- `_conifer_shadow_sml1__ffshadowlg` has no required UV pack 3.
- `masterpivot` has alternate pivot metadata.

All 2,916 root model pairs have GRID metadata. 1,678 pairs / 1,700 owner references have reduction metadata. These metadata are preserved; neither is an automatic selected-rigid refusal. The four recorded zero-draw Shop siblings remain in their original complete body header but are not root-reachable selected models. There is no zero-draw root-model omission to hide behind an aggregate count.

The native diagnostic opens one bounded body/header at a time, then advances a raw-record cursor and delegates one-row metadata views through the source-header wrapper. The host orchestration compares complete results across release, ASan and UBSan and runs three malformed-envelope refusals per mode. Success frees body/workspace; diagnostic failures terminate the process and do not claim reusable-library failure cleanup. Leak sanitizer is disabled in this environment. No stream bytes are inflated for mesh validation by this diagnostic, and no material callback or server startup occurs. Existing native bridge preparation remains separately qualified on the Shop roof and Neon sign only.
