# Native client and zone startup investigation for 0.13.36

The new physical requirement is a client start below one minute and zone travel at or below 30 seconds, with the overall reopen target still below five minutes. None of those targets has been demonstrated. The user successfully used Send Text again and reports returning from Kings Row to Atlas Park. The next reopen must use the authoritative persisted PostgreSQL location; it must not assume the earlier Kings Row checkpoint still applies after the later reported Atlas save. The native ordinary logout is recorded in Atlas; final PostgreSQL location still requires the next authoritative query.

This investigation keeps the published 0.13.35 Game, MapServer, DbServer, launcher, graphics and translation components unchanged in the successor application. The new native diagnostic source and workflow are a separate, explicitly nonshipping experiment. A successful diagnostic build or completed definition preload does not authorize replacing those components.

## New physical evidence

The reports are `coh-atlas-gameplay-20261013-031950.zip` and `coh-atlas-gameplay-20261013-034513.zip`; the former contains the first gameplay session and the latter the second session and return travel. The `032001` archive is a separate setup operation. Full report attribution and saved-state analysis belong to the physical report evidence, not this source investigation.

These are intervals between native console records, not whole launcher operation times. Native process observer timing includes additional startup work outside some intervals below.

| Native interval | First session, seconds | Second session, seconds |
|---|---:|---:|
| Game: fragment shader stage | 26.259 | 40.554 |
| Game: following vertex shader stage, through loading tricks | 6.922 | 15.262 |
| Game: texture headers | 23.039 | 30.022 |
| Game: sequencer initialization | 6.294 | 9.222 |
| Game: FX initialization | 24.768 | 25.388 |
| Game: first message-store loading through all-data-loaded | 194.640 | 251.769 |
| Kings: sequencer parse announcement through relevant-folder caching | 87.544 | 96.640 |
| Kings: FX initialization | 27.822 | 40.857 |

The second session's Atlas return additionally has an 82.256-second sequencer interval, 28.682-second FX interval and 18.732-second PhysX object-creation interval. These native costs alone explain why eliminating launcher preparation cannot by itself guarantee a 30-second cold destination start. They do not explain the whole eleven-minute transfer; destination preparation and actual client arrival must be measured independently.

Several native intervals became slower on the second run despite the improved overall reopen. This is an observation, not a proven concurrency regression. CPU contention, thermal state, filesystem caching, differing overlap and other work remain possible causes. Both sessions already use overlapping startup, and the available evidence does not isolate those variables.

## Shader cache logs require correction in interpretation

The second Game console contains 249 `Compiled Cg/CgFX Shader` messages. Those messages **do not prove 249 source compilations or cache misses**.

In `Game/src/render/thread/rt_cgfx.c`, `rt_cgCreateProgramFromBuffer` calls `ReviewShaderCompileResults` for both `CG_SOURCE` and `CG_OBJECT`. That review emits the same message for a newly compiled source program and an already compiled object read from the disk cache. Both paths then call `cgGLLoadProgram`; a cached Cg object still needs driver work.

The stock shader manager enables its cache by default outside safe mode. It keys variants using compile flags and build hints, checks source-content MD5 and include files, and stores objects beneath the Wine user's local application data. The guest retains the game prefix. The current evidence does not establish whether the observed delay is source compilation, object parsing, graphics driver program loading, repeated cache-file operations, or a mixture.

The diagnostic overlay records the actual `CG_SOURCE`/`CG_OBJECT` choice, `cgCreateProgram` duration and `cgGLLoadProgram` duration separately. It preserves the exact arguments, review calls, error handling, object destruction and returned handles. `CG_OBJECT` means the Cg object path was used; it does not prove a Mesa/GPU driver cache hit. The original shader cache acceptance rules remain unchanged.

A separate source audit found that `findContentMd5Field` tests the pointer instead of the pointed-to NUL byte in its outer loop. Malformed metadata lacking a `CONTENT=` line could therefore fail to terminate. This is not established as the cause of either physical delay: both runs completed. The observer does not silently change that behavior; a repair requires its own malformed-cache and native regression coverage.

## Existing optimizations are active

The second client's texture index reports 38,986 hits and zero ordinary header reads, yet its header stage takes 30.022 seconds. The index is active; the remaining time must be separated into processing, allocation, metadata and driver-related work rather than assuming the index was unused.

The native server animation certificate also remains active. Its previously observed approximately one-second hashing work is not an explanation for an 82–97-second server sequencer interval. The client and server sequencer intervals differ substantially, and the server performs full animation attachment and final indexing. The diagnostic retains both operations and separates them from BIN freshness and decode time.

Two superficially promising source shortcuts were rejected:

- The disabled shared heap already returns immediately from `sharedHeapAcquireEx`; replacing the load mode is not justified as a fix for a long shared-memory wait.
- `FileListFind` already uses `FileListSearch`, a binary search. Its old comment describes a linear search incorrectly; rewriting it based on that comment would not remove the presumed cost.

## Executable diagnostic qualification

The isolated work is in `.github/workflows/android-native-startup-profile.yml`. It runs only on its dedicated `codex/native-startup-profile-036` research branch or explicit dispatch. The normal successor publication workflow does not build or import these native replacements.

The workflow is designed to perform the following fresh gates:

1. Authenticate unchanged public animation and source inputs. Stage the retained MapServer source, compile a control with Win32 OptDebug and persistence fixtures disabled, and record its exact native bytes before applying observations.
2. Apply the existing BIN freshness/decoder and sequencer observer to that same source tree and rebuild the diagnostic MapServer with the same compiler and configuration.
3. Stage the complete retained Game render-queue source chain, append only the Cg observer, and compile the complete diagnostic Game. Preserve the native DLL import closure.
4. Execute a real Win32 C fixture containing the extracted original and diagnostic `rt_cgCreateProgramFromBuffer` control flow. Ten source/object success, null-return, review-failure and driver-failure cases compare calls and returned handles. Cg/GPU APIs are controlled fixture boundaries; this is not a real graphics runtime test.
5. On an isolated Wine runner, prepare the complete authenticated historical provider, then run fresh control and diagnostic MapServers through the genuine native TSR definition preload. Compare definition counts, every prepared BIN's bytes and identifier files. Require normal owned-console exit and stopped-prefix proof. The diagnostic must emit valid actual freshness, decoder, sequencer postprocess and finalization rows.

The paired native preload does not start PostgreSQL, open player data, connect a character, load Atlas/Kings collision worlds, or exercise the diagnostic Game. Its report explicitly keeps those claims false. A genuine preload result advances beyond a compiled host prototype while still leaving full world and graphics acceptance outstanding.

At source preparation, 24 host tests passed across the existing native profiler, new Cg observer and strict observation-admission tests. The complete retained Game source chain was staged and its original source validators passed after adding the Cg observer. Native Windows compilation and Wine execution were pending at that checkpoint; their eventual source commit, workflow result and artifact identities must be recorded separately. A failed or unfinished native workflow must remain failed or unfinished in the final handoff.

The observation headers use stack records and bounded static counters: at most 256 rows per MapServer translation unit and 1,024 Cg rows. There are no new explicit heap allocations or asset reads. Formatted console output can still have CRT/logging overhead, which has not been measured on Thor. Invalid clocks fail observation admission. Diagnostic tokens identify groups; they are not content hashes or cache authority.

## Native optimization order after measured decomposition

1. **Shader program path:** determine source/object counts and create-versus-driver time. Preserve source, compiler, GPU/driver and option identity for any subsequent reusable cache. Do not remove shader variants or change graphics quality to satisfy an apparent loading target.
2. **Server sequencer load:** compare freshness, binary decode, animation attachment and finalization. Target the largest measured component, retaining the complete animation payload, certified validation and base-skeleton relationships.
3. **Per-BIN provider authority:** bind the opened BIN, schema/defines, native consumer, ordered provider roots/PIGs, all effective source dependencies and absence checks to an immutable generation. Existing bounded-anchor receipts do not establish that complete authority. Unknown or changed inputs must retain the stock freshness and text fallback path. Globally forcing production mode remains prohibited.
4. **Remaining client work:** measure texture-header processing despite valid index hits, group-library initialization and repeated FX initialization. Require actual client rendering parity before shipping a native replacement.
5. **Collision reuse:** the Atlas PhysX interval is now 18.732 seconds, so retain the owned-stream investigation and measure exact SDK/geometry/cooking identity, bounded memory and both-world parity. It remains smaller than the server sequencer work and cannot explain the full transfer.

The source already supports on-demand MapServers through the DbServer launcher and retains owned destinations during a session. An already resident destination can avoid a new process's common initialization; warm filesystem cache alone cannot. Stock TSR preload is not a proven process-cloning mechanism. No separate dynamic-map engine, unsafe cross-session residency, global freshness bypass, or unqualified native replacement is introduced by this investigation.


## Recovered completed native result after publication

The original Windows compilation succeeded in job `115126749610` of run `38345782437`, source `da5cf809925d9d91e029a117d8be184af03db2b6`; the whole workflow was cancelled before Wine execution after a Windows/POSIX receipt-path mismatch. Its successful original artifact was retained and recovered exactly; it was not rebuilt. A strict legacy adapter preserves every original member and producer identity. Subsequent run `38348218236` failed the provider-module binding before native launch; `38348835899` ran the control then failed the BIN-immutability gate. Run `38350025346` ran both real native preloads but still failed because 18 original BINs regenerated. Equal resulting output was not relabelled unchanged.

The Map-only metadata candidate was built successfully at `47e40d4d586d29e273e31ed4d0d51d160832b89d` in run `38350813669`, job `115142552789`. Original candidate artifact `11790609618` ZIP SHA-256 is `69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab`; candidate MapServer SHA-256 is `5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6`. It invokes the ordinary native animation metadata tree request before individual sequencer attachment lookups, with default-off opt-in and stock schema/date/decode/text fallback intact. It does not load animation payloads early or establish new cache authority.

The completed paired reuse lane at `9454e7892ac81cf4503fd8ad961dc36c27cfc152` (tree `c3d1400216e5b170c4c90c2c75c007387014ca21`) passed in [run 38352862725](https://github.com/Russianranger/coh-android/actions/runs/38352862725). It performed one explicit native fixture generation, then fresh observed-control and candidate consumers. Original producer inputs and timestamp-dependent dependency envelopes were authenticated; generated outputs retained exact schema/body, source-date and identifier proofs. The former failed fixture remained failed.

| Actual host phase | Observed baseline | Metadata candidate |
|---|---:|---:|
| Whole native preload | 18.185 s | 14.634 s |
| Sequencer total | 6.570165 s | 1.367097 s |
| Combined move validation/animation attachment | 6.018023 s | 0.662457 s |

The earlier stock generation took 18.550 s. The one metadata request took approximately 0.113 s. All 191 generated BIN inventories, 12 identifier files, 129 ordered decoder/sequencer decisions and 125 ordered freshness outcomes matched. The full provider contained 176,422 leaves / 3,484,837,198 bytes. Native definition counts were preserved. Recovery artifact `11791389599`, ZIP 281,739 bytes, SHA-256 `5a5bf01b901e5c5398bb42f07e4c1737ac8b13ee90e90fb297ca01cd08dfa34b`. The actual report SHA-256 is `a84aa918e89a8e4f60be80fc26ccd2960cffcac80c79ddf38d15619ffff5dfb7`.

This is one ordered host pair, preceded by complete hashing that warms the filesystem. It proves a useful native metadata optimization under that fixture; it does not establish Thor savings, new world entry, collision behavior, graphics or RAM parity. RSS/PSS was not collected in that lane. FolderCache allocates node chunks and string keys, so memory is not assumed free. Current .36 physical client/server costs and both-world/native-client qualification are being handled in the .37 continuation.
