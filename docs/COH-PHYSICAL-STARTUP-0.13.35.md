# AYN Thor 0.13.35 physical follow-up — 2026-10-13

This records the three supplied outer ZIPs without changing their contents. Machine-readable observations and original input byte/SHA-256 identities are in [the evidence](android-evidence/coh-physical-startup-0.13.35-analysis.json). A successful native save and an incomplete overall Character Check are separate outcomes.

## Physical findings

| Observation | First session | Second session |
|---|---:|---:|
| Reopen to Kings world event | 860.825 s (14:20.825) | 584.314 s (9:44.314) |
| Kings preparation | 311.216 s, cold | 21.073 s, validated reuse |
| Native Kings console startup | 256.833 s | 309.838 s |
| GPU prerequisites, UI interval | 75.828 s | 71.348 s |
| Game initialization observer | 202.935 s | 263.847 s |

These are nested phases, not additive totals. The user separately observed approximately 14 minutes and 9:40. Reused preparation was 290.143 s shorter in these sessions; this demonstrates actual reuse, not a controlled estimate of a release's causal speedup. Native MapServer and Game were slower in the second session. CPU contention, storage and thermals remain possible causes, not established diagnoses.

The second GPU report rejected an existing roughly 966 MB closed probe-prefix inventory because its temporary Wine server lock was absent. Wine/WGL initialization and probing consumed 66.441 s; the native Vulkan probe took about 31 ms. Reusing the registered prefix still requires current GPU probes and authenticated shutdown/cache evidence.

Second Game initialization included a 251.769 s message-store-to-all-data interval. Nested phases include shaders 55.816 s, texture headers 30.022 s, FX 25.388 s and client sequencers 9.222 s. The texture header index reported 38,986 hits and zero ordinary reads: it was working. The 249 CompiledCg/CgFXShader log rows occur for both CG_SOURCE and cached CG_OBJECT paths; they do not prove 249 fresh shader compilations or cache misses. Native source/object creation and driver loading require separate observations.

## Kings to Atlas

The actual native monorail transfer succeeded. Native verified arrival was 672.826 s (11:12.826), and fresh Android views followed at 675.122 s. Python/runtime preparation was 303.211 s, including mirror 243.078 s, graph 49.736 s and native-cache preparation about 4.536 s. Native readiness took 273.728 s, with console startup 261.866 s. Departure-to-native-character-ready took 76.345 s; a client object-library gap accounted for 62.629 s. Remaining observation overhead and nested instrumentation must not be double-counted.

The latest native ordinary logout was at **03:43:45 UTC in Atlas Park, map 1**, position **(706.343750, 58, -1416.796875)**. The final PostgreSQL location was not exported because the old strict selected-row checker threw first. Atlas is therefore the expected next destination, not a substitute for the next startup's authoritative PostgreSQL query. Do not force either world or change saved position.

## Why Character Check failed

First session: all seven prior core powers retained their stable UniqueIDs and semantic fields; the native Commuter temporary power was added, shifting packed row/index numbers. Thirteen costume rows were unchanged. The first after-save SQL snapshot exactly equals the second session baseline, establishing persistence of that save. Login count advanced 5 to 6.

Second session: XP increased 20 to 45 and influence 17 to 34; the native reward logs support the exact +25 XP and +17 influence. Login count advanced 6 to 7. The Commuter temporary power was removed and the same seven core powers remained. The old reward validator rejected the already-validated monorail connection source and assumed Atlas-only routing. These exceptions occurred before save-success flags were set. They are not evidence that native ordinary saving failed.

Both sessions completed owned cleanup: workers were reaped, Wine stopped and PostgreSQL shut down gracefully. Input transport failures were zero, and the user confirms Send Text works again. Both gameplay outer ZIPs retain current native and SQL failure evidence. The third ZIP is a successful runtime setup report; generic gameplay passed:false fields are not a runtime setup failure.

## Acceptance limits

No sub-five-minute whole startup, sub-one-minute client start or sub-30-second zone has been demonstrated. Report export and owned cleanup have physical evidence here; complete corrected Character Check, final SQL Atlas position, cross-map rewards and future enhancement preservation require current qualification and a short physical retest. No player database, profile, position or inventory was modified by this analysis.
