# Exact modern MapServer runtime qualification

Production source stays frozen at `e563fe5664cd13570899800695c7e9680ac68877`.
Native build: 41363927704. Supporting test code is independently identified and
cannot replace those candidate identities.

Implemented: full .36 donor hydration, exact native/source admission, the four
additional asset stages, actual completed-tick/DbServer readiness, Atlas creation,
ordinary committed save, explicit shipped zoning reopen and unchanged profile,
character, save and owned-cleanup validators. The task-gate payload stays intact.

Nine controls pass with:

```sh
COH_CANDIDATE_ROOT=/path/to/candidate python3 armport/modern-runtime/test_modern_runtime.py -v
```

Local full hydration passed: 23 external payloads / 4,786,799,760 bytes; 89 runtime
and 81 client pins; original importer contract 173,011 leaves / 2,977,730,517 bytes.
Evidence: `armport/evidence/modern-runtime-donor-hydration.json`. This did not
execute a native program or access a database.

A read-only x86 wait job now observes the exact native build and discovers the
unique same-source app runtime. It fails on upstream failure, duplicate runtime
runs or changed identities, then passes the successful runtime ID to the ARM job.
No manual ID placeholder or follow-up dispatch is needed. Setup commits use
[skip ci]; a single supporting workflow-only kickoff starts the wait.
Twelve waiter controls plus nine modern admission controls pass. The wait is
bounded to198 minutes; the ARM job then has its independent360-minute cap.
No write API, compiler or workflow dispatch exists in this read-only handoff.
The production branch stays frozen and its existing coordinator owns dispatch.

Each guest has its own existing 5,400-second correctness timeout. A passing pair
qualifies Atlas creation/save/reopen only. A third ordinary reopen uses the actual
authenticated original .36 modern MapServer and the same stopped disposable save
to test backward compatibility. It retains client/DbServer/data bytes and uses
verified PRoot file binds for immutable assets; candidate inodes and payloads are
unchanged. Six admission/continuity controls and independent review passed.
The prior read-only waiter41367191699 is cancelled before native execution and
a corrected workflow-only kickoff includes this third stage. King's Row, combat, rewards, collision,
zoning, memory/thermal behavior and Thor cold-start acceptance remain separate.
No <=60-second performance or physical-device result is claimed.
