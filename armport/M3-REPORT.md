# M3 report: incomplete, implementation review requested

Updated 2026-10-24. Draft PR #6 targets COH-ArmPort. This is an implementation
review checkpoint, not a claim that M3 is complete or ready to merge.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run [39960894368](https://github.com/Russianranger/coh-android/actions/runs/39960894368), attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Accepted in Claude review 5635319013. |
| Rendered Atlas screenshot | Not met. Run [40054327137](https://github.com/Russianranger/coh-android/actions/runs/40054327137), server-run 120756731269, ended with world_rendered=false and still_connected=false. Its artifact has the access-level QA notice trace and a modal on the loading screen. The bounded acknowledgement fix is being tested in [40087788009](https://github.com/Russianranger/coh-android/actions/runs/40087788009) at 563e49ac; no rendering pass is inferred from the fix. |
| All supplied packets through original receivers | Cursor/ACK stage passed in [40087788115](https://github.com/Russianranger/coh-android/actions/runs/40087788115), head 563e49ac: ARM64 job 120854188812, i686 job 120854188725. Each target executes ID1 twice and ID31 once; each execution reports 117 exact cursors, ACK IDs [1,2], and matching native INITIAL command boundaries. |
| Full deterministic state comparison | Not met. Patch 0059 and replay/state.c now emit explicitly partial snapshots. CI [40091320504](https://github.com/Russianranger/coh-android/actions/runs/40091320504), head 1e6952ed, fails in the first snapshot formatter after INITIAL cursor/ACK. The corrected formatter has passed both local links and four preprocessing controls; rerun pending. Full entity/player/tail coverage is still incomplete. |
| Independent native INITIAL comparison | Command boundaries passed in 40087788115. Four additional recorded fields are checked by the new observer harness: selected entity index/type and costume bodytype/part count. That subset is not full native INITIAL equivalence; see replay/fixtures/native-initial-entity.json and replay/README.md. |
| Final milestone approval | Pending. Claude review [5637131418](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5637131418) reviewed 443f1b73 and requested changes. Its replay P2 fix is now integrated; new code and final evidence still need review. |

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
canonicalize the three fields agreed in review 5635783793, only when equal
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
state comparison is still unqualified.

## Next exits

Inspect the current Atlas run and its actual image; fix any remaining load
failure. Complete and execute full deterministic state coverage, retaining
the agreed literal and sensitivity checks plus independent native evidence.
Then update this report, obtain Claude's milestone review and the user's merge
approval, and merge with a merge commit. M4 work is on armport/m4-runtime;
its startup/interactive results do not waive any M3 requirement.
