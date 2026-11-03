# x86 track integration

Updated 2026-11-02 America/Chicago. Integration/handoff only; Claude leads next.
The x86 client is primary; ARM64 stays experimental and shelved.
Keep x86 Win32 servers, PhysX and ragdolls; cold-start goals remain unmeasured here.
Default branch remains main; no release, APK handoff or repository setting change.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification
  → m5-thor (b7806a6bd King's Row docs) → performance-path docs.
- P2/P3 sampler and Windows producer fixes included through 8dc2a66d72477b3c62227e572538b13f0e4f912b.
  See armport/notes/M5-SAMPLER-REVIEW.md and HANDOFF-X86.md.
- Last device result is .44: King's Row cold prep 656.024 s, request→arrival
  711.056 s, loaded render mean 25.63 FPS (11 complete windows).
  See armport/notes/M5-THOR-20261102-RESULTS.md and its export evidence.
- Both zone servers are x86; Atlas stays resident. Preparation swap pressure
  does not prove gameplay causation. No matched pre-port x86 baseline is supplied.
- Save committed, but Wine worker EACCES prevented proved owned cleanup;
  Atlas cache return failed and the data cache remained stranded.
- Historical .46 build40929292200/runtime40945708189/APK40952408285 succeeded;
  modern Thor build checks and retained-runtime execution have different scope.
- Startup instrumentation/ODBC reuse included; gain and ≤60 s remain unmeasured.
  Historical build41363927704 passed; runtime41372922907 rejected old 0119 pin
  before guest launch. Corrected pin and regression are included.
- .37 cleanup hardening ported at e50a0e42e; packaging admission at 263acad1f.
  Manual policy already superseded; dormant metadata/promotion chain skipped.
- Local ArmPort445/modern53 and guest27/64/17 pass. Cleanup whole-/proc has one
  inherited host EACCES error, reproduced on pristine c86; guards remain intact.
- Full interactive:3048 run/69 failures/28 errors/31 skips before fixture repair.
  Affected rerun138:2 legacy GPU-policy failures, no errors/skips; full is not green.
- Exact source, preserved logs, skips, runtime pins and pending frozen-head CI
  request: HANDOFF-X86.md and issue10. No new CI/APK chain was started here.
- Use X86-THOR-TEST.md for Claude's next reviewed x86 device baseline.

## Performance rounds (Claude, 2026-11-03; PR #11, issue #10)
- Fast mode (PRoot seccomp) default on: CI Atlas start −26/−32% (41588867344 vs 41584980465).
- Trusted bins: reopen Atlas 130→94 s (41610459604 vs 41605600310); inert with the shipping MapServer.
- CI creation re-parses ~230 s: CI's retained-progress MapServer fails the cache check (41630365042).
- 0.13.49 on the Thor (2 sessions, ARM64 client): in-world FPS mean 45-48, 91-97% windows ≥30;
  Atlas MapServer ready 204/222 s (.44: 287 s); King's Row failed (420 s Python budget, cold mirror).
- Shared-tree probes: scripts.loc clean, mirror 106→74 s (41636702283); wide set rebuilds bins (41648097743).
