# Phase 7: bounded REA-assisted animation discovery

The retained Phase 1 project was queried read-only using the recovered REA-assisted workflow and directly supervised Ghidra 12.1.4. The original client was not executed, imported again or autoanalyzed. The prior REA native bridge PID ownership restriction was preserved; this is direct Ghidra continuation evidence, not an REA-owned provider response.

Reference `CityOfHeroes.exe` SHA256 is `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b`. Portable tool identities, script/result hashes and all ten unchanged checkpoint file hashes are preserved in [the receipt](evidence/phase7/rea-animation-seams.json). Original REA version 6.4.0 and commit `0365454a573eb52c7089320fd74bfd4a673b78ae` are recorded there.

| Exact raw anchor | Virtual address |
| --- | --- |
| `animtrackanimate.c` | `0x00a59adf` |
| `seqanimate.c` | `0x00a5bb6f` |
| `seqskeleton.c` | `0x00a5c82f` |
| `seqsequence.c` | `0x00a5c58f` |
| `Could not find animTrack for bone` | `0x00a5caa0` |
| `Animation file %s doesn't exist` | `0x00a5cb30` |
| `bone_IdIsValid(anim_id)` | `0x00a5bb7c` |

No references to these anchors were recovered from the partial inherited database. Searches for `unPackQuatElem`, `seqSetAnimationHeader`, and the backslash spelling of the chosen asset names found no exact raw anchor. Empty results do not prove absent behavior. No analyzed function was assigned an original source name and no new pseudocode was produced.

The [retained query](evidence/phase7/CoHPhase7AnimationSeams.java) checks the executable identity, limits each initialized-memory pattern search to ten matches per block, caps reference edges and candidate functions, and leaves the database unchanged. It ran with `-process CityOfHeroes.exe -noanalysis -readOnly`, a 90-second process deadline and the same portable JDK21/Ghidra paths documented in [Phase 6](PHASE6-REA.md).

The animation probe therefore relies on separately hash-pinned original source-function checks and genuine encoded base/motion assets for key decoding, clock, hierarchy and socket parity. The binary anchors corroborate investigation boundaries; they do not establish source-to-binary function equivalence or an original-client runtime capture.
