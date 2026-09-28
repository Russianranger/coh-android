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

The installed, accepted Thor 0.1.5 APK remains the device baseline. The subsequent
complete guest sequence and host validation correction are recorded below.
Android game listener binding and a game APK remain unqualified.

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
`36424870915` passed tooling and bridge build and completed the full ARM64
guest sequence. Its final host-only rejection and correction are recorded below.
The corrected debugger affects failed-query inspection only and was not invoked
by this completed execution.

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
130-test suite passed with two environment-dependent skips. Commit
`47f7a927157dd9af0992e559b3db7bd62660858b` publishes the assertion fix;
hosted diagnostic run `36425243364` passed all five jobs, including tooling,
PostgreSQL, APK, database runtime and client runtime.

The independent continuation commit `41f3aff596826e22e2774375e11590de895ca33d`
adds opt-in main-thread dispatch publication. Its Wine DbServer run
`36425508780` passed the live Windows mapping contracts, normal and fixture
builds, Windows persistence, and all 28 ARM64 stages / 21 persistence checks
with complete owned cleanup. Both package and report artifact hashes were
independently verified. See `dispatch-dbserver-qualified-36425508780.json`.
That gate ran with the marker disabled; enabled FEX publication and Atlas
qualification remain pending. Its game reader remains separately in development.
That source change is not present in this recovery branch.

## Complete guest sequence and host contract correction

Run `36424870915` at `f756f50b708cfd2307f460946918d1c24c36e0af` finished the
guest at 13:33:14 UTC with `status:passed`, no failures, all 18 stages and
complete cleanup. `TEST05026` / container 1 connected, changed live influence
to 12345, and saved through protocol logout before forced client cleanup.
The same PostgreSQL cluster and game services restarted, and the committed SQL
snapshot remained identical. The same character resumed with creation disabled
and a processed server entity update, then completed a second protocol save.
LoginCount progressed 1 → 1 → 2; 1 Ents row, 1 Ents2 row, 12 powers and 14
costume parts remained unchanged. All 128 process captures closed; zero owned
processes and zero ownership inspection errors remained.

The original workflow is **failed**, not silently reclassified. After the guest
passed, `host_game_smoke.validate_session` required `result.child_exited:true`.
The real format-1 `TestClientBridge.c` producer never writes that field. It
writes an integer `child_exit_code` only when its owned process handle yields
a completed status from `GetExitCodeProcess`, excluding `STILL_ACTIVE`. Both
real receipts have code 125, forced cleanup after independent save proof, no
bridge error, a final console snapshot and complete disconnected pipe framing.
The synthetic host test had invented the extra boolean, masking the mismatch.

The host validator now requires the actual uint32 exit status, rejects null,
boolean, negative, oversized and STILL_ACTIVE values, and retains every identity,
pre-stop save proof, capture, framing and cleanup requirement. No game binary,
guest execution, runtime evidence or timeout changed. All 67 tooling tests pass,
including both real captured bridge receipts and invalid-status regressions.

Artifact `10973022843` is 8,984,584 bytes, SHA-256
`a539817527900628ed3387a7384fa230fd9dcaa9964b5373780d54b2b4210ee3`.
The unchanged 192,204-byte raw report is preserved as
`game-arm64-completed-36424870915.json`, SHA-256
`56a7e295c7a942176cb8ce353ad8cbf6f038894d04bb243334b69866e14ca015`.
Both client captures and all three SQL snapshots are preserved in
`game-captures-36424870915/`. The bounded replay tool pins the original archive,
donors, reviewed producer and accepted data/schema/runtime identities; it runs
the complete report, capture-file and service-capture validators on unmodified
bytes. Local replay passed. Independent CI revalidation is being published.

This run also recorded a successful 86.757-second cold-start readiness query.
It does not resolve earlier intermittent startup failures, which remain a
reliability issue. The continuation branch adopted this recovery's pinned
download retry after its instrumented attempt `36427680960` failed before game
execution. Further direct dispatch diagnostics are separate from this completed
unmodified-DbServer runtime evidence. Neither result qualifies Android game
execution, an interactive game surface or hardware-accelerated rendering.
