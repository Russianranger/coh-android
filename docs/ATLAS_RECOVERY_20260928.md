# Atlas continuation recovery, 2026-09-28

The continuation checkout was recovered from `18522cada866d059ef54f42e60aadf15f5a23a7b`.
Its last game attempt, run `36375412599`, failed a 90-second readiness query
after Atlas reached `Retrieving AutoCommands`. It did not start character testing.
The earlier workspace reported `409 environment_offline`; local execution is
available in this recovery session.

New writes appeared in the old checkout during recovery. To preserve that work,
this investigation uses the separate branch `codex/atlas-recovery-20260928`.
The continuation branch independently added an owned PE32 stack observer at
`324823be6ca9713bdc60446eb31596004ff6286a`; its run is `36416020268`.
Do not overwrite or force-update that branch with this recovery branch.

## Recovery changes

- `5de3f78f1074059b68510a62c02d0b4f84786f6d` adds failure-only Wine debugger
  captures for the three expected game processes in the fresh, exclusively
  locked prefix. It records bounded thread stacks, private network socket
  tables, and the last SQL text for the disposable game's sessions, before
  cleanup. The original query still fails and normal cleanup remains required.
  Game binaries, normal execution and acceptance criteria are unchanged.
- All 63 game tooling tests passed locally and on the hosted runner. The first
  hosted Windows bridge build also passed.
- Run `36415754123` failed **before guest execution**: the pinned Samba talloc
  source download timed out while building native PRoot. There is no game
  runtime report for this run, so it is not a new Atlas runtime failure.
- `3dc466764252355ead31d19729ae8c5efb8ca510` adds three bounded transport attempts
  that discard partial downloads and preserve the original mandatory source
  digest and size limits. Hash mismatches and permanent HTTP errors fail.
  Three focused download regressions passed. The Atlas workflow now watches
  its PRoot build dependency.

## Active qualification

[Run 36416446409](https://github.com/Russianranger/coh-android/actions/runs/36416446409)
tests `3dc466764252355ead31d19729ae8c5efb8ca510`.
At this checkpoint its tooling and Windows bridge jobs passed; ARM64 runtime
qualification is pending. Inspect its terminal result and artifact before
starting another runtime attempt. The new observation is stored in
`game-runtime-report.json` under `game_failure_inspection` if a query fails.

The companion Android workflow is `36416446231`; it rebuilds existing 0.1.5
diagnostics and does not add a game launch feature. Local broad tests encountered
two `/proc` permission errors in process-ownership tests; hosted tooling passed
all 127 pre-existing tests on the preceding recovery commit. Do not weaken the
production ownership checks to accommodate the local execution sandbox.

An independently verified source fallback is available in accepted run
`36364550345`, artifact `10946592550` (`coh-proot-android-source-and-build`).
The artifact is 1,162,455 bytes, SHA-256
`ff12b5d7fca65434a5bb6d76e35dafd5f956e10d492086810cb3ca449db7baeb`.
Inside `proot-corresponding-sources.tar.gz`, `sources/talloc-2.4.3.tar.gz`
is exactly 684,092 bytes, SHA-256
`dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd`.
Those inner bytes were recovered and verified locally. The existing build
script accepts them through `--talloc-archive` without changing source inputs.

The installed, accepted Thor 0.1.5 APK remains the device baseline. Atlas
character persistence, Android game listener binding and a game APK remain
unqualified. Diagnose the live wait before altering game source or deadlines.
