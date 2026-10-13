# Phase 8: bounded REA-assisted character discovery

The retained REA-assisted City of Heroes checkpoint was queried with supervised Ghidra 12.1.4 using `-process CityOfHeroes.exe -noanalysis -readOnly`. The 90-second process completed successfully. All ten checkpoint files retained their exact SHA256 identities. The client was not executed, imported again, or autoanalyzed; the REA bridge ownership restriction remained in place.

The [receipt](evidence/phase8/rea-character-seams.json) preserves REA 6.4.0 commit `0365454a573eb52c7089320fd74bfd4a673b78ae`, target SHA256 `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b`, portable tool pins, checkpoint identities, and the complete raw query results. The [query](evidence/phase8/CoHPhase8CharacterSeams.java) limits pattern hits, reference edges, candidate functions, and decompilation time.

| Raw byte pattern | Virtual address |
| --- | --- |
| `costume_client.c` | `0x00a7e114` |
| `seqgraphics.c` | `0x00a8c7de` |
| `seqskeleton.c` | `0x00a5c82f` |
| `seqanimate.c` | `0x00a5bb6f` |
| `rt_tricks.c` | `0x00a9de2b` |
| `rt_model.c` | `0x00a9949b` |

The shorter `model.c` pattern matched five byte sequences, including the suffix of `rt_model.c`; these are substring hits rather than five distinct identified source modules. `rt_boned.c`, `GEO_Head_Wretch`, `GEO_Hair_Jack`, and `Collar2x` had no exact raw-pattern hits. No references to the found anchors were recovered from the partial inherited database, and no new function decompilation or source-to-binary function assignment was made. Empty results do not establish absent behavior.

The complete-character gate uses separately pinned original source kernels, genuine costume/geometry/material data, and independent numerical references for its qualified behavior. This binary investigation corroborates the investigation boundary; it is not an original-client runtime capture.
