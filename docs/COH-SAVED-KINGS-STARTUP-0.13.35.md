# Saved Kings Row startup changes for 0.13.35

THORHERO remains saved in Kings Row, map 5, port 7003. The 0.13.34 physical report proved world entry and a committed save there. Its guest-to-client-ready path took 1,394.9 seconds; the user observed approximately 24 minutes before login. Under five minutes remains the next device target, not a demonstrated result of this continuation.

## Changes on the measured startup path

The previous Kings reopen first prepared a complete Atlas provider under the local DbServer stage: 283.8 seconds mirroring Atlas data and 36.0 seconds preparing its graph. The actual DbServer startup was 29.9 seconds. Kings then prepared another complete mirror in 221.8 seconds, its graph in 39.7 seconds, and spent 236.4 seconds reaching native readiness. Those prior-version measurements explain why optimizing PostgreSQL itself, which was ready in 0.5 seconds, would not address the main problem.

The production zoning server now reads the complete preserved-character baseline from PostgreSQL before selecting the initial provider. Saved `staticmapid=5`, including its already supported unassigned pre-login `mapid`, selects Kings Row. Identity, powers, enhancements, costume and saved position receive the existing baseline checks. A second baseline after native DbServer startup must select the same saved map. No SQL mutation, relocation or character recreation is introduced.

For saved Kings, the native DbServer starts from the authenticated minimal DbServer input layout (62 files, including schema, account/catalog and map configuration). The Atlas mirror, animation/FX providers and graph are deferred until an actual Atlas transfer request. Common authenticated schema and required original geometry checks remain. The initial launch prepares exactly one Kings provider and one MapServer at port 7003. Atlas direct reopen retains its existing preparation behavior.

An eventual Kings-to-Atlas journey builds a separate owned Atlas runtime. It does not rename the running DbServer's schema or credentials. Atlas preparation checks the existing shared 600-second transfer allowance and ordinary Save/Logout requests throughout cooperative work. Failure or cancellation leaves the saved character and current Kings process under their existing controls and cannot launch Atlas afterward. The guard does not extend the native bridge deadline.

The exact retained MapServer consumer excludes `texture_library` before initializing its native folder cache. For those pinned native bytes only, cold server mirroring now omits the top-level texture directory without enumerating its leaves. Client textures, nested text definitions, geometry, collision inputs, graphs, private BIN roots and native bytes are preserved. A different consumer gets the complete mirror. A previously qualified, closed full server generation can migrate without deleting its texture inputs; an unowned, changed or incompletely closed generation cannot be adopted. Complete original-asset qualification reports the real projected file counts separately.

## Kings MapServer and client initialization

The physical Kings native MapServer and Game initialization took approximately 236 and 214 seconds sequentially. Their sum alone exceeded five minutes before preparation and GPU checks. The changed Kings schedule starts client preparation and Game initialization while the fully prepared, owned Kings MapServer initializes in its separate mutable data tree.

Client input remains blocked until both independent proofs pass: current Game renderer/data readiness and current Kings native completed ticks plus a fresh DbServer map/world/port status query. Process launch or a first tick alone cannot admit input or claim character world entry. Actual character connection and movement retain their later independent SQL/native checks.

The original MapServer startup deadline is checked during client asset work and GPU preparation, as well as at the final readiness join. The Game's own startup deadline measures Game readiness rather than time waiting for the map. Failed ownership, native exit, cancellation or readiness failure follows existing cleanup and report handling. Retrying client initialization cannot launch another MapServer. Atlas direct startup remains serial in this stage of the change.

Reports keep the MapServer stage separate from whichever client stage is current. They record launch time, sampled first completed tick, sampled native readiness, client launch, and any native zero-tick progress observed after client launch. Process residency overlap is labeled separately from evidence of overlapping native initialization; neither is presented as an isolated CPU speedup. Deferred Atlas and Kings native logs are attributed to their owned map runtimes and included in the bounded archive.

## Qualification and performance limits

A fresh focused invocation passed **236 tests with zero failures, errors or skips**. It includes 25 new preparation/overlap tests, saved-map and identity tests, zoning/monorail tests, manual-session integration, original transfer budgets, log attribution, native animation compatibility against authenticated public donor bytes, graph/provider receipts and warm-cache ownership. Exact commands and file hashes are in `android-evidence/saved-kings-startup-0.13.35-host-tests.json`.

The tests use controlled SQL and native process evidence. They do not constitute a physical Kings connection. The new complete-assets adapter separately executes production saved-map preparation against actual packaged assets. It also preserves the frozen historical full-startup fixture with an explicit legacy Atlas/control boundary; its earlier SQL/native limitations remain declared. The final source qualification at `6136171e842eb69807636dbad9aedff0af6c5887` passed 201 current suites / 2,772 cases with zero failures, errors or skips; 7 suites / 95 historical cases retain their original identities. Actual Windows native Db startup/restart and shipping launcher lifecycle are separate current gates. Signed packaging and public-byte evidence are recorded in `android-evidence/client-manual-session-0.13.35-publication.json`.

The same host invocation measured a 4,002-leaf cache fixture at 0.624 seconds cold and 0.003 seconds warm, with 4,002 versus zero immutable link creations. This small host result demonstrates reuse behavior only. It cannot predict Android/PRoot wall time, native loading or the next cold install.

The change removes previously measured redundant Atlas work, enables exact closed-generation reuse, and removes the serial MapServer/Game dependency. Their physical savings are not additive estimates: CPU contention and storage contention can change both native times. Overlap can also increase peak transient RAM. No device RSS/PSS, thermal, FPS or successor speed improvement has yet been measured. A first upgrade can still require cold preparation if the prior generation did not prove cleanup; unsafe prior trees are preserved rather than reused.

The next physical acceptance starts with the existing THORHERO in Kings Row. Record total time to input-ready login and usable world separately, verify the new manual input/capture controls, save normally and export the complete outer ZIP before any long monorail test. Then follow the ordered tests below, using the report's actual destination and independent loading phases.

## Ordered AYN Thor acceptance

This order refines the bundled testing notes, which discuss warm comparison together with follow-up travel. Do not begin a long travel or cache-comparison test until the short Kings save and outer ZIP export pass.

**A — THORHERO saved in Kings Row.** Install 0.13.35 over the existing application, preserving all data and Assets 1.0.0. Run Set up / update runtime once. Reopen saved THORHERO and confirm Kings Row / map 5 / port 7003. Record reopen-to-login-ready time separately from time away and login-to-usable-world time. Try Send Text/L3 for login when convenient. Use Start test when ready, verify movement, powers, costume, enhancements, graphics and combat, then Stop test. Record FPS and temperature. Save character / log out normally, wait for Saved character verified, Finish and export the complete outer ZIP. Export a storage scan if cleanup/reuse needs investigation. No long monorail journey during A.

**B — Kings Row to Atlas.** After A passes, reopen in Kings and use the real monorail to Atlas. Record preparation, native startup, transfer and usable-world arrival separately. Confirm movement and character state, save normally in Atlas and export the outer ZIP.

**C — Saved Atlas reopen.** Reopen from the new Atlas save. Confirm Atlas selection and persisted position/state, with no unnecessary Kings MapServer. Save normally and export.

**D — Warm-cache and round trips.** After A–C pass, compare equivalent cold versus authenticated reused-cache preparation and test Atlas-to-Kings and Kings-to-Atlas as practical. Distinguish same-session resident MapServer reuse from a new process with warm filesystem caches. Capture loading phases, FPS, thermals and available memory separately. Start/Stop capture is manual; startup, transfer and cleanup failure guards remain. Preserve saved data and export failure evidence if a guarded operation cannot complete.
