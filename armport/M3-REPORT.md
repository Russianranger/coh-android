# M3 report: incomplete, implementation review requested

Updated 2026-10-24. Draft PR #6 targets COH-ArmPort. This is an implementation
review checkpoint, not a claim that M3 is complete or ready to merge.

## Review 5638821870: corrected coverage and loader evidence

Code `7a91b34d956a115940cd4e9c5a58b50415110a71` runs
[build/Atlas 40111054496](https://github.com/Russianranger/coh-android/actions/runs/40111054496)
and [replay 40111054487](https://github.com/Russianranger/coh-android/actions/runs/40111054487).
The PR integration adds only these CI links over that code; execution is pending.

Claude's [review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638821870)
confirms the accepted phase rule implementation and 0064's VBO correction;
it does not approve a milestone or merge.

Run [40105902494](https://github.com/Russianranger/coh-android/actions/runs/40105902494)
fails on both targets with 541 dispatch errors: 179 geometry/model reports,
360 custom-texture reports and two mission-room reports. All 117 pairs exist.
Run [40106727443](https://github.com/Russianranger/coh-android/actions/runs/40106727443)
repeats the failure. Comparison job 120915264128 has 133,392 shared literal
texts, no architecture-only texts and no count differences. Its downloaded
artifact 12565955691 matches SHA-256
`1def01e816b3ed6bdac9cb9ab937a6586aba61aba50e0c5f557330a58ef16310`.
All 45 geometry paths and 135 texture names in the retained dispatch evidence
are absent from both staged runtimes. i686 is no longer pending.

The previous manifest scan was wrong: it did not decode gzip+base64 manifests.
`reviewed_asset_coverage.py` verifies both compressed and decoded identities,
then resolves exact geometry paths and texture candidates. Against these same
missing files, its retained `evidence/m3-reviewed-file-selection.json` selects:

| Reviewed archive | Files selected | Bytes |
|---|---:|---:|
| client-visual-assets, 0.13.10 | 142 | 15,334,280 |
| character-avatar-defaults | 11 | 1,882,288 |
| zones-world-supplement | 13 | 776,315 |

Command: `python3 armport/scripts/reviewed_asset_coverage.py --evidence
armport/evidence/m3-dispatch-errors-40105902494.json --output
armport/evidence/m3-reviewed-file-selection.json`. It reports zero ambiguous
candidates and **seven uncovered geometry files plus seven texture names**.
The earlier 37/119 figures are superseded. Every selected texture resolves to
one exact path and hash across reviewed sources; ambiguous stems fail staging.

CI retrieves the existing visual artifact from 37249488856 and zone resource
artifact from 38112251836. Archive bytes/SHA-256, complete inventories and each
selected file are verified before staging. The 166-file/17,992,883-byte result
is checked again after retrieval and merged with strict checks against all
earlier data layers. The selected archive is retained for 90 days. No original
pigg fetch is made. Local staging verified the 153 visual/default files;
zone donor execution and the new replay are pending CI.

Patch 0065 adds a separate numeric thread ID to isolated records; literal error
text and counts remain unchanged. After dispatch 116, the driver runs the
original geometry and texture completion functions inside a mandatory paired
drain window. Errors between dispatches also count as dispatch errors, so late
APCs cannot escape simply by falling between markers. This extra driver step
is not a captured packet or a change to original receive logic. Patch 0066
logs a NULL grid tracker, its ID/entries and its parent's group name if available;
the original assertion/fault stays intact. No NULL bypass is added.

Local validation: `python3 -m unittest discover -s armport/tests -p 'test_*.py'`
passes 66 tests, including malformed drain markers, delayed errors, missing
thread IDs, compressed-manifest corruption and conflicting file pins. Both
ARM64 and i686 OptDebug Game links pass with `CMAKE_BUILD_PARALLEL_LEVEL=2`
(`review-round7-arm-build.log`, `review-round7-i686-build.log`). YAML parsing and
`git diff --check` pass. Runtime replay/Atlas evidence is still required.

Two explicit decisions remain: fetching the 14 uncovered files from original
pigg archives, and allowing only handled startup RPC code 6ba before map.start.
Neither is implemented or assumed approved. M3 still lacks full state coverage,
accepted replay and a rendered/connected Atlas screenshot.

M4 run [40106299491](https://github.com/Russianranger/coh-android/actions/runs/40106299491)
passes guest boot but fails creation with PC 0x14007457c reading
0x0000010000000010. Exact executable hash
`0e82dd6656a91e0e09eadb2a685de9c1dfb59e7573f22f6fa6d04e9c4dcf0844`
symbolizes to searchPowerCustomizations, power_customization.c:159 (invalid
search key). M4 diagnostic head b9cf89cb enables Wine SEH registers/caller
logging in [40110421624](https://github.com/Russianranger/coh-android/actions/runs/40110421624).
The cause is not yet established; all 23 M4 client host tests pass. Neither
milestone is complete and no APK signing/Thor test is requested.

## Review 5638651994 and the accepted error split

The [user decision 6385679120](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6385679120)
on 2026-10-24 supersedes the earlier process-wide zero-game-error rule below.
All 117 dispatch windows must have zero errors; indexed begin/end records are
written in the isolated trace around original receive, ACK and snapshot work.
Missing, nested, unclosed or misindexed windows fail. Game-run Wine exceptions,
stdio assertions, fatals and log-write failures still fail. Error/fatal marker
counts must match between stdio and the isolated trace, including partial loss.
All six startup/load error inventories must match literally, with counts, across
ARM64/i686, repeats and synthetic IDs. No error normalization is accepted.
Atlas inventories startup/load and rejects post-load errors, incomplete evidence,
Wine exceptions and blocking dialogs; no error dialog is auto-acknowledged.

Run [40100355275](https://github.com/Russianranger/coh-android/actions/runs/40100355275)
at efc716bb still fails the old process-wide rule on both targets. Diagnostic job
120896348621 reports 183,269 occurrences per target, 133,392 shared literal keys,
zero architecture-only keys and 45 shared absent geometry paths. This confirms
patch 0062's deterministic spellings; it is not a replay/milestone pass.
The same counts were recorded in run 40099922039 at 023fd0dd.

Classification of that retained ARM64 inventory with `client_errors.error_class`
(command output, 2026-10-24):

| CI data/environment gap class | Occurrences |
|---|---:|
| Deleted symbolic group reference | 22,290 |
| Missing root geometry/model | 9,887 |
| Geometry file or model | 179 |
| Custom costume texture | 80,023 |
| Player costume texture | 65,317 |
| Texture trick | 5,156 |
| Material texture | 412 |
| DirectSound unavailable | 1 |
| Loading-screen match | 1 |
| Parser input | 1 |
| Mission room marker | 2 |

The new diagnostic resolves named textures case-insensitively under the actual
staged texture_library, recording paths, sizes and hashes. It separately retains
symbolic group references and phase/class counts. Only a shared error's file
absent from both actual runtimes is a missing-file candidate; a missing model in
an existing geometry file is not. Group references alone do not establish file
absence. No new data is added. Existing startup evidence predates phase markers;
new CI is required for phase attribution and the full texture lookup.

Review nits: patch 0062 now explains the optional Appearance fields at the edit;
supplement artifact retention is restored for 90 days under the existing public
upload authorization; Atlas notices include trace_record_count.

### Runtime fixes and remaining crashes

Run [40100355259](https://github.com/Russianranger/coh-android/actions/runs/40100355259)
passes both builds, libraries and login boot, including original/patched grid
controls under Wine. However server-run 120893845364 still faults at
0x1400a4ff4, groupGridActivate (groupgrid.c:96), reading NULL+0x88.
Patch 0063 repairs genuine pointer loss but has not resolved this Atlas fault.
The remaining NULL definition/lifecycle cause must be investigated; no bypass
is added and no rendered Atlas is claimed.

M4 run [40098262167](https://github.com/Russianranger/coh-android/actions/runs/40098262167)
at ddceae53 passes startup but crashes during character creation. Exact client
SHA256 0392424f466ceb6cbcb31d6c40252eace3570319db071369711ef35b74a6a00f,
`llvm-symbolizer --obj=CityOfHeroes.exe 0x140231a94`: createVboDirect,
rt_model_cache.c:79:41. The producer stores a native pointer then overwrites
its upper four bytes with TexID at offset four; the consumer uses that same
four-byte header. Patch 0064 changes both offsets and allocation to sizeof(VBO*).
The original 32-bit layout stays four bytes. No rendering logic is replaced.

Local validation commands (2026-10-24):
- `python3 -m unittest discover -s armport/tests -p 'test_*.py'`: 63 tests OK
  (review-round6-tests.log); window/order/error/lost-record negatives and
  literal startup-inventory/count differences are covered.
- `ASAN_OPTIONS=detect_leaks=0 python3 armport/tests/vbo_header.py --source
  upstream/ouroboros --expect-full-width 0`: allocation=0, payload=0.
  Patched-source control with --expect-full-width 1: allocation=1, payload=1.
  Both exit 0. ASan/UBSan active; leak detection unavailable in the local tracer.
  CI additionally executes both controls under ARM64 Wine.
- Both OptDebug Game links: [103/103], exit 0, two compiler processes;
  review-round6-arm-build.log and review-round6-i686-build.log.
- M4 `python3 -m unittest discover -s armport/tests -p 'test_client*.py'`:
  23 tests OK (m4-round4-tests.log), including data byte/time metrics and bounded
  guest crash notices. Cleanup remains fail-closed. M4 must retry with 0064.

## Earlier review follow-up (5638301654; superseded where noted)

Claude verified the previous corrections at 045fe9aad, then requested full
unmixed errors, same-commit ARM64/i686 data-gap classification, and runtime
supplement collision checks. Code 0b42f7cf implements those corrections.
Run [40097455262](https://github.com/Russianranger/coh-android/actions/runs/40097455262)
fails strict replay on both targets: each has 183,269 complete game errors.
The diagnostic comparison job 120887913787 succeeds; it is not replay success.
It reports 132,393 shared literal keys, 1,020 ARM64-only spellings and 999
i686-only spellings. Both actual staged runtimes lack the same 45 named
geometry paths. No new costume assets have been added.

The downloaded comparison artifact 12561139952 matches API SHA256
8c971df69594458d9b18ce2b5e16685c8c47a84b1ba3d5d9c873bd0a519bcd77.
A local diagnostic that casefolds the full texts produces identical dictionaries:
133,341 keys, 183,269 occurrences, zero differing counts. Acceptance remains
literal and zero-error. Source inspection found an uninitialized optional
costumeFilePrefix in costumeVerifyTextures' dummy Appearance, used by
determineTextureNames to choose uppercase B versus the data's lowercase b.
Patch 0062 zero-initializes that structure, preserving the selected bodytype.
Both OptDebug links pass ([8/8]); run
[40099922039](https://github.com/Russianranger/coh-android/actions/runs/40099922039)
at 023fd0dd tests whether this explains the architecture-only spellings.
That result is still required; casefolding does not prove source correctness.

A local manifest scan finds five of the 45 geometry paths in the reviewed
character-avatar-defaults manifest and three in zones-world-supplement; 37
have no matching entry in assets/*manifest.json. The 45-path list is not a
complete inventory of every missing texture/model. Only shared errors and
actual absent files can justify additions, from already reviewed pinned
sources with per-file hashes. Any new data source needs the user's approval.

Patch 0061 adds the full JSONL trace on a dedicated locked append handle and
corrects i686 stdio routing. Strict replay rejects missing/malformed trace,
error/fatal records, stdio assertions, and log-write failures. The independent
error-comparison job checks source identity and actual-runtime file hashes.
The earlier i686 run 40094942235 lacked client-stdio.txt; the new run supplies
complete evidence on both targets. Both earlier real handled-SEH controls pass.
No decoder, dialog-acknowledgement or zero-error rule is loosened.

The Atlas stage mechanically verifies all 2,877 retained hashes and sizes
against the repository's reviewed 2,904-file manifest. Runtime staging checks
case-insensitive collisions against every earlier layer, including shadowed
files; differing bytes fail before copying. The second public supplement
upload is removed: future runs use cache and the existing pinned donor.
Previously uploaded artifacts have not been deleted.

### Atlas crash and pointer correction

Run [40094942248](https://github.com/Russianranger/coh-android/actions/runs/40094942248)
at 7fb7c692 fails server-run 120877721069. The original client exits 5, with
an access violation reading 0x88 at 0x1400a4da4 after map.finish.begin.
The final screenshot is black and the database never confirms this client's
Atlas connection. QA-notice search/acknowledgement was not reached; the
previous modal is not established as this run's failure.

Evidence artifact 12562347411 matches API SHA256
8aa29fecadec100f6fdc6ade178f1925aa89320a4a68b3bd27591d010f8f6403.
The exact Release archive 12560726582 matches
e87a4c98b28fa0497607196da2c765566c50ca9b5817a845c520ebec87fbd9a7.
`llvm-symbolizer --obj=CityOfHeroes.exe 0x1400A4DA4` reports groupGridActivate,
groupgrid.c:96:14. Disassembly loads def from the retrieved tracker and faults
at def+0x88. Source inspection finds grid entries, insertion and collision
lookup narrowing pointers to U32, plus an int temporary in sphere lookup.
Patch 0063 preserves uintptr_t throughout storage, removal indices and both
lookup paths. Small numeric node IDs and the low-bit group tag are preserved.
It adds no NULL bypass or missing-geometry allowance.

`grid_pointers.py` runs the actual grid insertion/removal and both lookup
bodies with allocator/geometry adapters. Opaque addresses above 4 GB are never
dereferenced. Original source returns storage=0, sphere=0, collision=0,
distinct=0; patched source returns all four as 1. Two high addresses with
identical low bits must remain distinct. Both generated controls compile for
ARM64 Windows; the workflow also executes them under the pinned Wine.
Actual Atlas execution after this correction remains required.

Local validation on 2026-10-24:
- `python3 -m unittest discover -s armport/tests -v`: 57 tests, OK.
- `python3 armport/tests/grid_pointers.py --source ../patchwork-active/src
  --expect-full-width 1` and the original-source negative control: exit 0.
- Both OptDebug Game builds use CMAKE_BUILD_PARALLEL_LEVEL=2. Patch 0062
  links both targets; patch 0063 also links both targets ([99/99], exit 0).
- The standalone armport_zone_trace concurrent test links for ARM64. It checks
  64 complete 8,191-byte messages from four threads; Wine execution is required.
- `stage_atlas_supplement.py stage --source ../recovered-atlas --output
  ../reviewed-atlas-data`: 2,877 files / 309,655,940 bytes, matching reviewed
  manifest SHA256 204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86.
- Workflow YAML parses; git diff --check passes; upstream/ has no changes.

M4 continues independently: run 40095316035 reaches the actual ARM64 client,
then faults at 0x140204184. The exact retained executable resolves that address
to texResetTrickBasedParametersComposite, tex.c:1081:61 (generic texture NULL).
Its log records failures opening reviewed textures. M4 branch ddceae53 makes
private regular copies instead of calling link() inside --link2symlink PRoot,
and captures client evidence from the ARM64 directory. The 22 app tests pass;
run 40098262167 must confirm the staging hypothesis. No M4 pass is claimed.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run [39960894368](https://github.com/Russianranger/coh-android/actions/runs/39960894368), attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Accepted in Claude review 5635319013. |
| Rendered Atlas screenshot | Not met. Run [40054327137](https://github.com/Russianranger/coh-android/actions/runs/40054327137), server-run 120756731269, ended with world_rendered=false and still_connected=false. Its artifact has the access-level QA notice trace and a modal on the loading screen. Run [40087788009](https://github.com/Russianranger/coh-android/actions/runs/40087788009) at 563e49ac also fails: world_rendered=false, zero QA-notice actions, 1,507 seconds loading. Its inspected screen remains white with a blank modal area; the pending exact notice is still in stdio. |
| All supplied packets through original receivers | Cursor/ACK stage passed in [40087788115](https://github.com/Russianranger/coh-android/actions/runs/40087788115), head 563e49ac: ARM64 job 120854188812, i686 job 120854188725. Each target executes ID1 twice and ID31 once; each execution reports 117 exact cursors, ACK IDs [1,2], and matching native INITIAL command boundaries. |
| Full deterministic state comparison | Not met. Patch 0059 and replay/state.c now emit explicitly partial snapshots. CI [40091320504](https://github.com/Russianranger/coh-android/actions/runs/40091320504), head 1e6952ed, fails in the first snapshot formatter after INITIAL cursor/ACK. The corrected formatter has passed both local links and four preprocessing controls; rerun [40092531364](https://github.com/Russianranger/coh-android/actions/runs/40092531364) at 0296f2fb writes 117 ARM64 snapshots but rejects the costume subset because the validator confused 60 allocated slots with 28 logical parts. The current correction compares num_parts; full state remains incomplete. Full entity/player/tail coverage is still incomplete. |
| Independent native INITIAL comparison | Command boundaries passed in 40087788115. Four additional recorded fields are checked by the new observer harness: selected entity index/type and costume bodytype/part count. That subset is not full native INITIAL equivalence; see replay/fixtures/native-initial-entity.json and replay/README.md. |
| Final milestone approval | Pending. Claude implementation review [5638301654](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638301654) verified prior fixes and requested the follow-up above. Its new corrections require execution and review; this is not milestone approval. |

## Earlier implementation changes

The last review identified a P2: accepting a plausible receiver transcript
without examining the game Wine log. The integrated check_wine_output now
rejects handled/unhandled exception dispatches, fatal Wine and loader reports;
bootstrap/registry logs are separate. Counterexample tests in
`test_receiver_evidence.py` supply complete transcripts plus fatal/handled-SEH
logs, missing logs and oversized evidence. The exact-head cursor run
40087788115 passes with this rejection enabled.

The first original replay failed because earlier handshake initialization
was missing, not because an alternative decoder was required. The driver
now installs the 35 original command-shortcut names in original shared-table
order and initializes the original static Atlas map list. Both prerequisites
are logged and documented in `replay/README.md`. Patch 0058 records original
command boundaries. Run 40087788115 establishes all 117 dispatches after
these changes; it does not establish complete state equivalence.

The Atlas harness recognizes only the exact traced access-level QA notice.
It requires one mapped client PID and one visible Program Error window for
that PID, records before/after captures, and attempts acknowledgement at most
three times. Unknown/fatal alerts are not acknowledged. The input operation
does not count as a rendered frame. Existing original load/READY markers,
client-cropped Atlas text, two nonblank/non-loading frames, database connection
and cleanup requirements remain in force. Human screenshot inspection is
still required. The tests are in `test_qa_notice.py` and `test_zone_frame.py`.

Patch 0059 was exported with `patchwork.py`. Its read-only observers retain
accepted wire quaternion components before normalization and expose actual
delete history in server-index order. `state.c` is inactive without replay
initialization. It writes bounded JSON and SHA-256 after each completed
receiver dispatch. Identity, raw network position/orientation, ordering IDs,
selected costume parts, selected character scalar/attribute fields and one
player lifecycle ID are included. Full power/inventory/player, team/task/UI,
dynamic-group and further costume fields remain missing. All completion flags
are false. See `replay/README.md` for coverage and explicit exclusions.

The comparison checks input/commit identity and snapshot hashes, then compares
same-ID repeats and ARM64/i686 bytes literally. Only ID1-versus-ID31 checks
canonicalize the five named fields agreed in reviews 5635783793/5638209554, only when equal
to that run's synthetic INITIAL ID; all other values stay literal. A mismatch
fails the partial stage and records field paths. A passing partial stage
cannot complete M3.

## Validation and limits

Commands executed on 2026-10-24 for the observer implementation:

- `python3 -m unittest discover -s armport/tests -v`: 41 tests, OK. Includes
  authenticated but changed final state, wrong commit, missing/tampered state,
  path substitution, native subset mismatch, Wine exceptions and frame checks.
- `CMAKE_BUILD_PARALLEL_LEVEL=2 cmake --build ../build-arm-new --target Game`
  and the same command for `../build-i686-new`: both exit 0; final output
  `[8/8] Linking CXX executable bin/CityOfHeroes.exe`. Both are OptDebug.
- PyYAML parsed armport-reference.yml; `git diff --check` passed. STATUS has
  40 lines. `git diff HEAD -- upstream/ native-android/ android/` is empty
  for this replay change. Source modifications are patchwork exports.

The i686 reference uses the same ArmPort patches and clang, with SSE2 math.
It isolates architecture/pointer-width differences, not shared source/compiler
mistakes. Both targets disable NOVODEX; i686 retains real CPUID while ARM64
reports no SSE. Reference-only patch 0054 removes three local SEH handlers;
any resulting fault fails the run, never establishes equivalent recovery.
See `notes/M3-REPLAY-PLAN.md` for the agreed scope and wire-value rules.

Earlier fixes and diagnostic evidence remain in `notes/64BIT-AUDIT.md`,
`notes/M3-LOAD-STALL.md` and `notes/WORKER-QUEUE.md`. In particular, run
40035482170 demonstrates the independently reproduced worker wake/publication
fix; it is not an Atlas rendering result. Run 40042636088 validates CRT trace
writes and the socketless sink, not world loading. No ACK/READY grammar or
original receive decoder was replaced.

The first observer execution exposed the original ARRAY_SIZE_CHECKED printf
macros on a heap-buffer offset (40091320504, quick_sprintf.c:101). The writer
now explicitly uses bounded CRT formatting. Actual ARM64/i686 preprocessing
and negative controls verify the correction; both updated links pass. See
replay/README.md for the artifact identity and exact command. Runtime
state comparison is still unqualified. The corrected code is tested by
40092531364 at 0296f2fb fails the native costume count check described above.

## Next exits

Inspect the current Atlas run and its actual image; fix any remaining load
failure. Complete and execute full deterministic state coverage, retaining
the agreed literal and sensitivity checks plus independent native evidence.
Then update this report, obtain Claude's milestone review and the user's merge
approval, and merge with a merge commit. M4 work is on armport/m4-runtime;
its startup/interactive results do not waive any M3 requirement.

## Review 5638209554 corrections and data evidence

- H1: sensitivity-only normalization now explicitly includes pkt_id_pos[]
  and pkt_id_qrot[]; same-ID/cross-architecture bytes remain exact.
- M1: receiver.c also unbinds CRT macros; actual preprocessing and negative
  controls cover both observer units on both architectures.
- M3: patch 0060 enables identical game-error tracing on i686; both targets
  require zero client.error/assert reports. Complete recorded multiline
  texts and counts go into client-errors.json, including Atlas artifacts.
- M4: per-run and partial comparison summaries emit Actions notices.
- L1/L2: retain pinned bins/Cg in a run-keyed cache and 90-day artifacts;
  add a real handled-SEH Wine control, separately logged from the game.

M2 investigation: parsing all 16,721 entries of
assets/reference-inputs-manifest.json with casefold searches finds zero
matches for tickertape_talos_island or arch_ent_wall_brick_01. In the verified
40054327137 artifact, client_errors.inventory reports 12,713 errors and
11,063 distinct recorded texts, including twice: `TexSwap Warning: was unable
to find source texture 'tickertape_TALOS_ISLAND' to swap (does not exist in
texture_library/)`. This is the source-texture warning in texCheckSwapList,
not a failed destination texFind call. It means no matching source was
swapped; the name comparison in texCheckForSceneSwaps is stricmp. The absent
case-insensitive manifest entry establishes a reviewed-bundle data gap; it
does not prove that adding this one asset will complete loading. The QA
notice/error pop-ups are specific to the fake-auth access-level-9 account.
No error dialog is automatically acknowledged.

Run 40092531364 artifact 12559387913 (SHA256
da15257d2fd11d850ffc08a888d532f27d7f336582c597c5361653f2632b70bf)
contains 184,514 game error records, 137,888 legacy inventory keys (not reliable distinct messages), in
id1-a/client-stdio.txt. `client_errors.inventory` collected mixed/truncated stdio text;
examples include missing Arch_Ent_Wall_Brick_01 and deleted geometry references.
The new strict validator will reject these, even with exact dispatch cursors.
The data errors must be resolved before state equivalence is accepted.

Local review validation, 2026-10-24: 46 host tests pass; ARM64 and i686
OptDebug Game links exit 0 with `[15/15] Linking CXX executable
bin/CityOfHeroes.exe`; current/negative preprocessing controls pass for
receiver.c and state.c on both targets. seh-control.c links for both targets.
Workflow YAML parses; git diff --check passes. Runtime controls are pending.
M4 branch 723bbc32 addresses the separate missing client_visual_assets import
from run 40092467628; 19 app tests pass. No M4 completion is claimed.

### Reviewed Atlas supplement and current execution

The missing texture is present in the already reviewed
assets/atlas-world-supplement-manifest.json: 22,316 bytes, SHA256
60e4fa246b6212ae882c44a0d3571bcb4ecc7d2c35f85f316fdad8a35f53b344.
The retained 0.10 APK (run 36920583713, artifact 11192425448) supplies the
original 2,877-file Atlas supplement. CI now verifies the exact APK and
embedded manifest/archive hashes, retains the archive, and adds those
original bytes to the client data for Atlas and both replay architectures.
It does not modify the server's existing data or acknowledge error dialogs.
The reviewed current 2,904-file Atlas manifest and base reference manifest
have zero overlapping paths (`casefold` missing-texture search and Python
manifest-set intersection, 2026-10-24). The 27 later material additions are
not silently substituted for the retained baseline. This is a data-gap
correction to test, not evidence that all game errors or loading are fixed.

Run 40087788009 artifact 12559808809 SHA256
68f239a459ff0cada2eafc49c375c831acce4e7ea3139a02791641768984612e
was downloaded and verified. Its final trace is the exact QA notice after
the missing source-texture warning; pending_qa_notice returns true locally,
but qa_notice_actions is empty. The next run records the exact-window search
result without widening its acceptance.

Run 40094248191 at 1e3df462 fails the newly expanded preprocessing check
before compilation because AutoGen/bones_h_ast.h has not been generated.
Commit 06296c38 moves that check after the build and before executable caching;
40094448205 tests it. Actual local incremental links and eight preprocessing
controls already passed. The supplemental data change has 50 passing host
tests, including byte identity, unexpected members, path links and refusal
to overwrite different data; production donor execution remains pending.
M4 correction 723bbc32 runs in 40094077884; app sources and guest boot pass,
interactive creation/save/reopen is still running.

### Review follow-up execution, 2026-10-24

Run 40094448205 ARM64 job 120873737155 passes the real handled-SEH rejection
control (`target=arm64, rejected=true` annotation at 12:40:27 UTC), then
fails closed on 184,514 game error reports as intended. This is a validator
control/data-error result, not state equivalence. Artifact 12560234319 SHA256
0689027af7bb9e780e2e71eef7c0aff97ddaa3b40277965cc01b957e9136ce30
retains all recorded errors; the i686 side is still running.

At code 7fb7c692, new runs 40094942235 (replay) and 40094942248 (Atlas/build)
are in progress. The latter's libraries, Release and OptDebug jobs pass.
Both asset jobs recover the reviewed supplement. Downloaded artifact
12560402926 matches API SHA256
1167a7d2a36adf1a264d6007ff2f7f1106bcfef15cd6e19aa88489b16e0a2308.
`python3 armport/scripts/stage_atlas_supplement.py stage --source
../recovered-atlas --output ../reviewed-atlas-data` then verifies and stages
2,877 files / 309,655,940 bytes locally. The missing texture is 22,316 bytes
and its SHA256 equals the reviewed 60e4fa24...f53b344 pin. No rendered-frame
or error-free replay result has yet been established with this data.

M4 run 40094077884 passes boot and proceeds beyond the visual-helper failure,
then fails importing native_monorail_contract during cache ancestry checking.
Branch commit 589a015bf86dada8d1f5673cd5ca53eed91b0478 adds the cache ancestry
helpers; 20 app tests pass, including unsupported-producer rejection.
40095316035 tests it; complete interactive qualification remains pending.
