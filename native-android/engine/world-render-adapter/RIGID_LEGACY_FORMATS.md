# Explicit v2/v3/v4 CPU formats

Three fixed module functions, `coh_wr_rigid_v2_acquire`, `coh_wr_rigid_v3_acquire` and `coh_wr_rigid_v4_acquire`, prepare model-local CPU geometry. There is no public version mask. Existing default/source0/8, v5/v7 entries and opaque SourceBody bridges retain their policies; the latter are deliberately not extended to versions 2–4 in this tranche.

The source distinctions are explicit:

| Version | Original model record | Pack/ID semantics |
| --- | --- | --- |
| 2 | Fixed 216-byte `ModelFormatOnDisk_v2` | Seven disk packs remap to runtime slots 0,1,2,3,5,6,7; secondary UV/reductions/reflection absent; original runtime-pointer/flags/pivot guards remain enforced. |
| 3 | Variable record, eight packs | Original ID follows the eight packs. CLIENT source sets autolod distances to -1. |
| 4 | Variable record, eight packs plus two obsolete slots | Original source skips 24 obsolete lightmap-transform bytes before ID; they are preserved, not interpreted as reductions/reflections. |

All use the original five-field envelope and fixed 148-byte legacy LOD rows. Every row count and active float is bounded/validated while raw unused/trailing bytes remain intact; no LOD selection or transformation is applied. Legacy v2 leaves zero-initialized autolod fields untouched, unlike the variable v3/v4 branch. The native original32 expectations preserve this distinction.

## Actual retained scope

`qualification/rigid-v234-20261017/all35-host.json` covers every current root-unique model pair in these versions, rather than inferring success from their header similarity:

| Version | Exact bodies | Root-unique model pairs | Captured model-owner references |
| --- | ---: | ---: | ---: |
| 2 | 5 | 21 | 21 |
| 3 | 1 | 2 | 3 |
| 4 | 4 | 12 | 12 |
| Total | 10 | 35 | 36 |

All 35 complete CPU packets, totaling 253,712 bytes, match independently executed unchanged original delta decoding, V conversion and exact ordered source partitions (22,014 decoded scalars). The inputs include compressed indices/positions/normals/UVs, multi-part meshes, both v3 root trays and the actual nonempty v4 obsolete transform slots. The original legacy LOD consumer executes on all 101 actual rows from the ten exact bodies in every host mode, with raw active field outputs identical to source bytes. Runtime destination/allocation helpers in that oracle remain harness substitutes; no effective CLIENT LOD state is claimed.

The v3 tray partitions include five/six `PORTAL_door*.tga` parts plus `blackbox.tga`. They remain present, ordered and counted. CPU qualification does not admit portal visibility, clipping, invisible material behavior or drawing these parts. Likewise editor-prop, glass, glow and other source tricks still require independently qualified CLIENT semantics. Fixture material callbacks, fixture asset generation 17 and material generation 19 are explicit lower-level test inputs; these entries do not derive a server/live generation or a SourceBody profile.

## Qualification and retained limits

Release, ASan and UBSan each passed 5,296 controls, including 175 allocation-failure stages and 313 grammar controls. Checks cover cross-entry/version refusal, legacy flags and runtime/pivot guards, malformed compressed channels/pack spans/LOD count/span, unsupported NaN LOD, duplicate model identities, wrong layout/digest/generation, budgets, cancellation after material pins and pin/loader cleanup. Changing the 24 obsolete v4 bytes to a synthetic nonempty pattern leaves CPU packets unchanged, matching the original source skip rule; this is a grammar control and not an admitted mutated asset. All original body SHA pins remain unchanged.

All 35 unchanged original32 `readModel` oracles and original disk declarations compile and pass layout checks. Local ELF32 execution remains refused with errno 8 for every case; no original32 execution or 55-fact metadata comparison is claimed. `all35-original-source-diagnostics.zip` and its checksum ledger preserve 325 source/object/binary/refusal/expected/output members. Each case includes its exact 220-byte expectation, including source autolod values, for a later minimal coordinator execution check. `--require-original32` refuses success unless every consumer actually executes and matches. The original legacy LOD and delta consumers already execute natively as separately recorded above.

Required unchanged-entry regressions pass in all three modes: default v0 243 controls, default v8 259, source0/8 291, v5 206 and v7 225. Existing opaque default bridge controls remain 947,306, and source0/8/v7/v5 bridge controls remain 947,664 per mode with exact CPU packet equality. The additive `check_source_rigid_after_legacy_formats.py` only directs the existing bridge qualifier to these new frozen low-level regression receipts; the previous qualifier and receipts are untouched.

The four-case preliminary diagnostic remains preserved locally and is superseded by the complete 35-pair proof. No accepted APK/module, protected asset API, JNI, Gradle, CMake, gameplay code or server is modified. Leak sanitizer is disabled in this host environment. Android build/execution, physical Thor, live GROUPS association, authenticated gameplay, effective CLIENT materials/LOD and world authority remain unqualified for this tranche. No CI, server capture, download or APK was launched.
