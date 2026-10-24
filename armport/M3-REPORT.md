# M3 report: incomplete, implementation review requested

Updated 2026-10-24. Draft PR #6 targets COH-ArmPort. This is an implementation
review checkpoint, not a claim that M3 is complete or ready to merge.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run [39960894368](https://github.com/Russianranger/coh-android/actions/runs/39960894368), attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Accepted in Claude review 5635319013. |
| Rendered Atlas screenshot | Not met. Run [40054327137](https://github.com/Russianranger/coh-android/actions/runs/40054327137), server-run 120756731269, ended with world_rendered=false and still_connected=false. Its artifact has the access-level QA notice trace and a modal on the loading screen. Run [40087788009](https://github.com/Russianranger/coh-android/actions/runs/40087788009) at 563e49ac also fails: world_rendered=false, zero QA-notice actions, 1,507 seconds loading. Its inspected screen remains white with a blank modal area; the pending exact notice is still in stdio. |
| All supplied packets through original receivers | Cursor/ACK stage passed in [40087788115](https://github.com/Russianranger/coh-android/actions/runs/40087788115), head 563e49ac: ARM64 job 120854188812, i686 job 120854188725. Each target executes ID1 twice and ID31 once; each execution reports 117 exact cursors, ACK IDs [1,2], and matching native INITIAL command boundaries. |
| Full deterministic state comparison | Not met. Patch 0059 and replay/state.c now emit explicitly partial snapshots. CI [40091320504](https://github.com/Russianranger/coh-android/actions/runs/40091320504), head 1e6952ed, fails in the first snapshot formatter after INITIAL cursor/ACK. The corrected formatter has passed both local links and four preprocessing controls; rerun [40092531364](https://github.com/Russianranger/coh-android/actions/runs/40092531364) at 0296f2fb writes 117 ARM64 snapshots but rejects the costume subset because the validator confused 60 allocated slots with 28 logical parts. The current correction compares num_parts; full state remains incomplete. Full entity/player/tail coverage is still incomplete. |
| Independent native INITIAL comparison | Command boundaries passed in 40087788115. Four additional recorded fields are checked by the new observer harness: selected entity index/type and costume bodytype/part count. That subset is not full native INITIAL equivalence; see replay/fixtures/native-initial-entity.json and replay/README.md. |
| Final milestone approval | Pending. Claude implementation review [5638209554](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638209554) reviewed 49c390ada and requested H1/M1–M4. Corrections below still require execution and review; this is not milestone approval. |

## Changes since Claude's last review

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
contains 184,514 game error records, 137,888 distinct recorded texts, in
id1-a/client-stdio.txt. `client_errors.inventory` preserves multiline text;
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
