# M3 report: incomplete

2026-10-23, branch armport/m3-atlas, draft PR #6. This report does not claim
the M3 exit test passes and is not a merge request.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run 39960894368 attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Claude accepted this item in PR #6 review 5635319013. |
| Rendered Atlas screenshot and client map name | Not met. Run 39973792458 stayed on the loading screen. Run 40011219458 stopped at textures.wait with 49 unchanged log-size samples. Run 40032719161 failed earlier in group loading with a Wine access violation at 0x6fffffdb7518 reading 0x50; it does not establish the texture stall's cause. |
| Original receive-code replay | Not met. Both inputs are recovered and hash-verified; replay_inventory.py validates envelopes only. Claude agreed to the method in review 5635319013, including a required same-driver i686 reference. See notes/M3-REPLAY-PLAN.md. |

The earlier trace run can be reproduced with:

```
python3 armport/scripts/ci_results.py --run 40032719161 --job server-run --no-wait --grep 'load status' 'zone stages' 'exceptions' 'crash'
```

## Changes and review follow-up

- 0044 preserves SOCKET width; 0045 supplies an explicit fake-auth version
  opt-in; 0047 tolerates missing world-group slots. See notes/64BIT-AUDIT.md.
- 0046, 0048, 0049 and 0051 remain kept-inert diagnostics, enabled only by
  ARMPORT_STDIO_LOG. They log UI/loading progress and thread identity without
  changing gameplay, queue ordering or timeouts. The QueueUserAPC call remains
  the original call; its diagnostic wrapper only reports failure.
  With ARMPORT_STDIO_LOG enabled, 0049's StartDummy/FinishDummy APC markers
  intentionally include every map load, even outside armportTracingTexQueue:
  earlier queue nesting is needed to interpret a later stuck Finish. Other
  detailed finish/drain markers remain gated. With the environment opt-in
  absent, all these markers are inert.
- 0050 fixes a reproduced worker wake/publication race on ARM64. Run
  40035482170, libraries job 120693769990: original dispatched=0, patched=1,
  then 4096 commands/replies each. wtReqFlush already wakes a queued worker;
  this latency fix is not established as the Atlas stall fix. The i686
  volatile-access ordering race remains; see notes/WORKER-QUEUE.md.
- The screen verdict now requires original textures.done and ready.sent after
  the latest Atlas map.start, two nonblank/non-loading client frames, and
  visible Atlas Park text. A black screen cannot pass. Human screenshot
  inspection remains required before completing M3.
- Bounded debugger sampling includes PC/LR and at most eight ARM64 frame-chain
  entries per thread. Missing/unusable chains remain diagnostic gaps. Actual
  sampling duration is excluded from the 1500-second loading observation;
  a debugger pause cannot itself satisfy that observation interval or prove
  rendering. SQL connection and cleanup checks remain required.

Local validation: `python3 -m unittest discover -s armport/tests -p 'test_*.py'
-v` passed 13 tests, including black/white/uniform frames, missing map name,
missing original completion, and stale completion from an earlier map.
The changed zone-trace header compiled in the ARM64 tex.c translation unit
(`ninja -j2 Game/CMakeFiles/Game.dir/src/render/tex.c.obj`, 8 existing warnings).
Run 40040798938 libraries passed the initial 12-test review suite and worker
controls; ci_results.py reads the new worker notices. The additional client-only
OCR crop test passed locally. Full Atlas and replay validation remain pending.

Run 40041703285 libraries passed all 13 host tests and the original socketless
network preflight. Run 40035482170 server-run failed before the texture wait.
Patch 0052 fixes a confirmed FILE*/FileWrapper* mismatch in the diagnostic
header; its before/after compile control and pinned-Wine disassembly are in
notes/M3-LOAD-STALL.md. Run 40042636088, libraries job 120717013954, passed
both CRT trace writes and the original socketless preflight. Server-run then failed after texqueue.drain.done, stopping at
texqueue.swaps.begin. Run 40043254025 repeats this boundary. See
notes/M3-LOAD-STALL.md; 0057 adds bounded swap/model/dialog diagnostics.
The cause remains unproven and Atlas remains unqualified.

## Reference coverage and review 5635783793

The i686 reference is the ArmPort-patched tree built with clang, so it checks
pointer-width/architecture differences but is not independent of shared
patches or compiler behavior. INITIAL must also match the recorded
native-android 32-bit decode; the same-driver comparison does not replace it.
Run 40043254232, reference-build job 120718968162, passed compile/link only.

Both builds disable NOVODEX; original i686 PhysX/ragdoll receive paths are
outside this comparison. i686 retains real CPUID and sseAvailable while
ARM64 reports no SSE; the zOcclusion/frustum rendering paths consequently
differ. Patch 0054 removes local SEH recovery only in the reference: the
keepMemoryThread call is already disabled by if(0), and volume-exit/audio
faults must fail replay, never be swallowed. See notes/M3-REPLAY-PLAN.md.

Review 5635783793 clarifies the ID 1/31 sensitivity comparison: preserve raw
IDs in dumps and normalize only pkt_id_create, lastClientStatePktId and
delete-history pkt_id when they equal that run's synthetic INITIAL ID.
Same-ID repeats and ARM64/i686 comparisons remain literally identical.
This agreement is not receiver execution or milestone approval.

The guest screenshot handshake now allows 2100 seconds, leaving headroom
over the host's unchanged 1500-second loading observation and diagnostic
pauses. ArmPort build runs once per internal branch push; branch-scoped
concurrency cancels superseded runs. Manual dispatch remains available.

## Remaining work

Patch 0056 now exposes the original receive switch below commGetStats, with
an inert post-startup hook. armport/replay/receiver.c verifies input identities,
dispatch counts/cursors and records original ACK IDs. Local llvm-mingw builds
of clientcomm.c, game.c and receiver.c pass for ARM64 Release and i686
OptDebug. Execution and full state comparison remain pending; the driver
explicitly exits 2 with m3_replay_complete=false even if all cursors pass.
The reference workflow now builds OptDebug because FINAL disables assertions.
See replay/README.md. No raw replay input or user report archive is committed.

The historical 0048 preprocessing check is also complete: all eight checks
in `check_zone_trace_preprocess.py ../build-active/compile_commands.json`
pass. The three original trace sites call CRT fprintf, the tex.c negative
control calls x_fprintf, and 0052 makes all four use CRT fprintf. Details
and commands are in notes/M3-LOAD-STALL.md.

Diagnose the loader stall/crash, obtain and inspect a rendered Atlas frame,
implement and run all 117 original receiver dispatches with i686 comparison,
then replace this incomplete report with the final results. No M3 approval,
merge, M4 completion or Thor gameplay claim is implied by build/unit success.
