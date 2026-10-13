# Native startup investigation for 0.13.35

The next physical start remains **THORHERO saved in Kings Row, Map 5, port 7003**. The immediate user target is below five minutes from reopen to usable world, excluding manual login. This is a target, not an achieved device measurement. This investigation preserves the accepted .32 native MapServer and .34 Game/DbServer; the isolated profiler described below is not included in the APK.

## Observed critical path

The .34 user observation was approximately 24 minutes before login, including 5:53 labelled local database startup and 8:29 labelled Kings Row startup. These whole-operation labels contain preparation and native startup. The detailed evidence and archive attribution are in [COH-PHYSICAL-STARTUP-0.13.34.md](COH-PHYSICAL-STARTUP-0.13.34.md).

| Physical report phase | Seconds | Meaning |
|---|---:|---|
| Local server preparation | 331.595 | Includes an unnecessary complete Atlas provider before saved Kings selection |
| Atlas cold private mirror | 283.768 | Filesystem traversal and private/link creation, not native DbServer computation |
| Atlas graph preparation | 36.019 | Shared prerequisite handling plus Atlas-specific graph work |
| Native DbServer dispatch readiness | 29.947 | Actual owned native process after preparation |
| Kings provider preparation | 269.820 | Includes another complete mirror |
| Kings cold private mirror | 221.761 | Repeats most shared immutable inputs |
| Kings graph preparation | 39.695 | Actual required Kings destination data |
| Native Kings readiness | 232.543 | Native console duration; observer sampled it at 236.365 |
| Native sequencer interval | 99.481 | Parsing message through relevant-folder caching; decomposition not yet measured |
| Native FX | 23.003 | Despite a prepared projected FX BIN remaining present |
| Native story arcs | 26.910 | Repeated definition setup |
| Native group libraries / map | 17.123 / 19.170 | World loading |
| Native beacons / collision unpack / PhysX | 3.680 / 2.320 / 6.400 | Not the dominant startup cost in this session |

Client native startup was also about 213.6 seconds. Eliminating the duplicated Atlas preparation alone cannot achieve the target if native MapServer and Game initialization stay serial. The .35 guest stage therefore prepares only the saved world and joins independently verified MapServer and client startup. Overlapping these processes can contend for CPU and memory; the next device report must measure that effect. Adding or subtracting the old phase durations is not a forecast of device performance.

The reported private MapServer providers each included 187,638 files and 11,385 directories. A new host qualification records the original texture inventory, the current client texture inventory and actual projected mirror file count rather than estimating their reduction. Its measurement is input inventory, not native reads or time saved.

## Dynamic MapServer question

This source already supports on-demand maps. `DBServer/src/mapxfer.c` has `startInstancedMap` and `startMapIfStatic`, both using `launcherCommStartProcess`. `DBServer/src/launchercomm.c` constructs the same `mapserver.exe -db ... -udp ... -map_id ... -launcher -cookie ...` process for the selected map. An instanced map is a different assignment/lifetime of this engine; this code does not contain a separate fast-loading MapServer implementation.

The Android implementation already starts the selected native destination on demand and retains at most two owned maps for a return trip during the session. It did **not** start a second Atlas native process in the reported Kings reopen. Its waste was preparing Atlas's complete input tree before starting the selected Kings native process. Replacing Python supervision with the stock Launcher would not remove the common definition and animation loading in a newly started process.

`MapServer/src/svr/svr_init.c:checkTsr` is a resident preload/synchronization mode, not a safe factory that clones fully initialized maps. Current map launches disable shared memory. Adding a TSR process under that configuration would add residency without demonstrating reuse. Cross-session native residency would require separate ownership, Android lifecycle, database-session and memory qualification. Same-session destination residency remains useful and is distinguished from merely warm filesystem caches in reports.

## Source-bound preparation reduction

The accepted native MapServer's `sysInit` explicitly excludes `texture_library` from FolderCache enumeration before opening its data directory. `MapServer/src/svr/dbquery_init.c` has the same exclusion. The .35 private server projection applies only to the exact retained MapServer SHA-256 `fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363`, the expected upstream source commit and `svr_init.c` SHA-256 `2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d`.

Only the top-level texture tree is excluded. Client texture files and translated text definition directories remain available to Game. An unknown native consumer receives the full input policy. Existing authenticated full caches can be adopted only through the reviewed cache ownership/identity transition. The native FolderCache exclusion is evidence of enumeration policy; explicit path overrides exist, so it must not be described as proof that all possible native file accesses are impossible. Native bytes, map geometry, definitions, animation input and collision/beacon data remain unchanged.

The minimal local Db runtime contains the complete accepted **62-file input bundle**, including account catalog/loyalty definitions, inventory/proficiency dbidmaps, map assignments, load balancing, schema templates and attributes. It is not a directory containing only SQL DDL. Its stock normal-Db predecessor had actual ARM64 PRoot/Wine normal-schema qualification. Retained manual-Db overlays add the guarded launcher wait, SQL save/read repair and thread-name formatting fix; they add no definition or asset loaders. A .35 actual-assets host preparation test proves exact bytes and structure but does not itself execute this retained manual DbServer against the smaller runtime. Fresh native qualification and inherited qualification must remain separate in release evidence. The final source now has an additional fresh Windows proof: retained native DbServer startup, map-status queries, schema/identity preservation, restart and owned cleanup against an isolated disposable PostgreSQL cluster passed in job `115066186047` of workflow `38326347301`. It used the minimal input layout and synthetic fixtures; it did not execute Wine/Android, MapServer world entry or the physical THORHERO profile. See the final publication receipt for exact artifact and native byte identities.

## Native provider and reusable BIN authority

The 99.481-second sequencer interval needs finer native evidence before changing its format or validation. `Common/seq/seqload.c:seqPreloadSeqInfos` runs the parser, postprocessing with move validation and full animation attachment (including base skeletons), then final state-to-move indexing. The 83,739,012-byte `sequencers.bin` is not simply memory-mapped immutable data: the native binary decoder reconstructs allocated structures and strings. `serialize.c:SimpleBufOpenRead` reads a whole binary stream into memory before decoding; repeated decoder fields are not necessarily separate physical filesystem reads.

The physical animation certificate counter reported 5,120 certified tracks, no fallback and 78,663,000 approximate raw bytes hashed in **1.097004 seconds**. Certificate hashing cannot explain the whole sequencer interval. Existing validation-skipping certificates remain retained. It is also not established that the native parser opened each prepared BIN successfully merely because the files existed before and after startup.

Existing namespace/collision receipts protect their intended inputs. A receipt over directories and selected anchors does not authenticate arbitrary in-place changes to every provider leaf. `ParserIsPersistNewer` enforces signature/schema and dependency membership/date/absence checks. Globally forcing production mode would change freshness and text fallback behavior; that is not an acceptable substitute for provider proof.

The next reusable-BIN authority stage should bind each BIN to its exact opened source provider generation, dependency inventory including absent inputs, parser schema and native consumer. An immutable packed provider or equally strong generation authority is needed before amortizing all leaf checks across process starts. Failure must fall back to the current parser. Native Atlas and Kings outputs and world readiness must be compared before shipping a cache-authority change.

## Isolated native profiler implemented in this continuation

`tools/prepare_native_startup_profile_source.py` stages an additive diagnostic overlay after the retained .32 source overlay. It refuses immutable upstream/repository destinations, changed input anchors, linked paths and pre-existing outputs. It does not bypass freshness, rewrite animation data, provide a reusable-cache certificate or authorize publication.

The existing freshness observer was guarded by `SERVER`. UtilitiesLib is its own compilation target and does not inherit the MapServer target's private definition. The diagnostic now activates the parser observer explicitly in its own translation unit, after project includes, preserving Windows/Winsock header order. This avoids shipping a profiler that silently reports nothing from the parser library.

The new `COH_NATIVE_STARTUP_PROFILE_V1` rows time:

- Existing six-phase BIN freshness decisions through the retained observer.
- BIN dependency table, unchanged decoder and close, with original success/failure preserved.
- Sequencer postprocessing, including existing full animation attachment.
- Sequencer finalization and complete preload.

The header uses stack records and bounded static counters, with at most 256 rows per translation unit. It introduces no allocation, persistent cache or filesystem reads. Invalid clocks and clock regression produce an explicit invalid observation. Input tokens are diagnostic grouping identifiers, not cryptographic proof. Wall-clock time is not CPU time.

Fresh host execution: **23 tests passed, no skips** across the new 8 profiler tests, 9 existing freshness-observer tests and 6 namespace-certificate tests. The new tests compile extracted production decoder control flow in a portable harness and compare six success/failure scenarios, check activation without `SERVER`, disabled output, bounded rows, clock failure and unchanged sequencer statements. These are not a full Windows MapServer build or Wine/device execution. A complete staged Windows build, both native worlds, console attribution and output parity remain mandatory before a profiler binary can be used for physical qualification. The shipping MapServer is unchanged.

## Ranked remaining work

1. Measure .35 saved-Kings-only preparation, closed-cache reuse, Map/Game overlap, normal save and report export on Thor. The host adapter executes original Assets 1.0.0 import bytes and current APK preparation methods for cold and warm Kings plus deferred Atlas; SQL/readiness/cleanup facts are explicit controlled boundaries.
2. Execute the isolated profiler in a fully qualified native build. Separate freshness, decoding and animation attachment inside the sequencer interval. Repeat provider proof for FX and story arcs before selecting the next optimization.
3. Implement per-BIN reusable proof only against authenticated provider generations. Measure native skipped work and peak allocation rather than reporting reduced host operation counts as device speedup.
4. Revisit exact SDK/geometry/cooking collision reuse after the larger costs. The reported PhysX stage was 6.4 seconds, so it is a lower-value first target than the duplicate mirrors and 99.5-second sequencer interval. Preserve the owned-stream prototype; require native Atlas/Kings parity before shipping it.

No measured sub-five-minute device start, lower peak RSS/PSS, thermal improvement or FPS gain is established by these host changes. The first acceptance test is a short Kings Row session with ordinary save and an exportable outer ZIP. Capture preparation, validation/reuse, native launches, independent readiness, login, world entry and movement separately; then measure return travel after that test passes.
