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

## Verified results and current qualification

Recovery run `36416446409` failed its 90-second Atlas readiness query. The
hash-verified raw report and analysis are in
`docs/android-evidence/game-arm64-failed-36416446409.json` and
`game-runtime-failure-36416446409.json`. Before cleanup, all 65 game SQL sessions
were idle: foreground last SQL `;`, 64 workers last SQL `COMMIT`. DbServer's
6997 listener had one pending connection and established connections had unread
request bytes. The blocked function is still unknown. All three WineDbg
attachments returned error 5 / exit 255; **no stacks were obtained**. Reviewing
pinned Wine 10.0 `programs/winedbg/winedbg.c` and `tgt_active.c` explains the
observer failure: the SysWOW64 debugger attaches, then `restart_if_wow64()`
launches a second debugger that repeats the attach. The local follow-up uses
System32 WineDbg directly; this has not yet been exercised on hosted failure. The
following fix makes that partial capture explicit rather than leaving the
inspection's top-level failure list empty. Cleanup passed.

The independent continuation run `36416020268` at `324823be6ca9713bdc60446eb31596004ff6286a`
passed Atlas readiness and its sustained observation, fresh character creation
and connection, live influence change to 12345, protocol logout, and independent
committed SQL verification. Character `TEST02279`, container 1, saved 1 Ents row,
1 Ents2 row, 7 powers and 17 costume parts with login count 1. Owned Wine shutdown
and PostgreSQL shutdown/restart passed. **Game restart then failed before
DbServer launch**, with Python `EADDRINUSE` in the port preflight. This is not a
new SQL failure or a persistence comparison failure. Raw report and analysis:
`game-arm64-first-save-36416020268.json` and `game-first-save-36416020268.json` in
`docs/android-evidence/`.

Commit `eb28fd6598502420028d171384977a5a4b67692a` fixes the TCP port preflight:
SO_REUSEADDR permits a stopped connection's TIME_WAIT; an actual listen call
still excludes an existing listener. UDP retains exclusive bind behavior.
Real socket regressions reproduce the old failure and verify rejection of live
TCP and UDP sockets. All 66 game tests passed locally. No game binaries,
ownership cleanup checks, save criteria or time limits changed.

[Run 36419952350](https://github.com/Russianranger/coh-android/actions/runs/36419952350)
passed all 66 tooling tests and the Windows bridge build, then failed the
90-second first Atlas query at 12:34 UTC. It did not exercise the restart fix.
The SQL inspection again found 65 idle sessions, and all three failed WineDbg
captures are now explicitly reported as failures with `stacks_available:false`.
Owned cleanup completed. Raw evidence and concise interpretation are in
`game-arm64-failed-36419952350.json` and `game-runtime-failure-36419952350.json`.
Companion diagnostic APK run `36419952339` passed all five jobs.
The preceding companion `36416446231` passed all five jobs, including APK,
native PostgreSQL, database runtime and client runtime. It remains diagnostic
version 0.1.5, without a game-launch feature.

An independently verified source fallback is available in accepted run
`36364550345`, artifact `10946592550` (`coh-proot-android-source-and-build`).
The artifact is 1,162,455 bytes, SHA-256
`ff12b5d7fca65434a5bb6d76e35dafd5f956e10d492086810cb3ca449db7baeb`.
Inside `proot-corresponding-sources.tar.gz`, `sources/talloc-2.4.3.tar.gz`
is exactly 684,092 bytes, SHA-256
`dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd`.
Those inner bytes were recovered and verified locally. The existing build
script accepts them through `--talloc-archive` without changing source inputs.

The installed, accepted Thor 0.1.5 APK remains the device baseline. Full Atlas
save/restart/resume persistence, Android game listener binding and a game APK
remain unqualified. The first live character save is now verified; do not
promote that partial result to full milestone acceptance.

## Native context limitation

Continuation run `36420158506` at `04b9771120737f3e8daf7b4740d2a9fcd6850f28`
also failed startup, but captured three processes, 72 thread contexts and 114
modules before cleanup. All 65 database sessions were idle. Successful Windows
API return codes **do not validate current emulator execution**.

Resolving those contexts against the hash-verified pinned Wine DLLs places
the three main-thread EIPs at `kernelbase!RaiseException+0x69`. Their EBX values
point to source filenames used by the game's thread-naming exception. At that
instruction the exception record should begin at `EBP-0x54`, equal to captured
ESP, but the independently read stack does not contain the expected exception
record. Most worker contexts still name `ntdll!RtlUserThreadStart`. These
inconsistent register and memory observations strongly indicate cached WOW64
contexts; they do not prove a thread-name exception hang or an active SQL call.
Raw stack words are not an unwound call chain.

The pinned FEX WOW64 implementation flushes emulator state for owned threads;
remote Windows context retrieval does not by itself establish that flush.
The recovery debugger now reports `current_execution_validated:false`, even
if its corrected native executable obtains output. Direct opt-in DbServer
dispatch markers are being developed in the separate continuation checkout.
Do not change SQL, skip AutoCommands, or extend timeouts based on these contexts.
See `game-context-analysis-36420158506.json` for artifact identities, exact
addresses, binary hashes and pinned source references.

## Subsequent observer qualification

Commit `f756f50b708cfd2307f460946918d1c24c36e0af` corrects WineDbg selection
and publishes the context limitation and terminal retry evidence. Game run
`36424870915` passed tooling and bridge build; ARM64 execution is in progress.
The corrected debugger affects failed-query inspection only.

Companion diagnostic run `36424871060` failed one of 130 tooling tests at
`DiagnosticProcessTests.assert_stopped`. The log shows the assertion returned
in milliseconds, before its three-second deadline. Its first liveness check
therefore observed exit, while the immediate second check returned alive.
The helper deliberately treats a successful kill(0) followed by an ambiguous
/proc disappearance as alive. Reaping a previously observed zombie between
those checks can therefore cause a false failure. The helper now retains the
first confirmed exit instead of invalidating it with an immediate second read.
No runtime cleanup or ownership logic changed. A deterministic stopped-then-
ambiguous observation reproduces the old failure and passes the fix. The local
130-test suite passed with two environment-dependent skips; hosted verification
is still required.
