# M3 report: incomplete

2026-10-23, branch armport/m3-atlas, draft PR #6. This report does not claim
the M3 exit test passes and is not a merge request.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run 39960894368 attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Claude accepted this item in PR #6 review 5635319013. |
| Rendered Atlas screenshot and client map name | Not met. Run 39973792458 stayed on the loading screen. Run 40011219458 stopped at textures.wait with 49 unchanged log-size samples. Run 40032719161 failed earlier in group loading with a Wine access violation at 0x6fffffdb7518 reading 0x50; it does not establish the texture stall's cause. |
| Original receive-code replay | Not met. Both inputs are recovered and hash-verified; replay_inventory.py validates envelopes only. Claude agreed to the method in review 5635319013, including a required same-driver i686 reference. See notes/M3-REPLAY-PLAN.md. |

The latest completed trace run can be reproduced with:

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
-v` passed 12 tests, including black/white/uniform frames, missing map name,
missing original completion, and stale completion from an earlier map.
The changed zone-trace header compiled in the ARM64 tex.c translation unit
(`ninja -j2 Game/CMakeFiles/Game.dir/src/render/tex.c.obj`, 8 existing warnings).
CI validation of these review follow-ups is pending.

## Remaining work

Diagnose the loader stall/crash, obtain and inspect a rendered Atlas frame,
implement and run all 117 original receiver dispatches with i686 comparison,
then replace this incomplete report with the final results. No M3 approval,
merge, M4 completion or Thor gameplay claim is implied by build/unit success.
