# Client startup and zoning: nonshipping follow-up

Reviewed against frozen release source `3570430cefdb15d9b239563e85cccf4d8fe6f32e`. This is a separate research-only contribution on `codex/native-client-metadata-036`. No release files, installed runtime, player data or native executables were changed by this follow-up. The accompanying prototype is a host algorithm fixture; it does not create production cache authority.

## Measured targets

Second physical report: `coh-atlas-gameplay-20261013-034513`, client console SHA-256 `d0f4598de7348e4bced088aa5a954dc6541aeba346e43ee23f3b23ae414c3eaf` (629,821 bytes).

| Target | Physical evidence | Interpretation |
| --- | --- | --- |
| Native client initial data/renderer initialization | 251.769 s, root/physical analysis boundary | Distinct from the surrounding launcher and GPU prerequisite stage. |
| Texture headers | `03:25:40.163` Loading texture headers to `03:26:10.185` Loaded texture headers: 30.022 s | All 38,986 indexed header reads hit, zero ordinary reads. The ready index precedes the `texture_library` request at `03:25:40.356`; initial index load/parse therefore occupies at most 0.193 s of this phase. |
| Guest texture-index preparation | Same report's `texture_header_index`: 12.691 s total, 12.671 s complete inventory, one inventory pass, reused header pack | Separate from the native 30.022 s. Reuse the required current inventory observations if developing a metadata envelope; adding another full guest walk would move or increase cost. |
| FX catalog | `03:27:43.690` Loading FX info to `03:28:09.078` Loaded FX info: 25.388 s | This reads `fxinfo.bin`; current output does not separate freshness scanning from native decode. It is not evidence of source reparsing or FX geometry loading. |
| Initial renderer/shaders | 55.816 s, physical analysis boundary | Existing `Compiled Cg/CgFX` messages occur for both CG_SOURCE and cached CG_OBJECT. They do not establish shader cache misses. Native agent owns the newly built diagnostic Cg observer. |
| Kings-to-Atlas client world groups | Native scene row `groups_libraries_and_definitions=41121 ms` | The largest measured child of the 55.429 s enclosing `groups_network_and_processing` phase. Do not add parent and child. |
| Kings-to-Atlas surviving FX geometry preload | Native scene row `gfx_surviving_fx_preload=12450 ms` | Separate from the startup FX catalog. Native client departure-to-ready was 76.345 s. The coarse object_library-to-Detailing-trays gap, 62.629 s, overlaps multiple phases and is not isolated object-library I/O. |

The texture and FX observations suggest metadata work as a candidate, but do not measure its fraction of the enclosing phase. None of these numbers establish a .36 speedup, a subminute client startup or 30-second zoning.

## Exact source chain and remaining work

Paths below are relative to `upstream/ouroboros`, except explicitly named patches/guest helpers.

1. `Game/src/render/tex.c:1453` still calls `fileScanAllDataDirs` before required basic/composite/trick/localized bind initialization. The shipped index patches only substitute header bytes inside `texFillInBind`. `libs/UtilitiesLib/src/utils/fileutil.c:168–264` requests the tree, then traverses FolderNodes; `FolderCache.c:1424–1478` populates an uncached dynamic tree using every configured loose root. `FolderCache.c:203–312` calls `fwFindFirstFile/fwFindNextFile`, converting timestamps and adding every file/directory. `fileWatch.c:240–306` maps those directly to Win32 FindFirstFileA/FindNextFileA. Therefore a header-cache rewrite cannot eliminate the remaining enumeration and bind work.
2. `Common/fxinfo.c:378–393` uses the full client `fxinfo.bin` through `ParserLoadFiles`. On a valid BIN, `textparser.c:2443–2451` checks freshness, decodes and returns; `fxPreloadFxInfoPreProcess` is only reached by text regeneration, not successful BIN consumption. The current repository FX source has 61,854 files and 1,719 directories, including 19,606 `.fx`, 36,263 `.part`, 5,724 `.bhvr`, 255 `.cape`, six `.txt`. These are source counts, not an authenticated on-device namespace. Native freshness requests the whole FX tree even when the current file mask is `.fx`; later behavior/cape reads can reuse the same tree. Moving the scan earlier or omitting the other extensions alone does not prove a net saving.
3. `Game/src/group/groupnetrecv.c:659–733,879–897` consumes server group files/definitions. `receiveGroupFile` first attempts `objectLibraryLoadBoundsFile(fname,checksum)` before full library loading. `Common/group/groupfilelib.c:776–826` reads the bounds BIN and verifies the server-supplied checksum before accepting it. A useful next world-load breakdown is bounds-cache hit/fail/full-load/decode counts plus `receiveDef` time. Preserve its checksum and geometry dependency semantics. Client world loading is already over the zoning goal before native server startup is counted.
4. `Common/fxinfo.c:1122–1215` traverses cape/door/flag geometry and references from every FX event; `geoLoad` deduplicates according to its existing model lifecycle. The previous discarded-scene optimization already removed the disposable preload. Skipping this surviving preload without proving model lifetime would regress rendering. No such skip is proposed.

## Why current cache formats are insufficient for native provider authority

`tools/map_startup_namespace_certificate.py` already records the missing provider authority. Preserve that fail-closed result.

* `character_server_data_cache.py` records owned generation directories/private caches and bounded immutable anchors. A source leaf can change in place without changing its parent directory mtime. This is not a complete authenticated native namespace.
* `texture_header_index.py` inventories every admitted `.texture` leaf plus parent directories, checks readonly real sources, and binds the actual Game/content/import identity. Its native pack contains path/header payload, not complete FolderCache metadata, nontexture members, root/PIG ordering or provider selection. It cannot directly populate the whole native tree.
* The actual `FolderNodeAdd` chooses between ordered roots and PIGs, case-insensitively. PIG-versus-loose one-hour timestamp handling is directional. `fileDatesEqual` is separately symmetric for freshness. These are different rules.
* `seen_in_fs` remains set even when an equal-date PIG wins over a loose file; DEVELOPMENT_DYNAMIC scanning uses it. PIG insertion does not clear an existing loose node's writeable/hidden/system flags. Dropping either detail changes behavior.
* `FileListInsert(...,date=0)` calls `fileLastChanged`; zero is not an instruction to ignore a dependency. Missing optional-prefix names and new matching files affect cache validity. Negative membership needs a complete authenticated namespace.

## Narrow next-stage implementation

Start with **metadata hydration**, keeping the entire existing BIN signature/schema CRC, FileList membership/date validation and decoder. Do not start with a freshness bypass.

1. Build one explicit metadata envelope for a bounded tree (`texture_library` or `fx`) while the existing guest performs a complete validated per-launch inventory. Retain exact current native root order, PIG list and indices, mode, ignore policy, ASCII/case behavior, path membership including empty directories, effective timestamps after native conversion, sizes, attributes, `seen_in_fs`, winning provider/index, and immutable content/source generation. Bind the exact consumer and adapter/source schema. The first stage can reuse a scan already required for authentication; it must not add a separate whole-tree cryptographic pass on every map start.
2. Prove import/provider completeness and exclusive generation ownership before any native use. Caller assertions and source archive hashes alone are insufficient if an unobserved private loose override can win. Missing authority, changed leaves, unknown private caches, root/PIG reorder, conflicts, linked/changed parents, partial manifests or unknown attributes fall back to ordinary native enumeration. Existing staged generation and texture pack identities cannot silently stand in for this authority.
3. Add a diagnostic **shadow mode** in an isolated native build: run ordinary FolderCache population, derive a full effective-node digest, hydrate a separate isolated tree from the envelope, and compare complete traversal, lookup/provider, attributes, counts, FileList memberships and optional absence. Record mismatches; do not route real Game reads through the prototype. Windows and pinned Wine must both pass on all original client Assets 1.0.0, with loose/PIG overlays and mutated negative fixtures.
4. After shadow parity, qualify native hydration of only a complete attested tree through the same `FolderNodeAdd`/hash-table interfaces. Mark that tree complete only after successful hydration; preserve callbacks and ordinary out-of-tree queries. Release the transient envelope after ingestion; use the same native nodes so there is no permanent second namespace in RAM. Cache ownership changes or any write invalidate the lease before subsequent reads. Native/client world Atlas/Kings graphics, powers, texture substitutions and collision must be requalified.
5. Only later consider **per-BIN reusable freshness proofs**: bind exact opened BIN bytes, Parse6/current schema/defines CRC/ABI, full dependency table including zero dates and generated ID sources, matching top-level set and optional absence, and the closed native effective namespace. Unknown or altered BINs run the original path. A success certificate generated from the ordinary path is not valid across an unproved source generation.

The benefit ceiling is the measured enumeration/freshness fraction, not all 30.022 + 25.388 seconds. Capture guest snapshot overhead, native ingestion/enum/bind/decode time, and peak/private working set before selecting this stage. This prototype neither estimates a device gain nor demonstrates it.

## Isolated prototype and what passed

`tools/native_client_metadata_parity.py` extracts the unchanged current `FolderNodeAdd`, `FolderNodeFind` and `fileDatesEqual` C bodies, compiles them locally, replays synthetic ordered provider observations, and serializes effective nodes. Hydration reconstructs a separate tree and compares the complete output. The adapter is source-bound to `FolderCacheAddFolderToNode` and `FolderCacheAddPig`, including their attribute differences.

The test suite has 12 tests, including 80 deterministic randomized sequences of 64 provider events, directional PIG/DST behavior, original casing, loose-presence flags, PIG attribute retention, empty directories, optional addition/deletion, provider/root order changes, identity changes, malformed bounds, source/schema changes, and payload tampering with a recomputed payload hash. A test explicitly demonstrates that unchanged metadata cannot authenticate changed source bytes; production acceptance is always false. These are actual host C algorithms with bounded I/O adapters, not full native Game/Wine/Android execution. No per-BIN freshness path is changed.

Reproduce from the repository root with Python 3 and a host C compiler:

```sh
python3 -m unittest discover -s tools -p test_native_client_metadata_parity.py -v
python3 tools/native_client_metadata_parity.py
```

The first command runs exactly these 12 tests. The second prints one example fixture's parity result; it is not another integration qualification. The script resolves source paths relative to its repository location. The source-bound receipt, fixture manifest and recorded results are in `docs/android-evidence/native-client-metadata-0.13.36-research.json`.

## Genuine retained-Game diagnostic route

The shipped Game already has `COH_CLIENT_BIN_PROFILE=1` timers for BIN open/freshness/decode. `android/guest/client_interactive_diagnostic.py:249–251` explicitly overrides this to zero for the scene profile, explaining their absence in these reports. Use a separate diagnostic launch environment after the existing producer checks; do not modify the frozen release.

Use the exact retained Game and console launcher with ordinary, nongenerator startup: `wine <retained-launcher.exe> <fresh-32-hex-session-id> <exact-CityOfHeroes.exe> <isolated-client-workdir> --character-manual`, and the current qualified `COH_CLIENT_GRAPHICS_PROFILE=performance` environment to match the physical session. The host supervisor must stop and clean up its owned processes after finite login-screen observation or diagnostic failure. Omitting the fifth mode argument is also a genuine normal startup, but the launcher then forces the standard graphics profile, so it is not an equivalent performance-profile comparison. Build the workdir through the verified complete client closure/prepared-cache/prerequisite path, including the current readonly import, exact normalized timestamps, retained animation supplements, texture index and ordinary client DLLs. The server profiling fixture is not this client closure. Supply an exclusive temporary WINEPREFIX/HOME, owned Xvfb display, TZ=UTC, pinned Wine identity and the already qualified client environment; add only BIN profiling. No physical profile, persistent PostgreSQL or THORHERO data is needed to reach the real login screen.

Record full ordinary renderer/data/main-loop completion, owner PID/window and cleanup, BIN rows and source/provider identity. Compare a second launch in the same isolated closed prefix and unchanged input generation. Software GL on CI can establish native semantics and decomposition but cannot predict Thor Cg/driver/FEX timing. Native Cg observer results must identify CG_SOURCE versus CG_OBJECT separately from driver program load.

Do not use `--generate-caches`/`-createbins` as a replacement for this comparison: it changes process priority (ABOVE_NORMAL rather than development IDLE), generation behavior, and skips renderer/final FX/ordinary world initialization. It is a distinct cache producer.

Local environment contains `cc` but no Wine/Xvfb or complete current client runtime. Genuine Game execution is therefore **pending**, coordinated with the native agent; no such test or device performance claim is reported as passed.

### Exact next execution inputs and command

The physical report pins the retained inputs as follows. The donor and package verifiers must establish the same hashes before this route is used; these observations do not replace verification.

| Input | SHA-256 |
| --- | --- |
| CityOfHeroes.exe | `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b` |
| client-launcher.exe | `b453c42876408a842a4f3b717ef3857d4f10624f02462b6e1c6ce5bcdca92159` |
| client-runtime.zip | `5636fe9b3d45c313b062ac83ba954bfb3b1b160af4aec1b34f046c8c2b421509` |
| client-caches.zip | `5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051` |
| client-prerequisites.zip | `cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e` |

Reuse `tools/android/interactive/build_client_startup_latency_apk.py download-donor --output out/research-donor.apk` and `download-donor-evidence --output out/research-donor-evidence` to obtain the exact .35 donor designated by this frozen base. Extract and verify its client assets using the retained package validators; assemble the complete worktree through `android/guest/client_startup_diagnostic.py:prepare_worktree`, with the current supplemental client assets applied as the ordinary launch does. Then call `texture_header_index.prepare` for that worktree, import identity and exact executable. Retain the returned `COH_TEXTURE_HEADER_PACK`, `COH_TEXTURE_HEADER_ID`, `COH_TEXTURE_HEADER_ROOT`, `COH_TEXTURE_DIAGNOSTIC_DEDUP` and `COH_STARTUP_DIAGNOSTIC_BOUND` environment. Its pack identity is derived from the new fixture's authenticated inventory; **do not reuse the physical report's device-path-specific identity**.

Inside a new fixture supervisor that already owns its exclusive Wine prefix, display, stdout/stderr and process group, the exact launcher command is:

```sh
env \
  COH_CLIENT_GRAPHICS_PROFILE=performance \
  COH_CLIENT_KNOWN_STRING_COPY=1 \
  COH_CLIENT_DEPENDENCY_PRELOAD=1 \
  COH_CLIENT_SCENE_PROFILE=1 \
  COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD=1 \
  COH_CLIENT_FRAME_TIMING=1 \
  COH_CLIENT_GAMEPLAY_FPS=30 \
  COH_CLIENT_BOUNDED_TEXTURE_ERRORS=1 \
  COH_CLIENT_RENDERER_ATTRIBUTION=1 \
  COH_CLIENT_RENDER_PIPELINE=0 \
  COH_CLIENT_RENDER_QUEUE=1 \
  COH_CLIENT_BIN_PROFILE=1 \
  "$COH_RESEARCH_WINE" "$COH_RESEARCH_LAUNCHER" \
  "$COH_RESEARCH_SESSION" "$COH_RESEARCH_GAME_WIN" \
  "$COH_RESEARCH_WORK_WIN" --character-manual
```

`COH_RESEARCH_SESSION` is a newly generated 32-character lowercase hexadecimal ID. `COH_RESEARCH_WINE` and `COH_RESEARCH_LAUNCHER` are absolute host paths to the verified Wine executable and retained launcher. `COH_RESEARCH_GAME_WIN` and `COH_RESEARCH_WORK_WIN` are absolute `Z:\\...` paths for the verified Game and its isolated runtime working directory; the latter contains the `data` directory, rather than naming `data` itself. The parent environment also contains the newly verified texture variables above, the exclusive WINEPREFIX, DISPLAY, TZ=UTC and runtime DLL settings. All environment flags shown except BIN profiling match the physical session's retained enabled/disabled features; authenticate their current producer contracts before enabling them. This direct launch avoids the guest scene helper resetting `COH_CLIENT_BIN_PROFILE` to zero.

Use a finite **host diagnostic** bound, for example 900 seconds to actual main-loop/login-screen readiness and a short observation, and verify process ownership and prefix shutdown when stopping. This is not a new gameplay timer and must never attach to a user's existing prefix or kill unrelated Wine processes. There is no normal-exit/login automation in this research contribution; a supervisor integration is still required. For CI software GL, record the intentional `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`, `LP_NUM_THREADS=2` environment separately from the Thor graphics path. Do not mix those timings with the physical renderer.

Remaining blockers are concrete: complete verified client asset staging; a pinned Wine/Xvfb runner with isolated ownership/cleanup; current producer-contract validation before enabling the flags; and actual ordinary Game readiness evidence. The existing server profiling fixture and synthetic C fixture do not supply these. No new Game build is required to collect BIN open/freshness/decode rows. The optional separately built Cg observer needs its own exact artifact and qualification identity and must not be presented as the retained shipping Game.
